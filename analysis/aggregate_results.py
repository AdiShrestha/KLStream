#!/usr/bin/env python3
"""
Aggregate 30-run results for all 3 architectures.

Metrics reported:
  - Raw tick-level F1  (section 22 of KLStream_Research.md)
  - PA%20 F1           (Kim et al. 2022 — segment-adjusted)
  - LBA@10ms / @25ms / @50ms  (Latency-Bounded Accuracy)
    NOTE: LBA@1ms is NOT reported — best-case P95 latency (~17ms) is already
    17× above the 1ms bound, so it has zero discriminating power.
  - P50 / P95 / P99 latency (ms)

SAFETY: verifies exactly 30 files exist per architecture before aggregating.
"""
import os
import sys
import glob
import pandas as pd
import numpy as np
from scipy import stats  # for Wilcoxon paired test

import sys
sys.path.insert(0, os.path.dirname(__file__))
from compute_metrics import tick_level_f1, pa_k_f1, lba_f1

REQUIRED_RUNS = 30
OUT_DIR = "results/raw/exp2_3"
GT_PATH = "data/replay/replay_AAPL_20120621.csv"
ARCHITECTURES = ["fixed", "datadriven", "adaptive"]


def load_segments(gt):
    segments = []
    in_seg, start = False, 0
    for i, label in enumerate(gt["label"]):
        if label != 0 and not in_seg:
            in_seg, start = True, i
        elif label == 0 and in_seg:
            in_seg = False
            segments.append((start, i - 1))
    if in_seg:
        segments.append((start, len(gt) - 1))
    return segments


def verify_files():
    """Abort if any architecture is missing its 30 files."""
    ok = True
    for arch in ARCHITECTURES:
        files = glob.glob(os.path.join(OUT_DIR, f"run_{arch}_*.csv"))
        if len(files) != REQUIRED_RUNS:
            print(f"❌ {arch}: found {len(files)} files, expected {REQUIRED_RUNS}")
            ok = False
    if not ok:
        print("\nFile count mismatch. Run run_experiments.py first.")
        sys.exit(1)
    print("✅ File counts verified (30 per architecture).\n")


def main():
    verify_files()

    print("Loading ground truth...")
    gt = pd.read_csv(GT_PATH)
    segments = load_segments(gt)
    print(f"  {len(gt)} ticks, {len(segments)} anomaly segments.\n")

    summary = {}

    for arch in ARCHITECTURES:
        files = sorted(glob.glob(os.path.join(OUT_DIR, f"run_{arch}_*.csv")))

        f1s, pa20s, lba10s, lba25s, lba50s, lats_all = [], [], [], [], [], []

        for f in files:
            df = pd.read_csv(f)
            threshold = df["max_score"].quantile(0.95)

            _, _, f1   = tick_level_f1(df, gt, threshold)
            _, _, pa20 = pa_k_f1(df, gt, threshold, 0.20, segments)
            _, _, l10  = lba_f1(df, gt, threshold, 10.0)
            _, _, l25  = lba_f1(df, gt, threshold, 25.0)
            _, _, l50  = lba_f1(df, gt, threshold, 50.0)

            f1s.append(f1);  pa20s.append(pa20)
            lba10s.append(l10); lba25s.append(l25); lba50s.append(l50)
            lats_all.extend(df["latency_ns"].values / 1e6)  # → ms

        lats = np.array(lats_all)

        summary[arch] = {
            "f1":    (np.mean(f1s),   np.std(f1s)),
            "pa20":  (np.mean(pa20s), np.std(pa20s)),
            "lba10": (np.mean(lba10s), np.std(lba10s)),
            "lba25": (np.mean(lba25s), np.std(lba25s)),
            "lba50": (np.mean(lba50s), np.std(lba50s)),
            "p50":  np.percentile(lats, 50),
            "p95":  np.percentile(lats, 95),
            "p99":  np.percentile(lats, 99),
            "pmax": np.max(lats),
            "_f1s":    f1s,
            "_pa20s":  pa20s,
            "_lba10s": lba10s,
            "_lba25s": lba25s,
            "_lba50s": lba50s,
        }

        print(f"=== {arch.upper()} ===")
        print(f"  Raw F1:      {np.mean(f1s):.4f} ± {np.std(f1s):.4f}")
        print(f"  PA%20 F1:    {np.mean(pa20s):.4f} ± {np.std(pa20s):.4f}")
        print(f"  LBA@10ms:    {np.mean(lba10s):.4f} ± {np.std(lba10s):.4f}")
        print(f"  LBA@25ms:    {np.mean(lba25s):.4f} ± {np.std(lba25s):.4f}")
        print(f"  LBA@50ms:    {np.mean(lba50s):.4f} ± {np.std(lba50s):.4f}")
        print(f"  P50 Latency: {np.percentile(lats, 50):.2f} ms")
        print(f"  P95 Latency: {np.percentile(lats, 95):.2f} ms")
        print(f"  P99 Latency: {np.percentile(lats, 99):.2f} ms")
        print(f"  Max Latency: {np.max(lats):.2f} ms")
        print()

    # ── Paired Wilcoxon tests: Adaptive vs Fixed & DataDriven ────────────
    print("=== Statistical Tests (Wilcoxon signed-rank, paired per-run) ===")
    metrics_to_test = [
        ("Raw F1", "_f1s"),
        ("PA%20 F1", "_pa20s"),
        ("LBA@10ms", "_lba10s"),
        ("LBA@25ms", "_lba25s"),
        ("LBA@50ms", "_lba50s")
    ]
    for metric, key in metrics_to_test:
        for baseline in ["fixed", "datadriven"]:
            a_vals  = summary["adaptive"][key]
            b_vals  = summary[baseline][key]
            try:
                stat, p = stats.wilcoxon(a_vals, b_vals)
                direction = "adaptive > baseline" if np.mean(a_vals) > np.mean(b_vals) else "baseline > adaptive"
                print(f"  {metric:10s} adaptive vs {baseline:11s}: p={p:.4f}  ({direction})")
            except Exception as e:
                print(f"  {metric} vs {baseline}: test failed ({e})")
    print()

    # ── Save summary CSV ──────────────────────────────────────────────────
    rows = []
    for arch in ARCHITECTURES:
        s = summary[arch]
        rows.append({
            "architecture": arch,
            "f1_mean": s["f1"][0],     "f1_std": s["f1"][1],
            "pa20_mean": s["pa20"][0], "pa20_std": s["pa20"][1],
            "lba10_mean": s["lba10"][0],"lba10_std": s["lba10"][1],
            "lba25_mean": s["lba25"][0],"lba25_std": s["lba25"][1],
            "lba50_mean": s["lba50"][0],"lba50_std": s["lba50"][1],
            "lat_p50_ms": s["p50"],
            "lat_p95_ms": s["p95"],
            "lat_p99_ms": s["p99"],
            "lat_max_ms": s["pmax"],
        })
    out_df = pd.DataFrame(rows)
    out_df.to_csv("results/aggregated_results.csv", index=False)
    print("Saved to results/aggregated_results.csv")


if __name__ == "__main__":
    main()
