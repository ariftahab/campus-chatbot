# Experiment Log

> Otomatik üretilir (`python -m experiments.report`). Production: **EXP-044**. Ayrıntılar: `experiments/results/EXP-*.json`.

**Dataset:** `eval/sorular.json` v2.0 (27 cevaplı + 3 cevapsız/kapsam dışı) · `eval/sorular_v3.json` v3.0 (71 cevaplı + 6 cevapsız/kapsam dışı) · `eval/sorular_v4.json` v4.0 (116 cevaplı + 23 cevapsız/kapsam dışı) · `eval/sorular_v41.json` v4.1 (117 cevaplı + 22 cevapsız/kapsam dışı) · `eval/sorular_v42.json` v4.2 (127 cevaplı + 22 cevapsız/kapsam dışı) · `eval/sorular_v45.json` v4.5 (139 cevaplı + 26 cevapsız/kapsam dışı) · `eval/sorular_v46.json` v4.6 (168 cevaplı + 32 cevapsız/kapsam dışı) · `eval/sorular_v47.json` v4.7 (187 cevaplı + 32 cevapsız/kapsam dışı) · `eval/sorular_val_v1.json` vval-1.0 (85 cevaplı + 15 cevapsız/kapsam dışı) · `eval/sorular_val_v2.json` vval-2.0 (88 cevaplı + 23 cevapsız/kapsam dışı). Bir chunk, doğru kaynak belgelerden birine aitse ve o belgede birebir geçen evidence cümlesini içeriyorsa relevant sayılır. Farklı setlerle koşulan deneyler birbiriyle karşılaştırılmaz.  
**Kural:** Her deney parent'ından tek bir parametre farklı. Hypothesis deneyden önce yazılır. p < 0,05 = anlamlı (McNemar / Wilcoxon, aynı sorular üzerinde).  
**Sabit parametreler:** `citation_style=madde`, `rrf_k=60`, `reranker_max_length=512`, `llm_temperature=0.3`

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
| EXP-017 | EXP-016 | v2 | cuda | pdfplumber | structural_v2 | 1500 | 150 | bge-m3 | ✓ | hybrid | bge-reranker | 5 | v2 | 3.1-flash-lite | 4045 |
| EXP-018 | EXP-017 | v2 | cuda | pdfplumber | structural_v2 | 1500 | 150 | bge-m3 | ✓ | hybrid | bge-reranker | 5 | **v3_kapsam** | 3.1-flash-lite | 4045 |
| EXP-019 | EXP-017 | **v3** | cuda | pdfplumber | structural_v2 | 1500 | 150 | bge-m3 | ✓ | hybrid | bge-reranker | 5 | v2 | 3.1-flash-lite | 3785 |
| EXP-020 | EXP-019 | v3 | cuda | pdfplumber | structural_v2 | 1500 | 150 | bge-m3 | ✓ | hybrid | bge-reranker | 5 | **v3_kapsam** | 3.1-flash-lite | 3785 |
| EXP-021 | EXP-020 | v3 | cuda | pdfplumber | structural_v2 | 1500 | 150 | bge-m3 | ✓ | hybrid | bge-reranker | 5 | v3_kapsam | 3.1-flash-lite | 3785 |
| EXP-022 | EXP-021 | v3 | cuda | pdfplumber | structural_v2 | 1500 | 150 | bge-m3 | ✓ | hybrid | bge-reranker | 5 | v3_kapsam | 3.1-flash-lite | 3785 |
| EXP-023 | EXP-022 | **v4** | cuda | pdfplumber | structural_v2 | 1500 | 150 | bge-m3 | ✓ | hybrid | bge-reranker | 5 | v3_kapsam | 3.1-flash-lite | 3753 |
| EXP-024 | EXP-023 | v4 | cuda | pdfplumber | structural_v2 | 1500 | 150 | bge-m3 | ✓ | hybrid | bge-reranker | 5 | v3_kapsam | 3.1-flash-lite | 3753 |
| EXP-025 | EXP-024 | v4 | cuda | pdfplumber | structural_v2 | 1500 | 150 | bge-m3 | ✓ | hybrid | bge-reranker | 5 | **v4_netlestirme** | 3.1-flash-lite | 3753 |
| EXP-026 | EXP-024 | v4 | cuda | pdfplumber | structural_v2 | 1500 | 150 | bge-m3 | ✓ | hybrid | bge-reranker | 5 | v3_kapsam | 3.1-flash-lite | 3753 |
| EXP-027 | EXP-024 | v4 | cuda | pdfplumber | structural_v2 | 1500 | 150 | bge-m3 | ✓ | hybrid | bge-reranker | 5 | v3_kapsam | 3.1-flash-lite | 3753 |
| EXP-028 | EXP-027 | v4 | cuda | pdfplumber | structural_v2 | 1500 | 150 | bge-m3 | ✓ | hybrid | bge-reranker | 5 | v3_kapsam | 3.1-flash-lite | – |
| EXP-029 | EXP-027 | v4 | cuda | pdfplumber | structural_v2 | 1500 | 150 | bge-m3 | ✓ | hybrid | bge-reranker | 5 | v3_kapsam | 3.1-flash-lite | 3753 |
| EXP-030 | EXP-029 | v4 | cuda | pdfplumber | structural_v2 | 1500 | 150 | bge-m3 | ✓ | hybrid | bge-reranker | 5 | v3_kapsam | 3.1-flash-lite | 3753 |
| EXP-031 | EXP-029 | v4 | cuda | pdfplumber | structural_v2 | 1500 | 150 | bge-m3 | ✓ | **vector** | bge-reranker | 5 | v3_kapsam | 3.1-flash-lite | 3753 |
| EXP-032 | EXP-029 | v4 | cuda | pdfplumber | structural_v2 | 1500 | 150 | bge-m3 | ✓ | hybrid | bge-reranker | 5 | v3_kapsam | 3.1-flash-lite | – |
| EXP-033 | EXP-032 | v4 | cuda | pdfplumber | structural_v2 | 1500 | 150 | bge-m3 | ✓ | hybrid | bge-reranker | 5 | v3_kapsam | 3.1-flash-lite | 3753 |
| EXP-034 | EXP-033 | v4 | cuda | pdfplumber | structural_v2 | 1500 | 150 | bge-m3 | ✓ | hybrid | bge-reranker | 5 | v3_kapsam | 3.1-flash-lite | 3753 |
| EXP-035 | EXP-033 | v4 | cuda | pdfplumber | structural_v2 | 1500 | 150 | bge-m3 | ✓ | hybrid | bge-reranker | 5 | v3_kapsam | **3.5-flash-lite** | 3753 |
| EXP-036 | EXP-033 | v4 | cuda | pdfplumber | structural_v2 | 1500 | 150 | bge-m3 | ✓ | hybrid | bge-reranker | 5 | **v7_kapsamsiz** | 3.1-flash-lite | 3753 |
| EXP-037 | EXP-036 | v4 | cuda | pdfplumber | structural_v2 | 1500 | 150 | bge-m3 | ✓ | hybrid | bge-reranker | 5 | **v8_kapsamsiz** | 3.1-flash-lite | 3753 |
| EXP-038 | EXP-037 | v4 | cuda | pdfplumber | structural_v2 | 1500 | 150 | bge-m3 | ✓ | hybrid | bge-reranker | 5 | v8_kapsamsiz | 3.1-flash-lite | – |
| EXP-039 | EXP-038 | v4 | cuda | pdfplumber | structural_v2 | 1500 | 150 | bge-m3 | ✓ | hybrid | bge-reranker | 5 | **v9_kapsamsiz** | 3.1-flash-lite | 3753 |
| EXP-040 | EXP-038 | v4 | cuda | pdfplumber | structural_v2 | 1500 | 150 | bge-m3 | ✓ | hybrid | bge-reranker | 5 | v8_kapsamsiz | 3.1-flash-lite | 3753 |
| EXP-041 | EXP-038 | v4 | cuda | pdfplumber | structural_v2 | 1500 | 150 | bge-m3 | ✓ | hybrid | bge-reranker | 5 | v8_kapsamsiz | 3.1-flash-lite | 3753 |
| EXP-042 | EXP-041 | v4 | cuda | pdfplumber | structural_v2 | 1500 | 150 | bge-m3 | ✓ | hybrid | bge-reranker | 5 | v8_kapsamsiz | 3.1-flash-lite | 3753 |
| EXP-043 | EXP-041 | v4 | cuda | pdfplumber | structural_v2 | 1500 | 150 | bge-m3 | ✓ | hybrid | bge-reranker | 5 | v8_kapsamsiz | 3.1-flash-lite | 3753 |
| EXP-044 | EXP-043 | **v5** | cuda | pdfplumber | structural_v2 | 1500 | 150 | bge-m3 | ✓ | hybrid | bge-reranker | 5 | v8_kapsamsiz | 3.1-flash-lite | 3802 |
| EXP-045 | EXP-044 | v5 | cuda | pdfplumber | structural_v2 | 1500 | 150 | bge-m3 | ✓ | hybrid | bge-reranker | 5 | v8_kapsamsiz | 3.1-flash-lite | 3802 |
| EXP-046 | EXP-045 | v5 | cuda | pdfplumber | structural_v2 | 1500 | 150 | bge-m3 | ✓ | hybrid | bge-reranker | 5 | v8_kapsamsiz | 3.1-flash-lite | 3802 |
| EXP-047 | EXP-044 | v5 | cuda | pdfplumber | structural_v2 | 1500 | 150 | bge-m3 | ✓ | hybrid | bge-reranker | 5 | v8_kapsamsiz | 3.1-flash-lite | 3802 |
| EXP-048 | EXP-047 | v5 | cuda | pdfplumber | structural_v2 | 1500 | 150 | bge-m3 | ✓ | hybrid | bge-reranker | 5 | v8_kapsamsiz | 3.1-flash-lite | 3802 |
| EXP-049 | EXP-048 | v5 | cuda | pdfplumber | structural_v2 | 1500 | 150 | bge-m3 | ✓ | hybrid | bge-reranker | 5 | v8_kapsamsiz | 3.1-flash-lite | 3802 |
| EXP-050 | EXP-048 | v5 | cuda | pdfplumber | structural_v2 | 1500 | 150 | bge-m3 | ✓ | hybrid | bge-reranker | 5 | v8_kapsamsiz | 3.1-flash-lite | 3802 |

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
| EXP-017 | Referans: değerlendirme seti 2.0 → 3.0 (77 soru, 31 belge) | 3.0 | 0.852 | 0.789 | 0.930 | 0.930 | 5798 | 397 ms | referans (yeni soru seti, karşılaştırma yok) | – |
| EXP-018 | Prompt: v2 → v3_kapsam (kurallar kapsama göre farklıysa hepsi kapsamıyla) | 3.0 | 0.852 | 0.789 | 0.930 | 0.930 | 5798 | 394 ms | answer acc. ↓ kötüleşti (p=1.00, anlamlı değil) | ✗ |
| EXP-019 | Corpus: kopyalar çıkarıldı (v2 → v3, 139 → 131 belge) | 3.0 | 0.852 | 0.789 | 0.930 | 0.930 | 5728 | 407 ms | MRR@10 ↓ kötüleşti (p=1.00, anlamlı değil) | ✗ |
| EXP-020 | Prompt v3 (kapsam) kopyasız corpus'ta (v2_kaynakli → v3_kapsam, corpus v3) | 3.0 | 0.852 | 0.789 | 0.930 | 0.930 | 5728 | 366 ms | MRR@10 = değişmedi (p=1.00, anlamlı değil) | ✓ |
| EXP-021 | Reranker penceresi havuzun tamamı (rerank_candidates 8 → 30) | 3.0 | 0.871 | 0.817 | 0.944 | 0.944 | 5856 | 1.4 s | MRR@10 ↑ iyileşti (p=0.92, anlamlı değil) | ~ |
| EXP-022 | Reranker yarım hassasiyette (reranker_dtype fp32 → fp16) | 3.0 | 0.871 | 0.817 | 0.944 | 0.944 | 5856 | 363 ms | MRR@10 = değişmedi (p=1.00, anlamlı değil) | ✓ |
| EXP-023 | Yeni baseline: corpus v4 (2026-2027 takvimi, yaz öğretimi yok) + soru seti 4.0 | 4.0 | 0.816 | 0.733 | 0.940 | 0.940 | 5777 | 371 ms | referans (yeni soru seti, karşılaştırma yok) | – |
| EXP-024 | Soru seti 4.1 baseline'ı (prompt değişmeden, netleştirme ölçümüyle) | 4.1 | 0.818 | 0.735 | 0.940 | 0.940 | 5783 | 3.0 s | referans (yeni soru seti, karşılaştırma yok) | – |
| EXP-025 | Prompt v4_netlestirme: fakülte belirtilmemişse genel kural + fakülteyi sor | 4.1 | 0.818 | 0.735 | 0.940 | 0.940 | 5783 | 1.8 s | answer acc. ↓ kötüleşti (p=0.69, anlamlı değil) | ✗ |
| EXP-026 | Kapsam tamamlama (scope_search=parallel_v1): reddedilen alternatifin ölçümü | 4.1 | 0.817 | 0.735 | 0.940 | 0.940 | 6986 | 490 ms | context chars ↑ kötüleşti (p<0.01, anlamlı) | ✓ |
| EXP-027 | Netleştirmeyi belge kapsam etiketleri tetikler (clarify_trigger=scope_labels_v1) | 4.1 | 0.818 | 0.735 | 0.940 | 0.940 | 5783 | 329 ms | answer acc. ↓ kötüleşti (p=0.25, anlamlı değil) | ✗ |
| EXP-028 | Production yapılandırması: EXP-027 + yaz okulu sabit cevabı (fixed_answers=summer_v1) | | | | | | | | koşulmadı | |
| EXP-029 | Havuz derinliği A: vector_k ve bm25_k 15 → 30 (rerank_candidates 30 sabit) | 4.1 | 0.819 | 0.735 | 0.949 | 0.949 | 5785 | 562 ms | rerank_input_recall ↑ iyileşti (p=1.00, anlamlı değil) | ~ |
| EXP-030 | Havuz derinliği B: rerank_candidates 30 → 60 (reranker havuzun tamamını görür) | 4.1 | 0.818 | 0.735 | 0.949 | 0.949 | 5812 | 892 ms | rerank_input_recall = değişmedi (p=1.00, anlamlı değil) | ✓ |
| EXP-031 | Hybrid ablasyonu: retrieval hybrid → vector (reranker ve 30 aday sabit) | 4.1 | 0.820 | 0.735 | 0.940 | 0.940 | 5727 | 723 ms | rerank_input_recall ↓ kötüleşti (p=1.00, anlamlı değil) | ~ |
| EXP-032 | Production yapılandırması: EXP-029 (havuz derinliği A) + yaz okulu sabit cevabı (fixed_answers=summer_v1) | | | | | | | | koşulmadı | |
| EXP-033 | Baseline: production (EXP-032) set 4.2'de (birleştirme soruları + 80 → 90 etiketi) | 4.2 | 0.830 | 0.748 | 0.953 | 0.953 | 5756 | 447 ms | baseline |  |
| EXP-034 | Netleştirme cevabının biçimi tarif edilir (clarify_prompt=v5_netlestirme_kisa) | 4.2 | 0.830 | 0.748 | 0.953 | 0.953 | 5756 | 417 ms | netlestirme_uzunlugu ↓ iyileşti (p<0.01, anlamlı) | ✓ |
| EXP-035 | LLM gemini-3.1-flash-lite → gemini-3.5-flash-lite | 4.2 | 0.833 | 0.756 | 0.953 | 0.953 | 5752 | 430 ms | answer acc. ↑ iyileşti (p=1.00, anlamlı değil) | ~ |
| EXP-036 | Prompt v3_kapsam + v4_netlestirme → v7_kapsamsiz + v7_netlestirme | 4.2 | 0.830 | 0.748 | 0.953 | 0.953 | 5756 | 538 ms | answer acc. ↓ kötüleşti (p=0.38, anlamlı değil) | ✗ |
| EXP-037 | Ana prompt v7_kapsamsiz → v8_kapsamsiz (fakülte sorma kararı iki belge testine bağlı) | 4.2 | 0.830 | 0.748 | 0.953 | 0.953 | 5756 | 412 ms | answer acc. ↑ iyileşti (p=1.00, anlamlı değil) | ✗ |
| EXP-038 | Production yapılandırması: EXP-037 + staj sabit cevabı (fixed_answers=summer_staj_v1) | | | | | | | | koşulmadı | |
| EXP-039 | Başka üniversite anılınca BAİBÜ kuralını verme: v8_kapsamsiz → v9_kapsamsiz, v7_netlestirme → v8_netlestirme | 4.2 | 0.830 | 0.748 | 0.953 | 0.953 | 5756 | 416 ms | baseline |  |
| EXP-040 | Production (EXP-038) validation setinde: baseline | val-1.0 | 0.840 | 0.753 | 0.953 | 0.953 | 5239 | 413 ms | baseline |  |
| EXP-041 | Production yapılandırması: staj sabit cevabının kör noktaları kapatıldı (fixed_answers=summer_staj_v2) | 4.2 | 0.830 | 0.748 | 0.953 | 0.953 | 5756 | 423 ms | baseline |  |
| EXP-042 | Resmi belge başlıkları: chunk başlığında dosya adı yerine belge kataloğundaki ad (doc_titles=katalog_v1) | 4.2 | 0.814 | 0.740 | 0.921 | 0.921 | 5878 | 437 ms | MRR@10 ↓ kötüleşti (p=0.09, anlamlı değil) | ✗ |
| EXP-043 | Baseline: production yapılandırması (corpus v4) set 4.5'te, yalnız retrieval | 4.5 | 0.758 | 0.683 | 0.871 | 0.871 | 5776 | 451 ms | referans (yeni soru seti, karşılaştırma yok) | – |
| EXP-044 | Corpus v5: Bilgisayar Mühendisliği ders programı ve akademik personeli (JSON, kayıt bazında chunk) | 4.5 | 0.841 | 0.763 | 0.957 | 0.957 | 5462 | 479 ms | context_hit ↑ iyileşti (p<0.01, anlamlı) | ✓ |
| EXP-045 | Production (EXP-044) validation setinde (val-1.0): soru türü başına cevap doğruluğu | val-1.0 | 0.840 | 0.753 | 0.953 | 0.953 | 5227 | 412 ms | referans (yeni soru seti, karşılaştırma yok) | – |
| EXP-046 | Production (EXP-044) validation seti 2.0'da: öğrenci dili ve soru türü başına cevap doğruluğu | val-2.0 | 0.749 | 0.659 | 0.898 | 0.898 | 5272 | 420 ms | referans (yeni soru seti, karşılaştırma yok) | – |
| EXP-047 | Production (EXP-044) dev seti 4.6'da: soru türü başına baseline | 4.6 | 0.817 | 0.738 | 0.929 | 0.929 | 5467 | 456 ms | referans (yeni soru seti, karşılaştırma yok) | – |
| EXP-048 | Production (EXP-044) dev seti 4.7'de: retrieval baseline (BM25 tokenizer deneyleri için) | 4.7 | 0.808 | 0.722 | 0.925 | 0.925 | 5440 | 429 ms | referans (yeni soru seti, karşılaştırma yok) | – |
| EXP-049 | BM25 tokenizer: ilk 5 harf -> Snowball Türkçe stemmer | 4.7 | 0.802 | 0.711 | 0.925 | 0.925 | 5417 | 428 ms | rerank_input_recall ↓ kötüleşti (p=1.00, anlamlı değil) | ✗ |
| EXP-050 | BM25 tokenizer: ilk 5 harf -> Türkçe karakter katlama + ilk 5 harf | 4.7 | 0.808 | 0.722 | 0.925 | 0.925 | 5443 | 437 ms | MRR@10 ↓ kötüleşti (p=0.32, anlamlı değil) | ✗ |

