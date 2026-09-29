"""experiments/experiment_log.md dosyasını deney tanımları (configs/) ve sonuçlarından (results/) üretir.

  python -m experiments.report

Günlük elle düzenlenmez: gerekçe, hipotez ve yorumlar configs/EXP-*.json içindeki alanlara yazılır
("neden", "hipotez", "notlar"); sayılar results/ dosyalarından gelir. Böylece metin ile ölçüm hiçbir zaman
birbirinden kopmaz.
"""
import json

import config
from experiments import evaluation as ev

LOG_FILE = config.EXPERIMENTS_DIR / "experiment_log.md"
METRIC_NAMES = {
    "mrr@10": "MRR@10", "hit@1": "Hit@1", "hit@3": "Hit@3", "hit@5": "Hit@5", "hit@10": "Hit@10",
    "context_hit": "Bağlam isabeti", "context_chars": "Bağlam uzunluğu (karakter)",
    "latency_ms": "Getirme gecikmesi (ms)", "answer_acc": "Cevap doğruluğu",
}
DIRECTION_NAMES = {"artis": "artış", "azalis": "azalış", "degisim_yok": "değişim yok"}


def _load(folder):
    items = {}
    for path in sorted((config.EXPERIMENTS_DIR / folder).glob("EXP-*.json")):
        items[path.stem] = json.loads(path.read_text(encoding="utf-8"))
    return items


def _fmt(value, metric=None):
    if value is None:
        return "–"
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return str(value)
    if metric in ("context_chars", "latency_ms", "latency_ms_median"):
        return f"{value:,.0f}".replace(",", ".")
    return f"{float(value):.3f}".replace(".", ",")  # ortalaması tam 1 olan metrikler de 1,000 görünsün


def _fmt_delta(value, metric):
    if abs(value) < ev.NO_CHANGE_EPS:
        return "0"
    sign = "+" if value > 0 else "−"
    return sign + _fmt(abs(value), metric)


def _fmt_p(p):
    return "<0,001" if p < 0.001 else f"{p:.3f}".replace(".", ",")


def _fmt_param(v):
    return "`None`" if v is None else f"`{v}`"


def protocol(dataset, dataset_hash):
    n_ret = sum(1 for q in dataset["sorular"] if "kanit" in q)
    n_all = len(dataset["sorular"])
    return f"""# Deney Günlüğü

> Bu dosya `python -m experiments.report` ile **otomatik üretilir**; elle düzenlemeyin.
> Gerekçe/hipotez/yorumlar `experiments/configs/EXP-*.json`, sayılar `experiments/results/EXP-*.json` içindedir.
> Sohbet uygulamasının kullandığı yapılandırma: **{config.PRODUCTION_EXPERIMENT}** (`config.PRODUCTION_EXPERIMENT`).

## 1. Protokol

**Değerlendirme seti.** `eval/sorular.json`, sürüm {dataset['surum']} (SHA-256 ilk 16: `{dataset_hash}`).
{n_all} soru: {n_ret} tanesi belgelerde cevabı olan soru (getirme ve cevap değerlendirmesinde kullanılır),
{n_all - n_ret} tanesi kapsam dışı soru (yalnız cevap değerlendirmesinde). Tüm deneyler aynı set üzerinde koşulur;
set değişirse eski sonuçlarla karşılaştırma geçersiz sayılır ve günlükte işaretlenir.

**İlgililik.** Her soru için kaynak PDF ve kaynakta birebir geçen kısa bir *kanıt* ifadesi tanımlıdır (takvimde tarih ve
etkinlik birlikte). Bir parça; kaynak dosyası tutuyorsa ve kanıtı içeriyorsa ilgili sayılır. Karşılaştırmada Türkçe küçük
harfe çevrilir ve harf/rakam dışındaki her şey (boşluk, satır sonu, noktalama) yok sayılır. Bu sayede ölçüt **parçalama
yönteminden ve PDF okuyucudan bağımsızdır**. Koşucu, her kanıtın iki PDF okuyucusunun (pypdf, pdfplumber) ham metninde de
geçtiğini deney öncesinde doğrular.

**Metrikler** (soru başına hesaplanır, ortalaması raporlanır):

| Metrik | Tanım |
|---|---|
| MRR@10 | 1 / ilk ilgili parçanın sırası (ilk 10'da yoksa 0) |
| Hit@k | İlk k parçada ilgili parça var mı (k = 1, 3, 5, 10) |
| Bağlam isabeti | LLM'e verilen ilk `final_k` parçada ilgili parça var mı |
| Bağlam uzunluğu | LLM'e verilen bağlamın karakter sayısı (maliyet/gecikme göstergesi) |
| Getirme gecikmesi | Sorgu başına getirme süresi, LLM hariç (ms; donanıma bağlıdır) |
| Cevap doğruluğu | LLM cevabı beklenen anahtar kelimeleri içeriyor mu; kapsam dışı sorularda "{config.NO_ANSWER}" (`--llm` ile) |

**Tek değişken ilkesi.** Her deney bir *üst deneyden* türetilir ve ondan yalnız bir parametre farklıdır; koşucu bunu
denetler. Birden fazla parametrenin birlikte değişmesi gerekiyorsa gerekçe (`coklu_degisiklik_gerekcesi`) zorunludur.
Bazı parametreler bazı yapılandırmalarda etkisizdir (ör. `reranker_model` `None` iken `rerank_candidates`); bunlar
tüm deneylerde sabit tutulur ki farklar yalnız gerçek değişikliği göstersin.

**Karar kuralı** (deney koşulmadan önce belirlenir). Her deneyin bir *birincil metriği* ve *beklenen yönü* vardır.
Üst deneyle aynı sorular üzerinde eşleştirilmiş test yapılır: ikili metriklerde kesin McNemar testi, sürekli
metriklerde Wilcoxon işaretli sıra testi, α = 0,05.
- *Değişim yok*: fark 0.
- *Anlamlı iyileşme/kötüleşme*: fark ≠ 0 ve p < 0,05.
- *Sayısal iyileşme/kötüleşme (anlamlı değil)*: fark ≠ 0 ve p ≥ 0,05.
- Hipotez: gözlenen yön beklenenle aynı ve anlamlıysa *Doğrulandı*; yön aynı ama anlamlı değilse *Yön doğru, anlamlı değil*;
  aksi halde *Doğrulanmadı*. Beklenen sonucun çıkmaması da bir sonuç olarak kaydedilir.

**Tekrar üretme.** Her sonuç dosyası git commit'ini, commit edilmemiş değişiklik olup olmadığını, paket sürümlerini,
Hugging Face model revizyonlarını, donanımı ve indeks parmak izini içerir:

```
git checkout <commit>
python -m experiments.run EXP-XXX --yeniden
```

**Geçerlilik sınırları.** (1) Set küçüktür ({n_ret} soru): bir sorunun değişmesi Hit@k'yı {100 / n_ret:.1f} puan oynatır;
bu yüzden anlamlılık testleri tutucudur ve çoğu fark anlamlı çıkmayabilir. (2) Yapılandırma seçimleri aynı set üzerinde
yapıldığı için sonuçlar iyimser olabilir; tez için ayrı bir test seti ile son doğrulama önerilir. (3) Gecikme ölçümleri
yalnız aynı makinedeki deneyler arasında karşılaştırılabilir. (4) Gemini ücretsiz kotası (günlük 20 istek) nedeniyle cevap
doğruluğu ölçümleri ayrı günlerde yapılabilir.
"""


