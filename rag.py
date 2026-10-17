"""Getirme (vektör / BM25 / hibrit + isteğe bağlı reranker) ve Gemini ile cevap üretimi.

Tüm davranış bir config.RagConfig ile belirlenir; bkz. experiments/configs/.
"""
import json
import re
import time
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


# --- Kapsam tamamlama (scope_search) ---
# Aynı konuda kendi kuralını koyan öğrenci grupları ("paralel kapsamlar") ve sorguya eklenen adları. Genel bir soruda
# (ör. "Mezun olmak için kaç kredi?") reranker genel kuralı öne alır; fakülteye özel maddeler context'e ulaşmaz
# (EXP-023: kapsam isabeti 0,51). Kapsam adı sorguya eklenince reranker o kapsamın maddesini doğru puanlar.
SCOPE_FILES = {"parallel_v1": config.DATA_DIR / "belge_kapsam_v1.json"}
PARALLEL_SCOPES = {
    "genel_onlisans_lisans": "önlisans ve lisans",
    "tip": "Tıp Fakültesi",
    "dis": "Diş Hekimliği Fakültesi",
    "hukuk": "Hukuk Fakültesi",
    "lisansustu": "lisansüstü, yüksek lisans ve doktora",
}
# Soru bir kapsamı adıyla anıyorsa kullanıcı o kapsamı soruyordur; tamamlama yapılmaz.
SCOPE_MENTION = re.compile(r"\btıp|\bdiş|\bhukuk|lisansüstü|yüksek lisans|doktora|önlisans|ön lisans", re.IGNORECASE)
SCOPE_CANDIDATES = 10   # her kapsamda vector ve BM25'ten alınan aday sayısı
SCOPE_RERANK = 5        # kapsam içinde reranker'a giden aday sayısı
SCOPE_MIN_SCORE = 0.0   # eklenmek için en düşük reranker puanı (kalibrasyonla belirlenecek)
SCOPE_EXTRA_MAX = 4     # context'e eklenebilecek en fazla chunk


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
            if cfg.reranker_dtype == "fp16":
                # Ağırlıklar 16 bit: GPU'da ~3× hızlı, ~1 GB daha az bellek; puanlar fp32'den çok az farklıdır.
                self.reranker.model.half()
        self.scope_of = {}  # chunk_id -> paralel kapsam (yalnız paralel kapsamlardaki belgelerin chunk'ları)
        if cfg.scope_search:
            labels = json.loads(SCOPE_FILES[cfg.scope_search].read_text(encoding="utf-8"))["belgeler"]
            for c in chunks:
                scope = labels.get(c.metadata["source"], {}).get("kapsam")
                if scope in PARALLEL_SCOPES:
                    self.scope_of[c.metadata["chunk_id"]] = scope

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
            # batch_size=8: varsayılan 32 çift tek seferde işlenince 6 GB GPU'da bellek taşıyor (bge-m3 de
            # GPU'da); 30 aday 1,2 sn yerine ~6 sn sürüyor. Batch boyutu puanları değil, yalnız belleği/hızı etkiler.
            scores = self.reranker.predict([(query, self.chunks[i].page_content) for i in head], batch_size=8)
            head = [head[j] for j in sorted(range(len(head)), key=lambda j: scores[j], reverse=True)]
            ids = head + tail
        trace["context_n"] = cfg.final_k  # LLM'e giden parça sayısı (kapsam tamamlama artırabilir)
        if cfg.scope_search:
            ids = self._complete_scopes(query, ids, trace)
        trace["final"] = list(ids)
        return [self.chunks[i] for i in ids]

    def _complete_scopes(self, query, ids, trace):
        """Context'te temsil edilmeyen paralel kapsamların en iyi chunk'ını o kapsamın belgelerinde arayıp ekler.

        Yalnız context'te en az bir paralel kapsam belgesi varsa (soru bu yönetmeliklerin konusu) ve soru bir kapsamı
        adıyla anmıyorsa devreye girer. Eklenen chunk'lar context'in sonuna (final_k'dan sonra) konur.
        """
        k = self.cfg.final_k
        present = {self.scope_of[i] for i in ids[:k] if i in self.scope_of}
        trace["scope_added"] = []
        if not present or SCOPE_MENTION.search(query):
            return ids
        found = []
        for scope, label in PARALLEL_SCOPES.items():
            if scope in present:
                continue
            allowed = {i for i, s in self.scope_of.items() if s == scope}
            scoped_query = f"{query} ({label})"
            vec = [d.metadata["chunk_id"] for d in self.store.similarity_search(
                scoped_query, k=SCOPE_CANDIDATES, filter=lambda md: md["chunk_id"] in allowed,
                fetch_k=len(self.chunks))]
            bm_scores = self.bm25.get_scores(tokenize(scoped_query))
            bm = sorted((i for i in allowed if bm_scores[i] > 0), key=lambda i: bm_scores[i], reverse=True)
            fused = {}
            for ranked in (vec, bm[:SCOPE_CANDIDATES]):
                for rank, chunk_id in enumerate(ranked):
                    fused[chunk_id] = fused.get(chunk_id, 0) + 1 / (self.cfg.rrf_k + rank)
            cands = sorted(fused, key=fused.get, reverse=True)[:SCOPE_RERANK]
            if not cands:
                continue
            scores = self.reranker.predict([(scoped_query, self.chunks[i].page_content) for i in cands], batch_size=8)
            best = max(range(len(cands)), key=lambda j: scores[j])
            trace["scope_added"].append({"kapsam": scope, "chunk_id": cands[best], "puan": round(float(scores[best]), 4),
                                         "eklendi": bool(scores[best] >= SCOPE_MIN_SCORE)})
            if scores[best] >= SCOPE_MIN_SCORE:
                found.append((float(scores[best]), cands[best]))
        extra = [i for _, i in sorted(found, reverse=True)[:SCOPE_EXTRA_MAX] if i not in ids[:k]]
        trace["context_n"] = k + len(extra)
        return ids[:k] + extra + [i for i in ids[k:] if i not in extra]

    def search(self, query):
        trace = {}
        ranking = self.rank(query, trace=trace)
        return ranking[:trace["context_n"]]


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

