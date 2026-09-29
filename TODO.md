# TODO

## Veri kapsamı: üniversitenin tüm bilgileri

Hedef: Chatbot, BAİBÜ'nün sitesindeki bütün bilgileri kapsayacak. Şu an sadece 3 PDF var.

- [ ] Sitedeki **tüm yönergeler, yönetmelikler ve mevzuat** `data/` içine eklenecek.
- [ ] **Ders programları:** Sitenin ders programı bölümünde her dönemin ders programı yayınlanıyor. Her dönem başında
      yeni program yayınlandığında linkteki dosya da data'ya eklenecek.
- [ ] Diğer bilgiler (duyurular, birim sayfaları, iletişim, akademik takvimin yeni yılları...) eklenecek.
- [ ] Bunları toplamak için gerekirse **web scraping** yapılacak.

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
