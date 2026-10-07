# Complete Reproduction Guide

This guide details the end-to-end execution of the KLStream reproduction harness, verifying all published data artifact checksums, native binaries, and empirical claims.

---

## 1. Automated Full Reproduction Pipeline

Run the automated reproduction pipeline:

```bash
python3 source/experiments/reproduce.py --output-report data/reproduction_report.json
```

The pipeline automatically carries out the following verification stages:

### Stage 1: Native Engine Compilation & Binary Hashing
- Invokes CMake to configure and build the C++ engine in Release mode.
- Computes and records the SHA-256 digests of `build/engine_runner` and `build/engine_tests`.

### Stage 2: Native Unit Testing
- Executes `build/engine_tests` directly.
- Validates lock-free ring buffer state transitions, token bucket pacing, and model tree traversals.

### Stage 3: Public Research Artifact Integrity Attestation
- Checks the file sizes and SHA-256 digests of all 7 published research data artifacts:
  - `data/cohort.csv` (`5e2c5ed3ccc47c9da95c6918c9a65d252f22b28ae9a3d0f6ebe1f9bb7c7d9496`)
  - `data/source_records.csv` (`3754da4d952e9eeee2c48bfeda9edc138fe99b188c1364d36d9fbdcfaf96d6b7`)
  - `data/provenance.json` (`2f0e96056eb2fef808ece08ee86526987d893548002c1962a722044110496dd7`)
  - `data/budget_curves.json` (`d8f7b6c94eb54b35cf5a2f2eacc8214d626ad37fa15819163a4cfe6f9c0522c8`)
  - `data/pilot_telemetry.json` (`02e995534fd7a44f0ac7f6d7d38f73cd4cab958a673fd7937e5bb56550bda73a`)
  - `data/sensitivity_manifest.json` (`b88ac4188537a78cf4481fa18025ac328e233c8f1c47cec7f24c20fc869722b5`)
  - `data/independent_verdict.json` (`5d557562a71dd1ee550208105c5330f9cbda639c10d3b3e446cd2ddebf2bc1b8`)

### Stage 4: Quickstart Streaming Demo
- Runs multi-policy execution (`adaptive_grow` vs `fixed_w1`) over 5,233 validation events.
- Asserts 100% event conservation ($N_{\text{offered}} == N_{\text{admitted}} == N_{\text{emitted}}$, zero drops).

### Stage 5: Secrecy & Credential Audit
- Scans all tracked files for private key headers, tokens, or private infrastructure artifacts.
- Asserts 0 violations.

---

## 2. Running Individual Experiments

### Running the Python Runner Directly
```bash
python3 source/experiments/runner.py \
    --cohort data/cohort.csv \
    --eval-splits validation \
    --policy adaptive_grow \
    --seed 42 \
    --run-dir runs/test_adaptive
```
Inspect generated outputs in `runs/test_adaptive/`:
- `trace.csv`: Full per-event 7-timestamp records.
- `predictions.csv`: Model anomaly scores per event ID.
- `result.json`: Exact nearest-rank quantiles and conservation summary.

### Running the Factorial Sensitivity Grid
```bash
python3 source/experiments/run_sensitivity.py \
    --cohort data/cohort.csv \
    --model data/model_checkpoint.iforest \
    --output runs/sensitivity_out.json
```

### Running the Independent Verdict Analysis
```bash
python3 source/experiments/analysis/independent_verdict.py \
    --cohort data/cohort.csv \
    --output runs/verdict_out.json
```
