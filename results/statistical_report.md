# Statistical Evaluation Report

## Overview
This report presents the non-parametric statistical hypothesis tests comparing **Adaptive-EMA** windowing against all baseline and control strategies across **6** experimental evaluation datasets.

- **Significance Level ($\alpha$):** 0.05
- **Statistical Tests:** Exact paired Wilcoxon signed-rank test (two-tailed)
- **Effect Sizes:** Cliff's delta ($\delta$)
- **Confidence Intervals:** 95% Percentile Bootstrap (10,000 resamples)
- **Multiplicity Correction:** Bonferroni-Holm Step-Down FWER Adjustment

---

## Metric: P99 End-to-End Latency (ns)

| Comparator | Adaptive Mean | Comparator Mean | Mean Diff | Cliff's $\delta$ (Magnitude) | Wilcoxon W | Raw p-value | Adj. p-value | Significant ($\alpha=0.05$) |
|---|---|---|---|---|---|---|---|---|
| Unadaptive Streaming (W=1) | 1483.60 | 583.56 | +900.04 | +1.000 (large) | 0.0 | 0.0312 | 0.2500 | No |
| Fixed Window (W=10) | 1483.60 | 1483.60 | +0.00 | +0.000 (negligible) | 0.0 | 1.0000 | 1.0000 | No |
| Fixed Window (W=50) | 1483.60 | 7443.76 | -5960.16 | -1.000 (large) | 0.0 | 0.0312 | 0.2500 | No |
| Fixed Window (W=100) | 1483.60 | 14937.69 | -13454.09 | -1.000 (large) | 0.0 | 0.0312 | 0.2500 | No |
| Fixed Window (W=200) | 1483.60 | 29933.73 | -28450.14 | -1.000 (large) | 0.0 | 0.0312 | 0.2500 | No |
| Fixed Window (W=500) | 1483.60 | 74932.09 | -73448.49 | -1.000 (large) | 0.0 | 0.0312 | 0.2500 | No |
| Shuffled-Occupancy Control | 1483.60 | 65054.02 | -63570.42 | -1.000 (large) | 0.0 | 0.0312 | 0.2500 | No |
| Periodic Schedule Control | 1483.60 | 40580.99 | -39097.39 | -1.000 (large) | 0.0 | 0.0312 | 0.2500 | No |

## Metric: Mean End-to-End Latency (ns)

| Comparator | Adaptive Mean | Comparator Mean | Mean Diff | Cliff's $\delta$ (Magnitude) | Wilcoxon W | Raw p-value | Adj. p-value | Significant ($\alpha=0.05$) |
|---|---|---|---|---|---|---|---|---|
| Unadaptive Streaming (W=1) | 1478.20 | 578.14 | +900.05 | +1.000 (large) | 0.0 | 0.0312 | 0.2500 | No |
| Fixed Window (W=10) | 1478.20 | 1478.20 | +0.00 | +0.000 (negligible) | 0.0 | 1.0000 | 1.0000 | No |
| Fixed Window (W=50) | 1478.20 | 7438.18 | -5959.99 | -1.000 (large) | 0.0 | 0.0312 | 0.2500 | No |
| Fixed Window (W=100) | 1478.20 | 14933.46 | -13455.26 | -1.000 (large) | 0.0 | 0.0312 | 0.2500 | No |
| Fixed Window (W=200) | 1478.20 | 29930.63 | -28452.44 | -1.000 (large) | 0.0 | 0.0312 | 0.2500 | No |
| Fixed Window (W=500) | 1478.20 | 74929.50 | -73451.30 | -1.000 (large) | 0.0 | 0.0312 | 0.2500 | No |
| Shuffled-Occupancy Control | 1478.20 | 46141.00 | -44662.80 | -1.000 (large) | 0.0 | 0.0312 | 0.2500 | No |
| Periodic Schedule Control | 1478.20 | 38151.74 | -36673.54 | -1.000 (large) | 0.0 | 0.0312 | 0.2500 | No |

## Metric: Pointwise AUC-ROC

| Comparator | Adaptive Mean | Comparator Mean | Mean Diff | Cliff's $\delta$ (Magnitude) | Wilcoxon W | Raw p-value | Adj. p-value | Significant ($\alpha=0.05$) |
|---|---|---|---|---|---|---|---|---|
| Unadaptive Streaming (W=1) | 0.53 | 0.53 | +0.00 | +0.000 (negligible) | 0.0 | 1.0000 | 1.0000 | No |
| Fixed Window (W=10) | 0.53 | 0.53 | +0.00 | +0.000 (negligible) | 0.0 | 1.0000 | 1.0000 | No |
| Fixed Window (W=50) | 0.53 | 0.53 | +0.00 | +0.000 (negligible) | 0.0 | 1.0000 | 1.0000 | No |
| Fixed Window (W=100) | 0.53 | 0.53 | +0.00 | +0.000 (negligible) | 0.0 | 1.0000 | 1.0000 | No |
| Fixed Window (W=200) | 0.53 | 0.53 | +0.00 | +0.000 (negligible) | 0.0 | 1.0000 | 1.0000 | No |
| Fixed Window (W=500) | 0.53 | 0.53 | +0.00 | +0.000 (negligible) | 0.0 | 1.0000 | 1.0000 | No |
| Shuffled-Occupancy Control | 0.53 | 0.53 | +0.00 | +0.000 (negligible) | 0.0 | 1.0000 | 1.0000 | No |
| Periodic Schedule Control | 0.53 | 0.53 | +0.00 | +0.000 (negligible) | 0.0 | 1.0000 | 1.0000 | No |

## Metric: Pointwise F1 Score

| Comparator | Adaptive Mean | Comparator Mean | Mean Diff | Cliff's $\delta$ (Magnitude) | Wilcoxon W | Raw p-value | Adj. p-value | Significant ($\alpha=0.05$) |
|---|---|---|---|---|---|---|---|---|
| Unadaptive Streaming (W=1) | 0.05 | 0.05 | +0.00 | +0.000 (negligible) | 0.0 | 1.0000 | 1.0000 | No |
| Fixed Window (W=10) | 0.05 | 0.05 | +0.00 | +0.000 (negligible) | 0.0 | 1.0000 | 1.0000 | No |
| Fixed Window (W=50) | 0.05 | 0.05 | +0.00 | +0.000 (negligible) | 0.0 | 1.0000 | 1.0000 | No |
| Fixed Window (W=100) | 0.05 | 0.05 | +0.00 | +0.000 (negligible) | 0.0 | 1.0000 | 1.0000 | No |
| Fixed Window (W=200) | 0.05 | 0.05 | +0.00 | +0.000 (negligible) | 0.0 | 1.0000 | 1.0000 | No |
| Fixed Window (W=500) | 0.05 | 0.05 | +0.00 | +0.000 (negligible) | 0.0 | 1.0000 | 1.0000 | No |
| Shuffled-Occupancy Control | 0.05 | 0.05 | +0.00 | +0.000 (negligible) | 0.0 | 1.0000 | 1.0000 | No |
| Periodic Schedule Control | 0.05 | 0.05 | +0.00 | +0.000 (negligible) | 0.0 | 1.0000 | 1.0000 | No |

