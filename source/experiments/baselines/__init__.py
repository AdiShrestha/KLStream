"""
Baselines Package for KLStream Evaluation Suite.
"""

from .base_controller import BaseWindowController
from .fixed_window_controller import FixedWindowController
from .unadaptive_streaming_controller import UnadaptiveStreamingController
from .ema_window_controller import EMAWindowController
from .shuffled_occupancy_controller import ShuffledOccupancyController
from .periodic_schedule_controller import PeriodicScheduleController

def get_controller(name: str, **kwargs) -> BaseWindowController:
    name_clean = name.lower().replace("-", "_")
    if "fixed" in name_clean:
        return FixedWindowController(window_size=kwargs.get("window_size", 100))
    elif "unadaptive" in name_clean:
        return UnadaptiveStreamingController()
    elif "ema" in name_clean or "adaptive" in name_clean:
        return EMAWindowController(
            w_min=kwargs.get("w_min", 10),
            w_max=kwargs.get("w_max", 500),
            alpha=kwargs.get("alpha", 0.2),
            deadband=kwargs.get("deadband", 0.05),
            target_occupancy=kwargs.get("target_occupancy", 0.5)
        )
    elif "shuffled" in name_clean:
        return ShuffledOccupancyController(
            w_min=kwargs.get("w_min", 10),
            w_max=kwargs.get("w_max", 500),
            seed=kwargs.get("seed", 42)
        )
    elif "periodic" in name_clean:
        return PeriodicScheduleController(
            w_min=kwargs.get("w_min", 10),
            w_max=kwargs.get("w_max", 500),
            period_events=kwargs.get("period_events", 500)
        )
    else:
        raise ValueError(f"Unknown controller baseline: {name}")

__all__ = [
    "BaseWindowController",
    "FixedWindowController",
    "UnadaptiveStreamingController",
    "EMAWindowController",
    "ShuffledOccupancyController",
    "PeriodicScheduleController",
    "get_controller"
]
