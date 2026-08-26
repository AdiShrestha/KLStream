#!/usr/bin/env python3
"""
calibrate_thresholds.py — Calibrate anomaly detection decision thresholds strictly on Validation split.

Governing Invariants:
- INV-005: Zero test-set leakage — threshold calibration uses only Validation data
- SVI-002: Temporal monotonicity preserved across train -> val -> test
"""

import argparse
import csv
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple
import numpy as np

# Add experiments root to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "source" / "experiments"))

from train_models import load_serialized_model, FEATURE_COLUMNS
from metrics.evaluation_metrics import (
    compute_auc_roc,
    compute_pr_auc,
    compute_binary_classification_metrics,
    tune_validation_threshold
)

def load_validation_partition(csv_path: Path, start_idx: int, end_idx: int) -> Tuple[np.ndarray, np.ndarray]:
    features = []
    labels = []
    
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i < start_idx:
                continue
            if i >= end_idx:
                break
            vec = [float(row.get(col, 0.0) or 0.0) for col in FEATURE_COLUMNS]
            features.append(vec)
            labels.append(int(row.get("is_anomaly", 0) or 0))
            
    X = np.asarray(features, dtype=float)
    y = np.asarray(labels, dtype=int)
    return X, y

def main():
    parser = argparse.ArgumentParser(description="Calibrate operating thresholds on Validation split")
    parser.add_argument("--models-dir", default="models", help="Path to serialized models")
    parser.add_argument("--manifest", default="data/processed/split_manifest.json", help="Path to split manifest")
    parser.add_argument("--data-dir", default="data/processed", help="Path to preprocessed datasets")
    parser.add_argument("--target-fpr", type=float, default=0.05, help="Target allowable False Positive Rate")
    parser.add_argument("--output", default="results/validation_calibration.json", help="Output calibration JSON path")
    args = parser.parse_args()
    
    models_dir = Path(args.models_dir)
    manifest_path = Path(args.manifest)
    data_dir = Path(args.data_dir)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(manifest_path, "r") as f:
        manifest = json.load(f)
        
    calibrations = []
    
    for ds_entry in manifest["datasets"]:
        fname = ds_entry["dataset_filename"]
        csv_path = data_dir / fname
        
        # Locate corresponding model
        if "seed" in fname:
            seed_part = fname.split("seed")[1].split(".")[0]
            model_file = models_dir / f"iforest_seed{seed_part}.bin"
            alias = f"synthetic_seed{seed_part}"
        else:
            model_file = models_dir / "iforest_academic.bin"
            alias = "academic_sample"
            
        if not model_file.exists():
            raise FileNotFoundError(f"Model missing: {model_file}")
            
        model = load_serialized_model(model_file)
        
        val_info = ds_entry["val_split"]
        start_idx = val_info["start_idx"]
        end_idx = val_info["end_idx"]
        
        X_val, y_val = load_validation_partition(csv_path, start_idx, end_idx)
        scores_val = 0.5 - model.decision_function(X_val)
        
        tau = tune_validation_threshold(y_val, scores_val, target_fpr=args.target_fpr)
        auc_roc = compute_auc_roc(y_val, scores_val)
        pr_auc = compute_pr_auc(y_val, scores_val)
        cls_metrics = compute_binary_classification_metrics(y_val, scores_val, threshold=tau)
        
        calibrations.append({
            "dataset_alias": alias,
            "dataset_filename": fname,
            "validation_rows": len(X_val),
            "validation_anomalies": int(np.sum(y_val == 1)),
            "validation_auc_roc": float(auc_roc),
            "validation_pr_auc": float(pr_auc),
            "threshold": float(tau),
            "target_fpr": float(args.target_fpr),
            "validation_fpr": float(cls_metrics["fpr"]),
            "validation_precision": float(cls_metrics["precision"]),
            "validation_recall": float(cls_metrics["recall"]),
            "validation_f1": float(cls_metrics["f1"]),
            "model_filepath": str(model_file)
        })
        print(f"[{alias}] tau* = {tau:.6f}, Val FPR = {cls_metrics['fpr']:.4f}, Val AUC = {auc_roc:.4f}")
        
    calibration_doc = {
        "manifest_version": "1.0.0",
        "governing_invariants": ["INV-005", "SVI-002", "MAR-3"],
        "target_fpr": float(args.target_fpr),
        "num_calibrations": len(calibrations),
        "calibrations": calibrations
    }
    
    with open(out_path, "w") as f:
        json.dump(calibration_doc, f, indent=2)
        
    print(f"\nValidation calibrations frozen to {out_path}")

if __name__ == "__main__":
    main()
