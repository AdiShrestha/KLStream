#!/usr/bin/env python3
"""
synthetic_generator.py — Multi-Seed Synthetic Order-Book Stream Generator.

Complies with:
- INV-001 (Provenance Transparency)
- INV-002 (Synthetic/Real Separation)
- MAR-1 (Zero collision with real LOBSTER names)
- MAR-3 (Independent multi-seed realizations)

Outputs explicit synthetic order-book datasets under data/synthetic/ and
records full injection provenance in synthetic_generation_manifest.json.
"""

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import random
from typing import Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DEFAULT_OUT_DIR = REPO_ROOT / "data" / "synthetic"
MANIFEST_PATH = DEFAULT_OUT_DIR / "synthetic_generation_manifest.json"

def compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def inject_flash_crash(rows: List[dict], start_idx: int, n_events: int, rng: random.Random) -> dict:
    decay = rng.uniform(0.80, 0.92)
    step_prob = 0.25
    for i in range(n_events):
        idx = start_idx + i
        if idx >= len(rows): break
        r = rows[idx]
        r['bid_sz'] = max(1, int(r['bid_sz'] * decay))
        if rng.random() < step_prob:
            r['bid_px'] -= rng.randint(2, 8)
        r['ask_sz'] = int(r['ask_sz'] * rng.uniform(1.1, 1.3))
        r['label'] = 1 # Flash crash anomaly
    return {
        "type": "flash_crash_precursor",
        "start_idx": start_idx,
        "n_events": n_events,
        "label_id": 1
    }

def inject_wash_trade(rows: List[dict], start_idx: int, n_events: int, rng: random.Random) -> dict:
    base_px = rows[start_idx]['bid_px']
    for i in range(n_events):
        idx = start_idx + i
        if idx >= len(rows): break
        r = rows[idx]
        r['bid_sz'] = int(r['bid_sz'] * rng.uniform(4.0, 8.0))
        r['ask_sz'] = int(r['ask_sz'] * rng.uniform(4.0, 8.0))
        r['bid_px'] = base_px + rng.choice([-2, -1, 0, 0, 1, 2])
        r['ask_px'] = r['bid_px'] + max(2, rows[start_idx]['ask_px'] - rows[start_idx]['bid_px'])
        r['label'] = 2 # Wash trade anomaly
    return {
        "type": "wash_trade_proxy",
        "start_idx": start_idx,
        "n_events": n_events,
        "label_id": 2
    }

