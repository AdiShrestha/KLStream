#!/usr/bin/env python3
"""
Generates the Pareto frontier scatter plot (P95 Latency vs PA%20 F1)
with ALL 30 individual run points per architecture visible as dots.
Saves to: results/figures/pareto_scatter.png and pareto_scatter.pdf
"""
import os, glob
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import sys

sys.path.insert(0, 'analysis')
from compute_metrics import tick_level_f1, pa_k_f1

# ── Configuration ─────────────────────────────────────────────────────────
REPLAY_PATH   = 'data/replay/replay_AAPL_20120621.csv'
EXP_DIR       = 'results/raw/exp2_3'
OUTPUT_DIR    = 'results/figures'
THRESHOLD_PCT = 0.95   # use the 95th percentile of adaptive scores as threshold

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Load ground truth ─────────────────────────────────────────────────────
ground_truth_df = pd.read_csv(REPLAY_PATH)
labels = ground_truth_df['label'].values
segments = []
in_seg = False
for i, lbl in enumerate(labels):
    if lbl != 0 and not in_seg:
        seg_start = i; in_seg = True
    elif lbl == 0 and in_seg:
        segments.append((seg_start, i - 1)); in_seg = False
if in_seg:
    segments.append((seg_start, len(labels) - 1))
print(f"Ground truth: {len(segments)} anomaly segments")

# ── Per-run threshold (95th pct) will be computed dynamically ────────────

# ── Collect per-run (P95_latency_ms, PA20_F1) for each architecture ───────
architectures = {
    'Fixed':        ('fixed',       '#1f77b4', 'o', 100),  # blue circles
    'Data-Driven':  ('datadriven',  '#ff7f0e', 's', 100),  # orange squares
    'Adaptive':     ('adaptive',    '#2ca02c', '^', 100),  # green triangles
}

results = {}
for display_name, (arch, color, marker, size) in architectures.items():
    files = sorted(glob.glob(f'{EXP_DIR}/run_{arch}_*.csv'))
    p95_values  = []
    pa20_values = []
    for f in files:
        df = pd.read_csv(f)
        lat_ms = df['latency_ns'].values / 1e6
        p95 = float(np.percentile(lat_ms, 95))
        threshold = float(df['max_score'].quantile(THRESHOLD_PCT))
        _, _, pa20 = pa_k_f1(df, ground_truth_df, threshold, 0.20, segments)
        p95_values.append(p95)
        pa20_values.append(pa20)
    results[display_name] = {
        'color': color, 'marker': marker, 'size': size,
        'p95': p95_values, 'pa20': pa20_values,
        'mean_p95': np.mean(p95_values), 'mean_pa20': np.mean(pa20_values),
    }
    print(f"{display_name}: mean P95={np.mean(p95_values):.2f}ms "
          f"mean PA%20={np.mean(pa20_values):.4f} n={len(files)}")

# ── Plot ─────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(8, 6))

for display_name, data in results.items():
    ax.scatter(data['p95'], data['pa20'],
               c=data['color'], marker=data['marker'],
               s=data['size'], alpha=0.5, label=f'{display_name} (n=30)',
               edgecolors='black', linewidths=0.5)
    # Plot mean as larger, fully opaque point with black border
    ax.scatter([data['mean_p95']], [data['mean_pa20']],
               c=data['color'], marker=data['marker'],
               s=data['size'] * 3, alpha=1.0, edgecolors='black',
               linewidths=2.0, zorder=5)

# Annotate means
for display_name, data in results.items():
    ax.annotate(f"  {display_name}\n  mean",
                xy=(data['mean_p95'], data['mean_pa20']),
                fontsize=8, color=data['color'],
                fontweight='bold')

ax.set_xlabel('P95 Detection Latency (ms)  ←  lower is better',
              fontsize=12)
ax.set_ylabel('PA%20 F1 Score  ←  higher is better',
              fontsize=12)
ax.set_title('Latency–Accuracy Pareto Frontier\n'
             '(All 30 runs per architecture; large markers = means)',
             fontsize=12)
ax.legend(fontsize=10)
ax.grid(True, linestyle='--', alpha=0.4)

# Add quadrant annotation
ax.axvline(x=25, color='gray', linestyle=':', alpha=0.5)
ax.text(22, ax.get_ylim()[0] + 0.002, 'Low-latency\nregion',
        ha='right', fontsize=8, color='gray')

plt.tight_layout()
plt.savefig(f'{OUTPUT_DIR}/pareto_scatter.png', dpi=300, bbox_inches='tight')
plt.savefig(f'{OUTPUT_DIR}/pareto_scatter.pdf', bbox_inches='tight')
print(f"Saved: {OUTPUT_DIR}/pareto_scatter.png")
print(f"Saved: {OUTPUT_DIR}/pareto_scatter.pdf")

# Save the underlying data as CSV for inclusion in paper
rows = []
for display_name, data in results.items():
    for p95, pa20 in zip(data['p95'], data['pa20']):
        rows.append({'architecture': display_name, 'p95_ms': p95,
                     'pa20_f1': pa20})
pd.DataFrame(rows).to_csv(f'{OUTPUT_DIR}/pareto_data.csv', index=False)
print(f"Saved raw data: {OUTPUT_DIR}/pareto_data.csv")
