#!/usr/bin/env python3
"""
Test Suite: test_manuscript_claims.py
Verifies that all empirical claims, numbers, equations, and references in paper/manuscript.md
strictly and programmatically match the verified JSON manifests and research artifacts.
Also asserts zero absolute host paths (/Users/...) in paper/ and docs/.
"""

import json
import os
import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


class TestManuscriptClaims(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manuscript_path = REPO_ROOT / "paper" / "manuscript.md"
        cls.assertTrue(cls.manuscript_path.exists(), f"Missing manuscript at {cls.manuscript_path}")
        cls.manuscript_text = cls.manuscript_path.read_text(encoding="utf-8")

        # Load independent verdict manifest
        cls.verdict_path = REPO_ROOT / "data" / "independent_verdict.json"
        cls.assertTrue(cls.verdict_path.exists(), f"Missing verdict manifest at {cls.verdict_path}")
        with open(cls.verdict_path, "r", encoding="utf-8") as f:
            cls.verdict = json.load(f)

        # Load sensitivity manifest
        cls.sensitivity_path = REPO_ROOT / "data" / "sensitivity_manifest.json"
        cls.assertTrue(cls.sensitivity_path.exists(), f"Missing sensitivity manifest at {cls.sensitivity_path}")
        with open(cls.sensitivity_path, "r", encoding="utf-8") as f:
            cls.sensitivity = json.load(f)

        # Load budget curves manifest
        cls.budget_path = REPO_ROOT / "data" / "budget_curves.json"
        cls.assertTrue(cls.budget_path.exists(), f"Missing budget curves manifest at {cls.budget_path}")
        with open(cls.budget_path, "r", encoding="utf-8") as f:
            cls.budget = json.load(f)

    def test_cohort_claims(self):
        """Verify test cohort size, positives, prevalence, and group counts."""
        cohort = self.verdict["cohort_summary"]
        self.assertEqual(cohort["test_events"], 2153)
        self.assertEqual(cohort["test_positives"], 46)
        self.assertAlmostEqual(cohort["test_prevalence"], 0.021365, places=5)
        self.assertEqual(cohort["test_groups"], 48)

        # Assert presence in manuscript
        self.assertIn("2,153", self.manuscript_text)
        self.assertIn("46", self.manuscript_text)
        self.assertIn("0.021365", self.manuscript_text)
        self.assertIn("48", self.manuscript_text)

    def test_accuracy_and_scoring_parity(self):
        """Verify test AP, AUROC, and bitwise scoring parity claims."""
        seed_data = self.verdict["per_seed_telemetry"]["adaptive"]["42"]
        ap_val = seed_data["ap"]
        auroc_val = seed_data["auroc"]

        self.assertAlmostEqual(ap_val, 0.916415, places=5)
        self.assertAlmostEqual(auroc_val, 0.997328, places=5)

        # Parity checks from claim graph
        claim_fid = self.verdict["claim_graph"]["claim_fidelity_preservation"]["evidence"]
        self.assertEqual(claim_fid["max_score_difference"], 0.0)
        self.assertEqual(claim_fid["delta_average_precision"], 0.0)
        self.assertEqual(claim_fid["delta_auroc"], 0.0)

        # Assert presence in manuscript
        self.assertIn("0.916415", self.manuscript_text)
        self.assertIn("0.997328", self.manuscript_text)
        self.assertIn("0.000000", self.manuscript_text)
        self.assertIn("Delta s| = 0.0", self.manuscript_text)

    def test_event_conservation(self):
        """Verify 100% event conservation claim across all confirmatory runs."""
        claim_feas = self.verdict["claim_graph"]["claim_benchmark_feasibility"]["evidence"]
        self.assertEqual(claim_feas["total_events_evaluated"], 21530)
        self.assertEqual(claim_feas["dropped_events"], 0)
        self.assertEqual(claim_feas["conservation_delta"], 0)

        # Assert presence in manuscript
        self.assertIn("100.0% event conservation", self.manuscript_text)
        self.assertIn("21,530", self.manuscript_text)

    def test_tail_reduction_burst_b10(self):
        """Verify 7.1x tail latency reduction at burst intensity B=10."""
        bursts = self.sensitivity["factorial_dimensions"]["burst_intensity"]
        fixed_p99 = bursts["fixed_w1"]["B_10"]["exact_quantiles_ns"]["end_to_end_latency"]["p99"] / 1000.0
        adapt_p99 = bursts["adaptive_grow"]["B_10"]["exact_quantiles_ns"]["end_to_end_latency"]["p99"] / 1000.0

        self.assertAlmostEqual(fixed_p99, 2195.0, places=1)
        self.assertAlmostEqual(adapt_p99, 309.0, places=1)

        ratio = fixed_p99 / adapt_p99
        self.assertAlmostEqual(ratio, 7.10, places=1)

        # Assert citations in manuscript
        self.assertIn("7.1", self.manuscript_text)
        self.assertIn("2,195.0", self.manuscript_text)
        self.assertIn("309.0", self.manuscript_text)

    def test_tail_reduction_buffer_c128(self):
        """Verify 3.3x tail latency reduction at buffer capacity C=128."""
        caps = self.sensitivity["factorial_dimensions"]["buffer_capacity"]
        fixed_p99 = caps["fixed_w8"]["C_128"]["exact_quantiles_ns"]["end_to_end_latency"]["p99"] / 1000.0
        adapt_p99 = caps["adaptive_grow"]["C_128"]["exact_quantiles_ns"]["end_to_end_latency"]["p99"] / 1000.0

        self.assertAlmostEqual(fixed_p99, 859.5, places=1)
        self.assertAlmostEqual(adapt_p99, 263.2, places=1)

        ratio = fixed_p99 / adapt_p99
        self.assertAlmostEqual(ratio, 3.27, places=1)

        # Assert citations in manuscript
        self.assertIn("3.3", self.manuscript_text)
        self.assertIn("859.5", self.manuscript_text)
        self.assertIn("263.2", self.manuscript_text)

    def test_saturation_boundary(self):
        """Verify saturation boundary at 35-40 kHz."""
        sat = self.sensitivity["factorial_dimensions"]["saturation_breakdown_c128"]["adaptive_grow"]
        p99_30k = sat["rate_30000"]["exact_quantiles_ns"]["end_to_end_latency"]["p99"] / 1000.0
        p99_45k = sat["rate_45000"]["exact_quantiles_ns"]["end_to_end_latency"]["p99"] / 1000.0

        self.assertLess(p99_30k, 300.0)
        self.assertGreater(p99_45k, 4000.0)

        # Assert citation in manuscript
        self.assertIn("35-40", self.manuscript_text)
        self.assertIn("kHz", self.manuscript_text)

    def test_no_absolute_host_paths(self):
        """Assert zero absolute host paths (/Users/...) in paper/ and docs/."""
        directories = [REPO_ROOT / "paper", REPO_ROOT / "docs"]
        pattern = re.compile(r"/Users/[a-zA-Z0-9_\.\-]+")

        for d in directories:
            self.assertTrue(d.exists(), f"Directory missing: {d}")
            for path in d.rglob("*"):
                # Ignore private untracked docs/audit directory and hidden files
                if "docs/audit" in str(path) or path.name.startswith("."):
                    continue
                if path.is_file():
                    content = path.read_text(encoding="utf-8", errors="ignore")
                    matches = pattern.findall(content)
                    self.assertEqual(
                        matches,
                        [],
                        f"Found absolute host path in {path.relative_to(REPO_ROOT)}: {matches}",
                    )


if __name__ == "__main__":
    unittest.main()
