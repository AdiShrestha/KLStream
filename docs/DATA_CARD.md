# Data Card — KLStream Authentic Observational Cohort

## 1. Dataset Summary & Origin

- **Dataset Identifier:** `klstream-btc-usdt-observational-cohort-v1`
- **Origin / Upstream Source:** Binance Public Data Archive (`https://data.binance.vision/`)
- **Instrument:** Spot Market `BTCUSDT` (Bitcoin / Tether)
- **Temporal Horizon:** August 17, 2017 through August 19, 2017 (3 consecutive calendar days)
- **Primary Artifacts:**
  - Raw Ingestion Checksums: `data/source_records.csv`
  - Provenance Specification: `data/provenance.json`
  - Cohort Manifest: `data/cohort.csv`
- **License:** Creative Commons Attribution 4.0 International (CC-BY-4.0)

---

## 2. Cryptographic Provenance & Verification

Each raw daily archive was verified against provider-issued cryptographic checksums:

| Archive Name | Provider Checksum Hash | Verification Digest (SHA-256) | Status |
|---|---|---|---|
| `BTCUSDT-trades-2017-08-17.zip` | Provider `.CHECKSUM` | `9c43d561a3f6f9fcda831b01777d46fc7d58133ca06b3a24687550302b1c2b51` | Authentic |
| `BTCUSDT-trades-2017-08-18.zip` | Provider `.CHECKSUM` | `7be2e1ba09e6cf27b3f9ff7fe3a7a9fc75073e514f76269df10f279d63c5a70d` | Authentic |
| `BTCUSDT-trades-2017-08-19.zip` | Provider `.CHECKSUM` | `d0c3ebc9c3ca9d5d8868c2805b45aa3e35a1215bb4c3a7711d95015b7468132e` | Authentic |

The immutable hashes of all ingested files are recorded in `data/source_records.csv` (SHA-256: `3754da4d952e9eeee2c48bfeda9edc138fe99b188c1364d36d9fbdcfaf96d6b7`).

---

## 3. Sampling, Partitioning & Cohort Design

The cohort manifest `data/cohort.csv` contains **10,813 records** partitioned strictly by temporal horizon across 30-minute independent trading windows:

| Split Name | Calendar Date | Record Count | Independent Groups | Positive Anomalies | Negative Normals | Anomaly Prevalence |
|---|---|---|---|---|---|---|
| `train` | 2017-08-17 | 3,427 | 40 | 72 | 3,355 | 0.021010 |
| `validation` | 2017-08-18 | 5,233 | 48 | 111 | 5,122 | 0.021211 |
| `test` | 2017-08-19 | 2,153 | 48 | 46 | 2,107 | 0.021365 |
| **Total** | **3 Days** | **10,813** | **136** | **229** | **10,584** | **0.021178** |

### Split Hygiene & Policy Floors
- **Group-Safe Temporal Separation:** Train, validation, and test splits correspond to disjoint calendar days. No samples or windows are shared across splits.
- **Statistical Power Floors:** The test split contains **48 independent test groups** (exceeding the policy floor of $\ge 30$) and **46 positive anomalies** (exceeding the floor of $\ge 10$).
- **Monotonic Time Ordering:** Timestamps are strictly non-decreasing; any out-of-order records trigger fail-closed abortion.

---

## 4. Derived Features & Mathematical Specification

Each event record is parsed causally (without forward-looking information) into 7 numeric dimensions:

1. `price` ($P_t$): Execution trade price in USDT.
2. `qty` ($Q_t$): Executed base quantity in BTC.
3. `quote_qty` ($V_t = P_t \cdot Q_t$): Notional quote volume in USDT.
4. `is_buyer_maker` ($M_t \in \{0.0, 1.0\}$): Trade direction indicator (1 if buyer was maker, 0 if seller was maker).
5. `interarrival_ms` ($\Delta t = (T_t - T_{t-1})$): Elapsed time from previous trade in milliseconds.
6. `log_return` ($r_t = \ln(P_t / P_{t-1})$): Instantaneous log price return ($0.0$ for initial event).
7. `trade_flow` ($F_t = (1 - 2M_t) \cdot Q_t$): Signed signed trade order flow.

Full mathematical definitions, normalization constants, and error conditions are documented in `docs/FEATURE_SPECIFICATION.md`.
