"""Soru türü başına cevap doğruluğu: anahtar kelimeyle ve anlamca.

  python experiments/kategori_raporu.py <EXP-ID>

Kararlar experiments/anlamca/<EXP-ID>.json'dan okunur (soru başına 'anahtar' ve 'anlamca'). Soru türü set dosyasındaki
'soru_turu' alanından; alan yoksa (val-1.0 gibi değiştirilmeyen eski setler) eval/soru_turleri_<set>.json'dan gelir.
'coklu_belge' türündeki bir sorunun bütün kaynakları aynı belgedeyse 'coklu_madde' (tek belge, birden fazla madde)
sayılır (kullanıcı kararı, 2026-10-28): ayrım kaynaklardan türetilir, set dosyaları değişmez.
Çıktı markdown tablosu; config 'notlar' alanına ve günlüklere buradan aktarılır.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
from experiments.run import dataset_name  # noqa: E402

# Tablodaki sıra ve adlar (kullanıcının 6 kategorisi, ardından sistemdeki 3 davranış)
TURLER = {
    "duz": "1. Belgede var, düz soru",
    "farkli_ifade": "2. Belgede var, farklı ifade",
    "coklu_madde": "3a. Tek belge, birden fazla madde",
    "coklu_belge": "3b. Birden fazla belge",
    "belgede_yok": "4. Belgede yok, konu yakın",
    "konu_disi": "5. Konu dışı",
    "yazim_hatali": "6. Yazım hatalı / argo",
    "netlestirme": "7. Netleştirme gerekir",
    "takip": "8. Takip sorusu",
    "yanlis_oncul": "9. Yanlış öncül",
}


def question_types(set_name, items):
    if all("soru_turu" in q for q in items):
        types = {q["id"]: q["soru_turu"] for q in items}
    else:
        types = json.loads((config.ROOT / "eval" / f"soru_turleri_{set_name.removeprefix('sorular_')}.json")
                           .read_text(encoding="utf-8"))["soru_turu"]
    for q in items:
        if types[q["id"]] == "coklu_belge" and len({k["belge"] for k in q.get("kaynaklar", [])}) == 1:
            types[q["id"]] = "coklu_madde"
    return types


def main(exp_id):
    exp = config.load_experiment(exp_id)
    set_name = dataset_name(exp)
    items = json.loads((config.ROOT / "eval" / f"{set_name}.json").read_text(encoding="utf-8"))["sorular"]
    types = question_types(set_name, items)
    verdicts = json.loads((config.EXPERIMENTS_DIR / "anlamca" / f"{exp_id}.json").read_text(encoding="utf-8"))["kararlar"]
    rows = []
    for key, name in [*TURLER.items(), (None, "**Toplam**")]:
        ids = [q["id"] for q in items if key is None or types[q["id"]] == key]
        if not ids:
            rows.append(f"| {name} | 0 | – | – |")
            continue
        kw = sum(verdicts[i]["anahtar"] for i in ids)
        sem = sum(verdicts[i]["anlamca"] for i in ids)
        rows.append(f"| {name} | {len(ids)} | {kw}/{len(ids)} ({kw / len(ids):.2f}) | {sem}/{len(ids)} ({sem / len(ids):.2f}) |")
    print(f"{exp_id} ({set_name})\n")
    print("| Soru türü | n | Anahtar kelime | Anlamca |\n|---|---|---|---|")
    print("\n".join(rows))
    wrong = [(i, v.get("gerekce", "")) for i, v in verdicts.items() if not v["anlamca"]]
    if wrong:
        print("\nAnlamca yanlış:")
        for i, why in wrong:
            print(f"- [{TURLER[types[i]]}] {next(q['soru'] for q in items if q['id'] == i)} — {why}")


if __name__ == "__main__":
    main(sys.argv[1])