# v4: fakülte belirtilmeyen sorularda bütün kapsamları saymak yerine genel kuralı verip fakülteyi sorar (set 4.1'in
# hedef davranışı). Diğer kapsamların chunk'ları çoğu zaman context'e hiç gelmiyor (EXP-023: kapsam isabeti 0,51);
# saymaya çalışmak eksik liste demekti. v3'ten tek fark kapsam maddesi.
_V3_SCOPE_RULE = """- Aynı soruya bağlamdaki belgeler farklı kapsamlar için farklı kurallar veriyorsa yalnızca birini seçme. Her kuralı,
  hangi kapsam için geçerli olduğunu açıkça söyleyerek ayrı ayrı yaz."""
_V4_SCOPE_RULE = """- Soru öğrencinin fakültesini, bölümünü veya öğretim düzeyini belirtmiyorsa ve bağlamdaki kural bunlara göre farklılık
  gösteriyorsa: genel kuralı ver, bazı fakülte veya programlarda farklı olabileceğini belirt ve sonunda öğrencinin hangi
  fakültede veya programda okuduğunu sor. Diğer kapsamların kurallarını tek tek sayma. Soru bir fakülte veya program
  belirtiyorsa sorma; o kapsamın kuralını ver."""
assert _V3_SCOPE_RULE in _V3_SYSTEM
_V4_SYSTEM = _V3_SYSTEM.replace(_V3_SCOPE_RULE, _V4_SCOPE_RULE)

# v5: v4'te model "diğer kapsamları tek tek sayma" yasağına rağmen kapsamları sayıp sonra soruyordu (EXP-027: netleştirme
# açılan cevaplar ortalama 602, en uzun 2635 karakter). Yasak yerine istenen biçim adım adım tarif edilir.
_V5_SCOPE_RULE = """- Bu soruda öğrencinin fakültesi, bölümü veya öğretim düzeyi belli değil ve bağlamdaki kural bunlara göre
  değişebiliyor. Cevabı tam olarak şu üç parçayla yaz:
  1) Genel kuralı bir veya iki cümleyle, kaynağıyla birlikte yaz.
  2) Tek cümleyle bazı fakülte veya programlarda bu kuralın farklı olabileceğini söyle (farklı kuralların içeriğini
     yazma).
  3) Son cümlede öğrencinin hangi fakültede veya programda okuduğunu sor.
  Örnek biçim: "Genel olarak ... [Belge, Madde N]. Bazı fakülte ve programlarda bu kural farklı olabilir. Hangi
  fakültede veya programda okuyorsunuz?\""""
