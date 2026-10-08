"""PDF'leri okur, parçalara böler, FAISS indeksini ve BM25 için parça listesini diske kaydeder.

Kullanım: python ingest.py [EXP-ID]   (varsayılan: config.PRODUCTION_EXPERIMENT)
Sohbet ve deney betikleri, indeks yoksa bunu otomatik çağırır.
"""
import bisect
import hashlib
import json
import re
import time
from datetime import datetime
from pathlib import Path

import pdfplumber
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

import config

ARTICLE_RE = re.compile(r"^(?:MADDE|Madde)\s*(\d+)\s*[-–]")
# structural_v2: yeni eklenen belgelerdeki madde biçimleri de tanınır:
#   "Madde 4.", "Madde 1:", "Madde–1:", "MADDE 7 (Değişik...)", "MADDE 17 − (1)" (Unicode eksi),
#   "MADDE 17/A-" (ek madde), "MADDE1 2-" (PDF'te dipnot rakamı yapışmış), satırda tek başına "Madde 16",
#   "Amaç Madde 1." (başlık aynı satırda; yalnız satır "Madde N." ile bitiyorsa).
# Cümle içi atıflar ("Madde 5'te belirtilen", "Madde 12 kapsamında") bilerek eşleşmez.
ARTICLE_RE_V2 = re.compile(
    r"^(?:MADDE|Madde)\s*[-–—−]?\s*(?:\d\s+)?(\d+(?:/[A-Z])?)\s*(?:[-–—−.:]|\(|$)"
    r"|^[A-ZÇĞİÖŞÜ][a-zçğıöşü]+(?:\s+[A-Za-zÇĞİÖŞÜçğıöşü]+){0,3}\s+(?:MADDE|Madde)\s*(\d+)\s*[.:]?\s*$")
# chunking değeri -> madde başlangıcı deseni (structural_v3 = v2 deseni + iyileştirilmiş fallback)
ARTICLE_PATTERNS = {"structural": ARTICLE_RE, "structural_v2": ARTICLE_RE_V2, "structural_v3": ARTICLE_RE_V2}
SECTION_RE = re.compile(r"^\S+\s+BÖLÜM$")
TERM_HEADINGS = {"GÜZ YARIYILI", "BAHAR YARIYILI", "YAZ ÖĞRETİMİ"}
PAGE_FOOTER_RE = re.compile(r"^Sayfa:\s*\d+\s*/\s*\d+$")


# --- Belge okuma ---

def _doc_info(path):
    info = config.DOCUMENTS.get(path.name, {})
    return info.get("title", path.stem), info.get("tur")


def _read_lines(pdf):
    """Tüm sayfaların satırlarını (sayfa_no, satır) olarak döndürür."""
    lines = []
    for page_no, page in enumerate(pdf.pages, start=1):
        for line in (page.extract_text() or "").splitlines():
            line = line.strip()
            if line and not PAGE_FOOTER_RE.match(line):
                lines.append((page_no, line))
    return lines


def _is_title_line(line, article_re=ARTICLE_RE):
    """Madde başlığı mı? ("Amaç", "Kayıt dondurma" gibi kısa ve cümle sonu olmayan satır)"""
    return len(line) <= 100 and not line.endswith((".", ",", ";", ":")) and not article_re.match(line)


