#!/usr/bin/env python3
import subprocess
import os
import itertools
import pandas as pd
import numpy as np
from compute_metrics import tick_level_f1, pa_k_f1

def run_experiment_4(oscillation_speed_factor: int = 1460, n_reps: int = 30):
    """
    Experiment 4: Sensitivity grid over occ_low / occ_high / shrink / grow.

    IMPORTANT: uses oscillation_speed_factor 1460. Previously tested at 150x 
    (moderate load), but that did not trigger threshold adaptation effectively.
    We test at 1460x to determine if any configuration can recover F1 under
    heavy load without sacrificing latency bounds.

    n_reps: number of repeated runs per grid cell. Set to 30 for full rigor
    (matches the Exp 2/3 protocol), or 10 for targeted replication of key cells.
    """
    print(f"--- Running Experiment 4: Sensitivity Grid ---")
    print(f"    speed_factor={oscillation_speed_factor}, n_reps={n_reps} per cell")

    occ_pairs = [(0.2, 0.6), (0.3, 0.7), (0.4, 0.8)]
    factor_pairs = [(0.4, 1.05), (0.5, 1.1), (0.6, 1.15)]

    grid = list(itertools.product(occ_pairs, factor_pairs))

    gt_path = "data/replay/replay_AAPL_20120621.csv"
    gt = pd.read_csv(gt_path)

    # Extract segments
    segments = []
    in_seg = False
    start = 0
    for i, label in enumerate(gt["label"]):
        if label != 0 and not in_seg:
            in_seg = True
            start = i
        elif label == 0 and in_seg:
            in_seg = False
            segments.append((start, i-1))
    if in_seg:
        segments.append((start, len(gt)-1))

    results = []

    os.makedirs("results/raw/exp4", exist_ok=True)

    n_cells = len(grid)
    for i, ((occ_low, occ_high), (shrink, grow)) in enumerate(grid):
        print(f"\n[{i+1}/{n_cells}] occ_low={occ_low}, occ_high={occ_high}, shrink={shrink}, grow={grow}  ({n_reps} reps)")

        cell_f1s, cell_pa20s, cell_lats_mean, cell_lats_p95 = [], [], [], []

        import concurrent.futures

        def run_rep(rep):
            out_csv = f"results/raw/exp4/grid_{i}_rep_{rep}.csv"
            cmd = [
                "./build/adaptive_window/adaptive_window_main",
                "--architecture=adaptive",
                f"--out={out_csv}",
                "--duration=10",
                f"--speed-factor={oscillation_speed_factor}",
                "--preserve-timing",
                f"--occ_low={occ_low}",
                f"--occ_high={occ_high}",
                f"--shrink={shrink}",
                f"--grow={grow}"
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            res = pd.read_csv(out_csv)
            threshold = res["max_score"].quantile(0.95)
            
            p, r, f1 = tick_level_f1(res, gt, threshold)
            p20, r20, f1_20 = pa_k_f1(res, gt, threshold, 0.20, segments)
            
            mean_lat = res["latency_ns"].mean() / 1e6  # ms
            p95_lat  = res["latency_ns"].quantile(0.95) / 1e6  # ms
            
            return f1, f1_20, mean_lat, p95_lat

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            rep_results = list(executor.map(run_rep, range(n_reps)))

        for rep, (f1, f1_20, mean_lat, p95_lat) in enumerate(rep_results):
            cell_f1s.append(f1)
            cell_pa20s.append(f1_20)
            cell_lats_mean.append(mean_lat)
            cell_lats_p95.append(p95_lat)

            if (rep + 1) % 5 == 0:
                print(f"  rep {rep+1}/{n_reps}: PA%20 F1={f1_20:.4f}, P95={p95_lat:.2f}ms")

        mean_f1     = float(np.mean(cell_f1s))
        std_f1      = float(np.std(cell_f1s))
        mean_pa20   = float(np.mean(cell_pa20s))
        std_pa20    = float(np.std(cell_pa20s))
        mean_lat_ms = float(np.mean(cell_lats_mean))
        std_lat_ms  = float(np.std(cell_lats_mean))
        median_p95  = float(np.median(cell_lats_p95))
        iqr_p95     = float(np.percentile(cell_lats_p95, 75) - np.percentile(cell_lats_p95, 25))

        results.append({
            "occ_low": occ_low,
            "occ_high": occ_high,
            "shrink": shrink,
            "grow": grow,
            "n_reps": n_reps,
            "raw_f1_mean":   mean_f1,   "raw_f1_std":   std_f1,
            "pa20_f1_mean":  mean_pa20, "pa20_f1_std":  std_pa20,
            "mean_lat_ms_mean": mean_lat_ms, "mean_lat_ms_std": std_lat_ms,
            "p95_lat_ms_median": median_p95, "p95_lat_ms_iqr":  iqr_p95,
        })

        print(f"  → Raw F1: {mean_f1:.4f} ± {std_f1:.4f}  "
              f"PA%20 F1: {mean_pa20:.4f} ± {std_pa20:.4f}  "
              f"P95 lat: {median_p95:.2f} (IQR: {iqr_p95:.2f}) ms")

    df = pd.DataFrame(results)
    out_path = "results/experiment4_grid_replicated.csv"
    df.to_csv(out_path, index=False)
    print(f"\nGrid search complete ({n_reps} reps/cell). Saved to {out_path}.")
    print("\n=== Summary table ===")
    print(df[["occ_low","occ_high","shrink","grow",
              "raw_f1_mean","raw_f1_std","pa20_f1_mean","pa20_f1_std",
              "p95_lat_ms_median","p95_lat_ms_iqr"]].to_string(index=False))
    return df


if __name__ == "__main__":
    import sys
    sf    = int(sys.argv[1]) if len(sys.argv) > 1 else 150
    reps  = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    run_experiment_4(oscillation_speed_factor=sf, n_reps=reps)
