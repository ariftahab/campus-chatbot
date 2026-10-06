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

---

## Adım 2 — Paketlerin kurulması (2026-10-06)

### Ne yapıldı?
`fastapi`, `uvicorn[standard]`, `gradio`, `httpx` kuruldu ve `requirements.txt`'ye sürümleriyle eklendi.

| Paket | Ne işe yarar |
|---|---|
| **FastAPI** | API'yi tanımladığımız web framework'ü: endpoint'ler, istek doğrulama, otomatik dokümantasyon |
| **uvicorn** | FastAPI uygulamasını çalıştıran sunucu (ASGI server). FastAPI tek başına çalışmaz, uvicorn onu ağa açar |
| **Gradio** | Arayüz (sohbet ekranı, data sekmesi) |
| **httpx** | Python'dan HTTP isteği atmak için. Gradio arayüzü API'ye bununla bağlanacak |

### Karşılaşılan sorun: bağımlılık çakışması (dependency conflict)
Kurmadan önce `pip install --dry-run` ile neyin kurulacağına bakıldı. En yeni Gradio (6.29) `huggingface-hub` 2.x
istiyordu. Embedding ve reranker'ı çalıştıran `transformers` 4.57.1 ise `huggingface-hub<1.0` istiyor. Doğrudan
kursaydık pip hub'ı yükseltecek, `transformers` bozulacak ve büyük ihtimalle model yüklenirken hata alacaktık.

**Çözüm:** Kritik paketler (`huggingface-hub`, `transformers`, `langchain-core`, `pydantic`) mevcut sürümlerine
sabitlenerek kurulum yapıldı. pip bu kısıtlarla uyumlu en yeni Gradio'yu (6.17.3) buldu. Kurulumdan önce ve sonra
`pip freeze` alınıp karşılaştırıldı: **hiçbir mevcut paket değişmedi**, sadece yeni paketler eklendi.

### Kavram: Dependency resolution ve version pinning
- **Nedir?** Her paket başka paketlerin belirli sürüm aralıklarına ihtiyaç duyar. pip bu kısıtların hepsini aynı anda
  sağlayan bir sürüm kombinasyonu arar (dependency resolution). Version pinning, bir paketi `==` ile tam bir sürüme
  sabitlemek demek.
- **Basit örnek:** A paketi "B'nin 1'den küçük sürümü" ister, C paketi "B'nin 2 veya üstü" ister. İkisi aynı ortamda
  olamaz. Ya C'nin eski bir sürümünü bulursun ya da A'yı yükseltirsin.
- **Bizim projede:** Gradio'nun eski ama uyumlu sürümü seçildi. `transformers`'ı yükseltmek embedding sonuçlarını
  değiştirebilirdi; bu da eski deneylerle karşılaştırmayı bozardı.
- **Dikkat:** `pip install X` komutu sessizce başka paketleri yükseltebilir. Önemli bir ortamda önce `--dry-run`,
  sonra `pip check`. `requirements.txt`'de sürüm yazmak, projeyi başka bilgisayarda aynı şekilde kurabilmenin şartı.

---

## Adım 3 — Service katmanı ve soru-cevap kaydı (2026-10-06)

### Ne yapıldı?
`app/service.py` dosyasına `ChatService` sınıfı yazıldı:

| Metot | Ne yapar |
|---|---|
| `ChatService.from_experiment()` | Deney config'ine göre modelleri yükler. Uygulama açılırken **bir kez** çağrılır |
| `ask(question, history, session_id)` | Soruyu cevaplar, `logs/sohbet.jsonl`'e kaydeder |
| `feedback(answer_id, rating, note)` | 👍 (1) / 👎 (-1) geri bildirimini `logs/geri_bildirim.jsonl`'e kaydeder |
| `documents()` | Corpus'taki belgeler ve chunk sayıları (data sekmesi için) |
| `document_chunks(source)` | Bir belgenin chunk'ları (data sekmesi için) |

`logs/` klasörü `.gitignore`'a eklendi: gerçek kullanıcı soruları repoya girmemeli.

### Log kaydının biçimi
```json
{"id": "555abf88...", "zaman": "2026-10-06T15:45:48", "oturum": "s1",
 "soru": "peki son günü?", "rewritten_query": "Bahar dönemi ders kayıtlarının son günü ne?",
 "gecmis_uzunlugu": 2, "cevap": "...",
 "kaynaklar": [{"chunk_id": 0, "etiket": "Yatay Geçiş Yönergesi, Madde 8, s. 3"}],
 "config": "EXP-019", "commit": "7871b95", "latency_ms": 2140, "hata": null}
```

