"""Hibrit getirme (FAISS + BM25), reranker ve Gemini ile cevap üretimi."""
import re
from datetime import date

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI
from rank_bm25 import BM25Okapi

import config
import ingest


def tr_lower(text):
    """Türkçe'ye uygun küçük harf: 'I' -> 'ı', 'İ' -> 'i' (str.lower bunu yanlış yapar)."""
    return text.replace("I", "ı").replace("İ", "i").lower()


def tokenize(text):
    # Türkçe eklemeli bir dil; kelimelerin ilk 5 harfini almak basit ama etkili bir kök bulma
    # yöntemi ("geçiş", "geçişi", "geçişler" -> "geçiş").
    return [w[:5] for w in re.findall(r"\w+", tr_lower(text))]


def source_label(doc):
    m = doc.metadata
    if "madde" in m:
        return f"{m['title']}, Madde {m['madde']}, s. {m['page']}"
    if m.get("section"):
        return f"{m['title']}, {m['section']}, s. {m['page']}"
    return f"{m['title']}, s. {m['page']}"


class HybridRetriever:
    """Vektör + BM25 sonuçlarını RRF ile birleştirir, varsa reranker ile yeniden sıralar."""

    def __init__(self, store, chunks):
        self.store = store
        self.chunks = chunks
        self.bm25 = BM25Okapi([tokenize(c.page_content) for c in chunks])
        self.reranker = None
        if config.RERANKER_MODEL:
            from sentence_transformers import CrossEncoder
            self.reranker = CrossEncoder(config.RERANKER_MODEL, max_length=config.RERANKER_MAX_LENGTH)

    def _vector_ids(self, query):
        return [d.metadata["chunk_id"] for d in self.store.similarity_search(query, k=config.VECTOR_K)]

    def _bm25_ids(self, query):
        scores = self.bm25.get_scores(tokenize(query))
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        return [i for i in ranked[:config.BM25_K] if scores[i] > 0]

    def search(self, query):
        # Reciprocal Rank Fusion: iki listede de üst sıralarda olan parçalar öne çıkar.
        fused = {}
        for ids in (self._vector_ids(query), self._bm25_ids(query)):
            for rank, chunk_id in enumerate(ids):
                fused[chunk_id] = fused.get(chunk_id, 0) + 1 / (60 + rank)
        ranked = sorted(fused, key=fused.get, reverse=True)

        if not self.reranker:
            return [self.chunks[i] for i in ranked[:config.FINAL_K]]
        candidates = [self.chunks[i] for i in ranked[:config.RERANK_CANDIDATES]]
        scores = self.reranker.predict([(query, c.page_content) for c in candidates])
        order = sorted(range(len(candidates)), key=lambda i: scores[i], reverse=True)
        return [candidates[i] for i in order[:config.FINAL_K]]


REWRITE_SYSTEM = (
    "Sana bir sohbet geçmişi ve kullanıcının son sorusu verilecek. Son soruyu, geçmişi görmeden de "
    "anlaşılabilecek bağımsız bir soru olarak yeniden yaz (ör. 'peki bunun son günü ne?' -> "
    "'Bahar dönemi ders kayıtlarının son günü ne?'). Soruyu cevaplama; sadece yeniden yazılmış soruyu "
    "döndür. Soru zaten bağımsızsa aynen döndür."
)

ANSWER_SYSTEM = """Sen Bolu Abant İzzet Baysal Üniversitesi (BAİBÜ) öğrencilerine yardım eden bir asistansın.

Kurallar:
- Yalnızca aşağıdaki "Bağlam" bölümündeki bilgilere dayanarak cevap ver. Dışarıdan bilgi ekleme, tahmin yürütme.
- Cevap bağlamda yoksa yalnızca "{no_answer}" yaz.
- Kullandığın her bilginin sonunda kaynağını köşeli parantezle belirt, ör. [Yatay Geçiş Yönergesi, Madde 8].
- Belgede bir kapsam veya istisna notu varsa (ör. takvimin hangi fakülteleri kapsamadığı) ve soruyla ilgiliyse belirt.
- Bugünün tarihi: {today}. Tarih sorularında gerekirse bu tarihin öncesinde mi sonrasında mı olduğunu belirt.
- Kısa, net ve Türkçe cevap ver.

Bağlam:
{context}"""


class RagBot:
    def __init__(self, retriever, llm):
        self.retriever = retriever
        self.llm = llm
        self.history = []
        self.rewrite_chain = ChatPromptTemplate.from_messages([
            ("system", REWRITE_SYSTEM),
            MessagesPlaceholder("history"),
            ("human", "{question}"),
        ]) | llm
        self.answer_chain = ChatPromptTemplate.from_messages([
            ("system", ANSWER_SYSTEM),
            MessagesPlaceholder("history"),
            ("human", "{question}"),
        ]) | llm

    @classmethod
    def from_index(cls):
        store, chunks = ingest.load_index()
        # max_retries düşük: kota dolduğunda (429) kullanıcı dakikalarca beklemesin.
        llm = ChatGoogleGenerativeAI(model=config.LLM_MODEL, temperature=config.LLM_TEMPERATURE, max_retries=2)
        return cls(HybridRetriever(store, chunks), llm)

    def reset(self):
        self.history = []

    def retrieve(self, question):
        """Geçmişe göre soruyu bağımsız hale getirip ilgili parçaları döndürür."""
        history = self.history[-config.HISTORY_MESSAGES:]
        query = question
        if history:
            query = self.rewrite_chain.invoke({"history": history, "question": question}).text.strip()
        return query, self.retriever.search(query)

    def ask(self, question):
        query, docs = self.retrieve(question)
        context = "\n\n".join(f"[{source_label(d)}]\n{d.page_content}" for d in docs)
        answer = self.answer_chain.invoke({
            "history": self.history[-config.HISTORY_MESSAGES:],
            "question": question,
            "context": context,
            "no_answer": config.NO_ANSWER,
            "today": date.today().strftime("%d.%m.%Y"),
        }).text.strip()
        self.history += [HumanMessage(question), AIMessage(answer)]
        return {"answer": answer, "query": query, "docs": docs}
