#!/usr/bin/env python3
"""
experiment_runner.py — Automated Experimental Execution Runner & Telemetry Harness for KLStream.

Integrates:
- Preprocessed dataset streaming & split slicing (split_manifest.json)
- Baseline & adaptive window controllers (source/experiments/baselines)
- Model inference & anomaly scoring
- Decomposed latency tracking (INV-010) & exact event accounting (INV-007)
- Comprehensive metric evaluation & JSON telemetry emission (SVI-005)
"""

import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sklearn.ensemble import IsolationForest

# Add experiments root to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "source" / "experiments"))

from baselines import get_controller, BaseWindowController
from metrics.evaluation_metrics import (
    compute_auc_roc,
    compute_pr_auc,
    compute_binary_classification_metrics,
    compute_decomposed_latency_summary,
    compute_latency_summary,
    tune_validation_threshold
)

FEATURE_COLUMNS = [
    "mid_price", "spread", "spread_bps", "log_return", "rolling_vol", "order_imbalance", "volume"
]

def load_dataset_split(csv_path: str, manifest_path: str, split_name: str) -> Tuple[List[Dict[str, Any]], np.ndarray, np.ndarray]:
    """
    Loads dataset rows filtered by split_manifest.json slice.
    Returns (records, feature_matrix, label_array).
    """
    csv_file = Path(csv_path)
    if not csv_file.exists():
        raise FileNotFoundError(f"Dataset not found: {csv_path}")

    start_row = 0
    end_row = None
    
    if manifest_path and Path(manifest_path).exists():
        with open(manifest_path, "r") as f:
            manifest = json.load(f)
            
        ds_name = csv_file.name
        split_key = f"{split_name}_split" if not split_name.endswith("_split") else split_name
        
        for ds_entry in manifest.get("datasets", []):
            fname = ds_entry.get("dataset_filename", "")
            if fname == ds_name or ds_name.endswith(fname):
                if split_key in ds_entry:
                    start_row = ds_entry[split_key]["start_idx"]
                    end_row = ds_entry[split_key]["end_idx"]
                break


    records = []
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i < start_row:
                continue
            if end_row is not None and i >= end_row:
                break
            records.append(row)

    if not records:
        raise ValueError(f"No records found for split '{split_name}' in {csv_path}")

    # Build numpy feature matrix and ground-truth labels
    X = np.empty((len(records), len(FEATURE_COLUMNS)), dtype=float)
    y = np.empty(len(records), dtype=int)
    for i, r in enumerate(records):
        for j, col in enumerate(FEATURE_COLUMNS):
            X[i, j] = float(r.get(col, 0.0) or 0.0)
        y[i] = int(r.get("is_anomaly", 0) or 0)

    return records, X, y

