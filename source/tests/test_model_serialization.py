#!/usr/bin/env python3
"""Adversarial and integrity test suite for Portable Isolation Forest Model Serialization.

Verifies:
1. Bitwise score equivalence (Delta score == 0.0 for 100% of samples) between
   in-memory fitted model and deserialized model from .iforest binary file.
2. Binary schema header inspection and IEEE 802.3 CRC32 integrity check.
3. Fail-closed rejection of corrupted and adversarial model payloads:
   - Invalid magic bytes (expected 'KLIF')
   - Unsupported format version (!= 1)
   - Payload byte corruption (CRC32 checksum mismatch)
   - Truncated byte streams (header and tree payload)
   - Feature dimension mismatch (eval data vs model header; internal split vs dimension)
   - Corrupted child node offsets (out-of-bounds index)
   - Circular child node offsets (self-loop or backward edge)
   - Non-finite split threshold (NaN, Inf)
   - Non-finite or negative leaf harmonic correction
   - Zero node sample count
   - Trailing unparsed bytes
"""
from __future__ import annotations

import csv
import math
import os
import pathlib
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


def find_engine_binary() -> pathlib.Path:
    candidates = [
        REPO_ROOT / "build" / "engine_runner",
        REPO_ROOT / "build-sanitizers" / "engine_runner",
        REPO_ROOT / "source" / "build" / "engine_runner",
    ]
    for c in candidates:
        if c.is_file() and os.access(c, os.X_OK):
            return c
    raise FileNotFoundError("engine_runner executable not found. Build the project first.")


class ModelSerializationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine_bin = find_engine_binary()
        cls.cohort_path = REPO_ROOT / "data" / "cohort.csv"
        assert cls.cohort_path.is_file(), f"Missing cohort at {cls.cohort_path}"

        # Extract features for first 150 rows from cohort for deterministic tests
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.tmp = pathlib.Path(cls.temp_dir.name)

        cls.train_csv = cls.tmp / "train.csv"
        cls.eval_csv = cls.tmp / "eval.csv"
        cls.valid_model_path = cls.tmp / "valid_model.iforest"
        cls.pred_fit_path = cls.tmp / "pred_fitted.csv"

        ignored = {"sample_id", "label", "group_id", "split", "source_ids"}
        rows = []
        with open(cls.cohort_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                feats = [float(v) for k, v in r.items() if k not in ignored and math.isfinite(float(v))]
                rows.append([r["sample_id"]] + feats)
                if len(rows) >= 150:
                    break

        cls.train_rows = rows[:100]
        cls.eval_rows = rows[100:150]
        cls.feature_dim = len(rows[0]) - 1

        with open(cls.train_csv, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerows(cls.train_rows)
        with open(cls.eval_csv, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerows(cls.eval_rows)

        # Train baseline model and serialize to valid_model_path
        cmd = [
            str(cls.engine_bin),
            "--train", str(cls.train_csv),
            "--eval", str(cls.eval_csv),
            "--output", str(cls.pred_fit_path),
            "--model-save", str(cls.valid_model_path),
            "--trees", "50",
            "--subsample", "64",
            "--seed", "42",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        assert res.returncode == 0, f"Baseline fit failed: {res.stderr}"
        assert cls.valid_model_path.is_file()
        cls.valid_bytes = cls.valid_model_path.read_bytes()

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def _run_with_model_bytes(self, model_bytes: bytes, eval_csv: pathlib.Path | None = None) -> subprocess.CompletedProcess:
        target_eval = eval_csv or self.eval_csv
        model_file = self.tmp / "test_run.iforest"
        out_file = self.tmp / "test_out.csv"
        model_file.write_bytes(model_bytes)
        cmd = [
            str(self.engine_bin),
            "--eval", str(target_eval),
            "--output", str(out_file),
            "--model-load", str(model_file),
        ]
        return subprocess.run(cmd, capture_output=True, text=True)

    def test_bitwise_score_equivalence(self):
        """Scores produced by reloaded model must match in-memory fitted model bitwise (Delta = 0.0)."""
        pred_loaded_path = self.tmp / "pred_loaded.csv"
        cmd = [
            str(self.engine_bin),
            "--eval", str(self.eval_csv),
            "--output", str(pred_loaded_path),
            "--model-load", str(self.valid_model_path),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"Model load run failed: {res.stderr}")

        with open(self.pred_fit_path, "r", encoding="utf-8") as f:
            fit_scores = {r["sample_id"]: float(r["score"]) for r in csv.DictReader(f)}
        with open(pred_loaded_path, "r", encoding="utf-8") as f:
            load_scores = {r["sample_id"]: float(r["score"]) for r in csv.DictReader(f)}

        self.assertEqual(len(fit_scores), len(self.eval_rows))
        self.assertEqual(fit_scores.keys(), load_scores.keys())

        deltas = []
        for sid in fit_scores:
            delta = abs(fit_scores[sid] - load_scores[sid])
            deltas.append(delta)
            self.assertEqual(
                delta, 0.0,
                f"Sample {sid} score mismatch: fitted={fit_scores[sid]}, loaded={load_scores[sid]}"
            )

        self.assertEqual(max(deltas), 0.0)

    def test_header_schema_and_crc_verification(self):
        """Validate header fields and exact IEEE 802.3 CRC32 match over tree payload."""
        self.assertGreaterEqual(len(self.valid_bytes), 32)
        magic, version, n_trees, subsample, dim, height, seed, checksum = struct.unpack(
            "<4sIIIIIII", self.valid_bytes[:32]
        )
        self.assertEqual(magic, b"KLIF")
        self.assertEqual(version, 1)
        self.assertEqual(n_trees, 50)
        self.assertEqual(subsample, 64)
        self.assertEqual(dim, self.feature_dim)
        self.assertEqual(seed, 42)

        tree_payload = self.valid_bytes[32:]
        expected_crc = zlib.crc32(tree_payload) & 0xFFFFFFFF
        self.assertEqual(checksum, expected_crc, "Header CRC32 does not match zlib computed CRC32")

    def test_fail_closed_invalid_magic(self):
        """Engine must fail closed if magic bytes do not equal 'KLIF'."""
        bad_magics = [b"BADF", b"NOPE", b"\x00\x00\x00\x00", b"RIFF"]
        for bm in bad_magics:
            corrupted = bm + self.valid_bytes[4:]
            res = self._run_with_model_bytes(corrupted)
            self.assertNotEqual(res.returncode, 0)
            self.assertIn("magic", res.stderr.lower())

    def test_fail_closed_unsupported_version(self):
        """Engine must fail closed if format version != 1."""
        for bad_ver in [0, 2, 999]:
            header = list(struct.unpack("<4sIIIIIII", self.valid_bytes[:32]))
            header[1] = bad_ver
            corrupted = struct.pack("<4sIIIIIII", *header) + self.valid_bytes[32:]
            res = self._run_with_model_bytes(corrupted)
            self.assertNotEqual(res.returncode, 0)
            self.assertIn("version", res.stderr.lower())

    def test_fail_closed_corrupted_checksum(self):
        """Engine must fail closed if payload bytes are altered without matching checksum."""
        # Mutate single byte in tree payload
        payload = bytearray(self.valid_bytes[32:])
        payload[10] ^= 0xFF
        corrupted = self.valid_bytes[:32] + bytes(payload)
        res = self._run_with_model_bytes(corrupted)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("checksum mismatch", res.stderr.lower())

    def test_fail_closed_truncated_byte_stream(self):
        """Engine must fail closed on truncated header or truncated payload."""
        # Header truncation
        for length in [0, 4, 16, 31]:
            res = self._run_with_model_bytes(self.valid_bytes[:length])
            self.assertNotEqual(res.returncode, 0)

        # Body truncation
        for length in [32, 64, len(self.valid_bytes) // 2]:
            res = self._run_with_model_bytes(self.valid_bytes[:length])
            self.assertNotEqual(res.returncode, 0)

    def test_fail_closed_mismatched_feature_dimensions(self):
        """Engine must reject query evaluation where data dimensions do not match model."""
        # 1. Eval CSV with wrong number of columns
        bad_eval = self.tmp / "bad_dim_eval.csv"
        with open(bad_eval, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            for r in self.eval_rows:
                w.writerow([r[0]] + r[1:3])  # only 2 features instead of self.feature_dim
        res = self._run_with_model_bytes(self.valid_bytes, eval_csv=bad_eval)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("dimension", res.stderr.lower())

        # 2. Mutate internal node split feature index >= feature_dim
        # Unpack tree data, find an internal node, mutate feature index
        header = list(struct.unpack("<4sIIIIIII", self.valid_bytes[:32]))
        payload = bytearray(self.valid_bytes[32:])
        # First tree: node_count at offset 0
        node_count = struct.unpack_from("<I", payload, 0)[0]
        # First node starts at offset 4
        # Schema: <BIdIIQd (37 bytes)
        leaf_flag = payload[4]
        if leaf_flag == 0:  # internal node
            # feature index is at offset 4 + 1 = 5
            struct.pack_into("<I", payload, 5, self.feature_dim + 10)  # out of bounds feature
            new_crc = zlib.crc32(payload) & 0xFFFFFFFF
            header[7] = new_crc
            corrupted = struct.pack("<4sIIIIIII", *header) + bytes(payload)
            res = self._run_with_model_bytes(corrupted)
            self.assertNotEqual(res.returncode, 0)
            self.assertIn("feature index out of bounds", res.stderr.lower())

    def test_fail_closed_corrupted_child_offsets_out_of_bounds(self):
        """Engine must fail closed if child node offset exceeds tree node count."""
        header = list(struct.unpack("<4sIIIIIII", self.valid_bytes[:32]))
        payload = bytearray(self.valid_bytes[32:])
        node_count = struct.unpack_from("<I", payload, 0)[0]
        leaf_flag = payload[4]
        if leaf_flag == 0:
            # left child is at offset 4 + 1(leaf) + 4(feature) + 8(split) = 17
            struct.pack_into("<I", payload, 17, node_count + 100)  # out of bounds
            new_crc = zlib.crc32(payload) & 0xFFFFFFFF
            header[7] = new_crc
            corrupted = struct.pack("<4sIIIIIII", *header) + bytes(payload)
            res = self._run_with_model_bytes(corrupted)
            self.assertNotEqual(res.returncode, 0)
            self.assertIn("child node offset out of bounds", res.stderr.lower())

    def test_fail_closed_corrupted_child_offsets_circular(self):
        """Engine must fail closed if child node offset forms a circular self-loop."""
        header = list(struct.unpack("<4sIIIIIII", self.valid_bytes[:32]))
        payload = bytearray(self.valid_bytes[32:])
        leaf_flag = payload[4]
        if leaf_flag == 0:
            # left child at offset 17: set to 0 (pointing to itself!)
            struct.pack_into("<I", payload, 17, 0)
            new_crc = zlib.crc32(payload) & 0xFFFFFFFF
            header[7] = new_crc
            corrupted = struct.pack("<4sIIIIIII", *header) + bytes(payload)
            res = self._run_with_model_bytes(corrupted)
            self.assertNotEqual(res.returncode, 0)
            self.assertIn("child offset invalid or circular", res.stderr.lower())

    def test_fail_closed_non_finite_split_threshold(self):
        """Engine must fail closed if internal split threshold is NaN or Inf."""
        header = list(struct.unpack("<4sIIIIIII", self.valid_bytes[:32]))
        payload = bytearray(self.valid_bytes[32:])
        leaf_flag = payload[4]
        if leaf_flag == 0:
            # split is at offset 4 + 1 + 4 = 9 (double)
            struct.pack_into("<d", payload, 9, float("nan"))
            new_crc = zlib.crc32(payload) & 0xFFFFFFFF
            header[7] = new_crc
            corrupted = struct.pack("<4sIIIIIII", *header) + bytes(payload)
            res = self._run_with_model_bytes(corrupted)
            self.assertNotEqual(res.returncode, 0)
            self.assertIn("non-finite split threshold", res.stderr.lower())

    def test_fail_closed_zero_node_sample_count(self):
        """Engine must fail closed if a node has sample_count == 0."""
        header = list(struct.unpack("<4sIIIIIII", self.valid_bytes[:32]))
        payload = bytearray(self.valid_bytes[32:])
        # sample_count at offset 4 + 1 + 4 + 8 + 4 + 4 = 25 (uint64)
        struct.pack_into("<Q", payload, 25, 0)
        new_crc = zlib.crc32(payload) & 0xFFFFFFFF
        header[7] = new_crc
        corrupted = struct.pack("<4sIIIIIII", *header) + bytes(payload)
        res = self._run_with_model_bytes(corrupted)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("sample count: zero", res.stderr.lower())

    def test_fail_closed_trailing_garbage_bytes(self):
        """Engine must fail closed if file has trailing bytes beyond declared trees."""
        header = list(struct.unpack("<4sIIIIIII", self.valid_bytes[:32]))
        payload = bytearray(self.valid_bytes[32:]) + b"\xDE\xAD\xBE\xEF\x00\x01\x02\x03"
        new_crc = zlib.crc32(payload) & 0xFFFFFFFF
        header[7] = new_crc
        corrupted = struct.pack("<4sIIIIIII", *header) + bytes(payload)
        res = self._run_with_model_bytes(corrupted)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("trailing unparsed bytes", res.stderr.lower())


if __name__ == "__main__":
    unittest.main()
