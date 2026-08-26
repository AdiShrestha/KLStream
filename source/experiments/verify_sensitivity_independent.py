#!/usr/bin/env python3
"""
verify_sensitivity_independent.py — Independent verifier calculating valid grid combinations.
"""
import json

def main():
    alphas = [0.01, 0.05, 0.1, 0.2, 0.5]
    w_mins = [5, 10, 20]
    w_maxs = [100, 250, 500, 1000]
    count = 0
    for a in alphas:
        for wmin in w_mins:
            for wmax in w_maxs:
                if wmin < wmax:
                    count += 1
    print(json.dumps({"num_grid_evaluations": count}))

if __name__ == "__main__":
    main()
