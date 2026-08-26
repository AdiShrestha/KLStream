#!/usr/bin/env python3
"""
verify_anomaly_original.py — Original verifier that reads anomaly catalog verification artifact.
"""
import json
from pathlib import Path

VERIF_JSON = Path(__file__).resolve().parent / "anomaly_verification.json"

def main():
    with open(VERIF_JSON, "r") as f:
        data = json.load(f)
    print(json.dumps({"anomaly_archetypes_count": data["anomaly_archetypes_count"]}))

if __name__ == "__main__":
    main()
