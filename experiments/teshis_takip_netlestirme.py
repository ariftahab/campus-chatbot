"""Teşhis (deney değil): netleştirmeden sonra kullanıcı yönetmeliği olmayan bir fakülteyi söyleyince ne oluyor?

  python experiments/teshis_takip_netlestirme.py <llm_model> <çıktı.json>

Production yapılandırması, yalnız LLM modeli değiştirilerek. Her senaryoda önce fakülteye göre değişen bir soru
sorulur (netleştirme açılır ve model fakülteyi sorar), sonra kullanıcı kendi yönetmeliği olmayan bir fakülteyi söyler.
Ölçülen: ikinci turda netleştirme yeniden açıldı mı, model fakülteyi tekrar sordu mu, rewrite ve cevap.
Senaryo başına ~3 LLM isteği (6 senaryo, ~18 istek).
"""
import json
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from langchain_google_genai import ChatGoogleGenerativeAI  # noqa: E402

import config  # noqa: E402
import ingest  # noqa: E402
import rag  # noqa: E402
from experiments.run import asks_unit  # noqa: E402

SCENARIOS = [
    ("Teorik derslerin yüzde kaçına girmek zorundayım?", "Mühendislik fakültesi"),
    ("Mezun olmak için kaç kredi almam gerekiyor?", "İktisadi ve idari bilimlerdeyim"),
    ("Kayıt dondurma hangi durumlarda yapılabilir?", "fen edebiyat"),
    ("Finalden kalırsam bütünleme sınavına girebilir miyim?", "eğitim fakültesi"),
    ("Okulu en fazla kaç yılda bitirmem gerekiyor?", "ziraat fakültesindeyim"),
    ("Mezun olmak için not ortalamam en az kaç olmalı?", "Mimarlık"),
]


def main(model, out_path):
    cfg = replace(config.production_config(), llm_model=model)
    store, chunks, _ = ingest.load_index(cfg)
    bot = rag.RagBot(cfg, rag.Retriever(cfg, store, chunks),
                     ChatGoogleGenerativeAI(model=model, temperature=cfg.llm_temperature, max_retries=0))
    rows = []
    for q1, q2 in SCENARIOS:
        a1 = bot.ask(q1)
        history = [{"role": "user", "content": q1}, {"role": "assistant", "content": a1["answer"]}]
        a2 = bot.ask(q2, history)
        row = {"soru": q1, "tetik1": a1["clarify"], "sordu1": asks_unit(a1["answer"]), "cevap1": a1["answer"],
               "takip": q2, "rewrite": a2["query"], "tetik2": a2["clarify"], "sordu2": asks_unit(a2["answer"]),
               "cevap2": a2["answer"]}
        rows.append(row)
        print(f"[{q2}] 1. tur: tetik={row['tetik1']} sordu={row['sordu1']} | 2. tur: tetik={row['tetik2']} "
              f"TEKRAR SORDU={row['sordu2']}", flush=True)
    Path(out_path).write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
