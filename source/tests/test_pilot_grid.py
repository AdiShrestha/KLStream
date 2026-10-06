"""Unit and validation tests for KLS-09 Exploratory Calibration & Prospective Precision."""
from __future__ import annotations

import csv
import json
import pathlib
import struct
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
COHORT_PATH = DATA_DIR / "cohort.csv"
MODEL_PATH = DATA_DIR / "model_checkpoint.iforest"
TELEMETRY_PATH = DATA_DIR / "pilot_telemetry.json"


class PilotGridTests(unittest.TestCase):
    def test_data_isolation_boundary(self):
        """Verifies that development validation data is strictly isolated from test holdout."""
        self.assertTrue(COHORT_PATH.is_file(), f"Cohort CSV missing: {COHORT_PATH}")
        with open(COHORT_PATH, "r", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))

        val_rows = [r for r in reader if r.get("split") == "validation"]
        test_rows = [r for r in reader if r.get("split") == "test"]
        train_rows = [r for r in reader if r.get("split") == "train"]

        self.assertEqual(len(train_rows), 3427, "Train split record count must match 3,427")
        self.assertEqual(len(val_rows), 5233, "Validation split record count must match 5,233")
        self.assertEqual(len(test_rows), 2153, "Test split record count must match 2,153")

        # Confirm disjoint groups / days
        val_groups = {r["group_id"] for r in val_rows}
        test_groups = {r["group_id"] for r in test_rows}
        self.assertTrue(val_groups.isdisjoint(test_groups), "Validation and test groups must be strictly disjoint")

        # Verify source IDs
        val_source_days = {r["source_ids"] for r in val_rows}
        test_source_days = {r["source_ids"] for r in test_rows}
        self.assertEqual(val_source_days, {"rec_20170818"})
        self.assertEqual(test_source_days, {"rec_20170819"})

    def test_model_checkpoint_integrity(self):
        """Verifies that the pre-trained binary model checkpoint conforms to KLIF v1 format."""
        if not MODEL_PATH.is_file():
            self.skipTest(f"Model checkpoint not present in clean checkout: {MODEL_PATH}")
        self.assertGreater(MODEL_PATH.stat().st_size, 32, "Model file size too small for header")

        with open(MODEL_PATH, "rb") as f:
            header = f.read(32)
            payload = f.read()
        import zlib
        magic, version, trees, subsample, dim, height, seed, checksum = struct.unpack("<4sIIIIIII", header)
        self.assertEqual(magic, b"KLIF", "Invalid model magic header")
        self.assertEqual(version, 1, "Unsupported model format version")
        self.assertEqual(trees, 200, "Model trees mismatch")
        self.assertEqual(subsample, 128, "Model subsample mismatch")
        self.assertEqual(dim, 6, "Model feature dimension mismatch")
        self.assertEqual(seed, 42, "Model seed mismatch")
        expected_crc = zlib.crc32(payload) & 0xFFFFFFFF
        self.assertEqual(checksum, expected_crc, "Model CRC32 checksum mismatch")

    def test_pilot_telemetry_manifest(self):
        """Verifies structure and invariants of data/pilot_telemetry.json."""
        self.assertTrue(TELEMETRY_PATH.is_file(), f"Pilot telemetry manifest missing: {TELEMETRY_PATH}")
        with open(TELEMETRY_PATH, "r", encoding="utf-8") as f:
            payload = json.load(f)

        self.assertEqual(payload["contract"], "KLS-09")
        iso = payload["isolation_boundary"]
        self.assertEqual(iso["evaluated_split"], "validation")
        self.assertEqual(iso["evaluated_records"], 5233)
        self.assertEqual(iso["source_day"], "rec_20170818")
        self.assertTrue(iso["test_holdout_sealed"])

        policies = [
            "fixed_w1", "fixed_w4", "fixed_w8", "fixed_w16", "fixed_w32", "fixed_w64",
            "deadline_flush", "adaptive_grow", "adaptive_shrink",
        ]

        # Check Regime A
        self.assertIn("regime_a_replay", payload)
        regime_a = payload["regime_a_replay"]["results"]
        for p in policies:
            self.assertIn(p, regime_a, f"Missing policy {p} in Regime A")
            r = regime_a[p]
            self.assertEqual(r["events_offered"], 5233)
            self.assertEqual(r["events_emitted"], 5233)
            self.assertEqual(r["events_dropped"], 0)
            self.assertEqual(r["conservation_delta"], 0)

            # Check quantile monotonicity
            for metric in ("end_to_end_latency", "queue_wait", "service_time"):
                q = r["exact_quantiles_ns"][metric]
                self.assertLessEqual(q["p50"], q["p90"])
                self.assertLessEqual(q["p90"], q["p99"])
                self.assertLessEqual(q["p99"], q["p99.9"])
                self.assertGreaterEqual(q["p50"], 0.0)

        # Check Regime B
        self.assertIn("regime_b_burst", payload)
        regime_b = payload["regime_b_burst"]["results"]
        for p in policies:
            self.assertIn(p, regime_b, f"Missing policy {p} in Regime B")
            r = regime_b[p]
            self.assertEqual(r["events_offered"], 5233)
            self.assertEqual(r["events_emitted"], 5233)
            self.assertEqual(r["events_dropped"], 0)
            self.assertEqual(r["conservation_delta"], 0)

            for metric in ("end_to_end_latency", "queue_wait", "service_time"):
                q = r["exact_quantiles_ns"][metric]
                self.assertLessEqual(q["p50"], q["p90"])
                self.assertLessEqual(q["p90"], q["p99"])
                self.assertLessEqual(q["p99"], q["p99.9"])

        # Check Operating-Region Sweep
        self.assertIn("operating_region_burst_sweep", payload)
        sweep = payload["operating_region_burst_sweep"]["results"]
        for b_key in ("B_2", "B_5", "B_10", "B_20"):
            self.assertIn(b_key, sweep)
            for p in ("fixed_w1", "fixed_w8", "fixed_w32", "adaptive_grow"):
                self.assertIn(p, sweep[b_key])
                self.assertEqual(sweep[b_key][p]["conservation_delta"], 0)

        # Check Prospective Design
        self.assertIn("prospective_precision_design", payload)
        design = payload["prospective_precision_design"]
        self.assertEqual(design["target_epoch"], "KLS-10")
        self.assertEqual(design["practical_threshold_delta_us"], 500.0)
        self.assertIn("independent_units", design)
        self.assertIn("stopping_plan", design)


if __name__ == "__main__":
    unittest.main()
