# CLAUDE.md

Bolu Abant İzzet Baysal Üniversitesi (BAİBÜ) için RAG chatbot. **Bitirme projesi; sonunda akademik tez yazılacak.**
Python 3.11, venv `venv/` içinde. Kullanıcıya dönük metinler, yorumlar ve commit mesajları Türkçe.

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

**Dil / terim kuralı:** Cümleler Türkçe, **teknik terimler İngilizce** ve çevrilmeden: branch, commit, push, chunk,
chunking, embedding, token, retrieval, reranker, vector store, index, pipeline, baseline, hypothesis, evaluation,
dataset, context, latency, prompt, hash, fingerprint vb. ("dal", "parçalama", "getirme", "gecikme" gibi çeviriler
kullanılmaz.) Sohbet, learning_log, experiment log ve deney başlıkları için geçerli.

`my_notes/` kullanıcının kendi notları ve notebook'ları içindir; yalnız istendiğinde dosya ekle.
## Deney disiplini (önemli)
RAG bileşenlerindeki (PDF okuma, parçalama, chunk size/overlap, embedding, getirme yöntemi, k, reranker, prompt, LLM)
her değişiklik "kod iyileştirmesi" olarak değil, **deney** olarak yapılır:
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
- `eval/sorular.json` değişirse veri seti hash'i değişir ve eski sonuçlarla karşılaştırma geçersiz olur.
  Soru eklemek gerekiyorsa sürümü artır ve referans zinciri yeniden koşulmalı.
- Commit mesajları ayrıntılı olmalı (ne, neden, sayısal sonuç); tezde kaynak olarak kullanılacak.

## Komutlar
- `venv/Scripts/python.exe chat.py` — sohbet (`config.PRODUCTION_EXPERIMENT` yapılandırmasıyla)
- `venv/Scripts/python.exe -m experiments.run EXP-XXX [--llm] [--yeniden]` / `--all`
- `venv/Scripts/python.exe -m experiments.report`
- `venv/Scripts/python.exe ingest.py [EXP-ID]`
- Windows'ta Türkçe çıktı için `PYTHONIOENCODING=utf-8` gerekebilir.

## Mimari
- `config.py` — yollar, `CORPORA` (belge kümeleri: v1 = 3 belge, v2 = `data/corpus_v2.txt`'deki 139 belge),
  `DOCUMENTS` (belge başlık/tür), `RagConfig` (tüm RAG parametreleri), `PRODUCTION_EXPERIMENT`.
- `ingest.py` — `pdf_parser` (pypdf | pdfplumber) ve `chunking` (recursive | structural). Structural: mevzuat madde madde
  ("Madde N-"), eşiği aşan maddeler fıkra sınırından bölünür; takvimde her tablo bir parça. İndeks
  `vectorstore/<parmak izi>/` altında (PDF'ler + indeks parametreleri + ingest.py kaynağı); yoksa otomatik kurulur.
- `rag.py` — `Retriever.rank()`: vector | bm25 | hybrid (RRF) + isteğe bağlı cross-encoder reranker. `PROMPTS` sürümleri.
  `RagBot`: geçmiş varsa soruyu bağımsız hale getirir, Gemini ile cevaplar.
- `chat.py` — CLI.
- `experiments/evaluation.py` — kanıt tabanlı ilgililik (parçalamadan bağımsız), metrikler (MRR@10, Hit@k, bağlam isabeti,
  bağlam uzunluğu, gecikme, cevap doğruluğu), McNemar/Wilcoxon, ortam kaydı.
- `experiments/run.py` — deney koşucu, `experiments/report.py` — günlük üretici.
- `eval/sorular.json` — 27 cevaplı + 3 kapsam dışı soru; her soruda kaynakta birebir geçen `kanit`.

## Notlar
- LLM: Gemini (`langchain-google-genai`), `.env` içinde `GOOGLE_API_KEY`. Ücretsiz kota günde 20 istek (gemini-2.5-flash);
  `--llm` değerlendirmesi 30 istek sürer, günlere bölünmesi gerekebilir.
- Donanım yalnız CPU; reranker sorgu başına birkaç saniye ekler.
- `langchain-core` 1.0.4'e sabit; yükseltme diğer langchain paketleriyle uyumu bozabilir.
- Eski tek dosyalık prototip `main` dalında ve `yedek-oncesi` etiketinde (`prototip-chat.py`); EXP-000 onu yeniden üretir.
