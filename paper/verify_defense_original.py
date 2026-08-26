#!/usr/bin/env python3
"""
verify_defense_original.py — Original verifier that extracts evaluated grid count from sensitivity_analysis.json.
"""
import json
from pathlib import Path

SENS_PATH = Path("results/sensitivity_analysis.json")

def main():
    with open(SENS_PATH, "r") as f:
        data = json.load(f)
    print(json.dumps({"num_grid_evaluations": int(data["num_grid_evaluations"])}))

if __name__ == "__main__":
    main()
