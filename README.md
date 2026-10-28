# mevzuat-rag

**Bolu Abant İzzet Baysal Üniversitesi (BAİBÜ) mevzuatı üzerinden soru cevaplayan, kaynak gösteren bir RAG chatbot.**

**Öne çıkanlar**
- 131 belge (129 yönetmelik, yönerge ve akademik takvim PDF'i + bir bölümün ders programı ve personel verisi), ~3.800
  chunk; mevzuat madde madde chunk'lanır.
- Hybrid retrieval (bge-m3 vector search + BM25, RRF ile birleştirme) ve cross-encoder reranker; cevapta belge ve madde
  atıfı, arayüzde tıklanınca açılan madde paneli.
- 51 kayıtlı deney: her biri tek parametre değiştirir, hipotez koşmadan önce yazılır, sonuç commit hash'iyle saklanır,
  değişim eşleştirilmiş testlerle (McNemar, Wilcoxon) sınanır.
- Öğrenci diliyle yazılmış, sistem ayarlanırken kullanılmayan validation setinde anlamca cevap doğruluğu 0,88; yanlış
  cevapların soru türüne ve hatanın oluştuğu katmana göre analizi ([Bilinen zayıflıklar](#bilinen-zayıflıklar)).

*In English:* mevzuat-rag is a retrieval-augmented chatbot that answers students' questions about the regulations of
Bolu Abant İzzet Baysal University (Turkey) and cites the exact document and article for every claim. It indexes 131
documents (~3,800 article-level chunks) and combines bge-m3 dense retrieval, BM25, reciprocal rank fusion and a
cross-encoder reranker before generating with Gemini; a FastAPI backend serves a web UI with clickable citations. Every
design decision is a logged, single-variable experiment (51 so far) with paired significance tests, and the system scores
0.88 semantic answer accuracy on a held-out validation set written in students' own words, with a published error
analysis by question type.

Öğrenciler "Yatay geçiş başvurusu için not ortalamam kaç olmalı?", "Kaç dersten devamsızlık hakkım var?" ya da
"Bahar dönemi final sınavları ne zaman?" gibi sorular sorar. Chatbot cevabı üniversitenin yönetmelik, yönerge ve akademik
takvim belgelerinden bulur ve her bilginin yanında belgeyi ve madde numarasını verir
(ör. `[BAİBÜ Yatay Geçiş Yönergesi, Madde 8]`). Hedef davranış, cevap belgelerde yoksa uydurmak yerine "Bu konuda bilgim
yok." demesi; ölçülen sonuçlar ve sistemin hata yaptığı yerler [Bilinen zayıflıklar](#bilinen-zayıflıklar) bölümünde.

Sistemdeki her tasarım kararı, ölçülmüş ve tekrar üretilebilir bir **deney** olarak
kayıtlıdır (bkz. [Deneyler](#deneyler)).

---

## Özellikler

- **Kaynaklı cevap:** Her cevapta belge adı ve madde numarası yer alır. Arayüzde atıfa tıklayınca yan panelde ilgili madde açılır; oradan PDF'in ilgili sayfasına gidilebilir.
- **Çekimser kalma (hedef):** Bağlamda cevap yoksa "bilgim yok" der. Belgede olmayan konularda ölçülen 15/15; ama birden
  fazla şey soran sorularda bir kısmın maddesi context'e gelmeyince model o kısım için zaman zaman yanlış bilgi üretiyor.
- **Takip soruları:** "Peki bunun son günü ne?" gibi sorular, sohbet geçmişine bakılarak bağımsız bir soruya dönüştürülür
  ve öyle aranır (validation setinde 7/7).
- **Kapsam farkındalığı (hedef):** Aynı konu farklı fakültelerde farklı düzenlenmişse (ör. Tıp Fakültesinin ayrı
  yönetmeliği) genel kuralı verir ve öğrencinin fakültesini sorar. Validation setinde bu türde 9/12: genel kuralın maddesi
  context'e gelmeyince başka bir fakültenin kuralı genel kural gibi sunuluyor.
- **Web arayüzü:** sohbet ekranı, belge ve chunk tarayıcısı, cevapları etiketlemek için yönetici paneli.
- **REST API:** FastAPI ile; Swagger dokümantasyonu `/docs` adresinde.
- **Deney altyapısı:** retrieval ve cevap kalitesini ölçen değerlendirme koşucusu, istatistiksel testler
  (McNemar / Wilcoxon) ve otomatik üretilen deney günlüğü.

## Nasıl çalışır?

```mermaid
flowchart LR
    Q[Soru + sohbet geçmişi] --> RW[Rewrite<br/>bağımsız soru]
    RW --> FX{Sabit cevap?}
    FX -- evet --> A[Cevap]
    FX -- hayır --> V[Vector search<br/>bge-m3, 30 aday]
    RW --> B[BM25<br/>30 aday]
    V --> RRF[RRF birleştirme]
    B --> RRF
    RRF --> RR[Reranker<br/>bge-reranker-v2-m3]
    RR --> CTX[En iyi 5 chunk]
    CTX --> LLM[Gemini<br/>3.1-flash-lite]
    LLM --> A
```

**1. Belgelerin hazırlanması (`ingest.py`).** PDF'ler `pdfplumber` ile okunur. Mevzuat **madde madde** chunk'lara bölünür:
her chunk tek bir maddedir; çok uzun maddeler fıkra sınırından ikiye ayrılır. Akademik takvimde her tablo bir chunk olur.
Sabit boyutlu bölme yerine yapısal bölmenin seçilme nedeni, bir maddenin yarısının bir chunk'ta yarısının ötekinde
kalmasını önlemektir. Chunk'lar `BAAI/bge-m3` ile embedding'e çevrilip FAISS index'ine yazılır. Index, kendisini etkileyen
parametrelerin (belge kümesi, chunking, embedding modeli...) **fingerprint**'iyle adlandırılır; belge başına cache
sayesinde yalnız değişen belgeler yeniden işlenir.

**2. Retrieval (`rag.py`).** Soru iki yoldan aranır:
- **Vector search** anlam benzerliğini yakalar ("okuldan ayrılmak" ↔ "kayıt sildirme").
- **BM25** kelime eşleşmesini yakalar (madde numaraları, "AKTS", "GNO" gibi terimler). Türkçe eklemeli bir dil olduğu
  için kelimelerin ilk 5 harfi alınarak basit bir kök bulma yapılır.

İki liste **Reciprocal Rank Fusion (RRF)** ile birleştirilir. İlk 30 aday bir **cross-encoder reranker**
(`BAAI/bge-reranker-v2-m3`) ile soruyla birlikte okunup yeniden sıralanır ve en iyi 5 chunk modele bağlam olarak verilir.

**3. Cevap üretimi.** Gemini, system prompt'taki kurallarla yalnız bağlamdaki bilgiyi kullanarak, kaynak göstererek cevap
yazar. Yürürlükten kalkmış konular (ör. yaz okulu) için retrieval yapılmadan sabit bir cevap döner. Bağlamda aynı konuyu
farklı fakülteler için düzenleyen belgeler varsa (belge kapsam etiketleri `data/belge_kapsam_v1.json`), netleştirme
prompt'u kullanılır: genel kural verilir ve öğrencinin fakültesi sorulur.

## Kurulum

Gereksinimler: Python 3.11, bir [Gemini API anahtarı](https://aistudio.google.com/apikey). Production yapılandırması
NVIDIA GPU (CUDA) kullanır; GPU yoksa aşağıdaki [CPU notu](#gpu-olmadan-çalıştırma)na bakın.

```bash
git clone https://github.com/ariftahab/mevzuat-rag.git
cd mevzuat-rag
python -m venv venv
venv\Scripts\activate                    # Windows  (Linux/macOS: source venv/bin/activate)

# GPU için torch'u önce CUDA build'iyle kurun, yoksa pip CPU sürümünü indirir:
pip install torch==2.9.0 --index-url https://download.pytorch.org/whl/cu128
pip install -r requirements.txt
```

Proje köküne bir `.env` dosyası oluşturun:

```
GOOGLE_API_KEY=...
# İsteğe bağlı: yönetici paneli (/admin). Tanımlı değilse panel kapalıdır.
ADMIN_USER=admin
ADMIN_PASSWORD=...
```

İlk çalıştırmada embedding ve reranker modelleri (~6.5 GB) Hugging Face'ten indirilir ve index kurulur (GPU'da birkaç
dakika). Sonraki açılışlar index'i diskten okur.

## Kullanım

### Web arayüzü ve API

```bash
python -m uvicorn app.main:app --port 8000
```

| Adres | İçerik |
|---|---|
| http://localhost:8000/ | Sohbet ekranı |
| http://localhost:8000/belgeler | Belgeler ve chunk'ları; atıflardan buraya gelinir |
| http://localhost:8000/admin | Yönetici paneli: kullanıcı sorularını ve cevapları görme, doğru/yanlış etiketleme |
| http://localhost:8000/docs | API dokümantasyonu (Swagger) |

Başlıca API uçları: `POST /ask` (soru sor), `POST /feedback` (cevabı beğen/beğenme), `GET /documents`,
`GET /documents/{source}/chunks`, `GET /files/{source}` (PDF), `GET /health`.

```bash
curl -X POST http://localhost:8000/ask -H "Content-Type: application/json" \
     -d '{"question": "Yatay geçiş başvurusu için not ortalaması kaç olmalı?", "history": []}'
```

Sohbet kayıtları `logs/` altına JSONL olarak yazılır ve repoya girmez (kullanıcı soruları kişisel veri sayılır).

### Terminal sohbeti

```bash
python chat.py          # 'yeni' geçmişi temizler, 'çık' ile çıkılır
```

### GPU olmadan çalıştırma

Hangi parametrelerle çalışılacağını `config.PRODUCTION_EXPERIMENT` belirler (şu an `EXP-044`). CPU'da çalıştırmak için
bu config'i kopyalayıp `device` değerini `"cpu"`, `reranker_dtype` değerini `"fp32"` yapın ve `PRODUCTION_EXPERIMENT`'i
yeni config'e çevirin. CPU'da retrieval saniyeler mertebesinde sürer.

## Proje yapısı

```
config.py            yollar, belge kümeleri (CORPORA), RagConfig (bütün RAG parametreleri), PRODUCTION_EXPERIMENT
ingest.py            PDF okuma, chunking, embedding, FAISS index + belge bazında cache
rag.py               Retriever (vector / BM25 / hybrid + reranker), prompt sürümleri, RagBot
chat.py              terminal sohbeti
app/                 FastAPI (api.py), iş mantığı ve log'lar (service.py), arayüz (static/)
data/                PDF'ler, belge kümesi listeleri (corpus_v*.txt), belge kapsam etiketleri
eval/                soru setleri (soru, beklenen kaynak madde, kanıt cümlesi, beklenen cevap)
experiments/         configs/ (deney tanımları), results/ (sonuçlar), run.py, evaluation.py, report.py,
                     experiment_log.md (otomatik üretilir)
```

## Deneyler

RAG hattındaki her değişiklik (PDF okuyucu, chunking, embedding, retrieval yöntemi, reranker, prompt, LLM) bir deney
olarak yapılır:

- Her deney `experiments/configs/EXP-XXX.json` dosyasında tanımlıdır ve üst deneyden **tek bir parametre** farklıdır.
- Neden, hipotez, birincil metrik ve beklenen yön deney koşulmadan önce yazılır.
- Sonuç dosyası, deneyin koşulduğu **commit hash**'ini kaydeder; böylece her sonuç tekrar üretilebilir.
- Aynı sorular üzerinde eşleştirilmiş testler (McNemar, Wilcoxon) ile değişimin anlamlı olup olmadığına bakılır.

**Değerlendirme.** Bir chunk, beklenen kaynak belgeye aitse ve o belgede birebir geçen kanıt cümlesini içeriyorsa ilgili
(relevant) sayılır. Retrieval için MRR@10, Hit@k ve bağlam isabeti; cevaplar için anlamca değerlendirilen cevap doğruluğu,
netleştirme isabeti ve atıf metrikleri ölçülür.

**Yapıyı değiştiren ana deneyler** (her satır, üst deneyine göre ölçülen etki; soru seti ve corpus deneyler boyunca
büyüdüğü için satırlar arasında sayı karşılaştırılmaz):

| Deney | Değişiklik | Etkisi |
|---|---|---|
| EXP-002 | Sabit boyutlu chunking → madde madde (yapısal) chunking | Bağlam isabeti 0,78 → 1,00: doğru chunk her soruda LLM'e ulaştı |
| EXP-004 | Embedding: MiniLM → bge-m3 | En büyük kazanç: MRR@10 +0,27 |
| EXP-007 / EXP-008 | Hybrid retrieval (BM25 + RRF) ve reranker (bge-reranker-v2-m3) | 3 belgede doğru chunk her soruda 1. sırada |
| EXP-014 | Donanım: CPU → GPU | Retrieval latency 5,4 sn → 0,37 sn, sıralama aynı |
| EXP-015 | Corpus: 3 belge → 139 belge (bütün mevzuat) | MRR@10 1,00 → 0,86; reranker düşüşü sınırladı (RRF 0,59 → 0,86) |
| EXP-021 | Reranker'a giden aday 8 → 30 | Doğru chunk'ın reranker'a ulaşma oranı 0,958 → 0,986 |
| EXP-022 | Reranker fp32 → fp16 | Sıralama birebir aynı, latency 1372 → 363 ms |

**Güncel sistem:**

| Soru seti | MRR@10 | Hit@1 | Hit@5 | Cevap doğruluğu |
|---|---|---|---|---|
| Set 4.2 (149 soru): geliştirme sırasında kullanılan set; prompt ve eşik kararları buna göre verildi | 0.830 | 0.748 | 0.953 | 0.953 |
| Validation 2.0 (111 soru): öğrenci diliyle yazıldı, sistem bu sete göre ayarlanmadan önce ölçüldü | 0.749 | 0.659 | 0.898 | **0.88** (anlamca) |

Gerçek kullanıma yakın sayı validation satırıdır. Kilitli test seti (115 soru) bütün ayarlar bitince bir kez koşulacak ve
üçüncü satır olarak eklenecek. Retrieval latency GPU'da ~410 ms.

Bütün deneyler (reddedilenler dahil), hipotezler ve yorumlar: [`experiments/experiment_log.md`](experiments/experiment_log.md).

```bash
python -m experiments.run EXP-037          # retrieval metrikleri (API çağrısı yok)
python -m experiments.run EXP-037 --llm    # cevap kalitesini de ölç (Gemini kotası harcar, soru başına ~1 istek)
python -m experiments.report               # deney günlüğünü yeniden üret
```

**Yeni deney eklemek için:** bir config'i kopyalayıp yeni kimlik verin, `ust_deney` alanını karşılaştırılacak deney yapın
ve `params` içinde yalnız bir parametreyi değiştirin. `neden`, `hipotez`, `birincil_metrik` ve `beklenen_yon` alanlarını
doldurun, kodu commit'leyin, sonra deneyi koşun.

## Belgeler

`data/` klasöründeki PDF'ler üniversitenin kamuya açık mevzuatıdır (yönetmelikler, yönergeler, akademik takvim).
Güncel belge kümesi (`config.CORPORA`, `data/corpus_v5.txt`) 129 PDF'e ek olarak Bilgisayar Mühendisliği'nin 2026-2027
güz ders programını ve akademik personel listesini (JSON, her ders ve her kişi bir chunk) içerir.
Hangi belgelerin index'e girdiğini belge kümesi belirler.
Yeni bir belge eklemek için PDF'i `data/`'ya koyup yeni bir belge kümesi tanımlayın; index kendiliğinden yeniden kurulur.
Eski deneyler eski belge kümesiyle ölçüldüğü için yeni kümeyle yapılan ölçümlerle karşılaştırılamaz.

## Bilinen zayıflıklar

Öğrenci diliyle yazılmış validation setinde (111 soru) anlamca doğruluk 0,88. Sistemin hata yaptığı soru türleri:

**Tek belgede birden fazla madde gerektiren sorular (7/12).** Öğrenci tek mesajda iki şey soruyor ve cevaplar aynı
belgenin farklı maddelerinde ("staj yerimi değiştirirsem kaç gün önce söylemeliyim, raporu ne zaman teslim edeceğim?").
Soru tek bir embedding'e çevrildiği için ikinci maddenin chunk'ı context'e girmiyor; model o kısma "belgede
belirtilmemiş" diyor, bazen de yanlış bilgi uyduruyor.

**Fakülteye göre değişen kurallar (9/12).** Fakülte belirtilmeyen soruda genel kuralı verip fakülteyi sorması gerekiyor
("DC alırsam geçer miyim?"). Genel yönetmelik kuralı tabloyla ya da başka bir terimle (ders yerine AKTS) yazdığı için
reranker onu, kuralı cümleyle yazan fakülte yönetmeliğinin altına itiyor; model o fakültenin kuralını genel kural gibi
sunuyor.

**Yazım hatalı ya da Türkçe karakter kullanılmadan yazılmış sorular (8/10).** "hazirlikta derslerin yuzde kacina"
gibi sorularda doğru chunk aday listesine hiç girmiyor; model "bilgim yok" diyor ya da yanlış belgeden cevap veriyor.
BM25'te Türkçe karakter katlama (ı→i, ü→u ...) bu sorunu kısmen çözüyor: "yuzde" ile "yüzde" eşleşince doğru chunk
RRF'de 47. sıradan 8.'ye çıkıyor, ama reranker onu 11. sıraya itiyor ve context'e yine giremiyor (EXP-050: final sıralama
değişmedi). Yanlış cevaplanan diğer yazım hatalı soruda ("hazırlıkta güz dönemi dersler ne zmn bitiyo") sorun yazım
değil kelime farkı: öğrenci "bitiyor" diyor, akademik takvim "sona ermesi" diyor; soruda "güz" ve "dersler" geçtiği için
context'i Bilgisayar Mühendisliği'nin güz ders programı dolduruyor.

**Birden fazla belge gerektiren sorular (2/3).** İki ayrı yönetmeliği birleştirmesi gereken sorularda belgelerden biri
context'e gelmiyor.

**Örtük çıkarım gerektiren sorular.** Doğru madde context'te olsa da model iki bilgiyi birleştiremiyor: yönerge "uyarı
cezası hariç disiplin cezası alanın bursu kesilir" diyor, öğrenci "kınama aldım, bursum kesilir mi?" diye soruyor; model
kınamanın bu kapsama girdiğini çıkaramayıp "kesilmez" diyor.

**Konu dışı sorular.** Reddediliyor, ama yalnız "Bu konuda bilgim yok." deniyor; asistanın BAİBÜ mevzuatı için olduğu
söylenmiyor.

Yanlış cevapların 21'inden 19'unda sorun retrieval'da (doğru chunk ilk 5'in dışında ya da aday listesinde yok), 2'sinde
modelin çıkarımında. Soru soru ayrıntı: [`experiments/hata_analizi_2026-10-28.md`](experiments/hata_analizi_2026-10-28.md).

## Sınırlamalar

- Chatbot yalnız index'teki belgeleri bilir; duyurular ve birim web sayfaları kapsam dışıdır. Ders programı ve akademik
  personel verisi yalnız Bilgisayar Mühendisliği (2026-2027 güz) için var; diğer bölümlerin ders programları yok.
- Belgeler güncellendiğinde cevaplar da ancak PDF'ler yenilenip index yeniden kurulunca güncellenir.
- Cevaplar resmî görüş değildir; kesin bilgi için ilgili birime başvurulmalıdır.

## Kullanılan teknolojiler

Python 3.11 · LangChain · FAISS · sentence-transformers (bge-m3, bge-reranker-v2-m3) · rank-bm25 · pdfplumber ·
Google Gemini · FastAPI · vanilla JavaScript

## Lisans

Kod [MIT](LICENSE) lisansıyla dağıtılır. `data/` klasöründeki PDF'ler Bolu Abant İzzet Baysal Üniversitesine aittir ve
lisansın kapsamında değildir.
