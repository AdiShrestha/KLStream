# Artifact Evaluation Appendix — KLStream

## 1. Artifact Meta-Information

- **Paper Title:** Queue-Occupancy Microbatching for Low-Latency Streaming Anomaly Detection on Multicore Processors
- **Paper Track:** ACM DEBS / EuroSys / USENIX ATC Systems Track
- **Artifacts Available:** Yes (Public Git repository)
- **Badges Claimed:**
  - **Artifacts Available:** All source code, authentic cohorts, manifests, and documentation are publicly hosted under open licenses.
  - **Artifacts Evaluated – Functional:** The codebase builds cleanly from scratch via CMake, passes 100% of native and integration test suites, and includes a standalone quickstart demo executing in $< 1\,\text{second}$.
  - **Results Reproduced:** A unified reproduction harness (`source/experiments/reproduce.py`) verifies all 7 published research artifact checksums and replicates core empirical claims.

---

## 2. Hardware & Software Requirements

### Hardware Requirements
- **Processor:** 64-bit multicore CPU (Tested on Apple Silicon M3 ARM64; compatible with x86_64 and aarch64 processors).
- **Cores:** Minimum 2 physical CPU cores (recommended 4+ cores).
- **Memory (RAM):** Minimum 4 GB RAM (peak experiment resident memory $< 1\,\text{GB}$).
- **Disk Storage:** At least 200 MB free disk space.

### Software Requirements
- **Operating System:** macOS (Sonoma 14.x+) or Linux (Ubuntu 22.04+ / Debian 12+).
- **C++ Compiler:** C++20 compliant compiler (`clang++` $\ge 14.0$ or `g++` $\ge 12.0$).
- **Build System:** CMake $\ge 3.20$ and Make or Ninja.
- **Python Runtime:** Python $\ge 3.10$ (standard library only; no external package dependencies required for core reproduction).

---

## 3. Quickstart & Verification (< 60 Seconds)

To verify functionality in less than one minute:

```bash
# 1. Configure and build C++ engine in Release mode
cmake -B build -S . -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel 2

# 2. Run automated test suite
ctest --test-dir build --output-on-failure

# 3. Execute quickstart streaming demo
python3 source/experiments/demo.py
```

Expected output:
- All registered test targets pass (100% pass rate).
- The demo completes in $< 1\,\text{second}$, reporting 100% event conservation ($N_{\text{offered}} == N_{\text{admitted}} == N_{\text{emitted}} == 5,233$) and comparing `adaptive_grow` versus `fixed_w1`.

---

## 4. Full Deterministic Reproduction (< 5 Minutes)

To execute the complete end-to-end artifact attestation pipeline:

```bash
python3 source/experiments/reproduce.py --output-report data/reproduction_report.json
```

This harness executes five sequential verification stages:
1. **Engine Compilation & Binary Hashing:** Rebuilds `engine_runner` and `engine_tests` and records their SHA-256 digests.
2. **Native Unit Tests:** Runs `build/engine_tests` directly, verifying ring buffer transitions, rate limiters, and model traversal.
3. **Artifact Integrity Attestation:** Verifies bitwise SHA-256 digests of all 7 published research data artifacts:
   - `data/cohort.csv`
   - `data/source_records.csv`
   - `data/provenance.json`
   - `data/budget_curves.json`
   - `data/pilot_telemetry.json`
   - `data/sensitivity_manifest.json`
   - `data/independent_verdict.json`
4. **Streaming Anomaly Demo:** Executes multi-policy evaluation asserting 100% event conservation ($E_3$).
5. **Secrecy & Credential Audit:** Scans repository for any leaked private keys or restricted tokens (0 violations).

The resulting attestation report is saved to `data/reproduction_report.json`.

---

## 5. Artifact Structure

```text
.
├── CMakeLists.txt                    # Root build and CTest configuration
├── README.md                         # Project overview and instructions
├── data/                             # Authentic research data and manifests
│   ├── cohort.csv                    # Authentic Binance BTC/USDT cohort (10,813 events)
│   ├── source_records.csv            # Raw archive SHA-256 digests
│   ├── provenance.json               # Data provenance metadata
│   ├── budget_curves.json            # Model hyperparameter evaluation grid
│   ├── pilot_telemetry.json          # Multi-policy exploratory pilot telemetry
│   ├── sensitivity_manifest.json     # Factorial sensitivity grid records
│   ├── independent_verdict.json      # Independent confirmatory verdict manifest
│   └── reproduction_report.json      # Cold reproduction attestation record
├── docs/                             # Documentation, cards, and reproduction guides
│   ├── ARTIFACT_EVALUATION.md        # This evaluation appendix
│   ├── DATA_CARD.md                  # Comprehensive dataset specification
│   ├── MODEL_CARD.md                 # Model topology and training details
│   ├── FEATURE_SPECIFICATION.md      # Causal feature derivation formulas
│   ├── figures/                      # Evidence-derived vector figures (SVG)
│   └── reproduction/                 # Step-by-step reproduction guides
│       ├── quickstart.md             # 60-second quickstart walkthrough
│       ├── full_run.md               # Complete reproduction guide
│       ├── environment.md            # Hardware and OS details
│       └── troubleshooting.md        # Common issues and remediations
├── paper/                            # Academic manuscript and artifacts
│   ├── manuscript.md                 # Complete evidence-derived manuscript
│   ├── references.bib                # BibTeX references
│   └── LICENSES.md                   # Explicit license terms (MIT, CC-BY-4.0)
└── source/                           # C++ engine and experimental runners
    ├── include/klstream/             # C++ header-only engine library
    ├── experiments/                  # Runners, parsers, and reproduction tools
    └── tests/                        # Comprehensive unit and integration tests
```
