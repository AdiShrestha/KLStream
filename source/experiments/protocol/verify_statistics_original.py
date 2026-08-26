#!/usr/bin/env python3
"""
verify_statistics_original.py — Original verifier for statistical reference values.
"""
import json
from pathlib import Path

VERIF_JSON = Path(__file__).resolve().parent / "statistical_verification.json"

def main():
    with open(VERIF_JSON, "r") as f:
        data = json.load(f)
    print(json.dumps({"cliffs_delta_reference": data["cliffs_delta_reference"]}))

if __name__ == "__main__":
    main()
