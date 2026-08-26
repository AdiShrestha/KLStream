#!/usr/bin/env python3
"""
verify_hardware_original.py — Original verifier that reads target throughput from hardware benchmark report.
"""
import json
from pathlib import Path

REPORT_PATH = Path("results/hardware_benchmark_report.json")

def main():
    with open(REPORT_PATH, "r") as f:
        data = json.load(f)
    print(json.dumps({"spsc_target_mops": float(data["spsc_target_mops"])}))

if __name__ == "__main__":
    main()
