"""Değerlendirme: eval/sorular.json'daki sorularla getirme ve cevap kalitesini ölçer.

  python eval.py          -> sadece getirme (API çağrısı yok, ücretsiz)
  python eval.py --llm    -> cevapları da Gemini ile üretip kontrol eder

Getirme başarısı: beklenen madde/takvim bölümü LLM'e giden parçalar arasında mı?
Cevap başarısı: cevap beklenen anahtar kelimeleri içeriyor mu? ("a|b" = a veya b)
"""
import argparse
import json
import re
import time

import config
from rag import RagBot, tr_lower


def normalize(text):
    text = tr_lower(text)
    return re.sub(r"\b0(\d)", r"\1", text)  # "05 Ocak" == "5 Ocak"


def retrieval_hit(item, docs):
    for d in docs:
        m = d.metadata
        if m["source"] != item["kaynak"]:
            continue
        if "madde" in item and m.get("madde") == item["madde"]:
            return True
        if "bolum" in item and item["bolum"] in m.get("section", ""):
            return True
    return False


def answer_ok(item, answer):
    answer = normalize(answer)
    if item.get("cevapsiz"):
        return normalize(config.NO_ANSWER) in answer
    return all(any(normalize(alt) in answer for alt in kw.split("|")) for kw in item["beklenen"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--llm", action="store_true", help="cevapları da üret ve kontrol et")
    parser.add_argument("--bekle", type=float, default=4.0, help="LLM çağrıları arası saniye (kota için)")
    args = parser.parse_args()

    items = json.loads(config.EVAL_FILE.read_text(encoding="utf-8"))
    bot = RagBot.from_index()

    ret_total = ret_hits = ans_total = ans_hits = 0
    for n, item in enumerate(items, start=1):
        bot.reset()
        marks = []
        if "kaynak" in item:
            _, docs = bot.retrieve(item["soru"])
            hit = retrieval_hit(item, docs)
            ret_total += 1
            ret_hits += hit
            marks.append("getirme " + ("OK " if hit else "YOK"))
        if args.llm:
            try:
                answer = bot.ask(item["soru"])["answer"]
            except Exception as e:
                answer = f"<hata: {type(e).__name__}: {e}>"
            ok = answer_ok(item, answer)
            ans_total += 1
            ans_hits += ok
            marks.append("cevap " + ("OK " if ok else "YANLIŞ"))
            time.sleep(args.bekle)
        print(f"{n:2}. [{' | '.join(marks)}] {item['soru']}")
        if args.llm and not ok:
            print(f"      cevap: {answer[:300]}")

    print()
    if ret_total:
        print(f"Getirme başarısı: {ret_hits}/{ret_total} ({ret_hits / ret_total:.0%})")
    if ans_total:
        print(f"Cevap başarısı:   {ans_hits}/{ans_total} ({ans_hits / ans_total:.0%})")


if __name__ == "__main__":
    main()
