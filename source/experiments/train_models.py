#!/usr/bin/env python3
"""
train_models.py — Trains and serializes Isolation Forest models strictly on Training partitions.

Governing Invariants:
- INV-004: Model artifact provenance and hash integrity recorded
- INV-005: Model training strictly confined to Training partition (zero leakage)
"""

import argparse
import csv
import hashlib
import json
import os
import pickle
import struct
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple
import numpy as np
from sklearn.ensemble import IsolationForest

FEATURE_COLUMNS = [
    "mid_price", "spread", "spread_bps", "log_return", "rolling_vol", "order_imbalance", "volume"
]

def load_training_partition(csv_path: Path, start_idx: int, end_idx: int) -> Tuple[np.ndarray, np.ndarray]:
    """
    Extracts strictly the Training partition rows [start_idx, end_idx) from preprocessed CSV.
    """
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

def serialize_model_with_header(model: IsolationForest, output_path: Path) -> str:
    """
    Serializes Isolation Forest model with 64-byte 'KLIF' binary header (C03-08) and computes SHA-256.
    Header format:
    - magic: 4 bytes b'KLIF'
    - version: uint32 (1)
    - num_trees: uint32 (100)
    - max_depth: uint32 (8)
    - subsample_size: uint32 (256)
    - reserved: 16 bytes
    - payload_sha256: 32 bytes
    Followed by pickled model payload.
    """
    payload = pickle.dumps(model)
    payload_sha256_bytes = hashlib.sha256(payload).digest()
    
    magic = b"KLIF"
    version = 1
    num_trees = len(model.estimators_)
    subsample_size = model.max_samples_ if isinstance(model.max_samples_, int) else 256
    num_features = len(FEATURE_COLUMNS)
    payload_size = len(payload)
    # c(psi) for subsample 256 is approx 2 * (ln(255) + 0.5772156649) - (2 * 255 / 256) ≈ 10.24
    c_psi = 2.0 * (np.log(max(1, subsample_size - 1)) + 0.5772156649) - (2.0 * (subsample_size - 1.0) / float(subsample_size))
    
    header = struct.pack("<4sIIIIId32s", magic, version, num_trees, subsample_size, num_features, payload_size, float(c_psi), payload_sha256_bytes)
    assert len(header) == 64, f"Header size mismatch: {len(header)} != 64"
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(header)
        f.write(payload)
        
    full_sha256 = hashlib.sha256(open(output_path, "rb").read()).hexdigest()
    return full_sha256

def load_serialized_model(model_path: Path) -> IsolationForest:
    """
    Verifies 64-byte KLIF header and loads Isolation Forest model.
    """
    with open(model_path, "rb") as f:
        header = f.read(64)
        magic, version, num_trees, subsample_size, num_features, payload_size, c_psi, payload_sha256_bytes = struct.unpack("<4sIIIIId32s", header)
        assert magic == b"KLIF", f"Invalid magic: {magic}"
        assert version == 1, f"Unsupported version: {version}"
        payload = f.read()
        
    assert hashlib.sha256(payload).digest() == payload_sha256_bytes, "Model payload SHA-256 corruption detected"
    model = pickle.loads(payload)
    return model


def main():
    parser = argparse.ArgumentParser(description="Train and serialize Isolation Forest models on Training partitions")
    parser.add_argument("--split-manifest", default="data/processed/split_manifest.json", help="Path to split manifest")
    parser.add_argument("--data-dir", default="data/processed", help="Path to preprocessed data directory")
    parser.add_argument("--output-dir", default="models", help="Directory to save serialized models")
    args = parser.parse_args()
    
    manifest_path = Path(args.split_manifest)
    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    with open(manifest_path, "r") as f:
        manifest = json.load(f)
        
    model_entries = []
    
    for ds_entry in manifest["datasets"]:
        fname = ds_entry["dataset_filename"]
        csv_path = data_dir / fname
        if not csv_path.exists():
            raise FileNotFoundError(f"Dataset file missing: {csv_path}")
            
        train_info = ds_entry["train_split"]
        start_idx = train_info["start_idx"]
        end_idx = train_info["end_idx"]
        
        print(f"Training on {fname} (rows {start_idx}..{end_idx})...")
        X_train, y_train = load_training_partition(csv_path, start_idx, end_idx)
        
        # Train strictly on normal samples in Training partition
        normal_mask = (y_train == 0)
        X_fit = X_train[normal_mask] if np.sum(normal_mask) > 50 else X_train
        
        model = IsolationForest(
            n_estimators=100,
            max_samples=min(256, len(X_fit)),
            random_state=42
        )
        model.fit(X_fit)
        
        # Model alias naming
        if "seed" in fname:
            seed_part = fname.split("seed")[1].split(".")[0]
            model_name = f"iforest_seed{seed_part}.bin"
            seed_val = int(seed_part)
        else:
            model_name = "iforest_academic.bin"
            seed_val = None
            
        out_bin = output_dir / model_name
        file_sha256 = serialize_model_with_header(model, out_bin)
        
        # Verify load integrity immediately
        loaded = load_serialized_model(out_bin)
        assert len(loaded.estimators_) == 100, "Loaded model verification failed"
        
        model_entries.append({
            "model_name": model_name,
            "filepath": str(out_bin),
            "dataset_filename": fname,
            "training_rows": len(X_train),
            "training_normal_rows": int(np.sum(normal_mask)),
            "seed": seed_val,
            "sha256": file_sha256,
            "n_estimators": 100,
            "max_samples": 256,
            "random_state": 42
        })
        print(f"  [SAVED] {out_bin} (SHA-256: {file_sha256[:16]}...)")
        
    # Write training manifest
    training_manifest = {
        "manifest_version": "1.0.0",
        "governing_invariants": ["INV-004", "INV-005"],
        "num_models": len(model_entries),
        "models": model_entries
    }
    
    manifest_out = output_dir / "training_manifest.json"
    with open(manifest_out, "w") as f:
        json.dump(training_manifest, f, indent=2)
        
    print(f"\nTraining manifest written to {manifest_out} ({len(model_entries)} models)")

if __name__ == "__main__":
    main()
