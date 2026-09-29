# campus-chatbot
Making chatbot assistant for university

Bolu Abant İzzet Baysal Üniversitesi belgeleri (akademik takvim, yönetmelikler) üzerinden
soru cevaplayan bir RAG chatbot.

## Kurulum

```bash
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

Proje köküne `.env` dosyası oluşturup Gemini anahtarını ekleyin:

```
GOOGLE_API_KEY=...
# GEMINI_MODEL=gemini-2.5-flash   (isteğe bağlı)
```

## Kullanım

```bash
python chat.py      # sohbet ('çık' ile çıkılır, 'yeni' geçmişi temizler)
python ingest.py    # indeksi elle yeniden kur (normalde otomatik)
python eval.py      # getirme kalitesini ölç (API çağrısı yapmaz)
python eval.py --llm  # cevap kalitesini de ölç (Gemini kotası harcar)
```

İlk çalıştırmada embedding ve reranker modelleri (~4.5 GB) indirilir.
Yeni belge eklemek için PDF'i `data/` klasörüne koyup `config.py` içindeki `DOCUMENTS`'a
başlığını ve türünü yazın; indeks bir sonraki açılışta kendiliğinden yenilenir.
