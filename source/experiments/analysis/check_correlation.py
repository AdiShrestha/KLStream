import pandas as pd
import numpy as np
import glob
import os

gt = pd.read_csv("data/replay/replay_AAPL_20120621.csv")
n_ticks = len(gt)
labels = gt["label"].values != 0
total_anomaly_ticks = labels.sum()
total_normal_ticks = n_ticks - total_anomaly_ticks

out_lines = ["run_id,total_anomaly_ticks,burst_ticks,overlap_ticks,pct_anomaly_in_burst,pct_normal_in_burst"]

for i in range(1, 31):
    file_path = f"results/raw/exp2_3/run_adaptive_{i}.csv"
    if not os.path.exists(file_path): continue
    
    df = pd.read_csv(file_path)
    
    # Create an array to track if a tick was evaluated at w_min (16)
    w_min_ticks = np.zeros(n_ticks, dtype=bool)
    
    for _, row in df.iterrows():
        if row["window_size_used"] == 16:
            s = int(row["first_seq"])
            e = int(row["last_seq"])
            if s < n_ticks and e < n_ticks:
                w_min_ticks[s:e + 1] = True
            
    burst_ticks = w_min_ticks.sum()
    overlap_ticks = (w_min_ticks & labels).sum()
    
    pct_anomaly = (overlap_ticks / total_anomaly_ticks) * 100 if total_anomaly_ticks > 0 else 0
    pct_normal = ((burst_ticks - overlap_ticks) / total_normal_ticks) * 100 if total_normal_ticks > 0 else 0
    
    out_lines.append(f"{i},{total_anomaly_ticks},{burst_ticks},{overlap_ticks},{pct_anomaly:.2f},{pct_normal:.2f}")

with open("results/event_fraction_analysis.csv", "w") as f:
    f.write("\n".join(out_lines) + "\n")

# Calculate means
df_res = pd.read_csv("results/event_fraction_analysis.csv")
print(f"Mean pct_anomaly_in_burst: {df_res['pct_anomaly_in_burst'].mean():.2f}% ± {df_res['pct_anomaly_in_burst'].std():.2f}%")
print(f"Mean pct_normal_in_burst: {df_res['pct_normal_in_burst'].mean():.2f}% ± {df_res['pct_normal_in_burst'].std():.2f}%")
