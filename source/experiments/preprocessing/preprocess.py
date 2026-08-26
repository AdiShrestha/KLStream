#!/usr/bin/env python3
"""
preprocess.py — Schema-Validated Preprocessing and Feature Engineering.

Complies with:
- INV-004 (Provenance Continuity & Schema Validation)
- MAR-X2 (Explicit Ground Truth Injection Manifest)
- MAR-1 (Disjoint Output Paths)
"""

import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SYNTHETIC_DIR = REPO_ROOT / "data" / "synthetic"
ACADEMIC_DIR = REPO_ROOT / "data" / "raw" / "academic_sample"
PROCESSED_DIR = REPO_ROOT / "data" / "processed"
INJECTION_MANIFEST_PATH = PROCESSED_DIR / "injection_manifest.json"

REQUIRED_PROCESSED_COLUMNS = [
    "seq", "timestamp_ns", "bid_px", "ask_px", "bid_sz", "ask_sz",
    "mid_price", "spread", "spread_bps", "log_return", "rolling_vol",
    "order_imbalance", "microprice", "volume", "is_anomaly", "anomaly_type", "is_burst_period"
]

def compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def validate_and_process_synthetic(csv_path: Path) -> Tuple[List[dict], List[dict]]:
    """
    Validates synthetic order-book CSV and computes derived features.
    """
    rows = []
    injections = []
    
    with open(csv_path, "r", newline="") as f:
        reader = csv.DictReader(f)
        req_fields = {"seq", "timestamp_ns", "bid_px", "ask_px", "bid_sz", "ask_sz"}
        if not req_fields.issubset(set(reader.fieldnames or [])):
            raise ValueError(f"Missing required columns in {csv_path}. Expected at least {req_fields}")
            
        last_ts = -1
        last_mid = None
        vol_ema = 0.0
        
        current_anomaly = None
        
        for idx, row in enumerate(reader):
            try:
                seq = int(row["seq"])
                ts_ns = int(row["timestamp_ns"])
                bid_px = float(row["bid_px"])
                ask_px = float(row["ask_px"])
                bid_sz = int(row["bid_sz"])
                ask_sz = int(row["ask_sz"])
                label = int(row.get("label", 0))
                is_burst = int(row.get("is_burst_period", 0))
            except (ValueError, KeyError) as e:
                raise ValueError(f"Malformed row {idx} in {csv_path}: {e}")
                
            # Fail-closed domain validation
            if bid_px <= 0 or ask_px <= 0:
                raise ValueError(f"Non-positive price at row {idx}: bid={bid_px}, ask={ask_px}")
            if ask_px <= bid_px:
                raise ValueError(f"Crossed/locked book at row {idx}: ask={ask_px} <= bid={bid_px}")
            if bid_sz < 0 or ask_sz < 0:
                raise ValueError(f"Negative size at row {idx}: bid_sz={bid_sz}, ask_sz={ask_sz}")
            if ts_ns < last_ts:
                raise ValueError(f"Non-monotonic timestamp at row {idx}: {ts_ns} < {last_ts}")
            last_ts = ts_ns
            
            mid = (ask_px + bid_px) / 2.0
            spread = ask_px - bid_px
            spread_bps = 10000.0 * spread / mid
            
            if last_mid is None or last_mid <= 0:
                log_ret = 0.0
            else:
                log_ret = math.log(mid / last_mid)
            last_mid = mid
            
            vol_ema = 0.05 * (log_ret ** 2) + 0.95 * vol_ema
            
            tot_sz = bid_sz + ask_sz
            imbalance = (bid_sz - ask_sz) / float(tot_sz) if tot_sz > 0 else 0.0
            microprice = (bid_px * ask_sz + ask_px * bid_sz) / float(tot_sz) if tot_sz > 0 else mid
            vol_log = math.log1p(tot_sz)
            
            is_anom = 1 if label != 0 else 0
            anom_type = "none"
            if label == 1:
                anom_type = "flash_crash_precursor"
            elif label == 2:
                anom_type = "wash_trade_proxy"
            elif label != 0:
                anom_type = f"anomaly_label_{label}"
                
            # Anomaly episode span tracking
            if is_anom:
                if current_anomaly is None or current_anomaly["anomaly_type"] != anom_type:
                    if current_anomaly is not None:
                        injections.append(current_anomaly)
                    current_anomaly = {
                        "dataset": csv_path.name,
                        "anomaly_type": anom_type,
                        "start_seq": seq,
                        "end_seq": seq,
                        "start_timestamp_ns": ts_ns,
                        "end_timestamp_ns": ts_ns,
                        "count": 1
                    }
                else:
                    current_anomaly["end_seq"] = seq
                    current_anomaly["end_timestamp_ns"] = ts_ns
                    current_anomaly["count"] += 1
            else:
                if current_anomaly is not None:
                    injections.append(current_anomaly)
                    current_anomaly = None
                    
            rows.append({
                "seq": seq,
                "timestamp_ns": ts_ns,
                "bid_px": bid_px,
                "ask_px": ask_px,
                "bid_sz": bid_sz,
                "ask_sz": ask_sz,
                "mid_price": round(mid, 4),
                "spread": round(spread, 4),
                "spread_bps": round(spread_bps, 4),
                "log_return": round(log_ret, 8),
                "rolling_vol": round(vol_ema, 8),
                "order_imbalance": round(imbalance, 6),
                "microprice": round(microprice, 4),
                "volume": round(vol_log, 6),
                "is_anomaly": is_anom,
                "anomaly_type": anom_type,
                "is_burst_period": is_burst
            })
            
        if current_anomaly is not None:
            injections.append(current_anomaly)
            
    return rows, injections

