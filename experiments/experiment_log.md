# Experiment Log

> Otomatik üretilir (`python -m experiments.report`). Production: **EXP-014**. Ayrıntılar: `experiments/results/EXP-*.json`.

**Dataset:** `eval/sorular.json` v2.0 (27 cevaplı + 3 cevapsız/kapsam dışı). Bir chunk, doğru kaynak belgelerden birine aitse ve o belgede birebir geçen evidence cümlesini içeriyorsa relevant sayılır. Farklı setlerle koşulan deneyler birbiriyle karşılaştırılmaz.  
**Kural:** Her deney parent'ından tek bir parametre farklı. Hypothesis deneyden önce yazılır. p < 0,05 = anlamlı (McNemar / Wilcoxon, aynı sorular üzerinde).  
**Sabit parametreler:** `vector_k=15`, `bm25_k=15`, `rrf_k=60`, `reranker_max_length=512`, `rerank_candidates=8`, `llm_temperature=0.3`

## 1. Setup (hyperparameters)

Kalın hücre = parent'a göre değişen parametre.

| Exp | Parent | corpus | device | parser | chunking | chunk_size | overlap | embedding | normalize | retrieval | reranker | final_k | prompt | llm | #chunks |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| EXP-000 | – | v1 | cpu | pypdf | recursive | 1000 | 200 | MiniLM | ✗ | vector | – | 10 | v1 | 2.5-flash | 68 |
| EXP-001 | EXP-000 | v1 | cpu | **pdfplumber** | recursive | 1000 | 200 | MiniLM | ✗ | vector | – | 10 | v1 | 2.5-flash | 68 |
| EXP-002 | EXP-001 | v1 | cpu | pdfplumber | **structural** | 1000 | 200 | MiniLM | ✗ | vector | – | 10 | v1 | 2.5-flash | 90 |
| EXP-003 | EXP-002 | v1 | cpu | pdfplumber | structural | 1000 | 200 | MiniLM | **✓** | vector | – | 10 | v1 | 2.5-flash | 90 |
| EXP-004 | EXP-003 | v1 | cpu | pdfplumber | structural | 1000 | 200 | **bge-m3** | ✓ | vector | – | 10 | v1 | 2.5-flash | 90 |
| EXP-005 | EXP-004 | v1 | cpu | pdfplumber | structural | **1500** | 200 | bge-m3 | ✓ | vector | – | 10 | v1 | 2.5-flash | 74 |
| EXP-006 | EXP-005 | v1 | cpu | pdfplumber | structural | 1500 | **150** | bge-m3 | ✓ | vector | – | 10 | v1 | 2.5-flash | 73 |
| EXP-007 | EXP-006 | v1 | cpu | pdfplumber | structural | 1500 | 150 | bge-m3 | ✓ | **hybrid** | – | 10 | v1 | 2.5-flash | 73 |
| EXP-008 | EXP-007 | v1 | cpu | pdfplumber | structural | 1500 | 150 | bge-m3 | ✓ | hybrid | **bge-reranker** | 10 | v1 | 2.5-flash | 73 |
| EXP-009 | EXP-008 | v1 | cpu | pdfplumber | structural | 1500 | 150 | bge-m3 | ✓ | hybrid | bge-reranker | **5** | v1 | 2.5-flash | 73 |
| EXP-010 | EXP-009 | v1 | cpu | pdfplumber | structural | 1500 | 150 | bge-m3 | ✓ | hybrid | bge-reranker | 5 | **v2** | 2.5-flash | 73 |
| EXP-011 | EXP-004 | v1 | cpu | pdfplumber | structural | 1000 | 200 | bge-m3 | **✗** | vector | – | 10 | v1 | 2.5-flash | 90 |
| EXP-012 | EXP-008 | v1 | cpu | pdfplumber | structural | 1500 | 150 | bge-m3 | ✓ | **vector** | bge-reranker | 10 | v1 | 2.5-flash | 73 |
| EXP-013 | EXP-010 | v1 | cpu | pdfplumber | structural | 1500 | 150 | bge-m3 | ✓ | hybrid | bge-reranker | 5 | v2 | **3.1-flash-lite** | 73 |
| EXP-014 | EXP-013 | v1 | **cuda** | pdfplumber | structural | 1500 | 150 | bge-m3 | ✓ | hybrid | bge-reranker | 5 | v2 | 3.1-flash-lite | 73 |
| EXP-015 | EXP-014 | **v2** | cuda | pdfplumber | structural | 1500 | 150 | bge-m3 | ✓ | hybrid | bge-reranker | 5 | v2 | 3.1-flash-lite | 4033 |
| EXP-016 | EXP-015 | v2 | cuda | pdfplumber | **structural_v2** | 1500 | 150 | bge-m3 | ✓ | hybrid | bge-reranker | 5 | v2 | 3.1-flash-lite | 4045 |