| Alan | Neden var |
|---|---|
| `id` | 👍/👎 geri bildirimini bu cevaba bağlamak için (UUID: rastgele, çakışmayan kimlik) |
| `rewritten_query` | Rewrite yapılmadıysa `null`. Yanlış cevapta hatanın rewriting'de mi retrieval'da mı olduğunu ayırmak için |
| `kaynaklar` | LLM'e giden chunk'lar. Doğru chunk gelmiş mi? (retrieval hatası mı, generation hatası mı?) |
| `config`, `commit` | Bu cevabı hangi pipeline sürümü üretti? Commit edilmemiş kodla çalışıyorsa `-dirty` eki alır (deneylerdeki `git_dirty` gibi) |
| `latency_ms` | Cevap süresi (rewrite + retrieval + LLM) |
| `hata` | Kota dolması (429), ağ hatası vb. Hatalı istekler de kaydedilir; kaç sorunun cevapsız kaldığını görmek için |

### Neden böyle tasarlandı?

**1. JSONL, append-only.** Her satır bağımsız bir JSON nesnesi, yeni kayıt sadece sona eklenir.
- *Alternatif: tek bir JSON dosyası (liste).* Her kayıtta dosyanın tamamını okuyup yeniden yazmak gerekir. Yazma
  sırasında program çökerse dosyanın tamamı bozulur.
- *Alternatif: SQLite veritabanı.* Sorgulama güçlü, ama şimdilik gereksiz karmaşıklık. JSONL ileride kolayca SQLite'a
  veya pandas'a aktarılır (`pd.read_json(..., lines=True)`).
- JSONL'de en kötü ihtimalle son satır yarım kalır; önceki kayıtların hepsi sağlam kalır.

**2. Geri bildirim ayrı dosyada.** 👍/👎'yi sohbet kaydının içine yazmak, o satırı sonradan değiştirmek demek. Bu,
append-only kuralını bozar. Bunun yerine geri bildirim ayrı dosyaya yazılır ve `id` ile bağlanır; veritabanlarındaki
foreign key mantığı. Aynı cevaba fikir değiştirip ikinci geri bildirim verilirse ikisi de kalır, en sonuncusu geçerli
sayılır.

**3. Hata olunca da kayıt.** `try / except / finally`: cevap da dönse hata da fırlasa `finally` bloğu çalışır ve kayıt
yazılır. Hata, kaydedildikten sonra yukarıya (API'ye) iletilir; API kullanıcıya uygun bir mesaj gösterecek.

**4. Kilit (lock).** FastAPI senkron fonksiyonları ayrı thread'lerde çalıştırır. İki istek aynı anda dosyaya yazarsa
satırlar birbirine karışabilir. `threading.Lock` yazma işlemlerini sıraya sokar. Testte 8 thread aynı anda 400 kayıt
yazdı; bozuk satır çıkmadı.

### Kavram: Dependency injection
- **Nedir?** Bir sınıfın ihtiyaç duyduğu nesneyi kendisi oluşturması yerine dışarıdan alması.
- **Basit örnek:** Bir kahve makinesine suyu içine gömülü bir depodan değil, takılabilir bir hazneden vermek. Test
  ederken hazneye istediğin suyu koyabilirsin.
- **Bizim projede:** `ChatService(bot, experiment_id)` botu dışarıdan alıyor. Gerçek kullanımda
  `ChatService.from_experiment()` GPU modelleriyle gerçek botu oluşturuyor. Testte ise sabit cevap dönen sahte bir
  `FakeBot` veriliyor. Test GPU, model ve Gemini kotası gerektirmeden 1 saniyede çalışıyor.
- **Dikkat:** `from_experiment` gibi "fabrika" metotları gerçek bağımlılıkları kurar, `__init__` ise sadece alır. Bu
  ayrım test edilebilir kodun temel kalıbı. FastAPI'nin kendi `Depends()` sistemi de aynı fikre dayanır.

### Kavram: Thread ve race condition
- **Nedir?** Thread, aynı program içinde paralel çalışan bir iş akışı. Race condition, iki thread'in aynı kaynağa
  (dosya, değişken) aynı anda erişip sonucun hangisinin önce davrandığına bağlı olması.
- **Basit örnek:** İki kişi aynı deftere aynı anda yazarsa satırlar iç içe geçer. Kilit, kalemi tek kişiye vermektir.
- **Bizim projede:** `with self._lock:` bloğu içinde aynı anda sadece bir thread dosyaya yazabilir.
- **Dikkat:** Kilit sadece aynı süreç (process) içindeki thread'leri korur. İleride birden fazla sunucu süreci
  çalıştırılırsa dosya yerine veritabanına geçmek gerekir.

### Nasıl doğrulandı?
Sahte bot ve geçici bir klasörle (gerçek `logs/` kullanılmadan) test edildi:
- Geçmişsiz soruda `rewritten_query` null, geçmişli soruda dolu.
- Hata fırlatan soru `hata` alanıyla kaydedildi ve hata yukarı iletildi.
- Bilinmeyen `id`'ye ve geçersiz puana geri bildirim reddedildi.
- Servis yeniden başlatıldığında eski kayıtların kimlikleri tanındı.
- 8 thread × 50 eşzamanlı soru: 400 satırın hepsi geçerli JSON.
