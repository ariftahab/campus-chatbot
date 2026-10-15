# CLAUDE.md

Bolu Abant İzzet Baysal Üniversitesi (BAİBÜ) için RAG chatbot. **Bitirme projesi; sonunda akademik tez yazılacak.**
Python 3.11, venv `venv/` içinde. Kullanıcıya dönük metinler ve yorumlar Türkçe; commit mesajları İngilizce (aşağıya bak).

## Öğretim rolü (önemli)
Claude bu projede yalnız kod yazan bir araç değil, öğretici bir pair programmer / mentor. Bitirme projesi; kullanıcının
mimariyi gerçekten anlaması gerekiyor. Yapılan işi sadece özetleme, arkasındaki teknik mantığı öğret.

**Büyük mimari değişikliklerden önce** (yeni bileşen, yöntem değişikliği, veri akışını değiştiren şeyler): uygulamadan
önce neyi değiştireceğini, neden, alternatifleri ve beklenen etkisini açıkla ve **onay bekle**. Küçük ve mekanik
değişikliklerde (yazım, biçim, küçük düzeltme) doğrudan ilerlenebilir.

**Yalnız kullanıcı açıkça istediğinde** ("10 maddelik şeyi yaz" vb.) sohbette şu 13 bölümü yaz. Her görevden sonra
otomatik yazılmaz; normalde kısa ve öğretici bir açıklama yeterli:
1. TASK — benden ne istendi
2. PROBLEM — hangi problem çözülüyordu
3. CURRENT ARCHITECTURE — değişiklik sistemin hangi kısmını etkiliyor
4. CHANGES — hangi dosyada ne değişti
5. WHY — neden
6. ALTERNATIVES — hangi alternatifler vardı
7. WHY THIS APPROACH — neden bu seçildi
8. IMPORTANT CONCEPTS — öğrenilecek kavramlar ve açıklamaları
9. FAILURE MODES — hangi durumlarda başarısız olur
10. EXPERIMENT — deneyse: hypothesis, variables, baseline, result, interpretation
11. BEFORE / AFTER — eski ve yeni mimari farkı
12. LEARNING QUESTIONS — 3-5 soru sor. Cevapları verme; kullanıcının cevabını bekle, sonra değerlendir ve düzelt.
    Sorular **kendi başına anlaşılır** olmalı: iç kodlar (Y01, EXP-008, "Madde 8/2") ve daha önce açıklanmamış
    kavramlar kullanılmaz; her soru o görevde anlatılan bir kavramın ne işe yaradığını sorar.
(13. EXPLAIN IT YOURSELF — kullanıcının isteğiyle şimdilik kaldırıldı.)

Kullanıcı bir öğrenci ve öğrenmeye açık; **amaç projeyi hızla bitirmek değil, kullanıcının öğrenmesi**. Ne yapıldığını,
hangi kavramların kullanıldığını ve ne işe yaradıklarını anlatmaya öncelik ver. Kullanıcı "şu günün log'una dokunma"
derse dokunma.

**Her gün sonunda** `learning_log/YYYY-MM-DD.md`: kullanıcının **ders çalışır gibi okuyabileceği** study notes.
Yoğun, ansiklopedik metin yazma. Biçim için `learning_log/2026-09-29.md`'ye bak:
- Büyük resim (pipeline diyagramı + bir örnek sorunun gerçek yolculuğu)
- Concept kartları: **Nedir? → Basit örnek → Bizim projede (projeden ölçülmüş gerçek sayılar) → Dikkat**
- Kısa deney tablosu ve 2-3 ana ders
Kullanıcının kendi notlarının yerine geçmemeli; amaç anlamasını sağlamak. Aynı gün ikinci oturumsa `YYYY-MM-DD-2.md`.

