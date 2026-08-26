#!/usr/bin/env python3
"""
verify_anomaly_independent.py — Independent parsing of anomaly catalog archetypes.
"""
import json
import re
from pathlib import Path

CATALOG_MD = Path(__file__).resolve().parent / "anomaly_catalog.md"

def main():
    with open(CATALOG_MD, "r") as f:
        text = f.read()
    matches = re.findall(r"### Archetype \d+:", text)
    print(json.dumps({"anomaly_archetypes_count": len(matches)}))

if __name__ == "__main__":
    main()
