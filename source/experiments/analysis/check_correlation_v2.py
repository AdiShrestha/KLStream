#!/usr/bin/env python3
"""
Correctly computes, per adaptive run, what fraction of ORIGINAL TICKS
(not windows) were covered by a window that was running at w_min=16,
and cross-references this against which ticks are labeled anomalous
in the ground truth. This REPLACES check_correlation.py, which used
an incorrect static replay-CSV flag instead of the actual runtime
window_size_used column.
"""
import pandas as pd
import numpy as np
import glob
import sys

REPLAY_PATH = 'data/replay/replay_AAPL_20120621.csv'
EXP_DIR = 'results/raw/exp2_3'

# Load ground truth once
gt = pd.read_csv(REPLAY_PATH)
n_ticks = len(gt)
anomaly_mask = (gt['label'].values != 0)
print(f"Ground truth: {n_ticks} total ticks, {anomaly_mask.sum()} anomalous ticks")

files = sorted(glob.glob(f'{EXP_DIR}/run_adaptive_*.csv'))
if not files:
    print("ERROR: no adaptive run files found. Check EXP_DIR path.")
    sys.exit(1)

rows = []
for i, f in enumerate(files):
    df = pd.read_csv(f)
    if 'window_size_used' not in df.columns:
        print(f"ERROR: {f} has no window_size_used column. Columns present: {list(df.columns)}")
        sys.exit(1)
    if 'first_seq' not in df.columns or 'last_seq' not in df.columns:
        print(f"ERROR: {f} missing first_seq/last_seq columns. Columns: {list(df.columns)}")
        sys.exit(1)

    # Build a per-tick "was this tick covered by a w_min window" mask
    tick_at_wmin = np.zeros(n_ticks, dtype=bool)
    for _, row in df.iterrows():
        if row['window_size_used'] == 16:
            s = int(row['first_seq'])
            e = int(row['last_seq'])
            if s < n_ticks and e < n_ticks and s <= e:
                tick_at_wmin[s:e+1] = True

    total_anomaly = anomaly_mask.sum()
    total_normal = (~anomaly_mask).sum()
    anomaly_at_wmin = (anomaly_mask & tick_at_wmin).sum()
    normal_at_wmin = (~anomaly_mask & tick_at_wmin).sum()

    pct_anomaly_at_wmin = 100.0 * anomaly_at_wmin / total_anomaly if total_anomaly else 0.0
    pct_normal_at_wmin  = 100.0 * normal_at_wmin  / total_normal  if total_normal  else 0.0

    rows.append({
        'run_id': i,
        'total_anomaly_ticks': int(total_anomaly),
        'total_normal_ticks': int(total_normal),
        'anomaly_ticks_at_wmin': int(anomaly_at_wmin),
        'normal_ticks_at_wmin': int(normal_at_wmin),
        'pct_anomaly_at_wmin': pct_anomaly_at_wmin,
        'pct_normal_at_wmin': pct_normal_at_wmin,
    })
    print(f"Run {i}: anomaly@wmin={pct_anomaly_at_wmin:.2f}%  normal@wmin={pct_normal_at_wmin:.2f}%")

out = pd.DataFrame(rows)
out.to_csv('results/event_fraction_analysis_v2.csv', index=False)

print("\n=== SUMMARY ACROSS ALL RUNS ===")
print(f"Mean pct_anomaly_at_wmin: {out['pct_anomaly_at_wmin'].mean():.4f}% "
      f"± {out['pct_anomaly_at_wmin'].std():.4f}%")
print(f"Mean pct_normal_at_wmin:  {out['pct_normal_at_wmin'].mean():.4f}% "
      f"± {out['pct_normal_at_wmin'].std():.4f}%")
print(f"Saved: results/event_fraction_analysis_v2.csv")
