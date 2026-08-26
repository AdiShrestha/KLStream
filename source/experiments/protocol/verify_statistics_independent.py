#!/usr/bin/env python3
"""
verify_statistics_independent.py — Independent computation of Cliff's delta on disjoint sets.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import statistical_methods as sm

def main():
    # Disjoint strictly dominant sample A > B
    sample_a = [10.0, 20.0, 30.0, 40.0]
    sample_b = [1.0, 2.0, 3.0, 4.0]
    delta = sm.cliffs_delta(sample_a, sample_b)
    print(json.dumps({"cliffs_delta_reference": delta}))

if __name__ == "__main__":
    main()
