#!/usr/bin/env python3
"""Validation-Only Hyperparameter Selection Curves & Model Checkpoint Serialization.

Evaluates Dynamic Isolation Forest budget curves across a hyperparameter grid:
  trees in {25, 50, 100, 200}
  subsample in {64, 128, 256, 512}

STRICT DATA ISOLATION ENFORCEMENT:
  Fitting and evaluation are strictly conducted on 'train' (rec_20170817) and
  'validation' (rec_20170818) splits from data/cohort.csv.
  The 'test' holdout split (rec_20170819) is NEVER accessed, loaded, or evaluated.

Saves the selected baseline model checkpoint in portable .iforest binary format.
Standard library only.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
from typing import Any


def find_engine_binary(root: pathlib.Path) -> pathlib.Path:
    candidates = [
        root / "build" / "engine_runner",
        root / "build-sanitizers" / "engine_runner",
        root / "source" / "build" / "engine_runner",
    ]
    for c in candidates:
        if c.is_file() and os.access(c, os.X_OK):
            return c
    raise FileNotFoundError("engine_runner binary not found. Build the project first.")


def compute_auroc(labels: list[float], scores: list[float]) -> float:
    n = len(labels)
    pos = sum(labels)
    neg = n - pos
    if n == 0 or pos == 0 or neg == 0:
        return 0.5

    # Rank-sum calculation
    ordered = sorted(zip(scores, labels))
    rank_sum, i = 0.0, 0
    while i < n:
        j = i + 1
        while j < n and ordered[j][0] == ordered[i][0]:
            j += 1
        rank_sum += (i + 1 + j) / 2.0 * sum(z[1] for z in ordered[i:j])
        i = j
    return (rank_sum - pos * (pos + 1.0) / 2.0) / (pos * neg)


def compute_separation(labels: list[float], scores: list[float]) -> dict[str, float]:
    pos_scores = [s for l, s in zip(labels, scores) if l == 1.0]
    neg_scores = [s for l, s in zip(labels, scores) if l == 0.0]
    pos_mean = sum(pos_scores) / len(pos_scores) if pos_scores else 0.0
    neg_mean = sum(neg_scores) / len(neg_scores) if neg_scores else 0.0
    return {
        "pos_mean": pos_mean,
        "neg_mean": neg_mean,
        "delta_mu": pos_mean - neg_mean,
    }


def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(
        description="KLStream Model Training and Validation Budget Curve Evaluation"
    )
    parser.add_argument("--cohort", default="data/cohort.csv", help="Path to cohort CSV")
    parser.add_argument("--output", default="data/model_checkpoint.iforest", help="Path to output .iforest checkpoint")
    parser.add_argument("--curves-json", default=None, help="Optional output path for budget curves JSON")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    repo_root = pathlib.Path(__file__).resolve().parents[2]
    cohort_path = pathlib.Path(args.cohort)
    if not cohort_path.is_absolute():
        cohort_path = repo_root / cohort_path

    if not cohort_path.is_file():
        sys.stderr.write(f"Cohort CSV not found at {cohort_path}\n")
        sys.exit(1)

    engine_bin = find_engine_binary(repo_root)

    # 1. Load cohort data with STRICT DATA ISOLATION
    train_rows = []
    val_rows = []
    test_count = 0
    ignored_keys = {"sample_id", "label", "group_id", "split", "source_ids"}

    with open(cohort_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            split = r.get("split")
            if split == "train":
                train_rows.append(r)
            elif split == "validation":
                val_rows.append(r)
            elif split == "test":
                test_count += 1
            else:
                pass

    print("================================================================================")
    print("STRICT DATA ISOLATION VERIFICATION (Contract KLS-06)")
    print(f"  Training Split (rec_20170817):    {len(train_rows)} samples admitted for fitting")
    print(f"  Validation Split (rec_20170818):  {len(val_rows)} samples admitted for hyperparameter selection")
    print(f"  Test Split Holdout (rec_20170819): {test_count} samples COMPLETELY EXCLUDED (unaccessed)")
    print("================================================================================\n")

    if not train_rows:
        raise ValueError("Training split is empty")
    if not val_rows:
        raise ValueError("Validation split is empty")

    # Extract features and labels
    def prepare_data(rows: list[dict[str, Any]]):
        sample_ids = []
        labels = []
        feature_matrix = []
        for r in rows:
            sid = r["sample_id"]
            lbl = float(r["label"])
            feats = []
            for k, v in r.items():
                if k not in ignored_keys:
                    val = float(v)
                    if not math.isfinite(val):
                        raise ValueError(f"Non-finite feature {k}={v} in sample {sid}")
                    feats.append(val)
            sample_ids.append(sid)
            labels.append(lbl)
            feature_matrix.append(feats)
        return sample_ids, labels, feature_matrix

    train_ids, train_labels, train_feats = prepare_data(train_rows)
    val_ids, val_labels, val_feats = prepare_data(val_rows)
    feature_dim = len(train_feats[0])

    print(f"Feature Dimension: {feature_dim} causal features per sample.")
    print(f"Train Class Balance:      Pos={int(sum(train_labels))}, Neg={int(len(train_labels)-sum(train_labels))}")
    print(f"Validation Class Balance: Pos={int(sum(val_labels))}, Neg={int(len(val_labels)-sum(val_labels))}\n")

    # Hyperparameter Grid
    trees_grid = [25, 50, 100, 200]
    subsample_grid = [64, 128, 256, 512]

    results = []
    best_config = None
    best_val_auroc = -1.0
    best_val_sep = -1.0

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = pathlib.Path(tmpdir)
        train_csv_path = tmp / "train_features.csv"
        val_csv_path = tmp / "val_features.csv"

        with open(train_csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            for sid, feats in zip(train_ids, train_feats):
                w.writerow([sid] + feats)

        with open(val_csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            for sid, feats in zip(val_ids, val_feats):
                w.writerow([sid] + feats)

        print("Evaluating Model Budget Curve Grid (16 configurations)...")
        print("| Trees | Subsample | Val AUROC | Val Delta-Mu | Train AUROC | Train Delta-Mu | Size (KB) |")
        print("|-------|-----------|-----------|--------------|-------------|----------------|-----------|")

        for t in trees_grid:
            for s in subsample_grid:
                model_tmp_path = tmp / f"model_t{t}_s{s}.iforest"
                val_pred_path = tmp / f"pred_val_t{t}_s{s}.csv"
                train_pred_path = tmp / f"pred_train_t{t}_s{s}.csv"

                # 1. Fit on train, evaluate on validation, save model
                cmd_fit = [
                    str(engine_bin),
                    "--train", str(train_csv_path),
                    "--eval", str(val_csv_path),
                    "--output", str(val_pred_path),
                    "--model-save", str(model_tmp_path),
                    "--trees", str(t),
                    "--subsample", str(s),
                    "--seed", str(args.seed),
                ]
                res_fit = subprocess.run(cmd_fit, capture_output=True, text=True)
                if res_fit.returncode != 0:
                    raise RuntimeError(f"Engine fit failed for t={t}, s={s}: {res_fit.stderr}")

                # 2. Evaluate on train using reloaded model
                cmd_train_eval = [
                    str(engine_bin),
                    "--eval", str(train_csv_path),
                    "--output", str(train_pred_path),
                    "--model-load", str(model_tmp_path),
                ]
                res_train_eval = subprocess.run(cmd_train_eval, capture_output=True, text=True)
                if res_train_eval.returncode != 0:
                    raise RuntimeError(f"Engine train eval failed for t={t}, s={s}: {res_train_eval.stderr}")

                # Compute metrics
                with open(val_pred_path, "r", encoding="utf-8") as f:
                    val_scores_dict = {r["sample_id"]: float(r["score"]) for r in csv.DictReader(f)}
                with open(train_pred_path, "r", encoding="utf-8") as f:
                    train_scores_dict = {r["sample_id"]: float(r["score"]) for r in csv.DictReader(f)}

                ordered_val_scores = [val_scores_dict[sid] for sid in val_ids]
                ordered_train_scores = [train_scores_dict[sid] for sid in train_ids]

                val_auroc = compute_auroc(val_labels, ordered_val_scores)
                val_sep = compute_separation(val_labels, ordered_val_scores)
                train_auroc = compute_auroc(train_labels, ordered_train_scores)
                train_sep = compute_separation(train_labels, ordered_train_scores)

                size_kb = os.path.getsize(model_tmp_path) / 1024.0

                record = {
                    "trees": t,
                    "subsample": s,
                    "val_auroc": round(val_auroc, 5),
                    "val_delta_mu": round(val_sep["delta_mu"], 5),
                    "val_pos_mean": round(val_sep["pos_mean"], 5),
                    "val_neg_mean": round(val_sep["neg_mean"], 5),
                    "train_auroc": round(train_auroc, 5),
                    "train_delta_mu": round(train_sep["delta_mu"], 5),
                    "train_pos_mean": round(train_sep["pos_mean"], 5),
                    "train_neg_mean": round(train_sep["neg_mean"], 5),
                    "model_size_bytes": os.path.getsize(model_tmp_path),
                }
                results.append(record)

                print(
                    f"| {t:5d} | {s:9d} | {val_auroc:9.4f} | {val_sep['delta_mu']:+12.4f} | "
                    f"{train_auroc:11.4f} | {train_sep['delta_mu']:+14.4f} | {size_kb:8.1f} KB |"
                )

                # Selection logic: prioritize validation AUROC, tie-break on validation separation
                if (val_auroc > best_val_auroc) or (
                    abs(val_auroc - best_val_auroc) < 1e-4 and val_sep["delta_mu"] > best_val_sep
                ):
                    best_val_auroc = val_auroc
                    best_val_sep = val_sep["delta_mu"]
                    best_config = (t, s, model_tmp_path)

        # Copy selected baseline model to target destination
        assert best_config is not None
        sel_t, sel_s, sel_path = best_config
        out_path = pathlib.Path(args.output)
        if not out_path.is_absolute():
            out_path = repo_root / out_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(sel_path, out_path)

    out_hash = sha256_file(out_path)
    print("\n================================================================================")
    print(f"SELECTED BASELINE MODEL CHECKPOINT (Strict Validation-Only Selection):")
    print(f"  Configuration:       trees={sel_t}, subsample={sel_s}, seed={args.seed}")
    print(f"  Validation AUROC:    {best_val_auroc:.4f}")
    print(f"  Validation Delta-Mu: {best_val_sep:+.4f}")
    print(f"  Target Checkpoint:   {out_path}")
    print(f"  File Size:           {os.path.getsize(out_path)} bytes")
    print(f"  SHA-256 Digest:      {out_hash}")
    print("================================================================================\n")

    if args.curves_json:
        cj_path = pathlib.Path(args.curves_json)
        if not cj_path.is_absolute():
            cj_path = repo_root / cj_path
        cj_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cj_path, "w", encoding="utf-8") as f:
            json.dump({
                "selected_config": {"trees": sel_t, "subsample": sel_s, "seed": args.seed, "sha256": out_hash},
                "grid_evaluations": results,
            }, f, indent=2)
        print(f"Saved curves metadata to: {cj_path}")


if __name__ == "__main__":
    main()
