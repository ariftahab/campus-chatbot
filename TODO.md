# TODO

Yalnız açık işler, sırasıyla. Yapılanların sonuçları config `notlar` alanlarında, `experiments/experiment_log.md`'de ve
RAG-Study-Notes `daily_log/`'unda; tarihçe git'te. Kesinleşmiş kararlar memory'de (`user-decisions`).

## Sıra

1. [ ] **EXP-036: v7 prompt'ları** — `prompt_version` v3_kapsam → `v7_kapsamsiz`, `clarify_prompt` v4 → `v7_netlestirme`
       (tek kavram: kapsam davranışı, `coklu_degisiklik_gerekcesi`), üst deney EXP-033, set 4.2, ~150 istek. Birincil
       `answer_acc` (düşmemeli, 0,966); ikincil netleştirme uzunluğu (674), çekimser kalma ve takip grupları, birleştirme
       (3/10). Gereksiz netleştirme raporlanır, hata sayılmaz. Koşudan sonra liste satırları da sayılabilir (kota yok).
       Alt küme teşhisi (2026-10-17): sorunlu 12 soruda 12/12, takip senaryolarında 9/9.
   - Kabul edilirse production = EXP-036 + `fixed_answers="summer_staj_v1"` (koşu yok; birim belirtilmeyen staj sorusunda
     birim sorulur, set 4.2'de yalnız "Stajımı kaç gün yapmam gerekiyor?" etkileniyor).

2. [ ] **Fıkra atfı deneyi** — `citation_style` madde → fikra. Birincil `fikra_atif_orani` (EXP-033: 0,029), ikincil
       `fikra_dogrulugu`. Üst deney EXP-036 kabul edilirse o, edilmezse EXP-033. Panelde fıkra vurgusu ayrı UI işi.
   - Birleştirme deneyi (`v5_birlestirme`) çıkarıldı: v7 birleştirme kuralını yeniden yazdı; EXP-036'nın birleştirme
     sonucu kötüyse geri gelir.

3. [ ] **Validation seti** — taslak `eval/taslak/sorular_val_v1_taslak.json` (44 soru, set 4.x'te sorulmamış belgelerden).
       Kullanıcı düzeltecek, sonra `eval/sorular_val_v1.json`. Amaç: set 4.x'te (dev) seçilen kararları ayrı sorularla
       doğrulamak (overfitting).

4. [ ] **Sonraki set sürümü için etiket düzeltmesi** — "Kaç gün rapor hakkım var?" sorusu "dahil" bekliyor; corpus'ta gün
       sayısı yok, "bilgim yok" doğru (kullanıcı kararı 2026-10-16). Yeni set sürümü, referans zinciri yeniden koşulur.

5. [ ] **Ders programları** — ayrı bir scraper, büyük ihtimalle CSV. Tablo verisi için chunk yerine yapılandırılmış
       saklama (dönem, bölüm, gün, saat, ders, derslik) + tool ile sorgulama (mimari değişiklik, önce onay).
   - [ ] Scraping kaynağı ve CSV şeması (her dönem `donem` metadata'sıyla).
   - [ ] Yapılandırılmış saklama (ör. SQL) — deney olarak.
   - [ ] Ders programı soruları için yeni soru seti sürümü.

6. [ ] **Diğer bilgiler** — birim sayfaları, iletişim...

7. [ ] **Tool calling: transkripte göre mezuniyet hesabı** — öğrenci transkriptini yükler ("mezun olmak için kaç kredi
       daha lazım?"); ajan transkripti okur, AKTS'yi toplar, yönetmelikten kuralı çeker, farkı hesaplar (mimari
       değişiklik, önce onay).
   - Araçlar: `transkript_oku` (PDF → ders listesi), `mevzuat_ara` (mevcut `Retriever`), `hesapla` (aritmetik Python'da).
     Gemini function calling (`bind_tools`).
   - Transkript örneği gerekli (kendi transkriptinle başla); müfredat corpus'ta yok, ilk sürüm yalnız kredi + genel kurallar.
   - Kişisel veri: transkript yalnız oturum boyunca bellekte; log'a ve diske yazılmaz.
   - Değerlendirme: cevabı bilinen sentetik transkriptler; hesap doğruluğu, kaynak, araç çağrısı sayısı, latency, istek sayısı.

## Sürekli
- **Veriden öğrenme:** gerçek kullanıcı soruları biriktikçe hata türleri analiz edilir; seçilenler yeni set sürümüne girebilir.

## Belki
- **Agentic retrieval** — model aramayı kendisi yönetir (sorgu genişletme, çoklu arama, yetersiz context'te tekrar
  arama). Araştırma: RAG-Study-Notes `learning_log/agentic_retrieval_arastirma.md`. Maliyet: soru başına birden fazla
  istek. Yapılırsa 7. maddedeki tool calling altyapısından sonra, deney olarak.

## Tezin sonunda
- **Kilitli test seti** — corpus tamamlandıktan sonra o günkü belgelerden yeni yazılan sorularla; deneylerde kullanılan
  setlerden seçilmez; gruplara dengeli; yalnız bir kez koşulur.
