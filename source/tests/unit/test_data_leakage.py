#!/usr/bin/env python3
"""
test_data_leakage.py — Verification of zero data leakage across train, val, and test splits.

Verifies:
- Monotonic timestamp ordering across splits (T_train_max <= T_val_min <= T_test_min).
- Exact contiguous row coverage with zero indexing gaps or overlaps.
- Threshold tuning pre-registration targeting Validation split.
"""

import json
import os
from pathlib import Path
import unittest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
MANIFEST_PATH = REPO_ROOT / "data" / "processed" / "split_manifest.json"

class TestDataLeakage(unittest.TestCase):
    def setUp(self):
        self.assertTrue(MANIFEST_PATH.exists(), f"Split manifest missing at {MANIFEST_PATH}")
        with open(MANIFEST_PATH, "r") as f:
            self.manifest = json.load(f)

    def test_manifest_structure(self):
        self.assertIn("datasets", self.manifest)
        self.assertGreater(len(self.manifest["datasets"]), 0)
        self.assertIn("INV-005", self.manifest.get("governing_invariants", []))

    def test_split_temporal_monotonicity(self):
        for d in self.manifest["datasets"]:
            name = d["dataset_filename"]
            train = d["train_split"]
            val = d["val_split"]
            test = d["test_split"]
            
            # Row index contiguity
            self.assertEqual(train["start_idx"], 0, f"{name}: Train start is not 0")
            self.assertEqual(train["end_idx"], val["start_idx"], f"{name}: Gap between train and val")
            self.assertEqual(val["end_idx"], test["start_idx"], f"{name}: Gap between val and test")
            self.assertEqual(test["end_idx"], d["total_rows"], f"{name}: Test does not reach end")
            
            # Sum of row counts
            self.assertEqual(train["row_count"] + val["row_count"] + test["row_count"], d["total_rows"])
            
            # Temporal monotonicity (Zero lookahead leakage)
            self.assertLessEqual(
                train["end_timestamp_ns"], val["start_timestamp_ns"],
                f"{name}: Train end timestamp ({train['end_timestamp_ns']}) exceeds Val start ({val['start_timestamp_ns']})"
            )
            self.assertLessEqual(
                val["end_timestamp_ns"], test["start_timestamp_ns"],
                f"{name}: Val end timestamp ({val['end_timestamp_ns']}) exceeds Test start ({test['start_timestamp_ns']})"
            )
            
            # Pre-registration of threshold tuning
            self.assertEqual(d["threshold_tuning_target"], "val", f"{name}: Threshold target is not val")

if __name__ == "__main__":
    unittest.main()
