#!/usr/bin/env python3
"""
verify_matrix_original.py — Original verifier that reads total_events_dropped from execution_summary.json.
"""
import json
from pathlib import Path

SUMMARY_JSON = Path("results/execution_summary.json")

def main():
    with open(SUMMARY_JSON, "r") as f:
        data = json.load(f)
    print(json.dumps({"total_events_dropped": data["total_events_dropped"]}))

if __name__ == "__main__":
    main()
