#!/usr/bin/env python3
"""
test_experiment_runner.py — Unit tests and dry-run validation for experiment_runner.py.
"""

import json
import sys
import unittest
from pathlib import Path

# Add runners to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "experiments" / "runners"))
from experiment_runner import run_experiment, load_dataset_split

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent

class TestExperimentRunner(unittest.TestCase):
    def setUp(self):
        self.dataset_path = str(REPO_ROOT / "data" / "processed" / "replay_synthetic_seed101.csv")
        self.manifest_path = str(REPO_ROOT / "data" / "processed" / "split_manifest.json")

    def test_load_dataset_split_slice(self):
        records, X, y = load_dataset_split(self.dataset_path, self.manifest_path, "val")
        # In split_manifest.json, validation split is 2,000 rows
        self.assertEqual(len(records), 2000)
        self.assertEqual(X.shape, (2000, 7))
        self.assertEqual(y.shape, (2000,))

    def test_dry_run_execution_and_accounting(self):
        telemetry = run_experiment(
            dataset_path=self.dataset_path,
            split_name="val",
            controller_name="adaptive",
            manifest_path=self.manifest_path,
            dry_run=True
        )
        
        # SVI-005 & INV-007 Verification
        accounting = telemetry["event_accounting"]
        self.assertEqual(accounting["events_ingested"], 500)
        self.assertEqual(accounting["events_processed"], 500)
        self.assertEqual(accounting["events_dropped"], 0)
        
        # Detection metrics validation
        det = telemetry["detection_metrics"]
        self.assertIn("auc_roc", det)
        self.assertIn("pr_auc", det)
        self.assertIn("classification_at_tau", det)
        
        # Latency breakdown validation
        lat = telemetry["latency_summary_ns"]
        self.assertIn("queuing_latency", lat)
        self.assertIn("freshness_lag", lat)
        self.assertIn("execution_latency", lat)
        self.assertIn("end_to_end_latency", lat)
        
        mean_q = lat["queuing_latency"]["mean_ns"]
        mean_f = lat["freshness_lag"]["mean_ns"]
        mean_e = lat["execution_latency"]["mean_ns"]
        mean_e2e = lat["end_to_end_latency"]["mean_ns"]
        self.assertAlmostEqual(mean_e2e, mean_q + mean_f + mean_e, places=4)

if __name__ == "__main__":
    unittest.main()
