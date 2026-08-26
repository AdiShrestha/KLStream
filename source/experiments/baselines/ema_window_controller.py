#!/usr/bin/env python3
"""
ema_window_controller.py — Closed-loop adaptive window controller with EMA occupancy filtering.
"""

from .base_controller import BaseWindowController

class EMAWindowController(BaseWindowController):
    def __init__(self, w_min: int = 10, w_max: int = 500, alpha: float = 0.2, deadband: float = 0.05, target_occupancy: float = 0.5):
        self.w_min = int(w_min)
        self.w_max = int(w_max)
        self.alpha = float(alpha)
        self.deadband = float(deadband)
        self.target_occupancy = float(target_occupancy)
        self.current_w = int(w_min)
        self.ema_occ = 0.0
        self.initialized = False

    def get_window_size(self, occupancy: float, current_time_ns: int = 0) -> int:
        occ = max(0.0, min(1.0, float(occupancy)))
        if not self.initialized:
            self.ema_occ = occ
            self.initialized = True
        else:
            self.ema_occ = self.alpha * occ + (1.0 - self.alpha) * self.ema_occ

        diff = self.ema_occ - self.target_occupancy
        if abs(diff) > self.deadband:
            # Proportional adaptation
            norm = (self.ema_occ - self.target_occupancy) / max(self.target_occupancy, 1.0 - self.target_occupancy)
            step = int(norm * (self.w_max - self.w_min) * 0.25)
            self.current_w = max(self.w_min, min(self.w_max, self.current_w + step))

        return self.current_w

    def reset(self) -> None:
        self.current_w = self.w_min
        self.ema_occ = 0.0
        self.initialized = False

    @property
    def name(self) -> str:
        return f"Adaptive-EMA[W{self.w_min}-W{self.w_max}]"
