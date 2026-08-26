#!/usr/bin/env python3
"""
verify_framing_original.py — Original verification script for research framing parameters.
"""
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
VERIF_JSON = REPO_ROOT / "source" / "experiments" / "research_framing_verification.json"

def main():
    with open(VERIF_JSON, "r") as f:
        data = json.load(f)
    print(json.dumps({"hypotheses_count": data["hypotheses_count"]}))

if __name__ == "__main__":
    main()
