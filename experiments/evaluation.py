"""Deneylerde kullanılan ölçüm fonksiyonları: veri seti, ilgililik, metrikler, istatistik testleri, ortam bilgisi.

Metrik tanımları (hepsi soru başına hesaplanıp ortalaması alınır):
  hit@k        : ilk k parçada en az bir ilgili parça var mı (0/1)
  rr           : 1 / (ilk ilgili parçanın sırası), ilk 10'da yoksa 0; ortalaması MRR@10
  context_hit  : LLM'e giden ilk final_k parçada ilgili parça var mı (0/1)
  context_chars: LLM'e giden bağlamın toplam karakter sayısı (maliyet göstergesi)
  latency_ms   : yalnız getirme süresi (LLM hariç), milisaniye
  answer_ok    : LLM cevabı beklenen anahtar kelimeleri içeriyor mu (0/1), yalnız --llm ile
"""
import hashlib
import importlib.metadata
import json
import os
import platform
import re
import subprocess
from pathlib import Path

from scipy.stats import binomtest, wilcoxon

import config
from rag import tr_lower

EVAL_DEPTH = 10  # sıralama metrikleri ilk 10 parça üzerinden
HIT_KS = (1, 3, 5, 10)

# Metriklerin "iyi" yönü: +1 büyük iyi, -1 küçük iyi
METRIC_DIRECTION = {
    "mrr@10": +1, "hit@1": +1, "hit@3": +1, "hit@5": +1, "hit@10": +1,
    "context_hit": +1, "context_chars": -1, "latency_ms": -1, "answer_acc": +1,
}
PER_QUESTION_KEY = {  # özet metrik -> soru başına değer anahtarı
    "mrr@10": "rr", "hit@1": "hit@1", "hit@3": "hit@3", "hit@5": "hit@5", "hit@10": "hit@10",
    "context_hit": "context_hit", "context_chars": "context_chars", "latency_ms": "latency_ms",
    "answer_acc": "answer_ok",
}
BINARY_METRICS = {"hit@1", "hit@3", "hit@5", "hit@10", "context_hit", "answer_acc"}
NO_CHANGE_EPS = 1e-9


# --- Veri seti ---

def load_dataset():
    raw = config.EVAL_FILE.read_bytes()
    data = json.loads(raw.decode("utf-8"))
    return data, hashlib.sha256(raw).hexdigest()[:16]


def norm(text):
    """Karşılaştırma için: NFC + Türkçe küçük harf + harf/rakam dışı her şey silinir.

    Böylece "ö ğretim" (pypdf boşluk hatası), satır sonları, tire ve iki nokta farkları eşleşmeyi bozmaz.
    """
    return re.sub(r"[\W_]+", "", tr_lower(text))


def evidence_alternatives(item):
    """Her alternatif, aynı parçada birlikte bulunması gereken ifadelerin listesidir."""
    return [[alt] if isinstance(alt, str) else alt for alt in item["kanit"]]


def is_relevant(item, chunk_text_norm, chunk_source):
    return chunk_source == item["kaynak"] and any(
        all(norm(part) in chunk_text_norm for part in alt) for alt in evidence_alternatives(item))


def validate_dataset(data):
    """Her kanıtın kaynak PDF'in ham metninde (her iki okuyucuda da) geçtiğini doğrular.

    Kanıt bir okuyucunun metninde yoksa o okuyucuyla yapılan deneyler haksız yere cezalanır;
    bu yüzden eksik kanıt hata sayılır.
    """
    import ingest
    texts = {}
    # Yalnız soruların kaynak gösterdiği belgeler okunur (138 belgenin hepsini iki okuyucuyla okumak yavaş).
    for path in {config.DATA_DIR / item["kaynak"] for item in data["sorular"] if "kanit" in item}:
        for parser in ("pypdf", "pdfplumber"):
            texts[(path.name, parser)] = norm(" ".join(ingest.read_pages(path, parser)))
    problems = []
    for item in data["sorular"]:
        if "kanit" not in item:
            continue
        for alt in evidence_alternatives(item):
            for part in alt:
                for parser in ("pypdf", "pdfplumber"):
                    if norm(part) not in texts.get((item["kaynak"], parser), ""):
                        problems.append(f"{item['id']}: '{part}' {parser} metninde bulunamadı")
    return problems


