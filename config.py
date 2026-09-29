"""Projenin tüm ayarları tek yerde. Değiştirdikten sonra `python ingest.py` ile indeksi yeniden kur."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
INDEX_DIR = ROOT / "vectorstore"
EVAL_FILE = ROOT / "eval" / "sorular.json"

# Belge adları kaynak gösteriminde ve parçaların başlığında kullanılır.
# Listede olmayan bir PDF eklenirse dosya adı başlık olarak kullanılır.
# tur: "takvim" -> tablo satırları okunur, "mevzuat" -> madde madde bölünür.
DOCUMENTS = {
    "akademik-takvim.pdf": {"title": "BAİBÜ 2025-2026 Akademik Takvimi", "tur": "takvim"},
    "ogrenci-kayıt-yonerge.pdf": {"title": "BAİBÜ Öğrenci Kayıt Kabul İşleri Yönetmeliği", "tur": "mevzuat"},
    "yatay-gecis-yonergesi.pdf": {"title": "BAİBÜ Yatay Geçiş Yönergesi", "tur": "mevzuat"},
}

# Embedding: bge-m3 çok dilli, Türkçe'de iyi ve 8192 token okuyabiliyor.
EMBEDDING_MODEL = "BAAI/bge-m3"
# Reranker: soruyla her adayı birlikte okuyup yeniden sıralar. None yapılırsa kapanır
# (CPU'da sorgu başına ~4-5 saniye). eval'de doğru parçayı 1. sıraya koyma 25/27 -> 27/27.
RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"
RERANKER_MAX_LENGTH = 512

# Uzun maddeler bu boyutu aşarsa fıkra sınırlarından bölünür (karakter).
MAX_CHUNK_CHARS = 1500
CHUNK_OVERLAP = 150

# Getirme: vektör ve BM25'ten ayrı ayrı aday alınır, RRF ile birleştirilir,
# reranker'a RERANK_CANDIDATES aday gider, LLM'e FINAL_K parça verilir.
VECTOR_K = 15
BM25_K = 15
RERANK_CANDIDATES = 8
FINAL_K = 5

LLM_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
LLM_TEMPERATURE = 0.2
# Soru yeniden yazma ve cevapta kullanılacak son mesaj sayısı (soru+cevap = 2 mesaj).
HISTORY_MESSAGES = 6

NO_ANSWER = "Bu konuda bilgim yok."
