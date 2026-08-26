#!/usr/bin/env python3
"""
verify_preregistration_original.py — Original verifier that reads recorded digest.
"""
import json
from pathlib import Path

DIGEST_JSON = Path(__file__).resolve().parent / "preregistration_digest.json"

def main():
    with open(DIGEST_JSON, "r") as f:
        data = json.load(f)
    print(json.dumps({"sha256": data["sha256"]}))

if __name__ == "__main__":
    main()