def validate_and_process_lobster(msg_file: Path, ob_file: Path) -> Tuple[List[dict], List[dict]]:
    """
    Validates and processes raw LOBSTER Level-1 files.
    """
    rows = []
    with open(msg_file, "r") as fm, open(ob_file, "r") as fo:
        m_reader = csv.reader(fm)
        o_reader = csv.reader(fo)
        
        last_ts = -1
        last_mid = None
        vol_ema = 0.0
        
        for idx, (m_row, o_row) in enumerate(zip(m_reader, o_reader)):
            if len(m_row) < 6 or len(o_row) < 4:
                raise ValueError(f"Incomplete row at index {idx}")
                
            t_sec = float(m_row[0])
            ts_ns = int(t_sec * 1_000_000_000)
            seq = int(m_row[2])
            
            ask_px = float(o_row[0]) / 100.0 # Convert ticks/cents to dollars
            ask_sz = int(o_row[1])
            bid_px = float(o_row[2]) / 100.0
            bid_sz = int(o_row[3])
            
            if bid_px <= 0 or ask_px <= 0:
                raise ValueError(f"Non-positive price in LOBSTER row {idx}")
            if ask_px <= bid_px:
                raise ValueError(f"Crossed book in LOBSTER row {idx}: ask={ask_px} <= bid={bid_px}")
            if ts_ns < last_ts:
                raise ValueError(f"Non-monotonic timestamp in LOBSTER row {idx}")
            last_ts = ts_ns
            
            mid = (ask_px + bid_px) / 2.0
            spread = ask_px - bid_px
            spread_bps = 10000.0 * spread / mid
            
            if last_mid is None or last_mid <= 0:
                log_ret = 0.0
            else:
                log_ret = math.log(mid / last_mid)
            last_mid = mid
            
            vol_ema = 0.05 * (log_ret ** 2) + 0.95 * vol_ema
            tot_sz = bid_sz + ask_sz
            imbalance = (bid_sz - ask_sz) / float(tot_sz) if tot_sz > 0 else 0.0
            microprice = (bid_px * ask_sz + ask_px * bid_sz) / float(tot_sz) if tot_sz > 0 else mid
            vol_log = math.log1p(tot_sz)
            
            rows.append({
                "seq": seq,
                "timestamp_ns": ts_ns,
                "bid_px": bid_px,
                "ask_px": ask_px,
                "bid_sz": bid_sz,
                "ask_sz": ask_sz,
                "mid_price": round(mid, 4),
                "spread": round(spread, 4),
                "spread_bps": round(spread_bps, 4),
                "log_return": round(log_ret, 8),
                "rolling_vol": round(vol_ema, 8),
                "order_imbalance": round(imbalance, 6),
                "microprice": round(microprice, 4),
                "volume": round(vol_log, 6),
                "is_anomaly": 0,
                "anomaly_type": "none",
                "is_burst_period": 0
            })
            
    return rows, []