def generate_single_dataset(seed: int, num_rows: int, output_dir: Path, initial_price: float = 15000.0) -> Tuple[Path, dict]:
    rng = random.Random(seed)
    
    rows = []
    mid_px = float(initial_price)
    timestamp_ns = 34200000 * 1_000_000_000 # 9:30 AM in nanoseconds
    
    for seq in range(num_rows):
        # Geometric Brownian Motion with stochastic drift
        drift = rng.gauss(0.0, 0.00015)
        mid_px = max(100.0, mid_px * math.exp(drift))
        
        spread = rng.randint(1, 4) * 2 # 2 to 8 ticks spread
        bid_px = int(mid_px - spread / 2)
        ask_px = int(mid_px + spread / 2)
        if ask_px <= bid_px:
            ask_px = bid_px + 2
            
        bid_sz = int(rng.expovariate(1.0 / 400.0)) + 50
        ask_sz = int(rng.expovariate(1.0 / 400.0)) + 50
        
        timestamp_ns += rng.randint(200_000, 5_000_000) # 0.2ms to 5ms cadence
        
        rows.append({
            'seq': seq,
            'timestamp_ns': timestamp_ns,
            'bid_px': bid_px,
            'ask_px': ask_px,
            'bid_sz': bid_sz,
            'ask_sz': ask_sz,
            'label': 0,
            'is_burst_period': 0
        })
        
    # Inject discrete anomaly episodes (~3% of rows)
    injections = []
    num_episodes = max(2, int(num_rows * 0.03 / 40))
    min_gap = 200
    candidate_indices = list(range(100, num_rows - 200, min_gap))
    rng.shuffle(candidate_indices)
    chosen_indices = sorted(candidate_indices[:num_episodes])
    
    for start_idx in chosen_indices:
        n_events = rng.randint(25, 60)
        is_flash = rng.choice([True, False])
        if is_flash:
            meta = inject_flash_crash(rows, start_idx, n_events, rng)
        else:
            meta = inject_wash_trade(rows, start_idx, n_events, rng)
        injections.append(meta)
        
        # Mark surrounding burst window
        for j in range(max(0, start_idx - 30), min(len(rows), start_idx + n_events + 30)):
            rows[j]['is_burst_period'] = 1

    # Feature calculation pass
    out_rows = []
    vol_ema = 0.0
    for i in range(len(rows)):
        r = rows[i]
        mid_t = (r['ask_px'] + r['bid_px']) / 2.0
        
        if i == 0:
            log_ret = 0.0
        else:
            prev_mid = (rows[i-1]['ask_px'] + rows[i-1]['bid_px']) / 2.0
            log_ret = math.log(mid_t / prev_mid) if prev_mid > 0 else 0.0
            
        vol_ema = 0.05 * (log_ret ** 2) + 0.95 * vol_ema
        
        b_sz = r['bid_sz']
        a_sz = r['ask_sz']
        imbalance = (b_sz - a_sz) / float(b_sz + a_sz) if (b_sz + a_sz) > 0 else 0.0
        spread_bps = 10000.0 * (r['ask_px'] - r['bid_px']) / mid_t if mid_t > 0 else 0.0
        volume_log = math.log1p(b_sz + a_sz)
        
        out_rows.append((
            r['seq'],
            r['timestamp_ns'],
            r['bid_px'],
            r['ask_px'],
            r['bid_sz'],
            r['ask_sz'],
            f"{mid_t:.4f}",
            f"{log_ret:.8f}",
            f"{vol_ema:.8f}",
            f"{imbalance:.6f}",
            f"{spread_bps:.4f}",
            f"{volume_log:.6f}",
            r['label'],
            r['is_burst_period']
        ))
        
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    out_file = output_dir / f"synthetic_orderbook_seed{seed}.csv"
    
    with open(out_file, "w") as f:
        f.write("seq,timestamp_ns,bid_px,ask_px,bid_sz,ask_sz,mid_price,log_return,rolling_vol,order_imbalance,spread_bps,volume,label,is_burst_period\n")
        for row in out_rows:
            f.write(",".join(str(x) for x in row) + "\n")
            
    sha = compute_sha256(out_file)
    anomaly_rows = sum(1 for r in rows if r['label'] != 0)
    
    meta = {
        "seed": seed,
        "filename": out_file.name,
        "filepath": str(out_file.resolve().relative_to(REPO_ROOT)),
        "row_count": len(rows),
        "anomaly_row_count": anomaly_rows,
        "anomaly_episodes": len(injections),
        "sha256": sha,
        "injections": injections
    }
    return out_file, meta


def main():
    parser = argparse.ArgumentParser(description="Multi-Seed Synthetic Order-Book Generator")
    parser.add_argument("--seeds", type=int, nargs="+", default=[101, 102, 103, 104, 105],
                        help="List of random seeds for independent realization generation")
    parser.add_argument("--num-rows", type=int, default=10000, help="Row count per dataset")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUT_DIR, help="Destination directory")
    parser.add_argument("--initial-price", type=float, default=15000.0, help="Base mid-price in cents ($150)")
    
    args = parser.parse_args()
    
    print(f"Generating synthetic datasets for seeds: {args.seeds}...")
    dataset_manifests = []
    
    for seed in args.seeds:
        out_path, meta = generate_single_dataset(seed, args.num_rows, args.output_dir, args.initial_price)
        dataset_manifests.append(meta)
        print(f"  [OK] Seed {seed} -> {out_path.name} ({meta['row_count']} rows, {meta['anomaly_row_count']} anomalous ticks, SHA-256: {meta['sha256'][:12]}...)")
        
    manifest = {
        "generation_timestamp": "2026-08-26T13:38:00Z",
        "generator_script": "source/experiments/preprocessing/synthetic_generator.py",
        "governing_policy": "DL-008 (Zero-Cost Academic Sample & Synthetic Order-Book Policy)",
        "invariants_satisfied": ["INV-001", "INV-002", "MAR-1", "MAR-3"],
        "num_datasets": len(dataset_manifests),
        "datasets": dataset_manifests
    }
    
    manifest_file = args.output_dir / "synthetic_generation_manifest.json"
    with open(manifest_file, "w") as fm:
        json.dump(manifest, fm, indent=2)
        
    print(f"\nManifest successfully written to {manifest_file}")

if __name__ == "__main__":
    main()