_V5_SYSTEM = _V3_SYSTEM.replace(_V3_SCOPE_RULE, _V5_SCOPE_RULE)

# v6: v5'in "cevabı tam olarak şu üç parçayla yaz" kuralı cevap bağlamda yokken de bir genel kural yazdırıyordu (EXP-034:
# iki çekimser kalma sorusunda "bilgim yok" yerine başka kapsamın kuralı) ve kurallar aynıyken de fakülteyi sorduruyordu.
# Üç durum ayrı ayrı, olumlu talimatla tarif edilir (kullanıcı kararı: prompt'ta yasak yerine istenen davranış yazılır).
_V6_SCOPE_RULE = """- Bu soruda öğrencinin fakültesi, bölümü veya öğretim düzeyi belli değil. Cevabı bağlama göre şu üç durumdan
  birine uygun yaz:
  a) Bağlamdaki belgeler bu soruya farklı kapsamlar için farklı kurallar veriyorsa cevabı şu üç parçayla yaz:
     1) Genel kuralı bir veya iki cümleyle, kaynağıyla birlikte yaz.
     2) Tek cümleyle bazı fakülte veya programlarda bu kuralın farklı olabileceğini söyle; cevapta yalnız genel kuralın
        içeriği yer alsın.
     3) Son cümlede öğrencinin hangi fakültede veya programda okuduğunu sor.
     Örnek biçim: "Genel olarak ... [Belge, Madde N]. Bazı fakülte ve programlarda bu kural farklı olabilir. Hangi
     fakültede veya programda okuyorsunuz?"
  b) Bağlamdaki belgeler bu soruya tek bir kural veriyorsa ya da bütün kapsamlar için aynı kuralı veriyorsa kuralı
     doğrudan, kaynağıyla birlikte yaz.
  c) Sorunun cevabı bağlamda yoksa yalnızca "{no_answer}" yaz."""
_V6_SYSTEM = _V3_SYSTEM.replace(_V3_SCOPE_RULE, _V6_SCOPE_RULE)

# v7: kapsam kararı kesin (2026-10-17): model kapsamları hiçbir zaman sıralamaz. Soruda kapsam varsa o kapsamın kuralı,
# yoksa genel kural + fakülte sorusu. v3'ün "her kuralı kapsamıyla ayrı ayrı yaz" maddesi (tetik açılmadığında da
# sıralatıyordu, ör. staj süresi sorusu) ve "belirli kapsamı soruyorsa" maddesi bu iki maddeye iner. Bütün kurallar
# olumlu talimat (kullanıcı kararı); "Dışarıdan bilgi ekleme" ve "tekrar etme" de istenen davranış olarak yazılır.
_V7_GENERAL_RULE = """- Soru bir kapsam belirtmiyorsa genel kuralı ver. Genel kural, bütün öğrencileri ya da bütün ön lisans ve lisans
  öğrencilerini kapsayan belgedeki kuraldır. Bağlamda belirli fakülte, yüksekokul veya programlara özgü kurallar da
  varsa genel kuralın ardından tek cümleyle bazı fakülte veya programlarda bu kuralın farklı olabileceğini söyle ve
  son cümlede öğrencinin hangi fakültede veya programda okuduğunu sor."""
