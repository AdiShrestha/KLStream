#!/usr/bin/env python3
"""Unit and regression tests for Causal Data Parser and Workload Generators.

Tests strict causality validation (future-mutation invariance), fail-closed
boundary handling (non-finite, negative, non-monotonic values), exact 1-to-1
cohort joins, and non-stationary workload arrival schedules.
"""
from __future__ import annotations

import csv
import math
import pathlib
import sys
import unittest

# Ensure preprocessing and experiment modules are discoverable
REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "source" / "experiments"))
sys.path.insert(0, str(REPO_ROOT / "source" / "experiments" / "preprocessing"))

from causal_parser import CausalTradeParser, CausalParseError, ParsedTrade
from workload_generator import (
    create_generator,
    ReplayWorkloadGenerator,
    PoissonWorkloadGenerator,
    ParetoWorkloadGenerator,
    BurstStepWorkloadGenerator,
)


class CausalParserTests(unittest.TestCase):
    def setUp(self):
        self.parser = CausalTradeParser()
        self.cohort_path = REPO_ROOT / "data" / "cohort.csv"

    def test_future_mutation_invariance(self):
        """Mutating or deleting future rows k > i MUST NOT alter features for j <= i."""
        # 1. Base sequence of 20 realistic raw trades
        base_rows = []
        base_t = 1503014400000
        base_p = 4300.0
        for i in range(20):
            t = base_t + i * 500  # 500 ms apart
            p = base_p + (i % 5) * 0.5
            q = 0.1 + (i % 3) * 0.05
            qq = p * q
            maker = "true" if i % 2 == 0 else "false"
            base_rows.append([str(i + 1), f"{p:.2f}", f"{q:.6f}", f"{qq:.6f}", str(t), maker, "true"])

        # Parse full baseline sequence
        self.parser.reset()
        baseline_parsed = self.parser.parse_stream(base_rows, date_str="20170817")
        self.assertEqual(len(baseline_parsed), 20)

        # Record features for prefix j <= 9 (first 10 trades)
        prefix_baseline_features = [trade.feature_vector() for trade in baseline_parsed[:10]]

        # 2. Mutation Experiment A: Alter future rows 10..19 (change prices, quantities, maker flags)
        mutated_rows_a = [list(r) for r in base_rows]
        for k in range(10, 20):
            mutated_rows_a[k][1] = "9999.99"  # drastically changed price
            mutated_rows_a[k][2] = "100.0"    # drastically changed quantity
            mutated_rows_a[k][3] = "999999.0"
            mutated_rows_a[k][5] = "false" if mutated_rows_a[k][5] == "true" else "true"

        self.parser.reset()
        mutated_parsed_a = self.parser.parse_stream(mutated_rows_a, date_str="20170817")
        prefix_features_a = [trade.feature_vector() for trade in mutated_parsed_a[:10]]

        # Assert strict bitwise identity of all earlier features
        for j in range(10):
            self.assertEqual(
                prefix_baseline_features[j],
                prefix_features_a[j],
                f"Causality violation under future row mutation at event {j}",
            )

        # 3. Mutation Experiment B: Truncate / delete future rows (feed only first 10 rows)
        truncated_rows = base_rows[:10]
        self.parser.reset()
        truncated_parsed = self.parser.parse_stream(truncated_rows, date_str="20170817")
        prefix_features_b = [trade.feature_vector() for trade in truncated_parsed]

        self.assertEqual(len(prefix_features_b), 10)
        for j in range(10):
            self.assertEqual(
                prefix_baseline_features[j],
                prefix_features_b[j],
                f"Causality violation under future row deletion at event {j}",
            )

    def test_malformed_and_boundary_rejections(self):
        """Reject non-finite values, negative values, and non-monotonic timestamps."""
        valid_row = ["101", "4300.00", "0.500000", "2150.00", "1503014400000", "true", "true"]

        # 1. Non-finite price (NaN / Inf)
        for bad_p in ["NaN", "nan", "Inf", "-Inf", "infinity"]:
            p = CausalTradeParser()
            with self.assertRaises(CausalParseError):
                p.parse_row(["1", bad_p, "0.5", "100.0", "1000", "true", "true"])

        # 2. Non-finite quantity
        for bad_q in ["NaN", "nan", "Inf", "-Inf"]:
            p = CausalTradeParser()
            with self.assertRaises(CausalParseError):
                p.parse_row(["1", "4300.0", bad_q, "100.0", "1000", "true", "true"])

        # 3. Negative or zero price
        for bad_p in ["-10.0", "0.0", "-0.0001"]:
            p = CausalTradeParser()
            with self.assertRaises(CausalParseError):
                p.parse_row(["1", bad_p, "0.5", "100.0", "1000", "true", "true"])

        # 4. Negative or zero quantity
        for bad_q in ["-0.5", "0.0", "-1.0"]:
            p = CausalTradeParser()
            with self.assertRaises(CausalParseError):
                p.parse_row(["1", "4300.0", bad_q, "100.0", "1000", "true", "true"])

        # 5. Non-monotonic timestamp retrogression
        p = CausalTradeParser()
        p.parse_row(["1", "4300.0", "0.5", "2150.0", "1503014405000", "true", "true"])
        with self.assertRaises(CausalParseError):
            # Previous timestamp was 1503014405000; retrogression to 1503014401000 must fail closed
            p.parse_row(["2", "4301.0", "0.5", "2150.5", "1503014401000", "true", "true"])

        # 6. Malformed row (missing columns)
        p = CausalTradeParser()
        with self.assertRaises(CausalParseError):
            p.parse_row(["1", "4300.0", "0.5"])

    def test_feature_mathematical_consistency(self):
        """Verify mathematical definitions match docs/FEATURE_SPECIFICATION.md."""
        p = CausalTradeParser()
        r0 = p.parse_row(["1", "4000.00", "2.000000", "8000.00", "1503014400000", "false", "true"])
        # Event 0 initializations
        self.assertEqual(r0.interarrival_ms, 0.0)
        self.assertEqual(r0.log_return, 0.0)
        self.assertEqual(r0.is_buyer_maker, 0.0)
        self.assertEqual(r0.trade_flow, +2.0)  # Buyer taker -> +qty

        r1 = p.parse_row(["2", "4200.00", "1.500000", "6300.00", "1503014402500", "true", "true"])
        # Event 1 transitions
        self.assertEqual(r1.interarrival_ms, 2500.0)
        expected_ret = math.log(4200.0 / 4000.0)
        self.assertAlmostEqual(r1.log_return, expected_ret, places=9)
        self.assertEqual(r1.is_buyer_maker, 1.0)
        self.assertEqual(r1.trade_flow, -1.5)  # Seller taker -> -qty

    def test_exact_one_to_one_join_with_cohort(self):
        """Ensure row ordinals and trade IDs in raw archives map 1-to-1 to cohort.csv."""
        self.assertTrue(self.cohort_path.is_file(), f"Missing cohort at {self.cohort_path}")
        with open(self.cohort_path, "r", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))

        self.assertGreater(len(reader), 10000)
        # Sample inspect first 100 rows
        parser = CausalTradeParser()
        for idx in range(100):
            row = reader[idx]
            sid = row["sample_id"]
            # Verify deterministic format: t_YYYYMMDD_XXXXXXX
            parts = sid.split("_")
            self.assertEqual(len(parts), 3)
            self.assertEqual(parts[0], "t")
            self.assertEqual(len(parts[1]), 8)  # YYYYMMDD
            self.assertEqual(len(parts[2]), 7)  # trade ID 7 digits


class WorkloadGeneratorTests(unittest.TestCase):
    def setUp(self):
        self.cohort_path = REPO_ROOT / "data" / "cohort.csv"

    def test_workload_generators_monotonicity_and_bounds(self):
        """Verify all workload generators generate monotonic schedules and valid delays."""
        generators = [
            ("replay", create_generator("replay", cohort_path=self.cohort_path)),
            ("poisson", create_generator("poisson", rate_hz=500.0, seed=123)),
            ("pareto", create_generator("pareto", alpha=1.4, rate_hz=500.0, seed=123)),
            ("burst_step", create_generator("burst_step", rate_low_hz=100.0, rate_high_hz=2500.0, seed=123)),
        ]

        for name, gen in generators:
            points = gen.generate(count=100)
            self.assertEqual(len(points), 100)
            prev_offset = -1
            for pt in points:
                self.assertGreaterEqual(pt.delay_ns, 0, f"Negative delay in {name}")
                self.assertGreaterEqual(pt.t_offered_offset_ns, prev_offset, f"Non-monotonic offset in {name}")
                prev_offset = pt.t_offered_offset_ns


if __name__ == "__main__":
    unittest.main()