# --- İstatistik ---

def paired_test(metric, before, after):
    """Aynı sorular üzerinde eşleştirilmiş test.

    İkili metrikler (hit, context_hit, answer) için kesin McNemar testi (uyuşmayan çiftler üzerinde
    binom testi); sürekli metrikler (rr, karakter, gecikme) için Wilcoxon işaretli sıra testi.
    Tüm farklar sıfırsa p = 1.
    """
    if metric in BINARY_METRICS:
        b = sum(1 for x, y in zip(before, after) if x > y)
        c = sum(1 for x, y in zip(before, after) if x < y)
        if b + c == 0:
            return {"test": "McNemar (kesin)", "p": 1.0, "kotulesen": b, "iyilesen": c}
        return {"test": "McNemar (kesin)", "p": binomtest(min(b, c), b + c, 0.5).pvalue,
                "kotulesen": b, "iyilesen": c}
    diffs = [y - x for x, y in zip(before, after)]
    if all(abs(d) < NO_CHANGE_EPS for d in diffs):
        return {"test": "Wilcoxon", "p": 1.0}
    return {"test": "Wilcoxon", "p": float(wilcoxon(before, after, zero_method="wilcox").pvalue)}


def verdict(metric, delta, p, expected):
    """Önceden tanımlı karar kuralı (experiment_log.md başında açıklanır)."""
    better = METRIC_DIRECTION[metric]
    if abs(delta) < NO_CHANGE_EPS:
        observed = "degisim_yok"
        # Ortalama aynı kalıp bazı sorular iyileşip bazıları kötüleşmiş olabilir.
        outcome = "Değişim yok" if p >= 1.0 else "Ortalamada değişim yok (bazı sorularda sıra değişti)"
    else:
        observed = "artis" if delta > 0 else "azalis"
        good = (delta > 0) == (better > 0)
        word = "iyileşme" if good else "kötüleşme"
        outcome = f"Anlamlı {word} (p<0,05)" if p < 0.05 else f"Sayısal {word} (istatistiksel olarak anlamlı değil)"
    if expected == observed:
        hypothesis = "Doğrulandı" if (observed == "degisim_yok" or p < 0.05) else "Yön doğru, anlamlı değil"
    else:
        hypothesis = "Doğrulanmadı"
    return outcome, hypothesis


# --- Ortam ---

KEY_PACKAGES = ["torch", "sentence-transformers", "transformers", "faiss-cpu", "rank-bm25", "pdfplumber",
                "pypdf", "langchain-core", "langchain-community", "langchain-text-splitters",
                "langchain-huggingface", "langchain-google-genai", "scipy"]


def _git(*args):
    try:
        return subprocess.run(["git", *args], cwd=config.ROOT, capture_output=True, text=True,
                              check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def model_revision(name):
    """Hugging Face önbelleğindeki model anlık görüntüsünün (snapshot) commit kimliği."""
    if not name:
        return None
    from huggingface_hub import try_to_load_from_cache
    repo = name if "/" in name else f"sentence-transformers/{name}"
    path = try_to_load_from_cache(repo, "config.json")
    return Path(path).parent.name if isinstance(path, str) else None


def environment(cfg):
    import torch
    return {
        "git_commit": _git("rev-parse", "HEAD"),
        # Koşucunun kendi çıktıları (sonuçlar, günlük) "commit edilmemiş değişiklik" sayılmaz.
        "git_dirty": bool(_git("status", "--porcelain", "--", ".", ":!experiments/results",
                               ":!experiments/experiment_log.md")),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "cpu": platform.processor(),
        "cpu_count": os.cpu_count(),
        "torch_device": "cuda" if torch.cuda.is_available() else "cpu",
        "packages": {p: _version(p) for p in KEY_PACKAGES},
        "model_revisions": {
            "embedding": model_revision(cfg.embedding_model),
            "reranker": model_revision(cfg.reranker_model),
        },
    }


def _version(package):
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return None
