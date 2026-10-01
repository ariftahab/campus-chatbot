"""Getirme (vektör / BM25 / hibrit + isteğe bağlı reranker) ve Gemini ile cevap üretimi.

Tüm davranış bir config.RagConfig ile belirlenir; bkz. experiments/configs/.
"""
import re
import unicodedata
from datetime import date

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI
from rank_bm25 import BM25Okapi

import config
import ingest


def tr_lower(text):
    """Türkçe'ye uygun küçük harf: 'I' -> 'ı', 'İ' -> 'i' (str.lower bunu yanlış yapar)."""
    text = unicodedata.normalize("NFC", text)
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


class Retriever:
    """cfg.retrieval'a göre vektör, BM25 ya da ikisinin RRF birleşimi; varsa reranker ile yeniden sıralar."""

    def __init__(self, cfg, store, chunks):
        self.cfg = cfg
        self.store = store
        self.chunks = chunks
        self.bm25 = BM25Okapi([tokenize(c.page_content) for c in chunks])
        self.reranker = None
        if cfg.reranker_model:
            from sentence_transformers import CrossEncoder
            self.reranker = CrossEncoder(cfg.reranker_model, max_length=cfg.reranker_max_length, device=cfg.device)

    def _vector_ids(self, query, k):
        return [d.metadata["chunk_id"] for d in self.store.similarity_search(query, k=k)]

    def _bm25_ids(self, query, k):
        scores = self.bm25.get_scores(tokenize(query))
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        return [i for i in ranked[:k] if scores[i] > 0]

    def rank(self, query, depth=10, trace=None):
        """Parçaların sıralı listesini döndürür (en az `depth` uzunluğunda, mümkünse).

        LLM'e bunun ilk final_k elemanı gider; değerlendirme ise sıralamanın tamamına bakar.
        `trace` bir sözlük verilirse ara aşamaların chunk_id listeleri içine yazılır
        ("vector", "bm25", "rrf", "rerank_input", "final"); sonuç bundan etkilenmez.
        """
        cfg = self.cfg
        trace = {} if trace is None else trace
        if cfg.retrieval == "vector":
            ids = trace["vector"] = self._vector_ids(query, max(cfg.vector_k, depth))
        elif cfg.retrieval == "bm25":
            ids = trace["bm25"] = self._bm25_ids(query, max(cfg.bm25_k, depth))
        elif cfg.retrieval == "hybrid":
            # Reciprocal Rank Fusion: iki listede de üst sıralarda olan parçalar öne çıkar.
            trace["vector"] = self._vector_ids(query, cfg.vector_k)
            trace["bm25"] = self._bm25_ids(query, cfg.bm25_k)
            fused = {}
            for ranked in (trace["vector"], trace["bm25"]):
                for rank, chunk_id in enumerate(ranked):
                    fused[chunk_id] = fused.get(chunk_id, 0) + 1 / (cfg.rrf_k + rank)
            ids = trace["rrf"] = sorted(fused, key=fused.get, reverse=True)
        else:
            raise ValueError(f"Bilinmeyen retrieval: {cfg.retrieval}")

        if self.reranker:
            # İlk rerank_candidates aday yeniden sıralanır, geri kalanlar sırasını korur.
            head, tail = ids[:cfg.rerank_candidates], ids[cfg.rerank_candidates:]
            trace["rerank_input"] = list(head)
            scores = self.reranker.predict([(query, self.chunks[i].page_content) for i in head])
            head = [head[j] for j in sorted(range(len(head)), key=lambda j: scores[j], reverse=True)]
            ids = head + tail
        trace["final"] = list(ids)
        return [self.chunks[i] for i in ids]

    def search(self, query):
        return self.rank(query)[:self.cfg.final_k]


# --- Prompt'lar ---
# Sürümler silinmez; eski deneylerin tekrar üretilebilmesi için yenisi yeni anahtarla eklenir.

# İlk prototipin (prototip-chat.py) prompt'u, girinti dahil birebir.
_V1_TEMPLATE = """
    Sen bir üniversite asistan chatbotusun. 
    Sana verilen 'Bağlam'ı kullanarak 'Soru'ya cevap ver. 
    Eğer cevap 'Bağlam' içinde yoksa, "Bu konuda bilgim yok." de. 
    Cevaplarını sadece verilen bağlama dayandır, dışarıdan bilgi ekleme.

    Bağlam:
    {context}

    Soru:
    {input}

    Cevap:
    """

_V2_SYSTEM = """Sen Bolu Abant İzzet Baysal Üniversitesi (BAİBÜ) öğrencilerine yardım eden bir asistansın.

Kurallar:
- Yalnızca aşağıdaki "Bağlam" bölümündeki bilgilere dayanarak cevap ver. Dışarıdan bilgi ekleme, tahmin yürütme.
- Cevap bağlamda yoksa yalnızca "{no_answer}" yaz.
- Kullandığın her bilginin sonunda kaynağını köşeli parantezle belirt, ör. [Yatay Geçiş Yönergesi, Madde 8].
- Belgede bir kapsam veya istisna notu varsa (ör. takvimin hangi fakülteleri kapsamadığı) ve soruyla ilgiliyse belirt.
- Bugünün tarihi: {today}. Tarih sorularında gerekirse bu tarihin öncesinde mi sonrasında mı olduğunu belirt.
- Kısa, net ve Türkçe cevap ver.

Bağlam:
{context}"""


