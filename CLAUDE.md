# CLAUDE.md

Bolu Abant İzzet Baysal Üniversitesi (BAİBÜ) için RAG chatbot. Python 3.11, venv `venv/` içinde.
Kullanıcıya dönük metinler ve yorumlar Türkçe.

## Komutlar
- `venv/Scripts/python.exe chat.py` — terminal sohbeti
- `venv/Scripts/python.exe ingest.py` — indeksi yeniden kur
- `venv/Scripts/python.exe eval.py` — getirme değerlendirmesi (API'siz); `--llm` ile cevaplar da (Gemini kotası harcar)
- Windows'ta Türkçe çıktı için `PYTHONIOENCODING=utf-8` gerekebilir.

## Mimari
- `config.py` — tüm ayarlar (model adları, k değerleri, belge başlık/tür eşlemesi `DOCUMENTS`).
- `ingest.py` — PDF'leri pdfplumber ile okur. `mevzuat` türü madde madde ("Madde N-" / "MADDE N-") bölünür,
  1500 karakteri aşan maddeler fıkra sınırlarından ikiye ayrılır ve her parçaya "Belge - Madde N (başlık)" eklenir.
  `takvim` türünde her tablo (ör. "EĞİTİM-ÖĞRETİM - BAHAR YARIYILI") bir parçadır; başlıklar tablo üstündeki metinden alınır.
  FAISS indeksi + `chunks.json` (BM25 için) `vectorstore/`'a kaydedilir. `manifest.json`'daki parmak izi
  (PDF içerikleri + ayarlar + ingest.py kaynağı) değişirse `load_index()` indeksi otomatik yeniden kurar.
- `rag.py` — `HybridRetriever`: FAISS (bge-m3) + BM25 (Türkçe için ilk 5 harf kökleme) → RRF → bge-reranker-v2-m3.
  `RagBot`: geçmiş varsa soruyu LLM ile bağımsız hale getirir, sonra Gemini ile kaynaklı cevap üretir.
- `chat.py` — CLI döngüsü; API hataları yakalanır, `yeni` geçmişi sıfırlar.
- `eval.py` + `eval/sorular.json` — soru, beklenen kaynak (madde veya takvim bölümü) ve beklenen anahtar kelimeler
  (`"a|b"` = alternatifler, `cevapsiz: true` = "Bu konuda bilgim yok." beklenir).

## Notlar
- LLM: Gemini (`langchain-google-genai`), anahtar `.env` içinde `GOOGLE_API_KEY`. `.env` git'e girmez.
- Donanım: sadece CPU. Reranker sorgu başına birkaç saniye ekler; `config.RERANKER_MODEL = None` ile kapatılır.
- `langchain-core` 1.0.4'e sabitlendi; yükseltme `langchain-google-genai`/`langchain-community` ile uyumu bozabilir.
- Parçalama/getirme değişikliğinden sonra `eval.py` çalıştırıp sonucu karşılaştır.
- `main` branch'inde eski tek dosyalık prototip (`prototip-chat.py`) duruyor; `yedek-oncesi` etiketi de o hali gösterir.
