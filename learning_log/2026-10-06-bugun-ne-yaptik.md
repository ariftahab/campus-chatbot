# 2026-10-06 — Bugün ne yaptık?

> Bu dosya günün **yapılan işler özeti**. Öğrenilecek kavramlar `learning_log/2026-10-06.md`'de, UI/API'nin adım adım
> gerekçeleri `learning_log/ui_api_log.md`'de.

## Kısaca

| # | Ne yaptık | Sonuç | Commit |
|---|---|---|---|
| 1 | Yol haritası güncellendi | Sıra: (1) UI + soru-cevap kaydı, (2) ders programı ve takvim scraping, (3) deneylere dönüş | `7871b95` |
| 2 | `RagBot` stateless yapıldı | Geçmiş `ask(soru, history)` ile dışarıdan geliyor; deneylerin davranışı aynı | `7871b95` |
| 3 | FastAPI, uvicorn, Gradio, httpx kuruldu | Bağımlılık çakışması (`huggingface-hub`) önceden yakalandı; mevcut paketlerin hiçbiri değişmedi | `f9778f1` |
| 4 | Service katmanı + soru-cevap kaydı | `logs/sohbet.jsonl`, `logs/geri_bildirim.jsonl` (append-only) | `f9778f1` |
| 5 | EXP-020: prompt v3 + kopyasız corpus | Retrieval EXP-019 ile birebir aynı; **production EXP-014 → EXP-020** (3 belge → 131 belge) | `d3cb825`, `9167638` |
| 6 | FastAPI endpoint'leri | `/ask`, `/feedback`, `/documents`, `/health`, Swagger `/docs` | `a24f489` |
| 7 | Gradio arayüzü | Çalıştı ama tasarım beğenilmedi | `fd9bee0`, `d44c500` |
| 8 | Kendi frontend'imiz (HTML/CSS/JS) | Tıklanabilir kaynaklar + PDF'te o sayfa, okunaklı tasarım, `/admin` değerlendirme sayfası | `22a5414` |
| 9 | İlk gerçek kullanım | 8 soru elle değerlendirildi: 6 doğru, 2 kısmen | — |
| 10 | Günlükler `learning_log/`'da toplandı, deploy planı TODO'ya yazıldı | Bu dosya dahil | bu commit |

---

## 1. Yol haritası

Yönetmelik PDF'leri tamamlandığı için `TODO.md` yeniden sıralandı:
1. **UI:** sohbet, sorulan soruların ve cevapların kaydı, doğruluk ölçümü, belgeleri görme. UI'dan belge ekleme
   şimdilik kapsam dışı.
2. **Ders programları ve akademik takvim:** okulun sitesinden her dönem scrape edilecek. Mevcut chunking'e uymayabilir;
   yeni sorular yeni bir soru seti sürümüyle eklenecek.
3. Bunlar bitince **deneylere dönüp optimizasyon**.

## 2. Mimari kararı: FastAPI + üstünde ince bir arayüz

Streamlit, Gradio ve FastAPI + kendi sayfamız karşılaştırıldı. İleride sistemin bir hocaya verilmesi veya okul
sistemine entegre edilmesi ihtimali ve FastAPI deneyimi isteği yüzünden **API baştan kuruldu**:
`arayüz → API (api.py) → service (service.py) → RAG çekirdeği (rag.py)`. Sohbet geçmişi istemcide (stateless API).

## 3. Production config'i: EXP-014 → EXP-020

