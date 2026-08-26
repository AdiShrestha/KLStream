import pandas as pd
import numpy as np

# Load ground truth
gt = pd.read_csv('data/replay/replay_AAPL_20120621.csv')
is_anomaly = gt['label'] != 0
total_anomaly_ticks = is_anomaly.sum()

burst_anomaly_overlap = []
total_burst_ticks = []

for i in range(30):
    run = pd.read_csv(f'results/raw/run_adaptive_{i}.csv')
    
    # Create a boolean array for the whole sequence indicating if the tick was processed in w_min
    in_burst = np.zeros(len(gt), dtype=bool)
    for _, row in run.iterrows():
        if row['window_size_used'] == 16:
            in_burst[int(row['first_seq']):int(row['last_seq']) + 1] = True
            
    overlap = np.sum(in_burst & is_anomaly)
    b_ticks = np.sum(in_burst)
    burst_anomaly_overlap.append(overlap)
    total_burst_ticks.append(b_ticks)

print(f"Total anomaly ticks: {total_anomaly_ticks}")
print(f"Mean burst ticks per run: {np.mean(total_burst_ticks)}")
print(f"Mean overlap (anomaly AND burst): {np.mean(burst_anomaly_overlap)}")
print(f"Percentage of anomaly ticks occurring during bursts: {np.mean(burst_anomaly_overlap)/total_anomaly_ticks*100:.2f}%")
print(f"Percentage of normal ticks occurring during bursts: {(np.mean(total_burst_ticks) - np.mean(burst_anomaly_overlap))/(len(gt) - total_anomaly_ticks)*100:.2f}%")
