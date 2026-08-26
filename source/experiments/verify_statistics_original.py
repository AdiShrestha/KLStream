#!/usr/bin/env python3
"""
verify_statistics_original.py — Original verifier that reads metric count from statistical_summary.json.
"""
import json
from pathlib import Path

SUMMARY_JSON = Path("results/statistical_summary.json")

def main():
    with open(SUMMARY_JSON, "r") as f:
        data = json.load(f)
    print(json.dumps({"num_metric_comparisons": len(data["comparisons"])}))

if __name__ == "__main__":
    main()
