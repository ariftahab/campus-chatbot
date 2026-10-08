# TODO

## Sıra

0. [x] **PDF'ler:** Sitedeki yönergeler, yönetmelikler ve mevzuat `data/` içine eklendi (corpus v2 = 139 belge,
       v3 = kopyalar çıkarılmış 131 belge). Corpus artık deney config'inde bir parametre (`corpus`).

1. [x] **UI (chatbot arayüzü)** — FastAPI backend + kendi HTML/CSS/JS frontend'imiz (ayrıntılar RAG-Study-Notes
       reposundaki `learning_log/frontend_backend_log.md`). 2026-10-08'de tamamlandı.
   - [x] Sohbet sekmesi, soru-cevap kaydı (`logs/sohbet.jsonl`), 👍/👎 ve `/admin`'de elle değerlendirme.
   - [x] Tıklanabilir kaynaklar (panelde chunk metni + PDF'te o sayfa), Belgeler sekmesi.
   - [x] `/admin` için HTTP Basic Auth (`.env`'de `ADMIN_PASSWORD`).
   - [x] Değerlendirme sayfasından soru-cevabı kalıcı olarak silme (uygunsuz sorular için).
   - [x] Mobil düzen (yalnız mesaj listesi ve üst bar kayar) ve cache busting.
   - [x] Eski Gradio arayüzü (`/ui`) kaldırıldı.
   - [x] **Başka biri tarafından test:** Cloudflare Quick Tunnel (`cloudflared tunnel --url http://localhost:8000`).
         Laptop açık kalmalı, link her açılışta değişir. `/ask` için günlük sınır şimdilik yok (Gemini kotası paylaşılıyor).
     - Kalıcı demo gerekirse: **Hugging Face Spaces** (ücretsiz CPU, 16 GB RAM; Docker, index + PDF yükleme,
       API anahtarı secret). CPU'da retrieval soru başına ~5 sn.
   - (UI'dan belge ekleme kapsam dışı; belgeler eskisi gibi `data/` + yeni corpus sürümüyle eklenir.)

2. [ ] **Deneylere geri dönüş / optimizasyon** — büyüyen corpus, gerçek kullanıcı soruları ve yeni soru setiyle RAG
       bileşenleri (chunking, embedding, retrieval, reranker, prompt, LLM) yeniden deneylerle optimize edilecek.
   - [ ] **Veriden öğrenme:** Yeterli gerçek kullanıcı sorusu birikince, sistemin hangi soru türlerinde hata yaptığı
         analiz edilir. Gerçek sorulardan seçilenler yeni bir soru seti sürümü olarak eklenebilir (eski setler değiştirilmez).
   - [ ] **Atıfta fıkra:** LLM şu an atıflarda fıkra yazmıyor (2026-10-08: log'daki 64 atıfın hiçbirinde yok), bu
         yüzden panelde fıkra vurgulanamıyor. Fıkrayı yazdırmak bir prompt değişikliği, yani deney.

3. [ ] **Ders programları ve akademik takvim (scraping)** — en sona bırakıldı: her bölümün programı farklı
       biçimde; tek başına bitirme projesi büyüklüğünde bir iş. Yapılırsa önce yalnız bir bölüm (Bilgisayar Müh.).
   - [ ] Program/takvim HTML tablo mu, PDF mi, Excel mi? Her dönemin verisi `donem` / `gecerlilik` metadata'sıyla.
   - [ ] Tablo verisi için yeni chunking veya yapılandırılmış saklama (ör. SQL) — deney olarak.
   - [ ] Ders programı soruları için yeni soru seti sürümü (ör. "Salı günü 3. sınıfın hangi dersleri var?").

4. [ ] Diğer bilgiler (birim sayfaları, iletişim...).

## Belki (kesin değil)

Yapılıp yapılmayacağı henüz belli değil; karar verilirse numaralı sıraya alınır.

- [ ] **Duyurular (web scraping)** — sitedeki duyurular listesinden her duyurunun sayfasına girip metnini almak.
   - [ ] Sitenin yapısını incele: liste sayfası, sayfalama (pagination), duyuru sayfasının HTML'i; `robots.txt` ve
         kullanım koşulları; istekler yavaş gönderilmeli (rate limit).
   - [ ] Scraper: liste sayfası → duyuru linkleri → her duyurunun sayfası → ana metin. `url`, `tarih`, `baslik`
         metadata'sı; aynı duyuru iki kez eklenmesin (URL ile).
   - [ ] Güncellik: eski duyurular ne olacak? (süresi geçen başvuru duyurusu yanlış cevaba yol açabilir)
   - [ ] Index'e ekleme yeni bir corpus sürümüyle; duyurular için yeni sorularla yeni bir soru seti sürümü.

## Bu plan mimariyi nasıl etkiler? (uygulamadan önce konuşulacak)

Aşağıdakiler karar verilmesi gereken sorular. Her biri, uygulanmadan önce alternatifleriyle birlikte anlatılıp
onaylanacak ve RAG bileşenini etkileyenler deney olarak kaydedilecek.

- **UI ve deney ayrımı:** UI production config'i (`config.PRODUCTION_EXPERIMENT`) kullanır; deney koşucusundan bağımsızdır.
- **Kullanıcı sorularının değerlendirilmesi:** Gerçek sorularda "doğru cevap" önceden bilinmiyor. Etiketleme (elle,
  kullanıcı geri bildirimi, LLM-as-judge) yöntemi seçilmeli; Gemini ücretsiz kotası (günde 500 istek) sınırlayıcı.
- **Güncellik (freshness):** Ders programı ve takvim her dönem değişiyor. Eski sürümler arşive mi alınacak, silinecek mi?
- **Yeniden indexleme:** Yeni belge geldiğinde bütün index'i baştan kurmak yerine sadece yeni belgeyi eklemek
  (incremental indexing) gerekebilir. Şu anki fingerprint sistemi her değişiklikte hepsini yeniden kuruyor.
- **Ders programı soruları:** Tablo verisi üzerinde filtreleme gerektirir; embedding ile aramak iyi çalışmayabilir.
  Tabloyu yapılandırılmış veri olarak saklayıp sorgulamak (ör. SQL) bir alternatif.
- **Vector store:** Binlerce chunk ve metadata filtresi ("sadece 2026 Bahar") gerekince Chroma / Qdrant gibi bir
  vector database düşünülebilir.
- **Kaynak gösterme:** Cevapta belgenin sitedeki linki de verilebilir (metadata'da `url`).

## Diğer açık işler

- [ ] Evaluation dataset'i zorlaştır (ceiling effect) ve tez için ayrı bir test seti oluştur.
- [ ] Hybrid search ve reranker production'da kalsın mı? (Büyük corpus'ta yeniden ölçülmeli.)
