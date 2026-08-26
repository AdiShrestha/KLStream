# Statistical Testing & Hypothesis Evaluation Protocol — KLStream

**Version:** 1.0.0  
**Date:** 2026-08-26  
**Governing Invariants:** `INV-006` (Statistical Testing Protocol), `INV-007` (Multiple Comparisons)  
**External Review Traces:** `MAR-3` (Multi-Seed Replication & Statistical Rigor)

---

## 1. Statistical Philosophy & Paradigm

Because streaming latency distributions and financial return volatility distributions exhibit heavy tails and non-Gaussian characteristics, KLStream enforces a **strictly non-parametric statistical evaluation framework**. No assumptions of asymptotic normality or homoscedasticity are permitted.

All experimental comparisons are conducted across the 5 independent realization seeds (`seed101` through `seed105`) generated in Chunk 04, with paired evaluation across identical arrival regimes.

---

## 2. Hypothesis Testing: Paired Wilcoxon Signed-Rank Test

For paired observations $(x_1, y_1), \dots, (x_n, y_n)$ across $n=5$ independent seeds:
1. Compute paired differences: $d_i = x_i - y_i$.
2. Discard zero differences ($d_i = 0$) and let $N_r$ denote the remaining sample count.
3. Rank the absolute differences $|d_i|$ from smallest (rank 1) to largest (rank $N_r$), assigning mid-ranks for ties.
4. Compute rank sums:
   $$W^+ = \sum_{d_i > 0} \text{Rank}(|d_i|), \quad W^- = \sum_{d_i < 0} \text{Rank}(|d_i|)$$
5. Test statistic $T = \min(W^+, W^-)$ with exact two-tailed permutation distribution for small $N_r \le 20$.
6. Significance threshold: $\alpha = 0.05$.

---

## 3. Effect Size: Cliff's Delta ($\delta$)

To quantify the magnitude of difference independently of sample size, we compute Cliff's delta:
$$\delta = \frac{\# (x_i > y_j) - \# (x_i < y_j)}{n_x \cdot n_y}$$
where $\delta \in [-1.0, +1.0]$.

**Standard Romano et al. Effect Size Thresholds:**
- $|\delta| < 0.147$: **Negligible**
- $0.147 \le |\delta| < 0.330$: **Small**
- $0.330 \le |\delta| < 0.474$: **Medium**
- $|\delta| \ge 0.474$: **Large**

A systems superiority claim requires $|\delta| \ge 0.474$ (large effect) in addition to statistical significance.

---

## 4. Confidence Intervals: 95% Non-Parametric Bootstrap

For any performance metric $\theta$, 95% confidence intervals are estimated via the non-parametric percentile bootstrap:
1. Resample $N_{\text{boot}} = 10,000$ bootstrap replicates with replacement: $\mathbf{x}^{*(b)}$.
2. Compute the metric for each replicate: $\hat{\theta}^{*(b)}$.
3. Estimate lower and upper bounds as the 2.5th and 97.5th percentiles:
   $$\text{CI}_{95\%} = \left[ \hat{\theta}^*_{(0.025)}, \; \hat{\theta}^*_{(0.975)} \right]$$
4. Random seed fixed to `42` for cryptographic reproducibility.

---

## 5. Multiple Comparison Control: Bonferroni-Holm

When testing $K$ related hypotheses simultaneously, the family-wise error rate (FWER) is controlled via the step-down **Bonferroni-Holm adjustment**:
1. Sort raw $p$-values in ascending order: $p_{(1)} \le p_{(2)} \le \dots \le p_{(K)}$.
2. Compute adjusted critical values $\alpha_k = \frac{\alpha}{K - k + 1}$ for $k=1, \dots, K$.
3. Adjusted $p$-values:
   $$p_{\text{adj},(k)} = \min\left(1.0, \; \max_{j \le k} (K - j + 1) \cdot p_{(j)}\right)$$
4. A comparison is rejected iff $p_{\text{adj},(k)} < \alpha = 0.05$.

---

## 6. Pre-Registered Decision Rule

| Outcome | Criteria | Interpretation |
|---|---|---|
| **SUPPORTED** | $p_{\text{adj}} < 0.05$ AND $|\delta| \ge 0.474$ in predicted direction | Null rejected with substantial practical effect |
| **INCONCLUSIVE** | $p_{\text{adj}} < 0.05$ BUT $|\delta| < 0.474$ | Statistically detectable but practically negligible effect |
| **FALSIFIED** | $p_{\text{adj}} \ge 0.05$ OR $\delta$ in opposite direction | Null not rejected; claim refuted |