def summary_table(configs, results):
    lines = [
        "## 2. Özet",
        "",
        "| Deney | Üst | Değişiklik | MRR@10 | Hit@1 | Hit@3 | Hit@5 | Bağlam isabeti | Bağlam (kar.) | Gecikme (ms) | Cevap doğr. | Karar (birincil metrik) |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for exp_id, exp in configs.items():
        res = results.get(exp_id)
        if not res:
            lines.append(f"| {exp_id} | {exp['ust_deney'] or '–'} | {exp['baslik']} | koşulmadı |||||||||")
            continue
        m = res["retrieval"]["metrics"]
        llm = res.get("llm") or {}
        acc = (llm.get("metrics") or {}).get("answer_acc")
        karar = (res.get("karsilastirma") or {}).get("karar")
        verdict = f"{METRIC_NAMES[karar['metrik']]}: {karar['sonuc']}" if karar else "Referans"
        lines.append(
            f"| {exp_id} | {exp['ust_deney'] or '–'} | {exp['baslik']} | {_fmt(m['mrr@10'])} | {_fmt(m['hit@1'])} | "
            f"{_fmt(m['hit@3'])} | {_fmt(m['hit@5'])} | {_fmt(m['context_hit'])} | "
            f"{_fmt(m['context_chars'], 'context_chars')} | {_fmt(m['latency_ms'], 'latency_ms')} | "
            f"{_fmt(acc) if acc is not None else '–'} | {verdict} |")
    return "\n".join(lines)


def experiment_section(exp, res):
    out = [f"### {exp['id']} — {exp['baslik']}", ""]
    out.append(f"- **Üst deney:** {exp['ust_deney'] or '– (referans)'}")
    if res:
        env = res["environment"]
        dirty = " (commit edilmemiş değişiklik vardı)" if env["git_dirty"] else ""
        out.append(f"- **Koşulma:** {res['calisma_zamani']}, commit `{(env['git_commit'] or '?')[:10]}`{dirty}, "
                   f"veri seti {res['dataset']['surum']} (`{res['dataset']['hash']}`)")
    out.append("")

    diff = res["degisen_parametreler"] if res else {}
    if diff:
        out += ["**Değişen parametre(ler):**", "", "| Parametre | Üst deney | Bu deney |", "|---|---|---|"]
        out += [f"| `{k}` | {_fmt_param(a)} | {_fmt_param(b)} |" for k, (a, b) in diff.items()]
        out.append("")
    if exp.get("coklu_degisiklik_gerekcesi"):
        out += [f"**Birden fazla parametrenin birlikte değişme gerekçesi:** {exp['coklu_degisiklik_gerekcesi']}", ""]
    out += [f"**Neden:** {exp['neden']}", ""]
    if exp["ust_deney"]:
        out += [f"**Hipotez:** {exp['hipotez']} *(Birincil metrik: {METRIC_NAMES[exp['birincil_metrik']]}, "
                f"beklenen yön: {DIRECTION_NAMES[exp['beklenen_yon']]})*", ""]

    if not res:
        return "\n".join(out + ["*Henüz koşulmadı.*", ""])

    m = res["retrieval"]["metrics"]
    comp = res.get("karsilastirma")
    out += ["**Sonuçlar:**", ""]
    if comp and comp.get("ayni_veri_seti"):
        out += ["| Metrik | Üst deney | Bu deney | Fark | Test | p |", "|---|---|---|---|---|---|"]
        for metric, c in comp["metrikler"].items():
            extra = f" ({c['iyilesen']}↑ / {c['kotulesen']}↓ soru)" if "iyilesen" in c else ""
            out.append(f"| {METRIC_NAMES[metric]} | {_fmt(c['once'], metric)} | {_fmt(c['sonra'], metric)} | "
                       f"{_fmt_delta(c['fark'], metric)} | {c['test']}{extra} | {_fmt_p(c['p'])} |")
        out.append("")
        k = comp["karar"]
        out += [f"**Karar:** {k['sonuc']} — birincil metrik {METRIC_NAMES[k['metrik']]}. "
                f"**Hipotez:** {k['hipotez']}.", ""]
        if comp["degisen_sorular"]:
            changes = ", ".join(f"{d['id']} ({d['once'] or '>10'}→{d['sonra'] or '>10'})"
                                for d in comp["degisen_sorular"])
            out += [f"**İlk ilgili parçanın sırası değişen sorular:** {changes}", ""]
        else:
            out += ["**İlk ilgili parçanın sırası değişen soru yok.**", ""]
    else:
        if comp and not comp.get("ayni_veri_seti"):
            out += [f"> {comp['uyari']}", ""]
        out += ["| Metrik | Değer |", "|---|---|"]
        out += [f"| {METRIC_NAMES[k]} | {_fmt(m[k], k)} |" for k in METRIC_NAMES if k in m]
        out.append("")

    misses = [r["id"] for r in res["retrieval"]["per_question"] if not r["rank"]]
    if misses:
        out += [f"**İlk 10'da ilgili parça bulunamayan sorular:** {', '.join(misses)}", ""]
    llm = res.get("llm")
    if llm:
        state = "" if llm["tamamlandi"] else " (kota nedeniyle yarıda kaldı)"
        wrong = [r["id"] for r in llm["per_question"] if not r["answer_ok"]]
        out += [f"**Cevap değerlendirmesi{state}:** {llm['metrics']['n']} soru, doğruluk "
                f"{_fmt(llm['metrics']['answer_acc'])}" + (f"; yanlış: {', '.join(wrong)}" if wrong else ""), ""]
    else:
        out += ["**Cevap değerlendirmesi:** bu koşuda yapılmadı (`--llm`).", ""]

    idx = res["index"]
    out += [f"**İndeks:** {idx['chunks']} parça, ortalama {idx['avg_chunk_chars']:.0f} karakter, "
            f"kurulum {idx['build_seconds']} sn (parmak izi `{idx['fingerprint']}`). "
            f"Medyan getirme gecikmesi {_fmt(m['latency_ms_median'], 'latency_ms')} ms.", ""]
    if exp.get("notlar"):
        out += [f"**Yorum:** {exp['notlar']}", ""]
    out += ["<details><summary>Tüm parametreler</summary>", "", "| Parametre | Değer |", "|---|---|"]
    out += [f"| `{k}` | {_fmt_param(v)} |" for k, v in res["params"].items()]
    out += ["", "</details>", ""]
    return "\n".join(out)


def build():
    dataset, dataset_hash = ev.load_dataset()
    configs = _load("configs")
    results = _load("results")
    parts = [protocol(dataset, dataset_hash), summary_table(configs, results), "", "## 3. Deneyler", ""]
    parts += [experiment_section(exp, results.get(exp_id)) for exp_id, exp in configs.items()]
    LOG_FILE.write_text("\n".join(parts), encoding="utf-8")


if __name__ == "__main__":
    build()
    print(f"Yazıldı: {LOG_FILE}")
