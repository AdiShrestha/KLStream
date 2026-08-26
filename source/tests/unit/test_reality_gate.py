#!/usr/bin/env python3
"""
test_reality_gate.py — Unit tests for the Reality Gate domain verification engine.

Verifies:
- All 6 domain checks pass on compliant datasets.
- Each individual check fails-closed when encountering domain violations.
"""

import csv
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Add preprocessing directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "experiments" / "preprocessing"))
import reality_gate

class TestRealityGate(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dir_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write_csv(self, filename: str, rows: list) -> Path:
        filepath = self.dir_path / filename
        fieldnames = ["seq", "timestamp_ns", "bid_px", "ask_px", "bid_sz", "ask_sz", "mid_price", "is_anomaly"]
        with open(filepath, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in rows:
                writer.writerow(r)
        return filepath

    def test_clean_dataset_passes(self):
        rows = [
            {"seq": 0, "timestamp_ns": 1000, "bid_px": 100.0, "ask_px": 101.0, "bid_sz": 50, "ask_sz": 50, "mid_price": 100.5, "is_anomaly": 0},
            {"seq": 1, "timestamp_ns": 2000, "bid_px": 100.2, "ask_px": 101.2, "bid_sz": 60, "ask_sz": 40, "mid_price": 100.7, "is_anomaly": 1}
        ]
        csv_file = self._write_csv("clean.csv", rows)
        res = reality_gate.verify_dataset(csv_file)
        self.assertEqual(res["status"], "PASS")
        self.assertTrue(all(c["passed"] for c in res["checks"].values()))

    def test_negative_price_fails_rg_pos(self):
        rows = [
            {"seq": 0, "timestamp_ns": 1000, "bid_px": -10.0, "ask_px": 101.0, "bid_sz": 50, "ask_sz": 50, "mid_price": 45.5, "is_anomaly": 0}
        ]
        csv_file = self._write_csv("bad_pos.csv", rows)
        res = reality_gate.verify_dataset(csv_file)
        self.assertEqual(res["status"], "FAIL")
        self.assertFalse(res["checks"]["RG-POS"]["passed"])
        self.assertEqual(res["checks"]["RG-POS"]["violations"], 1)

    def test_crossed_book_fails_rg_spread(self):
        rows = [
            {"seq": 0, "timestamp_ns": 1000, "bid_px": 105.0, "ask_px": 101.0, "bid_sz": 50, "ask_sz": 50, "mid_price": 103.0, "is_anomaly": 0}
        ]
        csv_file = self._write_csv("bad_spread.csv", rows)
        res = reality_gate.verify_dataset(csv_file)
        self.assertEqual(res["status"], "FAIL")
        self.assertFalse(res["checks"]["RG-SPREAD"]["passed"])
        self.assertEqual(res["checks"]["RG-SPREAD"]["violations"], 1)

    def test_zero_size_fails_rg_size(self):
        rows = [
            {"seq": 0, "timestamp_ns": 1000, "bid_px": 100.0, "ask_px": 101.0, "bid_sz": 0, "ask_sz": 50, "mid_price": 100.5, "is_anomaly": 0}
        ]
        csv_file = self._write_csv("bad_size.csv", rows)
        res = reality_gate.verify_dataset(csv_file)
        self.assertEqual(res["status"], "FAIL")
        self.assertFalse(res["checks"]["RG-SIZE"]["passed"])

    def test_inverted_time_fails_rg_time(self):
        rows = [
            {"seq": 0, "timestamp_ns": 2000, "bid_px": 100.0, "ask_px": 101.0, "bid_sz": 50, "ask_sz": 50, "mid_price": 100.5, "is_anomaly": 0},
            {"seq": 1, "timestamp_ns": 1000, "bid_px": 100.0, "ask_px": 101.0, "bid_sz": 50, "ask_sz": 50, "mid_price": 100.5, "is_anomaly": 0}
        ]
        csv_file = self._write_csv("bad_time.csv", rows)
        res = reality_gate.verify_dataset(csv_file)
        self.assertEqual(res["status"], "FAIL")
        self.assertFalse(res["checks"]["RG-TIME"]["passed"])

    def test_invalid_label_fails_rg_labels(self):
        rows = [
            {"seq": 0, "timestamp_ns": 1000, "bid_px": 100.0, "ask_px": 101.0, "bid_sz": 50, "ask_sz": 50, "mid_price": 100.5, "is_anomaly": 5}
        ]
        csv_file = self._write_csv("bad_label.csv", rows)
        res = reality_gate.verify_dataset(csv_file)
        self.assertEqual(res["status"], "FAIL")
        self.assertFalse(res["checks"]["RG-LABELS"]["passed"])

if __name__ == "__main__":
    unittest.main()