**Günlüklerin yeri:** Study notes ve günlükler bu repoda değil, ayrı private repo **RAG-Study-Notes**'ta
(GitHub: `Kuwoka/RAG-Study-Notes`, yerelde `C:\GitHub\RAG-Study-Notes`). Aşağıdaki yollar o repoya göredir;
o repodaki değişiklikler orada ayrıca commit/push edilir.
- `learning_log/YYYY-MM-DD.md`: study notes (yukarıdaki biçim).
- `daily_log/YYYY-MM-DD.md`: günün yapılan işler özeti (tablo + commit'ler). Biçim: `daily_log/2026-10-06.md`.
- `learning_log/frontend_backend_log.md`: arayüz ve API'deki her adım (ne, neden, alternatifler, kavram kartları).
- `experiments/experiment_log.md`: deney günlüğü (elle düzenlenmez, `experiments.report` üretir).

**Dil / terim kuralı:** Cümleler Türkçe, **teknik terimler İngilizce** ve çevrilmeden: branch, commit, push, chunk,
chunking, embedding, token, retrieval, reranker, vector store, index, pipeline, baseline, hypothesis, evaluation,
dataset, context, latency, prompt, hash, fingerprint vb. ("dal", "parçalama", "getirme", "gecikme" gibi çeviriler
kullanılmaz.) Sohbet, learning_log, experiment log ve deney başlıkları için geçerli.

**Kod değil bağlam kuralı:** Değerlendirme sorularının kimlikleri (K08, Y01, T05, N33...) ve "Madde 8/2" gibi kısaltmalar
**hiçbir yerde** tek başına yazılmaz: experiment log (`notlar`, `kisa_not`), learning_log, my_notes, commit mesajları,
sohbet. Her zaman **sorunun kendisi** ("Üniversitenin öğretim dili nedir?") ve **bağlamı** ("Yatay Geçiş Yönergesi'nin
başvuru şartları maddesi") yazılır. Kimlikler yalnız `eval/*.json` ve `results/*.json` gibi makine dosyalarında kalır.

`my_notes/` (RAG-Study-Notes içinde) kullanıcının kendi notları ve notebook'ları içindir; yalnız istendiğinde dosya ekle.
(Claude'un yazdığı özetler `daily_log/` ve `learning_log/` klasörlerinde.)

## Commit kuralları
Her commit tek bir mantıksal değişiklik içersin, Conventional Commits formatında, İngilizce, ilk satır 70 karakteri
geçmesin, gövdede sadece neden yazılsın.
## Deney disiplini (önemli)
RAG bileşenlerindeki (PDF okuma, parçalama, chunk size/overlap, embedding, getirme yöntemi, k, reranker, prompt, LLM)
her değişiklik "kod iyileştirmesi" olarak değil, **deney** olarak yapılır:
- **Onay kuralı:** Her deneyden önce sohbette neden yapılmak istendiği, hipotez ve neyin ölçüleceği (ve mevcut
  değerlendirme setiyle neyin ölçülemeyeceği) yazılır; kullanıcının **açık onayı** olmadan config yazılmaz, deney
  koşulmaz. Deneyler art arda kendiliğinden zincirlenmez: bir deney biter → sonuç yorumlanır → sonraki önerilir → onay.
- Yeni bir `experiments/configs/EXP-XXX.json` oluştur. Tam parametre seti olmalı, `ust_deney`'den **tek** parametre farklı
  olmalı (runner denetler; zorunluysa `coklu_degisiklik_gerekcesi`).
- `neden`, `hipotez`, `birincil_metrik`, `beklenen_yon` alanları deney **koşulmadan önce** yazılır.
- Eski config/sonuç dosyaları silinmez ve değiştirilmez. Yeni davranış yeni parametre değeriyle eklenir;
  eski kod yolu korunur (ör. `rag.PROMPTS["v1_prototip"]`, `pdf_parser="pypdf"`).
- Kod önce commit edilir, sonra `python -m experiments.run EXP-XXX` koşulur. Sonuç dosyası commit hash'ini kaydeder;
  `git_dirty: true` sonuçlar tekrar üretilebilir sayılmaz.
- Sonuç yorumu config'in `notlar` alanına yazılır. Beklenen iyileşme çıkmadıysa bu da açıkça yazılır.
- `experiments/experiment_log.md` elle düzenlenmez, `python -m experiments.report` ile üretilir. Log **kısa** kalmalı:
  setup (hyperparameter) tablosu, results tablosu ve deney başına tek satır (`kisa_not`). Ayrıntılar `results/*.json` içinde.
- Soru setleri değiştirilmez: bir set değişirse hash'i değişir ve eski sonuçlarla karşılaştırma geçersiz olur. Yeni
  sorular yeni bir set dosyası olarak eklenir; deney config'inde `veri_seti` alanıyla seçilir (yoksa `sorular`).
  Soru eklemek gerekiyorsa sürümü artır ve referans zinciri yeniden koşulmalı.
- Deney commit'leri de "Commit kuralları"na uyar; deneyin ayrıntılı sonucu config `notlar` alanında ve `results/*.json` içindedir.

## Komutlar
- `venv/Scripts/python.exe -m uvicorn app.main:app --port 8000` — arayüz (http://localhost:8000/, /belgeler, /admin) + API (/docs)
- `venv/Scripts/python.exe chat.py` — terminal sohbeti (`config.PRODUCTION_EXPERIMENT` yapılandırmasıyla)
- `venv/Scripts/python.exe -m experiments.run EXP-XXX [--llm] [--yeniden]` / `--all`
- `venv/Scripts/python.exe -m experiments.report`
- `venv/Scripts/python.exe ingest.py [EXP-ID]`
- Windows'ta Türkçe çıktı için `PYTHONIOENCODING=utf-8` gerekebilir.

## Mimari
- `config.py` — yollar, `CORPORA` (belge kümeleri: v1 = 3 belge, v2 = `data/corpus_v2.txt`'deki 139 belge, v3 = v2 eksi 8 kopya, 131 belge, v4 = v3 eksi 2025-2026 takvimi ve yaz öğretimi belgeleri, artı 2026-2027 takvimi, 129 belge; v1-v3'ün bazı PDF'leri data/'dan silindi, yeniden üretmek için sonuçtaki commit'e dönülür),
  `DOCUMENTS` (belge başlık/tür), `RagConfig` (tüm RAG parametreleri), `PRODUCTION_EXPERIMENT`.
- `ingest.py` — `pdf_parser` (pypdf | pdfplumber) ve `chunking` (recursive | structural | structural_v2: genişletilmiş madde regex'i | structural_v3: + belge bütünü fallback). Structural: mevzuat madde madde
  ("Madde N-"), eşiği aşan maddeler fıkra sınırından bölünür; takvimde her tablo bir parça. İndeks
  `vectorstore/<parmak izi>/` altında (PDF'ler + indeks parametreleri + ingest.py kaynağı); yoksa otomatik kurulur.
- `rag.py` — `Retriever.rank()`: vector | bm25 | hybrid (RRF) + isteğe bağlı cross-encoder reranker. `PROMPTS` sürümleri (v1_prototip, v2_kaynakli,
  v3_kapsam: kurallar kapsama göre farklıysa her birini kapsamıyla verir).
  `RagBot` (stateless): geçmişi `ask(question, history)` ile dışarıdan alır, varsa soruyu bağımsız hale getirir, Gemini ile cevaplar.
- `chat.py` — CLI.
- `app/` — UI / API: `service.py` (iş mantığı; `logs/` altında sohbet, geri bildirim, elle değerlendirme JSONL'leri),
  `api.py` (FastAPI), `static/` (HTML/CSS/vanilla JS frontend: sohbet, belgeler, /admin değerlendirme), `main.py`
  (hepsi tek sunucuda). Her adım RAG-Study-Notes'taki `learning_log/frontend_backend_log.md` dosyasına yazılır.
- `experiments/evaluation.py` — kanıt tabanlı ilgililik (parçalamadan bağımsız), metrikler (MRR@10, Hit@k, bağlam isabeti,
  bağlam uzunluğu, gecikme, cevap doğruluğu), McNemar/Wilcoxon, ortam kaydı.
- `experiments/run.py` — deney koşucu, `experiments/report.py` — günlük üretici.
- `eval/sorular.json` (set 2.0) — 27 cevaplı + 3 kapsam dışı soru, yalnız ilk 3 belgeden; EXP-000..016.
- `eval/sorular_v3.json` (set 3.0) — 77 soru: eski 30 + yeni 47 (31 belge). `kaynaklar`: birden fazla doğru kaynak
  (her biri kendi `kanit`'iyle), `stil` (belge/ogrenci dili), `kategori`, cevapsızlarda isteğe bağlı `kabul`.
- `eval/sorular_v4.json` (set 4.0, corpus v4) — 139 soru, `grup`: A bulma, B kapsam (coklu_kapsam'da kapsam isabeti),
  C çekimser kalma, D takip sorusu (`gecmis` ile; koşucu production'daki rewrite'ı önbellekli kullanır). EXP-023'ten beri.
- `eval/sorular_v41.json` (set 4.1) — 4.0 + 4 etiket düzeltmesi; fakülte belirtilmeyen kapsam sorularında hedef
  davranış genel kural + fakülteyi sormak (`beklenen_davranis: netlestirme`, koşucuda `netlestirme_isabeti` /
  `gereksiz_netlestirme`).

## Notlar
- LLM: Gemini (`langchain-google-genai`), `.env` içinde `GOOGLE_API_KEY`. EXP-013'ten beri `gemini-3.1-flash-lite`:
  ücretsiz kota günde 500 istek (eski `gemini-2.5-flash` günde 20 istekti).
- Donanım: NVIDIA RTX 4050 Laptop (6 GB). torch CUDA build'i (`2.9.0+cu128`) kurulu; embedding ve reranker GPU'da
  çalışır. 2026-10-01'e kadar CPU build kuruluydu: EXP-000..013 CPU ile koşuldu, `latency_ms` karşılaştırılamaz.
  GPU, CPU ile birebir aynı sıralamayı veriyor (EXP-013 ile 27/27 soru doğrulandı).
- `langchain-core` 1.0.4'e sabit; yükseltme diğer langchain paketleriyle uyumu bozabilir.
- Eski tek dosyalık prototip `yedek-oncesi` etiketinde (`prototip-chat.py`); EXP-000 onu yeniden üretir.
