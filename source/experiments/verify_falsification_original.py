#!/usr/bin/env python3
"""
verify_falsification_original.py — Original verifier that reads claim count from falsification_verdicts.json.
"""
import json
from pathlib import Path

VERDICTS_JSON = Path("results/falsification_verdicts.json")

def main():
    with open(VERDICTS_JSON, "r") as f:
        data = json.load(f)
    print(json.dumps({"num_claims_evaluated": data["num_claims_evaluated"]}))

if __name__ == "__main__":
    main()
