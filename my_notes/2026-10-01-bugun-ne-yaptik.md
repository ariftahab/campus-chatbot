# 2026-10-01 — Bugün ne yaptık?

> Bu dosya günün **yapılan işler özeti**. Öğrenilecek kavramlar ayrıca `learning_log/`'a yazılacak.

## Kısaca

| # | Ne yaptık | Sonuç | Commit |
|---|---|---|---|
| 1 | LLM: gemini-2.5-flash → gemini-3.1-flash-lite | EXP-013. Retrieval aynı; cevap kalitesi henüz ölçülmedi | `c99ba06`, `4120dbe` |
| 2 | 13 bölümlük özet artık yalnız sen isteyince | CLAUDE.md güncellendi | `0efc9a5` |
| 3 | 136 yeni PDF + veri temizliği + `corpus` parametresi | 3 → 139 belge | `5c8a2c5` |
| 4 | GPU'ya geçiş (torch CUDA build'i) | Embedding ~18 kat hızlandı | `a98fafe` |
| 5 | Retrieval ara listeleri kaydediliyor (stage-wise evaluation) | Hatanın hangi aşamada oluştuğu görülüyor | `1c3106c` |
| 6 | `device` parametresi, deneylerin yeniden numaralandırılması | EXP-014 = GPU, EXP-015 = corpus | `a0f687f` |
| 7 | EXP-014 koşuldu (CPU → GPU) | Latency 5,4 sn → 0,37 sn, sıralama birebir aynı | `fbf0177` |
| 8 | EXP-015 koşuldu (3 → 139 belge) | MRR@10 1,00 → 0,86 | `4607190` |
| 9 | Regex genişletme + fallback kodu, corpus v3 (kopyasız) | Kod commit edildi | `a899135` |
| 10 | EXP-016 koşuldu (regex genişletme) | Retrieval değişmedi (beklenen) | `4bd87f6` |
| 11 | Onay kuralı CLAUDE.md'ye yazıldı | Her deneyden önce gerekçe + onay | `91d70f2` |

---

## 1. LLM değişikliği (EXP-013)

- **Ne:** Cevap üreten model `gemini-3.1-flash-lite` oldu.
- **Neden:** 2.5-flash'ın ücretsiz kotası günde 20 istek. `--llm` değerlendirmesi 30 istek sürdüğü için tek günde bitmiyordu.
- **Nasıl doğruladık:** Model adını tahmin etmedik, API'nin model listesinden kontrol ettik. Sonra tek bir istekle (smoke test) çalıştığını gördük.
- **Sonuç:** Retrieval metrikleri EXP-010 ile aynı. Bu beklenen bir sonuç: LLM, retrieval'dan sonra devreye giriyor.
- **Açık:** Cevap doğruluğu (`answer_acc`) henüz ölçülmedi.

## 2. Yeni belgeler ve veri temizliği

Taramada çıkan sorunlar ve yapılanlar:

| Sorun | Ne yapıldı |
|---|---|
| Birebir aynı 2 PDF çifti (aynı hash) | Sen sildin |
| `BAİBÜ Intibak Yönergesi.pdf` ile `intibak yönergesi.pdf` metni %98 aynı | Biri silindi |
| `ogrenci-kayıt-yonerge.pdf` başka bir adla duruyordu (değerlendirme seti bu adı kullanıyor) | Sen eski adına geri döndürdün |
| `.uzaktan-ogretime-...pdf` adı noktayla başlıyordu, gizli dosya sayılıp listeye girmedi | Yeniden adlandırıldı |
| Taranmış (metinsiz) PDF | Yok, OCR gerekmedi |

**`corpus` parametresi:** Belge kümesi artık bir deney parametresi.
- `v1` = ilk 3 belge
- `v2` = `data/corpus_v2.txt`'deki 139 belge

Liste sabit tutuluyor. `data/`'ya sonradan PDF eklesen bile eski deneyler aynı belgelerle yeniden üretilebilir. Eski config'lerde bu alan yok, onlar için `v1` varsayılıyor.

**Doğrulama:** Yeni kod `v1` ile eski index'teki 73 chunk'ın birebir aynısını üretti.

## 3. GPU (EXP-014)

- **Ne oldu:** Makinede RTX 4050 vardı ama venv'deki PyTorch **CPU build**'iydi (`2.9.0+cpu`), yani GPU hiç kullanılmıyordu. Aynı sürümün CUDA build'ini (`2.9.0+cu128`) kurduk. Kod değişmedi; sentence-transformers GPU'yu kendisi buluyor.
- **`device` parametresi:** `cpu` | `cuda`. Eski deneyler için `cpu` varsayılıyor, istenirse hâlâ CPU'da tekrar koşulabilirler.

