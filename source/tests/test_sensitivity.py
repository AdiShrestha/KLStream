"""Unit and regression tests for KLS-11 Factorial Mechanisms & Sensitivity Analysis."""
from __future__ import annotations

import json
import pathlib
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
MANIFEST_PATH = DATA_DIR / "sensitivity_manifest.json"


class SensitivityTests(unittest.TestCase):
    def test_sensitivity_manifest_structure(self):
        """Validates schema, dimensions, and isolation boundaries of sensitivity manifest."""
        self.assertTrue(MANIFEST_PATH.is_file(), f"Missing sensitivity manifest at {MANIFEST_PATH}")
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        self.assertEqual(manifest["contract"], "KLS-11")
        self.assertEqual(manifest["isolation_boundary"]["evaluated_split"], "validation")
        self.assertEqual(manifest["isolation_boundary"]["evaluated_records"], 5233)
        self.assertTrue(manifest["isolation_boundary"]["test_holdout_sealed"])

        dims = manifest["factorial_dimensions"]
        self.assertIn("buffer_capacity", dims)
        self.assertIn("flush_deadline", dims)
        self.assertIn("controller_gain", dims)
        self.assertIn("ema_smoothing", dims)
        self.assertIn("burst_intensity", dims)
        self.assertIn("saturation_breakdown_c128", dims)

        # Check buffer capacities
        for c_key in ("C_128", "C_256", "C_512", "C_1024"):
            self.assertIn(c_key, dims["buffer_capacity"]["adaptive_grow"])
            self.assertIn(c_key, dims["buffer_capacity"]["fixed_w8"])

        # Check deadlines
        for d_key in ("T_100", "T_250", "T_500", "T_1000"):
            self.assertIn(d_key, dims["flush_deadline"]["adaptive_grow"])
            self.assertIn(d_key, dims["flush_deadline"]["fixed_w8"])

        # Check gains
        for g_key in ("gamma_1.1", "gamma_1.25", "gamma_1.5", "gamma_2.0"):
            self.assertIn(g_key, dims["controller_gain"])

        # Check alphas
        for a_key in ("alpha_0.05", "alpha_0.1", "alpha_0.2", "alpha_0.4"):
            self.assertIn(a_key, dims["ema_smoothing"])

    def test_event_conservation_invariants(self):
        """Validates that event conservation Delta_conservation == 0 holds across all configurations."""
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        dims = manifest["factorial_dimensions"]

        def check_run(run_dict: dict):
            self.assertEqual(run_dict["events_offered"], 5233)
            self.assertEqual(run_dict["events_emitted"], 5233)
            self.assertEqual(run_dict["conservation_delta"], 0)
            q = run_dict["exact_quantiles_ns"]["end_to_end_latency"]
            self.assertLessEqual(q["p50"], q["p90"])
            self.assertLessEqual(q["p90"], q["p99"])
            self.assertLessEqual(q["p99"], q["p99.9"])

        for pol in ("adaptive_grow", "fixed_w8"):
            for r in dims["buffer_capacity"][pol].values():
                check_run(r)
            for r in dims["flush_deadline"][pol].values():
                check_run(r)

        for r in dims["controller_gain"].values():
            check_run(r)
        for r in dims["ema_smoothing"].values():
            check_run(r)

    def test_deadband_stability_invariant(self):
        """Verifies that no batch size transitions occur when queue depth is within deadband."""
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        gains = manifest["factorial_dimensions"]["controller_gain"]
        for g_key, r in gains.items():
            self.assertEqual(
                r["deadband_oscillations"], 0,
                f"Deadband oscillation detected under gain {g_key}: {r['deadband_oscillations']} transitions"
            )

    def test_saturation_breakdown_advantage(self):
        """Verifies that adaptive microbatching retains tail containment at high rates over pointwise."""
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        sat = manifest["factorial_dimensions"]["saturation_breakdown_c128"]
        # At 15 kHz and 30 kHz, adaptive_grow retains superior tail containment over pointwise fixed_w1
        for rate_key in ("rate_15000", "rate_30000"):
            if rate_key in sat["adaptive_grow"] and rate_key in sat["fixed_w1"]:
                p99_adapt = sat["adaptive_grow"][rate_key]["exact_quantiles_ns"]["end_to_end_latency"]["p99"]
                p99_w1 = sat["fixed_w1"][rate_key]["exact_quantiles_ns"]["end_to_end_latency"]["p99"]
                self.assertLess(
                    p99_adapt, p99_w1,
                    f"Adaptive p99 ({p99_adapt} ns) should be less than fixed_w1 ({p99_w1} ns) at {rate_key}"
                )

        # Under burst surge (B=10, 5 kHz), adaptive_grow dramatically outperforms pointwise
        bursts = manifest["factorial_dimensions"]["burst_intensity"]
        p99_adapt_burst = bursts["adaptive_grow"]["B_10"]["exact_quantiles_ns"]["end_to_end_latency"]["p99"]
        p99_w1_burst = bursts["fixed_w1"]["B_10"]["exact_quantiles_ns"]["end_to_end_latency"]["p99"]
        self.assertLess(
            p99_adapt_burst, p99_w1_burst,
            f"Adaptive p99 ({p99_adapt_burst} ns) should outperform pointwise ({p99_w1_burst} ns) under B=10 burst"
        )


if __name__ == "__main__":
    unittest.main()
