# TODO

## Sıra

0. [x] **PDF'ler:** Sitedeki yönergeler, yönetmelikler ve mevzuat `data/` içine eklendi (corpus v2 = 139 belge,
       v3 = kopyalar çıkarılmış 131 belge). Corpus artık deney config'inde bir parametre (`corpus`).

1. [ ] **UI (chatbot arayüzü)** — terminal yerine sohbet arayüzü.
   - [x] **Sohbet sekmesi:** soru sor, cevabı ve kaynakları (belge + madde) gör.
   - [x] **Soru-cevap kaydı (logging):** Sorulan her soru, verilen cevap, retrieve edilen chunk'lar, kullanılan
         config / commit hash ve zaman bir dosyaya yazılır (ör. `logs/sohbet.jsonl`).
   - [x] **Doğruluk ölçümü:** 👍/👎 + `/admin` sayfasında elle değerlendirme (cevap etiketi, doğru kaynak geldi mi,
         hata aşaması). LLM-as-judge şimdilik yok; elle etiketler ileride judge için referans olur.
   - [x] **Tıklanabilir kaynaklar:** kaynak düğmeleri ve cevaptaki atıflar → panelde chunk metni + PDF'te o sayfa.
   - [ ] Gradio arayüzünü (`/ui`, `app/ui.py`) yeni arayüz oturunca kaldır.
   - [x] `/admin` için kimlik doğrulama (HTTP Basic Auth, `.env`'de `ADMIN_PASSWORD`).
   - [ ] Atıftaki fıkrayı ("Madde 8/2") panelde vurgulama.
   - [x] **Başka biri tarafından test (deploy):** 2026-10-08'de Cloudflare Quick Tunnel ile açıldı (`/ask` sınırı şimdilik yok).
     - Kısa test için: **Cloudflare Quick Tunnel** (`cloudflared tunnel --url http://localhost:8000`). Uygulama
       laptopta GPU ile çalışır, ücretsiz geçici link verir. Laptop açık kalmalı, link her açılışta değişir.
     - Kalıcı demo için: **Hugging Face Spaces** (ücretsiz CPU, 16 GB RAM yeterli; Docker, index + PDF yükleme,
       API anahtarı secret). CPU'da retrieval soru başına ~5 sn.
     - Açmadan önce: Gemini günlük kotası (link herkese açık, kotayı başkası tüketebilir) → `/ask` için günlük istek
       sınırı; `/admin` için şifre (HTTP Basic Auth), çünkü linki bilen herkes değerlendirme verisine etiket
       yazabilir; test edene soruların kaydedildiğini söylemek.
   - [ ] **Veriden öğrenme:** Yeterli gerçek kullanıcı sorusu birikince, sistemin hangi soru türlerinde hata yaptığı
         analiz edilir ve model / pipeline buna göre güncellenir. Gerçek sorulardan seçilenler yeni bir soru seti
         sürümü olarak eklenebilir (eski setler değiştirilmez).
   - [x] **Data sekmesi:** Corpus'taki belgeleri listele (başlık, tür, chunk sayısı), bir belgenin chunk'larını gör.
   - (UI'dan belge ekleme şimdilik kapsam dışı; belgeler eskisi gibi `data/` + yeni corpus sürümüyle eklenir.)
   - Karar: FastAPI backend + kendi HTML/CSS/JS frontend'imiz (ayrıntılar RAG-Study-Notes reposundaki `learning_log/frontend_backend_log.md`).

2. [ ] **Ders programları ve akademik takvim (scraping)** — okulun sitesinde her dönem güncelleniyor; her dönem elle
       indirip yüklemek yerine scrape edilecek.
   - [ ] Sitenin yapısını incele: program/takvim HTML tablo mu, PDF mi, Excel mi? `robots.txt` ve kullanım koşulları;
         istekler yavaş gönderilmeli (rate limit).
   - [ ] Scraper yaz; her dönemin verisini `donem` / `gecerlilik` metadata'sıyla sakla (eski dönem yenisiyle karışmasın).
   - [ ] **Chunking geliştirmesi:** Bu veriler mevcut structural chunking'e ("Madde N-" ve takvim tablosu) uymayabilir;
         yeni bir chunking yöntemi (veya tablo verisini yapılandırılmış saklama, ör. SQL) gerekebilir. Deney olarak yapılır.
   - [ ] **Soru seti:** Ders programı ve takvim için yeni sorular eklenerek yeni bir set sürümü oluşturulur
         (ör. "Salı günü 3. sınıfın hangi dersleri var?"); referans zinciri yeni setle yeniden koşulur.

3. [ ] **Deneylere geri dönüş / optimizasyon** — 1 ve 2 bittikten sonra, büyüyen corpus, gerçek kullanıcı soruları ve
       yeni soru setiyle RAG bileşenleri (chunking, embedding, retrieval, reranker, prompt, LLM) yeniden deneylerle
       optimize edilecek.

4. [ ] Diğer bilgiler (duyurular, birim sayfaları, iletişim...). Gerekirse web scraping.

## Bu plan mimariyi nasıl etkiler? (uygulamadan önce konuşulacak)

Aşağıdakiler karar verilmesi gereken sorular. Her biri, uygulanmadan önce alternatifleriyle birlikte anlatılıp
onaylanacak ve RAG bileşenini etkileyenler deney olarak kaydedilecek.

- **UI ve deney ayrımı:** UI production config'i (`config.PRODUCTION_EXPERIMENT`) kullanır; deney koşucusundan bağımsızdır.
- **Kullanıcı sorularının değerlendirilmesi:** Gerçek sorularda "doğru cevap" önceden bilinmiyor. Etiketleme (elle,
  kullanıcı geri bildirimi, LLM-as-judge) yöntemi seçilmeli; Gemini ücretsiz kotası (günde 20 istek) sınırlayıcı.
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
