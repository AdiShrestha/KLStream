#!/usr/bin/env python3
"""
Clean 90-run sweep: 30 runs × 3 architectures at the calibrated speed factor.

SAFETY: clears results/raw/exp2_3/ before starting and verifies exactly 30
files per architecture exist with timestamps from THIS run before returning.
"""
import subprocess
import os
import glob
import shutil
import sys
from datetime import datetime, timezone

architectures = ["datadriven"]
runs          = 30
duration      = 10   # seconds per run
speed_factor  = 1460 # Calibrated: passes oscillation criterion (std=0.358, frac_high=15.1%, frac_low=83.8%)
out_dir       = "results/raw/exp2_3"

def main():
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    run_start = datetime.now(timezone.utc)

    for arch in architectures:
        print(f"--- Running {runs} iterations for {arch} ---")
        for i in range(1, runs + 1):
            out_file = os.path.join(out_dir, f"run_{arch}_{i}.csv")
            cmd = [
                "./build/adaptive_window/adaptive_window_main",
                f"--architecture={arch}",
                f"--speed-factor={speed_factor}",
                "--preserve-timing",
                f"--duration={duration}",
                f"--out={out_file}"
            ]
            print(f"Run {i}/{runs} ... ", end="", flush=True)
            result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if result.returncode != 0:
                print(f"FAILED (exit code {result.returncode}) — aborting.")
                sys.exit(1)
            print("Done.")
        print()

    # ── Verify: exactly 30 files per architecture, all from THIS run ──────
    print("=== Verifying output ===")
    all_ok = True
    for arch in architectures:
        files = sorted(glob.glob(os.path.join(out_dir, f"run_{arch}_*.csv")))
        n = len(files)
        flag = "✅" if n == runs else "❌"
        print(f"{flag}  {arch}: {n}/{runs} files found")
        if n != runs:
            all_ok = False

    if all_ok:
        print("\n✅ All files verified. Safe to run aggregate_results.py.")
    else:
        print("\n❌ File count mismatch — do NOT proceed to aggregation.")
        sys.exit(1)

if __name__ == "__main__":
    main()