_V7_SYSTEM = """Sen Bolu Abant İzzet Baysal Üniversitesi (BAİBÜ) öğrencilerine yardım eden bir asistansın.

Kurallar:
- Yalnızca aşağıdaki "Bağlam" bölümündeki bilgilere dayanarak cevap ver.
- Cevap bağlamda yoksa yalnızca "{no_answer}" yaz.
- Kullandığın her bilginin sonunda kaynağını köşeli parantezle belirt (bağlamdaki parça etiketlerinde yazan belge adı ve madde).
- Bağlamdaki her belgenin kimi kapsadığını belge adından ve içeriğinden anla: tüm üniversite mi, belirli bir fakülte
  veya yüksekokul mu, belirli bir öğretim düzeyi mi (ön lisans, lisans, lisansüstü), belirli bir öğrenci grubu mu.
- Soru bir fakülte, yüksekokul, program veya öğretim düzeyi belirtiyorsa o kapsamın kuralını ver; bağlamda o kapsama
  özgü bir düzenleme yoksa genel kuralı ver ve bunun genel kural olduğunu belirt.
""" + _V7_GENERAL_RULE + """
- Farklı belgeler aynı kuralı veriyorsa bu kuralı tek cümlede, kaynaklarını aynı köşeli parantezde ';' ile ayırarak yaz.
- Belgede bir istisna veya kapsam notu varsa ve soruyla ilgiliyse belirt.
- Bugünün tarihi: {today}. Tarih sorularında gerekirse bu tarihin öncesinde mi sonrasında mı olduğunu belirt.
- Kısa, net ve Türkçe cevap ver.

Bağlam:
{context}"""
# Netleştirme tetiği açıldığında (context'te farklı paralel kapsamların belgeleri, soruda kapsam yok) fakülte sorusu
# koşulsuz istenir; cevap bağlamda yoksa genel "bilgim yok" kuralı geçerli kalsın diye biçim cevabın varlığına bağlanır.
_V7_CLARIFY_RULE = """- Bu soruda öğrencinin fakültesi, bölümü veya öğretim düzeyi belli değil ve bağlamdaki kural bunlara göre
  değişebiliyor. Bağlamda sorunun cevabı varsa genel kuralı bir veya iki cümleyle, kaynağıyla yaz; ardından tek cümleyle
  bazı fakülte veya programlarda bu kuralın farklı olabileceğini söyle ve son cümlede öğrencinin hangi fakültede veya
  programda okuduğunu sor. Genel kural, bütün öğrencileri ya da bütün ön lisans ve lisans öğrencilerini kapsayan
  belgedeki kuraldır."""
_V7_CLARIFY_SYSTEM = _V7_SYSTEM.replace(_V7_GENERAL_RULE, _V7_CLARIFY_RULE)

# v5_birlestirme: v3'te "her kuralı kapsamıyla ayrı ayrı yaz" ile "aynı kuralı tekrar etme" çelişiyordu; model aynı kuralı
# her kapsam için ayrı yazıyordu (ör. lisans ve hukuk için aynı kredi iki satır). Kapsam maddesi kuralları önce
# karşılaştırmayı ve aynı olanları tek satırda birleştirmeyi tarif eder; ayrı birleştirme maddesi bu yüzden kalkar.
_V3_MERGE_RULE = "- Farklı belgeler aynı kuralı aynı şekilde veriyorsa tekrar etme; tek cevapta birleştir.\n"
_MERGE_SCOPE_RULE = """- Aynı soruya bağlamdaki belgeler farklı kapsamlar için kural veriyorsa yalnızca birini seçme. Önce kuralları
  karşılaştır: aynı olan kapsamları tek satırda birleştir ve kaynaklarını aynı köşeli parantezde ';' ile ayırarak yaz,
  ör. "X ve Y programları: <ortak kural> [Belge A, Madde N; Belge B, Madde M]". Kuralı farklı olan
  her kapsamı ayrı satırda, hangi kapsam için geçerli olduğunu söyleyerek yaz."""
