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
   - **Sıra (2026-10-08, ilk 19 gerçek sorunun etiketlerinden):** retrieval hataları hep "cevap birime göre
     değişen" sorularda (ör. mezuniyet kredisinde tıp ve diş gelmedi). generation hataları: cevap yokken ilgisiz
     bilgi eklemek; aynı düzeyde aynı kuralı tekrar etmek (lisans 240 AKTS = hukuk 240 AKTS ayrı yazılmış).
     - [x] **0. Teşhis** (deney değil, kota harcamaz): eksik chunk'lar retrieval'ın neresinde kayboluyor?
           Sonuç: mezuniyet kredisinde tıp maddesi vector'da 75-90. sırada (havuzda yok), diş 12-14. sırada ama
           RRF'te 18-24 (reranker'a ulaşmıyor); ulaşsalar da reranker puanları LLM'e giden 5'ten düşük → sorun
           sıralama değil **kapsam**; `rerank_candidates` düzeltmez. Rapor sorusunda lisans Madde 24 vector'da 28.
           sırada; reranker puanı ilk 5'teki iki alakasız chunk'tan yüksek → havuz büyüse (`vector_k` ≥ 28) girerdi.
           Kayıt dondurmada yönetmelik lisans için koşulları saymıyor (corpus sınırı). Fikir: düşük reranker puanı
           "belgelerde net cevap yok" sinyali olabilir.
     - [x] **1. `rerank_candidates` 8 → 30** (EXP-021; EXP-022'de fp16 ile gecikme bedeli kalktı). Gerekirse
           `final_k` ayrı deney.
     - [x] **2. Soru seti v4** (`eval/sorular_v4.json`, 139 soru, corpus v4 için): gruplar A=bulma 70, B=kapsam 29,
           C=çekimser kalma 25, D=takip sorusu 15 (sohbet geçmişiyle). v3'ün 77 sorusu (takvim 2026-2027'ye taşındı,
           yaz öğretimi soruları cevapsız), 8 gerçek kullanıcı sorusu, 54 yeni soru. Koşucuya sohbet geçmişi (rewrite
           önbellekli) ve coklu_kapsam için kapsam isabeti eklendi.
     - [x] **EXP-023:** corpus v4 + set 4.0 baseline; production oldu (2026-10-08).
     - [x] **Kapsam sorunu (2026-10-15):** hedef davranış "bütün fakülteleri say" yerine "genel kural + fakülteyi
           sor" (set 4.1). EXP-024 baseline, EXP-025 netleştirme prompt'u (%45 gereksiz sorma, alınmadı), EXP-026 kapsam
           tamamlama (reddedildi), EXP-027 netleştirmeyi belge kapsam etiketleri tetikler (production adayı).
     - [x] **EXP-028 production** (2026-10-16): EXP-027 + `fixed_answers="summer_v1"`. Deney koşulmadı (mimari
           değişmedi); 9/9 yaz sorusu sabit cevabı aldı, diğer 130 soruda eşleşme yok.
     - Kapsam kararı kesin (2026-10-16): kuralı fakülteye göre değişen sorularda genel kural verilir ve fakülte
       sorulur; retrieval tarafında kapsam tamamlama yapılmaz.
     - [ ] **Havuz derinliği A** (retrieval-only, kota harcamaz): `vector_k` 15 → 30, `bm25_k` 15 → 30,
           `rerank_candidates` 30. İki parametre birlikte (`coklu_degisiklik_gerekcesi`: havuz derinliği tek kavram,
           iki liste simetrik). Birincil metrik `rerank_input_recall` (EXP-027: 0,966), ikincil final MRR@10.
           Not: birleşim 60 adaya çıkabilir; reranker yalnız RRF'in ilk 30'unu görür.
     - [ ] **Havuz derinliği B:** A + `rerank_candidates` 30 → 60 (havuzun tamamı). Gecikme ölçülür (sunucu kapalı).
     - [ ] **Hybrid + reranker ablasyonu:** `retrieval` hybrid → vector, aday sayısı eşit. Soru: BM25 havuza
           reranker'ın kullandığı aday katıyor mu? (Reranker'ın gerekliliği aşama metriklerinden belli: EXP-027'de
           RRF 0,629 → final 0,818.)
     - [ ] **Cevap uzunluğu:** netleştirmede model diğer kapsamları sayıp sonra soruyor (ör. kayıt dondurmada 2635
           karakter). Hedef: önce genel kural, sonra fakülte sorusu. Olumlu biçim tarif eden prompt deneyi.
     - [ ] **3. Prompt: cevap yoksa** yalnız "bilgim yok" (ilgisiz bilgi ekleme).
     - [ ] **4. Birleştirme:** gelen kurallar karşılaştırılır, aynı kural tek satırda verilir ("Lisans (Hukuk
           dahil): 240 AKTS"); yalnız farklı olanlar ayrı yazılır. Prompt deneyi.
     - [ ] **Set etiketi:** açık öğretimden örgün öğretime yatay geçiş not ortalaması 80 → 90 (kredi transferi
           yönetmeliği 28/2/2026 değişikliği); bir sonraki set sürümünde. Çelişki değil: normal yatay geçiş (80) ile
           açık öğretimden örgün öğretime geçiş (90) ayrı kurallar; model doğru cevap verdi.
   - [ ] **Veriden öğrenme:** Yeterli gerçek kullanıcı sorusu birikince, sistemin hangi soru türlerinde hata yaptığı
         analiz edilir. Gerçek sorulardan seçilenler yeni bir soru seti sürümü olarak eklenebilir (eski setler değiştirilmez).
   - [ ] **Atıfta fıkra (yapılacak):** LLM şu an atıflarda fıkra yazmıyor (2026-10-08: log'daki 64 atıfın
         hiçbirinde yok), bu yüzden panelde fıkra vurgulanamıyor. Fıkrayı yazdırmak bir prompt değişikliği, yani deney.
   - [ ] **Soru setleri: dev / validation / test** (overfitting): set 4.1 dev seti (ayar, eşik seçimi) olarak
         kalır. Aynı corpus'tan sıfırdan yazılmış ayrı bir validation seti, dev'de seçilen eşik ve kararları
         doğrular (ör. EXP-027'nin netleştirme tetiği set 4.1'de hem seçildi hem ölçüldü). Kilitli test seti tezin
         sonunda bir kez (aşağıda "Diğer açık işler").
   - [ ] **Incremental indexing:** şu an parmak izi bütün PDF'leri kapsıyor; tek belge değişince index baştan
         kuruluyor (corpus v4: 3753 chunk, 341 sn). Öneri: belge bazında cache (PDF byte'ları + chunking
         parametreleri + `ingest.py` hash'i → o belgenin chunk'ları ve embedding'leri `vectorstore/_cache/`),
         index `FAISS.from_embeddings` ile birleştirilir; parmak izi sistemi aynen kalır. Doğrulama: cache'li ve
         baştan kurulan index aynı chunk'lar ve set 4.1'de aynı sıralama. Mimari değişiklik, önce onay.

3. [ ] **Ders programları** — duyurular kapsam dışı (2026-10-15). Akademik takvim mevcut chunking ile sorunsuz
       okunuyor. Ders programları ayrı bir scraping ile alınacak, büyük ihtimalle CSV (2026-10-16); tablo olduğu
       için chunk yerine yapılandırılmış saklama (dönem, bölüm, gün, saat, ders, derslik) + tool ile sorgulama
       düşünülüyor (mimari değişiklik, önce onay).
   - [ ] Scraping kaynağı ve CSV şeması. Her dönemin verisi `donem` metadata'sıyla.
   - [ ] Tablo verisi için yeni chunking veya yapılandırılmış saklama (ör. SQL) — deney olarak.
   - [ ] Ders programı soruları için yeni soru seti sürümü (ör. "Salı günü 3. sınıfın hangi dersleri var?").

4. [ ] Diğer bilgiler (birim sayfaları, iletişim...).

5. [ ] **Araç kullanan ajan (tool calling): transkripte göre mezuniyet hesabı** — model yalnız cevap üretmez, fonksiyon
       çağırır. Senaryo: öğrenci transkriptini (PDF) yükler ve "Bilgisayar mühendisliği okuyorum, mezun olmak için
       kaç kredi daha lazım?" diye sorar. Ajan transkripti okur, AKTS'yi toplar, yönetmelikten mezuniyet kuralını
       çeker, farkı hesaplar ve hesabı adım adım gösterir (mimari değişiklik, önce onay).
   - [ ] **Araçlar:** `transkript_oku` (PDF → ders listesi: kod, ad, AKTS, harf notu, dönem), `mevzuat_ara`
         (mevcut `Retriever`, kaynakla birlikte), `hesapla` (toplam AKTS, başarılı dersler, GANO; aritmetik LLM'e
         bırakılmaz, Python'da yapılır). Gemini function calling (`langchain-google-genai` `bind_tools`) ile.
   - [ ] **Transkript formatı:** OBS / e-Devlet transkripti örneği gerekli (kendi transkriptin ile başla). Okuma
         önce kuralla (pdfplumber tablo), olmazsa LLM ile yapılandırılmış çıktı.
   - [ ] **Bölüm müfredatı:** "Kaç kredi" yönetmelikten çıkar (lisans 240 AKTS), ama "hangi zorunlu dersler eksik"
         için bölümün müfredatı (Bologna sayfası, zorunlu/seçmeli listesi) gerekir; şu an corpus'ta yok. İlk sürüm
         yalnız kredi hesabı + genel kurallar (GANO şartı, FF/DZ dersler); müfredat ikinci adım.
   - [ ] **Kişisel veri:** Transkript kişisel veri; yalnız oturum boyunca bellekte tutulur, `logs/sohbet.jsonl`'a
         ve diske yazılmaz. Arayüzde bunu söyleyen not.
   - [ ] **Değerlendirme:** Cevabı bilinen sentetik transkriptler (ör. 180 AKTS, iki FF'li, GANO 1.90) + yeni soru
         seti. Ölçülecekler: hesap doğruluğu, doğru kural/kaynak, araç çağrısı sayısı, gecikme, LLM istek sayısı
         (her araç turu bir istek; günlük 500 kota).

## Belki (kesin değil)

Yapılıp yapılmayacağı henüz belli değil; karar verilirse numaralı sıraya alınır.

- [ ] **Agentic retrieval** — şu an pipeline sabit: soru → bir kez retrieval → cevap. Agentic retrieval'da model
      aramayı kendisi yönetir: gerekirse soruyu yeniden yazar, birden fazla arama yapar (ör. kapsam sorularında
      her fakülte için ayrı arama), bulduğu context yetmiyorsa tekrar arar, yeterli olunca cevaplar.
   - Araştırma (2026-10-16): RAG-Study-Notes `learning_log/agentic_retrieval_arastirma.md` (sorgu genişletme,
     router, CRAG, Self-RAG, multi-hop, tool calling agent, multi-agent; artı/eksi, kota ve latency). Karar bekliyor.
   - Kapsam sorununda katkısı az (çözüm netleştirme); öğrenci dili, karşılaştırma soruları ve havuz dışı
     sorularda işe yarayabilir.
   - Maliyet: soru başına birden fazla LLM isteği (kota ve latency artar); davranış daha az öngörülebilir.
   - Yapılırsa deney olarak: production config'e karşı aynı soru setinde (MRR, kapsam isabeti, çekimser kalma,
     LLM istek sayısı, latency). Madde 5'teki tool calling altyapısını paylaşır, o yüzden ondan sonra mantıklı.

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

- [ ] Tez için kilitli test seti: corpus tamamlandıktan sonra (duyurular, ders programı vb. eklenince) o günkü belgelerden **yeni yazılan** sorularla kurulur; deneylerde kullanılan setlerden seçilmez. Gruplara (A/B/C/D) göre dengeli, yalnız tezin sonunda bir kez koşulur.
- [ ] Hybrid search ve reranker production'da kalsın mı? (Büyük corpus'ta yeniden ölçülmeli.)
