#!/usr/bin/env python3
"""
Generates the hysteresis loop diagram for the relay window controller.
Source data: results/raw/occupancy_log.csv (logged during Experiment 1).
Also generates synthetic illustration if real log is missing or small.
Saves: results/figures/hysteresis_loop.png and hysteresis_loop.pdf
"""
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.patches import FancyArrowPatch

OUTPUT_DIR = 'results/figures'
LOG_PATH   = 'results/raw/occupancy_log.csv'
os.makedirs(OUTPUT_DIR, exist_ok=True)

OCC_HIGH = 0.70
OCC_LOW  = 0.30
W_MIN    = 16
W_MAX    = 256

# ── Load occupancy log ────────────────────────────────────────────────────
try:
    df = pd.read_csv(LOG_PATH)
    if len(df) < 5:
        raise ValueError("Log too small")
    print(f"Loaded occupancy log: {len(df)} rows")
    use_real = True
except Exception as e:
    print(f"WARNING: {e}. Generating synthetic illustration.")
    use_real = False

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

# ─── Left plot: Time series of occupancy and window_size ────────────────
if use_real:
    t = df['time_ms'].values / 1000.0  # seconds
    occ = df['occupancy'].values
    ws  = df['window_size'].values
else:
    # Synthetic relay oscillation for illustration
    t = np.linspace(0, 10, 200)
    occ_base = 0.05
    ws_arr = []
    occ_arr = []
    current_w = W_MAX
    current_occ = occ_base
    for i in range(len(t)):
        if current_w == W_MAX:
            current_occ = min(current_occ + 0.06, 0.99)
        else:
            current_occ = max(current_occ - 0.08, 0.0)
        if current_occ > OCC_HIGH and current_w == W_MAX:
            current_w = W_MIN
        elif current_occ < OCC_LOW and current_w == W_MIN:
            current_w = W_MAX
        ws_arr.append(current_w)
        occ_arr.append(current_occ)
    occ = np.array(occ_arr)
    ws  = np.array(ws_arr)

ax1_twin = ax1.twinx()
l1, = ax1.plot(t if use_real else t, occ, color='#d62728', alpha=0.8,
               label='Queue occupancy', linewidth=1.5)
l2, = ax1_twin.plot(t if use_real else t, ws, color='#1f77b4', alpha=0.8,
                    label='Window size (W)', linewidth=1.5, linestyle='--')
ax1.axhline(OCC_HIGH, color='red',   linestyle=':', alpha=0.5,
            label=f'occ_high={OCC_HIGH}')
ax1.axhline(OCC_LOW,  color='green', linestyle=':', alpha=0.5,
            label=f'occ_low={OCC_LOW}')
ax1.set_xlabel('Time (seconds)', fontsize=11)
ax1.set_ylabel('Queue Occupancy', fontsize=11, color='#d62728')
ax1_twin.set_ylabel('Window Size W', fontsize=11, color='#1f77b4')
ax1_twin.set_ylim(0, W_MAX * 1.1)
ax1_twin.set_yticks([W_MIN, 64, 128, W_MAX])
ax1.set_ylim(-0.05, 1.05)
ax1.set_title('Time Series: Occupancy and Window Size', fontsize=11)
lines = [l1, l2]
labels = [l.get_label() for l in lines]
ax1.legend(lines, labels, loc='upper right', fontsize=9)

# ─── Right plot: Hysteresis loop (occupancy vs window_size) ─────────────
# Color by trajectory direction
colors = []
for i in range(len(occ)):
    if i == 0:
        colors.append('blue')
    elif ws[i] < ws[i-1] or (ws[i] == W_MIN and occ[i] > OCC_HIGH):
        colors.append('#d62728')   # red = shrinking
    elif ws[i] > ws[i-1] or (ws[i] == W_MAX and occ[i] < OCC_LOW):
        colors.append('#2ca02c')   # green = growing
    else:
        colors.append('#7f7f7f')   # gray = steady

sc = ax2.scatter(occ, ws, c=colors, s=15, alpha=0.6, zorder=3)

# Deadband shading
ax2.axvspan(OCC_LOW, OCC_HIGH, alpha=0.08, color='yellow', label='Deadband')
ax2.axvline(OCC_HIGH, color='red',   linestyle='--', alpha=0.7,
            label=f'occ_high={OCC_HIGH}  →  shrink')
ax2.axvline(OCC_LOW,  color='green', linestyle='--', alpha=0.7,
            label=f'occ_low={OCC_LOW}  →  grow')
ax2.axhline(W_MIN, color='#1f77b4', linestyle=':', alpha=0.5,
            label=f'w_min={W_MIN}')
ax2.axhline(W_MAX, color='#1f77b4', linestyle=':', alpha=0.5,
            label=f'w_max={W_MAX}')

# Legend for colors
from matplotlib.lines import Line2D
legend_elements = [
    Line2D([0],[0], marker='o', color='w', markerfacecolor='#d62728',
           markersize=8, label='Shrinking trajectory'),
    Line2D([0],[0], marker='o', color='w', markerfacecolor='#2ca02c',
           markersize=8, label='Growing trajectory'),
    Line2D([0],[0], marker='o', color='w', markerfacecolor='#7f7f7f',
           markersize=8, label='Steady state'),
]
ax2.legend(handles=legend_elements + [
    plt.Rectangle((0,0),1,1, fc='yellow', alpha=0.2, label='Deadband')],
    fontsize=8, loc='center right')

ax2.set_xlabel('Queue Occupancy (EMA-smoothed)', fontsize=11)
ax2.set_ylabel('Window Size W', fontsize=11)
ax2.set_xlim(-0.05, 1.05)
ax2.set_ylim(0, W_MAX * 1.1)
ax2.set_title('Hysteresis Loop: Relay Feedback Controller\n'
              '(Red=shrinking, Green=growing, Yellow=deadband)', fontsize=11)
ax2.grid(True, linestyle='--', alpha=0.3)

plt.tight_layout()
plt.savefig(f'{OUTPUT_DIR}/hysteresis_loop.png', dpi=300, bbox_inches='tight')
plt.savefig(f'{OUTPUT_DIR}/hysteresis_loop.pdf', bbox_inches='tight')
print(f"Saved: {OUTPUT_DIR}/hysteresis_loop.png")