def parse_regulation(path, title, article_re=ARTICLE_RE):
    """Yönetmelik/yönergeyi madde madde Document listesine çevirir."""
    with pdfplumber.open(path) as pdf:
        lines = _read_lines(pdf)

    # Önce bölüm başlıklarını ayıkla: "İKİNCİ BÖLÜM" + bir sonraki satır (bölüm adı).
    section_at = {}  # satır indeksi -> bölüm adı
    skip = set()
    for i, (_, line) in enumerate(lines):
        if SECTION_RE.match(line) and i + 1 < len(lines):
            section_at[i] = f"{line} - {lines[i + 1][1]}"
            skip.update({i, i + 1})

    # Madde başlangıçları: üstünde başlık satırı varsa madde oradan başlar.
    starts = set()
    for i, (_, line) in enumerate(lines):
        if article_re.match(line):
            has_title = i > 0 and (i - 1) not in skip and _is_title_line(lines[i - 1][1], article_re)
            starts.add(i - 1 if has_title else i)

    articles, current, section = [], None, ""
    for i, (page, line) in enumerate(lines):
        if i in section_at:
            section = section_at[i]
        if i in skip:
            continue
        if i in starts:
            current = {"page": page, "section": section, "lines": []}
            articles.append(current)
        if current:  # ilk maddeden önceki belge başlığı atlanır
            current["lines"].append(line)

    docs = []
    for a in articles:
        body = a["lines"]
        article_line = next(l for l in body if article_re.match(l))
        number = next(g for g in article_re.match(article_line).groups() if g)
        docs.append(Document(
            page_content="\n".join(body),
            metadata={
                "source": path.name,
                "title": title,
                "kind": "mevzuat",
                "page": a["page"],
                "madde": int(number) if number.isdigit() else number,  # ek madde: "17/A"
                "heading": body[0] if body[0] != article_line else "",
                "section": a["section"],
            },
        ))
    return docs


def parse_calendar(path, title):
    """Akademik takvimi tablo tablo okur; her tablo (ör. Bahar Yarıyılı) bir parça olur."""
    docs = []
    with pdfplumber.open(path) as pdf:
        pages = pdf.pages
        # Kapsam notu, ör. "(Tıp Fakültesi, ... Hariç)" - PDF'te iki satıra bölünmüş olabilir.
        first_page = " ".join((pages[0].extract_text() or "").split())
        scope = re.search(r"\([^)]*\)", first_page)
        scope = scope.group(0) if scope else ""
        footnotes = []
        for page in pages:
            for line in (page.extract_text() or "").splitlines():
                if line.startswith("*"):
                    footnotes.append(line.strip())

        group = "EĞİTİM-ÖĞRETİM"
        for page_no, page in enumerate(pages, start=1):
            prev_bottom = 0
            for table in page.find_tables():
                above = page.crop((0, prev_bottom, page.width, table.bbox[1])).extract_text() or ""
                prev_bottom = table.bbox[3]
                term = ""
                for line in above.splitlines():
                    line = line.strip()
                    if line in TERM_HEADINGS:
                        term = line
                    elif line.endswith(("İŞLEMLER", "İŞLEMLERİ")):
                        group = line
                rows, last_date = [], ""
                for row in table.extract():
                    date, event = (row + [None, None])[:2]
                    date = (date or last_date or "").replace("\n", " ").strip()
                    event = (event or "").replace("\n", " ").strip()
                    if event:
                        rows.append(f"- {date}: {event}")
                        last_date = date
                name = f"{group} - {term}" if term else group
                text = f"{title} {scope}\n{name}\n" + "\n".join(rows)
                if any("*" in r for r in rows):
                    text += "\n" + "\n".join(footnotes)
                docs.append(Document(
                    page_content=text,
                    metadata={"source": path.name, "title": title, "kind": "takvim",
                              "page": page_no, "section": name},
                ))
    return docs


