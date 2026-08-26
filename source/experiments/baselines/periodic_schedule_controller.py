#!/usr/bin/env python3
"""
periodic_schedule_controller.py — Adversarial Control: Open-Loop Periodic Schedule (MAR-X1).
"""

import math
from .base_controller import BaseWindowController

class PeriodicScheduleController(BaseWindowController):
    """
    Open-loop sinusoidal periodic window oscillation independent of queue state.
    """
    def __init__(self, w_min: int = 10, w_max: int = 500, period_events: int = 500):
        self.w_min = int(w_min)
        self.w_max = int(w_max)
        self.period = int(period_events)
        self.tick_count = 0

    def get_window_size(self, occupancy: float, current_time_ns: int = 0) -> int:
        phase = (self.tick_count % self.period) / float(self.period)
        self.tick_count += 1
        sin_val = (math.sin(phase * 2.0 * math.pi) + 1.0) / 2.0 # in [0.0, 1.0]
        return int(self.w_min + sin_val * (self.w_max - self.w_min))

    def reset(self) -> None:
        self.tick_count = 0

    @property
    def name(self) -> str:
        return f"Control-PeriodicSchedule[period={self.period}]"
