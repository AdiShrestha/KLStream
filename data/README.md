# KLStream Data Directory & Reproduction Guide

**Factory Version:** 2.2.0  
**Governing Policy:** Project Decision `DL-008` (Zero-Cost Academic Sample & Synthetic Simulation Policy)  
**License:** GNU Affero General Public License v3 (AGPLv3)

---

## 1. Directory Structure Layout

The `data/` directory is organized into strict, non-colliding hierarchies to maintain scientific provenance and prevent conflation between synthetic simulations and academic benchmark data:

```
data/
├── raw/
│   └── academic_sample/                        # Public academic benchmark sample files
│       ├── AMZN_2012-06-21_..._message_1.csv   # LOBSTER Level-1 message file
│       └── AMZN_2012-06-21_..._orderbook_1.csv # LOBSTER Level-1 orderbook file
├── synthetic/                                  # Multi-seed synthetic market realizations
│       ├── synthetic_orderbook_seed101.csv     # Realization seed 101 (10,000 rows)
│       ├── synthetic_orderbook_seed102.csv     # Realization seed 102 (10,000 rows)
│       ├── synthetic_orderbook_seed103.csv     # Realization seed 103 (10,000 rows)
│       ├── synthetic_orderbook_seed104.csv     # Realization seed 104 (10,000 rows)
│       ├── synthetic_orderbook_seed105.csv     # Realization seed 105 (10,000 rows)
│       └── synthetic_generation_manifest.json  # Generator seed metadata & SHA-256 digests
└── processed/                                  # Preprocessed streaming replay feature datasets
        ├── replay_academic_sample_AMZN_*.csv   # Preprocessed academic sample replay
        ├── replay_synthetic_seed101.csv        # Preprocessed synthetic seed 101 replay
        ├── replay_synthetic_seed102.csv        # Preprocessed synthetic seed 102 replay
        ├── replay_synthetic_seed103.csv        # Preprocessed synthetic seed 103 replay
        ├── replay_synthetic_seed104.csv        # Preprocessed synthetic seed 104 replay
        ├── replay_synthetic_seed105.csv        # Preprocessed synthetic seed 105 replay
        ├── injection_manifest.json             # Ground truth anomaly episode spans
        └── split_manifest.json                 # Frozen 60/20/20 chronological split bounds
```

---

## 2. End-to-End Pipeline Reproduction

To regenerate all raw data, preprocessed features, injection manifests, splits, and run the Reality Gate from scratch, execute the following commands in order:

### Step 1: Acquire / Construct Academic Benchmark Sample
```bash
python3 source/experiments/preprocessing/download_sample.py
```
*Outputs: `data/raw/academic_sample/` and `source/experiments/academic_sample_provenance.json`.*

### Step 2: Generate Multi-Seed Synthetic Market Realizations
```bash
python3 source/experiments/preprocessing/synthetic_generator.py \
  --seeds 101 102 103 104 105 \
  --num-rows 10000 \
  --output-dir data/synthetic
```
*Outputs: 5 independent CSV datasets in `data/synthetic/` and `synthetic_generation_manifest.json`.*

### Step 3: Run Schema-Validated Preprocessing & Feature Engineering
```bash
python3 source/experiments/preprocessing/preprocess.py \
  --input-dir data/synthetic \
  --academic-dir data/raw/academic_sample \
  --output-dir data/processed
```
*Outputs: Processed replay CSVs in `data/processed/` and `data/processed/injection_manifest.json`.*

### Step 4: Partition Temporal Train / Val / Test Splits
```bash
python3 source/experiments/preprocessing/create_splits.py \
  --input-dir data/processed \
  --manifest data/processed/split_manifest.json
```
*Outputs: Frozen 60/20/20 chronological boundaries in `data/processed/split_manifest.json`.*

### Step 5: Execute Automated Reality Gate Quality Barrier
```bash
python3 source/experiments/preprocessing/reality_gate.py \
  --data-dir data/processed \
  --report project/chunks/chunk04/reality_gate_report.json
```
*Evaluates all 6 domain checks and asserts `OVERALL VERDICT: PASS`.*

---

## 3. Schema & Feature Specifications

Every processed replay file adheres to the canonical 17-column CSV schema:

| Column | Type | Description |
|---|---|---|
| `seq` | `int` | Monotonically increasing sequence number ($0, 1, 2, \dots$) |
| `timestamp_ns` | `int` | Nanoseconds timestamp |
| `bid_px` | `float` | Best bid price ($> 0$) |
| `ask_px` | `float` | Best ask price ($\ge \text{bid\_px}$) |
| `bid_sz` | `int` | Top-of-book bid volume ($> 0$) |
| `ask_sz` | `int` | Top-of-book ask volume ($> 0$) |
| `mid_price` | `float` | Mid-price: $(P_{\text{ask}} + P_{\text{bid}}) / 2$ |
| `spread` | `float` | Absolute bid-ask spread: $P_{\text{ask}} - P_{\text{bid}}$ |
| `spread_bps` | `float` | Spread in basis points: $10,000 \times \text{spread} / \text{mid\_price}$ |
| `log_return` | `float` | Log-return: $\ln(\text{mid}_t / \text{mid}_{t-1})$ |
| `rolling_vol` | `float` | Exponential moving average volatility |
| `order_imbalance` | `float` | Order flow imbalance: $(V_{\text{bid}} - V_{\text{ask}}) / (V_{\text{bid}} + V_{\text{ask}})$ |
| `microprice` | `float` | Volume-weighted microprice |
| `volume` | `float` | Log-transformed total top volume: $\ln(1 + V_{\text{bid}} + V_{\text{ask}})$ |
| `is_anomaly` | `int` | Binary ground-truth anomaly indicator ($0$ = normal, $1$ = anomalous) |
| `anomaly_type` | `string` | Anomaly label category (`none`, `flash_crash_precursor`, `wash_trade_proxy`) |
| `is_burst_period` | `int` | Burst-load regime indicator ($0$ = baseline, $1$ = high-rate arrival) |

---

## 4. Citation and Attribution

When using the academic sample data, please cite the official benchmark source:
- **LOBSTER Academic Benchmark Data:** Humboldt University of Berlin / LOBSTER Data (`https://lobsterdata.com/info/DataSamples.php`).
- **KLStream Simulator:** Licensed under the GNU Affero General Public License v3 (AGPLv3).
