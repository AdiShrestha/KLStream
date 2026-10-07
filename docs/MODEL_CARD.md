# Model Card — Dynamic Isolation Forest (`.iforest`)

## 1. Model Details

- **Model Architecture:** `DynamicIsolationForest` (Streaming C++ implementation of Isolation Forest [liu2008isolation])
- **Model Checkpoint Path:** `data/model_checkpoint.iforest`
- **Model Checkpoint Digest (SHA-256):** `4321190fc2b197eb997931c5fe3a56f055b58c67c5d6ac789b637de00cab3b12`
- **Binary File Format:** KLStream Portable Binary Format v1 (`.iforest`)
  - Fixed-width 32-byte header: Magic `0x49464F52` (`IFOR`), version 1, tree count, subsample size, dimension count, seed, and IEEE 802.3 CRC32 checksum.
  - Compact 37-byte node representation: split feature, split value, left child, right child, node size, and leaf indicator.
  - Total on-disk serialized size: 569,300 bytes.
- **License:** Creative Commons Attribution 4.0 International (CC-BY-4.0)

---

## 2. Training Data & Hyperparameter Selection

The model checkpoint was trained strictly on the training partition of the authentic Binance BTC/USDT observational cohort:
- **Training Source Day:** `rec_20170817` (3,427 trades, 40 groups, 72 anomalies).
- **Validation Source Day:** `rec_20170818` (5,233 trades, 48 groups, 111 anomalies).
- **Test Holdout:** `rec_20170819` was **strictly unaccessed** during training and hyperparameter search.

A 16-configuration hyperparameter search grid evaluated tree count $T \in \{25, 50, 100, 200\}$ and subsample size $\psi \in \{64, 128, 256, 512\}$ (documented in `data/budget_curves.json`). The selected configuration achieves optimal discrimination:
- **Trees ($T$):** 200
- **Subsample Size ($\psi$):** 128
- **PRNG Seed:** 42
- **Validation AUROC:** 0.99771 ($\approx 0.9977$)
- **Validation Delta Mean ($\Delta \mu$):** 0.19903
- **Training AUROC:** 0.99496

---

## 3. Computational Complexity & Latency Profile

- **Inference Time Complexity:** $\mathcal{O}(T \cdot \log_2 \psi) = \mathcal{O}(200 \cdot 7) \approx 1,400$ tree node comparisons per event.
- **Single-Event Service Time ($W=1$):** $\approx 20-35\,\mu\text{s}$ on Apple Silicon ARM64 performance cores.
- **Microbatch Amortization ($W \in [1, 32]$):** Batch evaluation amortizes instruction dispatch and feature vector cache loads, reducing per-event service overhead during bursts.
- **Memory Footprint:** Resident memory footprint for the serialized tree structure is $< 1.5\,\text{MB}$, easily residing inside L2/L3 cache hierarchies.

---

## 4. Inference Fidelity & Determinism Guarantees

- **Scoring Invariance ($\Delta s = 0.0$):** Model inference is purely read-only and deterministic. Evaluating events in batches of size $W \in [1, 32]$ yields bitwise identical isolation depth scores to pointwise evaluation:
  $$\max_{i} |\text{score}_{\text{adaptive}}(i) - \text{score}_{\text{pointwise}}(i)| = 0.0$$
- **Downstream Metric Parity:**
  - Test Average Precision: $\text{AP} = 0.916415$ ($\Delta \text{AP} = 0.000000$)
  - Test AUROC: $\text{AUROC} = 0.997328$ ($\Delta \text{AUROC} = 0.000000$)
