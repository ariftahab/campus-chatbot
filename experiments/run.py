"""Deney koşturucu.

  python -m experiments.run EXP-003            # tek deney
  python -m experiments.run EXP-001 EXP-002    # sırayla birkaç deney
  python -m experiments.run --all              # tüm deneyler (sonucu olanlar atlanır)
  python -m experiments.run EXP-008 --llm      # cevap kalitesini de ölç (Gemini kotası harcar)
  python -m experiments.run EXP-003 --yeniden  # var olan sonucu yeniden üret

Her deney experiments/configs/EXP-*.json dosyasıyla tanımlanır. Sonuç experiments/results/EXP-*.json'a
yazılır ve experiments/experiment_log.md yeniden üretilir.
"""
import argparse
import json
import re
import statistics
import sys
import time
from datetime import datetime

import config
from experiments import evaluation as ev
from experiments import report

CONFIGS_DIR = config.EXPERIMENTS_DIR / "configs"
RESULTS_DIR = config.EXPERIMENTS_DIR / "results"
REQUIRED_FIELDS = ("id", "baslik", "ust_deney", "neden", "hipotez", "birincil_metrik", "beklenen_yon", "params")


def load_result(exp_id):
    path = RESULTS_DIR / f"{exp_id}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def dataset_name(exp):
    """Deneyin soru seti (eval/<ad>.json). Alan yoksa ilk set: EXP-000..016 onunla koşuldu."""
    return exp.get("veri_seti", ev.DEFAULT_DATASET)


def param_diff(exp):
    """Üst deneye göre değişen parametreler: {ad: [eski, yeni]}.

    Soru seti RAG parametresi değil ama değişirse deneyin tek değişkeni odur; bu yüzden farka dahil edilir.
    """
    if not exp["ust_deney"]:
        return {}
    parent_exp = config.load_experiment(exp["ust_deney"])
    parent = {**config.full_params(parent_exp["params"]), "veri_seti": dataset_name(parent_exp)}
    child = {**config.full_params(exp["params"]), "veri_seti": dataset_name(exp)}
    return {k: [parent[k], v] for k, v in child.items() if parent.get(k) != v}


def check_experiment(exp):
    missing = [f for f in REQUIRED_FIELDS if f not in exp]
    if missing:
        raise SystemExit(f"{exp.get('id')}: eksik alanlar {missing}")
    if exp["birincil_metrik"] not in ev.METRIC_DIRECTION:
        raise SystemExit(f"{exp['id']}: bilinmeyen birincil metrik {exp['birincil_metrik']}")
    if exp["beklenen_yon"] not in ("artis", "azalis", "degisim_yok"):
        raise SystemExit(f"{exp['id']}: beklenen_yon artis | azalis | degisim_yok olmalı")
    config.RagConfig.from_dict(exp["params"])  # parametre doğrulaması
    if not ev.dataset_path(dataset_name(exp)).exists():
        raise SystemExit(f"{exp['id']}: soru seti bulunamadı: {ev.dataset_path(dataset_name(exp))}")
    diff = param_diff(exp)
    if exp["ust_deney"] and not diff:
        raise SystemExit(f"{exp['id']}: üst deneyden hiçbir parametre farklı değil.")
    # Tek değişken ilkesi: birden fazla parametre değişiyorsa gerekçe yazılmış olmalı.
    if len(diff) > 1 and not exp.get("coklu_degisiklik_gerekcesi"):
        raise SystemExit(f"{exp['id']}: birden fazla parametre değişiyor {sorted(diff)}; etkiyi izole etmek için "
                         f"ayrı deneylere bölün ya da 'coklu_degisiklik_gerekcesi' yazın.")
    return diff


def ensure_index(exp_id, cfg):
    """İndeks yoksa ayrı bir süreçte kurar.

    Aynı süreçte kurulursa embedding hesabının GPU belleği (PyTorch önbelleği) retrieval ölçümü sırasında
    da tutulur; 6 GB'lık kartta VRAM dolup Windows belleği sistem RAM'ine taşıyınca latency birkaç kat
    şişiyordu (EXP-016: 2220 ms, ayrı süreçte ~400 ms). Süreç bitince belleğin tamamı geri verilir, böylece
    latency her zaman "indeks hazır, temiz süreç" koşulunda ölçülür.
    """
    import subprocess
    import ingest
    if not (ingest.index_dir(cfg) / "manifest.json").exists():
        subprocess.run([sys.executable, "ingest.py", exp_id], cwd=config.ROOT, check=True)


