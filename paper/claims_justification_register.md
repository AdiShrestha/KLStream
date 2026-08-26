# Claims Justification Register — KLStream

**Governing Invariant:** Invariant INV-015 (Claims Justification Audit)  
**Audit Status:** 100% VERIFIED (ALL CLAIMS MATCH DATA)  
**Total Claims Audited:** 10  

---

## Statement-by-Statement Evidence Traceability Ledger

| ID | Section Location | Stated Assertion Text | Stated Value | Ground-Truth Artifact & Key | Measured Value | Audit Status |
|---|---|---|---|---|---|---|
| **CLAIM-01** | Abstract, §5.5, Table 2 | Adaptive windowing reduces tail latency (P99) by 98.02% relative to fixed large batching (Fixed-500). | `98.02 %` | `results/falsification_verdicts.json`<br>`verdicts.claim_1.empirical_margin_pct` | `98.02 %` | **MATCH** |
| **CLAIM-02** | Abstract, §5.5, Table 2 | Claim 1 Wilcoxon signed-rank test p-value equals 0.03125. | `0.03125 p-value` | `results/falsification_verdicts.json`<br>`verdicts.claim_1.empirical_p_val` | `0.03125 p-value` | **MATCH** |
| **CLAIM-03** | Abstract, §5.5, Table 2 | Claim 1 effect size Cliff's delta equals 1.000. | `1.0 delta` | `results/falsification_verdicts.json`<br>`verdicts.claim_1.empirical_cliffs_delta` | `1.0 delta` | **MATCH** |
| **CLAIM-04** | Abstract, §5.5, Table 2 | Anomaly detection accuracy is strictly invariant across windowing regimens (delta AUC = 0.000). | `0.0 delta AUC` | `results/falsification_verdicts.json`<br>`verdicts.claim_2.empirical_auc_diff` | `0.0 delta AUC` | **MATCH** |
| **CLAIM-05** | Abstract, §5.5, Table 2, §6.1 | Dynamic closed-loop feedback provides a 97.72% tail latency reduction over shuffled-occupancy control. | `97.72 %` | `results/falsification_verdicts.json`<br>`verdicts.claim_3.empirical_margin_pct` | `97.72 %` | **MATCH** |
| **CLAIM-06** | Abstract, §5.2 | Lock-free SPSC queue sustains 22.14 Million operations per second throughput. | `22.14 Mops/sec` | `results/hardware_benchmark_report.json`<br>`performance_targets.spsc_measured_mops` | `22.1396 Mops/sec` | **MATCH** |
| **CLAIM-07** | Abstract, §5.2 | Point-wise Isolation Forest scoring completes in 270.99 nanoseconds. | `270.99 ns` | `results/hardware_benchmark_report.json`<br>`performance_targets.scoring_measured_mean_ns` | `270.993 ns` | **MATCH** |
| **CLAIM-08** | §5.1 | Total events processed in 54-run test matrix equals exactly 99,000 events. | `99000 events` | `results/execution_summary.json`<br>`total_events_processed` | `99000 events` | **MATCH** |
| **CLAIM-09** | §5.1, §5.2 | Total events dropped across all experimental matrix and replay benchmarks equals exactly 0. | `0 events` | `results/e2e_streaming_benchmark.json`<br>`events_dropped` | `0 events` | **MATCH** |
| **CLAIM-10** | §7.1 | Parameter sensitivity sweep evaluates 60 distinct parameter configurations. | `60 configs` | `results/sensitivity_analysis.json`<br>`num_grid_evaluations` | `60 configs` | **MATCH** |

---

## Audit Methodology and Certification

1. Every quantitative statement in `paper/paper.md` and `paper/main.tex` is bound to a formal entry in this register.
2. Ground-truth values are read programmatically from immutable, version-controlled JSON artifacts.
3. Zero hand-edited or ungrounded claims are permitted in the publication manuscripts.

- **Auditor Verdict:** PASSED (100% Traceability Confirmed)
