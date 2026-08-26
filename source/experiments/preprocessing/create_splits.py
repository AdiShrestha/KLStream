#!/usr/bin/env python3
"""
create_splits.py — Leakage-Safe Temporal Data Partitioning and Frozen Split Manifest.

Enforces:
- 60% Train, 20% Validation, 20% Test chronological ordering.
- Strict non-overlapping temporal boundaries (INV-005, SVI-002).
- Pre-registration of threshold tuning on Validation split only (MAR-3 Attack 4).
"""

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
from typing import Dict, List

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
PROCESSED_DIR = REPO_ROOT / "data" / "processed"
SPLIT_MANIFEST_PATH = PROCESSED_DIR / "split_manifest.json"

def calculate_splits_for_file(csv_path: Path) -> dict:
    rows = []
    with open(csv_path, "r", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append({
                "seq": int(r["seq"]),
                "timestamp_ns": int(r["timestamp_ns"]),
                "is_anomaly": int(r["is_anomaly"])
            })
            
    n = len(rows)
    if n < 10:
        raise ValueError(f"Dataset {csv_path.name} too small for partitioning: {n} rows")
        
    train_n = int(n * 0.60)
    val_n = int(n * 0.20)
    test_n = n - train_n - val_n
    
    train_rows = rows[:train_n]
    val_rows = rows[train_n : train_n + val_n]
    test_rows = rows[train_n + val_n :]
    
    train_anomalies = sum(r["is_anomaly"] for r in train_rows)
    val_anomalies = sum(r["is_anomaly"] for r in val_rows)
    test_anomalies = sum(r["is_anomaly"] for r in test_rows)
    
    # Assert temporal monotonicity
    if train_rows[-1]["timestamp_ns"] > val_rows[0]["timestamp_ns"]:
        raise ValueError(f"Temporal leakage in {csv_path.name}: Train max ts > Val min ts")
    if val_rows[-1]["timestamp_ns"] > test_rows[0]["timestamp_ns"]:
        raise ValueError(f"Temporal leakage in {csv_path.name}: Val max ts > Test min ts")
        
    return {
        "dataset_filename": csv_path.name,
        "total_rows": n,
        "split_policy": "Chronological 60% Train / 20% Val / 20% Test",
        "threshold_tuning_target": "val",
        "train_split": {
            "start_idx": 0,
            "end_idx": train_n,
            "row_count": train_n,
            "start_seq": train_rows[0]["seq"],
            "end_seq": train_rows[-1]["seq"],
            "start_timestamp_ns": train_rows[0]["timestamp_ns"],
            "end_timestamp_ns": train_rows[-1]["timestamp_ns"],
            "anomaly_count": train_anomalies
        },
        "val_split": {
            "start_idx": train_n,
            "end_idx": train_n + val_n,
            "row_count": val_n,
            "start_seq": val_rows[0]["seq"],
            "end_seq": val_rows[-1]["seq"],
            "start_timestamp_ns": val_rows[0]["timestamp_ns"],
            "end_timestamp_ns": val_rows[-1]["timestamp_ns"],
            "anomaly_count": val_anomalies
        },
        "test_split": {
            "start_idx": train_n + val_n,
            "end_idx": n,
            "row_count": test_n,
            "start_seq": test_rows[0]["seq"],
            "end_seq": test_rows[-1]["seq"],
            "start_timestamp_ns": test_rows[0]["timestamp_ns"],
            "end_timestamp_ns": test_rows[-1]["timestamp_ns"],
            "anomaly_count": test_anomalies
        }
    }

def main():
    parser = argparse.ArgumentParser(description="Create Leakage-Safe Data Split Manifest")
    parser.add_argument("--input-dir", type=Path, default=PROCESSED_DIR, help="Directory containing processed CSVs")
    parser.add_argument("--manifest", type=Path, default=SPLIT_MANIFEST_PATH, help="Output manifest JSON path")
    
    args = parser.parse_args()
    args.input_dir = args.input_dir.resolve()
    args.manifest = args.manifest.resolve()
    
    csv_files = sorted(args.input_dir.glob("replay_*.csv"))
    print(f"Assigning temporal splits for {len(csv_files)} processed files in {args.input_dir}...")
    
    dataset_splits = []
    for cf in csv_files:
        info = calculate_splits_for_file(cf)
        dataset_splits.append(info)
        print(f"  [OK] {cf.name}: Train=[0, {info['train_split']['end_idx']}), Val=[{info['val_split']['start_idx']}, {info['val_split']['end_idx']}), Test=[{info['test_split']['start_idx']}, {info['test_split']['end_idx']})")

    manifest = {
        "manifest_version": "1.0.0",
        "governing_invariants": ["INV-005", "SVI-002", "MAR-3"],
        "policy": "Deterministic temporal 60/20/20 partitioning with zero lookahead leakage",
        "num_datasets": len(dataset_splits),
        "datasets": dataset_splits
    }
    
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    with open(args.manifest, "w") as f:
        json.dump(manifest, f, indent=2)
        
    print(f"\nSplit manifest successfully written to {args.manifest}")

if __name__ == "__main__":
    main()
