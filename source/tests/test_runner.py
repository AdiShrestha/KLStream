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
                self.assertEqual(row["policy_id"], "adaptive_grow")
                self.assertGreater(float(row["latency_us"]), 0.0)

                # Verify 7-timestamp per-event schema
                t_offered = int(row["t_offered_ns"])
                t_released = int(row["t_released_ns"])
                t_admitted = int(row["t_admitted_ns"])
                t_ready = int(row["t_batch_ready_ns"])
                t_service = int(row["t_service_start_ns"])
                t_finish = int(row["t_inference_finish_ns"])
                t_emitted = int(row["t_emitted_ns"])

                self.assertGreater(t_offered, 0)
                self.assertGreaterEqual(t_released, t_offered)
                self.assertGreaterEqual(t_admitted, t_released)
                self.assertGreaterEqual(t_finish, t_service)
                self.assertGreaterEqual(t_emitted, t_finish)

                # Verify latency decomposition columns
                q_wait = int(row["queue_wait_ns"])
                svc_time = int(row["service_time_ns"])
                e2e_lat = int(row["end_to_end_latency_ns"])

                self.assertEqual(q_wait, t_service - t_admitted)
                self.assertEqual(svc_time, t_finish - t_service)
                self.assertEqual(e2e_lat, t_emitted - t_offered)
                self.assertGreater(e2e_lat, 0)

        # Check result JSON
        result_file = run_dir / "result.json"
        self.assertTrue(result_file.is_file())
        with open(result_file, "r", encoding="utf-8") as f:
            result = json.load(f)
            self.assertEqual(result["experiment_id"], "exp_test")
            self.assertEqual(result["seed"], 42)
            self.assertEqual(result["predictions"], "predictions.csv")
            self.assertEqual(result["method_evidence"], "method_evidence.txt")
            self.assertIn("telemetry_summary", result)
            self.assertEqual(result["telemetry_summary"]["policy_id"], "adaptive_grow")
            quantiles = result["telemetry_summary"]["exact_quantiles_ns"]
            for metric in ("end_to_end_latency", "queue_wait", "service_time"):
                self.assertIn(metric, quantiles)
                for q in ("p50", "p90", "p99", "p99.9"):
                    self.assertIn(q, quantiles[metric])
                    self.assertGreaterEqual(quantiles[metric][q], 0.0)

        # Check method evidence text
        evidence_file = run_dir / "method_evidence.txt"
        self.assertTrue(evidence_file.is_file())
        text = evidence_file.read_text(encoding="utf-8")
        self.assertIn("Isolation Forest", text)
        self.assertIn("Event Conservation", text)
        self.assertIn("7-Timestamp Telemetry", text)
        self.assertIn("Exact Offline Quantiles", text)

    def test_policy_registry_semantic_equivalence_and_conservation(self):
        runner_script = self.repo_root / "source" / "experiments" / "runner.py"
        real_cohort = self.repo_root / "data" / "cohort.csv"
        self.assertTrue(real_cohort.is_file(), f"Missing authentic cohort at {real_cohort}")

        policies = [
            "fixed_w1",
            "fixed_w4",
            "fixed_w8",
            "fixed_w16",
            "fixed_w32",
            "fixed_w64",
            "deadline_flush",
            "adaptive_grow",
            "adaptive_shrink",
        ]

        scores_by_policy = {}
        for p in policies:
            run_dir = self.root / f"run_policy_{p}"
            res = subprocess.run(
                [
                    sys.executable,
                    str(runner_script),
                    "--output-dir", str(run_dir),
                    "--policy", p,
                    "--cohort", str(real_cohort),
                    "--eval-splits", "test",
                    "--seed", "42",
                ],
                cwd=str(self.repo_root),
                capture_output=True,
                text=True,
            )
            self.assertEqual(res.returncode, 0, f"Policy {p} execution failed:\nSTDOUT: {res.stdout}\nSTDERR: {res.stderr}")

            # 1. Verify trace.csv and conservation
            trace_file = run_dir / "trace.csv"
            self.assertTrue(trace_file.is_file())
            with open(trace_file, "r", encoding="utf-8") as f:
                trace_rows = list(csv.DictReader(f))

            self.assertEqual(len(trace_rows), 2153, f"Policy {p} did not emit all 2153 test events")
            for row in trace_rows:
                self.assertEqual(row["status"], "OK")
                self.assertEqual(row["policy_id"], p)

                # Monotonic timestamp ordering
                t_offered = int(row["t_offered_ns"])
                t_released = int(row["t_released_ns"])
                t_admitted = int(row["t_admitted_ns"])
                t_ready = int(row["t_batch_ready_ns"])
                t_service = int(row["t_service_start_ns"])
                t_finish = int(row["t_inference_finish_ns"])
                t_emitted = int(row["t_emitted_ns"])

                self.assertGreater(t_offered, 0)
                self.assertGreaterEqual(t_released, t_offered)
                self.assertGreaterEqual(t_admitted, t_released)
                self.assertGreaterEqual(t_finish, t_service)
                self.assertGreaterEqual(t_emitted, t_finish)

                # Decomposition identities
                q_wait = int(row["queue_wait_ns"])
                svc_time = int(row["service_time_ns"])
                e2e_lat = int(row["end_to_end_latency_ns"])
                self.assertEqual(q_wait, t_service - t_admitted)
                self.assertEqual(svc_time, t_finish - t_service)
                self.assertEqual(e2e_lat, t_emitted - t_offered)

            # 2. Verify predictions.csv
            pred_file = run_dir / "predictions.csv"
            self.assertTrue(pred_file.is_file())
            with open(pred_file, "r", encoding="utf-8") as f:
                pred_rows = list(csv.DictReader(f))
            self.assertEqual(len(pred_rows), 2153)
            scores_by_policy[p] = {r["sample_id"]: float(r["score"]) for r in pred_rows}

            # 3. Verify result.json telemetry summary
            result_file = run_dir / "result.json"
            self.assertTrue(result_file.is_file())
            with open(result_file, "r", encoding="utf-8") as f:
                res_json = json.load(f)
            self.assertEqual(res_json["telemetry_summary"]["policy_id"], p)
            self.assertEqual(res_json["telemetry_summary"]["configured_parameters"]["policy"], p)

        # 4. Verify Semantic Scoring Equivalence: Delta score == 0.0 across all policies
        base_scores = scores_by_policy["fixed_w1"]
        for p in policies[1:]:
            for sid, base_s in base_scores.items():
                policy_s = scores_by_policy[p][sid]
                self.assertEqual(
                    policy_s,
                    base_s,
                    f"Anomaly score divergence between {p} and fixed_w1 for sample {sid}: {policy_s} vs {base_s}"
                )


if __name__ == "__main__":
    unittest.main()
