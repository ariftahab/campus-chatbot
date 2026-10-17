# campus-chatbot
Making chatbot assistant for university

Bolu Abant İzzet Baysal Üniversitesi belgeleri (akademik takvim, yönetmelikler) üzerinden
soru cevaplayan bir RAG chatbot. Bitirme projesi; RAG bileşenlerindeki her değişiklik
tekrar üretilebilir bir deney olarak kaydedilir (bkz. `experiments/experiment_log.md`).

## Kurulum

```bash
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

Proje köküne `.env` dosyası oluşturup Gemini anahtarını ekleyin:

```
GOOGLE_API_KEY=...
```

## Kullanım

```bash
python chat.py                          # sohbet ('çık' ile çıkılır, 'yeni' geçmişi temizler)
python ingest.py [EXP-ID]               # bir yapılandırmanın indeksini elle kur (normalde otomatik)
python -m experiments.run EXP-008       # bir deneyi koş (retrieval metrikleri, API çağrısı yok)
python -m experiments.run --all         # sonucu olmayan tüm deneyleri koş
python -m experiments.run EXP-010 --llm # cevap doğruluğunu da ölç (Gemini kotası harcar)
python -m experiments.report            # deney günlüğünü yeniden üret
python experiments/teshis_alt_kume.py   # bir değişikliği yalnız seçilen sorularda dene (deney değil)
```

Sohbet uygulaması `config.PRODUCTION_EXPERIMENT` ile seçilen deneyin parametreleriyle çalışır.
İlk çalıştırmada embedding ve reranker modelleri (~6.5 GB) indirilir.

## Yeni deney ekleme

1. `experiments/configs/` altındaki bir deneyi kopyalayıp yeni kimlik verin (`EXP-011.json`).
2. `ust_deney`'i karşılaştırılacak deney yapın ve `params` içinde **yalnız bir** parametreyi değiştirin.
3. `neden`, `hipotez`, `birincil_metrik` ve `beklenen_yon` alanlarını deneyi koşmadan önce doldurun.
4. Kodu commit edin, sonra `python -m experiments.run EXP-011` çalıştırın.
5. Sonucu yorumlayıp `notlar` alanına yazın, `python -m experiments.report` ile günlüğü güncelleyin ve commit edin.

## Yeni belge ekleme

PDF'i `data/` klasörüne koyup `config.py` içindeki `DOCUMENTS`'a başlığını ve türünü yazın.
Belgeler değişince indeksler kendiliğinden yeniden kurulur. Ancak eski deney sonuçları eski belgelerle
ölçüldüğü için yeni belgelerle yapılan ölçümlerle karşılaştırılamaz.
