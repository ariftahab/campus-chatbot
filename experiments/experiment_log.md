# Deney Günlüğü

> Bu dosya `python -m experiments.report` ile **otomatik üretilir**; elle düzenlemeyin.
> Gerekçe/hipotez/yorumlar `experiments/configs/EXP-*.json`, sayılar `experiments/results/EXP-*.json` içindedir.
> Sohbet uygulamasının kullandığı yapılandırma: **EXP-010** (`config.PRODUCTION_EXPERIMENT`).

## 1. Protokol

**Değerlendirme seti.** `eval/sorular.json`, sürüm 2.0 (SHA-256 ilk 16: `fbab400da1f4cc72`).
30 soru: 27 tanesi belgelerde cevabı olan soru (getirme ve cevap değerlendirmesinde kullanılır),
3 tanesi kapsam dışı soru (yalnız cevap değerlendirmesinde). Tüm deneyler aynı set üzerinde koşulur;
set değişirse eski sonuçlarla karşılaştırma geçersiz sayılır ve günlükte işaretlenir.

**İlgililik.** Her soru için kaynak PDF ve kaynakta birebir geçen kısa bir *kanıt* ifadesi tanımlıdır (takvimde tarih ve
etkinlik birlikte). Bir parça; kaynak dosyası tutuyorsa ve kanıtı içeriyorsa ilgili sayılır. Karşılaştırmada Türkçe küçük
harfe çevrilir ve harf/rakam dışındaki her şey (boşluk, satır sonu, noktalama) yok sayılır. Bu sayede ölçüt **parçalama
yönteminden ve PDF okuyucudan bağımsızdır**. Koşucu, her kanıtın iki PDF okuyucusunun (pypdf, pdfplumber) ham metninde de
geçtiğini deney öncesinde doğrular.

**Metrikler** (soru başına hesaplanır, ortalaması raporlanır):

