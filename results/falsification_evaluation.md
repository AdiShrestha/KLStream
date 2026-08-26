# Pre-Registered Falsification Evaluation Report

**Evaluation Date:** 2026-08-26  
**Governing Invariants:** `SVI-003`, `SVI-004`, `MAR-7`, `MAR-X6`  
**Pre-Registration SHA-256 Digest Verification:** **PASS (Verified intact)**  

---

## 1. Summary of Scientific Verdicts

| Claim | Objective & Comparison | Pre-Registered Falsification Bound | Empirical Finding | Verdict |
|---|---|---|---|---|
| **Claim 1** | Tail Latency vs Fixed-500 | Margin $< 15\%$ OR $p \ge 0.05$ OR $\delta < 0.330$ | **+98.02%** reduction ($p=0.0312, \delta=1.000$) | **SUPPORTED** |
| **Claim 2** | Detection Fidelity vs Unadaptive $W=1$ | AUC drop $> 0.03$ AND $p < 0.05$ | **0.0000** AUC drop (Invariance maintained) | **SUPPORTED** |
| **Claim 3** | Causal Feedback vs Shuffled Control | Margin $< 10\%$ OR $p \ge 0.05$ OR $\delta < 0.330$ | **+97.72%** reduction ($p=0.0312, \delta=1.000$) | **SUPPORTED** |

---

## 2. Detailed Claim Evaluations

### Claim 1: Tail Latency Reduction Under Bursty Order-Book Arrivals
- **Criterion:** Adaptive EMA must achieve $\ge 15\%$ lower $P_99$ latency than Fixed $W=500$ with $p < 0.05$ and Cliff's $\delta \ge 0.330$.
- **Empirical Measurement:**
  - Adaptive $P_99$ Latency: `1483.60 ns`
  - Fixed-500 $P_99$ Latency: `74932.09 ns`
  - Relative Reduction: `98.02%` (Exceeds $15.0\%$ target)
  - Paired Wilcoxon p-value: `0.0312` ($< 0.05$)
  - Non-parametric Effect Size (Cliff's $\delta$): `1.000` (Large effect $\ge 0.330$)
- **Formal Verdict:** **SUPPORTED**

---

### Claim 2: Pointwise Detection Fidelity Invariance Under Window Batching
- **Criterion:** Pointwise AUC-ROC under Adaptive EMA Windowing must not drop by $> 0.03$ compared to Unadaptive Serial Streaming ($W=1$).
- **Empirical Measurement:**
  - Adaptive AUC-ROC: `0.5304`
  - Unadaptive ($W=1$) AUC-ROC: `0.5304`
  - Observed Difference: `0.0000` (Zero degradation)
- **Formal Verdict:** **SUPPORTED**

---

### Claim 3: Causal Superiority of Closed-Loop Feedback Over Open-Loop Controls
- **Criterion:** Adaptive EMA must achieve $\ge 10\%$ lower $P_99$ latency than the Shuffled-Occupancy Control with $p < 0.05$ and Cliff's $\delta \ge 0.330$ (resolving MAR-X1).
- **Empirical Measurement:**
  - Adaptive $P_99$ Latency: `1483.60 ns`
  - Shuffled Control $P_99$ Latency: `65054.02 ns`
  - Relative Reduction: `97.72%` (Exceeds $10.0\%$ target)
  - Paired Wilcoxon p-value: `0.0312` ($< 0.05$)
  - Non-parametric Effect Size (Cliff's $\delta$): `1.000` (Large effect $\ge 0.330$)
- **Formal Verdict:** **SUPPORTED**

---

## 3. Anti-HARKing Conclusion
All pre-registered decision criteria were evaluated strictly and transparently. No thresholds or metric definitions were modified post-hoc.
