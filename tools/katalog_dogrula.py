"""Belge kataloğunu (data/belge_katalogu_v1.json) denetler; hata varsa listeler ve 1 ile çıkar.

  python tools/katalog_dogrula.py

Denetimler: corpus v4'ün her PDF'i katalogda ve katalogda corpus dışı belge yok; her kayıtta şemadaki alanlar var;
değerler şemadaki kümede; kapsam/haric belge_kapsam_v1.json ile aynı; ust_norm corpus'taki başka bir belge;
doğrulanmış (dogrulandi=true) kayıtta baslik ve tur boş değil.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402

CATALOG = config.DATA_DIR / "belge_katalogu_v1.json"
SCOPE_FILE = config.DATA_DIR / "belge_kapsam_v1.json"
CORPUS = "v4"

FIELDS = {"baslik", "tur", "kapsam", "haric", "yururluk", "tarih", "tarih_kaynagi", "ust_norm", "ekler", "notlar",
          "dogrulandi"}
TYPES = {"yonetmelik", "yonerge", "usul_esas", "takvim", "diger"}
STATUSES = {"yururlukte", "kaldirildi", "belirsiz"}
DATE_SOURCES = {"Resmî Gazete", "Senato"}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def check_record(name, rec, scopes, corpus):
    errors = []
    if set(rec) != FIELDS:
        errors.append(f"alanlar şemayla aynı değil (eksik {sorted(FIELDS - set(rec))}, fazla {sorted(set(rec) - FIELDS)})")
        return errors
    if rec["tur"] is not None and rec["tur"] not in TYPES:
        errors.append(f"tur geçersiz: {rec['tur']}")
    if rec["yururluk"] not in STATUSES:
        errors.append(f"yururluk geçersiz: {rec['yururluk']}")
    if rec["tarih"] is not None and not DATE_RE.match(rec["tarih"]):
        errors.append(f"tarih YYYY-MM-DD değil: {rec['tarih']}")
    if rec["tarih_kaynagi"] is not None and rec["tarih_kaynagi"] not in DATE_SOURCES:
        errors.append(f"tarih_kaynagi geçersiz: {rec['tarih_kaynagi']}")
    if rec["tarih"] is None and rec["tarih_kaynagi"] is not None:
        errors.append("tarih yok ama tarih_kaynagi var")
    scope = scopes.get(name, {})
    if rec["kapsam"] != scope.get("kapsam") or rec["haric"] != scope.get("haric", []):
        errors.append("kapsam/haric belge_kapsam_v1.json ile aynı değil")
    if rec["ust_norm"] is not None and (rec["ust_norm"] not in corpus or rec["ust_norm"] == name):
        errors.append(f"ust_norm corpus'taki başka bir belge değil: {rec['ust_norm']}")
    for ek in rec["ekler"] if isinstance(rec["ekler"], list) else [None]:
        if (not isinstance(ek, dict) or set(ek) != {"ad", "baslangic_sayfasi"}
                or not (ek["ad"] is None or isinstance(ek["ad"], str))
                or not isinstance(ek["baslangic_sayfasi"], int) or ek["baslangic_sayfasi"] < 1):
            errors.append(f"ekler kaydı geçersiz: {ek}")
    if not isinstance(rec["notlar"], str):
        errors.append("notlar metin değil")
    if not isinstance(rec["dogrulandi"], bool):
        errors.append("dogrulandi true/false değil")
    elif rec["dogrulandi"] and (not rec["baslik"] or rec["tur"] is None):
        errors.append("doğrulanmış kayıtta baslik ya da tur boş")
    return errors


def validate(catalog):
    scopes = json.loads(SCOPE_FILE.read_text(encoding="utf-8"))["belgeler"]
    corpus = {p.name for p in config.corpus_paths(CORPUS)}
    docs = catalog.get("belgeler", {})
    errors = [f"katalogda yok: {n}" for n in sorted(corpus - set(docs))]
    errors += [f"corpus {CORPUS}'te yok: {n}" for n in sorted(set(docs) - corpus)]
    for name, rec in docs.items():
        errors += [f"{name}: {e}" for e in check_record(name, rec, scopes, corpus)]
    return errors


def main():
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    errors = validate(catalog)
    docs = catalog["belgeler"]
    verified = sum(r.get("dogrulandi") is True for r in docs.values())
    for e in errors:
        print(f"HATA {e}")
    print(f"{len(docs)} belge, {verified} doğrulanmış, {len(errors)} hata")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