def write_processed_csv(rows: List[dict], out_file: Path) -> str:
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=REQUIRED_PROCESSED_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return compute_sha256(out_file)

def main():
    parser = argparse.ArgumentParser(description="Preprocess and Feature Engineering Pipeline")
    parser.add_argument("--input-dir", type=Path, default=SYNTHETIC_DIR, help="Synthetic input directory")
    parser.add_argument("--academic-dir", type=Path, default=ACADEMIC_DIR, help="Academic input directory")
    parser.add_argument("--output-dir", type=Path, default=PROCESSED_DIR, help="Output processed directory")
    
    args = parser.parse_args()
    args.output_dir = args.output_dir.resolve()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    
    all_injections = []
    processed_summary = []
    
    # 1. Process all synthetic datasets
    synth_files = sorted(args.input_dir.glob("synthetic_orderbook_seed*.csv"))
    print(f"Found {len(synth_files)} synthetic datasets in {args.input_dir}...")
    
    for sf in synth_files:
        seed_part = sf.stem.replace("synthetic_orderbook_", "")
        out_name = f"replay_synthetic_{seed_part}.csv"
        out_file = args.output_dir / out_name
        
        rows, injections = validate_and_process_synthetic(sf)
        sha = write_processed_csv(rows, out_file)
        for inj in injections:
            inj["processed_file"] = out_name
            all_injections.append(inj)
            
        processed_summary.append({
            "source": sf.name,
            "processed_file": out_name,
            "row_count": len(rows),
            "sha256": sha,
            "anomalies_injected": len(injections)
        })
        print(f"  [OK] Processed {sf.name} -> {out_name} ({len(rows)} rows, {len(injections)} anomaly episodes)")

    # 2. Process academic sample if present
    msg_files = list(args.academic_dir.glob("*_message_1.csv"))
    for mf in msg_files:
        prefix = mf.name.replace("_message_1.csv", "")
        ob_file = args.academic_dir / f"{prefix}_orderbook_1.csv"
        if ob_file.exists():
            out_name = f"replay_academic_sample_{prefix}.csv"
            out_file = args.output_dir / out_name
            rows, _ = validate_and_process_lobster(mf, ob_file)
            sha = write_processed_csv(rows, out_file)
            processed_summary.append({
                "source": f"{mf.name} + {ob_file.name}",
                "processed_file": out_name,
                "row_count": len(rows),
                "sha256": sha,
                "anomalies_injected": 0
            })
            print(f"  [OK] Processed academic sample {prefix} -> {out_name} ({len(rows)} rows)")

    # 3. Write injection manifest
    manifest_data = {
        "manifest_version": "1.0.0",
        "governing_invariants": ["INV-004", "MAR-X2"],
        "total_injection_episodes": len(all_injections),
        "processed_datasets": processed_summary,
        "injections": all_injections
    }
    
    with open(args.output_dir / "injection_manifest.json", "w") as fm:
        json.dump(manifest_data, fm, indent=2)
        
    print(f"\nPreprocessing complete! Injection manifest written to {args.output_dir / 'injection_manifest.json'}")

if __name__ == "__main__":
    main()