Hyp.: ✓ doğrulandı · ✗ doğrulanmadı · ~ yön doğru ama anlamlı değil

## 3. Retrieval stages

Her ara listede MRR@10. Rerank input recall: ilgili chunk reranker'a giden adaylar içinde mi (reranker'ın düzeltebileceğinin üst sınırı). Aşama verisi EXP-014'ten itibaren kaydediliyor.

| Exp | Vector | BM25 | RRF | Rerank input recall | Final |
|---|---|---|---|---|---|
| EXP-014 | 0.938 | 0.838 | 0.938 | 1.000 | 1.000 |
| EXP-015 | 0.602 | 0.581 | 0.594 | 0.963 | 0.863 |
| EXP-016 | 0.600 | 0.581 | 0.594 | 0.963 | 0.863 |
| EXP-017 | 0.674 | 0.588 | 0.687 | 0.944 | 0.852 |
| EXP-018 | 0.674 | 0.588 | 0.687 | 0.944 | 0.852 |
| EXP-019 | 0.682 | 0.593 | 0.680 | 0.958 | 0.852 |
| EXP-020 | 0.682 | 0.593 | 0.680 | 0.958 | 0.852 |
| EXP-021 | 0.682 | 0.593 | 0.680 | 0.986 | 0.871 |
| EXP-022 | 0.682 | 0.593 | 0.680 | 0.986 | 0.871 |
| EXP-023 | 0.622 | 0.520 | 0.630 | 0.966 | 0.816 |
| EXP-024 | 0.625 | 0.517 | 0.628 | 0.966 | 0.818 |
| EXP-025 | 0.625 | 0.517 | 0.628 | 0.966 | 0.818 |
| EXP-026 | 0.625 | 0.517 | 0.628 | 0.966 | 0.817 |
| EXP-027 | 0.625 | 0.517 | 0.628 | 0.966 | 0.818 |
| EXP-029 | 0.625 | 0.517 | 0.625 | 0.974 | 0.819 |
| EXP-030 | 0.625 | 0.517 | 0.625 | 0.974 | 0.818 |
| EXP-031 | 0.625 | – | – | 0.966 | 0.820 |
| EXP-033 | 0.646 | 0.523 | 0.635 | 0.976 | 0.830 |
| EXP-034 | 0.646 | 0.523 | 0.635 | 0.976 | 0.830 |
| EXP-035 | 0.649 | 0.534 | 0.636 | 0.976 | 0.833 |
| EXP-036 | 0.646 | 0.523 | 0.635 | 0.976 | 0.830 |
| EXP-037 | 0.646 | 0.523 | 0.635 | 0.976 | 0.830 |
| EXP-039 | 0.646 | 0.523 | 0.635 | 0.976 | 0.830 |
| EXP-040 | 0.699 | 0.608 | 0.708 | 0.965 | 0.840 |
| EXP-041 | 0.646 | 0.523 | 0.635 | 0.976 | 0.830 |
| EXP-042 | 0.615 | 0.527 | 0.629 | 0.969 | 0.814 |
| EXP-043 | 0.590 | 0.478 | 0.584 | 0.892 | 0.758 |
| EXP-044 | 0.672 | 0.560 | 0.666 | 0.978 | 0.841 |
| EXP-045 | 0.698 | 0.604 | 0.700 | 0.965 | 0.840 |
| EXP-046 | 0.579 | 0.423 | 0.567 | 0.943 | 0.749 |
| EXP-047 | 0.643 | 0.514 | 0.625 | 0.958 | 0.817 |
| EXP-048 | 0.651 | 0.506 | 0.622 | 0.957 | 0.808 |
| EXP-049 | 0.651 | 0.456 | 0.647 | 0.952 | 0.802 |
| EXP-050 | 0.651 | 0.521 | 0.628 | 0.957 | 0.808 |

