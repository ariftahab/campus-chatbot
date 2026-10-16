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
     - [x] **Havuz derinliği A** (EXP-029, retrieval-only, kota harcamaz): `vector_k` 15 → 30, `bm25_k` 15 → 30,
           `rerank_candidates` 30. İki parametre birlikte (`coklu_degisiklik_gerekcesi`: havuz derinliği tek kavram,
           iki liste simetrik). Birincil metrik `rerank_input_recall` (EXP-027: 0,966), ikincil final MRR@10.
           Not: birleşim 60 adaya çıkabilir; reranker yalnız RRF'in ilk 30'unu görür.
          Sonuç: 0,966 -> 0,974 (+1 soru, kayıp yok), MRR aynı, latency 329 -> 562 ms. Production'a alınmadı
          (karar bekliyor). Havuzdaki her ilgili chunk zaten RRF'in ilk 30'unda → B'nin recall kazancı olamaz.
     - [x] **Havuz derinliği B** (EXP-030): A + `rerank_candidates` 30 → 60. Recall aynı, MRR 0,819 → 0,818
          (2 soru biraz düştü), latency 562 → 892 ms. Alınmadı.
     - [x] **Hybrid + reranker ablasyonu** (EXP-031, üst deney EXP-029): vector-only'de BM25'in getirdiği tek soru
          kayboldu (recall 0,974 → 0,966), 3 soru biraz iyileşti, MRR aynı (0,820).
    - [x] **Latency yeniden ölçümü** (2026-10-16, GPU boş): EXP-027, -029, -030, -031 tek süreçte, tek Retriever
          ile, soru başına sıra karıştırılarak, 3 tur (soru başına medyan). Ortalama latency: EXP-027 347 ms,
          EXP-029 437, EXP-030 687, EXP-031 430 ms. Latency'yi belirleyen reranker'a giren aday sayısı: ~14 ms/aday
          (EXP-027'de 15+15 listenin birleşimi ortalama 23,5 aday; EXP-029 ve -031'de hep 30; EXP-030'da 47,7).
          Eski ölçümlerdeki 562 / 892 ms GPU paylaşımından şişmişti. Hybrid ile vector arasında latency farkı yok
          (BM25 ucuz).
    - [x] **Production kararı** (2026-10-16): A alındı, hybrid kaldı. EXP-032 = EXP-029 + yaz okulu sabit cevabı
          (koşu yok; 9/9 yaz sorusu sabit cevap). Production EXP-028 → EXP-032.
    - **Prompt deneyleri (2026-10-16, onaylı; Gemini kotası bittiği için koşular 2026-10-17'de).** Sıra: önce
      baseline, sonra deneyler tek tek; her biri bir öncekinin sonucu yorumlandıktan sonra.
      - [ ] **EXP-033 baseline:** production (EXP-032) set 4.2'de (`--llm`, ~140 istek). Config commit'li.
      - [ ] **EXP-034 cevap uzunluğu:** `clarify_prompt` v4 → `v5_netlestirme_kisa` (genel kural + "farklı
            olabilir" + fakülte sorusu; biçim tarif edilir). Birincil: `netlestirme_uzunlugu` (EXP-027'de 602
            karakter), netleştirme isabeti ve cevap doğruluğu düşmemeli. Config commit'li.
      - [ ] **EXP-035 model:** `llm_model` gemini-3.1-flash-lite → gemini-3.5-flash-lite (kullanıcının hipotezi: yeni
            model system prompt'a daha iyi uyar). 3.5'in ayrı kotasıyla 2026-10-16'da koşuldu; EXP-033 koşulunca
            `python -m experiments.run EXP-035 --karsilastir` ile karşılaştırma tamamlanır. Sonraki prompt deneyleri
            hangi modelle yapılacak, buna göre karar verilir.
            Ara sonuç (eşleştirilmiş test EXP-033'ten sonra): cevap doğruluğu 0,973; EXP-027'nin (3.1, retrieval biraz
            farklı) aynı 139 sorusuna göre 0,921 → 0,971 (8 soru düzeldi, 1 bozuldu; en çok çekimser kalma ve kapsam
            gruplarında). Gereksiz netleştirme 0,26 → 0,19, netleştirme cevapları 602 → 496 karakter, birleştirme 4/10.
            **LLM latency ~5 kat**: ortalama 14,5 sn (medyan 10,3), 3.1'de ~3 sn. Karar latency'yi de içermeli.
      - [ ] **EXP-036 birleştirme:** `prompt_version` v3_kapsam → `v5_birlestirme` (v3'teki "ayrı ayrı yaz" ile
            "tekrar etme" çelişkisi kaldırıldı). Birincil: `birlestirme_isabeti` (set 4.2 grup E, 10 soru). Üst deney
            EXP-034 kabul edilirse EXP-034, edilmezse EXP-033; config bu yüzden EXP-034'ten sonra yazılacak.
      - [ ] **EXP-037 atıfta fıkra:** `citation_style` madde → fikra. Birincil: `fikra_atif_orani` (EXP-027: 0,023),
            ikincil `fikra_dogrulugu` (kanıt cümlesi atıf yapılan fıkrada mı). Üst deney kabul edilen son deney.
            Panelde fıkra vurgusu ayrı UI işi (atıf linki "Madde 24/2" ile bozulmuyor).
      - [ ] **Netleştirmeden sonra yönetmeliği olmayan fakülte (2026-10-16 teşhisi):** kullanıcı fakültesini söyleyince
            (ör. "Mühendislik fakültesi") ne oluyor? Teşhis script'i: `experiments/teshis_takip_netlestirme.py`.
            - **(Öncelikli) Geçmişe bakma:** tetik yalnız tıp/diş/hukuk/lisansüstü/önlisans adlarını tanıdığı için
              ikinci turda netleştirme yine açılıyor (6 senaryonun 4'ünde). 3.5 bunu fark edip 6/6 tekrar sormadı; 3.1
              talimata daha harfiyen uyduğu için tekrar sorabilir (döngü). **Yarın 3.1 ile script koşulacak (~18 istek);
              tekrar sorarsa:** önceki asistan mesajı fakülteyi sorduysa netleştirme açılmaz (`clarify_trigger`'a yeni
              değer, deney).
            - Tetik herhangi bir birim adını tanısın ("… fakültesi", "… yüksekokulu", "MYO", "… bölümü"): birim adı
              geçiyorsa netleştirme açılmaz; ana prompt'taki "özel düzenleme yoksa genel kuralı ver" kuralı çalışır.
            - **Yeni bulgu (retrieval):** rewrite fakülte adını sorguya ekleyince o fakültenin ilgisiz belgeleri
              geliyor. "Ziraat Fakültesi öğrencilerinin okulu en fazla kaç yılda bitirmesi gerekmektedir?": ilk 4 chunk
              ziraat staj yönergesi, genel azami süre maddesi ilk 10'da yok → "bilgim yok". Fakülte adı olmadan aynı
              madde 1. sırada. Fikir: kendi yönetmeliği olmayan birim adı retrieval sorgusundan çıkarılır (ya da iki
              sorguyla aranıp birleştirilir); LLM'e giden soruda kalır. Deney; ölçmek için önce bu senaryoları içeren
              küçük bir takip seti gerekir.
            - 1. tur gözlemi (mazeret sınavı sorusu): genel yönetmeliğin kanıt chunk'ı 11. sırada; Madde 29 6 parçaya
              bölünmüş, kural 9. fıkrayla (ilgisiz konu) başlayan parçada, reranker puanı düşük (0,453). Aynı maddenin
              rapor fıkrası 2. sırada. Takip sorusunda ("Mühendislik fakültesi") sorgu "final sınavına mazeret"
              içerdiği için 2. sıraya çıktı.
      - [-] **Cevap yoksa yalnız "bilgim yok":** kullanıcı kararıyla atlandı (2026-10-16).
      - [x] **Set etiketi 80 → 90:** set 4.2'de (kredi transferi yönetmeliği kaynak olarak eklendi).
      - [ ] **Set etiketi (sonraki sürüm):** "Kaç gün rapor hakkım var?" sorusu "dahil" (rapor günleri devamsızlığa
            dahil) bekliyor; corpus'ta gün sayısı yok, kullanıcı kararı: "bilgim yok" doğru (2026-10-16).
   - [ ] **Veriden öğrenme:** Yeterli gerçek kullanıcı sorusu birikince, sistemin hangi soru türlerinde hata yaptığı
         analiz edilir. Gerçek sorulardan seçilenler yeni bir soru seti sürümü olarak eklenebilir (eski setler değiştirilmez).
   - [ ] **Soru setleri: dev / validation / test** (overfitting): set 4.1 dev seti (ayar, eşik seçimi) olarak
         kalır. Aynı corpus'tan sıfırdan yazılmış ayrı bir validation seti, dev'de seçilen eşik ve kararları
         doğrular (ör. EXP-027'nin netleştirme tetiği set 4.1'de hem seçildi hem ölçüldü). Kilitli test seti tezin
         sonunda bir kez (aşağıda "Diğer açık işler").
     - [x] Validation taslağı: `eval/taslak/sorular_val_v1_taslak.json` (44 soru, set 4.x'te sorulmamış belgelerden;
           kanıtlar doğrulandı). **Kullanıcı düzeltecek**, sonra `eval/sorular_val_v1.json` olarak eklenir.
   - [x] **Incremental indexing** (2026-10-16): belge bazında cache (`vectorstore/_cache/`, anahtar: PDF byte'ları + belge
         ayarı + indeks parametreleri + `ingest.py`). Doğrulama: soğuk kurulum eski indeksle bit-aynı (chunk'lar ve
         vektörler, fark 0); sıcak kurulum 316 sn → 0,2 sn; 3 belge yeniden embed edilince 8,5 sn, vektör farkı en çok
         3,4e-7, set 4.2'nin 149 sorusunda ilk 10 sıralama aynı. `ingest.py` değişince bütün cache geçersizleşir
         (kod chunking'i değiştirmiş olabilir).

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