| | CPU (EXP-013) | GPU (EXP-014) |
|---|---|---|
| Retrieval latency | 5352 ms | **366 ms** (~15 kat, p<0,001) |
| İndeks kurma (73 chunk) | 37 sn | **4 sn** |
| Sıralama | — | **27/27 soru birebir aynı** |

**Tez için anlamı:** GPU sonucu değiştirmiyor, sadece hızlandırıyor. CPU ile koşulan eski deneylerin kalite metrikleri karşılaştırılabilir kalıyor. Latency ise karşılaştırılamaz.

**Ek düzeltme:** `requirements.txt` BOM'suz UTF-16 olarak kaydedilmişti ve pip bu dosyayı okuyamıyordu. UTF-8'e çevrildi.

## 4. Stage-wise evaluation (senin fikrin)

`Retriever.rank()` artık ara listeleri de kaydediyor:

```
vector top-15 ─┐
               ├─ RRF ─→ ilk 8 → reranker ─→ final ─→ ilk 5 LLM'e
BM25 top-15 ───┘
```

Her aşama için "ilgili chunk kaçıncı sırada?" sorusunu soruyoruz. Böylece iki hata türü birbirinden ayrılıyor:
- **Recall hatası:** İlgili chunk hiçbir aday listesine girmemiş. Reranker görmediği bir chunk'ı düzeltemez.
- **Ranking hatası:** İlgili chunk adaylar arasında var ama aşağıda kalmış.

Bu bir deney değil, ölçüm altyapısı: chat'in davranışı değişmedi. Experiment log'a "Retrieval stages" tablosu eklendi.

## 5. Deney numaraları neden değişti?

Corpus deneyi önce EXP-014 olarak yazılmıştı. Sonra GPU'ya geçtik. Corpus deneyi GPU'da koşulsaydı EXP-013'e göre **iki** şey birden değişmiş olacaktı (belge sayısı + donanım) ve etkileri birbirinden ayrılamazdı. Bu yüzden:

| Deney | Değişen tek şey |
|---|---|
| EXP-014 | `device: cpu → cuda` |
| EXP-015 | `corpus: v1 → v2` |

Eski EXP-014'ün henüz sonucu yoktu, yani bir sonuç değiştirilmiş olmadı.

## 6. EXP-015: 3 → 139 belge

| Metrik | 3 belge | 139 belge |
|---|---|---|
| Chunk sayısı | 73 | 4033 |
| MRR@10 | 1,000 | **0,863** (p=0,02) |
| Hit@1 | 1,000 | 0,778 (6 soru kötüleşti) |
| Context hit | 1,000 | 0,963 (1 soruda doğru chunk LLM'e ulaşmıyor) |

**Aşamalar (MRR@10):**

| | Vector | BM25 | RRF | Rerank input recall | Final |
|---|---|---|---|---|---|
| 3 belge | 0,938 | 0,838 | 0,938 | 1,000 | 1,000 |
| 139 belge | 0,602 | 0,581 | 0,594 | 0,963 | **0,863** |

**Bulgular:**
1. **Distractor etkisi:** Benzer konulu belgeler (diğer fakültelerin eğitim yönetmelikleri gibi) retrieval'ı ciddi düşürüyor. Vector 0,94'ten 0,60'a indi.
2. **Reranker kritik:** RRF'teki 0,59'u 0,86'ya çıkarıyor. Bu sistemin en değerli bileşeni.
3. **BM25 zarar veriyor olabilir:** Kötüleşen 6 sorunun 4'ünde BM25 ilgili chunk'ı hiç bulamadı ve RRF'i vector'ün tek başına verdiği sıralamadan da aşağı çekti ("Yaz okulu ders kayıtları ne zaman yapılacak?" sorusunda vector 2. sıra → RRF 6. sıra).
4. **Reranker penceresi dar:** "Güz yarıyılında dersler ne zaman başlıyor?" sorusunda ilgili chunk RRF'te 9. sıradaydı. Reranker'a yalnız ilk 8 aday gittiği için onu hiç göremedi.
5. **Değerlendirme seti eksik etiketliyor:** Değerlendirme yalnız sorunun "kaynak" belgesini doğru sayıyor. "Üniversitenin öğretim dili nedir?" sorusunda öne geçen chunk "Üniversitenin eğitim-öğretim dili Türkçedir" diyor; bu doğru bir cevap, sadece başka bir yönetmelikte geçiyor. "Diplomamı kaybedersem ne yapmalıyım?" sorusu da benzer: mezun belgeleri yönergesi de diploma kaybını düzenliyor. Yani 6 kötüleşmenin **2'si gerçek hata değil**, eksik etiket (false negative).

## 7. Regex genişletme ve fallback kodu (commit `a899135`)

`ingest.py` ve `config.py`'de şu değişiklikler duruyor (`git status`'ta `M` olarak görünüyor):

