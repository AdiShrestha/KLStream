#!/usr/bin/env python3
"""
test_preprocessing_schema.py — Unit tests for schema validation and negative failure rejection.

Validates that invalid or corrupted input rows are rejected fail-closed with clear ValueErrors.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

# Add preprocessing directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "experiments" / "preprocessing"))
import preprocess

class TestPreprocessingSchema(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dir_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_valid_synthetic_data(self):
        csv_file = self.dir_path / "valid.csv"
        with open(csv_file, "w") as f:
            f.write("seq,timestamp_ns,bid_px,ask_px,bid_sz,ask_sz,label,is_burst_period\n")
            f.write("0,1000,100.0,101.0,50,50,0,0\n")
            f.write("1,2000,100.5,101.5,60,40,1,1\n")
            
        rows, injections = preprocess.validate_and_process_synthetic(csv_file)
        self.assertEqual(len(rows), 2)
        self.assertEqual(len(injections), 1)
        self.assertEqual(injections[0]["anomaly_type"], "flash_crash_precursor")
        self.assertEqual(rows[0]["mid_price"], 100.5)
        self.assertEqual(rows[1]["is_anomaly"], 1)

    def test_missing_column_rejected(self):
        csv_file = self.dir_path / "missing_col.csv"
        with open(csv_file, "w") as f:
            f.write("seq,timestamp_ns,bid_px,ask_px\n")
            f.write("0,1000,100.0,101.0\n")
            
        with self.assertRaises(ValueError) as ctx:
            preprocess.validate_and_process_synthetic(csv_file)
        self.assertIn("Missing required columns", str(ctx.exception))

    def test_negative_price_rejected(self):
        csv_file = self.dir_path / "negative_price.csv"
        with open(csv_file, "w") as f:
            f.write("seq,timestamp_ns,bid_px,ask_px,bid_sz,ask_sz,label,is_burst_period\n")
            f.write("0,1000,-10.0,101.0,50,50,0,0\n")
            
        with self.assertRaises(ValueError) as ctx:
            preprocess.validate_and_process_synthetic(csv_file)
        self.assertIn("Non-positive price", str(ctx.exception))

    def test_crossed_book_rejected(self):
        csv_file = self.dir_path / "crossed_book.csv"
        with open(csv_file, "w") as f:
            f.write("seq,timestamp_ns,bid_px,ask_px,bid_sz,ask_sz,label,is_burst_period\n")
            f.write("0,1000,102.0,101.0,50,50,0,0\n")
            
        with self.assertRaises(ValueError) as ctx:
            preprocess.validate_and_process_synthetic(csv_file)
        self.assertIn("Crossed/locked book", str(ctx.exception))

    def test_negative_size_rejected(self):
        csv_file = self.dir_path / "negative_size.csv"
        with open(csv_file, "w") as f:
            f.write("seq,timestamp_ns,bid_px,ask_px,bid_sz,ask_sz,label,is_burst_period\n")
            f.write("0,1000,100.0,101.0,-5,50,0,0\n")
            
        with self.assertRaises(ValueError) as ctx:
            preprocess.validate_and_process_synthetic(csv_file)
        self.assertIn("Negative size", str(ctx.exception))

    def test_non_monotonic_timestamp_rejected(self):
        csv_file = self.dir_path / "time_reversal.csv"
        with open(csv_file, "w") as f:
            f.write("seq,timestamp_ns,bid_px,ask_px,bid_sz,ask_sz,label,is_burst_period\n")
            f.write("0,2000,100.0,101.0,50,50,0,0\n")
            f.write("1,1000,100.0,101.0,50,50,0,0\n")
            
        with self.assertRaises(ValueError) as ctx:
            preprocess.validate_and_process_synthetic(csv_file)
        self.assertIn("Non-monotonic timestamp", str(ctx.exception))

if __name__ == "__main__":
    unittest.main()
