# UI / API Geliştirme Günlüğü

Bu dosya chatbot arayüzü ve API'si yazılırken atılan her adımı kaydeder: **ne yapıldı, neden, hangi alternatifler
vardı, neden bu seçildi, ne işe yarıyor.** Her adım bir ders notu gibi okunabilsin diye aynı kalıpta yazılır.

---

## Adım 0 — Mimari kararı (2026-10-06)

### Hedef
Terminal (`chat.py`) yerine bir arayüz. Arayüzde:
- sohbet edilebilmeli,
- sorulan sorular ve cevaplar dosyaya kaydedilmeli (sonradan doğrulukları ölçülecek),
- corpus'taki belgeler görülebilmeli (data sekmesi).

Şimdilik sadece ben kullanacağım. İleride bir hocaya verilebilir veya okul sistemine entegre edilebilir.

### Karar: FastAPI backend + üstünde ince bir Gradio arayüzü

```
Arayüz (değişebilir)     Gradio (/ui)  →  ileride: hocanın sayfası, okul sistemi
        │ HTTP / JSON
API katmanı              app/api.py      FastAPI endpoint'leri, Pydantic şemaları
        │ Python çağrısı
Service katmanı          app/service.py  ask, log yazma, feedback, belge listesi
        │
RAG çekirdeği            rag.py, config.py (mevcut)
```

### Değerlendirilen alternatifler

| Seçenek | Artısı | Eksisi |
|---|---|---|
| Streamlit | En az kodla güzel arayüz, zengin tablolar | Her etkileşimde script baştan çalışır (rerun modeli); dışarı açmak zahmetli |
| Gradio | Hazır sohbet ekranı, hazır 👍/👎 event'i, `share=True` linki | Tasarım esnekliği daha az |
| FastAPI + kendi HTML/JS | Tam kontrol, gerçek ürün mimarisi | En çok iş; zaman RAG yerine web geliştirmeye gider |

### Neden bu seçildi?
- **Sonradan geçiş derdi olmasın.** "Önce Gradio, sonra FastAPI" yolunda log, feedback ve geçmiş yönetimi Gradio
  fonksiyonlarının içine yazılır; geçişte hepsi söküp yeniden yazılır. Asıl sorun framework değil, **iş mantığının
  (business logic) arayüze yapışması.** API'yi baştan kurunca entegrasyon günü sadece en üst katman değişir.
- **FastAPI deneyimi** (CV için): endpoint, Pydantic, Swagger, lifespan, stateless tasarım.
- **Gradio API'ye HTTP ile bağlanacak** (fonksiyonları doğrudan çağırmayacak). Böylece arayüz, ileride okul sisteminin
  kullanacağı yolun aynısını kullanır. API'nin ilk istemcisi (client) biz oluruz ve onu her gün test etmiş oluruz.

### Kavram: Katmanlı mimari (layered architecture) / separation of concerns
- **Nedir?** Her katman tek bir işten sorumludur ve sadece bir altındaki katmanı bilir.
- **Basit örnek:** Restoranda garson (arayüz) yemeği pişirmez. Siparişi mutfağa (service) iletir, mutfak da kilerden
  (veri / model) malzeme alır. Garson değişse de mutfak aynı kalır.
- **Bizim projede:** Log yazma service katmanında olacak. Soru Gradio'dan da gelse, hocanın sisteminden de gelse aynı
  şekilde kaydedilir.
- **Dikkat:** Arayüz koduna "bir de şunu kaydedeyim" diye mantık eklemek cazip gelir. Eklenmemeli, service'e gitmeli.

---

## Adım 1 — `RagBot`'u stateless yapmak (2026-10-06)

### Ne yapıldı?
- `rag.py`: `RagBot` artık sohbet geçmişini kendi içinde (`self.history`) tutmuyor. `reset()` kaldırıldı.
  `ask(question, history)` ve `retrieve(question, history)` geçmişi parametre olarak alıyor.
- Geçmişin biçimi: `[{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]`.
  Yeni `_to_messages()` fonksiyonu bunu LangChain mesajlarına çeviriyor ve son 6 mesajı (`config.HISTORY_MESSAGES`) alıyor.
