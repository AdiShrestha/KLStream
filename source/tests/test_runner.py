"""Unit and regression tests for KLStream Native Execution Runner."""
from __future__ import annotations

import csv
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest


class ExperimentRunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name).resolve()
        self.repo_root = pathlib.Path(__file__).resolve().parents[2]

        self.data_dir = self.root / "data"
        self.data_dir.mkdir(parents=True)
        self.cohort_path = self.data_dir / "cohort.csv"

        # Generate test cohort with train, validation, and test splits
        with open(self.cohort_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["sample_id", "label", "group_id", "split", "source_ids", "f1", "f2"])
            for i in range(24):
                split = "train" if i < 10 else ("validation" if i < 16 else "test")
                label = i % 2
                f1 = 5.0 + 0.1 * i if label == 1 else 0.0 + 0.05 * i
                f2 = 5.0 + 0.1 * i if label == 1 else 0.0 + 0.05 * i
                w.writerow([f"s{i}", label, f"g{i}", split, f"r{i}", f"{f1:.2f}", f"{f2:.2f}"])

    def tearDown(self):
        self.tmp.cleanup()

    def test_runner_execution_and_artifacts(self):
        run_dir = self.root / "run_001"
        runner_script = self.repo_root / "source" / "experiments" / "runner.py"

        res = subprocess.run(
            [
                sys.executable,
                str(runner_script),
                "--output-dir", str(run_dir),
                "--seed", "42",
                "--experiment-id", "exp_test",
                "--cohort", str(self.cohort_path),
                "--eval-splits", "validation,test",
            ],
            cwd=str(self.repo_root),
            capture_output=True,
            text=True,
        )

        self.assertEqual(res.returncode, 0, f"Runner failed:\nSTDOUT: {res.stdout}\nSTDERR: {res.stderr}")

        # Check predictions CSV
        pred_file = run_dir / "predictions.csv"
        self.assertTrue(pred_file.is_file())
        with open(pred_file, "r", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))
            self.assertEqual(len(reader), 14)  # 6 validation + 8 test
            for row in reader:
                self.assertIn("sample_id", row)
                self.assertIn("score", row)
                score = float(row["score"])
                self.assertTrue(0.0 <= score <= 1.0)

        # Check telemetry trace CSV
        trace_file = run_dir / "trace.csv"
        self.assertTrue(trace_file.is_file())
        with open(trace_file, "r", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))
            self.assertEqual(len(reader), 14)
            for row in reader:
                self.assertEqual(row["status"], "OK")
                self.assertGreater(float(row["latency_us"]), 0.0)

        # Check result JSON
        result_file = run_dir / "result.json"
        self.assertTrue(result_file.is_file())
        with open(result_file, "r", encoding="utf-8") as f:
            result = json.load(f)
            self.assertEqual(result["experiment_id"], "exp_test")
            self.assertEqual(result["seed"], 42)
            self.assertEqual(result["predictions"], "predictions.csv")
            self.assertEqual(result["method_evidence"], "method_evidence.txt")

        # Check method evidence text
        evidence_file = run_dir / "method_evidence.txt"
        self.assertTrue(evidence_file.is_file())
        text = evidence_file.read_text(encoding="utf-8")
        self.assertIn("Isolation Forest", text)
        self.assertIn("Event Conservation", text)


if __name__ == "__main__":
    unittest.main()
