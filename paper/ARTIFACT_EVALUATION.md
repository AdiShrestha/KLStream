# Artifact Evaluation Guide — KLStream

**Paper Title:** *KLStream: Backpressure-Aware Dynamic Batch Adaptation for Low-Latency Stream Anomaly Detection in Financial Tick Feeds*  
**Artifact Badges Applied For:**
1. **Artifacts Available:** All source code, datasets, evaluation scripts, and models are available under open licenses with public Git repository and Zenodo-style archive releases.
2. **Artifacts Evaluated — Functional:** The artifact is complete, documented, easily exercisable, and includes automated verification machinery.
3. **Results Replicated:** All numbers, tables, falsification verdicts, and figures in the paper can be reproduced from raw inputs via a single automated script.

---

## 1. Artifact Overview

KLStream is an ultra-low-latency C++17 stream processing runtime for real-time anomaly detection over non-stationary financial tick feeds. It dynamically modulates batch window sizes $W \in [10, 500]$ based on closed-loop lock-free queue occupancy feedback.

This artifact evaluation package contains:
- The complete C++17 source code of KLStream (lock-free queues, lifecycle state machine, Isolation Forest scoring engine).
- The Python evaluation and statistical pipeline (Reality Gate data validator, pre-registered hypothesis test runner, falsification evaluator).
- All 6 evaluation streams (5 synthetic seeds + academic LOBSTER market sample benchmark).
- The one-step master reproduction script `scripts/reproduce_all.sh` executing all 9 experimental phases in $\approx 25$ seconds.
- Cryptographic provenance receipts (`source/experiments/reproducibility_receipt.md`) and the Claims Justification Register (`paper/claims_justification_register.md`).

---

## 2. Hardware and Software Prerequisites

### 2.1 Hardware Requirements
- **Architecture:** x86_64 or Apple Silicon (ARM64).
- **CPU:** 4+ physical cores recommended (benchmarks tested on 8-core Apple M3 and Linux x86_64).
- **Memory:** Minimum 8 GB RAM (16 GB recommended).
- **Disk Space:** 2 GB of free disk space.

### 2.2 Software Requirements
- **Operating System:** Linux (Ubuntu 20.04+) or macOS (12.0+).
- **C++ Toolchain:** C++17 compliant compiler (`g++-12+` or `clang-15+`).
- **Build System:** `cmake` (version 3.20+) and `ninja` (optional).
- **Python Environment:** Python 3.10, 3.11, or 3.12 with `numpy`, `scipy`, `scikit-learn`, `pandas`, `pytest`, `pyyaml`.

---

## 3. Environment Setup

### Option A: Local Native Setup (Recommended)
```bash
# Clone the repository
git clone https://github.com/adi/klstream.git
cd klstream

# Install Python dependencies
pip install -r requirements.txt || pip install numpy scipy scikit-learn pandas pytest pyyaml

# Verify build system
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel
ctest --test-dir build --output-on-failure
```

### Option B: Docker Container Setup
```bash
# Build multi-stage container
docker build -t klstream:reproduce .

# Run interactive reproduction container
docker run --rm -it klstream:reproduce /bin/bash
```

---

## 4. Step-by-Step Reproduction Guide (Under 5 Minutes)

The entire scientific and experimental pipeline can be reproduced using a single master script:

```bash
# Execute master reproduction workflow
bash scripts/reproduce_all.sh
```

### Execution Phase Breakdown
1. **Phase 1: Reality Gate Data Verification:** Audits temporal monotonicity, spread positivity, and split isolation across 6 datasets.
2. **Phase 2: Model Training:** Fits Isolation Forest estimators on 60% training splits.
3. **Phase 3: Validation Split Calibration:** Calibrates decision thresholds on 20% validation splits ($\text{FPR} \le 0.05$).
4. **Phase 4: Full Matrix Evaluation:** Executes 54 streaming runs (6 datasets $\times$ 9 regimens) processing 99,000 events with 0 drops.
5. **Phase 5: Telemetry Consolidation:** Ingests raw run logs into `results/consolidated_telemetry.csv`.
6. **Phase 6: Non-Parametric Hypothesis Tests:** Computes paired Wilcoxon signed-rank tests and Cliff's delta effect sizes.
7. **Phase 7: Pre-Registered Falsification:** Evaluates Claims 1..3 against frozen pre-registered bounds.
8. **Phase 8: Parameter Sensitivity & Dynamic Stability:** Sweeps 60 parameter configurations and tests 10x surge shock.
9. **Phase 9: Figure Generation & Archive Packaging:** Generates Figures 1..4 (PNG/PDF) and bundles the reproducible archive.

---

## 5. Key Claims & Verification Checkpoints

Reviewers can verify the core claims of the paper against the generated outputs:

| Paper Claim | Target Checkpoint | Command to Verify | Expected Output / Bound |
|---|---|---|---|
| **Claim 1 (P99 Latency Reduction)** | Table 2, §5.5 | `python3 -c "import json; v=json.load(open('results/falsification_verdicts.json')); print(v['verdicts']['claim_1'])"` | `verdict: SUPPORTED`, empirical margin: **98.02%** ($p = 0.03125$) |
| **Claim 2 (Accuracy Invariance)** | Table 2, §5.5 | `python3 -c "import json; v=json.load(open('results/falsification_verdicts.json')); print(v['verdicts']['claim_2'])"` | `verdict: SUPPORTED`, delta AUC: **0.0000** ($p = 1.00000$) |
| **Claim 3 (Causal Value of Feedback)** | Table 2, §5.5 | `python3 -c "import json; v=json.load(open('results/falsification_verdicts.json')); print(v['verdicts']['claim_3'])"` | `verdict: SUPPORTED`, empirical margin: **97.72%** ($p = 0.03125$) |
| **Micro-Benchmark: SPSC Queue** | Table 1, §5.2 | `./build-bench/source/benchmarks/benchmark_queues` | SPSC Throughput $> 10.0$ Mops/sec (Measured: **22.14 Mops/sec**) |
| **Micro-Benchmark: Scoring Latency** | Table 1, §5.2 | `./build-bench/source/benchmarks/benchmark_model` | Mean Latency $< 500$ ns (Measured: **270.99 ns**) |
| **Zero Event Drops** | INV-007, §5.1 | `python3 -c "import json; s=json.load(open('results/e2e_streaming_benchmark.json')); print('Dropped:', s['events_dropped'])"` | `Dropped: 0` |
| **Claims Justification Audit** | INV-015 | `python3 paper/audit_claims.py` | `Match Rate: 10/10 (100%)` |

---

## 6. Generated Publication Figures

All figures cited in the manuscript are produced in `results/figures/`:
- **`fig1_tradeoff_pareto.png`:** Throughput-latency Pareto frontier showing `adaptive_ema` dominance.
- **`fig2_latency_decomposition.png`:** Stacked bar chart decomposing latency into $T_q$, $T_{\text{freshness}}$, and $T_{\text{exec}}$.
- **`fig3_step_load_stability.png`:** Transient response curve demonstrating 10-step rise time and 0.00 chattering under 10x surge shock.
- **`fig4_pr_roc_curves.png`:** ROC and Precision-Recall curves confirming exact point-wise metric invariance.

---

## 7. Contact and Support

For questions, issues, or assistance with artifact evaluation, please open a GitHub Issue or contact:
- **Lead Author:** Adarsh Shrestha (`adarsh.shrestha@ku.edu.np`)
- **Department of Computer Science and Engineering**, Kathmandu University