- `chat.py`: geçmişi artık kendisi bir listede tutuyor. Her cevaptan sonra listeye ekliyor, "yeni" yazılınca boşaltıyor.
- `experiments/run.py`: `bot.reset()` satırı kaldırıldı. Deneylerde her soru zaten geçmişsiz soruluyordu; şimdi
  `ask(soru)` geçmiş vermeden çağrılıyor. **Davranış birebir aynı**, eski deney sonuçları geçerliliğini korur.

### Neden?
Web'de birden fazla oturum (session) aynı anda açık olabilir: sen iki sekme açarsın, ileride hocan da bağlanır.
Modeller (bge-m3, reranker) GPU'da **tek kopya** olarak yüklü ve paylaşılıyor. Geçmiş botun içinde dursaydı, A'nın
sorusu B'nin "peki son günü ne?" sorusunu yeniden yazarken karışırdı. Çözüm: **ağır ve ortak olan (modeller)
paylaşılır, kişiye özel olan (geçmiş) çağıran tarafta tutulur.**

### Alternatifler
1. **Stateful API:** sunucu `{session_id: geçmiş}` sözlüğü tutar, istemci her istekte `session_id` gönderir.
   Eksisi: sunucu yeniden başlayınca geçmişler kaybolur, birden fazla sunucuya ölçeklemek zorlaşır, kapatılmayan
   oturumlar bellekte birikir.
2. **Her oturuma ayrı `RagBot`:** modeller her oturumda yeniden yüklenir. 6 GB GPU'da imkânsız.
3. **Stateless (seçilen):** istemci geçmişi her istekte gönderir, sunucu hiçbir şey hatırlamaz.

### Neden stateless seçildi?
- REST API'lerin önerdiği yol. Her istek kendi başına anlaşılır, sunucu yeniden başlasa da bir şey kaybolmaz.
- Entegrasyonu en kolay yol: okul sistemi geçmişi kendi tarafında tutar, bize gönderir.
- `{"role", "content"}` biçimi OpenAI / Gemini / Claude API'lerinin kullandığı fiilî standart. Başka bir sistem
  zaten bu biçimde konuşuyor olabilir.

### Kavram: Stateful ve stateless
- **Nedir?** Stateful sunucu önceki istekleri hatırlar. Stateless sunucu her isteği sıfırdan değerlendirir; gereken
  her bilgi istekte gelir.
- **Basit örnek:** Telefonla bankayı arıyorsun. Stateful: "geçen sefer konuştuğumuz konu" deyince temsilci hatırlar.
  Stateless: her aramada müşteri numaranı ve konuyu baştan söylersin. Zahmetli görünür, ama hangi temsilciye bağlanırsan
  bağlan iş yürür.
- **Bizim projede:** `bot.ask("peki son günü?", history)`. Geçmişi `chat.py` (ileride Gradio / istemci) veriyor.
  Bot sadece son 6 mesaja bakıp soruyu "Bahar dönemi ders kayıtlarının son günü ne?" gibi bağımsız hale getiriyor.
- **Dikkat:** Geçmiş her istekte gönderildiği için istek büyür. Bu yüzden son 6 mesaj ile sınırlı. Ayrıca istemci
  geçmişi değiştirebilir; sunucu ona körü körüne güvenir (bizim için sorun değil, ama güvenlik açısından bilinmeli).

### Nasıl doğrulandı?
Gemini kotası harcamadan, LangChain'in `FakeListChatModel`'i (önceden belirlenen cevapları sırayla döndüren sahte LLM)
ve sahte bir retriever ile test edildi:
- Geçmişsiz soru: soru yeniden yazılmadan aranıyor.
- Geçmişli soru: rewrite zinciri çalışıyor, retriever yeniden yazılmış soruyla arıyor.
- 20 mesajlık geçmiş son 6 mesaja kırpılıyor.
- Botta artık `history` alanı yok.

Bu bir **deney değil**: retrieval, prompt ve LLM aynı. Sadece geçmişin nerede tutulduğu değişti.
