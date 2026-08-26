#!/usr/bin/env python3
"""
verify_receipt_original.py — Original verifier that reads verified artifact count from receipt summary.
"""
import json
from pathlib import Path

RECEIPT_JSON = Path("results/reproducibility_receipt_summary.json")

def main():
    with open(RECEIPT_JSON, "r") as f:
        data = json.load(f)
    print(json.dumps({"total_verified_artifacts": int(data["total_verified_artifacts"])}))

if __name__ == "__main__":
    main()
