#!/usr/bin/env python3
"""
reality_gate.py — Automated Reality Gate Quality and Domain Verification Engine.

Enforces:
- SVI-001 (Reality Gate Domain Verification)
- 6 Formal Market Checks:
  1. RG-POS: strictly positive bid/ask prices (> 0)
  2. RG-SPREAD: non-negative bid-ask spread (ask >= bid)
  3. RG-SIZE: strictly positive bid/ask sizes (> 0)
  4. RG-TIME: monotonic event timestamps (t_i <= t_{i+1})
  5. RG-BOUNDS: realistic price scale bounds ($1.0 to $10,000.0)
  6. RG-LABELS: binary label integrity (is_anomaly in {0, 1})
"""

import argparse
import csv
import json
import os
from pathlib import Path
from typing import Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
PROCESSED_DIR = REPO_ROOT / "data" / "processed"
DEFAULT_REPORT_PATH = REPO_ROOT / "project" / "chunks" / "chunk04" / "reality_gate_report.json"

def verify_dataset(csv_path: Path) -> dict:
    checks = {
        "RG-POS": {"name": "Strictly Positive Prices", "passed": True, "violations": 0, "first_violation": None},
        "RG-SPREAD": {"name": "Non-Negative Spread", "passed": True, "violations": 0, "first_violation": None},
        "RG-SIZE": {"name": "Positive Queue Sizes", "passed": True, "violations": 0, "first_violation": None},
        "RG-TIME": {"name": "Monotonic Timestamps", "passed": True, "violations": 0, "first_violation": None},
        "RG-BOUNDS": {"name": "Realistic Price Scale Bounds", "passed": True, "violations": 0, "first_violation": None},
        "RG-LABELS": {"name": "Binary Label Integrity", "passed": True, "violations": 0, "first_violation": None},
    }
    
    row_count = 0
    with open(csv_path, "r", newline="") as f:
        reader = csv.DictReader(f)
        last_ts = -1
        
        for idx, r in enumerate(reader):
            row_count += 1
            ts = int(r["timestamp_ns"])
            bid_px = float(r["bid_px"])
            ask_px = float(r["ask_px"])
            bid_sz = int(r["bid_sz"])
            ask_sz = int(r["ask_sz"])
            mid_px = float(r["mid_price"])
            is_anom = int(r["is_anomaly"])
            
            # Check 1: RG-POS
            if bid_px <= 0 or ask_px <= 0:
                checks["RG-POS"]["passed"] = False
                checks["RG-POS"]["violations"] += 1
                if checks["RG-POS"]["first_violation"] is None:
                    checks["RG-POS"]["first_violation"] = f"Row {idx}: bid={bid_px}, ask={ask_px}"
                    
            # Check 2: RG-SPREAD
            if ask_px < bid_px:
                checks["RG-SPREAD"]["passed"] = False
                checks["RG-SPREAD"]["violations"] += 1
                if checks["RG-SPREAD"]["first_violation"] is None:
                    checks["RG-SPREAD"]["first_violation"] = f"Row {idx}: ask={ask_px} < bid={bid_px}"
                    
            # Check 3: RG-SIZE
            if bid_sz <= 0 or ask_sz <= 0:
                checks["RG-SIZE"]["passed"] = False
                checks["RG-SIZE"]["violations"] += 1
                if checks["RG-SIZE"]["first_violation"] is None:
                    checks["RG-SIZE"]["first_violation"] = f"Row {idx}: bid_sz={bid_sz}, ask_sz={ask_sz}"
                    
            # Check 4: RG-TIME
            if ts < last_ts:
                checks["RG-TIME"]["passed"] = False
                checks["RG-TIME"]["violations"] += 1
                if checks["RG-TIME"]["first_violation"] is None:
                    checks["RG-TIME"]["first_violation"] = f"Row {idx}: {ts} < {last_ts}"
            last_ts = ts
            
            # Check 5: RG-BOUNDS ($1.00 to $10,000.00 / 100 to 1,000,000 cents)
            if mid_px < 1.0 or mid_px > 1000000.0:
                checks["RG-BOUNDS"]["passed"] = False
                checks["RG-BOUNDS"]["violations"] += 1
                if checks["RG-BOUNDS"]["first_violation"] is None:
                    checks["RG-BOUNDS"]["first_violation"] = f"Row {idx}: mid_price={mid_px} out of range [1.0, 1000000.0]"
                    
            # Check 6: RG-LABELS
            if is_anom not in (0, 1):
                checks["RG-LABELS"]["passed"] = False
                checks["RG-LABELS"]["violations"] += 1
                if checks["RG-LABELS"]["first_violation"] is None:
                    checks["RG-LABELS"]["first_violation"] = f"Row {idx}: is_anomaly={is_anom} not in {{0, 1}}"
                    
    dataset_passed = all(c["passed"] for c in checks.values())
    return {
        "dataset": csv_path.name,
        "row_count": row_count,
        "status": "PASS" if dataset_passed else "FAIL",
        "checks": checks
    }

def run_reality_gate(data_dir: Path, report_path: Path) -> bool:
    csv_files = sorted(data_dir.glob("replay_*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No processed replay files found in {data_dir}")
        
    print(f"Executing Reality Gate across {len(csv_files)} datasets in {data_dir}...")
    dataset_results = []
    all_passed = True
    
    for cf in csv_files:
        res = verify_dataset(cf)
        dataset_results.append(res)
        status_tag = "[PASS]" if res["status"] == "PASS" else "[FAIL]"
        print(f"  {status_tag} {cf.name} ({res['row_count']} rows)")
        if res["status"] != "PASS":
            all_passed = False
            for k, c in res["checks"].items():
                if not c["passed"]:
                    print(f"    - {k} ({c['name']}): {c['violations']} violations. First: {c['first_violation']}")
                    
    report_data = {
        "gate_version": "1.0.0",
        "governing_invariant": "SVI-001",
        "overall_verdict": "PASS" if all_passed else "FAIL",
        "num_datasets_evaluated": len(dataset_results),
        "all_datasets_passed": all_passed,
        "results": dataset_results
    }
    
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w") as f:
        json.dump(report_data, f, indent=2)
        
    print(f"\nReality Gate Report written to {report_path}")
    print(f"OVERALL VERDICT: {'PASS' if all_passed else 'FAIL'}")
    return all_passed

def main():
    parser = argparse.ArgumentParser(description="Automated Reality Gate Verification Engine")
    parser.add_argument("--data-dir", type=Path, default=PROCESSED_DIR, help="Directory containing processed CSV files")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH, help="Output JSON report path")
    
    args = parser.parse_args()
    success = run_reality_gate(args.data_dir.resolve(), args.report.resolve())
    if not success:
        exit(1)

if __name__ == "__main__":
    main()
