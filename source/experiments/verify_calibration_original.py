#!/usr/bin/env python3
"""
verify_calibration_original.py — Original verifier that reads validation_calibration.json.
"""
import json
from pathlib import Path

VERIF_JSON = Path("results/validation_calibration.json")

def main():
    with open(VERIF_JSON, "r") as f:
        data = json.load(f)
    print(json.dumps({"num_calibrations": data["num_calibrations"]}))

if __name__ == "__main__":
    main()
