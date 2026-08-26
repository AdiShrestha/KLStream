# Release Notes — KLStream v0.2.0

**Release Date:** 2026-08-26  
**Release Type:** Certified Rehabilitated Scientific Baseline  
**License:** AGPLv3  

---

## Highlights

**KLStream v0.2.0** is the first fully certified release of the KLStream high-performance stream processing runtime for real-time anomaly detection in financial tick feeds. This release represents the complete rehabilitation of the KLStream codebase through a rigorous 9-phase Software Factory process spanning 72 contracts with deterministic mechanical verification.

### Core Runtime
- **Zero-broker C++17 stream processing engine** with lock-free SPSC and MPMC ring buffers using cache-aligned acquire/release memory semantics.
- **Closed-loop adaptive batch windowing** driven by Exponential Moving Average (EMA) queue occupancy feedback, dynamically modulating batch sizes $W \in [10, 500]$.
- **Explicit `Runtime` lifecycle state machine** (`INIT → RUNNING → DRAINING → STOPPED`) with deterministic shutdown sequencing.
- **Cache-optimized Isolation Forest scoring engine** with 64-byte `KLIF` binary model serialization and SHA-256 integrity verification.

### Scientific Evaluation
- **Pre-registered falsification protocol** with 3 formal claims, all **SUPPORTED**:
  - **Claim 1:** 98.02% tail latency (P99) reduction vs fixed-500 batching ($p = 0.03125$, Cliff's $\delta = 1.000$).
  - **Claim 2:** Zero AUC degradation across windowing regimens ($\Delta\text{AUC} = 0.000$).
  - **Claim 3:** 97.72% tail latency reduction over shuffled-occupancy control, proving causal feedback value ($p = 0.03125$).
- **54-run experimental test matrix** (6 datasets × 9 regimens) processing 99,000 events with exactly 0 drops.
- **Reality Gate** automated data validation enforcing 6 domain invariants with strict 60/20/20 temporal split isolation.

### Performance
- **SPSC Queue Throughput:** 22.14 Million ops/sec (target: >10 Mops/sec).
- **Isolation Forest Scoring Latency:** 270.99 ns mean (target: <500 ns).
- **E2E Streaming Throughput:** 1.69M events/sec with zero event loss and 81,850 backpressure activations.

### Publication
- Complete IEEE-format LaTeX manuscript (`paper/main.tex`) with 10 BibTeX references.
- 100% claims justification audit (10/10 quantitative assertions verified against data artifacts).
- ACM/IEEE Artifact Evaluation guide with badge criteria and 5-minute reproduction instructions.

---

## Known Limitations

1. **Single-host deployment only** — no distributed cluster support in this release.
2. **Isolation Forest model only** — the scoring engine is not pluggable for arbitrary ML models.
3. **Synthetic + academic benchmark evaluation** — no proprietary production market data included (by design, per zero-cost academic data policy DL-008).
4. **macOS and Linux only** — Windows support is untested.

---

## Verification

All release artifacts can be independently verified:

```bash
# One-command full reproduction (~25 seconds)
bash scripts/reproduce_all.sh

# Verify release integrity
shasum -a 256 -c dist/SHA256SUMS

# Run claims justification audit
python3 paper/audit_claims.py
```

---

## Distribution Packages

| Package | Contents | Size |
|---|---|---|
| `klstream-0.2.0.tar.gz` | Source code, build system, benchmarks, tests, scripts | 172 KB |
| `klstream-paper-0.2.0.tar.gz` | LaTeX manuscript, figures, tables, bibliography | 1.77 MB |

SHA-256 digests are available in `dist/SHA256SUMS`.

---

## Factory Certification

- **Software Factory Version:** 2.2.0
- **Total Contracts:** 72 (Chunks 01–09)
- **Gatekeeper Release Certification:** `CERTIFIED` (0 hard findings, 0 warnings)
- **Mechanical Recompute Declarations:** 18 verified
- **Pre-Registered Falsification Verdicts:** Claims 1–3 SUPPORTED