assert _V3_MERGE_RULE in _V3_SYSTEM
_V5_MERGE_SYSTEM = _V3_SYSTEM.replace(_V3_SCOPE_RULE, _MERGE_SCOPE_RULE).replace(_V3_MERGE_RULE, "")


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
    "v4_netlestirme": {
        "template": ChatPromptTemplate.from_messages([
            ("system", _V4_SYSTEM),
            MessagesPlaceholder("history"),
            ("human", "{input}"),
        ]),
        "format": _format_v2,
        "history": True,
    },
    "v5_birlestirme": {
        "template": ChatPromptTemplate.from_messages([
            ("system", _V5_MERGE_SYSTEM),
            MessagesPlaceholder("history"),
            ("human", "{input}"),
        ]),
        "format": _format_v2,
        "history": True,
    },
    "v5_netlestirme_kisa": {
        "template": ChatPromptTemplate.from_messages([
            ("system", _V5_SYSTEM),
            MessagesPlaceholder("history"),
            ("human", "{input}"),
        ]),
        "format": _format_v2,
        "history": True,
    },
    "v6_netlestirme_durumlu": {
        "template": ChatPromptTemplate.from_messages([
            ("system", _V6_SYSTEM),
            MessagesPlaceholder("history"),
            ("human", "{input}"),
        ]),
        "format": _format_v2,
        "history": True,
    },
    "v7_kapsamsiz": {
        "template": ChatPromptTemplate.from_messages([
            ("system", _V7_SYSTEM),
            MessagesPlaceholder("history"),
            ("human", "{input}"),
        ]),
        "format": _format_v2,
        "history": True,
    },
    "v7_netlestirme": {
        "template": ChatPromptTemplate.from_messages([
            ("system", _V7_CLARIFY_SYSTEM),
            MessagesPlaceholder("history"),
            ("human", "{input}"),
        ]),
        "format": _format_v2,
        "history": True,
    },
}

# citation_style="fikra": atıf kuralı, madde metnindeki fıkra numarasını da istemek üzere değiştirilir (prompt sürümünden
# bağımsız; v3 tabanlı bütün prompt'larda aynı satır). Panelde fıkrayı vurgulayabilmek için (2026-10-08: 64 atıfın
# hiçbirinde fıkra yoktu). Örnek soyut tutulur: gerçek bir madde/fıkra soru setindeki bir cevabı ele verebilir.
_CITE_RULE = ("- Kullandığın her bilginin sonunda kaynağını köşeli parantezle belirt (bağlamdaki parça etiketlerinde yazan "
              "belge adı ve madde).")
_CITE_RULE_FIKRA = ("- Kullandığın her bilginin sonunda kaynağını köşeli parantezle belirt: bağlamdaki parça etiketinde yazan "
                    "belge adı, madde ve fıkra. Fıkra, madde metninde paragrafın başındaki parantez içindeki sayıdır (\"(2) ...\" ile "
                    "başlayan paragraf ikinci fıkradır). Atıfı [Belge adı, Madde N/F] biçiminde yaz (N madde, F fıkra "
                    "numarası). Bilgi birden fazla fıkradaysa hepsini yaz; madde metninde fıkra numarası yoksa yalnız maddeyi "
                    "yaz.")


def with_citation_style(template, style):
    """Sistem mesajındaki atıf kuralını citation_style'a göre değiştirilmiş yeni bir template döndürür."""
    if style == "madde":
        return template
    system = template.messages[0].prompt.template
    if _CITE_RULE not in system:
        raise ValueError("citation_style='fikra' yalnız v3 tabanlı prompt'larla kullanılabilir.")
    return ChatPromptTemplate.from_messages([("system", system.replace(_CITE_RULE, _CITE_RULE_FIKRA)),
                                             *template.messages[1:]])


RECITATION_HINT = ("\n\n(Cevabı belge metnini kelimesi kelimesine kopyalamadan, kendi cümlelerinle yaz; kaynak "
                   "atıflarını koru.)")
RECITATION_FALLBACK = ("Bu sorunun cevabı aşağıdaki kaynaklarda yer alıyor, ancak metin otomatik olarak aktarılamadı. "
                       "Lütfen kaynaklara bakın.")

# Yaz öğretimi yönetmeliği yürürlükten kalktı (corpus v4'ten çıkarıldı) ama staj yönergeleri, kimlik kartı yönergesi gibi
# belgelerde eski atıflar duruyor ve model bunlardan eskimiş cevaplar kuruyordu (EXP-023..027). "yaz dönemi" kapsanmaz:
# yazın yapılan staj soruları belgelerden cevaplanmaya devam eder.
SUMMER_PATTERN = re.compile(r"yaz\s*okul|yaz\s*öğretim")
SUMMER_ANSWER = (f"{config.NO_ANSWER} Yaz öğretimi (yaz okulu) yönetmeliği yürürlükten kaldırıldığı için yaz okulu "
                 "hakkında güncel bir bilgi veremiyorum. Güncel durum için Öğrenci İşleri Daire Başkanlığına başvurabilirsiniz.")

