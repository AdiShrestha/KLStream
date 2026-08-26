#!/usr/bin/env python3
"""
verify_calibration_independent.py — Independent verifier checking dataset count in split_manifest.json.
"""
import json
from pathlib import Path

MANIFEST_JSON = Path("data/processed/split_manifest.json")

def main():
    with open(MANIFEST_JSON, "r") as f:
        data = json.load(f)
    print(json.dumps({"num_calibrations": len(data["datasets"])}))

if __name__ == "__main__":
    main()
