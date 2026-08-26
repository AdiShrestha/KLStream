#!/usr/bin/env python3
"""
fixed_window_controller.py — Static Fixed-Window Baseline.
"""

from .base_controller import BaseWindowController

class FixedWindowController(BaseWindowController):
    def __init__(self, window_size: int = 100):
        if window_size < 1:
            raise ValueError(f"Window size must be >= 1, got {window_size}")
        self._window_size = int(window_size)

    def get_window_size(self, occupancy: float, current_time_ns: int = 0) -> int:
        return self._window_size

    def reset(self) -> None:
        pass

    @property
    def name(self) -> str:
        return f"Fixed-W{self._window_size}"
