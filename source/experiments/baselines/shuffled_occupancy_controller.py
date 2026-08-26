#!/usr/bin/env python3
"""
shuffled_occupancy_controller.py — Adversarial Control: Decoupled Random/Shuffled Feedback (MAR-X1).
"""

import random
from .base_controller import BaseWindowController

class ShuffledOccupancyController(BaseWindowController):
    """
    Decouples queue occupancy from window selection by generating pseudo-random
    occupancy values from the empirical distribution, breaking the closed-loop causal link.
    """
    def __init__(self, w_min: int = 10, w_max: int = 500, seed: int = 42):
        self.w_min = int(w_min)
        self.w_max = int(w_max)
        self.seed = int(seed)
        self.rng = random.Random(seed)

    def get_window_size(self, occupancy: float, current_time_ns: int = 0) -> int:
        # Generate random surrogate occupancy in [0.0, 1.0]
        fake_occ = self.rng.random()
        return int(self.w_min + fake_occ * (self.w_max - self.w_min))

    def reset(self) -> None:
        self.rng = random.Random(self.seed)

    @property
    def name(self) -> str:
        return f"Control-ShuffledOccupancy[seed={self.seed}]"
