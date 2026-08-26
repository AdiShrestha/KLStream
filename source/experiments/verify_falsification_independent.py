#!/usr/bin/env python3
"""
verify_falsification_independent.py — Independent verifier checking claim count in preregistration_digest.json.
"""
import json
from pathlib import Path

DIGEST_JSON = Path("source/experiments/protocol/preregistration_digest.json")

def main():
    with open(DIGEST_JSON, "r") as f:
        data = json.load(f)
    print(json.dumps({"num_claims_evaluated": len(data["claims_registered"])}))

if __name__ == "__main__":
    main()
