#!/usr/bin/env python3
"""
unadaptive_streaming_controller.py — Point-by-point serial streaming baseline (W=1).
"""

from .base_controller import BaseWindowController

class UnadaptiveStreamingController(BaseWindowController):
    def get_window_size(self, occupancy: float, current_time_ns: int = 0) -> int:
        return 1

    def reset(self) -> None:
        pass

    @property
    def name(self) -> str:
        return "Unadaptive-W1"
