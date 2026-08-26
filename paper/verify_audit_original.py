#!/usr/bin/env python3
"""
verify_audit_original.py — Original verifier that extracts matched claims count from claims_audit_summary.json.
"""
import json
from pathlib import Path

SUMMARY_PATH = Path("results/claims_audit_summary.json")

def main():
    with open(SUMMARY_PATH, "r") as f:
        data = json.load(f)
    print(json.dumps({"matched_claims": int(data["matched_claims"])}))

if __name__ == "__main__":
    main()
