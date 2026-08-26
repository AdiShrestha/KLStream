#!/usr/bin/env python3
"""
test_evaluation_metrics.py — Unit tests and known-answer verification for evaluation_metrics.py.
"""

import math
import sys
import unittest
from pathlib import Path
import numpy as np

# Add metrics directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "experiments" / "metrics"))
import evaluation_metrics as em

class TestEvaluationMetrics(unittest.TestCase):
    def test_perfect_auc_roc(self):
        y_true = [0, 0, 0, 0, 1, 1, 1, 1]
        y_scores = [0.1, 0.2, 0.3, 0.4, 0.6, 0.7, 0.8, 0.9]
        auc = em.compute_auc_roc(y_true, y_scores)
        self.assertAlmostEqual(auc, 1.0, places=6)
        
        pr_auc = em.compute_pr_auc(y_true, y_scores)
        self.assertAlmostEqual(pr_auc, 1.0, places=4)

    def test_inverted_auc_roc(self):
        y_true = [0, 0, 1, 1]
        y_scores = [0.9, 0.8, 0.2, 0.1]
        auc = em.compute_auc_roc(y_true, y_scores)
        self.assertAlmostEqual(auc, 0.0, places=6)

    def test_known_confusion_matrix_f1(self):
        y_true = [1, 1, 1, 1, 0, 0, 0, 0]
        y_scores = [0.9, 0.8, 0.7, 0.2, 0.85, 0.1, 0.2, 0.3]
        # At threshold 0.5:
        # Positives above 0.5: 3 (TP=3, FN=1)
        # Negatives above 0.5: 1 (FP=1, TN=3)
        res = em.compute_binary_classification_metrics(y_true, y_scores, threshold=0.5)
        self.assertEqual(res["tp"], 3)
        self.assertEqual(res["fp"], 1)
        self.assertEqual(res["fn"], 1)
        self.assertEqual(res["tn"], 3)
        self.assertAlmostEqual(res["precision"], 3.0 / 4.0)
        self.assertAlmostEqual(res["recall"], 3.0 / 4.0)
        self.assertAlmostEqual(res["f1"], 0.75)
        self.assertAlmostEqual(res["fpr"], 1.0 / 4.0)

    def test_latency_summary_known_quantiles(self):
        latencies = list(range(1, 101)) # 1 to 100
        summary = em.compute_latency_summary(latencies)
        self.assertEqual(summary["count"], 100)
        self.assertAlmostEqual(summary["min_ns"], 1.0)
        self.assertAlmostEqual(summary["max_ns"], 100.0)
        self.assertAlmostEqual(summary["mean_ns"], 50.5)
        self.assertAlmostEqual(summary["p50_ns"], 50.5, delta=1.0)
        self.assertAlmostEqual(summary["p90_ns"], 90.1, delta=1.0)
        self.assertAlmostEqual(summary["p99_ns"], 99.01, delta=1.0)

    def test_latency_decomposition_identity(self):
        t_q = [10.0, 20.0, 30.0]
        t_f = [5.0, 5.0, 5.0]
        t_e = [2.0, 2.0, 2.0]
        
        decomp = em.compute_decomposed_latency_summary(t_q, t_f, t_e)
        self.assertEqual(decomp["queuing_latency"]["count"], 3)
        self.assertEqual(decomp["freshness_lag"]["mean_ns"], 5.0)
        self.assertEqual(decomp["execution_latency"]["mean_ns"], 2.0)
        self.assertEqual(decomp["end_to_end_latency"]["mean_ns"], 20.0 + 5.0 + 2.0)

    def test_validation_threshold_tuning(self):
        # 100 normal samples with uniform scores in [0.0, 0.5]
        # 10 anomaly samples in [0.6, 1.0]
        y_val_true = [0] * 100 + [1] * 10
        y_val_scores = [i * 0.005 for i in range(100)] + [0.6 + i * 0.04 for i in range(10)]
        
        tau = em.tune_validation_threshold(y_val_true, y_val_scores, target_fpr=0.05)
        # 95th percentile of normal scores: 0.95 * (99 * 0.005) ≈ 0.47
        self.assertGreater(tau, 0.45)
        self.assertLess(tau, 0.55)

if __name__ == "__main__":
    unittest.main()
