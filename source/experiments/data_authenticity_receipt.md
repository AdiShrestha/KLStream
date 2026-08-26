# Data Authenticity & Provenance Verification Receipt — KLStream

**Date:** 2026-08-26  
**Governing Policies:** Project Decision `DL-008`, `source/experiments/data_policy.md`  
**Reality Gate Status:** `PASS` (100% of domain checks satisfied across all datasets)

---

## 1. Executive Summary & Authenticity Certification

This receipt certifies the full provenance, integrity, and non-colliding separation of all datasets utilized in the KLStream evaluation pipeline. In accordance with Decision **`DL-008`**, all evaluations are performed strictly on open-science academic benchmark samples and explicitly labeled multi-seed synthetic market simulations.

**Zero Commercial Data Access:** No claims of commercial, full-day LOBSTER AAPL data access are made or implied.

---

## 2. Multi-Seed Synthetic Market Realizations (`data/synthetic/`)

To eliminate the single-dataset pseudo-replication defect (**MAR-3**), 5 independent realization seeds were generated using `source/experiments/preprocessing/synthetic_generator.py`:

| Dataset Filename | Seed | Events | Injected Episodes | Anomalous Ticks | SHA-256 Digest |
|---|---|---|---|---|---|
| `synthetic_orderbook_seed101.csv` | 101 | 10,000 | 7 | 293 | `6e4d448e7a9a3f25c79e672722b51336d39691456d2cf9249ea93e3d368e5ff4` |
| `synthetic_orderbook_seed102.csv` | 102 | 10,000 | 7 | 276 | `028b0a13b02bfa406cb7bbd4e782c5a1fe0c7d42cf3fa19b26f588c8869c4fa7` |
| `synthetic_orderbook_seed103.csv` | 103 | 10,000 | 7 | 257 | `79bfc3d8bf90d20d43702585ee58129e924a13c9e6d013697eb2f84570ffbe1b` |
| `synthetic_orderbook_seed104.csv` | 104 | 10,000 | 7 | 308 | `55d83e942314644a49c25f448c4cf84f3dfcbffb12db1704e0e5a95ae182da94` |
| `synthetic_orderbook_seed105.csv` | 105 | 10,000 | 7 | 366 | `91428dfea7658c148e64c24ea095c57b7f1681dc5986fc0a4aa19b6ba1caae28` |

---

## 3. Public Academic Sample Dataset (`data/raw/academic_sample/`)

- **Dataset Identity:** LOBSTER Level-1 Academic Benchmark Sample (AMZN 2012-06-21)
- **Source URL:** `https://lobsterdata.com/info/DataSamples.php`
- **Retrieval Date:** 2026-08-26
- **Files & Hashes:**
  - `AMZN_2012-06-21_34200000_57600000_message_1.csv` (187,627 bytes, 5,000 rows, SHA-256: `8038464096ec981209fe3e2518bb1b033aa0ee1ce0cb34d0320f5345cace2bfd`)
  - `AMZN_2012-06-21_34200000_57600000_orderbook_1.csv` (130,632 bytes, 5,000 rows, SHA-256: `0e5e2482d24927272120ca4d67edd747964c5af25bfe38e1a52c6c78f9ec7613`)

---

## 4. Preprocessed Replay Datasets & Split Allocations (`data/processed/`)

All raw inputs were preprocessed via `preprocess.py` and partitioned chronologically (60% Train, 20% Val, 20% Test) via `create_splits.py`:

| Replay Dataset | Source | Total Rows | Train [0, 60%) | Val [60%, 80%) | Test [80%, 100%] |
|---|---|---|---|---|---|
| `replay_academic_sample_AMZN_2012-06-21_34200000_57600000.csv` | Academic Sample | 5,000 | 3,000 | 1,000 | 1,000 |
| `replay_synthetic_seed101.csv` | Synthetic Seed 101 | 10,000 | 6,000 | 2,000 | 2,000 |
| `replay_synthetic_seed102.csv` | Synthetic Seed 102 | 10,000 | 6,000 | 2,000 | 2,000 |
| `replay_synthetic_seed103.csv` | Synthetic Seed 103 | 10,000 | 6,000 | 2,000 | 2,000 |
| `replay_synthetic_seed104.csv` | Synthetic Seed 104 | 10,000 | 6,000 | 2,000 | 2,000 |
| `replay_synthetic_seed105.csv` | Synthetic Seed 105 | 10,000 | 6,000 | 2,000 | 2,000 |

---

## 5. Invariant & Governance Compliance

1. **INV-001 (Provenance Transparency):** Every dataset records upstream origin URLs or generator parameters with complete SHA-256 receipts.
2. **INV-002 (Synthetic/Real Separation & MAR-1):** Zero files share the ambiguous legacy name `replay_AAPL_20120621.csv`. All paths strictly reside under `data/synthetic/` or `data/raw/academic_sample/`.
3. **INV-004 (Schema Continuity & MAR-X2):** All 35 injected anomaly episodes are indexed with exact row spans in `data/processed/injection_manifest.json`.
4. **INV-005 & SVI-002 (Leakage-Safe Partitioning):** Monotonic temporal boundaries ($T_{\text{train}} \le T_{\text{val}} \le T_{\text{test}}$) frozen in `data/processed/split_manifest.json`.
5. **SVI-001 (Reality Gate Verification):** Automated verification passed 100% of checks with zero violations across all 55,000 events (`reality_gate_report.json`).
