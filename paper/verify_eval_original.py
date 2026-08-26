#!/usr/bin/env python3
"""
verify_eval_original.py — Original verifier that extracts Claim 1 latency reduction from falsification_verdicts.json.
"""
import json
from pathlib import Path

VERDICTS_PATH = Path("results/falsification_verdicts.json")

def main():
    with open(VERDICTS_PATH, "r") as f:
        data = json.load(f)
    print(json.dumps({"claim_1_margin_pct": float(data["verdicts"]["claim_1"]["empirical_margin_pct"])}))

if __name__ == "__main__":
    main()
