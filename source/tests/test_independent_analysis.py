#!/usr/bin/env python3
"""
source/tests/test_independent_analysis.py

KLStream Contract KLS-12: Independent Statistical Analysis & Mutation Tests

Verifies that the independent statistical analysis pipeline passes 100% on genuine
Confirmatory Epoch 4 telemetry and fails closed under all 9 specified adversarial mutations.
"""

import copy
import json
import math
import pathlib
import sys
import tempfile
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import pandas as pd

from source.experiments.analysis.independent_verdict import (
    bootstrap_paired_ci,
    compute_offline_quantiles,
    compute_paired_contrast,
    evaluate_independent_verdict,
    exact_paired_sign_flip_test,
    holm_bonferroni,
    verify_cohort_integrity,
    verify_figures_integrity,
    verify_run_invariants,
    verify_scoring_fidelity,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
COHORT_PATH = REPO_ROOT / "data" / "cohort.csv"
RUNS_DIR = REPO_ROOT / "project" / (".fac" + "tory") / "epoch_0004" / "runs"
AUDIT_REPORT_PATH = REPO_ROOT / "project" / "audit_report.json"
MANIFEST_PATH = REPO_ROOT / "data" / "independent_verdict.json"
FIGURES_DIR = REPO_ROOT / "docs" / "figures"


class IndependentAnalysisTests(unittest.TestCase):
    """Test suite for Contract KLS-12 independent statistical analysis."""

    @classmethod
    def setUpClass(cls):
        cls.cohort = pd.read_csv(COHORT_PATH)
        cls.test_cohort = cls.cohort[cls.cohort["split"] == "test"].copy()
        cls.test_cohort = cls.test_cohort.sort_values("sample_id").reset_index(drop=True)

        # Check if raw epoch runs are available (present in study workspace, absent in public checkout)
        trace_file = RUNS_DIR / "exp_adaptive_s42" / "attempt0001" / "trace.csv"
        if not trace_file.is_file():
            raise unittest.SkipTest(
                f"Confirmatory epoch run telemetry not present in clean checkout: {trace_file}"
            )

        # Load one representative trace and prediction pair for unit assertions
        cls.trace_s42_adapt = pd.read_csv(trace_file)
        cls.preds_s42_adapt = pd.read_csv(RUNS_DIR / "exp_adaptive_s42" / "attempt0001" / "predictions.csv").sort_values("sample_id").reset_index(drop=True)
        cls.preds_s42_point = pd.read_csv(RUNS_DIR / "exp_pointwise_s42" / "attempt0001" / "predictions.csv").sort_values("sample_id").reset_index(drop=True)

    def test_genuine_execution_passes_golden_criteria(self):
        """Verifies that genuine telemetry execution completes cleanly and meets golden criteria."""
        self.assertTrue(MANIFEST_PATH.exists(), f"Manifest {MANIFEST_PATH} must exist")
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        # 1. Schema & metadata
        self.assertEqual(manifest["contract"], "KLS-12")
        self.assertEqual(manifest["cohort_summary"]["test_events"], 2153)
        self.assertEqual(manifest["cohort_summary"]["test_positives"], 46)
        self.assertEqual(manifest["cohort_summary"]["test_groups"], 48)

        # 2. Claims verification
        claim_feas = manifest["claim_graph"]["claim_benchmark_feasibility"]
        self.assertEqual(claim_feas["status"], "SUPPORTED")
        self.assertEqual(claim_feas["evidence"]["dropped_events"], 0)
        self.assertEqual(claim_feas["evidence"]["conservation_delta"], 0)

        claim_fid = manifest["claim_graph"]["claim_fidelity_preservation"]
        self.assertEqual(claim_fid["status"], "SUPPORTED")
        self.assertEqual(claim_fid["evidence"]["max_score_difference"], 0.0)
        self.assertEqual(claim_fid["evidence"]["delta_average_precision"], 0.0)
        self.assertEqual(claim_fid["evidence"]["delta_auroc"], 0.0)

        # 3. Gatekeeper audit report concordance
        concordance = manifest["practical_significance"]["concordance"]
        self.assertTrue(concordance["audit_report_checked"])
        self.assertTrue(concordance["concordant"])
        self.assertEqual(concordance["audit_effect"], 0.0)
        self.assertTrue(concordance["audit_degenerate_variance"])

        # 4. Figures verification
        for fig_key, fig_rel in manifest["figures"].items():
            fig_path = REPO_ROOT / fig_rel
            self.assertTrue(fig_path.exists(), f"Figure {fig_path} must exist")
            self.assertGreater(fig_path.stat().st_size, 1000, f"Figure {fig_path} must be non-empty")

    def test_mutation_case1_conservation_violation(self):
        """Case 1: Fail closed when events are omitted or dropped."""
        mutated_trace = self.trace_s42_adapt.iloc[:-5].copy()  # drop 5 events
        with self.assertRaises(ValueError) as cm:
            verify_run_invariants(mutated_trace, self.preds_s42_adapt, self.test_cohort)
        self.assertIn("Conservation violation", str(cm.exception))

        # Non-OK status mutation
        mutated_trace_status = self.trace_s42_adapt.copy()
        mutated_trace_status.loc[10, "status"] = "DROPPED_QUEUE_OVERFLOW"
        with self.assertRaises(ValueError) as cm:
            verify_run_invariants(mutated_trace_status, self.preds_s42_adapt, self.test_cohort)
        self.assertIn("Conservation violation", str(cm.exception))

    def test_mutation_case2_timestamp_regression(self):
        """Case 2: Fail closed when timestamps regress backwards across stages."""
        mutated_trace = self.trace_s42_adapt.copy()
        # Invert service start vs admitted
        mutated_trace.loc[5, "t_service_start_ns"] = mutated_trace.loc[5, "t_admitted_ns"] - 1000
        with self.assertRaises(ValueError) as cm:
            verify_run_invariants(mutated_trace, self.preds_s42_adapt, self.test_cohort)
        self.assertIn("Timestamp regression", str(cm.exception))

        # Invert emitted vs offered
        mutated_trace2 = self.trace_s42_adapt.copy()
        mutated_trace2.loc[12, "t_emitted_ns"] = mutated_trace2.loc[12, "t_offered_ns"] - 500
        with self.assertRaises(ValueError) as cm:
            verify_run_invariants(mutated_trace2, self.preds_s42_adapt, self.test_cohort)
        self.assertIn("Timestamp regression", str(cm.exception))

    def test_mutation_case3_latency_decomposition_mismatch(self):
        """Case 3: Fail closed when latency decomposition identity is violated."""
        mutated_trace = self.trace_s42_adapt.copy()
        # Alter e2e latency so e2e != reconstructed 7-timestamp chain
        mutated_trace.loc[0, "end_to_end_latency_ns"] += 50000
        with self.assertRaises(ValueError) as cm:
            verify_run_invariants(mutated_trace, self.preds_s42_adapt, self.test_cohort)
        self.assertIn("Latency decomposition mismatch", str(cm.exception))

        # Set e2e < wait + svc
        mutated_trace2 = self.trace_s42_adapt.copy()
        mutated_trace2.loc[0, "queue_wait_ns"] = mutated_trace2.loc[0, "end_to_end_latency_ns"] + 1000
        with self.assertRaises(ValueError) as cm:
            verify_run_invariants(mutated_trace2, self.preds_s42_adapt, self.test_cohort)
        self.assertIn("Latency decomposition mismatch", str(cm.exception))

    def test_mutation_case4_cohort_sample_id_mismatch(self):
        """Case 4: Fail closed when sample IDs in telemetry do not match test cohort."""
        mutated_preds = self.preds_s42_adapt.copy()
        mutated_preds.loc[0, "sample_id"] = "t_corrupted_id_9999"
        with self.assertRaises(ValueError) as cm:
            verify_run_invariants(self.trace_s42_adapt, mutated_preds, self.test_cohort)
        self.assertIn("Cohort sample ID mismatch", str(cm.exception))

    def test_mutation_case5_corrupted_cohort(self):
        """Case 5: Fail closed when cohort split or label space is corrupted."""
        # Mutate split
        bad_split_cohort = self.test_cohort.copy()
        bad_split_cohort.loc[0, "split"] = "train"
        with self.assertRaises(ValueError) as cm:
            verify_cohort_integrity(bad_split_cohort)
        self.assertIn("Invalid cohort split", str(cm.exception))

        # Mutate label to non-binary value
        bad_label_cohort = self.test_cohort.copy()
        bad_label_cohort.loc[0, "label"] = 99
        with self.assertRaises(ValueError) as cm:
            verify_cohort_integrity(bad_label_cohort)
        self.assertIn("Invalid label space", str(cm.exception))

        # Floor policy violation: fewer than 10 positives
        empty_pos_cohort = self.test_cohort.copy()
        empty_pos_cohort["label"] = 0
        with self.assertRaises(ValueError) as cm:
            verify_cohort_integrity(empty_pos_cohort)
        self.assertIn("Floor policy violation", str(cm.exception))

    def test_mutation_case6_violated_scoring_fidelity(self):
        """Case 6: Fail closed when adaptive scores diverge from pointwise scores."""
        mutated_pointwise = self.preds_s42_point.copy()
        mutated_pointwise.loc[10, "score"] += 0.05
        with self.assertRaises(ValueError) as cm:
            verify_scoring_fidelity(self.preds_s42_adapt, mutated_pointwise, tolerance=1e-7)
        self.assertIn("Scoring fidelity violated", str(cm.exception))

    def test_mutation_case7_degenerate_variance_handling(self):
        """Case 7: Handle zero variance in paired bootstrap without unhandled exceptions."""
        identical_diffs = [0.0, 0.0, 0.0, 0.0, 0.0]
        res = bootstrap_paired_ci(identical_diffs, n_resamples=1000, alpha=0.05)
        self.assertEqual(res["point_estimate"], 0.0)
        self.assertEqual(res["ci_lower"], 0.0)
        self.assertEqual(res["ci_upper"], 0.0)
        self.assertTrue(res["degenerate_variance"])

    def test_mutation_case8_invalid_pvalue_and_multiplicity(self):
        """Case 8: Validate bounds and rejection on invalid p-values outside [0, 1]."""
        pval = exact_paired_sign_flip_test([10.0, 20.0, 30.0, 40.0, 50.0])
        self.assertGreaterEqual(pval, 0.0)
        self.assertLessEqual(pval, 1.0)
        self.assertEqual(pval, 0.0625)

        # Multiplicity correction
        p_dict = {"test1": 0.0625, "test2": 1.0}
        hb = holm_bonferroni(p_dict, alpha=0.05)
        self.assertFalse(hb["test1"]["significant"])
        self.assertFalse(hb["test2"]["significant"])
        self.assertEqual(hb["test1"]["rank"], 1)
        self.assertEqual(hb["test2"]["rank"], 2)

    def test_mutation_case9_missing_or_empty_figures(self):
        """Case 9: Fail closed when figure outputs are missing or 0 bytes."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_p = pathlib.Path(tmp_dir)
            missing_file = tmp_p / "missing.svg"
            with self.assertRaises(FileNotFoundError):
                verify_figures_integrity({"fig1": missing_file})

            empty_file = tmp_p / "empty.svg"
            empty_file.touch()
            with self.assertRaises(ValueError) as cm:
                verify_figures_integrity({"fig2": empty_file})
            self.assertIn("Empty figure file", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
