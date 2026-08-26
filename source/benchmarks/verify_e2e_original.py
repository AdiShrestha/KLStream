#!/usr/bin/env python3
"""
verify_e2e_original.py — Original verifier that reads dropped events from e2e_streaming_benchmark.json.
"""
import json
from pathlib import Path

REPORT_PATH = Path("results/e2e_streaming_benchmark.json")

def main():
    with open(REPORT_PATH, "r") as f:
        data = json.load(f)
    print(json.dumps({"events_dropped": int(data["events_dropped"])}))

if __name__ == "__main__":
    main()
