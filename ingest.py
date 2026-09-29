"""PDF'leri okur, parçalara böler, FAISS indeksini ve BM25 için parça listesini diske kaydeder.

Kullanım: python ingest.py
Chat ve eval, indeks yoksa ya da PDF'ler değiştiyse bunu otomatik çağırır.
"""
import hashlib
import json
import re
from pathlib import Path

import pdfplumber
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

import config

MANIFEST_FILE = config.INDEX_DIR / "manifest.json"
CHUNKS_FILE = config.INDEX_DIR / "chunks.json"

ARTICLE_RE = re.compile(r"^(?:MADDE|Madde)\s*(\d+)\s*[-–]")
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


def _is_title_line(line):
    """Madde başlığı mı? ("Amaç", "Kayıt dondurma" gibi kısa ve cümle sonu olmayan satır)"""
    return len(line) <= 100 and not line.endswith((".", ",", ";", ":")) and not ARTICLE_RE.match(line)


def parse_regulation(path, title):
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
        if ARTICLE_RE.match(line):
            has_title = i > 0 and (i - 1) not in skip and _is_title_line(lines[i - 1][1])
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
        article_line = next(l for l in body if ARTICLE_RE.match(l))
        docs.append(Document(
            page_content="\n".join(body),
            metadata={
                "source": path.name,
                "title": title,
                "kind": "mevzuat",
                "page": a["page"],
                "madde": int(ARTICLE_RE.match(article_line).group(1)),
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


def split_long(docs):
    """MAX_CHUNK_CHARS'ı aşan maddeleri fıkra sınırlarından böler, her parçaya başlık ekler."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.MAX_CHUNK_CHARS,
        chunk_overlap=config.CHUNK_OVERLAP,
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
        if len(doc.page_content) <= config.MAX_CHUNK_CHARS:
            out.append(Document(page_content=f"{label}\n{doc.page_content}", metadata=m))
            continue
        for part_no, part in enumerate(splitter.split_text(doc.page_content), start=1):
            prefix = label if part_no == 1 else f"{label} [devam]"
            out.append(Document(page_content=f"{prefix}\n{part.strip()}", metadata={**m, "part": part_no}))
    return out


def load_documents():
    docs = []
    for path in sorted(config.DATA_DIR.glob("*.pdf")):
        title, kind = _doc_info(path)
        if kind is None:
            with pdfplumber.open(path) as pdf:
                kind = "mevzuat" if any(ARTICLE_RE.match(l) for _, l in _read_lines(pdf)) else "genel"
        if kind == "takvim":
            docs.extend(parse_calendar(path, title))
        elif kind == "mevzuat":
            docs.extend(parse_regulation(path, title))
        else:
            with pdfplumber.open(path) as pdf:
                for page_no, page in enumerate(pdf.pages, start=1):
                    docs.append(Document(page_content=page.extract_text() or "",
                                         metadata={"source": path.name, "title": title,
                                                   "kind": "genel", "page": page_no}))
    chunks = split_long(docs)
    for i, chunk in enumerate(chunks):
        chunk.metadata["chunk_id"] = i  # FAISS ve BM25 sonuçlarını eşleştirmek için
    return chunks


# --- İndeks ---

def get_embeddings():
    return HuggingFaceEmbeddings(
        model_name=config.EMBEDDING_MODEL,
        encode_kwargs={"normalize_embeddings": True},
    )


def _fingerprint():
    """PDF'lerin ve parçalamayı etkileyen ayarların özeti; değişirse indeks yeniden kurulur."""
    h = hashlib.sha256()
    for path in sorted(config.DATA_DIR.glob("*.pdf")):
        h.update(path.name.encode())
        h.update(path.read_bytes())
    settings = [config.EMBEDDING_MODEL, config.MAX_CHUNK_CHARS, config.CHUNK_OVERLAP, config.DOCUMENTS]
    h.update(json.dumps(settings, sort_keys=True, ensure_ascii=False).encode())
    h.update(Path(__file__).read_bytes())  # parçalama kodu değişirse de yeniden kur
    return h.hexdigest()


def index_is_current():
    if not (MANIFEST_FILE.exists() and CHUNKS_FILE.exists()):
        return False
    manifest = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    return manifest.get("fingerprint") == _fingerprint()


def build_index(embeddings=None):
    print("PDF'ler okunuyor ve parçalanıyor...")
    chunks = load_documents()
    if not chunks:
        raise SystemExit(f"Hata: '{config.DATA_DIR}' klasöründe PDF bulunamadı.")
    print(f"{len(chunks)} parça oluşturuldu. Embedding'ler hesaplanıyor ({config.EMBEDDING_MODEL})...")
    embeddings = embeddings or get_embeddings()
    store = FAISS.from_documents(chunks, embeddings)
    config.INDEX_DIR.mkdir(exist_ok=True)
    store.save_local(str(config.INDEX_DIR))
    CHUNKS_FILE.write_text(
        json.dumps([{"page_content": c.page_content, "metadata": c.metadata} for c in chunks],
                   ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    MANIFEST_FILE.write_text(json.dumps({"fingerprint": _fingerprint(), "chunks": len(chunks)}), encoding="utf-8")
    print(f"İndeks kaydedildi: {config.INDEX_DIR}")
    return store, chunks


def load_index():
    """Kayıtlı indeksi yükler; yoksa veya eskiyse yeniden kurar."""
    embeddings = get_embeddings()
    if not index_is_current():
        print("İndeks yok ya da PDF'ler/ayarlar değişmiş, yeniden kuruluyor.")
        return build_index(embeddings)
    store = FAISS.load_local(str(config.INDEX_DIR), embeddings, allow_dangerous_deserialization=True)
    raw = json.loads(CHUNKS_FILE.read_text(encoding="utf-8"))
    chunks = [Document(page_content=c["page_content"], metadata=c["metadata"]) for c in raw]
    return store, chunks


if __name__ == "__main__":
    build_index()