Arayüzü yazarken production'ın hâlâ EXP-014 (corpus v1, **3 belge**) olduğu görüldü.
- İstenen: kopyasız corpus (v3) + kapsam ayıran prompt (v3).
- Bu kombinasyon hiç ölçülmemişti → **EXP-020** açıldı (EXP-019'dan tek fark: prompt).
- Retrieval-only koşuldu: MRR@10 0,852, Hit@1 0,789, Hit@5 0,930; EXP-019 ile birebir aynı (beklenen).
- Prompt v3'ün etkisi set 3.0 ile ölçülemiyor (sadece 2 çok kapsamlı soru var). Kanıt gerçek kullanım kayıtlarından
  gelecek.
- İlk koşu `git_dirty: true` çıktı (takip edilmeyen, konuyla ilgisiz bir PDF yüzünden). PDF silindikten sonra
  yeniden koşuldu, temiz sonuç kaydedildi.

## 4. Arayüz: Gradio → kendi frontend'imiz

Gradio arayüzü denendi. Geri bildirim: kaynaklar tıklanabilir olmalı, tasarım çok geniş ve okunması zor.
Gradio'nun bileşen modeli bu etkileşimlere izin vermediği için **HTML + CSS + vanilla JavaScript** ile yeniden yazıldı:

| Sayfa | Ne var |
|---|---|
| `/` Sohbet | 720px sütun, 15px yazı, koyu tema. Cevaptaki `[Belge, Madde N]` atıfları ve kaynak düğmeleri tıklanabilir → sağ panelde madde metni + "PDF'te aç (s. N)". 👍/👎 |
| `/belgeler` | 131 belge, arama, seçilen belgenin chunk'ları |
| `/admin` | Özet (doğruluk, doğru kaynak oranı, hata aşamaları, 👍/👎) + her cevap için etiket formu |
| `/docs` | Swagger (API dokümantasyonu) |

Güvenlik: LLM cevabı DOMPurify ile temizleniyor (XSS), PDF endpoint'i sadece corpus'taki dosyaları veriyor
(path traversal). `/admin` şimdilik korumasız.

## 5. İlk gerçek kullanım verisi

| Soru | Değerlendirme |
|---|---|
| Yatay geçiş başvurusu ne zaman yapılır? | doğru |
| yatay geçişi hangi dönem yapabilirim | doğru |
| peki lisans için kaç ortalama yapmam gerekli | doğru |
| tıp için kaç kredi / tıp okuyorsam kaç kredi / diş için kaç | doğru (üçü de) |
| mezun olmak için kaç kredi almam gerekiyor (iki farklı soruluş) | **kısmen**, hata: retrieval. Tıp ve diş hekimliği fakültelerinin farklı kuralları cevaba gelmedi |

Bulgu: Çok kapsamlı sorularda LLM'e giden 5 chunk genel yönetmelikle doluyor; prompt v3 kapsamları ayırmak istese de
fakülteye özel maddeleri hiç görmüyor. Optimizasyon aşamasında deney adayı.

Ortalama cevap süresi 14,6 sn; retrieval bunun ~0,4 sn'si, gerisi Gemini (rewrite olan sorularda 2 çağrı).

## 6. Günlüklerin düzenlenmesi

Bütün günlükler artık `learning_log/` altında:
- `app/gelistirme_gunlugu.md` → `learning_log/ui_api_log.md`
- `experiments/experiment_log.md` → `learning_log/experiment_log.md`. `experiments.report` yeni yere yazıyor; içerik
  birebir aynı. Deney koşucusunun "commit edilmemiş değişiklik" kontrolündeki istisna da yeni yola göre güncellendi.
- `my_notes/` içindeki notlar (`2026-10-01-bugun-ne-yaptik.md`, `eval_v3_taslak.md`) → `learning_log/`. `my_notes/`
  klasörü duruyor, kendi notların için.

## 7. Ertelenenler

- **Başka biri tarafından test (deploy):** kısa test için Cloudflare Quick Tunnel, kalıcı demo için Hugging Face Spaces.
  Açmadan önce `/ask` için günlük istek sınırı (Gemini kotası) ve `/admin` için şifre. Ayrıntılar `TODO.md`'de.
- Gradio'nun (`/ui`) kaldırılması, atıftaki fıkranın panelde vurgulanması.
- Sıradaki büyük iş: ders programı ve akademik takvim scraping.