def evaluate_retrieval(cfg, retriever, items):
    retriever.rank(items[0]["soru"])  # ısınma: ilk çağrıdaki model/önbellek yüklemesi süreye katılmasın
    rows = []
    for item in items:
        trace = {}
        started = time.perf_counter()
        ranking = retriever.rank(item["soru"], depth=ev.EVAL_DEPTH, trace=trace)
        latency = (time.perf_counter() - started) * 1000
        top = ranking[:ev.EVAL_DEPTH]
        relevant = [ev.is_relevant(item, ev.norm(c.page_content), c.metadata["source"]) for c in top]
        first = next((i + 1 for i, r in enumerate(relevant) if r), None)
        context = ranking[:cfg.final_k]
        row = {
            "id": item["id"],
            "rank": first,
            "rr": 1 / first if first else 0.0,
            "context_hit": int(any(relevant[:cfg.final_k])),
            "context_chars": sum(len(c.page_content) for c in context),
            "latency_ms": round(latency, 1),
            "top5": [f"{c.metadata['source']} s.{c.metadata['page']}"
                     + (f" m.{c.metadata['madde']}" if "madde" in c.metadata else "") for c in top[:5]],
        }
        for k in ev.HIT_KS:
            row[f"hit@{k}"] = int(bool(first and first <= k))
        row["asamalar"] = stage_ranks(item, retriever.chunks, trace)
        rows.append(row)
    return rows


def stage_ranks(item, chunks, trace):
    """Her ara listede ilk ilgili parçanın sırası (1'den başlar; listede yoksa None).

    Böylece bir hatanın aday üretiminde mi (ilgili parça hiçbir listeye girmemiş: recall hatası)
    yoksa sıralamada mı (aday listesinde var ama aşağıda kalmış: ranking hatası) oluştuğu görülür.
    """
    cache = {}

    def relevant(cid):
        if cid not in cache:
            c = chunks[cid]
            cache[cid] = ev.is_relevant(item, ev.norm(c.page_content), c.metadata["source"])
        return cache[cid]

    return {stage: next((i + 1 for i, cid in enumerate(ids) if relevant(cid)), None)
            for stage, ids in trace.items()}


def stage_metrics(rows):
    """Aşama başına MRR@10; reranker varsa ilgili parçanın reranker'a giden adaylar içinde olma oranı."""
    out = {}
    for stage in rows[0]["asamalar"]:
        ranks = [r["asamalar"][stage] for r in rows]
        if stage == "rerank_input":
            out["rerank_input_recall"] = round(statistics.mean(int(x is not None) for x in ranks), 4)
        else:
            out[f"{stage}_mrr@10"] = round(statistics.mean(
                1 / x if x and x <= ev.EVAL_DEPTH else 0.0 for x in ranks), 4)
    return out


def summarize(rows, key):
    return round(statistics.mean(r[key] for r in rows), 4)


def retrieval_metrics(rows):
    m = {"mrr@10": summarize(rows, "rr")}
    for k in ev.HIT_KS:
        m[f"hit@{k}"] = summarize(rows, f"hit@{k}")
    m["context_hit"] = summarize(rows, "context_hit")
    m["context_chars"] = round(statistics.mean(r["context_chars"] for r in rows), 1)
    m["latency_ms"] = round(statistics.mean(r["latency_ms"] for r in rows), 1)
    m["latency_ms_median"] = round(statistics.median(r["latency_ms"] for r in rows), 1)
    return m


def answer_rows(bot, items, wait):
    rows = []
    for n, item in enumerate(items):
        try:
            answer = bot.ask(item["soru"])["answer"]  # geçmişsiz: her soru bağımsız
        except Exception as e:  # kota dolarsa kalan soruları boşuna deneme
            print(f"  LLM hatası ({item['id']}): {type(e).__name__}: {str(e)[:200]}")
            if "ResourceExhausted" in type(e).__name__ or "429" in str(e):
                print("  Kota dolu; cevap değerlendirmesi yarıda kesildi.")
                return rows, False
            answer = f"<hata: {type(e).__name__}>"
        rows.append({"id": item["id"], "answer": answer, "answer_ok": int(answer_ok(item, answer))})
        print(f"  {item['id']} cevap {'OK' if rows[-1]['answer_ok'] else 'YANLIŞ'}")
        if n + 1 < len(items):
            time.sleep(wait)
    return rows, True


def _normalize_answer(text):
    return re.sub(r"\b0(\d)", r"\1", ev.tr_lower(text))  # "05 Ocak" == "5 Ocak"


