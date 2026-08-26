# Pre-Registered Falsification Criteria & Scientific Decision Boundaries — KLStream

**Version:** 1.0.0  
**Registration Date:** 2026-08-26  
**Governing Invariants:** `SVI-003` (Pre-Registered Falsification Criteria), `SVI-004` (Cryptographic Freeze)  
**External Review Traces:** `MAR-7`, `MAR-X6` (Pre-Registration Protocol)  
**Registration Stage:** Pre-Experimental Freeze (Formally frozen before Chunk 06 execution)

---

## 1. Protocol Pre-Registration Statement

In accordance with Open Science practices and to prevent Hypothesizing After Results are Known (HARKing), all experimental decision boundaries, statistical tests, comparison pairs, and quantitative falsification criteria are pre-registered and cryptographically frozen in this document prior to the execution of experimental training and evaluation runs in Chunk 06.

---

## 2. Pre-Registered Hypotheses & Falsification Criteria

### Claim 1: Tail Latency Reduction Under Bursty Order-Book Arrivals
- **Hypothesis $H_1$:** Under non-stationary bursty order-book arrival regimes, closed-loop Adaptive EMA Windowing achieves lower $P_{99}$ event-to-decision latency than the high-throughput static baseline ($W=500$) and serial unadaptive streaming ($W=1$).
- **Primary Metric:** $P_{99}$ End-to-End Latency ($T_{\text{e2e}}$) across 5 independent realization seeds (`seed101`..`seed105`).
- **Baseline Conditions:** Fixed-Window $W=500$ and Unadaptive Streaming $W=1$.
- **Formal Falsification Threshold:** Claim 1 is **FALSIFIED** if ANY of the following hold:
  1. Mean $P_{99}$ latency of Adaptive EMA is NOT at least $15\%$ lower than Fixed $W=500$ ($T_{P_{99},\text{Adaptive}} > 0.85 \times T_{P_{99},\text{Fixed500}}$).
  2. Paired Wilcoxon signed-rank test yields adjusted $p \ge 0.05$.
  3. Non-parametric effect size Cliff's $\delta < 0.330$ (fails to achieve at least medium effect).

---

### Claim 2: Pointwise Detection Fidelity Invariance Under Window Batching
- **Hypothesis $H_2$:** Dynamic window batching preserves pointwise Isolation Forest scoring fidelity without degrading anomaly detection performance relative to pure serial evaluation ($W=1$).
- **Primary Metric:** Pointwise Area Under the ROC Curve (AUC-ROC) and PR-AUC.
- **Baseline Condition:** Unadaptive Serial Streaming ($W=1$).
- **Formal Falsification Threshold:** Claim 2 is **FALSIFIED** if:
  1. Pointwise AUC-ROC under Adaptive EMA Windowing drops by more than $0.03$ compared to Unadaptive Streaming $W=1$ ($\text{AUC}_{\text{Adaptive}} < \text{AUC}_{W=1} - 0.03$) with statistical significance ($p < 0.05$).

---

### Claim 3: Causal Superiority of Closed-Loop Feedback Over Open-Loop Controls
- **Hypothesis $H_3$:** Queue-occupancy feedback provides intelligent load adaptation whose benefits cannot be replicated by open-loop periodic oscillation or decoupled random occupancy signals (resolving MAR-X1).
- **Primary Metric:** $P_{99}$ End-to-End Latency under dynamic load transitions.
- **Baseline Conditions:** Shuffled-Occupancy Control and Periodic Schedule Control.
- **Formal Falsification Threshold:** Claim 3 is **FALSIFIED** if ANY of the following hold:
  1. Adaptive EMA Windowing does NOT achieve at least $10\%$ lower $P_{99}$ latency than the Shuffled-Occupancy Control ($T_{P_{99},\text{Adaptive}} > 0.90 \times T_{P_{99},\text{Shuffled}}$).
  2. Paired Wilcoxon signed-rank test yields adjusted $p \ge 0.05$.
  3. Non-parametric effect size Cliff's $\delta < 0.330$.

---

## 3. Summary of Decision Matrix

| Claim | Target Comparison | Required Margin | Stat Significance | Effect Size | Falsification Condition |
|---|---|---|---|---|---|
| **Claim 1** | Adaptive vs. Fixed $W=500$ | $\ge 15\%$ $P_{99}$ reduction | $p_{\text{adj}} < 0.05$ | Cliff's $\delta \ge 0.330$ | Margin $< 15\%$ OR $p \ge 0.05$ OR $\delta < 0.330$ |
| **Claim 2** | Adaptive vs. Unadaptive $W=1$ | $\Delta \text{AUC} \le 0.03$ | N/A (Equivalence) | Negligible | Degradation $> 0.03$ AND $p < 0.05$ |
| **Claim 3** | Adaptive vs. Shuffled Control | $\ge 10\%$ $P_{99}$ reduction | $p_{\text{adj}} < 0.05$ | Cliff's $\delta \ge 0.330$ | Margin $< 10\%$ OR $p \ge 0.05$ OR $\delta < 0.330$ |