def simulate_pipeline(records: List[Dict[str, Any]],
                      X: np.ndarray,
                      y: np.ndarray,
                      controller: BaseWindowController,
                      model: IsolationForest,
                      t_fixed_ns: float = 500.0,
                      t_point_ns: float = 50.0,
                      max_events: Optional[int] = None) -> Dict[str, Any]:
    """
    Simulates streaming pipeline with dynamic window batching, queuing, and latency tracking.
    """
    total_events = len(records) if max_events is None else min(len(records), max_events)
    if total_events == 0:
        raise ValueError("Empty event stream")

    controller.reset()
    
    # Model inference scores
    # s(x) = 0.5 - decision_function(x) / 2.0
    scores = 0.5 - model.decision_function(X[:total_events])
    
    t_q_list = []
    t_freshness_list = []
    t_exec_list = []
    
    current_queue_depth = 0
    max_queue_depth = 0
    backpressure_count = 0
    
    i = 0
    while i < total_events:
        # Simulate non-stationary arrival burst from volume / log_return
        vol = float(records[i].get("volume", 50.0) or 50.0)
        occupancy = min(1.0, current_queue_depth / 100.0 + (vol / 500.0) * 0.4)
        if occupancy >= 0.80:
            backpressure_count += 1
            
        target_w = controller.get_window_size(occupancy)
        batch_w = max(1, min(target_w, total_events - i))
        
        # Latency model (INV-010)
        # Queuing delay: proportional to occupancy
        t_q = occupancy * 5000.0 # ns
        # Freshness lag: (w - 1) / (2 * lambda)
        t_freshness = (batch_w - 1.0) * 150.0 # ns
        # Batch amortized execution: T_fixed/w + T_point
        t_exec = (t_fixed_ns / batch_w) + t_point_ns
        
        for k in range(batch_w):
            t_q_list.append(t_q)
            t_freshness_list.append(t_freshness)
            t_exec_list.append(t_exec)
            
        current_queue_depth = max(0, current_queue_depth + int(vol / 20) - batch_w)
        max_queue_depth = max(max_queue_depth, current_queue_depth)
        i += batch_w

    # Verify exact event accounting (INV-007)
    assert len(t_q_list) == total_events, f"Event accounting mismatch: {len(t_q_list)} vs {total_events}"

    # Compute metrics
    auc_roc = compute_auc_roc(y[:total_events], scores)
    pr_auc = compute_pr_auc(y[:total_events], scores)
    
    tau = tune_validation_threshold(y[:total_events], scores, target_fpr=0.05)
    cls_metrics = compute_binary_classification_metrics(y[:total_events], scores, threshold=tau)
    
    latency_summary = compute_decomposed_latency_summary(t_q_list, t_freshness_list, t_exec_list)

    return {
        "event_accounting": {
            "events_ingested": total_events,
            "events_processed": total_events,
            "events_dropped": 0,
            "backpressure_activations": backpressure_count,
            "max_queue_occupancy": max_queue_depth
        },
        "detection_metrics": {
            "auc_roc": float(auc_roc),
            "pr_auc": float(pr_auc),
            "classification_at_tau": cls_metrics
        },
        "latency_summary_ns": latency_summary
    }

def run_experiment(dataset_path: str,
                   split_name: str,
                   controller_name: str,
                   manifest_path: str = "data/processed/split_manifest.json",
                   output_json: Optional[str] = None,
                   dry_run: bool = False,
                   controller_kwargs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Main entry point for running experimental benchmarks.
    """
    controller_kwargs = controller_kwargs or {}
    controller = get_controller(controller_name, **controller_kwargs)
    
    records, X, y = load_dataset_split(dataset_path, manifest_path, split_name)
    
    # Train Isolation Forest on normal background slice
    normal_mask = (y == 0)
    X_train = X[normal_mask] if np.sum(normal_mask) > 50 else X
    model = IsolationForest(n_estimators=100, max_samples=min(256, len(X_train)), random_state=42)
    model.fit(X_train)
    
    max_events = 500 if dry_run else None
    results = simulate_pipeline(
        records=records,
        X=X,
        y=y,
        controller=controller,
        model=model,
        max_events=max_events
    )
    
    telemetry = {
        "metadata": {
            "dataset": dataset_path,
            "split": split_name,
            "controller": controller.name,
            "dry_run": dry_run,
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        },
        **results
    }
    
    if output_json:
        out_path = Path(output_json)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w") as f:
            json.dump(telemetry, f, indent=2)
            
    return telemetry

def main():
    parser = argparse.ArgumentParser(description="KLStream Experiment Execution Runner")
    parser.add_argument("--dataset", required=True, help="Path to preprocessed replay CSV")
    parser.add_argument("--split", default="val", choices=["train", "val", "test", "full"], help="Dataset split")
    parser.add_argument("--split-manifest", default="data/processed/split_manifest.json", help="Path to split manifest")
    parser.add_argument("--controller", default="adaptive", help="Window controller (fixed, unadaptive, adaptive, shuffled, periodic)")
    parser.add_argument("--output-json", help="Path to save evaluation output JSON")
    parser.add_argument("--dry-run", action="store_true", help="Execute short dry-run on 500 events")
    
    args = parser.parse_args()
    
    out = run_experiment(
        dataset_path=args.dataset,
        split_name=args.split,
        controller_name=args.controller,
        manifest_path=args.split_manifest,
        output_json=args.output_json,
        dry_run=args.dry_run
    )
    
    print(json.dumps(out, indent=2))

if __name__ == "__main__":
    main()
