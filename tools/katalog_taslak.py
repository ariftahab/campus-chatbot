"""Belge kataloğu taslağı (LLM yok): corpus v4'teki her PDF için data/belge_katalogu_v1.json kaydı üretir.

  python tools/katalog_taslak.py [--uzerine-yaz]

Kaynaklar:
- baslik: config.DOCUMENTS, yoksa data/belge_basliklari_v1.json (PDF ilk sayfasındaki resmî ad).
- kapsam, haric: data/belge_kapsam_v1.json'dan aynen.
- tur: başlıktaki belge türü sözcüğünden (Yönetmeliği, Yönergesi, Usul ve Esasları, Akademik Takvim).
- tarih, tarih_kaynagi: ilk sayfanın üst satırlarındaki Resmî Gazete / Senato kararı tarihi; belge içinde daha yeni
  bir değişiklik notu ("(Değişik:RG-16/9/2024-...)", "(Değişik: Senato Kararı 07.09.2023-...)") varsa onun tarihi.
- ekler: madde numarası belgede ikinci kez 1'den başlıyorsa o satırın sayfası.
Okunamayan alan null kalır, tahmin edilmez; sondaki rapor kullanıcının PDF'e bakıp dolduracağı belgeleri listeler.
Kullanıcının doğruladığı kayıtlar kaybolmasın diye var olan katalog --uzerine-yaz olmadan değiştirilmez.
"""
import difflib
import json
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

import pdfplumber

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
from ingest import ARTICLE_RE_V2, PAGE_FOOTER_RE  # noqa: E402

CORPUS = "v4"
OUT = config.DATA_DIR / "belge_katalogu_v1.json"
SCOPE_FILE = config.DATA_DIR / "belge_kapsam_v1.json"
TITLE_FILE = config.DATA_DIR / "belge_basliklari_v1.json"
HEADER_LINES = 12  # tarih satırı ilk sayfanın üst kısmında

MONTHS = {"ocak": 1, "şubat": 2, "mart": 3, "nisan": 4, "mayıs": 5, "haziran": 6, "temmuz": 7, "ağustos": 8,
          "eylül": 9, "ekim": 10, "kasım": 11, "aralık": 12}
# "29 Ocak 2024 PAZARTESİ Resmî Gazete Sayı : 32444"
RG_LONG_RE = re.compile(r"^(\d{1,2})\s+(\w+)\s+(\d{4})\s+\w+\s+Resm[iî]\s+Gazete", re.IGNORECASE)
NUM_DATE = r"(\d{1,2})\s*[./]\s*(\d{1,2})\s*[./]\s*(\d{4})"
# "Resmî Gazete Tarihi: 23.01.2017"
RG_SHORT_RE = re.compile(r"Resm[iî]\s+Gazete\s+Tarihi\s*:\s*" + NUM_DATE, re.IGNORECASE)
# "Senato Karar Tarihi: 09.11.2023", "KARAR TARİHİ : 08.05.2009", "B.A.İ.B.Ü 28/03/2019 tarihli ve ... Senato Kararı"
SENATE_RE = re.compile(r"(?:senato|karar).*?" + NUM_DATE + r"|" + NUM_DATE + r".*?senato", re.IGNORECASE)
# "(Değişik:RG-22/6/2018-30456)", "(Değişik ibare:RG-16/9/2024-32664)", "(Değişik, Senato: 05.09.2025–2025/137)",
# "(Değişik: 25.02.2026-2026/25)" (kaynak yazmıyor). Kaynak, parantez içinde tarihten önce yazanla belirlenir.
AMEND_RE = re.compile(r"\((?:Değişik|Ek|Mülga|İptal)([^)]*?)" + NUM_DATE)

# Başlıkta aranan tür sözcükleri (küçük harfe çevrilmiş başlıkta). Türkçede belgenin türü başlığın sonundaki addır
# ("... Usul ve Esaslara İlişkin Yönerge" bir yönergedir): en sonda geçen sözcük seçilir; hiçbiri yoksa tür null.
TYPE_WORDS = {"yonetmelik": ("yönetmeliği", "yönetmelik"), "yonerge": ("yönergesi", "yönerge"),
              "usul_esas": ("usul ve esas",), "takvim": ("akademik takvim",)}


def tr_lower(text):
    return text.replace("İ", "i").replace("I", "ı").lower()


def iso(day, month, year):
    try:
        return date(int(year), int(month), int(day)).isoformat()
    except ValueError:
        return None


def read_lines(pdf):
    """(sayfa_no, satır) listesi; sayfa altlığı ("Sayfa: 1 / 5") atlanır."""
    return [(no, line.strip()) for no, page in enumerate(pdf.pages, start=1)
            for line in (page.extract_text() or "").splitlines()
            if line.strip() and not PAGE_FOOTER_RE.match(line.strip())]


def header_date(lines):
    """İlk sayfanın üst satırlarındaki kabul/yayım tarihi: (tarih, kaynak) ya da (None, None)."""
    for _, line in [l for l in lines if l[0] == 1][:HEADER_LINES]:
        if m := RG_LONG_RE.match(line):
            month = MONTHS.get(tr_lower(m.group(2)))
            if month and (d := iso(m.group(1), month, m.group(3))):
                return d, "Resmî Gazete"
        if m := RG_SHORT_RE.search(line):
            if d := iso(*m.groups()):
                return d, "Resmî Gazete"
        if m := SENATE_RE.search(line):
            parts = m.groups()[:3] if m.group(1) else m.groups()[3:]
            if d := iso(*parts):
                return d, "Senato"
    return None, None