- **`structural_v2`:** Genişletilmiş madde regex'i. Tanınan yeni biçimler:
  - `Madde 4.`, `Madde 1:`, `Madde–1:`
  - `MADDE 7 (Değişik...)`, `MADDE 17 −` (Unicode eksi), `MADDE 17/A-` (ek madde)
  - `MADDE1 2-` (PDF'te yapışmış dipnot rakamı)
  - Satırda tek başına `Madde 16`
  - `Amaç Madde 1.` (başlık ve madde aynı satırda)

  Fallback'e düşen belge sayısı 11'den 4'e iniyor. Tanınan madde satırı 2652'den ~2790'a çıkıyor. Cümle içi atıflar (`Madde 5'te belirtilen`) bilerek eşleşmiyor.
- **`structural_v3`:** v2'nin üstüne iyileştirilmiş fallback. Madde yapısı olmayan belge sayfa sayfa değil, bütün olarak bölünüyor; böylece sayfa sonunda cümle yarım kalmıyor.
- Eski `structural` yolu aynen korunuyor.

Doğrulama: eski `structural` yolu EXP-014 ve EXP-015 index'leriyle birebir aynı chunk'ları üretiyor.
Fallback iyileştirmesinin (v3) etkisi regex'ten sonra çok küçük kaldı: sadece 2 belge, 14 → 10 chunk.

### Ek kopyalar ve corpus v3
Chunk sayıları aynı olan belgelere bakınca **8 kopya çifti** daha bulundu (metin benzerliği %94-100). Hash'leri farklı olduğu
için ilk taramada görünmemişlerdi. Dosyalar silinmedi; `corpus: v3` = v2 eksi bu 8 kopya (131 belge, `data/corpus_v3.txt`).
v3 deneyi değerlendirme seti v2'den sonra yapılacak.

## 7b. EXP-016: regex genişletme (eski sorularla)

| Metrik | EXP-015 | EXP-016 |
|---|---|---|
| MRR@10 | 0,863 | 0,863 |
| Hit@1 | 0,778 | 0,778 |
| Değişen soru | — | 0 |

- **Neden değişmedi:** Soruların 3 kaynak belgesi bu değişiklikten hiç etkilenmiyor; değişen 16 belgenin hepsi distractor.
  "Regex işe yaramadı" demek **değil**, "bu soru setiyle ölçülemiyor" demek. Faydası v2 setiyle ölçülecek.
- **Latency artefaktı:** Sonuçta 407 → 2220 ms görünüyor ama bu ölçüm hatası. İki model 4,4 GB VRAM kullanıyor (kart 6 GB);
  index'i kuran aynı süreçte retrieval ölçülünce VRAM doluyor ve Windows belleği sistem RAM'ine taşıyor.
  Ayrı süreçte ölçünce ~400 ms çıkıyor.
- **Ek bilgi:** Index fingerprint'i `ingest.py`'nin kaynak kodunu da içeriyor. Bu yüzden `ingest.py` her değiştiğinde
  (eski yollar aynı kalsa bile) tüm index'ler yeniden kuruluyor.

## 8. Karar bekleyen konular

1. **Değerlendirme seti v2** (aşağıdaki öneri).
2. EXP-016 (regex) ve EXP-017 (fallback): eval v2'den sonra koşulmalı. Mevcut sorularla etkileri ölçülemiyor.
3. BM25 hâlâ gerekli mi? EXP-012'nin sorusu 139 belgede yeniden sorulmalı.
4. `rerank_candidates` 8'den büyük olmalı mı? GPU'da artırmak artık ucuz.
5. `--llm` ile cevap kalitesinin ölçülmesi (Gemini kotası harcar).

### Değerlendirme seti neden yetmiyor?

| Sorun | Sonucu |
|---|---|
| 27 sorunun hepsi ilk 3 belgeden | Yeni 136 belgedeki iyileşmeyi (ör. regex) **ölçemiyoruz** |
| Her sorunun tek bir "doğru belgesi" var | Başka belgedeki doğru cevap yanlış sayılıyor ("Üniversitenin öğretim dili nedir?", "Diplomamı kaybedersem ne yapmalıyım?") |
| 3 belgede her şey 1,000 çıkıyordu | Ceiling effect: iyileşme görülecek yer kalmamıştı |

### Önerim

- **v1 setini dondur.** Eski deneyler onunla karşılaştırılabilir kalsın.
- **Yeni bir v2 seti oluştur:**
  - Yeni belgelerden de sorular olsun. Kategoriler: madde içeriği, tarih, tanım, istisna, farklı fakültelerin benzer kuralları, kapsam dışı.
  - Bir soru için birden fazla belge doğru sayılabilsin (`kaynak` bir liste olsun).
  - Kanıt yine "kaynakta birebir geçen cümle" ile doğrulansın.
- **Referans zincirini v2 üzerinde yeniden koş:** EXP-015 yapılandırması v2 setiyle yeniden ölçülür ve yeni baseline o olur.
