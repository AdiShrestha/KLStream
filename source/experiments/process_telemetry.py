#!/usr/bin/env python3
"""
process_telemetry.py — Consolidate run telemetries and validate latency decomposition identities.

Governing Invariants:
- INV-007: Event accounting integrity (0 drops)
- INV-010: Latency decomposition validation (T_e2e = T_q + T_freshness + T_exec)
- INV-011: Metric identity validation
"""

import argparse
import csv
import glob
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List
import pandas as pd

def main():
    parser = argparse.ArgumentParser(description="Process and consolidate experimental telemetry runs")
    parser.add_argument("--runs-dir", default="results/runs", help="Directory containing run JSON files")
    parser.add_argument("--output-csv", default="results/consolidated_telemetry.csv", help="Path to save consolidated CSV")
    parser.add_argument("--report", default="results/latency_decomposition_report.json", help="Path to save validation report")
    args = parser.parse_args()
    
    runs_dir = Path(args.runs_dir)
    run_files = sorted(runs_dir.glob("*.json"))
    
    if not run_files:
        raise FileNotFoundError(f"No run JSON files found in {runs_dir}")
        
    rows = []
    validation_failures = []
    
    for rf in run_files:
        with open(rf, "r") as f:
            data = json.load(f)
            
        meta = data["metadata"]
        acct = data["event_accounting"]
        det = data["detection_metrics"]
        cls_tau = det.get("classification_at_tau", {})
        lat = data["latency_summary_ns"]
        
        q_lat = lat["queuing_latency"]
        f_lat = lat["freshness_lag"]
        e_lat = lat["execution_latency"]
        e2e_lat = lat["end_to_end_latency"]
        
        # Validate event accounting (INV-007)
        if acct["events_dropped"] != 0:
            validation_failures.append(f"{rf.name}: events_dropped != 0 ({acct['events_dropped']})")
            
        # Validate latency decomposition identity (INV-010)
        expected_mean = q_lat["mean_ns"] + f_lat["mean_ns"] + e_lat["mean_ns"]
        actual_mean = e2e_lat["mean_ns"]
        if abs(actual_mean - expected_mean) > 1e-3:
            validation_failures.append(f"{rf.name}: Latency decomposition mismatch: {actual_mean} != {expected_mean}")
            
        row = {
            "run_file": rf.name,
            "dataset_alias": meta["dataset_alias"],
            "dataset_filename": meta["dataset_filename"],
            "controller_name": meta["controller_name"],
            "controller_display_name": meta["controller_display_name"],
            "split": meta["split"],
            "calibrated_threshold": meta.get("calibrated_threshold"),
            "events_ingested": acct["events_ingested"],
            "events_processed": acct["events_processed"],
            "events_dropped": acct["events_dropped"],
            "backpressure_activations": acct["backpressure_activations"],
            "max_queue_occupancy": acct["max_queue_occupancy"],
            "auc_roc": det["auc_roc"],
            "pr_auc": det["pr_auc"],
            "precision": cls_tau.get("precision", 0.0),
            "recall": cls_tau.get("recall", 0.0),
            "f1": cls_tau.get("f1", 0.0),
            "fpr": cls_tau.get("fpr", 0.0),
            "accuracy": cls_tau.get("accuracy", 0.0),
            "t_q_mean_ns": q_lat["mean_ns"],
            "t_q_p99_ns": q_lat["p99_ns"],
            "t_freshness_mean_ns": f_lat["mean_ns"],
            "t_freshness_p99_ns": f_lat["p99_ns"],
            "t_exec_mean_ns": e_lat["mean_ns"],
            "t_exec_p99_ns": e_lat["p99_ns"],
            "t_e2e_min_ns": e2e_lat["min_ns"],
            "t_e2e_mean_ns": e2e_lat["mean_ns"],
            "t_e2e_p50_ns": e2e_lat["p50_ns"],
            "t_e2e_p90_ns": e2e_lat["p90_ns"],
            "t_e2e_p95_ns": e2e_lat["p95_ns"],
            "t_e2e_p99_ns": e2e_lat["p99_ns"],
            "t_e2e_max_ns": e2e_lat["max_ns"],
            "t_e2e_std_ns": e2e_lat["std_ns"]
        }
        rows.append(row)
        
    df = pd.DataFrame(rows)
    out_csv = Path(args.output_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_csv, index=False)
    
    report = {
        "manifest_version": "1.0.0",
        "governing_invariants": ["INV-007", "INV-010", "INV-011"],
        "num_runs_processed": len(rows),
        "total_events_processed": int(df["events_processed"].sum()),
        "total_events_dropped": int(df["events_dropped"].sum()),
        "zero_drops_verified": bool((df["events_dropped"] == 0).all()),
        "latency_decomposition_verified": len(validation_failures) == 0,
        "validation_failures": validation_failures,
        "overall_status": "PASS" if len(validation_failures) == 0 else "FAIL"
    }
    
    rep_path = Path(args.report)
    rep_path.parent.mkdir(parents=True, exist_ok=True)
    with open(rep_path, "w") as f:
        json.dump(report, f, indent=2)
        
    print(f"Consolidated CSV written to {out_csv} ({len(df)} runs)")
    print(f"Validation report written to {rep_path} (Status: {report['overall_status']})")
    
    if report["overall_status"] != "PASS":
        sys.exit(1)

if __name__ == "__main__":
    main()
