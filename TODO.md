# TODO

## Sıra

1. [ ] **PDF'ler:** Sitedeki tüm yönergeler, yönetmelikler ve mevzuat `data/` içine eklenecek (çok sayıda PDF).
2. [ ] **UI:** Chatbot için bir arayüz yazılacak (terminal yerine).
3. [ ] **Ders programları (en son):** Sitenin ders programı bölümünde her dönemin programı yayınlanıyor; her dönem başı
       linkteki dosya da data'ya eklenecek. Tablo yapısı yüzünden en zor kısım.
4. [ ] Diğer bilgiler (duyurular, birim sayfaları, iletişim...). Gerekirse **web scraping**.

## PDF'leri eklemeden önce bilinmesi gerekenler

- Şu an `config.DOCUMENTS`'ta olmayan bir PDF eklenirse: başlık = dosya adı; içinde "Madde N-" satırları varsa madde madde
  chunk'lanır, yoksa sayfa sayfa. Yani dosya adları anlamlı olmalı (ör. `lisans-egitim-ogretim-yonetmeligi.pdf`).
- **Corpus değişince eski deney sonuçları yeni sonuçlarla karşılaştırılamaz.** Şu an koşucu sadece evaluation dataset'in
  hash'ini kontrol ediyor, PDF'lerin (corpus) hash'ini karşılaştırmada kontrol etmiyor. PDF'ler eklendikten sonra:
  (a) koşucuya corpus hash kontrolü eklenmeli, (b) yeni corpus ile baseline yeniden koşulmalı.
- Yeni belgeler için evaluation dataset'e soru eklenmeli (yoksa yeni belgelerde sistemin nasıl çalıştığı ölçülmez).

## Bu plan mimariyi nasıl etkiler? (uygulamadan önce konuşulacak)

Aşağıdakiler karar verilmesi gereken sorular. Her biri, uygulanmadan önce alternatifleriyle birlikte anlatılıp
onaylanacak ve RAG bileşenini etkileyenler deney olarak kaydedilecek.

- **Data ingestion / scraping:** Hangi sayfalar ve dosyalar alınacak? Site PDF, HTML ya da Excel mi veriyor?
  `robots.txt` ve kullanım koşulları kontrol edilmeli; siteyi yormamak için istekler yavaş gönderilmeli (rate limit).
- **Güncellik (freshness):** Ders programı ve takvim her dönem değişiyor. Eski dönemin bilgisi yeni dönemle
  karışmamalı. Her belgeye `donem` / `gecerlilik` gibi metadata eklenmeli; eski sürümler arşive mi alınacak, silinecek mi?
- **Yeniden indexleme:** Yeni belge geldiğinde bütün index'i baştan kurmak yerine sadece yeni belgeyi eklemek
  (incremental indexing) gerekebilir. Şu anki fingerprint sistemi her değişiklikte hepsini yeniden kuruyor.
- **Chunking ölçeklenmesi:** Şu anki structural chunking sadece "Madde N-" biçimine ve bu takvimin tablo yapısına göre
  yazılmış. Farklı biçimli yönergeler, HTML sayfalar ve ders programı tabloları için yeni yöntemler gerekecek.
  `config.DOCUMENTS` listesine her dosyayı elle eklemek yüzlerce belgede sürdürülemez.
- **Ders programı soruları:** "Salı günü 3. sınıfın hangi dersleri var?" gibi sorular, tablo verisi üzerinde filtreleme
  gerektirir. Bunu embedding ile aramak iyi çalışmayabilir; tabloyu yapılandırılmış veri olarak saklayıp sorgulamak
  (ör. SQL) bir alternatif.
- **Vector store:** 73 chunk için FAISS yeterli. Binlerce chunk ve metadata filtresi ("sadece 2026 Bahar") gerekince
  Chroma / Qdrant gibi bir vector database düşünülebilir.
- **Retrieval kalitesi:** Belge sayısı artınca benzer belgeler (farklı fakültelerin benzer yönergeleri) karışabilir.
  Bugün etkisi görülmeyen BM25 ve reranker, büyük koleksiyonda fark yaratabilir; yeniden ölçülmeli.
- **Evaluation dataset:** Yeni belge türleri için yeni sorular gerekli (ders programı, farklı yönergeler).
  Dataset'in yeni sürümü eski sonuçlarla karşılaştırılamaz; baseline yeniden koşulmalı.
- **Kaynak gösterme:** Cevapta belgenin sitedeki linki de verilebilir (metadata'da `url`).

## Diğer açık işler

- [ ] Evaluation dataset'i zorlaştır (ceiling effect) ve tez için ayrı bir test seti oluştur.
- [ ] EXP-009 ve EXP-010 için answer accuracy ölç (`--llm`; Gemini ücretsiz kotası günde 20 istek).
- [ ] Hybrid search ve reranker production'da kalsın mı? (Bugünkü set üzerinde katkıları gösterilemedi.)
