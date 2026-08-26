#!/usr/bin/env python3
"""
test_baselines.py — Unit tests for baseline window batching controllers and adversarial controls.
"""

import math
import sys
import unittest
from pathlib import Path

# Add experiments directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "experiments"))
from baselines import (
    FixedWindowController,
    UnadaptiveStreamingController,
    EMAWindowController,
    ShuffledOccupancyController,
    PeriodicScheduleController,
    get_controller
)

class TestBaselines(unittest.TestCase):
    def test_fixed_window_controller(self):
        c = FixedWindowController(window_size=50)
        self.assertEqual(c.name, "Fixed-W50")
        self.assertEqual(c.get_window_size(0.1), 50)
        self.assertEqual(c.get_window_size(0.9), 50)
        
        with self.assertRaises(ValueError):
            FixedWindowController(window_size=0)

    def test_unadaptive_streaming_controller(self):
        c = UnadaptiveStreamingController()
        self.assertEqual(c.name, "Unadaptive-W1")
        self.assertEqual(c.get_window_size(0.0), 1)
        self.assertEqual(c.get_window_size(1.0), 1)

    def test_ema_adaptive_window_controller(self):
        c = EMAWindowController(w_min=10, w_max=500, alpha=0.5, deadband=0.05, target_occupancy=0.5)
        self.assertEqual(c.w_min, 10)
        self.assertEqual(c.w_max, 500)
        
        # High occupancy drives window up
        for _ in range(10):
            w = c.get_window_size(0.95)
        self.assertGreater(w, 10)
        self.assertLessEqual(w, 500)
        
        # Low occupancy drives window down
        for _ in range(20):
            w = c.get_window_size(0.05)
        self.assertEqual(w, 10)

    def test_shuffled_occupancy_controller(self):
        c1 = ShuffledOccupancyController(w_min=10, w_max=500, seed=42)
        c2 = ShuffledOccupancyController(w_min=10, w_max=500, seed=42)
        
        seq1 = [c1.get_window_size(0.5) for _ in range(20)]
        seq2 = [c2.get_window_size(0.5) for _ in range(20)]
        
        self.assertEqual(seq1, seq2)
        for val in seq1:
            self.assertGreaterEqual(val, 10)
            self.assertLessEqual(val, 500)

    def test_periodic_schedule_controller(self):
        period = 100
        c = PeriodicScheduleController(w_min=10, w_max=500, period_events=period)
        
        vals = [c.get_window_size(0.5) for _ in range(period)]
        self.assertEqual(len(vals), period)
        self.assertAlmostEqual(vals[0], (10 + 500) // 2, delta=20) # sin(0) is mid-level
        self.assertGreaterEqual(max(vals), 480) # near peak
        self.assertLessEqual(min(vals), 30)   # near trough

    def test_factory_get_controller(self):
        self.assertIsInstance(get_controller("fixed", window_size=200), FixedWindowController)
        self.assertIsInstance(get_controller("unadaptive"), UnadaptiveStreamingController)
        self.assertIsInstance(get_controller("ema"), EMAWindowController)
        self.assertIsInstance(get_controller("shuffled"), ShuffledOccupancyController)
        self.assertIsInstance(get_controller("periodic"), PeriodicScheduleController)
        
        with self.assertRaises(ValueError):
            get_controller("unknown_baseline")

if __name__ == "__main__":
    unittest.main()