def answer_ok(item, answer):
    normalize = _normalize_answer
    answer = normalize(answer)
    if item.get("cevapsiz"):
        # 'kabul': belge tutarı/saati vermiyor ama kimin belirlediğini söylüyor; bunu söyleyen cevap da doğru.
        return any(normalize(x) in answer for x in [config.NO_ANSWER, *item.get("kabul", [])])
    return all(any(normalize(alt) in answer for alt in kw.split("|")) for kw in item["beklenen"])


def compare(exp, result, parent):
    """Üst deneyle aynı sorular üzerinde eşleştirilmiş karşılaştırma."""
    same_data = parent["dataset"]["hash"] == result["dataset"]["hash"]
    out = {"ust_deney": exp["ust_deney"], "ayni_veri_seti": same_data, "metrikler": {}}
    if not same_data:
        out["uyari"] = "Üst deney farklı bir veri seti sürümüyle koşulmuş; karşılaştırma geçersiz."
        return out
    for metric, key in ev.PER_QUESTION_KEY.items():
        source = "llm" if metric == "answer_acc" else "retrieval"
        a, b = parent.get(source), result.get(source)
        if not a or not b or not a.get("tamamlandi", True) or not b.get("tamamlandi", True):
            continue
        before_rows = {r["id"]: r[key] for r in a["per_question"]}
        after_rows = {r["id"]: r[key] for r in b["per_question"]}
        ids = [i for i in after_rows if i in before_rows]
        before = [before_rows[i] for i in ids]
        after = [after_rows[i] for i in ids]
        before_mean, after_mean = statistics.mean(before), statistics.mean(after)
        test = ev.paired_test(metric, before, after)
        out["metrikler"][metric] = {
            "once": round(before_mean, 4), "sonra": round(after_mean, 4),
            "fark": round(after_mean - before_mean, 4), **test,
        }
    primary = exp["birincil_metrik"]
    if primary in out["metrikler"]:
        m = out["metrikler"][primary]
        outcome, hypothesis = ev.verdict(primary, m["fark"], m["p"], exp["beklenen_yon"])
        out["karar"] = {"metrik": primary, "beklenen_yon": exp["beklenen_yon"],
                        "sonuc": outcome, "hipotez": hypothesis}
    else:
        out["karar"] = {"metrik": primary, "beklenen_yon": exp["beklenen_yon"],
                        "sonuc": "Ölçülmedi", "hipotez": "Beklemede (birincil metrik bu koşuda ölçülmedi)"}
    # Sıralaması değişen sorular (tezde hata analizi için)
    before_rank = {r["id"]: r["rank"] for r in parent["retrieval"]["per_question"]}
    out["degisen_sorular"] = [
        {"id": r["id"], "once": before_rank.get(r["id"]), "sonra": r["rank"]}
        for r in result["retrieval"]["per_question"] if before_rank.get(r["id"]) != r["rank"]
    ]
    return out


def subset_metrics(rows, items, answers=None):
    """Soru alt grupları için ortalamalar: eski/yeni set, stil (belge/öğrenci dili), kategori.

    Set 2.0'da bu alanlar yok; o zaman boş döner. Grup küçükse (birkaç soru) ortalama gürültülüdür.
    """
    meta = {q["id"]: q for q in items}
    groups = {}
    for key in ("stil", "kategori"):
        for r in rows:
            if key in meta[r["id"]]:
                groups.setdefault(f"{key}:{meta[r['id']][key]}", []).append(r["id"])
    if any("stil" in q for q in items):
        for r in rows:
            groups.setdefault("set:eski" if meta[r["id"]].get("eski_set") else "set:yeni", []).append(r["id"])
    by_id = {r["id"]: r for r in rows}
    ok = {a["id"]: a["answer_ok"] for a in (answers or [])}
    out = {}
    for name, ids in sorted(groups.items()):
        out[name] = {"n": len(ids), "mrr@10": round(statistics.mean(by_id[i]["rr"] for i in ids), 4),
                     "hit@5": round(statistics.mean(by_id[i]["hit@5"] for i in ids), 4)}
        answered = [ok[i] for i in ids if i in ok]
        if answered:
            out[name]["answer_acc"] = round(statistics.mean(answered), 4)
    return out