def split_structural(docs, cfg):
    """chunk_size'ı aşan maddeleri fıkra sınırlarından böler, her parçaya başlık ekler."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=cfg.chunk_size,
        chunk_overlap=cfg.chunk_overlap,
        separators=["\n(", "\n", ". ", " "],
        keep_separator="start",
    )
    out = []
    for doc in docs:
        m = doc.metadata
        if m["kind"] == "takvim":  # takvim tabloları zaten başlıklı ve yarıyıl bütünlüğü korunmalı
            out.append(doc)
            continue
        label = m["title"]
        if "madde" in m:
            label += f" - Madde {m['madde']}" + (f" ({m['heading']})" if m["heading"] else "")
        if len(doc.page_content) <= cfg.chunk_size:
            out.append(Document(page_content=f"{label}\n{doc.page_content}", metadata=m))
            continue
        for part_no, part in enumerate(splitter.split_text(doc.page_content), start=1):
            prefix = label if part_no == 1 else f"{label} [devam]"
            out.append(Document(page_content=f"{prefix}\n{part.strip()}", metadata={**m, "part": part_no}))
    return out


def parse_general(path, title, cfg):
    """Madde yapısı olmayan belge (structural_v3 fallback'i).

    Eski fallback her sayfayı ayrı bölüyordu: sayfa sonunda yarım kalan cümle iki chunk'a ayrılıyor,
    kısa sayfalar (ör. son sayfadaki iki satır) tek başına chunk oluyordu. Burada belge önce tek metin
    olarak birleştirilir, sonra paragraf/satır/cümle sınırlarından bölünür; her chunk'ın sayfası
    başladığı karakterin hangi sayfaya düştüğüne göre bulunur.
    """
    pages = read_pages(path, "pdfplumber")
    starts, text = [], ""
    for page_text in pages:
        starts.append(len(text))
        text += page_text.strip() + "\n"
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=cfg.chunk_size, chunk_overlap=cfg.chunk_overlap,
        separators=["\n\n", "\n", ". ", " "], keep_separator="start", add_start_index=True,
    )
    docs = []
    for part_no, d in enumerate(splitter.create_documents([text]), start=1):
        page = bisect.bisect_right(starts, d.metadata["start_index"])  # 1'den başlar
        docs.append(Document(page_content=d.page_content.strip(), metadata={
            "source": path.name, "title": title, "kind": "genel", "page": page, "part": part_no}))
    return docs


def read_pages(path, parser):
    """Her sayfanın ham metnini döndürür. pypdf yolu ilk prototipteki PyPDFLoader'ın aynısıdır."""
    if parser == "pypdf":
        from langchain_community.document_loaders import PyPDFLoader
        return [d.page_content for d in PyPDFLoader(str(path)).load()]
    if parser == "pdfplumber":
        with pdfplumber.open(path) as pdf:
            return [page.extract_text() or "" for page in pdf.pages]
    raise ValueError(f"Bilinmeyen pdf_parser: {parser}")


def load_recursive(cfg):
    """Sabit boyutlu parçalama (ilk prototipin yöntemi): sayfa metinleri karakter sayısına göre bölünür."""
    splitter = RecursiveCharacterTextSplitter(chunk_size=cfg.chunk_size, chunk_overlap=cfg.chunk_overlap)
    pages = []
    for path in config.corpus_paths(cfg.corpus):
        title, _ = _doc_info(path)
        for page_no, text in enumerate(read_pages(path, cfg.pdf_parser), start=1):
            pages.append(Document(page_content=text, metadata={
                "source": path.name, "title": title, "kind": "sayfa", "page": page_no}))
    return splitter.split_documents(pages)


def load_structural(cfg):
    article_re = ARTICLE_PATTERNS[cfg.chunking]
    docs = []
    for path in config.corpus_paths(cfg.corpus):
        title, kind = _doc_info(path)
        if kind is None:
            with pdfplumber.open(path) as pdf:
                kind = "mevzuat" if any(article_re.match(l) for _, l in _read_lines(pdf)) else "genel"
        if kind == "takvim":
            docs.extend(parse_calendar(path, title))
        elif kind == "mevzuat":
            docs.extend(parse_regulation(path, title, article_re))
        elif cfg.chunking == "structural_v3":
            docs.extend(parse_general(path, title, cfg))
        else:
            for page_no, text in enumerate(read_pages(path, "pdfplumber"), start=1):
                docs.append(Document(page_content=text, metadata={
                    "source": path.name, "title": title, "kind": "genel", "page": page_no}))
    return split_structural(docs, cfg)


def load_documents(cfg):
    if cfg.chunking == "recursive":
        chunks = load_recursive(cfg)
    elif cfg.chunking in ARTICLE_PATTERNS:
        chunks = load_structural(cfg)
    else:
        raise ValueError(f"Bilinmeyen chunking: {cfg.chunking}")
    for i, chunk in enumerate(chunks):
        chunk.metadata["chunk_id"] = i  # FAISS ve BM25 sonuçlarını eşleştirmek için
    return chunks


# --- İndeks ---
# Her yapılandırmanın indeksi vectorstore/<parmak izi>/ altında ayrı tutulur; deneyler arasında
# geçiş yaparken indeksler birbirini ezmez.

def get_embeddings(cfg):
    return HuggingFaceEmbeddings(
        model_name=cfg.embedding_model,
        model_kwargs={"device": cfg.device},
        encode_kwargs={"normalize_embeddings": cfg.normalize_embeddings},
    )


def fingerprint(cfg):
    """Belge kümesindeki PDF içerikleri + indeks parametreleri + belge ayarları + bu dosyanın kaynak kodu."""
    h = hashlib.sha256()
    paths = config.corpus_paths(cfg.corpus)
    for path in paths:
        h.update(path.name.encode())
        h.update(path.read_bytes())
    # Yalnız bu küme içindeki belgelerin başlık/tür ayarları: DOCUMENTS'a başka bir kümenin belgesi
    # eklenince bu kümenin indeksi gereksiz yere yeniden kurulmasın.
    documents = {p.name: config.DOCUMENTS[p.name] for p in paths if p.name in config.DOCUMENTS}
    settings = [cfg.index_params(), documents]
    h.update(json.dumps(settings, sort_keys=True, ensure_ascii=False).encode())
    # Satır sonları normalize edilir: git'in CRLF/LF dönüşümü aynı kod için farklı parmak izi üretmesin.
    h.update(Path(__file__).read_bytes().replace(b"\r\n", b"\n"))
    return h.hexdigest()[:16]


def index_dir(cfg):
    return config.INDEX_ROOT / fingerprint(cfg)


def build_index(cfg, embeddings=None):
    out = index_dir(cfg)
    print(f"PDF'ler okunuyor ve parçalanıyor ({cfg.pdf_parser}, {cfg.chunking})...")
    started = time.perf_counter()
    chunks = load_documents(cfg)
    if not chunks:
        raise SystemExit(f"Hata: '{cfg.corpus}' belge kümesinde PDF bulunamadı.")
    print(f"{len(chunks)} parça oluşturuldu. Embedding'ler hesaplanıyor ({cfg.embedding_model})...")
    embeddings = embeddings or get_embeddings(cfg)
    store = FAISS.from_documents(chunks, embeddings)
    build_seconds = time.perf_counter() - started

    out.mkdir(parents=True, exist_ok=True)
    store.save_local(str(out))
    (out / "chunks.json").write_text(
        json.dumps([{"page_content": c.page_content, "metadata": c.metadata} for c in chunks],
                   ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    manifest = {
        "fingerprint": fingerprint(cfg),
        "index_params": cfg.index_params(),
        "chunks": len(chunks),
        "avg_chunk_chars": round(sum(len(c.page_content) for c in chunks) / len(chunks), 1),
        "build_seconds": round(build_seconds, 1),
        "created": datetime.now().isoformat(timespec="seconds"),
    }
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"İndeks kaydedildi: {out}")
    return store, chunks, manifest


def load_index(cfg):
    """Yapılandırmanın indeksini yükler; yoksa kurar. (store, chunks, manifest) döndürür."""
    embeddings = get_embeddings(cfg)
    out = index_dir(cfg)
    if not (out / "manifest.json").exists():
        print("Bu yapılandırma için indeks yok (ya da PDF'ler/kod değişmiş), kuruluyor.")
        return build_index(cfg, embeddings)
    store = FAISS.load_local(str(out), embeddings, allow_dangerous_deserialization=True)
    raw = json.loads((out / "chunks.json").read_text(encoding="utf-8"))
    chunks = [Document(page_content=c["page_content"], metadata=c["metadata"]) for c in raw]
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    return store, chunks, manifest


if __name__ == "__main__":
    import sys
    exp_id = sys.argv[1] if len(sys.argv) > 1 else config.PRODUCTION_EXPERIMENT
    print(f"Yapılandırma: {exp_id}")
    build_index(config.RagConfig.from_dict(config.load_experiment(exp_id)["params"]))
