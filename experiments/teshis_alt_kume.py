"""Teşhis (deney değil): bir deneyin yapılandırmasıyla, bir parametre değiştirilerek yalnız seçilen sorular sorulur.

  python experiments/teshis_alt_kume.py <EXP-ID> <param=değer> <soru id'leri, virgülle> <çıktı.json> [karşılaştırılacak EXP-ID'ler...]

Bütün seti koşmadan önce bir değişikliğin sorunlu sorularda işe yarayıp yaramadığını görmek için (ör. EXP-034'te
çekimser kalmayan iki soru): soru başına 1 LLM isteği (takip sorularında +1 rewrite). İyileşme varsa değişiklik yeni
bir deney config'iyle bütün sette koşulur; bu çıktı deney sonucu yerine geçmez.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from langchain_google_genai import ChatGoogleGenerativeAI  # noqa: E402

import config  # noqa: E402
import ingest  # noqa: E402
import rag  # noqa: E402
from experiments.run import answer_rows, dataset_name, load_result  # noqa: E402


def main(exp_id, override, ids, out_path, compare_ids):
    exp = config.load_experiment(exp_id)
    key, value = override.split("=", 1)
    cfg = config.RagConfig.from_dict({**exp["params"], key: value})  # from_dict değeri de denetler
    dataset = json.loads((config.ROOT / "eval" / f"{dataset_name(exp)}.json").read_text(encoding="utf-8"))
    wanted = ids.split(",")
    items = [q for q in dataset["sorular"] if q["id"] in wanted]
    store, chunks, _ = ingest.load_index(cfg)
    bot = rag.RagBot(cfg, rag.Retriever(cfg, store, chunks),
                     ChatGoogleGenerativeAI(model=cfg.llm_model, temperature=cfg.llm_temperature, max_retries=2))
    rows, _ = answer_rows(bot, items, wait=4.0)
    old = {c: {r["id"]: r for r in load_result(c)["llm"]["per_question"]} for c in compare_ids}
    for item, row in zip(items, rows):
        print(f"\n===== {item['soru']}  (gecmis: {bool(item.get('gecmis'))}, "
              f"beklenen_davranis: {item.get('beklenen_davranis')})")
        for c in compare_ids:
            r = old[c][item["id"]]
            print(f"  {c}: ok={r['answer_ok']} sordu={r['netlestirme']} {len(r['answer'])} kr | {r['answer'][:300]}")
        print(f"  YENİ: ok={row['answer_ok']} sordu={row['netlestirme']} tetik={row.get('netlestirme_tetik')} "
              f"{len(row['answer'])} kr | {row['answer']}")
    Path(out_path).write_text(json.dumps({"deney": exp_id, "degisiklik": override, "sorular": rows},
                                         ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5:])