def last_amendment(lines):
    """Belge içindeki en yeni değişiklik notu: (tarih, kaynak) ya da (None, None). Kaynağı yazmayan not (ör. kanun
    değişikliği "(Değişik:2/2/2023-7437/2 md.)") kaynak None ile döner."""
    best = (None, None)
    for _, line in lines:
        for m in AMEND_RE.finditer(line):
            d = iso(*m.groups()[1:])
            source = "Resmî Gazete" if "RG" in m.group(1) else "Senato" if "Senato" in m.group(1) else None
            if d and (best[0] is None or d > best[0]):
                best = (d, source)
    return best


def doc_type(title):
    low = tr_lower(title)
    positions = {t: max(low.rfind(w) for w in words) for t, words in TYPE_WORDS.items()}
    best = max(positions, key=positions.get)
    return best if positions[best] >= 0 else None


def annex_pages(lines):
    """Madde numarası 1'in ikinci (ve sonraki) kez geçtiği sayfalar: belgeye eklenmiş, kendi numaralı metni."""
    pages, seen_first = [], False
    for page_no, line in lines:
        m = ARTICLE_RE_V2.match(line)
        if m and (m.group(1) or m.group(2)) == "1":
            if seen_first:
                pages.append(page_no)
            seen_first = True
    return pages


def build():
    scopes = json.loads(SCOPE_FILE.read_text(encoding="utf-8"))["belgeler"]
    titles = json.loads(TITLE_FILE.read_text(encoding="utf-8"))["basliklar"]
    records, report = {}, defaultdict(list)
    for path in config.corpus_paths(CORPUS):
        name = path.name
        with pdfplumber.open(path) as pdf:
            lines = read_lines(pdf)
        title = config.DOCUMENTS.get(name, {}).get("title") or titles.get(name)
        accepted, accepted_src = header_date(lines)
        amended, amended_src = last_amendment(lines)
        tarih, kaynak = accepted, accepted_src
        if amended and (accepted is None or amended > accepted):
            tarih, kaynak = amended, amended_src
            report["tarih değişiklik notundan"].append(f"{name}: kabul {accepted}, son değişiklik {amended}"
                                                       f" ({amended_src or 'kaynak yazmıyor'})")
        scope = scopes.get(name)
        records[name] = {
            "baslik": title,
            "tur": doc_type(title) if title else None,
            "kapsam": scope["kapsam"] if scope else None,
            "haric": scope["haric"] if scope else [],
            "yururluk": "yururlukte",
            "tarih": tarih,
            "tarih_kaynagi": kaynak,
            "ust_norm": None,
            "ekler": [{"ad": None, "baslangic_sayfasi": p} for p in annex_pages(lines)],
            "notlar": "",
            "dogrulandi": False,
        }
        rec = records[name]
        if not title:
            report["başlığı yok"].append(name)
        if not scope:
            report["kapsam etiketi yok"].append(name)
        if tarih is None:
            report["tarihi okunamadı"].append(name)
        elif kaynak is None:
            report["tarih kaynağı belirsiz"].append(f"{name}: {tarih}")
        if rec["tur"] is None:
            report["türü belirlenemedi"].append(f"{name}: {title}")
        if rec["ekler"]:
            report["ek tespit edildi"].append(f"{name}: sayfa {[e['baslangic_sayfasi'] for e in rec['ekler']]}")
    # Aynı kapsamda aynı türden birden fazla belge; başlıkları birbirine çok benzeyenler ayrıca işaretlenir.
    groups = defaultdict(list)
    for name, rec in records.items():
        if rec["kapsam"] and rec["tur"]:
            groups[(rec["kapsam"], rec["tur"])].append(name)
    for (kapsam, tur), names in sorted(groups.items()):
        if len(names) > 1:
            report["aynı kapsam ve tür"].append(f"{kapsam} / {tur}: {len(names)} belge")
            for i, a in enumerate(names):
                for b in names[i + 1:]:
                    ratio = difflib.SequenceMatcher(None, records[a]["baslik"], records[b]["baslik"]).ratio()
                    if ratio >= 0.75:
                        report["benzer başlık (olası kopya/sürüm)"].append(f"{a} <-> {b} ({ratio:.2f})")
    return records, report


def main(overwrite):
    if OUT.exists() and not overwrite:
        raise SystemExit(f"{OUT.name} zaten var (doğrulanmış kayıtlar olabilir); üzerine yazmak için --uzerine-yaz")
    records, report = build()
    catalog = {
        "surum": "1",
        "aciklama": f"Belge kataloğu (corpus {CORPUS}). Taslak tools/katalog_taslak.py ile PDF'lerden üretildi "
                    "(LLM yok); okunamayan alanlar null. Kullanıcı kaydı kontrol edince dogrulandi=true. kapsam/haric "
                    "belge_kapsam_v1.json'dan aynen. Bu dosya pipeline'da kullanılmıyor; her kullanım ayrı deney.",
        "belgeler": records,
    }
    OUT.write_text(json.dumps(catalog, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{OUT.name}: {len(records)} belge yazıldı\n")
    for title, items in report.items():
        print(f"## {title} ({len(items)})")
        for item in items:
            print(f"  - {item}")
        print()


if __name__ == "__main__":
    main("--uzerine-yaz" in sys.argv[1:])
