"""Service katmanı: RAG çekirdeği ile API arasındaki iş mantığı.

Soru sorma, her soru-cevabı kaydetme, geri bildirimi kaydetme ve corpus'u listeleme burada yapılır.
Bu modül FastAPI'yi ya da Gradio'yu bilmez; hangi arayüzden gelirse gelsin her istek aynı şekilde
işlenir ve kaydedilir.

Kayıtlar append-only JSONL dosyalarıdır (her satır bir JSON nesnesi, satırlar sonradan değiştirilmez):
  logs/sohbet.jsonl         her soru-cevap (hata alanları dahil)
  logs/geri_bildirim.jsonl  👍/👎 geri bildirimi; "id" alanıyla sohbet kaydına bağlanır
"""
import json
import subprocess
import threading
import time
import uuid
from collections import Counter
from datetime import datetime

import config
from rag import RagBot, source_label

LOG_DIR = config.ROOT / "logs"


def _git(*args):
    try:
        return subprocess.run(["git", *args], cwd=config.ROOT, capture_output=True, text=True,
                              check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _now():
    return datetime.now().isoformat(timespec="seconds")


class ChatService:
    def __init__(self, bot, experiment_id, log_dir=LOG_DIR):
        # bot dışarıdan verilir (dependency injection): testlerde gerçek modeller yerine sahte bir bot verilebilir.
        self.bot = bot
        self.experiment_id = experiment_id
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.chat_log = log_dir / "sohbet.jsonl"
        self.feedback_log = log_dir / "geri_bildirim.jsonl"
        # Sunucu açılırken bir kez okunur: hangi kod sürümü cevap veriyor? (commit edilmemiş değişiklik varsa "-dirty")
        commit = _git("rev-parse", "--short", "HEAD")
        dirty = bool(_git("status", "--porcelain", "--untracked-files=no"))
        self.commit = f"{commit}-dirty" if commit and dirty else commit
        # FastAPI senkron endpoint'leri ayrı thread'lerde çalıştırır; iki istek aynı anda dosyaya yazıp
        # satırları birbirine karıştırmasın diye yazma işlemi kilitle sıraya sokulur.
        self._lock = threading.Lock()
        self._known_ids = {r["id"] for r in self._read(self.chat_log)}

    @classmethod
    def from_experiment(cls, experiment_id=None):
        """Modelleri yükler (yavaş: index + GPU modelleri). Uygulama açılırken bir kez çağrılır."""
        experiment_id = experiment_id or config.PRODUCTION_EXPERIMENT
        cfg = config.RagConfig.from_dict(config.load_experiment(experiment_id)["params"])
        return cls(RagBot.from_config(cfg), experiment_id)

    # --- Kayıt yardımcıları ---

    def _append(self, path, record):
        line = json.dumps(record, ensure_ascii=False)
        with self._lock, path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    @staticmethod
    def _read(path):
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

    # --- İş mantığı ---

    def ask(self, question, history=None, session_id=None):
        """Soruyu cevaplar ve kaydeder. Hata olursa da kaydeder, sonra hatayı yukarı iletir."""
        record = {
            "id": uuid.uuid4().hex,
            "zaman": _now(),
            "oturum": session_id,
            "soru": question,
            "rewritten_query": None,
            "gecmis_uzunlugu": len(history or []),
            "cevap": None,
            "kaynaklar": [],
            "config": self.experiment_id,
            "commit": self.commit,
            "latency_ms": None,
            "hata": None,
        }
        started = time.perf_counter()
        try:
            result = self.bot.ask(question, history)
            record["cevap"] = result["answer"]
            if result["query"] != question:  # rewrite yapılmadıysa null kalır
                record["rewritten_query"] = result["query"]
            record["kaynaklar"] = [{"chunk_id": d.metadata["chunk_id"], "etiket": source_label(d)}
                                   for d in result["docs"]]
            return record
        except Exception as e:
            record["hata"] = f"{type(e).__name__}: {str(e)[:500]}"
            raise
        finally:
            # finally: cevap da dönse hata da fırlasa kayıt yazılır.
            record["latency_ms"] = round((time.perf_counter() - started) * 1000)
            self._append(self.chat_log, record)
            self._known_ids.add(record["id"])

    def feedback(self, answer_id, rating, note=None):
        """rating: 1 (👍) ya da -1 (👎). Bilinmeyen bir cevap kimliği için KeyError."""
        if answer_id not in self._known_ids:
            raise KeyError(answer_id)
        if rating not in (1, -1):
            raise ValueError("rating 1 ya da -1 olmalı")
        record = {"id": answer_id, "puan": rating, "not": note, "zaman": _now()}
        self._append(self.feedback_log, record)
        return record

    def documents(self):
        """Corpus'taki belgeler ve her birinin chunk sayısı."""
        chunks = self.bot.retriever.chunks
        counts = Counter(c.metadata["source"] for c in chunks)
        first = {}
        for c in chunks:
            first.setdefault(c.metadata["source"], c.metadata)
        return [{"source": s, "title": first[s]["title"], "kind": first[s].get("kind"), "chunk_count": n}
                for s, n in sorted(counts.items())]

    def document_chunks(self, source):
        """Bir belgenin chunk'ları (sırasıyla). Belge yoksa KeyError."""
        rows = [{"chunk_id": c.metadata["chunk_id"], "etiket": source_label(c), "metin": c.page_content}
                for c in self.bot.retriever.chunks if c.metadata["source"] == source]
        if not rows:
            raise KeyError(source)
        return rows
