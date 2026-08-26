#!/usr/bin/env python3
"""
base_controller.py — Unified Base Interface for Window Batching Controllers.
"""

from abc import ABC, abstractmethod

class BaseWindowController(ABC):
    """
    Abstract interface for window size selection policies.
    """
    
    @abstractmethod
    def get_window_size(self, occupancy: float, current_time_ns: int = 0) -> int:
        """
        Calculates the target window batch size given the current queue occupancy and timestamp.
        
        Args:
            occupancy: Current normalized queue occupancy in [0.0, 1.0].
            current_time_ns: Current simulation timestamp in nanoseconds.
            
        Returns:
            Integer batch window size w >= 1.
        """
        pass

    @abstractmethod
    def reset(self) -> None:
        """Resets internal controller state (counters, filters)."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable identifier of the controller strategy."""
        pass
