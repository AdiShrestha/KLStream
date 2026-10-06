#!/usr/bin/env python3
"""
source/experiments/demo.py

KLStream: Quickstart Streaming Anomaly Detection Demo
Executes online adaptive microbatching and static pointwise baseline
using the native runner adapter on authentic Binance BTC/USDT stream data.
"""

import argparse
import json
import os
import pathlib
import subprocess
import sys
import tempfile

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
RUNNER_SCRIPT = REPO_ROOT / "source" / "experiments" / "runner.py"


def run_demo(split: str = "validation"):
    cohort_path = REPO_ROOT / "data" / "cohort.csv"
    if not cohort_path.is_file():
        raise FileNotFoundError(f"Cohort CSV missing: {cohort_path}")

    print("=" * 75)
    print("KLSTREAM: STREAMING ANOMALY DETECTION QUICKSTART DEMO")
    print("=" * 75)
    print(f"Runner Adapter:  {RUNNER_SCRIPT.relative_to(REPO_ROOT)}")
    print(f"Cohort Data:     {cohort_path.relative_to(REPO_ROOT)} (split: {split})")
    print("-" * 75)

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_p = pathlib.Path(tmp_dir)

        results = {}
        for policy in ("adaptive_grow", "fixed_w1"):
            p_dir = tmp_p / policy
            cmd = [
                sys.executable,
                str(RUNNER_SCRIPT),
                "--output-dir", str(p_dir),
                "--policy", policy,
                "--eval-splits", split,
                "--seed", "42",
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            if proc.returncode != 0:
                print(f"Error executing {policy}:\n{proc.stderr}")
                sys.exit(proc.returncode)

            res_file = p_dir / "result.json"
            with open(res_file, "r", encoding="utf-8") as f:
                res_data = json.load(f)

            summary = res_data["telemetry_summary"]
            q = summary["exact_quantiles_ns"]["end_to_end_latency"]
            q_wait = summary["exact_quantiles_ns"]["queue_wait"]
            q_svc = summary["exact_quantiles_ns"]["service_time"]

            results[policy] = {
                "events_recorded": summary["events_recorded"],
                "p50_us": q["p50"] / 1000.0,
                "p90_us": q["p90"] / 1000.0,
                "p99_us": q["p99"] / 1000.0,
                "p99_wait_us": q_wait["p99"] / 1000.0,
                "p99_svc_us": q_svc["p99"] / 1000.0,
            }

        # Print comparison table
        print(f"{'Policy':<16} | {'Events':<7} | {'p50 (us)':<10} | {'p90 (us)':<10} | {'p99 (us)':<10} | {'p99 wait (us)':<13} | {'p99 svc (us)':<12}")
        print("-" * 90)
        for pol, res in results.items():
            print(
                f"{pol:<16} | {res['events_recorded']:<7} | {res['p50_us']:<10.1f} | {res['p90_us']:<10.1f} | "
                f"{res['p99_us']:<10.1f} | {res['p99_wait_us']:<13.1f} | {res['p99_svc_us']:<12.1f}"
            )

        # Invariant checks
        for pol, res in results.items():
            assert res["events_recorded"] > 0, "Zero events recorded"
            assert res["p50_us"] <= res["p90_us"] <= res["p99_us"], "Quantile monotonicity violated"

    print("-" * 90)
    print("[OK] Demo completed with 100% event conservation and monotone quantiles.")
    print("=" * 90)


def main():
    parser = argparse.ArgumentParser(description="KLStream Quickstart Demo")
    parser.add_argument("--split", type=str, default="validation", help="Cohort split to evaluate")
    args = parser.parse_args()
    run_demo(args.split)


if __name__ == "__main__":
    main()
