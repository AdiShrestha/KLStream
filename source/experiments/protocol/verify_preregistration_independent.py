#!/usr/bin/env python3
"""
verify_preregistration_independent.py — Independent computation of SHA-256 hash of falsification_criteria.md.
"""
import hashlib
import json
from pathlib import Path

CRITERIA_MD = Path(__file__).resolve().parent / "falsification_criteria.md"

def main():
    with open(CRITERIA_MD, "rb") as f:
        content = f.read()
    digest = hashlib.sha256(content).hexdigest()
    print(json.dumps({"sha256": digest}))

if __name__ == "__main__":
    main()
