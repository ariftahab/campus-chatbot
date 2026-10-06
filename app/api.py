"""API katmanı: FastAPI endpoint'leri.

Çalıştırma:  venv/Scripts/python.exe -m uvicorn app.api:app --port 8000
Dokümantasyon (Swagger UI):  http://localhost:8000/docs

Bu katman yalnız HTTP ile ilgilenir: isteği doğrular (Pydantic), service'i çağırır, sonucu JSON'a ve
hataları uygun HTTP durum kodlarına çevirir. İş mantığı (kayıt, geri bildirim) app/service.py'dedir.
"""
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.service import ChatService


# --- Şemalar (API sözleşmesi) ---
# İstemcinin göreceği alan adları burada tanımlanır. Log dosyasının iç biçimi değişse bile bu sözleşme
# sabit kalabilir; dışarıya açılan API'lerde alan adları yaygın olarak İngilizcedir.

class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000, examples=["Yatay geçiş başvurusu ne zaman yapılır?"])
    history: list[Message] = Field(default_factory=list, description="Önceki mesajlar (stateless: istemci tutar)")
    session_id: str | None = Field(default=None, description="Aynı sohbetin kayıtlarını gruplamak için")


class Source(BaseModel):
    chunk_id: int
    label: str


class AskResponse(BaseModel):
    id: str = Field(description="Bu cevabın kimliği; geri bildirimde kullanılır")
    answer: str
    rewritten_query: str | None = Field(description="Geçmişe göre yeniden yazılan soru; rewrite yoksa null")
    sources: list[Source]
    latency_ms: int


class FeedbackRequest(BaseModel):
    id: str
    rating: Literal[1, -1] = Field(description="1 = 👍, -1 = 👎")
    note: str | None = Field(default=None, max_length=1000)


class DocumentInfo(BaseModel):
    source: str
    title: str
    kind: str | None
    chunk_count: int


class ChunkInfo(BaseModel):
    chunk_id: int
    label: str
    text: str


class Health(BaseModel):
    status: str
    experiment: str
    commit: str | None
    documents: int


# --- Uygulama ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    # yield'dan önceki kısım sunucu açılırken bir kez çalışır: modeller (index, bge-m3, reranker) burada
    # yüklenir, her istekte değil. yield'dan sonrası kapanışta çalışır (şimdilik temizlenecek bir şey yok).
    app.state.service = ChatService.from_experiment()
    yield


app = FastAPI(
    title="BAİBÜ Kampüs Asistanı API",
    description="Bolu Abant İzzet Baysal Üniversitesi mevzuatı üzerinde RAG tabanlı soru-cevap.",
    version="0.1.0",
    lifespan=lifespan,
)


def get_service(request: Request) -> ChatService:
    """Endpoint'lere service'i veren dependency. Testlerde app.dependency_overrides ile sahtesi verilir."""
    return request.app.state.service


# Endpoint'ler `async def` değil düz `def`: bot.ask() GPU ve Gemini'yi bekleyen bloklayan bir çağrı.
# FastAPI düz def endpoint'leri ayrı bir thread havuzunda çalıştırır; böylece bir soru cevaplanırken
# sunucu diğer istekleri (ör. /health) karşılamaya devam eder.

@app.get("/health", response_model=Health, tags=["sistem"])
def health(service: ChatService = Depends(get_service)):
    """Sunucu ayakta mı, hangi config ve kod sürümüyle çalışıyor?"""
    return Health(status="ok", experiment=service.experiment_id, commit=service.commit,
                  documents=len(service.documents()))


@app.post("/ask", response_model=AskResponse, tags=["sohbet"])
def ask(req: AskRequest, service: ChatService = Depends(get_service)):
    """Soruyu cevaplar. Her soru-cevap logs/sohbet.jsonl'e kaydedilir."""
    try:
        record = service.ask(req.question, [m.model_dump() for m in req.history], req.session_id)
    except Exception as e:
        # Hata service'te zaten kaydedildi; burada yalnız istemciye uygun HTTP cevabına çevrilir.
        if "ResourceExhausted" in type(e).__name__ or "429" in str(e):
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                                "LLM kotası doldu (Gemini ücretsiz kota). Daha sonra tekrar deneyin.")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Cevap üretilemedi: {type(e).__name__}")
    return AskResponse(
        id=record["id"],
        answer=record["cevap"],
        rewritten_query=record["rewritten_query"],
        sources=[Source(chunk_id=s["chunk_id"], label=s["etiket"]) for s in record["kaynaklar"]],
        latency_ms=record["latency_ms"],
    )


@app.post("/feedback", status_code=status.HTTP_201_CREATED, tags=["sohbet"])
def feedback(req: FeedbackRequest, service: ChatService = Depends(get_service)):
    """Bir cevaba 👍/👎 verir (logs/geri_bildirim.jsonl)."""
    try:
        service.feedback(req.id, req.rating, req.note)
    except KeyError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Böyle bir cevap kaydı yok: {req.id}")
    return {"ok": True}


@app.get("/documents", response_model=list[DocumentInfo], tags=["data"])
def documents(service: ChatService = Depends(get_service)):
    """Corpus'taki belgeler ve chunk sayıları."""
    return service.documents()


@app.get("/documents/{source}/chunks", response_model=list[ChunkInfo], tags=["data"])
def document_chunks(source: str, service: ChatService = Depends(get_service)):
    """Bir belgenin chunk'ları. `source` dosya adıdır (ör. yatay-gecis-yonergesi.pdf)."""
    try:
        rows = service.document_chunks(source)
    except KeyError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Corpus'ta böyle bir belge yok: {source}")
    return [ChunkInfo(chunk_id=r["chunk_id"], label=r["etiket"], text=r["metin"]) for r in rows]