def run(exp_id, use_llm, wait, rerun, datasets):
    exp = config.load_experiment(exp_id)
    diff = check_experiment(exp)
    dataset, dataset_hash = datasets(dataset_name(exp))
    if load_result(exp_id) and not rerun:
        print(f"{exp_id}: sonuç zaten var, atlanıyor (yeniden üretmek için --yeniden).")
        return
    if exp["ust_deney"] and not load_result(exp["ust_deney"]):
        print(f"{exp_id}: üst deney {exp['ust_deney']} henüz koşulmamış; karşılaştırma yapılmayacak.")

    cfg = config.RagConfig.from_dict(exp["params"])
    print(f"\n=== {exp_id}: {exp['baslik']}")
    for k, (old, new) in diff.items():
        print(f"    {k}: {old} -> {new}")

    from rag import RagBot, Retriever
    import ingest
    ensure_index(exp_id, cfg)
    store, chunks, manifest = ingest.load_index(cfg)
    retriever = Retriever(cfg, store, chunks)
    items = [q for q in dataset["sorular"] if ev.answerable(q)]
    rows = evaluate_retrieval(cfg, retriever, items)

    env = ev.environment(cfg)
    if env["git_dirty"]:
        print("  UYARI: çalışma dizininde commit edilmemiş değişiklik var; sonuç tam tekrar üretilemeyebilir.")
    result = {
        "id": exp_id,
        "calisma_zamani": datetime.now().isoformat(timespec="seconds"),
        "dataset": {"dosya": f"eval/{dataset_name(exp)}.json", "surum": dataset["surum"], "hash": dataset_hash,
                    "n_getirme": len(items),
                    "n_toplam": len(dataset["sorular"])},
        "params": exp["params"],
        "degisen_parametreler": diff,
        "index": manifest,
        "environment": env,
        "retrieval": {"metrics": retrieval_metrics(rows), "asamalar": stage_metrics(rows), "per_question": rows},
        "llm": None,
    }
    if use_llm:
        from langchain_google_genai import ChatGoogleGenerativeAI
        llm = ChatGoogleGenerativeAI(model=cfg.llm_model, temperature=cfg.llm_temperature, max_retries=2)
        bot = RagBot(cfg, retriever, llm)  # getirme için yüklenen retriever yeniden kullanılır
        answers, complete = answer_rows(bot, dataset["sorular"], wait)
        result["llm"] = {
            "tamamlandi": complete,
            "metrics": {"answer_acc": summarize(answers, "answer_ok") if answers else None,
                        "n": len(answers)},
            "per_question": answers,
        }
    llm_rows = result["llm"]["per_question"] if result["llm"] else None
    result["retrieval"]["alt_kirilimlar"] = subset_metrics(rows, items, llm_rows)
    parent = load_result(exp["ust_deney"]) if exp["ust_deney"] else None
    result["karsilastirma"] = compare(exp, result, parent) if parent else None

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / f"{exp_id}.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    m = result["retrieval"]["metrics"]
    print(f"  MRR@10={m['mrr@10']:.3f} Hit@1={m['hit@1']:.3f} Hit@5={m['hit@5']:.3f} "
          f"bağlam isabeti={m['context_hit']:.3f} gecikme={m['latency_ms']:.0f} ms")
    print("  Aşamalar: " + " ".join(f"{k}={v:.3f}" for k, v in result["retrieval"]["asamalar"].items()))
    if result["karsilastirma"] and "karar" in result["karsilastirma"]:
        k = result["karsilastirma"]["karar"]
        print(f"  Karar ({k['metrik']}): {k['sonuc']} | Hipotez: {k['hipotez']}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("ids", nargs="*")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--llm", action="store_true", help="cevap kalitesini de ölç (Gemini kotası harcar)")
    parser.add_argument("--bekle", type=float, default=4.0, help="LLM çağrıları arası saniye")
    parser.add_argument("--yeniden", action="store_true", help="var olan sonucun üzerine yaz")
    args = parser.parse_args()

    ids = sorted(p.stem for p in CONFIGS_DIR.glob("EXP-*.json")) if args.all else args.ids
    if not ids:
        parser.error("deney kimliği ya da --all verin")

    cache = {}

    def datasets(name):
        """Soru setini bir kez yükleyip doğrular (her deney kendi setini seçebilir)."""
        if name not in cache:
            dataset, dataset_hash = ev.load_dataset(name)
            problems = ev.validate_dataset(dataset)
            if problems:
                raise SystemExit(f"Soru seti ({name}) doğrulaması başarısız:\n  " + "\n  ".join(problems))
            cache[name] = (dataset, dataset_hash)
        return cache[name]

    for exp_id in ids:
        run(exp_id, args.llm, args.bekle, args.yeniden, datasets)
    report.build()
    print(f"\nGünlük güncellendi: {report.LOG_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