# v3: Corpus 139 belgeye çıkınca aynı konu birden fazla belgede, farklı kapsamlar için farklı kurallarla geçiyor
# (genel yönetmelik ile fakülteye özel yönetmelik, lisans ile lisansüstü). v2 bağlamdan tek bir cevap seçip
# kapsamı söylemeyebiliyordu. v3 kapsam ayrımını kavram olarak anlatır; belirli bir örnek vermez ki model
# örneği ezberlemek yerine kuralı genellesin.
_V3_SYSTEM = """Sen Bolu Abant İzzet Baysal Üniversitesi (BAİBÜ) öğrencilerine yardım eden bir asistansın.

Kurallar:
- Yalnızca aşağıdaki "Bağlam" bölümündeki bilgilere dayanarak cevap ver. Dışarıdan bilgi ekleme, tahmin yürütme.
- Cevap bağlamda yoksa yalnızca "{no_answer}" yaz.
- Kullandığın her bilginin sonunda kaynağını köşeli parantezle belirt (bağlamdaki parça etiketlerinde yazan belge adı ve madde).
- Bağlamdaki her belgenin kimi kapsadığını belge adından ve içeriğinden anla: tüm üniversite mi, belirli bir fakülte
  veya yüksekokul mu, belirli bir öğretim düzeyi mi (ön lisans, lisans, lisansüstü), belirli bir öğrenci grubu mu.
- Aynı soruya bağlamdaki belgeler farklı kapsamlar için farklı kurallar veriyorsa yalnızca birini seçme. Her kuralı,
  hangi kapsam için geçerli olduğunu açıkça söyleyerek ayrı ayrı yaz.
- Soru belirli bir kapsamı soruyorsa o kapsama özgü kuralı esas al; o kapsama özgü bir düzenleme bağlamda yoksa genel
  kuralı ver ve bunun genel kural olduğunu belirt.
- Farklı belgeler aynı kuralı aynı şekilde veriyorsa tekrar etme; tek cevapta birleştir.
- Belgede bir istisna veya kapsam notu varsa ve soruyla ilgiliyse belirt.
- Bugünün tarihi: {today}. Tarih sorularında gerekirse bu tarihin öncesinde mi sonrasında mı olduğunu belirt.
- Kısa, net ve Türkçe cevap ver.

Bağlam:
{context}"""


def _format_v1(docs):
    # create_stuff_documents_chain varsayılanı: parça metinleri boş satırla birleştirilir.
    return "\n\n".join(d.page_content for d in docs)


def _format_v2(docs):
    return "\n\n".join(f"[{source_label(d)}]\n{d.page_content}" for d in docs)


PROMPTS = {
    "v1_prototip": {
        "template": ChatPromptTemplate.from_template(_V1_TEMPLATE),
        "format": _format_v1,
        "history": False,
    },
    "v2_kaynakli": {
        "template": ChatPromptTemplate.from_messages([
            ("system", _V2_SYSTEM),
            MessagesPlaceholder("history"),
            ("human", "{input}"),
        ]),
        "format": _format_v2,
        "history": True,
    },
    "v3_kapsam": {
        "template": ChatPromptTemplate.from_messages([
            ("system", _V3_SYSTEM),
            MessagesPlaceholder("history"),
            ("human", "{input}"),
        ]),
        "format": _format_v2,  # parça etiketleri aynı: [Belge, Madde N, s. X]
        "history": True,
    },
}

REWRITE_SYSTEM = (
    "Sana bir sohbet geçmişi ve kullanıcının son sorusu verilecek. Son soruyu, geçmişi görmeden de "
    "anlaşılabilecek bağımsız bir soru olarak yeniden yaz (ör. 'peki bunun son günü ne?' -> "
    "'Bahar dönemi ders kayıtlarının son günü ne?'). Soruyu cevaplama; sadece yeniden yazılmış soruyu "
    "döndür. Soru zaten bağımsızsa aynen döndür."
)


class RagBot:
    def __init__(self, cfg, retriever, llm):
        self.cfg = cfg
        self.retriever = retriever
        self.llm = llm
        self.prompt = PROMPTS[cfg.prompt_version]
        self.history = []
        self.rewrite_chain = ChatPromptTemplate.from_messages([
            ("system", REWRITE_SYSTEM),
            MessagesPlaceholder("history"),
            ("human", "{question}"),
        ]) | llm

    @classmethod
    def from_config(cls, cfg):
        store, chunks, _ = ingest.load_index(cfg)
        # max_retries düşük: kota dolduğunda (429) kullanıcı dakikalarca beklemesin.
        llm = ChatGoogleGenerativeAI(model=cfg.llm_model, temperature=cfg.llm_temperature, max_retries=2)
        return cls(cfg, Retriever(cfg, store, chunks), llm)

    def reset(self):
        self.history = []

    def retrieve(self, question):
        """Geçmiş varsa soruyu bağımsız hale getirip ilgili parçaları döndürür."""
        history = self.history[-config.HISTORY_MESSAGES:]
        query = question
        if history and self.prompt["history"]:
            query = self.rewrite_chain.invoke({"history": history, "question": question}).text.strip()
        return query, self.retriever.search(query)

    def ask(self, question):
        query, docs = self.retrieve(question)
        variables = {"input": question, "context": self.prompt["format"](docs)}
        if self.prompt["history"]:
            variables.update({
                "history": self.history[-config.HISTORY_MESSAGES:],
                "no_answer": config.NO_ANSWER,
                "today": date.today().strftime("%d.%m.%Y"),
            })
        answer = (self.prompt["template"] | self.llm).invoke(variables).text.strip()
        self.history += [HumanMessage(question), AIMessage(answer)]
        return {"answer": answer, "query": query, "docs": docs}
