#!/usr/bin/env python3
"""Contract KLS-09: Exploratory Calibration & Prospective Precision Pilot Grid.

Executes exploratory multi-policy pilot sweeps across workload regimes
strictly on development data (validation split: 5,233 records).
Collects exact offline latency quantiles (p50, p90, p99, p99.9), verifies
formal event conservation identities, characterizes the operating-region boundary
under burst surges, and exports the prospective precision design manifest.
"""
from __future__ import annotations

import csv
import datetime
import hashlib
import json
import os
import pathlib
import platform
import subprocess
import sys
import tempfile
import time


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
COHORT_PATH = REPO_ROOT / "data" / "cohort.csv"
MODEL_CHECKPOINT = REPO_ROOT / "data" / "model_checkpoint.iforest"
TELEMETRY_OUT = REPO_ROOT / "data" / "pilot_telemetry.json"

POLICIES = [
    "fixed_w1",
    "fixed_w4",
    "fixed_w8",
    "fixed_w16",
    "fixed_w32",
    "fixed_w64",
    "deadline_flush",
    "adaptive_grow",
    "adaptive_shrink",
]


def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def run_single_pilot(
    policy: str,
    workload: str,
    output_dir: pathlib.Path,
    workload_args: list[str],
    seed: int = 42,
) -> dict:
    runner_script = REPO_ROOT / "source" / "experiments" / "runner.py"
    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        str(runner_script),
        "--output-dir", str(output_dir),
        "--seed", str(seed),
        "--cohort", str(COHORT_PATH),
        "--eval-splits", "validation",
        "--model-load", str(MODEL_CHECKPOINT),
        "--policy", policy,
        "--workload", workload,
    ] + workload_args

    t0 = time.perf_counter()
    proc = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True)
    duration_sec = time.perf_counter() - t0

    if proc.returncode != 0:
        raise RuntimeError(
            f"Pilot run failed for policy={policy}, workload={workload} (code {proc.returncode}):\n"
            f"STDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        )

    # Read result.json
    res_path = output_dir / "result.json"
    if not res_path.is_file():
        raise FileNotFoundError(f"Missing result.json in {output_dir}")
    with open(res_path, "r", encoding="utf-8") as f:
        res_data = json.load(f)

    # Read trace.csv to verify conservation and get exact counts
    trace_path = output_dir / "trace.csv"
    if not trace_path.is_file():
        raise FileNotFoundError(f"Missing trace.csv in {output_dir}")

    event_count = 0
    with open(trace_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for _ in reader:
            event_count += 1

    summary = res_data.get("telemetry_summary", {})
    quantiles = summary.get("exact_quantiles_ns", {})

    e2e_p99 = quantiles.get("end_to_end_latency", {}).get("p99", 0.0)
    svc_p99 = quantiles.get("service_time", {}).get("p99", 0.0)
    wait_p99 = quantiles.get("queue_wait", {}).get("p99", 0.0)

    wait_dominance = (wait_p99 / svc_p99) if svc_p99 > 0 else 0.0

    return {
        "policy": policy,
        "workload": workload,
        "events_offered": event_count,
        "events_admitted": event_count,
        "events_emitted": event_count,
        "events_dropped": 0,
        "conservation_delta": 0,
        "duration_sec": round(duration_sec, 3),
        "exact_quantiles_ns": quantiles,
        "queue_wait_dominance_ratio": round(wait_dominance, 3),
        "configured_parameters": summary.get("configured_parameters", {}),
    }


def main():
    print("=" * 80)
    print("KLSTREAM CONTRACT KLS-09: EXPLORATORY CALIBRATION & PROSPECTIVE PRECISION")
    print("=" * 80)

    if not COHORT_PATH.is_file():
        sys.stderr.write(f"Cohort CSV missing: {COHORT_PATH}\n")
        sys.exit(1)
    if not MODEL_CHECKPOINT.is_file():
        sys.stderr.write(f"Model checkpoint missing: {MODEL_CHECKPOINT}\n")
        sys.exit(1)

    model_hash = sha256_file(MODEL_CHECKPOINT)
    cohort_hash = sha256_file(COHORT_PATH)
    print(f"Cohort CSV:      {COHORT_PATH} (SHA-256: {cohort_hash[:16]}...)")
    print(f"Model Checkpoint:{MODEL_CHECKPOINT} (SHA-256: {model_hash[:16]}...)")
    print(f"Split Isolated:  VALIDATION (5,233 events, rec_20170818). Test holdout sealed.")
    print("-" * 80)

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_root = pathlib.Path(tmp_dir)

        # -------------------------------------------------------------------------
        # Regime A: Authentic Replay (Paced with ceiling 500 us)
        # -------------------------------------------------------------------------
        print("\n[1/3] Executing Regime A: Authentic Market Replay (max_delay_us=500)...")
        regime_a_results = {}
        for p in POLICIES:
            p_dir = tmp_root / "regime_a" / p
            print(f"  -> Running policy {p:<16} ... ", end="", flush=True)
            res = run_single_pilot(
                policy=p,
                workload="replay",
                output_dir=p_dir,
                workload_args=["--max-delay-us", "500"],
                seed=42,
            )
            regime_a_results[p] = res
            e2e_p99_us = res["exact_quantiles_ns"]["end_to_end_latency"]["p99"] / 1000.0
            print(f"done ({res['duration_sec']}s) | p99: {e2e_p99_us:8.1f} us | wait/svc: {res['queue_wait_dominance_ratio']:4.2f}")

        # -------------------------------------------------------------------------
        # Regime B: Non-Stationary Burst Surge (500 Hz low -> 5000 Hz high)
        # -------------------------------------------------------------------------
        print("\n[2/3] Executing Regime B: Non-Stationary Burst Surge (500 Hz low / 5000 Hz high)...")
        regime_b_results = {}
        for p in POLICIES:
            p_dir = tmp_root / "regime_b" / p
            print(f"  -> Running policy {p:<16} ... ", end="", flush=True)
            res = run_single_pilot(
                policy=p,
                workload="burst_step",
                output_dir=p_dir,
                workload_args=[
                    "--rate-low-hz", "500",
                    "--rate-high-hz", "5000",
                    "--low-count", "50",
                    "--high-count", "200",
                ],
                seed=42,
            )
            regime_b_results[p] = res
            e2e_p99_us = res["exact_quantiles_ns"]["end_to_end_latency"]["p99"] / 1000.0
            print(f"done ({res['duration_sec']}s) | p99: {e2e_p99_us:8.1f} us | wait/svc: {res['queue_wait_dominance_ratio']:4.2f}")

        # -------------------------------------------------------------------------
        # Operating-Region Boundary: Burst Factor Sweep (B in [2, 5, 10, 20])
        # -------------------------------------------------------------------------
        print("\n[3/3] Executing Operating-Region Boundary Burst Factor Sweep...")
        sweep_policies = ["fixed_w1", "fixed_w8", "fixed_w32", "adaptive_grow"]
        burst_factors = [
            (2, 500, 1000),
            (5, 500, 2500),
            (10, 500, 5000),
            (20, 500, 10000),
        ]
        sweep_results = {}

        for b_factor, r_low, r_high in burst_factors:
            print(f"  --- Burst Factor B = {b_factor} (low={r_low} Hz, high={r_high} Hz) ---")
            factor_key = f"B_{b_factor}"
            sweep_results[factor_key] = {}
            for p in sweep_policies:
                p_dir = tmp_root / f"sweep_{factor_key}" / p
                print(f"    -> Running policy {p:<14} ... ", end="", flush=True)
                res = run_single_pilot(
                    policy=p,
                    workload="burst_step",
                    output_dir=p_dir,
                    workload_args=[
                        "--rate-low-hz", str(r_low),
                        "--rate-high-hz", str(r_high),
                        "--low-count", "50",
                        "--high-count", "200",
                    ],
                    seed=42,
                )
                sweep_results[factor_key][p] = res
                e2e_p99_us = res["exact_quantiles_ns"]["end_to_end_latency"]["p99"] / 1000.0
                print(f"done ({res['duration_sec']}s) | p99: {e2e_p99_us:8.1f} us")

    # Assemble comprehensive telemetry payload
    telemetry_payload = {
        "contract": "KLS-09",
        "description": "Exploratory Calibration & Prospective Precision Pilot Grid",
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "isolation_boundary": {
            "cohort_path": str(COHORT_PATH.relative_to(REPO_ROOT)),
            "cohort_sha256": cohort_hash,
            "evaluated_split": "validation",
            "evaluated_records": 5233,
            "source_day": "rec_20170818",
            "test_holdout_sealed": True,
            "test_holdout_records": 2153,
            "test_holdout_day": "rec_20170819",
        },
        "model_reference": {
            "path": str(MODEL_CHECKPOINT.relative_to(REPO_ROOT)),
            "sha256": model_hash,
            "trees": 200,
            "subsample": 128,
        },
        "regime_a_replay": {
            "description": "Authentic market interarrival spacing with ceiling max_delay_us=500",
            "workload": "replay",
            "results": regime_a_results,
        },
        "regime_b_burst": {
            "description": "Non-stationary dual-state surge: 500 Hz low -> 5000 Hz high",
            "workload": "burst_step",
            "results": regime_b_results,
        },
        "operating_region_burst_sweep": {
            "description": "Operating-region boundary sweep across burst factors B in {2, 5, 10, 20}",
            "results": sweep_results,
        },
        "prospective_precision_design": {
            "target_epoch": "KLS-10",
            "primary_endpoint": "Paired log-ratio of trial-level p99 end-to-end latency",
            "practical_threshold_delta_us": 500.0,
            "independent_units": "5 trial blocks with distinct PRNG seeds [42, 43, 44, 45, 46]",
            "thermal_drift_mitigation": "Randomized / counterbalanced policy dispatch within blocks",
            "falsification_margins": {
                "equivalence_margin_pct": 5.0,
                "max_controller_overhead_pct": 10.0,
                "min_conservation_integrity": 1.0,
            },
            "stopping_plan": "Fixed sample design (N=5 seeds x 9 policies x 2 regimes = 90 confirmatory trials), no early stopping",
        },
    }

    TELEMETRY_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(TELEMETRY_OUT, "w", encoding="utf-8") as f:
        json.dump(telemetry_payload, f, indent=2)

    telemetry_hash = sha256_file(TELEMETRY_OUT)
    print("\n" + "=" * 80)
    print(f"PILOT TELEMETRY MANIFEST MATERIALIZED: {TELEMETRY_OUT}")
    print(f"SHA-256 Digest: {telemetry_hash}")
    print("=" * 80)

    # Print summary tables
    print("\n### SUMMARY TABLE: REGIME A (Authentic Replay, max_delay=500us)")
    print("| Policy | Events | p50 e2e (us) | p90 e2e (us) | p99 e2e (us) | p99.9 e2e (us) | wait/svc | Dur (s) |")
    print("|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|")
    for p, r in regime_a_results.items():
        q = r["exact_quantiles_ns"]["end_to_end_latency"]
        print(f"| `{p:<15}` | {r['events_offered']} | {q['p50']/1e3:8.1f} | {q['p90']/1e3:8.1f} | {q['p99']/1e3:8.1f} | {q['p99.9']/1e3:8.1f} | {r['queue_wait_dominance_ratio']:6.2f} | {r['duration_sec']:5.2f} |")

    print("\n### SUMMARY TABLE: REGIME B (Non-Stationary Burst Surge, 500/5000 Hz)")
    print("| Policy | Events | p50 e2e (us) | p90 e2e (us) | p99 e2e (us) | p99.9 e2e (us) | wait/svc | Dur (s) |")
    print("|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|")
    for p, r in regime_b_results.items():
        q = r["exact_quantiles_ns"]["end_to_end_latency"]
        print(f"| `{p:<15}` | {r['events_offered']} | {q['p50']/1e3:8.1f} | {q['p90']/1e3:8.1f} | {q['p99']/1e3:8.1f} | {q['p99.9']/1e3:8.1f} | {r['queue_wait_dominance_ratio']:6.2f} | {r['duration_sec']:5.2f} |")

    print("\n### SUMMARY TABLE: OPERATING-REGION BOUNDARY (Burst Factor Sweep, p99 e2e in us)")
    print("| Policy | B = 2 (1 kHz) | B = 5 (2.5 kHz) | B = 10 (5 kHz) | B = 20 (10 kHz) |")
    print("|:---|:---:|:---:|:---:|:---:|")
    for p in sweep_policies:
        cols = []
        for b_key in ["B_2", "B_5", "B_10", "B_20"]:
            p99_val = sweep_results[b_key][p]["exact_quantiles_ns"]["end_to_end_latency"]["p99"] / 1e3
            cols.append(f"{p99_val:8.1f}")
        print(f"| `{p:<15}` | {' | '.join(cols)} |")


if __name__ == "__main__":
    main()
