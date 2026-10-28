# Hata analizi (2026-10-28)

Production yapılandırması (EXP-044: corpus v5, hybrid retrieval + bge-reranker, 5 chunk context, `gemini-3.1-flash-lite`,
prompt `v8_kapsamsiz` + `v7_netlestirme`) üç sette anlamca yanlış cevapladığı sorular:

| Set | Deney | Anlamca doğruluk | Yanlış |
|---|---|---|---|
| Validation 1.0 (belge diline yakın, 100 soru) | EXP-045 | 0,93 | 7 |
| Validation 2.0 (öğrenci dili, 111 soru) | EXP-046 | 0,88 | 13 |
| Dev 4.6 (cevaplanan 150 soru; 50 soru kota yüzünden koşulmadı) | EXP-047 | 0,99 | 1 |

**Yöntem.** Cevaplar tek tek okunup anlamca değerlendirildi (kararlar ve gerekçeleri `experiments/anlamca/EXP-*.json`).
Her yanlış cevapta, beklenen kanıtı içeren chunk'ın retrieval'ın hangi aşamasında kaybolduğu ölçüldü (LLM'siz,
production yapılandırmasıyla): vector ve BM25 aday listeleri (her biri 30), RRF birleşimi, reranker sonrası sıra.
LLM'e ilk 5 chunk gider.

- **Reranker aşağı itti:** doğru chunk reranker'a giden 30 aday içinde, ama reranker sonrası 6. sıranın altında.
- **Aday listesine girmedi:** doğru chunk vector ve BM25 aramalarının ilk 30'unda yok; reranker onu hiç görmüyor.
- **Generation:** doğru chunk context'te, model yanlış çıkarım yapıyor.

## Yanlış cevaplanan sorular

| Soru | Set | Soru türü | Sorun nerede | Neden yanlış |
|---|---|---|---|---|
| DC harf notu alırsam dersi geçmiş sayılır mıyım? | Val 1 | Netleştirme | Reranker aşağı itti (genel yönetmeliğin not tablosu 6.) | Genel kural yerine yalnız Diş Hekimliği kuralı (DC geçmez) verildi |
| Bir dersten DC aldım, geçtim mi kaldım mı? | Val 2 | Netleştirme | Aday listesine girmedi | Yalnız Diş Hekimliği ve lisansüstü kuralı verildi |
| Bir dönemde en fazla kaç ders alabilirim? | Val 1 | Netleştirme | Reranker aşağı itti (ders yükü maddesi 7.) | Lisansüstü ve yandal kuralları verildi, genel ders yükü kuralı yok |
| Bir dönemde en fazla kaç ders seçebilirim? | Val 2 | Netleştirme | Reranker aşağı itti (12.) | Yalnız yandal kuralı (15 AKTS) verildi |
| Derslere hiç gitmezsem hangi sınavlara giremem? | Val 2 | Netleştirme | Reranker aşağı itti (11.) | Devamsızlık yerine ders kaydı yapmayanın kuralı verildi |
| Çift anadal ve yandal için not ortalaması şartı aynı mı? | Dev | Netleştirme | Reranker aşağı itti (yandal başvuru maddesi 16.) | Yandal başvurusu için 65 yerine başka maddeden 60 verildi |
| ikinci öğretimdeyim sınıfın ilk yüzde onuna girersem ne kadar öderim, daha önce bir dersten kaldıysam yine yararlanabilir miyim? | Val 1 | Tek belge, birden fazla madde | Reranker aşağı itti (ikinci madde 6.) | İkinci alt soru (dersten kalan yararlanamaz) düştü |
| Gece öğretimindeyim, sınıfta ilk yüzde ona girersem ne kadar harç öderim? Geçen dönem bir dersten kalmıştım, yine de olur mu? | Val 2 | Tek belge, birden fazla madde | Reranker aşağı itti (10.) + generation | İkinci alt soruya yanlış bilgi: "kalmak engel değil" |
| mühendislik stajından kalırsam ne zaman tekrar yaparım ve sigortamı kim öder? | Val 1 | Tek belge, birden fazla madde | Reranker aşağı itti (7.) | Tekrar zamanı (takip eden ilk staj dönemi) verilmedi |
| Mühendislikte stajdan kaldım; tekrar ne zaman yapacağım ve bu sefer sigortayı kim ödeyecek? | Val 2 | Tek belge, birden fazla madde | Aday listesine girmedi | Tekrar zamanı için "belirtilmemiş" dendi |
| mühendislikte staj yerimi değiştirmem gerekirse kaç gün önceden haber vermeliyim, staj defterini de ne zaman teslim edeceğim? | Val 2 | Tek belge, birden fazla madde | Reranker aşağı itti (6.) | Rapor teslimi için "belirtilmemiş" dendi, başka birimin kuralı verildi |
| Hazırlıkta yıl sonu sınavından kaç alırsam geçerim, notuma itiraz etmek için kaç günüm var? | Val 2 | Tek belge, birden fazla madde | Reranker aşağı itti (13. ve 11.) | Tümüyle "bilgim yok" |
| dikey geçişle geldim, önlisansta aldığım dersler sayılıyor mu ve not ortalamam nasıl hesaplanıyor? | Val 1 | Tek belge, birden fazla madde | Aday listesine girmedi (muafiyet maddesi) | Muafiyet alt sorusu düştü |
| Arkadaşlarla kulüp kurmak istiyoruz; danışman hoca bulmak zorunda mıyız, yılda kaç etkinlik yapmamız lazım? | Val 2 | Tek belge, birden fazla madde | Aday listesine girmedi (etkinlik maddesi) | Yılda en az 3 etkinlik için "alt sınır yok" dendi |
| Hazırlıktayım; derslerin en az ne kadarına gelmem lazım, başarılı olursam harç indirimi alabilir miyim? | Val 2 | Birden fazla belge | Aday listesine girmedi (hazırlık devam maddesi) | %80 devam için "bilgi yok" dendi |
| topluluğumuzun akademik danışmanı yok ne olur | Val 1 | Farklı ifade | Aday listesine girmedi | Faaliyetin durdurulacağı söylenmedi |
| Kütüphaneden aldığım kitabı bitiremedim ama başka biri sıraya girmiş, biraz daha tutabilir miyim? | Val 2 | Farklı ifade | Reranker aşağı itti (6.) | Ayırtılmış kitabın uzatılamayacağı söylenmedi, uzatma hakkı verildi |
| kınama cezası aldım yemek bursum kesilir mi | Val 1 | Farklı ifade | Generation (doğru madde 1. sırada) | "Kesilmez" dendi; uyarı dışındaki disiplin cezası bursu keser |
| Disiplinden kınama aldım, yemek bursum gider mi? | Val 2 | Farklı ifade | Generation (doğru madde 1. sırada) | Aynı çıkarım hatası |
| hazırlıkta güz dönemi dersler ne zmn bitiyo | Val 2 | Yazım hatalı | Aday listesine girmedi | Yanlış belge: Bilgisayar Mühendisliği ders programından 25 Aralık (doğrusu 31 Aralık) |
| hazirlikta derslerin yuzde kacina girmek zorundayim | Val 2 | Yazım hatalı | Aday listesine girmedi | "Bilgim yok" |

