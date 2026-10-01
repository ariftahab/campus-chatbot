"""Genel ayarlar ve RAG hattı yapılandırması.

RAG bileşenlerinin parametreleri (parçalama, embedding, getirme, reranker, LLM) kodda değil,
experiments/configs/EXP-*.json deney dosyalarında tutulur. Sohbet uygulaması
PRODUCTION_EXPERIMENT deneyinin parametreleriyle çalışır; böylece kullanılan her yapılandırma
kayıtlı ve ölçülmüş bir deneye karşılık gelir.
"""
import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
INDEX_ROOT = ROOT / "vectorstore"  # her yapılandırma kendi alt klasöründe
EVAL_FILE = ROOT / "eval" / "sorular.json"
EXPERIMENTS_DIR = ROOT / "experiments"

# Sohbet uygulamasının kullandığı deney. Yeni bir deney üretime alınacaksa burası değişir.
PRODUCTION_EXPERIMENT = "EXP-013"

# Belge adları kaynak gösteriminde ve parçaların başlığında kullanılır.
# Listede olmayan bir PDF eklenirse dosya adı başlık olarak kullanılır.
# tur: "takvim" -> tablo satırları okunur, "mevzuat" -> madde madde bölünür (yapısal parçalamada).
DOCUMENTS = {
    "akademik-takvim.pdf": {"title": "BAİBÜ 2025-2026 Akademik Takvimi", "tur": "takvim"},
    "ogrenci-kayıt-yonerge.pdf": {"title": "BAİBÜ Öğrenci Kayıt Kabul İşleri Yönetmeliği", "tur": "mevzuat"},
    "yatay-gecis-yonergesi.pdf": {"title": "BAİBÜ Yatay Geçiş Yönergesi", "tur": "mevzuat"},
}

# Soru yeniden yazma ve cevapta kullanılacak son mesaj sayısı (soru+cevap = 2 mesaj).
HISTORY_MESSAGES = 6
NO_ANSWER = "Bu konuda bilgim yok."


@dataclass(frozen=True)
class RagConfig:
    # Belge işleme
    pdf_parser: str            # "pypdf" | "pdfplumber"
    chunking: str              # "recursive" (sabit boyut) | "structural" (madde / takvim tablosu)
    chunk_size: int            # recursive: parça boyutu; structural: bu boyutu aşan madde bölünür (karakter)
    chunk_overlap: int         # karakter
    # Embedding
    embedding_model: str
    normalize_embeddings: bool  # True -> kosinüs benzerliği, False -> ham L2 uzaklığı
    # Getirme
    retrieval: str             # "vector" | "bm25" | "hybrid"
    vector_k: int              # vektör aramasından alınan aday sayısı
    bm25_k: int                # BM25'ten alınan aday sayısı
    rrf_k: int                 # Reciprocal Rank Fusion sabiti (yalnız hybrid)
    reranker_model: Optional[str]  # None -> reranker yok
    reranker_max_length: int   # reranker'ın okuduğu en fazla token
    rerank_candidates: int     # reranker'a giden aday sayısı
    final_k: int               # LLM'e bağlam olarak verilen parça sayısı
    # Üretim
    llm_model: str
    llm_temperature: float
    prompt_version: str        # rag.PROMPTS anahtarı

    # İndeksi (parçaları ve embedding'leri) etkileyen parametreler
    INDEX_FIELDS = ("pdf_parser", "chunking", "chunk_size", "chunk_overlap",
                    "embedding_model", "normalize_embeddings")

    @classmethod
    def from_dict(cls, params):
        names = {f.name for f in fields(cls)}
        unknown = set(params) - names
        missing = names - set(params)
        if unknown or missing:
            raise ValueError(f"Geçersiz parametreler. Bilinmeyen: {sorted(unknown)}, eksik: {sorted(missing)}")
        cfg = cls(**params)
        if cfg.chunking == "structural" and cfg.pdf_parser != "pdfplumber":
            raise ValueError("structural parçalama pdfplumber gerektirir (takvim tabloları için).")
        return cfg

    def to_dict(self):
        return asdict(self)

    def index_params(self):
        return {k: getattr(self, k) for k in self.INDEX_FIELDS}


def load_experiment(exp_id):
    path = EXPERIMENTS_DIR / "configs" / f"{exp_id}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def production_config():
    return RagConfig.from_dict(load_experiment(PRODUCTION_EXPERIMENT)["params"])
