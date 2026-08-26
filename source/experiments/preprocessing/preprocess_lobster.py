#!/usr/bin/env python3
"""
preprocess_lobster.py — Convert raw LOBSTER message+orderbook files into
a single replay-ready CSV with engineered features and injected anomaly
labels. Run once per ticker/day. Output feeds klstream's TickSource directly.

Usage:
    python preprocess_lobster.py \
        --message AAPL_2012-06-21_34200000_57600000_message_1.csv \
        --orderbook AAPL_2012-06-21_34200000_57600000_orderbook_1.csv \
        --out replay_AAPL_20120621.csv \
        --seed 42
"""
import argparse
import math
import random
import pandas as pd
import numpy as np

MSG_COLS = ["time_sec", "event_type", "order_id", "size", "price", "direction"]
OB_COLS  = ["ask_px", "ask_sz", "bid_px", "bid_sz"]   # NumLevels=1

# Event type 7 = trading halt; these rows carry no real book update.
DROP_EVENT_TYPES = {7}


def load(message_path, orderbook_path):
    msg = pd.read_csv(message_path, header=None, names=MSG_COLS)
    ob  = pd.read_csv(orderbook_path, header=None, names=OB_COLS)
    assert len(msg) == len(ob), "message/orderbook row count mismatch — corrupted download"
    df = pd.concat([msg, ob], axis=1)
    df = df[~df["event_type"].isin(DROP_EVENT_TYPES)].reset_index(drop=True)
    # LOBSTER prices are dollars * 10000 -> convert to cents (integers) for
    # the synthetic injectors in Section 9, then back to dollars for output.
    for c in ("price", "ask_px", "bid_px"):
        df[c] = df[c] / 100.0   # dollars * 100 == cents
    return df


def inject_flash_crash_precursor(df, start_idx, n_events, rng):
    decay = rng.uniform(0.85, 0.95)
    step_prob = 0.15
    for i in range(n_events):
        idx = start_idx + i
        df.at[idx, "bid_sz"] = max(1, int(df.at[idx, "bid_sz"] * decay))
        if rng.random() < step_prob:
            df.at[idx, "bid_px"] -= 1
        df.at[idx, "ask_sz"] = int(df.at[idx, "ask_sz"] * rng.uniform(1.0, 1.05))
        df.at[idx, "label"] = 1


def inject_wash_trade_proxy(df, start_idx, n_events, rng):
    base_px = df.at[start_idx, "bid_px"]
    base_spread = df.at[start_idx, "ask_px"] - df.at[start_idx, "bid_px"]
    for i in range(n_events):
        idx = start_idx + i
        df.at[idx, "bid_sz"] = int(df.at[idx, "bid_sz"] * rng.uniform(3.0, 6.0))
        df.at[idx, "ask_sz"] = int(df.at[idx, "ask_sz"] * rng.uniform(3.0, 6.0))
        df.at[idx, "bid_px"] = base_px + rng.choice([-1, 0, 0, 0, 1])
        df.at[idx, "ask_px"] = df.at[idx, "bid_px"] + base_spread
        df.at[idx, "label"] = 2


def inject_anomalies(df, rng, target_fraction=0.03, min_gap=500, max_window=256):
    n = len(df)
    df["label"] = 0
    n_target = int(n * target_fraction)
    placed = 0
    attempts = 0
    occupied = np.zeros(n, dtype=bool)
    while placed < n_target and attempts < n_target * 20:
        attempts += 1
        start = rng.randrange(min_gap, n - max_window - min_gap)
        n_events = rng.randint(20, 80)
        window = slice(start - min_gap, start + n_events + min_gap)
        if occupied[window].any():
            continue
        occupied[start:start + n_events] = True
        if rng.random() < 0.5:
            inject_flash_crash_precursor(df, start, n_events, rng)
        else:
            inject_wash_trade_proxy(df, start, n_events, rng)
        placed += n_events
    return df


def mark_burst_periods(df, rng, n_bursts=4, burst_len_events=2000):
    """Marks dense replay-rate segments for the bursty-source experiments
    (Section 25, reusing the original KLStream bursty-source pattern)."""
    n = len(df)
    df["is_burst_period"] = 0
    for _ in range(n_bursts):
        start = rng.randrange(0, max(1, n - burst_len_events))
        df.loc[start:start + burst_len_events, "is_burst_period"] = 1
    return df


def compute_features(df):
    mid = (df["ask_px"] + df["bid_px"]) / 2.0
    log_return = np.log(mid).diff().fillna(0.0)

    beta = 0.05
    rolling_vol = np.zeros(len(df))
    v = 0.0
    r2 = (log_return ** 2).values
    for i in range(len(df)):
        v = beta * r2[i] + (1 - beta) * v
        rolling_vol[i] = v

    order_imbalance = (df["bid_sz"] - df["ask_sz"]) / (df["bid_sz"] + df["ask_sz"]).clip(lower=1)
    spread_bps = 10000.0 * (df["ask_px"] - df["bid_px"]) / mid
    volume = np.log1p(df["bid_sz"] + df["ask_sz"])

    out = pd.DataFrame({
        "seq": np.arange(len(df)),
        "timestamp_ns": (df["time_sec"] * 1e9).astype(np.int64),
        "mid_price": mid,
        "log_return": log_return,
        "rolling_vol": rolling_vol,
        "order_imbalance": order_imbalance,
        "spread_bps": spread_bps,
        "volume": volume,
        "label": df["label"],
        "is_burst_period": df["is_burst_period"],
    })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--message", required=True)
    ap.add_argument("--orderbook", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    df = load(args.message, args.orderbook)
    df = inject_anomalies(df, rng)
    df = mark_burst_periods(df, rng)
    out = compute_features(df)
    out.to_csv(args.out, index=False)

    n_anom = (out["label"] != 0).sum()
    print(f"Wrote {len(out)} events to {args.out}")
    print(f"  Flash-crash-precursor events: {(out['label']==1).sum()}")
    print(f"  Wash-trade-proxy events:      {(out['label']==2).sum()}")
    print(f"  Total anomalous fraction:     {n_anom/len(out):.3%}")


if __name__ == "__main__":
    main()
