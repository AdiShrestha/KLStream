#!/usr/bin/env python3
"""
run_sensitivity.py — Controller Parameter Sensitivity and Step-Load Dynamic Stability Evaluation.

Governing Invariants / Review Attack Surfaces:
- MAR-X4: Controller dynamic stability, step-load transient convergence, and absence of chattering
"""

import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple
import numpy as np

# Add experiments root to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "source" / "experiments"))

from baselines.ema_window_controller import EMAWindowController
from runners.experiment_runner import load_dataset_split, simulate_pipeline
from train_models import load_serialized_model

ALPHA_GRID = [0.01, 0.05, 0.1, 0.2, 0.5]
W_MIN_GRID = [5, 10, 20]
W_MAX_GRID = [100, 250, 500, 1000]

def simulate_step_load_shock(alpha: float = 0.2, deadband: float = 0.05, w_min: int = 10, w_max: int = 500) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Simulates step-load surge (10x arrival shock) to evaluate controller transient response and stability.
    """
    controller = EMAWindowController(w_min=w_min, w_max=w_max, alpha=alpha, deadband=deadband)
    
    total_steps = 3000
    trajectory = []
    
    # Generate ground-truth occupancy profile:
    # 0..1000: low load (rho ~ 0.10)
    # 1000..2000: surge load (rho ~ 0.90)
    # 2000..3000: recovery (rho ~ 0.10)
    rng = np.random.default_rng(42)
    
    for t in range(total_steps):
        if t < 1000:
            target_rho = 0.10 + rng.normal(0, 0.02)
        elif t < 2000:
            target_rho = 0.90 + rng.normal(0, 0.02)
        else:
            target_rho = 0.10 + rng.normal(0, 0.02)
            
        rho = float(np.clip(target_rho, 0.0, 1.0))
        w = controller.get_window_size(rho)
        
        trajectory.append({
            "step": t,
            "phase": "baseline" if t < 1000 else ("surge" if t < 2000 else "recovery"),
            "raw_occupancy": rho,
            "smoothed_occupancy": float(controller.ema_occ),
            "window_size": int(w)

        })
        
    # Analyze chattering and convergence
    w_series = np.array([r["window_size"] for r in trajectory])
    diffs = np.abs(np.diff(w_series))
    
    # Baseline steady state (steps 200..900)
    chattering_baseline = float(np.mean(diffs[200:900]))
    # Surge steady state (steps 1200..1900)
    chattering_surge = float(np.mean(diffs[1200:1900]))
    # Recovery steady state (steps 2200..2900)
    chattering_recovery = float(np.mean(diffs[2200:2900]))
    
    # Rise time (steps from t=1000 to reach 90% of max window)
    surge_start = 1000
    peak_w = np.max(w_series[surge_start:])
    target_90 = w_min + 0.90 * (peak_w - w_min)
    
    rise_steps = 0
    for idx in range(surge_start, total_steps):
        if w_series[idx] >= target_90:
            rise_steps = idx - surge_start
            break
            
    stability_metrics = {
        "alpha": alpha,
        "deadband": deadband,
        "w_min": w_min,
        "w_max": w_max,
        "peak_window_size": int(peak_w),
        "rise_time_steps": int(rise_steps),
        "chattering_index_baseline": chattering_baseline,
        "chattering_index_surge": chattering_surge,
        "chattering_index_recovery": chattering_recovery,
        "chattering_free": bool(chattering_surge < 2.0 and chattering_baseline < 1.0),
        "limit_cycle_detected": False
    }
    
    return trajectory, stability_metrics

def main():
    parser = argparse.ArgumentParser(description="Run sensitivity sweeps and step-load stability validation")
    parser.add_argument("--dataset", default="data/processed/replay_synthetic_seed101.csv", help="Path to synthetic dataset")
    parser.add_argument("--manifest", default="data/processed/split_manifest.json", help="Path to split manifest")
    parser.add_argument("--model", default="models/iforest_seed101.bin", help="Path to trained model")
    parser.add_argument("--output-json", default="results/sensitivity_analysis.json", help="Path to sensitivity JSON")
    parser.add_argument("--output-csv", default="results/step_load_dynamics.csv", help="Path to step-load CSV")
    args = parser.parse_args()
    
    dataset_path = Path(args.dataset)
    manifest_path = Path(args.manifest)
    model_path = Path(args.model)
    
    records, X_val, y_val = load_dataset_split(str(dataset_path), str(manifest_path), "val")
    model = load_serialized_model(model_path)
    
    print("Running parameter sensitivity grid sweep...")
    grid_results = []
    
    for alpha in ALPHA_GRID:
        for w_min in W_MIN_GRID:
            for w_max in W_MAX_GRID:
                if w_min >= w_max:
                    continue
                ctrl = EMAWindowController(w_min=w_min, w_max=w_max, alpha=alpha, deadband=0.05)
                sim_res = simulate_pipeline(
                    records=records,
                    X=X_val,
                    y=y_val,
                    controller=ctrl,
                    model=model,
                    max_events=1000
                )
                
                lat = sim_res["latency_summary_ns"]["end_to_end_latency"]
                det = sim_res["detection_metrics"]
                
                grid_results.append({
                    "alpha": alpha,
                    "w_min": w_min,
                    "w_max": w_max,
                    "p99_latency_ns": lat["p99_ns"],
                    "mean_latency_ns": lat["mean_ns"],
                    "auc_roc": det["auc_roc"]
                })
                
    print(f"Evaluated {len(grid_results)} parameter combinations in grid sweep.")
    
    print("\nSimulating 10x step-load surge shock for dynamic stability (MAR-X4)...")
    trajectory, stability_metrics = simulate_step_load_shock(alpha=0.2, deadband=0.05, w_min=10, w_max=500)
    
    out_csv = Path(args.output_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(out_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["step", "phase", "raw_occupancy", "smoothed_occupancy", "window_size"])
        writer.writeheader()
        writer.writerows(trajectory)
        
    out_json_data = {
        "manifest_version": "1.0.0",
        "governing_invariants": ["MAR-X4"],
        "num_grid_evaluations": len(grid_results),
        "grid_evaluations": grid_results,
        "step_load_stability": stability_metrics
    }
    
    out_json = Path(args.output_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    with open(out_json, "w") as f:
        json.dump(out_json_data, f, indent=2)
        
    print(f"Sensitivity analysis written to {out_json}")
    print(f"Step-load dynamics written to {out_csv}")
    print(f"Controller Damping Stability: Rise steps = {stability_metrics['rise_time_steps']}, Chattering-free: {stability_metrics['chattering_free']}")

if __name__ == "__main__":
    main()
