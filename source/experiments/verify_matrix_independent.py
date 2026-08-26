#!/usr/bin/env python3
"""
verify_matrix_independent.py — Independent aggregation of dropped events across individual run JSONs.
"""
import glob
import json
from pathlib import Path

def main():
    total_drops = 0
    run_files = glob.glob("results/runs/*.json")
    for rf in run_files:
        with open(rf, "r") as f:
            data = json.load(f)
        total_drops += data["event_accounting"]["events_dropped"]
    print(json.dumps({"total_events_dropped": total_drops}))

if __name__ == "__main__":
    main()
