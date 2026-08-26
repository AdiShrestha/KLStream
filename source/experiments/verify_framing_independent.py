#!/usr/bin/env python3
"""
verify_framing_independent.py — Independent verifier that parses research_framing.md.
"""
import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
FRAMING_MD = REPO_ROOT / "source" / "experiments" / "research_framing.md"

def main():
    with open(FRAMING_MD, "r") as f:
        text = f.read()
    h_matches = re.findall(r"### Hypothesis \d+", text)
    print(json.dumps({"hypotheses_count": len(h_matches)}))

if __name__ == "__main__":
    main()
