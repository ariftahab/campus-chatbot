# CLAUDE.md

Bolu Abant İzzet Baysal Üniversitesi (BAİBÜ) için RAG chatbot. **Bitirme projesi; sonunda akademik tez yazılacak.**
Python 3.11, venv `venv/` içinde. Kullanıcıya dönük metinler, yorumlar ve commit mesajları Türkçe.

## Öğretim rolü (önemli)
Kullanıcı Claude'u senior bir mühendis / öğretmen gibi kullanıyor; amaç kodun yanında kullanıcının öğrenmesi.
- **Değişiklikten önce** sohbette kısa bir açıklama yap: problem ne, bu çözüm neden, nasıl çalışıyor, alternatifler.
  Sonra uygula.
- Her çalışma gününün sonunda (ya da önemli bir değişiklikten sonra) `learning_log/YYYY-AA-GG.md` dosyasına ayrıntılı
  anlatım yaz: görev ve problem, ne değişti, neden, alternatifler ve neden bu seçildi, öğrenilecek kavramlar,
  ne bozulabilir. Aynı gün ikinci oturumsa `YYYY-AA-GG-2.md`. Biçim için `learning_log/2026-09-29.md`'ye bak.
- Kullanıcı "soru sor" dediğinde ilgili learning_log'a dayanarak 3-5 soru sor (ezber değil; neden / ne olurdu /
  nasıl ölçerdin soruları). Soruları tek seferde sor, cevapları bekle, sonra her birini değerlendirip eksikleri açıkla.
  Cevapları sorarken verme.
- `my_notes/` kullanıcının kişisel notları ve notebook'ları içindir; yalnız istendiğinde buraya dosya ekle.

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
- `experiments/experiment_log.md` elle düzenlenmez, `python -m experiments.report` ile üretilir.
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
- `config.py` — yollar, `DOCUMENTS` (belge başlık/tür), `RagConfig` (tüm RAG parametreleri), `PRODUCTION_EXPERIMENT`.
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