| Metrik | Tanım |
|---|---|
| MRR@10 | 1 / ilk ilgili parçanın sırası (ilk 10'da yoksa 0) |
| Hit@k | İlk k parçada ilgili parça var mı (k = 1, 3, 5, 10) |
| Bağlam isabeti | LLM'e verilen ilk `final_k` parçada ilgili parça var mı |
| Bağlam uzunluğu | LLM'e verilen bağlamın karakter sayısı (maliyet/gecikme göstergesi) |
| Getirme gecikmesi | Sorgu başına getirme süresi, LLM hariç (ms; donanıma bağlıdır) |
| Cevap doğruluğu | LLM cevabı beklenen anahtar kelimeleri içeriyor mu; kapsam dışı sorularda "Bu konuda bilgim yok." (`--llm` ile) |

**Tek değişken ilkesi.** Her deney bir *üst deneyden* türetilir ve ondan yalnız bir parametre farklıdır; koşucu bunu
denetler. Birden fazla parametrenin birlikte değişmesi gerekiyorsa gerekçe (`coklu_degisiklik_gerekcesi`) zorunludur.
Bazı parametreler bazı yapılandırmalarda etkisizdir (ör. `reranker_model` `None` iken `rerank_candidates`); bunlar
tüm deneylerde sabit tutulur ki farklar yalnız gerçek değişikliği göstersin.

**Karar kuralı** (deney koşulmadan önce belirlenir). Her deneyin bir *birincil metriği* ve *beklenen yönü* vardır.
Üst deneyle aynı sorular üzerinde eşleştirilmiş test yapılır: ikili metriklerde kesin McNemar testi, sürekli
metriklerde Wilcoxon işaretli sıra testi, α = 0,05.
- *Değişim yok*: fark 0.
- *Anlamlı iyileşme/kötüleşme*: fark ≠ 0 ve p < 0,05.
- *Sayısal iyileşme/kötüleşme (anlamlı değil)*: fark ≠ 0 ve p ≥ 0,05.
- Hipotez: gözlenen yön beklenenle aynı ve anlamlıysa *Doğrulandı*; yön aynı ama anlamlı değilse *Yön doğru, anlamlı değil*;
  aksi halde *Doğrulanmadı*. Beklenen sonucun çıkmaması da bir sonuç olarak kaydedilir.

**Tekrar üretme.** Her sonuç dosyası git commit'ini, commit edilmemiş değişiklik olup olmadığını, paket sürümlerini,
Hugging Face model revizyonlarını, donanımı ve indeks parmak izini içerir:

```
git checkout <commit>
python -m experiments.run EXP-XXX --yeniden
```

**Geçerlilik sınırları.** (1) Set küçüktür (27 soru): bir sorunun değişmesi Hit@k'yı 3.7 puan oynatır;
bu yüzden anlamlılık testleri tutucudur ve çoğu fark anlamlı çıkmayabilir. (2) Yapılandırma seçimleri aynı set üzerinde
yapıldığı için sonuçlar iyimser olabilir; tez için ayrı bir test seti ile son doğrulama önerilir. (3) Gecikme ölçümleri
yalnız aynı makinedeki deneyler arasında karşılaştırılabilir. (4) Gemini ücretsiz kotası (günlük 20 istek) nedeniyle cevap
doğruluğu ölçümleri ayrı günlerde yapılabilir.

## 2. Özet

| Deney | Üst | Değişiklik | MRR@10 | Hit@1 | Hit@3 | Hit@5 | Bağlam isabeti | Bağlam (kar.) | Gecikme (ms) | Cevap doğr. | Karar (birincil metrik) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| EXP-000 | – | İlk prototip (referans) | 0,564 | 0,444 | 0,630 | 0,741 | 0,815 | 9.223 | 22 | – | Referans |
| EXP-001 | EXP-000 | PDF okuyucu: pypdf → pdfplumber | 0,584 | 0,481 | 0,667 | 0,667 | 0,778 | 9.278 | 21 | – | MRR@10: Sayısal iyileşme (istatistiksel olarak anlamlı değil) |
| EXP-002 | EXP-001 | Parçalama: sabit boyut → yapısal (madde / takvim tablosu) | 0,716 | 0,556 | 0,852 | 0,889 | 1,000 | 8.436 | 21 | – | MRR@10: Sayısal iyileşme (istatistiksel olarak anlamlı değil) |
| EXP-003 | EXP-002 | Embedding normalizasyonu: kapalı → açık (kosinüs) | 0,654 | 0,444 | 0,815 | 0,926 | 1,000 | 8.095 | 21 | – | MRR@10: Sayısal kötüleşme (istatistiksel olarak anlamlı değil) |
| EXP-004 | EXP-003 | Embedding modeli: MiniLM → bge-m3 | 0,920 | 0,852 | 1,000 | 1,000 | 1,000 | 8.708 | 83 | – | MRR@10: Anlamlı iyileşme (p<0,05) |
| EXP-005 | EXP-004 | Yapısal bölme eşiği: 1000 → 1500 karakter | 0,938 | 0,889 | 1,000 | 1,000 | 1,000 | 10.835 | 79 | – | MRR@10: Sayısal iyileşme (istatistiksel olarak anlamlı değil) |
| EXP-006 | EXP-005 | Yapısal bölmede overlap: 200 → 150 karakter | 0,938 | 0,889 | 1,000 | 1,000 | 1,000 | 10.793 | 73 | – | MRR@10: Değişim yok |
| EXP-007 | EXP-006 | Getirme: yalnız vektör → hibrit (vektör + BM25, RRF) | 0,938 | 0,889 | 1,000 | 1,000 | 1,000 | 10.678 | 78 | – | MRR@10: Ortalamada değişim yok (bazı sorularda sıra değişti) |
| EXP-008 | EXP-007 | Reranker: yok → bge-reranker-v2-m3 | 1,000 | 1,000 | 1,000 | 1,000 | 1,000 | 10.678 | 4.724 | – | MRR@10: Sayısal iyileşme (istatistiksel olarak anlamlı değil) |
| EXP-009 | EXP-008 | LLM'e giden parça sayısı: 10 → 5 | 1,000 | 1,000 | 1,000 | 1,000 | 1,000 | 5.448 | 5.340 | – | Bağlam uzunluğu (karakter): Anlamlı iyileşme (p<0,05) |
| EXP-010 | EXP-009 | Prompt: prototip → kaynaklı system prompt (v2) | 1,000 | 1,000 | 1,000 | 1,000 | 1,000 | 5.448 | 5.408 | – | Cevap doğruluğu: Ölçülmedi |
| EXP-011 | EXP-004 | Takip: bge-m3 ile normalizasyon kapalı (EXP-003 kararının sınanması) | 0,920 | 0,852 | 1,000 | 1,000 | 1,000 | 8.708 | 90 | – | MRR@10: Değişim yok |
| EXP-012 | EXP-008 | Takip: reranker varken hibrit → yalnız vektör (EXP-007 kararının sınanması) | 1,000 | 1,000 | 1,000 | 1,000 | 1,000 | 10.793 | 5.526 | – | MRR@10: Değişim yok |

## 3. Deneyler

### EXP-000 — İlk prototip (referans)

- **Üst deney:** – (referans)
- **Koşulma:** 2026-09-29T18:57:15, commit `0a47d1d3b0`, veri seti 2.0 (`fbab400da1f4cc72`)

**Neden:** İlk çalışan sistem (main dalındaki prototip-chat.py) sonraki tüm deneylerin karşılaştırma noktasıdır. PyPDFLoader (pypdf) ile sayfa metni, RecursiveCharacterTextSplitter 1000/200, paraphrase-multilingual-MiniLM-L12-v2 embedding (normalize edilmemiş, FAISS L2), yalnız vektör araması, ilk 10 parça LLM'e, Gemini 2.5 Flash sıcaklık 0,3, prototipin prompt'u birebir. `vector_k`, `bm25_k`, `rrf_k`, `reranker_max_length`, `rerank_candidates` bu yapılandırmada etkisizdir; sonraki deneylerle aynı değerde sabit tutulur.

**Sonuçlar:**

| Metrik | Değer |
|---|---|
| MRR@10 | 0,564 |
| Hit@1 | 0,444 |
| Hit@3 | 0,630 |
| Hit@5 | 0,741 |
| Hit@10 | 0,815 |
| Bağlam isabeti | 0,815 |
| Bağlam uzunluğu (karakter) | 9.223 |
| Getirme gecikmesi (ms) | 22 |

**İlk 10'da ilgili parça bulunamayan sorular:** T07, K03, K07, K08, Y03

**Cevap değerlendirmesi:** bu koşuda yapılmadı (`--llm`).

**İndeks:** 68 parça, ortalama 902 karakter, kurulum 1.5 sn (parmak izi `8e778e2cda3abbce`). Medyan getirme gecikmesi 21 ms.

**Yorum:** 27 sorudan 5'inde (T07, K03, K07, K08, Y03) ilgili parça ilk 10'da yok; bu sorularda LLM'e cevabı içeren metin hiç ulaşmıyor (bağlam isabeti 0,815). Kanıtların hepsi en az bir parçada mevcut, yani kayıplar parçalamanın cevabı bölmesinden değil sıralamadan kaynaklanıyor. Önceki (madde numarasına dayalı) ölçüt prototipin bu zayıflığını gösteremiyordu.

<details><summary>Tüm parametreler</summary>

| Parametre | Değer |
|---|---|
| `pdf_parser` | `pypdf` |
| `chunking` | `recursive` |
| `chunk_size` | `1000` |
| `chunk_overlap` | `200` |
| `embedding_model` | `paraphrase-multilingual-MiniLM-L12-v2` |
| `normalize_embeddings` | `False` |
| `retrieval` | `vector` |
| `vector_k` | `15` |
| `bm25_k` | `15` |
| `rrf_k` | `60` |
| `reranker_model` | `None` |
| `reranker_max_length` | `512` |
| `rerank_candidates` | `8` |
| `final_k` | `10` |
| `llm_model` | `gemini-2.5-flash` |
| `llm_temperature` | `0.3` |
| `prompt_version` | `v1_prototip` |

</details>

### EXP-001 — PDF okuyucu: pypdf → pdfplumber

- **Üst deney:** EXP-000
- **Koşulma:** 2026-09-29T18:57:19, commit `0a47d1d3b0`, veri seti 2.0 (`fbab400da1f4cc72`)

**Değişen parametre(ler):**

| Parametre | Üst deney | Bu deney |
|---|---|---|
| `pdf_parser` | `pypdf` | `pdfplumber` |

**Neden:** pypdf bu PDF'lerde kelimelerin içine boşluk ekliyor ("ö ğretim", "ortala ması", "Yüksekö ğretim"). Bozuk kelimeler hem embedding'in hem de anahtar kelime aramasının kelimeyi tanımasını engeller. pdfplumber aynı sayfalarda temiz metin veriyor.

**Hipotez:** Daha temiz metin, sorgu ile ilgili parça arasındaki benzerliği artırır; MRR@10 artar. *(Birincil metrik: MRR@10, beklenen yön: artış)*

**Sonuçlar:**

| Metrik | Üst deney | Bu deney | Fark | Test | p |
|---|---|---|---|---|---|
| MRR@10 | 0,564 | 0,584 | +0,021 | Wilcoxon | 0,720 |
| Hit@1 | 0,444 | 0,481 | +0,037 | McNemar (kesin) (3↑ / 2↓ soru) | 1,000 |
| Hit@3 | 0,630 | 0,667 | +0,037 | McNemar (kesin) (2↑ / 1↓ soru) | 1,000 |
| Hit@5 | 0,741 | 0,667 | −0,074 | McNemar (kesin) (0↑ / 2↓ soru) | 0,500 |
| Hit@10 | 0,815 | 0,778 | −0,037 | McNemar (kesin) (1↑ / 2↓ soru) | 1,000 |
| Bağlam isabeti | 0,815 | 0,778 | −0,037 | McNemar (kesin) (1↑ / 2↓ soru) | 1,000 |
| Bağlam uzunluğu (karakter) | 9.223 | 9.278 | +55 | Wilcoxon | 0,086 |
| Getirme gecikmesi (ms) | 22 | 21 | −0 | Wilcoxon | 0,923 |

**Karar:** Sayısal iyileşme (istatistiksel olarak anlamlı değil) — birincil metrik MRR@10. **Hipotez:** Yön doğru, anlamlı değil.

**İlk ilgili parçanın sırası değişen sorular:** T03 (2→1), T04 (1→2), T09 (1→2), T10 (8→6), K03 (>10→9), Y01 (2→>10), Y04 (5→>10), Y05 (5→1), Y08 (5→1)

**İlk 10'da ilgili parça bulunamayan sorular:** T07, K07, K08, Y01, Y03, Y04

**Cevap değerlendirmesi:** bu koşuda yapılmadı (`--llm`).

**İndeks:** 68 parça, ortalama 893 karakter, kurulum 2.7 sn (parmak izi `6542795ac5c35316`). Medyan getirme gecikmesi 21 ms.

**Yorum:** MRR@10 0,564 → 0,584 (+0,020, Wilcoxon p=0,72): anlamlı değil. Değişim iki yönlü: Hit@1 arttı (0,444 → 0,481) ama Hit@5 (0,741 → 0,667) ve bağlam isabeti (0,815 → 0,778) düştü; 9 sorunun sırası değişti (Y01 ve Y04 ilk 10'dan çıktı, K03 girdi). Sonuç: metin temizliği tek başına sabit boyutlu parçalamada belirgin bir getirme kazancı sağlamadı; hipotez desteklenmedi. pdfplumber'ın asıl katkısı yapısal parçalamayı (tablo okuma) mümkün kılmasıdır; EXP-002 buna dayanır.

<details><summary>Tüm parametreler</summary>

| Parametre | Değer |
|---|---|
| `pdf_parser` | `pdfplumber` |
| `chunking` | `recursive` |
| `chunk_size` | `1000` |
| `chunk_overlap` | `200` |
| `embedding_model` | `paraphrase-multilingual-MiniLM-L12-v2` |
| `normalize_embeddings` | `False` |
| `retrieval` | `vector` |
| `vector_k` | `15` |
| `bm25_k` | `15` |
| `rrf_k` | `60` |
| `reranker_model` | `None` |
| `reranker_max_length` | `512` |
| `rerank_candidates` | `8` |
| `final_k` | `10` |
| `llm_model` | `gemini-2.5-flash` |
| `llm_temperature` | `0.3` |
| `prompt_version` | `v1_prototip` |

</details>

### EXP-002 — Parçalama: sabit boyut → yapısal (madde / takvim tablosu)

- **Üst deney:** EXP-001
- **Koşulma:** 2026-09-29T18:57:24, commit `0a47d1d3b0`, veri seti 2.0 (`fbab400da1f4cc72`)

**Değişen parametre(ler):**

| Parametre | Üst deney | Bu deney |
|---|---|---|
| `chunking` | `recursive` | `structural` |

**Neden:** Sabit 1000 karakterlik bölme, maddeleri ortasından keser ve bir parçaya birden fazla konunun parçalarını koyar; takvimde tarih ile etkinlik farklı parçalara düşebilir. Yapısal parçalamada her yönetmelik maddesi (başlığıyla) bir parçadır, eşiği aşan maddeler fıkra sınırlarından bölünür ve her parçaya "Belge - Madde N (başlık)" eklenir; takvimde her tablo (ör. Bahar Yarıyılı) bir parçadır. Bu deneyde eşik ve overlap prototipteki gibi 1000/200 bırakıldı.

**Hipotez:** Parçalar tek bir konuya odaklandığı için ilgili parça daha üst sıraya çıkar; MRR@10 artar. *(Birincil metrik: MRR@10, beklenen yön: artış)*

**Sonuçlar:**

| Metrik | Üst deney | Bu deney | Fark | Test | p |
|---|---|---|---|---|---|
| MRR@10 | 0,584 | 0,716 | +0,132 | Wilcoxon | 0,224 |
| Hit@1 | 0,481 | 0,556 | +0,074 | McNemar (kesin) (8↑ / 6↓ soru) | 0,791 |
| Hit@3 | 0,667 | 0,852 | +0,185 | McNemar (kesin) (8↑ / 3↓ soru) | 0,227 |
| Hit@5 | 0,667 | 0,889 | +0,222 | McNemar (kesin) (8↑ / 2↓ soru) | 0,109 |
| Hit@10 | 0,778 | 1,000 | +0,222 | McNemar (kesin) (6↑ / 0↓ soru) | 0,031 |
| Bağlam isabeti | 0,778 | 1,000 | +0,222 | McNemar (kesin) (6↑ / 0↓ soru) | 0,031 |
| Bağlam uzunluğu (karakter) | 9.278 | 8.436 | −842 | Wilcoxon | <0,001 |
| Getirme gecikmesi (ms) | 21 | 21 | −0 | Wilcoxon | 0,182 |

**Karar:** Sayısal iyileşme (istatistiksel olarak anlamlı değil) — birincil metrik MRR@10. **Hipotez:** Yön doğru, anlamlı değil.

**İlk ilgili parçanın sırası değişen sorular:** T01 (6→3), T02 (3→2), T03 (1→2), T06 (1→3), T07 (>10→1), T09 (2→1), T10 (6→7), K01 (1→7), K02 (2→1), K03 (9→1), K04 (1→8), K05 (1→4), K07 (>10→1), K08 (>10→1), Y01 (>10→1), Y03 (>10→2), Y04 (>10→2), Y07 (2→1), Y08 (1→2)

**Cevap değerlendirmesi:** bu koşuda yapılmadı (`--llm`).

**İndeks:** 90 parça, ortalama 676 karakter, kurulum 3.0 sn (parmak izi `0870e52bdcd2f502`). Medyan getirme gecikmesi 21 ms.

**Yorum:** MRR@10 0,584 → 0,716 (+0,132, p=0,22) anlamlı değil; ancak bağlam isabeti 0,778 → 1,000 ile anlamlı arttı (McNemar p=0,031). LLM'e giden 10 parçada artık her sorunun cevabı var; ilk 10'da bulunamayan soru sayısı 6'dan 0'a indi. Bazı sorular geriledi (K01 1→7, K04 1→8, K05 1→4). Olası açıklama: bu sorularda madde parçaları uzun ve MiniLM'nin 128 token sınırı parçanın sonunu görmüyor. Bu sorular EXP-004'te (bge-m3) düzeliyor, bu da açıklamayı destekliyor. Parça sayısı 68 → 90.

<details><summary>Tüm parametreler</summary>

| Parametre | Değer |
|---|---|
| `pdf_parser` | `pdfplumber` |
| `chunking` | `structural` |
| `chunk_size` | `1000` |
| `chunk_overlap` | `200` |
| `embedding_model` | `paraphrase-multilingual-MiniLM-L12-v2` |
| `normalize_embeddings` | `False` |
| `retrieval` | `vector` |
| `vector_k` | `15` |
| `bm25_k` | `15` |
| `rrf_k` | `60` |
| `reranker_model` | `None` |
| `reranker_max_length` | `512` |
| `rerank_candidates` | `8` |
| `final_k` | `10` |
| `llm_model` | `gemini-2.5-flash` |
| `llm_temperature` | `0.3` |
| `prompt_version` | `v1_prototip` |

</details>

### EXP-003 — Embedding normalizasyonu: kapalı → açık (kosinüs)

- **Üst deney:** EXP-002
- **Koşulma:** 2026-09-29T18:57:28, commit `0a47d1d3b0`, veri seti 2.0 (`fbab400da1f4cc72`)

**Değişen parametre(ler):**

| Parametre | Üst deney | Bu deney |
|---|---|---|
| `normalize_embeddings` | `False` | `True` |

**Neden:** Prototipte vektörler normalize edilmeden FAISS L2 uzaklığıyla aranıyordu. paraphrase-MiniLM ve bge-m3 kosinüs benzerliğiyle eğitilmiş modellerdir; L2 uzaklığı vektör uzunluğundan etkilenir. Bir sonraki deneyde embedding modeli değişeceği için normalizasyonun etkisi önce ayrı ölçülüyor.

**Hipotez:** Kosinüs benzerliği modelin eğitim hedefiyle uyumlu olduğu için MRR@10 artar. *(Birincil metrik: MRR@10, beklenen yön: artış)*

**Sonuçlar:**

| Metrik | Üst deney | Bu deney | Fark | Test | p |
|---|---|---|---|---|---|
| MRR@10 | 0,716 | 0,654 | −0,061 | Wilcoxon | 0,061 |
| Hit@1 | 0,556 | 0,444 | −0,111 | McNemar (kesin) (0↑ / 3↓ soru) | 0,250 |
| Hit@3 | 0,852 | 0,815 | −0,037 | McNemar (kesin) (0↑ / 1↓ soru) | 1,000 |
| Hit@5 | 0,889 | 0,926 | +0,037 | McNemar (kesin) (1↑ / 0↓ soru) | 1,000 |
| Hit@10 | 1,000 | 1,000 | 0 | McNemar (kesin) (0↑ / 0↓ soru) | 1,000 |
| Bağlam isabeti | 1,000 | 1,000 | 0 | McNemar (kesin) (0↑ / 0↓ soru) | 1,000 |
| Bağlam uzunluğu (karakter) | 8.436 | 8.095 | −342 | Wilcoxon | 0,010 |
| Getirme gecikmesi (ms) | 21 | 21 | +0 | Wilcoxon | 0,516 |

**Karar:** Sayısal kötüleşme (istatistiksel olarak anlamlı değil) — birincil metrik MRR@10. **Hipotez:** Doğrulanmadı.

**İlk ilgili parçanın sırası değişen sorular:** T06 (3→4), T08 (1→2), K01 (7→4), K04 (8→9), K07 (1→2), K09 (1→2), Y04 (2→3)

**Cevap değerlendirmesi:** bu koşuda yapılmadı (`--llm`).

**İndeks:** 90 parça, ortalama 676 karakter, kurulum 3.1 sn (parmak izi `329fd8e57b64da6d`). Medyan getirme gecikmesi 20 ms.

**Yorum:** Beklenenin tersi: MRR@10 0,716 → 0,654 (−0,062, Wilcoxon p=0,061), Hit@1 0,556 → 0,444; 7 soru geriledi, 0 soru iyileşti. Hipotez doğrulanmadı. Anlamlılık sınırına yakın bir kötüleşme: bu sette MiniLM için ham L2 sıralaması kosinüsten daha iyi. Olası (doğrulanmamış) açıklama: MiniLM'de normalizasyon katmanı yok ve vektör uzunluğu içerikle ilgili bilgi taşıyor olabilir. Normalizasyon yine de zincirde açık bırakıldı; EXP-011 bu kararın bge-m3 için bir etkisi olmadığını gösterdi.

<details><summary>Tüm parametreler</summary>

| Parametre | Değer |
|---|---|
| `pdf_parser` | `pdfplumber` |
| `chunking` | `structural` |
| `chunk_size` | `1000` |
| `chunk_overlap` | `200` |
| `embedding_model` | `paraphrase-multilingual-MiniLM-L12-v2` |
| `normalize_embeddings` | `True` |
| `retrieval` | `vector` |
| `vector_k` | `15` |
| `bm25_k` | `15` |
| `rrf_k` | `60` |
| `reranker_model` | `None` |
| `reranker_max_length` | `512` |
| `rerank_candidates` | `8` |
| `final_k` | `10` |
| `llm_model` | `gemini-2.5-flash` |
| `llm_temperature` | `0.3` |
| `prompt_version` | `v1_prototip` |

</details>

### EXP-004 — Embedding modeli: MiniLM → bge-m3

- **Üst deney:** EXP-003
- **Koşulma:** 2026-09-29T18:57:35, commit `0a47d1d3b0`, veri seti 2.0 (`fbab400da1f4cc72`)

**Değişen parametre(ler):**

| Parametre | Üst deney | Bu deney |
|---|---|---|
| `embedding_model` | `paraphrase-multilingual-MiniLM-L12-v2` | `BAAI/bge-m3` |

**Neden:** paraphrase-multilingual-MiniLM-L12-v2 en fazla 128 token okuyor; 1000 karakterlik Türkçe bir parça bu sınırı aşar ve parçanın sonu embedding'e hiç girmez. BAAI/bge-m3 çok dilli, Türkçe'de daha güçlü ve 8192 token okuyabiliyor. Karşılığında model daha büyük (568M parametre) ve embedding daha yavaş.

**Hipotez:** Parçanın tamamı temsil edildiği ve model daha güçlü olduğu için MRR@10 artar. *(Birincil metrik: MRR@10, beklenen yön: artış)*

**Sonuçlar:**

| Metrik | Üst deney | Bu deney | Fark | Test | p |
|---|---|---|---|---|---|
| MRR@10 | 0,654 | 0,920 | +0,265 | Wilcoxon | 0,002 |
| Hit@1 | 0,444 | 0,852 | +0,407 | McNemar (kesin) (12↑ / 1↓ soru) | 0,003 |
| Hit@3 | 0,815 | 1,000 | +0,185 | McNemar (kesin) (5↑ / 0↓ soru) | 0,062 |
| Hit@5 | 0,926 | 1,000 | +0,074 | McNemar (kesin) (2↑ / 0↓ soru) | 0,500 |
| Hit@10 | 1,000 | 1,000 | 0 | McNemar (kesin) (0↑ / 0↓ soru) | 1,000 |
| Bağlam isabeti | 1,000 | 1,000 | 0 | McNemar (kesin) (0↑ / 0↓ soru) | 1,000 |
| Bağlam uzunluğu (karakter) | 8.095 | 8.708 | +614 | Wilcoxon | 0,002 |
| Getirme gecikmesi (ms) | 21 | 83 | +62 | Wilcoxon | <0,001 |

**Karar:** Anlamlı iyileşme (p<0,05) — birincil metrik MRR@10. **Hipotez:** Doğrulandı.

**İlk ilgili parçanın sırası değişen sorular:** T01 (3→1), T02 (2→1), T03 (2→1), T04 (2→1), T06 (4→1), T08 (2→1), T10 (7→3), K01 (4→2), K04 (9→1), K05 (4→1), K07 (2→1), K09 (2→1), Y03 (2→1), Y04 (3→2), Y07 (1→2), Y08 (2→1)

**Cevap değerlendirmesi:** bu koşuda yapılmadı (`--llm`).

**İndeks:** 90 parça, ortalama 676 karakter, kurulum 41.7 sn (parmak izi `8770086a3458fcce`). Medyan getirme gecikmesi 81 ms.

**Yorum:** Zincirdeki en büyük ve anlamlı tek kazanç: MRR@10 0,654 → 0,920 (+0,266, Wilcoxon p=0,0015), Hit@1 0,444 → 0,852 (McNemar p=0,003), Hit@3 ve Hit@5 1,000. 16 soru iyileşti, 1 soru (Y07 1→2) geriledi; EXP-002'de gerileyen uzun madde soruları (K01, K04, K05) düzeldi. Bedeli: getirme gecikmesi ~21 ms → ~83 ms (sorgu embedding'i), indeks kurulumu ~1 dk, model ~2,2 GB.

<details><summary>Tüm parametreler</summary>

| Parametre | Değer |
|---|---|
| `pdf_parser` | `pdfplumber` |
| `chunking` | `structural` |
| `chunk_size` | `1000` |
| `chunk_overlap` | `200` |
| `embedding_model` | `BAAI/bge-m3` |
| `normalize_embeddings` | `True` |
| `retrieval` | `vector` |
| `vector_k` | `15` |
| `bm25_k` | `15` |
| `rrf_k` | `60` |
| `reranker_model` | `None` |
| `reranker_max_length` | `512` |
| `rerank_candidates` | `8` |
| `final_k` | `10` |
| `llm_model` | `gemini-2.5-flash` |
| `llm_temperature` | `0.3` |
| `prompt_version` | `v1_prototip` |

</details>

### EXP-005 — Yapısal bölme eşiği: 1000 → 1500 karakter

- **Üst deney:** EXP-004
- **Koşulma:** 2026-09-29T18:57:42, commit `0a47d1d3b0`, veri seti 2.0 (`fbab400da1f4cc72`)

**Değişen parametre(ler):**

| Parametre | Üst deney | Bu deney |
|---|---|---|
| `chunk_size` | `1000` | `1500` |

**Neden:** bge-m3 uzun metni okuyabildiği için maddeleri 1000 karakterde bölmek artık gerekli değil. Eşiği yükseltmek daha az maddenin bölünmesi (bir hükmün bütün kalması) demek; karşılığında parçalar uzar ve LLM'e giden bağlam büyür.

**Hipotez:** Daha az madde bölündüğü için bağlam bütünlüğü artar; MRR@10 artar. *(Birincil metrik: MRR@10, beklenen yön: artış)*

**Sonuçlar:**

| Metrik | Üst deney | Bu deney | Fark | Test | p |
|---|---|---|---|---|---|
| MRR@10 | 0,920 | 0,938 | +0,018 | Wilcoxon | 0,564 |
| Hit@1 | 0,852 | 0,889 | +0,037 | McNemar (kesin) (2↑ / 1↓ soru) | 1,000 |
| Hit@3 | 1,000 | 1,000 | 0 | McNemar (kesin) (0↑ / 0↓ soru) | 1,000 |
| Hit@5 | 1,000 | 1,000 | 0 | McNemar (kesin) (0↑ / 0↓ soru) | 1,000 |
| Hit@10 | 1,000 | 1,000 | 0 | McNemar (kesin) (0↑ / 0↓ soru) | 1,000 |
| Bağlam isabeti | 1,000 | 1,000 | 0 | McNemar (kesin) (0↑ / 0↓ soru) | 1,000 |
| Bağlam uzunluğu (karakter) | 8.708 | 10.835 | +2.126 | Wilcoxon | <0,001 |
| Getirme gecikmesi (ms) | 83 | 79 | −4 | Wilcoxon | 0,106 |

**Karar:** Sayısal iyileşme (istatistiksel olarak anlamlı değil) — birincil metrik MRR@10. **Hipotez:** Yön doğru, anlamlı değil.

**İlk ilgili parçanın sırası değişen sorular:** K01 (2→1), Y02 (1→2), Y04 (2→1)

**Cevap değerlendirmesi:** bu koşuda yapılmadı (`--llm`).

**İndeks:** 74 parça, ortalama 793 karakter, kurulum 38.3 sn (parmak izi `c4967fa5352aaae6`). Medyan getirme gecikmesi 75 ms.

**Yorum:** MRR@10 0,920 → 0,938 (+0,018, p=0,56) anlamlı değil; 3 soru değişti (K01 ve Y04 iyileşti, Y02 geriledi). Parça sayısı 90 → 74, LLM'e giden bağlam 8.708 → 10.835 karakter (+%24). Getirme kalitesinde belirgin bir fark yok, bağlam maliyeti arttı. Hipotez desteklenmedi.

<details><summary>Tüm parametreler</summary>

| Parametre | Değer |
|---|---|
| `pdf_parser` | `pdfplumber` |
| `chunking` | `structural` |
| `chunk_size` | `1500` |
| `chunk_overlap` | `200` |
| `embedding_model` | `BAAI/bge-m3` |
| `normalize_embeddings` | `True` |
| `retrieval` | `vector` |
| `vector_k` | `15` |
| `bm25_k` | `15` |
| `rrf_k` | `60` |
| `reranker_model` | `None` |
| `reranker_max_length` | `512` |
| `rerank_candidates` | `8` |
| `final_k` | `10` |
| `llm_model` | `gemini-2.5-flash` |
| `llm_temperature` | `0.3` |
| `prompt_version` | `v1_prototip` |

</details>

### EXP-006 — Yapısal bölmede overlap: 200 → 150 karakter

- **Üst deney:** EXP-005
- **Koşulma:** 2026-09-29T18:57:48, commit `0a47d1d3b0`, veri seti 2.0 (`fbab400da1f4cc72`)

**Değişen parametre(ler):**

| Parametre | Üst deney | Bu deney |
|---|---|---|
| `chunk_overlap` | `200` | `150` |

**Neden:** Overlap yalnız eşiği aşan maddeler bölünürken kullanılır; bölünmeler fıkra sınırlarından yapıldığı için büyük bir overlap'e gerek olmadığı düşünüldü. Amaç tekrar eden metni azaltmak.

**Hipotez:** Bölmeler fıkra sınırından yapıldığı için overlap'in sıralamaya etkisi olmaz. *(Birincil metrik: MRR@10, beklenen yön: değişim yok)*

**Sonuçlar:**

| Metrik | Üst deney | Bu deney | Fark | Test | p |
|---|---|---|---|---|---|
| MRR@10 | 0,938 | 0,938 | 0 | Wilcoxon | 1,000 |
| Hit@1 | 0,889 | 0,889 | 0 | McNemar (kesin) (0↑ / 0↓ soru) | 1,000 |
| Hit@3 | 1,000 | 1,000 | 0 | McNemar (kesin) (0↑ / 0↓ soru) | 1,000 |
| Hit@5 | 1,000 | 1,000 | 0 | McNemar (kesin) (0↑ / 0↓ soru) | 1,000 |
| Hit@10 | 1,000 | 1,000 | 0 | McNemar (kesin) (0↑ / 0↓ soru) | 1,000 |
| Bağlam isabeti | 1,000 | 1,000 | 0 | McNemar (kesin) (0↑ / 0↓ soru) | 1,000 |
| Bağlam uzunluğu (karakter) | 10.835 | 10.793 | −41 | Wilcoxon | 0,492 |
| Getirme gecikmesi (ms) | 79 | 73 | −6 | Wilcoxon | 0,006 |

**Karar:** Değişim yok — birincil metrik MRR@10. **Hipotez:** Doğrulandı.

**İlk ilgili parçanın sırası değişen soru yok.**

**Cevap değerlendirmesi:** bu koşuda yapılmadı (`--llm`).

**İndeks:** 73 parça, ortalama 800 karakter, kurulum 37.3 sn (parmak izi `ab55108885a03428`). Medyan getirme gecikmesi 72 ms.

**Yorum:** Beklendiği gibi hiçbir sorunun sırası değişmedi; parça sayısı 74 → 73. Gecikmedeki 79 → 73 ms düşüş (Wilcoxon p=0,006) hesaplamadaki bir değişiklikten değil ölçüm gürültüsünden kaynaklanıyor, çünkü overlap getirme hesaplamasını etkilemez. Bu, gecikme için yapılan anlamlılık testlerinin aynı hesaplamaya sahip yapılandırmalar arasında yanıltıcı olabileceğini gösteriyor. Gecikme farkları yalnız büyüklük mertebesi olarak (ör. ms'ye karşı saniye) yorumlanmalıdır.

<details><summary>Tüm parametreler</summary>

| Parametre | Değer |
|---|---|
| `pdf_parser` | `pdfplumber` |
| `chunking` | `structural` |
| `chunk_size` | `1500` |
| `chunk_overlap` | `150` |
| `embedding_model` | `BAAI/bge-m3` |
| `normalize_embeddings` | `True` |
| `retrieval` | `vector` |
| `vector_k` | `15` |
| `bm25_k` | `15` |
| `rrf_k` | `60` |
| `reranker_model` | `None` |
| `reranker_max_length` | `512` |
| `rerank_candidates` | `8` |
| `final_k` | `10` |
| `llm_model` | `gemini-2.5-flash` |
| `llm_temperature` | `0.3` |
| `prompt_version` | `v1_prototip` |

</details>

### EXP-007 — Getirme: yalnız vektör → hibrit (vektör + BM25, RRF)

- **Üst deney:** EXP-006
- **Koşulma:** 2026-09-29T18:57:55, commit `0a47d1d3b0`, veri seti 2.0 (`fbab400da1f4cc72`)

**Değişen parametre(ler):**

| Parametre | Üst deney | Bu deney |
|---|---|---|
| `retrieval` | `vector` | `hybrid` |

**Neden:** Mevzuat ve takvim sorularında "yatay geçiş", "bütünleme", "AGNO" gibi birebir terimler ve tarihler belirleyici. Anlamsal arama bunları kaçırabilir; BM25 (Türkçe küçük harf + ilk 5 harf kökleme) birebir eşleşmeyi yakalar. İki liste Reciprocal Rank Fusion (k=60) ile birleştirilir.

**Hipotez:** İki yöntemin güçlü yanları birleştiği için MRR@10 artar. *(Birincil metrik: MRR@10, beklenen yön: artış)*

**Sonuçlar:**

| Metrik | Üst deney | Bu deney | Fark | Test | p |
|---|---|---|---|---|---|
| MRR@10 | 0,938 | 0,938 | 0 | Wilcoxon | 0,891 |
| Hit@1 | 0,889 | 0,889 | 0 | McNemar (kesin) (2↑ / 2↓ soru) | 1,000 |
| Hit@3 | 1,000 | 1,000 | 0 | McNemar (kesin) (0↑ / 0↓ soru) | 1,000 |
| Hit@5 | 1,000 | 1,000 | 0 | McNemar (kesin) (0↑ / 0↓ soru) | 1,000 |
| Hit@10 | 1,000 | 1,000 | 0 | McNemar (kesin) (0↑ / 0↓ soru) | 1,000 |
| Bağlam isabeti | 1,000 | 1,000 | 0 | McNemar (kesin) (0↑ / 0↓ soru) | 1,000 |
| Bağlam uzunluğu (karakter) | 10.793 | 10.678 | −115 | Wilcoxon | 0,768 |
| Getirme gecikmesi (ms) | 73 | 78 | +5 | Wilcoxon | <0,001 |

**Karar:** Ortalamada değişim yok (bazı sorularda sıra değişti) — birincil metrik MRR@10. **Hipotez:** Doğrulanmadı.

**İlk ilgili parçanın sırası değişen sorular:** T01 (1→2), T10 (3→1), K04 (1→2), Y02 (2→3), Y07 (2→1)

**Cevap değerlendirmesi:** bu koşuda yapılmadı (`--llm`).

**İndeks:** 73 parça, ortalama 800 karakter, kurulum 37.3 sn (parmak izi `ab55108885a03428`). Medyan getirme gecikmesi 76 ms.

**Yorum:** Hipotez doğrulanmadı: MRR@10 değişmedi (0,938). 5 sorunun sırası değişti ve iyileşme/kötüleşme dengelendi (T10 3→1, Y07 2→1 iyileşti; T01 1→2, K04 1→2, Y02 2→3 geriledi; p=0,89). bge-m3 bu sette zaten güçlü olduğu için BM25'in ek katkısı görülmedi. Bu setten 'hibrit arama daha iyidir' sonucu çıkarılamaz. EXP-012, reranker varken de BM25'in katkısı olmadığını gösterdi.

<details><summary>Tüm parametreler</summary>

| Parametre | Değer |
|---|---|
| `pdf_parser` | `pdfplumber` |
| `chunking` | `structural` |
| `chunk_size` | `1500` |
| `chunk_overlap` | `150` |
| `embedding_model` | `BAAI/bge-m3` |
| `normalize_embeddings` | `True` |
| `retrieval` | `hybrid` |
| `vector_k` | `15` |
| `bm25_k` | `15` |
| `rrf_k` | `60` |
| `reranker_model` | `None` |
| `reranker_max_length` | `512` |
| `rerank_candidates` | `8` |
| `final_k` | `10` |
| `llm_model` | `gemini-2.5-flash` |
| `llm_temperature` | `0.3` |
| `prompt_version` | `v1_prototip` |

</details>

### EXP-008 — Reranker: yok → bge-reranker-v2-m3

- **Üst deney:** EXP-007
- **Koşulma:** 2026-09-29T19:00:14, commit `0a47d1d3b0`, veri seti 2.0 (`fbab400da1f4cc72`)

**Değişen parametre(ler):**

| Parametre | Üst deney | Bu deney |
|---|---|---|
| `reranker_model` | `None` | `BAAI/bge-reranker-v2-m3` |

**Neden:** Embedding modelleri soruyu ve parçayı ayrı ayrı kodlar (bi-encoder). Cross-encoder reranker soruyla parçayı birlikte okuyarak daha hassas bir ilgililik puanı verir. İlk 8 aday (en fazla 512 token) yeniden sıralanır. Bedeli: CPU'da sorgu başına birkaç saniye ek gecikme.

**Hipotez:** Doğru parça daha sık 1. sıraya çıkar; MRR@10 artar (gecikme de artar). *(Birincil metrik: MRR@10, beklenen yön: artış)*

**Sonuçlar:**

| Metrik | Üst deney | Bu deney | Fark | Test | p |
|---|---|---|---|---|---|
| MRR@10 | 0,938 | 1,000 | +0,062 | Wilcoxon | 0,102 |
| Hit@1 | 0,889 | 1,000 | +0,111 | McNemar (kesin) (3↑ / 0↓ soru) | 0,250 |
| Hit@3 | 1,000 | 1,000 | 0 | McNemar (kesin) (0↑ / 0↓ soru) | 1,000 |
| Hit@5 | 1,000 | 1,000 | 0 | McNemar (kesin) (0↑ / 0↓ soru) | 1,000 |
| Hit@10 | 1,000 | 1,000 | 0 | McNemar (kesin) (0↑ / 0↓ soru) | 1,000 |
| Bağlam isabeti | 1,000 | 1,000 | 0 | McNemar (kesin) (0↑ / 0↓ soru) | 1,000 |
| Bağlam uzunluğu (karakter) | 10.678 | 10.678 | 0 | Wilcoxon | 1,000 |
| Getirme gecikmesi (ms) | 78 | 4.724 | +4.646 | Wilcoxon | <0,001 |

**Karar:** Sayısal iyileşme (istatistiksel olarak anlamlı değil) — birincil metrik MRR@10. **Hipotez:** Yön doğru, anlamlı değil.

**İlk ilgili parçanın sırası değişen sorular:** T01 (2→1), K04 (2→1), Y02 (3→1)

**Cevap değerlendirmesi:** bu koşuda yapılmadı (`--llm`).

**İndeks:** 73 parça, ortalama 800 karakter, kurulum 37.3 sn (parmak izi `ab55108885a03428`). Medyan getirme gecikmesi 4.974 ms.

**Yorum:** Bütün sorularda ilgili parça 1. sırada (MRR@10 = Hit@1 = 1,000). Fark +0,062 ama p=0,10: anlamlı değil, çünkü yalnız 3 soru değişebilirdi (T01, K04, Y02; üçü de iyileşti, kötüleşen yok). Tavan etkisi: set bu yapılandırmalar için artık ayırt edici değil; daha zor ve daha çok soru gerekiyor. Bedeli çok büyük: getirme gecikmesi ~78 ms → ~4,7 sn (CPU, yaklaşık 60 kat).

<details><summary>Tüm parametreler</summary>

| Parametre | Değer |
|---|---|
| `pdf_parser` | `pdfplumber` |
| `chunking` | `structural` |
| `chunk_size` | `1500` |
| `chunk_overlap` | `150` |
| `embedding_model` | `BAAI/bge-m3` |
| `normalize_embeddings` | `True` |
| `retrieval` | `hybrid` |
| `vector_k` | `15` |
| `bm25_k` | `15` |
| `rrf_k` | `60` |
| `reranker_model` | `BAAI/bge-reranker-v2-m3` |
| `reranker_max_length` | `512` |
| `rerank_candidates` | `8` |
| `final_k` | `10` |
| `llm_model` | `gemini-2.5-flash` |
| `llm_temperature` | `0.3` |
| `prompt_version` | `v1_prototip` |

</details>

### EXP-009 — LLM'e giden parça sayısı: 10 → 5

- **Üst deney:** EXP-008
- **Koşulma:** 2026-09-29T19:02:51, commit `0a47d1d3b0`, veri seti 2.0 (`fbab400da1f4cc72`)

**Değişen parametre(ler):**

| Parametre | Üst deney | Bu deney |
|---|---|---|
| `final_k` | `10` | `5` |

**Neden:** Reranker'dan sonra ilgili parça büyük olasılıkla ilk sıralarda; 10 parça göndermek gereksiz bağlam, daha yüksek token maliyeti ve LLM'in ilgisiz metinle dikkatinin dağılması riski demek. Sıralama metrikleri bu değişiklikten etkilenmez; ölçülmek istenen bağlam uzunluğu ve bağlam isabeti.

**Hipotez:** Bağlam uzunluğu belirgin azalır; bağlam isabeti korunur. *(Birincil metrik: Bağlam uzunluğu (karakter), beklenen yön: azalış)*

**Sonuçlar:**

| Metrik | Üst deney | Bu deney | Fark | Test | p |
|---|---|---|---|---|---|
| MRR@10 | 1,000 | 1,000 | 0 | Wilcoxon | 1,000 |
| Hit@1 | 1,000 | 1,000 | 0 | McNemar (kesin) (0↑ / 0↓ soru) | 1,000 |
| Hit@3 | 1,000 | 1,000 | 0 | McNemar (kesin) (0↑ / 0↓ soru) | 1,000 |
| Hit@5 | 1,000 | 1,000 | 0 | McNemar (kesin) (0↑ / 0↓ soru) | 1,000 |
| Hit@10 | 1,000 | 1,000 | 0 | McNemar (kesin) (0↑ / 0↓ soru) | 1,000 |
| Bağlam isabeti | 1,000 | 1,000 | 0 | McNemar (kesin) (0↑ / 0↓ soru) | 1,000 |
| Bağlam uzunluğu (karakter) | 10.678 | 5.448 | −5.230 | Wilcoxon | <0,001 |
| Getirme gecikmesi (ms) | 4.724 | 5.340 | +616 | Wilcoxon | <0,001 |

**Karar:** Anlamlı iyileşme (p<0,05) — birincil metrik Bağlam uzunluğu (karakter). **Hipotez:** Doğrulandı.

**İlk ilgili parçanın sırası değişen soru yok.**

**Cevap değerlendirmesi:** bu koşuda yapılmadı (`--llm`).

**İndeks:** 73 parça, ortalama 800 karakter, kurulum 37.3 sn (parmak izi `ab55108885a03428`). Medyan getirme gecikmesi 5.090 ms.

**Yorum:** Bağlam uzunluğu 10.678 → 5.448 karakter (−%49, Wilcoxon p<0,001); bağlam isabeti 1,000'de kaldı. Hipotez doğrulandı. Gecikmedeki 4.724 → 5.340 ms farkı ölçüm gürültüsüdür, çünkü final_k getirme hesaplamasını değiştirmez (bkz. EXP-006 notu).

<details><summary>Tüm parametreler</summary>

| Parametre | Değer |
|---|---|
| `pdf_parser` | `pdfplumber` |
| `chunking` | `structural` |
| `chunk_size` | `1500` |
| `chunk_overlap` | `150` |
| `embedding_model` | `BAAI/bge-m3` |
| `normalize_embeddings` | `True` |
| `retrieval` | `hybrid` |
| `vector_k` | `15` |
| `bm25_k` | `15` |
| `rrf_k` | `60` |
| `reranker_model` | `BAAI/bge-reranker-v2-m3` |
| `reranker_max_length` | `512` |
| `rerank_candidates` | `8` |
| `final_k` | `5` |
| `llm_model` | `gemini-2.5-flash` |
| `llm_temperature` | `0.3` |
| `prompt_version` | `v1_prototip` |

</details>

### EXP-010 — Prompt: prototip → kaynaklı system prompt (v2)

- **Üst deney:** EXP-009
- **Koşulma:** 2026-09-29T19:05:30, commit `0a47d1d3b0`, veri seti 2.0 (`fbab400da1f4cc72`)

**Değişen parametre(ler):**

| Parametre | Üst deney | Bu deney |
|---|---|---|
| `prompt_version` | `v1_prototip` | `v2_kaynakli` |

**Neden:** Prototip prompt'u tüm talimatı ve bağlamı tek bir kullanıcı mesajına koyuyordu, parçaların hangi belgeden geldiği LLM'e söylenmiyordu. v2: talimatlar system mesajında; her parça "[Belge, Madde N, s. X]" etiketiyle veriliyor; kaynak gösterimi zorunlu; kapsam/istisna notlarının belirtilmesi ve bugünün tarihi ekli; konuşma geçmişi destekleniyor. Getirme metrikleri değişmez; etki yalnız cevap değerlendirmesiyle (--llm) ölçülebilir.

**Hipotez:** Cevap doğruluğu artar (özellikle kapsam dışı ve istisna içeren sorularda). *(Birincil metrik: Cevap doğruluğu, beklenen yön: artış)*

**Sonuçlar:**

| Metrik | Üst deney | Bu deney | Fark | Test | p |
|---|---|---|---|---|---|
| MRR@10 | 1,000 | 1,000 | 0 | Wilcoxon | 1,000 |
| Hit@1 | 1,000 | 1,000 | 0 | McNemar (kesin) (0↑ / 0↓ soru) | 1,000 |
| Hit@3 | 1,000 | 1,000 | 0 | McNemar (kesin) (0↑ / 0↓ soru) | 1,000 |
| Hit@5 | 1,000 | 1,000 | 0 | McNemar (kesin) (0↑ / 0↓ soru) | 1,000 |
| Hit@10 | 1,000 | 1,000 | 0 | McNemar (kesin) (0↑ / 0↓ soru) | 1,000 |
| Bağlam isabeti | 1,000 | 1,000 | 0 | McNemar (kesin) (0↑ / 0↓ soru) | 1,000 |
| Bağlam uzunluğu (karakter) | 5.448 | 5.448 | 0 | Wilcoxon | 1,000 |
| Getirme gecikmesi (ms) | 5.340 | 5.408 | +68 | Wilcoxon | 0,064 |

**Karar:** Ölçülmedi — birincil metrik Cevap doğruluğu. **Hipotez:** Beklemede (birincil metrik bu koşuda ölçülmedi).

**İlk ilgili parçanın sırası değişen soru yok.**

**Cevap değerlendirmesi:** bu koşuda yapılmadı (`--llm`).

**İndeks:** 73 parça, ortalama 800 karakter, kurulum 37.3 sn (parmak izi `ab55108885a03428`). Medyan getirme gecikmesi 5.045 ms.

**Yorum:** Getirme metrikleri beklendiği gibi EXP-009 ile aynı. Birincil metrik (cevap doğruluğu) henüz ölçülmedi. Gemini ücretsiz kotası günde 20 istek; karşılaştırma için hem EXP-009 hem EXP-010'un `--llm` ile koşulması gerekiyor (her biri 30 istek). Hipotez beklemede.

<details><summary>Tüm parametreler</summary>

| Parametre | Değer |
|---|---|
| `pdf_parser` | `pdfplumber` |
| `chunking` | `structural` |
| `chunk_size` | `1500` |
| `chunk_overlap` | `150` |
| `embedding_model` | `BAAI/bge-m3` |
| `normalize_embeddings` | `True` |
| `retrieval` | `hybrid` |
| `vector_k` | `15` |
| `bm25_k` | `15` |
| `rrf_k` | `60` |
| `reranker_model` | `BAAI/bge-reranker-v2-m3` |
| `reranker_max_length` | `512` |
| `rerank_candidates` | `8` |
| `final_k` | `5` |
| `llm_model` | `gemini-2.5-flash` |
| `llm_temperature` | `0.3` |
| `prompt_version` | `v2_kaynakli` |

</details>

### EXP-011 — Takip: bge-m3 ile normalizasyon kapalı (EXP-003 kararının sınanması)

- **Üst deney:** EXP-004
- **Koşulma:** 2026-09-29T19:07:58, commit `8e35891218`, veri seti 2.0 (`fbab400da1f4cc72`)

**Değişen parametre(ler):**

| Parametre | Üst deney | Bu deney |
|---|---|---|
| `normalize_embeddings` | `True` | `False` |

**Neden:** EXP-003'te normalizasyon MiniLM'de MRR@10'u düşürdü (p=0,061) ama zincirde açık bırakıldı, çünkü bge-m3 kosinüs benzerliğiyle kullanılmak üzere tasarlanmış. Bu karar bge-m3 için ölçülmemişti; bu deney EXP-004'ten yalnız normalizasyonu kapatarak kararın bge-m3 için doğru olup olmadığını sınar.

**Hipotez:** bge-m3 normalize vektörlerle eğitildiği için normalizasyonu kapatmak sıralamayı değiştirmez ya da kötüleştirir. *(Birincil metrik: MRR@10, beklenen yön: değişim yok)*

**Sonuçlar:**

| Metrik | Üst deney | Bu deney | Fark | Test | p |
|---|---|---|---|---|---|
| MRR@10 | 0,920 | 0,920 | 0 | Wilcoxon | 1,000 |
| Hit@1 | 0,852 | 0,852 | 0 | McNemar (kesin) (0↑ / 0↓ soru) | 1,000 |
| Hit@3 | 1,000 | 1,000 | 0 | McNemar (kesin) (0↑ / 0↓ soru) | 1,000 |
| Hit@5 | 1,000 | 1,000 | 0 | McNemar (kesin) (0↑ / 0↓ soru) | 1,000 |
| Hit@10 | 1,000 | 1,000 | 0 | McNemar (kesin) (0↑ / 0↓ soru) | 1,000 |
| Bağlam isabeti | 1,000 | 1,000 | 0 | McNemar (kesin) (0↑ / 0↓ soru) | 1,000 |
| Bağlam uzunluğu (karakter) | 8.708 | 8.708 | 0 | Wilcoxon | 1,000 |
| Getirme gecikmesi (ms) | 83 | 90 | +7 | Wilcoxon | 0,004 |

**Karar:** Değişim yok — birincil metrik MRR@10. **Hipotez:** Doğrulandı.

**İlk ilgili parçanın sırası değişen soru yok.**

**Cevap değerlendirmesi:** bu koşuda yapılmadı (`--llm`).

**İndeks:** 90 parça, ortalama 676 karakter, kurulum 41.9 sn (parmak izi `4a4d98e18fce3ab9`). Medyan getirme gecikmesi 89 ms.

**Yorum:** Sıralama hiçbir soruda değişmedi. Nedeni ölçüldü: bge-m3'ün sentence-transformers yapılandırmasında (modules.json) çıkışta zaten bir Normalize katmanı var; MiniLM'de yok. Yani normalize_embeddings parametresi bge-m3 için etkisiz, EXP-003'teki kararın bge-m3 zincirine bir etkisi olmadı. Bulgu: normalizasyonun etkisi modele bağlı ve yalnız MiniLM'de (olumsuz yönde) görüldü.

<details><summary>Tüm parametreler</summary>

| Parametre | Değer |
|---|---|
| `pdf_parser` | `pdfplumber` |
| `chunking` | `structural` |
| `chunk_size` | `1000` |
| `chunk_overlap` | `200` |
| `embedding_model` | `BAAI/bge-m3` |
| `normalize_embeddings` | `False` |
| `retrieval` | `vector` |
| `vector_k` | `15` |
| `bm25_k` | `15` |
| `rrf_k` | `60` |
| `reranker_model` | `None` |
| `reranker_max_length` | `512` |
| `rerank_candidates` | `8` |
| `final_k` | `10` |
| `llm_model` | `gemini-2.5-flash` |
| `llm_temperature` | `0.3` |
| `prompt_version` | `v1_prototip` |

</details>

### EXP-012 — Takip: reranker varken hibrit → yalnız vektör (EXP-007 kararının sınanması)

- **Üst deney:** EXP-008
- **Koşulma:** 2026-09-29T19:10:41, commit `8e35891218`, veri seti 2.0 (`fbab400da1f4cc72`)

**Değişen parametre(ler):**

| Parametre | Üst deney | Bu deney |
|---|---|---|
| `retrieval` | `hybrid` | `vector` |

**Neden:** EXP-007'de hibrit aramanın MRR@10'a ölçülebilir katkısı olmadı ama reranker (EXP-008) hibrit aday listesinin üzerine eklendi. Reranker varken BM25'in gerekli olup olmadığı ölçülmemişti; bu deney EXP-008'den yalnız getirme yöntemini vektöre çevirir. BM25 kaldırılırsa sistem sadeleşir.

**Hipotez:** Reranker'a giden 8 aday vektör aramasında da ilgili parçayı içerdiği için sonuç değişmez. *(Birincil metrik: MRR@10, beklenen yön: değişim yok)*

**Sonuçlar:**

| Metrik | Üst deney | Bu deney | Fark | Test | p |
|---|---|---|---|---|---|
| MRR@10 | 1,000 | 1,000 | 0 | Wilcoxon | 1,000 |
| Hit@1 | 1,000 | 1,000 | 0 | McNemar (kesin) (0↑ / 0↓ soru) | 1,000 |
| Hit@3 | 1,000 | 1,000 | 0 | McNemar (kesin) (0↑ / 0↓ soru) | 1,000 |
| Hit@5 | 1,000 | 1,000 | 0 | McNemar (kesin) (0↑ / 0↓ soru) | 1,000 |
| Hit@10 | 1,000 | 1,000 | 0 | McNemar (kesin) (0↑ / 0↓ soru) | 1,000 |
| Bağlam isabeti | 1,000 | 1,000 | 0 | McNemar (kesin) (0↑ / 0↓ soru) | 1,000 |
| Bağlam uzunluğu (karakter) | 10.678 | 10.793 | +115 | Wilcoxon | 0,768 |
| Getirme gecikmesi (ms) | 4.724 | 5.526 | +802 | Wilcoxon | <0,001 |

**Karar:** Değişim yok — birincil metrik MRR@10. **Hipotez:** Doğrulandı.

**İlk ilgili parçanın sırası değişen soru yok.**

**Cevap değerlendirmesi:** bu koşuda yapılmadı (`--llm`).

**İndeks:** 73 parça, ortalama 800 karakter, kurulum 37.3 sn (parmak izi `ab55108885a03428`). Medyan getirme gecikmesi 5.286 ms.

**Yorum:** Reranker varken BM25'i kaldırmak hiçbir sorunun sırasını değiştirmedi (MRR@10 1,000). Gecikme farkı (~4,7 sn'ye karşı ~5,5 sn) reranker süresinin gürültüsü içinde kalıyor; BM25'in kendi maliyeti ihmal edilebilir düzeyde. Bu sette BM25'in katkısı ne tek başına (EXP-007) ne de reranker ile (EXP-012) gösterilebildi. Bu yapılandırma daha sade ve aynı sonucu veriyor. Üretimdeki hibrit yöntemin korunması bu veriyle desteklenmiyor; karar kullanıcıya bırakıldı.

<details><summary>Tüm parametreler</summary>

| Parametre | Değer |
|---|---|
| `pdf_parser` | `pdfplumber` |
| `chunking` | `structural` |
| `chunk_size` | `1500` |
| `chunk_overlap` | `150` |
| `embedding_model` | `BAAI/bge-m3` |
| `normalize_embeddings` | `True` |
| `retrieval` | `vector` |
| `vector_k` | `15` |
| `bm25_k` | `15` |
| `rrf_k` | `60` |
| `reranker_model` | `BAAI/bge-reranker-v2-m3` |
| `reranker_max_length` | `512` |
| `rerank_candidates` | `8` |
| `final_k` | `10` |
| `llm_model` | `gemini-2.5-flash` |
| `llm_temperature` | `0.3` |
| `prompt_version` | `v1_prototip` |

</details>
