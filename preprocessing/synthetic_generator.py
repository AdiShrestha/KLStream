#!/usr/bin/env python3
"""
synthetic_generator.py — Fallback synthetic order-flow generator.
Generates a mock LOBSTER-like orderbook with geometric Brownian motion mid-price,
injects anomalies, computes features, and writes the final CSV for the pipeline.
"""
import math
import random
import numpy as np
import pandas as pd
import os

def inject_flash_crash_precursor(rows, start_idx, n_events, rng):
    decay = rng.uniform(0.85, 0.95)
    step_prob = 0.15
    for i in range(n_events):
        r = rows[start_idx + i]
        r['bid_sz'] = max(1, int(r['bid_sz'] * decay))
        if rng.random() < step_prob:
            r['bid_px'] -= 1
        r['ask_sz'] = int(r['ask_sz'] * rng.uniform(1.0, 1.05))
        r['label'] = 1
    return rows

def inject_wash_trade_proxy(rows, start_idx, n_events, rng):
    base_px = rows[start_idx]['bid_px']
    for i in range(n_events):
        r = rows[start_idx + i]
        r['bid_sz'] = int(r['bid_sz'] * rng.uniform(3.0, 6.0))
        r['ask_sz'] = int(r['ask_sz'] * rng.uniform(3.0, 6.0))
        r['bid_px'] = base_px + rng.choice([-1, 0, 0, 0, 1])
        r['ask_px'] = r['bid_px'] + (rows[start_idx]['ask_px'] - rows[start_idx]['bid_px'])
        r['label'] = 2
    return rows

def main():
    N_EVENTS = 100000
    rng = random.Random(42)
    
    # 1. Generate base calm orderbook (geometric Brownian motion)
    rows = []
    mid_px = 15000.0 # $150.00
    
    timestamp = 34200000 * 1_000_000_000 # 9:30 AM in nanoseconds
    
    for i in range(N_EVENTS):
        # GBM step
        mid_px = mid_px * math.exp(rng.gauss(0, 0.0001))
        
        spread = rng.randint(1, 5) * 2 # 2 to 10 cents
        bid_px = int(mid_px - spread/2)
        ask_px = int(mid_px + spread/2)
        
        bid_sz = int(rng.expovariate(1/500)) + 100
        ask_sz = int(rng.expovariate(1/500)) + 100
        
        timestamp += rng.randint(100_000, 10_000_000) # 0.1ms to 10ms
        
        rows.append({
            'seq': i,
            'timestamp_ns': timestamp,
            'bid_px': bid_px,
            'ask_px': ask_px,
            'bid_sz': bid_sz,
            'ask_sz': ask_sz,
            'label': 0,
            'is_burst_period': 0
        })
        
    # 2. Inject anomalies
    num_anomalies = int(N_EVENTS * 0.03 / 50) # Approx 3% anomalies, each 50 length
    gap = 500
    
    indices = list(range(1000, N_EVENTS - 1000, gap))
    rng.shuffle(indices)
    injection_indices = indices[:num_anomalies]
    
    for idx in injection_indices:
        n_events = rng.randint(20, 80)
        is_flash = rng.choice([True, False])
        if is_flash:
            inject_flash_crash_precursor(rows, idx, n_events, rng)
        else:
            inject_wash_trade_proxy(rows, idx, n_events, rng)
            
        # Mark burst period (just for simulation purposes around anomaly)
        for j in range(idx - 100, idx + n_events + 100):
            if j < len(rows):
                rows[j]['is_burst_period'] = 1

    # 3. Compute Features
    out_rows = []
    vol_t = 0.0
    for i in range(len(rows)):
        r = rows[i]
        
        mid_t = (r['ask_px'] + r['bid_px']) / 2.0
        
        if i == 0:
            log_return = 0.0
        else:
            prev_mid = (rows[i-1]['ask_px'] + rows[i-1]['bid_px']) / 2.0
            log_return = math.log(mid_t / prev_mid) if prev_mid > 0 else 0.0
            
        vol_t = 0.05 * (log_return ** 2) + 0.95 * vol_t
        
        bid_sz = r['bid_sz']
        ask_sz = r['ask_sz']
        
        if bid_sz + ask_sz > 0:
            order_imbalance = (bid_sz - ask_sz) / float(bid_sz + ask_sz)
        else:
            order_imbalance = 0.0
            
        spread_bps = 10000.0 * (r['ask_px'] - r['bid_px']) / mid_t if mid_t > 0 else 0.0
        volume_log = math.log1p(bid_sz + ask_sz)
        
        out_rows.append({
            'seq': r['seq'],
            'timestamp_ns': r['timestamp_ns'],
            'mid_price': mid_t,
            'log_return': log_return,
            'rolling_vol': vol_t,
            'order_imbalance': order_imbalance,
            'spread_bps': spread_bps,
            'volume': volume_log,
            'label': r['label'],
            'is_burst_period': r['is_burst_period']
        })
        
    df = pd.DataFrame(out_rows)
    out_dir = "data/replay"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "replay_AAPL_20120621.csv")
    df.to_csv(out_path, index=False)
    print(f"Generated synthetic replay file at {out_path} ({len(df)} rows)")

if __name__ == "__main__":
    main()