## 2. Results

| Exp | Değişiklik | Set | MRR@10 | Hit@1 | Hit@5 | Context hit | Context chars | Latency | Primary metric | Hyp. |
|---|---|---|---|---|---|---|---|---|---|---|
| EXP-000 | Baseline (prototip) | 2.0 | 0.564 | 0.444 | 0.741 | 0.815 | 9223 | 22 ms | baseline |  |
| EXP-001 | PDF parser: pypdf → pdfplumber | 2.0 | 0.584 | 0.481 | 0.667 | 0.778 | 9278 | 21 ms | MRR@10 ↑ iyileşti (p=0.72, anlamlı değil) | ~ |
| EXP-002 | Chunking: recursive → structural | 2.0 | 0.716 | 0.556 | 0.889 | 1.000 | 8436 | 21 ms | MRR@10 ↑ iyileşti (p=0.22, anlamlı değil) | ~ |
| EXP-003 | Normalize embeddings: kapalı → açık | 2.0 | 0.654 | 0.444 | 0.926 | 1.000 | 8095 | 21 ms | MRR@10 ↓ kötüleşti (p=0.06, anlamlı değil) | ✗ |
| EXP-004 | Embedding: MiniLM → bge-m3 | 2.0 | 0.920 | 0.852 | 1.000 | 1.000 | 8708 | 83 ms | MRR@10 ↑ iyileşti (p<0.01, anlamlı) | ✓ |
| EXP-005 | chunk_size: 1000 → 1500 | 2.0 | 0.938 | 0.889 | 1.000 | 1.000 | 10835 | 79 ms | MRR@10 ↑ iyileşti (p=0.56, anlamlı değil) | ~ |
| EXP-006 | chunk_overlap: 200 → 150 | 2.0 | 0.938 | 0.889 | 1.000 | 1.000 | 10793 | 73 ms | MRR@10 = değişmedi (p=1.00, anlamlı değil) | ✓ |
| EXP-007 | Retrieval: vector → hybrid (BM25 + RRF) | 2.0 | 0.938 | 0.889 | 1.000 | 1.000 | 10678 | 78 ms | MRR@10 = değişmedi (p=0.89, anlamlı değil) | ✗ |
| EXP-008 | Reranker: yok → bge-reranker-v2-m3 | 2.0 | 1.000 | 1.000 | 1.000 | 1.000 | 10678 | 4.7 s | MRR@10 ↑ iyileşti (p=0.10, anlamlı değil) | ~ |
| EXP-009 | final_k: 10 → 5 | 2.0 | 1.000 | 1.000 | 1.000 | 1.000 | 5448 | 5.3 s | context chars ↓ iyileşti (p<0.01, anlamlı) | ✓ |
| EXP-010 | Prompt: v1 → v2 (system prompt + citation) | 2.0 | 1.000 | 1.000 | 1.000 | 1.000 | 5448 | 5.4 s | answer acc.: ölçülmedi | beklemede |
| EXP-011 | Kontrol: bge-m3 + normalize kapalı | 2.0 | 0.920 | 0.852 | 1.000 | 1.000 | 8708 | 90 ms | MRR@10 = değişmedi (p=1.00, anlamlı değil) | ✓ |
| EXP-012 | Kontrol: reranker + vector (BM25 yok) | 2.0 | 1.000 | 1.000 | 1.000 | 1.000 | 10793 | 5.5 s | MRR@10 = değişmedi (p=1.00, anlamlı değil) | ✓ |
| EXP-013 | LLM: gemini-2.5-flash → gemini-3.1-flash-lite | 2.0 | 1.000 | 1.000 | 1.000 | 1.000 | 5448 | 5.4 s | answer acc.: ölçülmedi | beklemede |
| EXP-014 | Donanım: CPU → GPU (RTX 4050) | 2.0 | 1.000 | 1.000 | 1.000 | 1.000 | 5448 | 366 ms | latency_ms ↓ iyileşti (p<0.01, anlamlı) | ✓ |
| EXP-015 | Corpus: 3 belge → 139 belge (tüm üniversite mevzuatı) | 2.0 | 0.863 | 0.778 | 0.963 | 0.963 | 5820 | 407 ms | MRR@10 ↓ kötüleşti (p=0.02, anlamlı) | ✓ |
| EXP-016 | Chunking: madde regex'i genişletildi (structural → structural_v2) | 2.0 | 0.863 | 0.778 | 0.963 | 0.963 | 5740 | 2.2 s | MRR@10 = değişmedi (p=1.00, anlamlı değil) | ✓ |