# fixed_answers="summer_staj_v1": staj kuralları her birimin kendi yönergesinde; herkesi kapsayan uygulamalı eğitimler
# yönergesi somut süre vermiyor ("en az 20 iş günü, bölüm kurulu belirler"). Birim belirtilmeyen staj sorusunda model
# bütün birimlerin yönergelerini sıralıyordu (v7 ve kapsam etiketli context ile de, 2026-10-17); kullanıcı kararıyla
# retrieval yapılmadan birim sorulur. Takip sorusunda rewrite birim adını sorguya kattığı için normal yol çalışır
# (turizm rehberliği: 30+30, mühendislik: 40 iş günü). Kalıp yeniden yazılmış sorguya uygulanır.
STAJ_PATTERN = re.compile(r"\bstaj")
UNIT_MENTION = re.compile(
    r"fakülte|yüksekokul|\bmyo\b|meslek yüksek|bölüm|program|enstitü|\btıp|\bdiş|hukuk|turizm|rehberli|otelcilik|"
    r"mühendis|mimarlık|ziraat|iibf|iktisadi|fizik tedavi|hemşire|eğitim fakülte|gerede|mengen|sağlık bilim|"
    r"spor bilim|güzel sanat|islami|ilahiyat|fen edebiyat|lisansüstü|yüksek lisans|doktora|ön ?lisans")
STAJ_ANSWER = ("Staj süresi ve kuralları fakülteden fakülteye, hatta bölümden bölüme değişiklik gösteriyor. Size doğru "
               "bilgi verebilmem için hangi fakültede veya bölümde okuduğunuzu söyleyebilir misiniz?")

REWRITE_SYSTEM = (
    "Sana bir sohbet geçmişi ve kullanıcının son sorusu verilecek. Son soruyu, geçmişi görmeden de "
    "anlaşılabilecek bağımsız bir soru olarak yeniden yaz (ör. 'peki bunun son günü ne?' -> "
    "'Bahar dönemi ders kayıtlarının son günü ne?'). Soruyu cevaplama; sadece yeniden yazılmış soruyu "
    "döndür. Soru zaten bağımsızsa aynen döndür."
)


def _to_messages(history):
    """{"role": "user"|"assistant", "content": ...} listesini LangChain mesajlarına çevirir (son HISTORY_MESSAGES)."""
    kinds = {"user": HumanMessage, "assistant": AIMessage}
    return [kinds[m["role"]](m["content"]) for m in (history or [])][-config.HISTORY_MESSAGES:]


def token_usage(metadata):
    """Cevap üretiminin token sayıları (RECITATION tekrarı varsa iki çağrının toplamı).

    reasoning: modelin cevaptan önce ürettiği "thinking" token'ları; API raporlamazsa 0. Latency'nin neden değiştiğini
    ayırmak için (daha uzun cevap mı, düşünme mi, yavaş üretim mi).
    """
    out = {"input": 0, "output": 0, "reasoning": 0}
    for m in metadata:
        if not m:
            continue
        out["input"] += m.get("input_tokens", 0)
        out["output"] += m.get("output_tokens", 0)
        out["reasoning"] += (m.get("output_token_details") or {}).get("reasoning", 0)
    return out


