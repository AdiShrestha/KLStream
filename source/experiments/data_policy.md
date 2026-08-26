# Data Sourcing, Licensing, and Provenance Policy — KLStream

**Version:** 1.0.0  
**Effective Date:** 2026-08-26  
**Governing Decision:** `DL-008` (Zero-Cost Academic Sample & Synthetic Order-Book Simulation Policy)  
**License Compliance:** AGPLv3 / Open Science Policy

---

## 1. Executive Summary & Policy Statement

In accordance with Project Decision **`DL-008`**, KLStream operates under a strict **zero-cost academic and open-science data policy**. This research project has zero commercial data budget. All empirical benchmarks, statistical validations, and system evaluations are conducted exclusively using:
1. **Public Academic Samples:** Officially released, non-commercial sample order-book datasets (e.g., LOBSTER academic benchmark sample data or NASDAQ open sample datasets).
2. **Explicitly Labeled Synthetic Market Streams:** Deterministic, multi-seed continuous double auction (CDA) order-book market simulations generated directly from verified open-source generator code.

---

## 2. Prohibition of Commercial Data Claims (INV-001 & INV-002)

To maintain scientific integrity and prevent deceptive or unsubstantiated claims:
- **Strict Prohibition:** Authors, contributors, and evaluation pipelines are explicitly prohibited from claiming or implying access to commercial, paid, full-day LOBSTER AAPL or proprietary market feed data without documented purchase receipts and institutional authorization.
- **Disjoint Identification (INV-001 / INV-002):** Synthetic market data files and academic sample files must reside in distinct directory paths with unambiguous file naming (e.g., `data/synthetic/synthetic_orderbook_seedN.csv` vs. `data/raw/academic_sample/lobster_sample_*.csv`). Silent substitution or conflation of synthetic data with real market data is strictly forbidden.

---

## 3. Data Categories and Usage Terms

### 3.1 Category A: Synthetic Market Simulations (`data/synthetic/`)
- **Generation:** Produced by `source/experiments/preprocessing/synthetic_generator.py` using calibrated geometric Brownian motion (GBM) with Poisson order arrivals and stochastic spread dynamics.
- **Licensing:** Generated directly by project code under the project's **AGPLv3** open-source license.
- **Usage:** Used for multi-seed statistical replication (addressing review critique **MAR-3**), stress testing, backpressure profiling, and synthetic anomaly injection benchmarks.

### 3.2 Category B: Public Academic Samples (`data/raw/academic_sample/`)
- **Source:** Publicly downloadable academic sample files provided by benchmark data vendors (e.g., Humboldt University of Berlin / LOBSTER academic sample).
- **Terms:** Used solely for non-commercial academic research and algorithmic comparison in compliance with academic fair-use guidelines.
- **Licensing & Distribution:** Raw third-party data files are git-ignored or stored as reproducible download artifacts. Full provenance receipts (`academic_sample_provenance.json`) record origin URL, date retrieved, file hash, and sample characteristics.

### 3.3 Category C: Clean Preprocessed Data (`data/processed/`)
- **Artifacts:** Preprocessed feature vectors and injection labels (`processed_*.csv`, `injection_manifest.json`, `split_manifest.json`).
- **Validation:** Must pass all 6 checks of the **Reality Gate** (`reality_gate.py`) prior to being ingested by downstream models or C++ streaming replay harnesses.

---

## 4. Integrity and Provenance Rules

1. **Deterministic Reproducibility:** Every synthetic dataset must record its exact random seed, generation parameters, and timestamp in `synthetic_generation_manifest.json`.
2. **Temporal Split Monotonicity (INV-005):** Evaluation splits must follow strict temporal separation ($T_{\text{train}} < T_{\text{val}} < T_{\text{test}}$) with zero lookahead leakage.
3. **Audit Trail:** All data generation and preprocessing scripts are version-controlled in `source/experiments/preprocessing/`.
