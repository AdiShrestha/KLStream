#!/usr/bin/env python3
"""
test_statistical_methods.py — Unit tests for non-parametric statistical methods.
"""

import math
import sys
import unittest
from pathlib import Path
import numpy as np

# Add protocol directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "experiments" / "protocol"))
import statistical_methods as sm

class TestStatisticalMethods(unittest.TestCase):
    def test_cliffs_delta_extremes(self):
        # Perfect positive separation
        a = [10, 11, 12, 13, 14]
        b = [1, 2, 3, 4, 5]
        self.assertAlmostEqual(sm.cliffs_delta(a, b), 1.0)
        self.assertEqual(sm.interpret_cliffs_delta(1.0), "large")
        
        # Perfect negative separation
        self.assertAlmostEqual(sm.cliffs_delta(b, a), -1.0)
        self.assertEqual(sm.interpret_cliffs_delta(-1.0), "large")
        
        # Identical sets
        self.assertAlmostEqual(sm.cliffs_delta(a, a), 0.0)
        self.assertEqual(sm.interpret_cliffs_delta(0.0), "negligible")

    def test_wilcoxon_paired_test(self):
        # Sample A consistently higher than Sample B
        a = [10.5, 12.0, 11.2, 13.5, 15.0]
        b = [8.1, 9.0, 9.5, 11.0, 12.0]
        
        res = sm.wilcoxon_paired_test(a, b)
        self.assertEqual(res["statistic"], 0.0) # W- = 0
        self.assertEqual(res["w_pos"], 15.0)   # 1+2+3+4+5 = 15
        # Exact one-sided permutation is 1/32 ≈ 0.03125, two-sided is 2/32 = 0.0625
        self.assertLessEqual(res["p_value"], 0.0625)

    def test_bootstrap_ci_coverage(self):
        # Sample drawn from known distribution
        sample = [10.0, 10.2, 9.8, 10.1, 9.9, 10.3, 9.7, 10.0]
        mean_val = np.mean(sample)
        
        ci_lower, ci_upper = sm.bootstrap_ci_95(sample, n_boot=2000, seed=42)
        self.assertLessEqual(ci_lower, mean_val)
        self.assertGreaterEqual(ci_upper, mean_val)
        self.assertGreater(ci_lower, 9.5)
        self.assertLess(ci_upper, 10.5)

    def test_bonferroni_holm_adjust(self):
        # Input raw p-values
        raw_p = [0.01, 0.04, 0.03, 0.005]
        # Sorted: 0.005 (x4 -> 0.02), 0.01 (x3 -> 0.03), 0.03 (x2 -> 0.06), 0.04 (x1 -> 0.06)
        adj_p = sm.bonferroni_holm_adjust(raw_p)
        
        self.assertEqual(len(adj_p), 4)
        self.assertAlmostEqual(adj_p[3], 0.02) # 0.005 * 4
        self.assertAlmostEqual(adj_p[0], 0.03) # 0.01 * 3
        self.assertAlmostEqual(adj_p[2], 0.06) # 0.03 * 2
        self.assertAlmostEqual(adj_p[1], 0.06) # max(0.06, 0.04 * 1)

if __name__ == "__main__":
    unittest.main()