Hyp.: ✓ doğrulandı · ✗ doğrulanmadı · ~ yön doğru ama anlamlı değil

## 3. Retrieval stages

Her ara listede MRR@10. Rerank input recall: ilgili chunk reranker'a giden adaylar içinde mi (reranker'ın düzeltebileceğinin üst sınırı). Aşama verisi EXP-014'ten itibaren kaydediliyor.

| Exp | Vector | BM25 | RRF | Rerank input recall | Final |
|---|---|---|---|---|---|
| EXP-014 | 0.938 | 0.838 | 0.938 | 1.000 | 1.000 |
| EXP-015 | 0.602 | 0.581 | 0.594 | 0.963 | 0.863 |
| EXP-016 | 0.600 | 0.581 | 0.594 | 0.963 | 0.863 |

## 5. Notes

- **EXP-000:** 27 sorunun 5'inde doğru chunk ilk 10'da yok; MiniLM chunk'ların ortalama %64'ünü görüyor (128 token sınırı).
- **EXP-001:** Anlamlı fark yok; bazı sorular iyileşti, bazıları kötüleşti. Asıl faydası structural chunking'i mümkün kılması.
- **EXP-002:** Context hit 0,78 → 1,00 (anlamlı): doğru chunk artık her soruda LLM'e ulaşıyor.
- **EXP-003:** Hypothesis ✗: MiniLM'de MRR düştü (p=0,06).
- **EXP-004:** En büyük kazanç (MRR +0,27, anlamlı). Latency 21 → 83 ms.
- **EXP-005:** Anlamlı fark yok; context %24 uzadı.
- **EXP-006:** Beklendiği gibi ranking değişmedi.
- **EXP-007:** Hypothesis ✗: MRR aynı; 2 soru iyileşti, 3 soru kötüleşti.
- **EXP-008:** Tüm sorularda doğru chunk 1. sırada ama anlamlı değil (ceiling effect). Latency ~60 kat arttı.
- **EXP-009:** Context %49 kısaldı, context hit 1,00'da kaldı.
- **EXP-010:** Answer accuracy henüz ölçülmedi (Gemini günlük kotası).
- **EXP-011:** Değişmedi: bge-m3 zaten kendi içinde normalize ediyor, parametre etkisiz.
- **EXP-012:** Değişmedi: BM25'in katkısı reranker ile de gösterilemedi.
- **EXP-013:** Retrieval aynı; answer_acc henüz ölçülmedi.
- **EXP-014:** Latency 5,4 sn → 0,37 sn (~15×, p<0,001); sıralamalar birebir aynı.
- **EXP-015:** MRR@10 1,00 → 0,86 (p=0,02); reranker düşüşü sınırlıyor (RRF 0,59 → 0,86). 6 kötüleşmenin 2'si eksik etiket.
- **EXP-016:** Değişmedi (beklenen): soruların kaynak belgeleri etkilenmiyor; fallback belge 11 → 2. Latency değeri ölçüm artefaktı.
