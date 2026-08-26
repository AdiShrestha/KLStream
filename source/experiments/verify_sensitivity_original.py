#!/usr/bin/env python3
"""
verify_sensitivity_original.py — Original verifier that reads grid evaluation count from sensitivity_analysis.json.
"""
import json
from pathlib import Path

SENSITIVITY_JSON = Path("results/sensitivity_analysis.json")

def main():
    with open(SENSITIVITY_JSON, "r") as f:
        data = json.load(f)
    print(json.dumps({"num_grid_evaluations": data["num_grid_evaluations"]}))

if __name__ == "__main__":
    main()