**Dağılım:** 21 hatanın 11'i reranker aşağı ittiği, 8'i aday listesine girmediği, 2'si generation yüzünden.
11 hatanın 6'sında doğru chunk 6. veya 7. sırada.

## Hata olmayan zayıf davranışlar

- **Konu dışı sorular** (hava durumu, yemek tarifi, şiir) reddediliyor, ama 15 cevabın 14'ü yalnız "Bu konuda bilgim
  yok."; asistanın BAİBÜ mevzuatı için olduğu söylenmiyor.
- **Eksik madde gelince** model kimi zaman dürüstçe "belirtilmemiş" diyor, kimi zaman boşluğu başka birimin kuralıyla ya
  da uydurmayla dolduruyor.
- **Atıf hataları:** "genel kural" diye Hukuk Fakültesi yönetmeliği gösteriliyor; bazı cevaplara ilgisiz kaynak ekleniyor.
- **Anahtar kelime ölçüsü yanıltıcı:** doğru cevabı kaçırıyor ("karşılanmamaktadır" ≠ "karşılanmaz"), yanlış cevabı
  ödüllendiriyor ("kesilmez" içinde "kesil"). Ana ölçü anlamca doğruluk.

## Bu analizden sonra denenenler

| Deney / teşhis | Sonuç |
|---|---|
| Netleştirmede genel yönetmeliği ayrıca arayıp ekleme (iki biçim, teşhis) | Dört netleştirme sorusunun yalnız birini düzeltti: reranker genel yönetmeliğin içinde de yanlış maddeyi seçiyor |
| EXP-049: BM25'te Snowball Türkçe stemmer | BM25 MRR@10 0,506 → 0,456 (kötüleşti); production değişmedi |
| EXP-050: BM25'te Türkçe karakter katlama | BM25 MRR@10 0,506 → 0,521, final sıralama aynı; production değişmedi |