class RagBot:
    """Stateless: sohbet geçmişini kendisi tutmaz, her çağrıda dışarıdan alır.

    Böylece aynı bot (ve GPU'daki modeller) birden fazla oturum arasında paylaşılabilir; geçmişi
    çağıran taraf tutar (chat.py'de bir liste, API'de istemci). Geçmiş biçimi:
    [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}, ...]
    """

    def __init__(self, cfg, retriever, llm):
        self.cfg = cfg
        self.retriever = retriever
        self.llm = llm
        self.prompt = PROMPTS[cfg.prompt_version]
        self.template = with_citation_style(self.prompt["template"], cfg.citation_style)
        self.clarify_template = (with_citation_style(PROMPTS[cfg.clarify_prompt]["template"], cfg.citation_style)
                                 if cfg.clarify_trigger else None)
        self.scope_labels = {}  # belge -> kapsam etiketi (yalnız clarify_trigger açıksa)
        if cfg.clarify_trigger:
            self.scope_labels = {src: v.get("kapsam") for src, v in json.loads(
                SCOPE_FILES["parallel_v1"].read_text(encoding="utf-8"))["belgeler"].items()}
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

    def needs_clarification(self, query, docs):
        """Netleştirme kararını LLM yerine belge etiketleri verir (EXP-025: LLM'e bırakınca soruların %45'inde soruyordu).

        Context'te en az iki farklı paralel kapsamın (genel, tıp, diş, hukuk, lisansüstü) belgesi varsa konu birden fazla
        yönetmelikte ayrı düzenleniyor demektir; soru bir kapsamı adıyla anıyorsa sormaya gerek yoktur.
        """
        if not self.cfg.clarify_trigger or SCOPE_MENTION.search(query):
            return False
        scopes = {self.scope_labels.get(d.metadata["source"]) for d in docs}
        return len(scopes & set(PARALLEL_SCOPES)) >= 2

    def rewrite(self, question, history=None):
        """Geçmiş varsa (ve prompt geçmiş kullanıyorsa) soruyu bağımsız hale getirir; yoksa aynen döndürür."""
        messages = _to_messages(history)
        if messages and self.prompt["history"]:
            return self.rewrite_chain.invoke({"history": messages, "question": question}).text.strip()
        return question

    def fixed_answer(self, query):
        """Belgelerden cevaplanmaması gereken konular için sabit cevap; yoksa None."""
        text = tr_lower(query)
        if self.cfg.fixed_answers and SUMMER_PATTERN.search(text):
            return SUMMER_ANSWER
        if self.cfg.fixed_answers == "summer_staj_v1" and STAJ_PATTERN.search(text) and not UNIT_MENTION.search(text):
            return STAJ_ANSWER
        return None

    def retrieve(self, question, history=None):
        """Geçmiş varsa soruyu bağımsız hale getirip ilgili parçaları döndürür."""
        query = self.rewrite(question, history)
        return query, self.retriever.search(query)

    def ask(self, question, history=None):
        """Cevap üretir; geçmişi güncellemez (yeni soru-cevabı geçmişe eklemek çağıranın işi)."""
        query = self.rewrite(question, history)
        fixed = self.fixed_answer(query)
        if fixed:
            return {"answer": fixed, "query": query, "docs": [], "generation_ms": 0.0, "clarify": False}
        docs = self.retriever.search(query)
        variables = {"input": question, "context": self.prompt["format"](docs)}
        if self.prompt["history"]:
            variables.update({
                "history": _to_messages(history),
                "no_answer": config.NO_ANSWER,
                "today": date.today().strftime("%d.%m.%Y"),
            })
        clarify = self.needs_clarification(query, docs)
        template = self.clarify_template if clarify else self.template
        chain = template | self.llm
        started = time.perf_counter()  # yalnız cevap üretimi: retrieval ve rewrite hariç
        message = chain.invoke(variables)
        usage = [message.usage_metadata]
        answer = message.text.strip()
        if not answer and message.response_metadata.get("finish_reason") == "RECITATION":
            # Gemini, cevabın bir metni (ör. yönetmelik maddesini) kelimesi kelimesine tekrar edeceğini düşününce
            # çıktıyı engelleyip boş döndürüyor (EXP-023: kısmi zamanlı ücret soruları). Bir kez kendi cümleleriyle
            # yazması istenir; yine boşsa kullanıcı boş cevap yerine kaynaklara yönlendirilir.
            message = chain.invoke({**variables, "input": question + RECITATION_HINT})
            usage.append(message.usage_metadata)
            answer = message.text.strip() or RECITATION_FALLBACK
        generation_ms = (time.perf_counter() - started) * 1000
        return {"answer": answer, "query": query, "docs": docs, "generation_ms": generation_ms,
                "clarify": clarify, "usage": token_usage(usage)}
