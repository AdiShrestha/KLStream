#!/usr/bin/env python3
"""
compute_statistics.py — Executes pre-registered statistical evaluation protocol on experimental runs.

Governing Invariants:
- INV-006: Exact Wilcoxon signed-rank test, Cliff's delta, and 95% bootstrap CIs
- MAR-3: Family-wise error rate control via Bonferroni-Holm adjustment
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List
import numpy as np
import pandas as pd

# Add protocol directory to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "source" / "experiments" / "protocol"))

from statistical_methods import (
    cliffs_delta,
    interpret_cliffs_delta,
    wilcoxon_paired_test,
    bootstrap_ci_95,
    bonferroni_holm_adjust
)

COMPARATORS = [
    ("unadaptive_w1", "Unadaptive Streaming (W=1)"),
    ("fixed_w10", "Fixed Window (W=10)"),
    ("fixed_w50", "Fixed Window (W=50)"),
    ("fixed_w100", "Fixed Window (W=100)"),
    ("fixed_w200", "Fixed Window (W=200)"),
    ("fixed_w500", "Fixed Window (W=500)"),
    ("shuffled_control", "Shuffled-Occupancy Control"),
    ("periodic_control", "Periodic Schedule Control")
]

METRICS = [
    ("t_e2e_p99_ns", "P99 End-to-End Latency (ns)", "lower_is_better"),
    ("t_e2e_mean_ns", "Mean End-to-End Latency (ns)", "lower_is_better"),
    ("auc_roc", "Pointwise AUC-ROC", "higher_is_better"),
    ("f1", "Pointwise F1 Score", "higher_is_better")
]

def main():
    parser = argparse.ArgumentParser(description="Compute non-parametric statistics on experimental telemetry")
    parser.add_argument("--telemetry", default="results/consolidated_telemetry.csv", help="Path to consolidated CSV")
    parser.add_argument("--output-json", default="results/statistical_summary.json", help="Path to output summary JSON")
    parser.add_argument("--output-md", default="results/statistical_report.md", help="Path to output Markdown report")
    args = parser.parse_args()
    
    df = pd.read_csv(args.telemetry)
    
    # Extract adaptive baseline
    adaptive_df = df[df["controller_name"] == "adaptive_ema"].sort_values("dataset_alias")
    datasets = list(adaptive_df["dataset_alias"].unique())
    
    results = {
        "manifest_version": "1.0.0",
        "governing_invariants": ["INV-006", "MAR-3"],
        "num_datasets": len(datasets),
        "datasets": datasets,
        "num_metric_comparisons": len(METRICS),
        "comparisons": {}
    }

    
    md_lines = [
        "# Statistical Evaluation Report",
        "",
        "## Overview",
        f"This report presents the non-parametric statistical hypothesis tests comparing **Adaptive-EMA** windowing against all baseline and control strategies across **{len(datasets)}** experimental evaluation datasets.",
        "",
        r"- **Significance Level ($\alpha$):** 0.05",
        "- **Statistical Tests:** Exact paired Wilcoxon signed-rank test (two-tailed)",
        r"- **Effect Sizes:** Cliff's delta ($\delta$)",
        "- **Confidence Intervals:** 95% Percentile Bootstrap (10,000 resamples)",
        "- **Multiplicity Correction:** Bonferroni-Holm Step-Down FWER Adjustment",
        "",
        "---",
        ""
    ]
    
    for metric_key, metric_label, direction in METRICS:
        results["comparisons"][metric_key] = {
            "metric_label": metric_label,
            "direction": direction,
            "tests": []
        }
        
        md_lines.extend([
            f"## Metric: {metric_label}",
            "",
            r"| Comparator | Adaptive Mean | Comparator Mean | Mean Diff | Cliff's $\delta$ (Magnitude) | Wilcoxon W | Raw p-value | Adj. p-value | Significant ($\alpha=0.05$) |",
            "|---|---|---|---|---|---|---|---|---|"
        ])
        
        raw_pvals = []
        test_records = []
        
        adaptive_vals = adaptive_df[metric_key].to_numpy()
        
        for comp_name, comp_label in COMPARATORS:
            comp_df = df[df["controller_name"] == comp_name].sort_values("dataset_alias")
            comp_vals = comp_df[metric_key].to_numpy()
            
            # Differences: Adaptive - Comparator
            diffs = adaptive_vals - comp_vals
            
            w_res = wilcoxon_paired_test(adaptive_vals, comp_vals)
            delta = cliffs_delta(adaptive_vals, comp_vals)
            magnitude = interpret_cliffs_delta(delta)
            ci_low, ci_high = bootstrap_ci_95(diffs, n_boot=10000, seed=42)
            
            rec = {
                "comparator_name": comp_name,
                "comparator_label": comp_label,
                "adaptive_mean": float(np.mean(adaptive_vals)),
                "comparator_mean": float(np.mean(comp_vals)),
                "mean_difference": float(np.mean(diffs)),
                "ci_95_low": float(ci_low),
                "ci_95_high": float(ci_high),
                "cliffs_delta": float(delta),
                "effect_magnitude": magnitude,
                "wilcoxon_stat": float(w_res["statistic"]),
                "raw_p_value": float(w_res["p_value"])
            }
            test_records.append(rec)
            raw_pvals.append(w_res["p_value"])
            
        adj_pvals = bonferroni_holm_adjust(raw_pvals)

        
        for rec, adj_p in zip(test_records, adj_pvals):
            rec["adj_p_value"] = float(adj_p)
            rec["is_significant"] = bool(adj_p < 0.05)
            results["comparisons"][metric_key]["tests"].append(rec)
            
            sig_str = "**YES**" if rec["is_significant"] else "No"
            md_lines.append(
                f"| {rec['comparator_label']} | {rec['adaptive_mean']:.2f} | {rec['comparator_mean']:.2f} | {rec['mean_difference']:+.2f} | {rec['cliffs_delta']:+.3f} ({rec['effect_magnitude']}) | {rec['wilcoxon_stat']:.1f} | {rec['raw_p_value']:.4f} | {rec['adj_p_value']:.4f} | {sig_str} |"
            )
            
        md_lines.append("")
        
    out_json = Path(args.output_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    with open(out_json, "w") as f:
        json.dump(results, f, indent=2)
        
    out_md = Path(args.output_md)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    with open(out_md, "w") as f:
        f.write("\n".join(md_lines) + "\n")
        
    print(f"Statistical summary written to {out_json}")
    print(f"Statistical report written to {out_md}")

if __name__ == "__main__":
    main()