## 4. Soru grupları (MRR@10)

Set 3.0'dan itibaren. Parantez içi soru sayısı; küçük gruplarda ortalama gürültülüdür.

| Exp | Eski sorular | Yeni sorular | Belge dili | Öğrenci dili | Fakülteye özel | Çok kapsamlı |
|---|---|---|---|---|---|---|
| EXP-017 | 0.900 (27) | 0.822 (44) | 0.921 (42) | 0.751 (29) | 1.000 (3) | 1.000 (2) |
| EXP-018 | 0.900 (27) | 0.822 (44) | 0.921 (42) | 0.751 (29) | 1.000 (3) | 1.000 (2) |
| EXP-019 | 0.932 (27) | 0.802 (44) | 0.923 (42) | 0.748 (29) | 1.000 (3) | 0.550 (2) |
| EXP-020 | 0.932 (27) | 0.802 (44) | 0.923 (42) | 0.748 (29) | 1.000 (3) | 0.550 (2) |
| EXP-021 | 0.921 (27) | 0.840 (44) | 0.937 (42) | 0.775 (29) | 1.000 (3) | 1.000 (2) |
| EXP-022 | 0.921 (27) | 0.840 (44) | 0.937 (42) | 0.775 (29) | 1.000 (3) | 1.000 (2) |
| EXP-023 | 0.933 (26) | 0.782 (90) | 0.911 (46) | 0.753 (70) | 0.814 (17) | 0.737 (12) |
| EXP-024 | 0.933 (26) | 0.784 (91) | 0.911 (46) | 0.757 (71) | 0.814 (17) | 0.737 (12) |
| EXP-025 | 0.933 (26) | 0.784 (91) | 0.911 (46) | 0.757 (71) | 0.814 (17) | 0.737 (12) |
| EXP-026 | 0.933 (26) | 0.783 (91) | 0.911 (46) | 0.755 (71) | 0.814 (17) | 0.737 (12) |
| EXP-027 | 0.933 (26) | 0.784 (91) | 0.911 (46) | 0.757 (71) | 0.814 (17) | 0.737 (12) |
| EXP-029 | 0.933 (26) | 0.787 (91) | 0.911 (46) | 0.759 (71) | 0.814 (17) | 0.737 (12) |
| EXP-030 | 0.931 (26) | 0.786 (91) | 0.910 (46) | 0.758 (71) | 0.814 (17) | 0.737 (12) |
| EXP-031 | 0.942 (26) | 0.786 (91) | 0.917 (46) | 0.758 (71) | 0.814 (17) | 0.737 (12) |
| EXP-033 | 0.933 (26) | 0.803 (101) | 0.911 (46) | 0.783 (81) | 0.814 (17) | 0.834 (22) |
| EXP-034 | 0.933 (26) | 0.803 (101) | 0.911 (46) | 0.783 (81) | 0.814 (17) | 0.834 (22) |
| EXP-035 | 0.933 (26) | 0.807 (101) | 0.911 (46) | 0.788 (81) | 0.814 (17) | 0.834 (22) |
| EXP-036 | 0.933 (26) | 0.803 (101) | 0.911 (46) | 0.783 (81) | 0.814 (17) | 0.834 (22) |
| EXP-037 | 0.933 (26) | 0.803 (101) | 0.911 (46) | 0.783 (81) | 0.814 (17) | 0.834 (22) |
| EXP-039 | 0.933 (26) | 0.803 (101) | 0.911 (46) | 0.783 (81) | 0.814 (17) | 0.834 (22) |
| EXP-040 | – | 0.840 (85) | 1.000 (1) | 0.838 (84) | 1.000 (4) | 0.491 (12) |
| EXP-041 | 0.933 (26) | 0.803 (101) | 0.911 (46) | 0.783 (81) | 0.814 (17) | 0.834 (22) |
| EXP-042 | 0.952 (26) | 0.779 (101) | 0.897 (46) | 0.767 (81) | 0.789 (17) | 0.823 (22) |
| EXP-043 | 0.933 (26) | 0.718 (113) | 0.892 (47) | 0.689 (92) | 0.814 (17) | 0.820 (24) |
| EXP-044 | 0.933 (26) | 0.819 (113) | 0.913 (47) | 0.803 (92) | 0.814 (17) | 0.820 (24) |
| EXP-045 | – | 0.840 (85) | 1.000 (1) | 0.838 (84) | 1.000 (4) | 0.491 (12) |
| EXP-046 | – | 0.749 (88) | 0.958 (12) | 0.715 (76) | 0.833 (4) | 0.417 (12) |
| EXP-047 | 0.933 (26) | 0.795 (142) | 0.913 (47) | 0.779 (121) | 0.814 (17) | 0.820 (24) |
| EXP-048 | 0.933 (26) | 0.788 (161) | 0.913 (47) | 0.773 (140) | 0.814 (17) | 0.820 (24) |
| EXP-049 | 0.936 (26) | 0.780 (161) | 0.915 (47) | 0.764 (140) | 0.814 (17) | 0.820 (24) |
| EXP-050 | 0.933 (26) | 0.788 (161) | 0.913 (47) | 0.772 (140) | 0.814 (17) | 0.820 (24) |

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
- **EXP-017:** Yeni baseline: MRR@10 0,852, answer_acc 0,896. Öğrenci dili 0,75 / belge dili 0,92 (MRR). Bazı hatalar eksik etiket ve anahtar kelime eşleşmesi.
- **EXP-018:** answer_acc 0,896 → 0,883 (anlamsız). Değişen 3 sorudan biri gerçek iyileşme (iki kapsamı ayırdı), biri kelime artefaktı, biri boş API cevabı.
- **EXP-019:** Context'teki kopya madde tekrarı 31 → 0; MRR@10 aynı (0,852). Büyük sıra değişimleri reranker penceresinin (8 aday) sınırından.
- **EXP-020:** Retrieval EXP-019 ile birebir aynı (beklenen). Production'a alındı; prompt etkisi gerçek kullanım kayıtlarıyla ölçülecek.
- **EXP-021:** Darboğaz kalktı: rerank input recall 0,958 → 0,986, pencere dışındaki 2 soru 1. sıraya çıktı; MRR@10 +0,019 (anlamlı değil). 3 soru 1-4 sıra geriledi, 1 'kötüleşme' eksik etiket. Gecikme +1 sn.
- **EXP-022:** Sıralama birebir aynı (71/71 soruda ilk 5 chunk aynı); gecikme 1372 → 363 ms. Production EXP-020 → EXP-022.
- **EXP-023:** Yeni baseline (set 4.0): MRR@10 0,816, cevap 0,885. Kapsam isabeti 0,507; takip soruları 15/15. 16 yanlışın 10'u gerçek (kapsam 5, retrieval 2, eskimiş yaz bilgisi 3), 2'si boş cevap (RECITATION), 4'ü ölçüm/etiket hatası.
- **EXP-024:** Set 4.1 baseline: MRR@10 0,818, cevap 0,942 (131/139); netleştirme 0/8, gereksiz 0 (prompt'ta kural yok). 8 yanlışın 2'si Türkçe olumsuz fiil biçiminden ölçüm hatası, 6'sı gerçek (retrieval 2, eskimiş yaz bilgisi 2, kapsam 1, belirsiz 1).
- **EXP-025:** Netleştirme 8/8 ama gereksiz netleştirme %45 (beklenen <= %5): model fakülteden bağımsız sorularda da soruyor; fakülte belirtilen 17 soruda 1. Cevap 0,928 (anlamca fark yok). Production'a alınmaz; tetikleme LLM'e bırakılınca aşırı.
- **EXP-026:** Reddedilen alternatif: kapsam isabeti 0,507 -> 0,576 (12 sorunun yalnız 2'si iyileşti), ama 117 sorunun 50'sinde tetiklendi ve context +%21 (tetiklenenlerde +%48) uzadı; MRR@10 değişmedi. Bırakıldı.
- **EXP-027:** Etiketle tetikleme: netleştirme 6/8, gereksiz 0,45 -> 0,26, fakülte belirtilende 0/17; sorma yalnız tetik açıkken. Cevap anlamca aynı (0,921). Cevaplar hâlâ diğer kapsamları sayıyor.
- **EXP-028:** Production yapılandırması, koşu yok: 9/9 yaz sorusu sabit cevap, diğer 130 soruda eşleşme yok. Production EXP-023 → EXP-028.
- **EXP-029:** Havuz 15 -> 30: reranker girdisi isabeti 0,966 -> 0,974 (+1 soru, kayıp yok), MRR aynı; latency 329 -> 562 ms. Kalan 3 kayıp ilk 30'da da yok, B'nin kazancı olamaz.
- **EXP-030:** Reranker havuzun tamamını görüyor: recall aynı (0,974), MRR 0,819 -> 0,818 (2 soru biraz düştü, iyileşen yok), latency 562 -> 892 ms. Alınmaz.
- **EXP-031:** Vector-only: BM25'in getirdiği tek soru kayboldu (recall 0,974 -> 0,966), 3 soru biraz iyileşti, MRR aynı (0,820). Latency ölçümü GPU paylaşımı yüzünden güvenilir değil.
- **EXP-032:** Production yapılandırması, koşu yok: EXP-029 retrieval'ı + yaz okulu sabit cevabı (9/9). Latency 347 → 437 ms. Production EXP-028 → EXP-032.
- **EXP-033:** 3.1 baseline set 4.2: cevap doğruluğu 0,966, birleştirme 3/10, netleştirme cevabı 674 karakter, LLM latency 4,0 sn. Sonraki prompt deneylerinin referansı.
- **EXP-034:** Kısa netleştirme: netleştirme cevabı 674 -> 359 karakter (p<0,001), ama 2 çekimser kalma sorusunda 'bilgim yok' yerine genel kural yazıyor; gereksiz netleştirme 0,21 -> 0,24.
- **EXP-035:** 3.5 flash-lite: cevap doğruluğu 0,966 -> 0,973 (anlamca ~eşit), cevaplar ve netleştirme belirgin kısa, LLM latency 4,0 -> 14,5 sn. Öneri: 3.1'de kal.
- **EXP-037:** v8: gereksiz netleştirme 0,624 -> 0,284, cevap 323 karakter, doğruluk 0,953 (yeni hata yok). git_dirty yalnız TODO.md'den. Production.
- **EXP-038:** Production yapılandırması, koşu yok: EXP-037 + staj sabit cevabı (yalnız birim belirtmeyen staj sorusu değişiyor). Production EXP-037 -> EXP-038.
- **EXP-039:** Hipotez tutmadı: BAİBÜ açıklaması 23/149 alakasız cevaba sızdı, netleştirme 0,875 -> 0,5, cevap +47 karakter. Production'a alınmadı.
- **EXP-040:** Validation baseline: doğruluk 0,85 (anlamca 0,95), netleştirme 12/12. En zayıf grup çok maddeli sorular (9/12, ikinci alt soru düşüyor). 10 yanlış etiket kaynaklı.
- **EXP-041:** Production yapılandırması, koşu yok: staj sabit cevabında bölüm adları, sigorta konuları ve tekrar sorma döngüsü düzeltildi; set 4.2'de karar değişmiyor. Production EXP-038 -> EXP-041.
- **EXP-042:** Resmi başlıklar chunk metninde retrieval'ı biraz düşürdü (MRR@10 0,830 -> 0,814, anlamlı değil; bağlam isabeti 0,953 -> 0,921); production değişmedi.
- **EXP-043:** Baseline (v4, set 4.5, yalnız retrieval): eski 127 soru EXP-041 ile aynı; yeni 12 ders programı/personel sorusu bulunamıyor.
- **EXP-044:** Corpus v5 (ders programı + personel JSON): yeni 12 soru 12/12 doğru, 6 çekimser soru doğru; eski 127 sorunun context'i hiç değişmedi. Production EXP-041 -> EXP-044.
- **EXP-045:** Production val-1.0'da anlamca 0,93 (anahtar 0,84); intörnlük düzeldi. En zayıf tür birden fazla madde gerektiren sorular (9/12); EXP-040 incelemesinden kaçan 3 hata bulundu.
- **EXP-046:** Öğrenci dilinde production: anlamca 0,88, MRR@10 0,749. En zayıf: birden fazla madde/belge 9/15, netleştirme 9/12, yazım hatalı 8/10.
- **EXP-048:** Dev 4.7 retrieval baseline: MRR@10 0,808, bağlam isabeti 0,925; en zayıf farklı ifade (0,72).
- **EXP-049:** Snowball stemmer BM25'i kötüleştirdi (MRR 0,506 -> 0,456); bağlam isabeti aynı. Production değişmedi.
- **EXP-050:** Karakter katlama BM25 MRR'ı artırdı (0,506 -> 0,521) ama final sıralama aynı; production değişmedi.
