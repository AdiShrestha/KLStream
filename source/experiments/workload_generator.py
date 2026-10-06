#!/usr/bin/env python3
"""Non-Stationary Workload Arrival Generators for KLStream.

Generates monotonic offered arrival schedules (t_offered_ns offsets and interarrival deltas)
to stress test the queueing engine, microbatching operators, and occupancy controllers.

Supports:
  - replay: Exact reproduction of authentic Binance inter-arrival trade deltas.
  - poisson: Poisson point process with parameterized arrival rate lambda (events/sec).
  - pareto: Heavy-tailed burst arrival process with shape parameter alpha.
  - burst_step: Dual-state alternating schedule (baseline rate lambda_low transitioning to lambda_high).

Standard library only. No third-party dependencies.
"""
from __future__ import annotations

import argparse
import csv
import math
import pathlib
import random
import sys
from typing import NamedTuple, Sequence


class SchedulePoint(NamedTuple):
    event_id: int
    sample_id: str
    delay_ns: int
    t_offered_offset_ns: int


class WorkloadGenerator:
    """Base interface for workload arrival schedule generation."""

    def generate(self, count: int, sample_ids: Sequence[str] | None = None) -> list[SchedulePoint]:
        raise NotImplementedError


class ReplayWorkloadGenerator(WorkloadGenerator):
    """Replays authentic interarrival deltas from Binance trade cohort."""

    def __init__(self, cohort_path: pathlib.Path, time_scale: float = 1.0, max_delay_us: float | None = None):
        self.cohort_path = cohort_path
        self.time_scale = max(1e-9, float(time_scale))
        self.max_delay_us = float(max_delay_us) if max_delay_us is not None else None

    def generate(self, count: int, sample_ids: Sequence[str] | None = None) -> list[SchedulePoint]:
        points = []
        if not self.cohort_path.is_file():
            raise FileNotFoundError(f"Cohort file not found for replay: {self.cohort_path}")

        with open(self.cohort_path, "r", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))

        row_by_id = {r["sample_id"]: r for r in reader if "sample_id" in r}
        total = len(sample_ids) if sample_ids else (min(count, len(reader)) if count > 0 else len(reader))
        accum_ns = 0

        for i in range(total):
            sid = sample_ids[i] if (sample_ids and i < len(sample_ids)) else (reader[i].get("sample_id", f"ev_{i+1}") if i < len(reader) else f"ev_{i+1}")
            row = row_by_id.get(sid, reader[i] if i < len(reader) else {})
            inter_ms = float(row.get("interarrival_ms", 0.0))
            delay_ns = int(round(inter_ms * 1_000_000.0 * self.time_scale))
            if self.max_delay_us is not None:
                delay_ns = min(delay_ns, int(round(self.max_delay_us * 1000.0)))
            if delay_ns < 0:
                delay_ns = 0
            accum_ns += delay_ns
            points.append(SchedulePoint(
                event_id=i + 1,
                sample_id=sid,
                delay_ns=delay_ns,
                t_offered_offset_ns=accum_ns,
            ))
        return points


class PoissonWorkloadGenerator(WorkloadGenerator):
    """Poisson point process: inter-arrival times follow exponential distribution."""

    def __init__(self, rate_hz: float = 200.0, seed: int = 42):
        if rate_hz <= 0.0:
            raise ValueError(f"Arrival rate must be positive, got {rate_hz}")
        self.rate_hz = float(rate_hz)
        self.seed = int(seed)

    def generate(self, count: int, sample_ids: Sequence[str] | None = None) -> list[SchedulePoint]:
        rng = random.Random(self.seed)
        points = []
        accum_ns = 0

        for i in range(count):
            sid = sample_ids[i] if (sample_ids and i < len(sample_ids)) else f"s_{i+1:06d}"
            # Exponential inter-arrival: -ln(U) / lambda in seconds
            u = max(1e-15, min(1.0 - 1e-15, rng.random()))
            delta_sec = -math.log(u) / self.rate_hz
            delay_ns = max(1, int(round(delta_sec * 1_000_000_000.0)))
            accum_ns += delay_ns
            points.append(SchedulePoint(
                event_id=i + 1,
                sample_id=sid,
                delay_ns=delay_ns,
                t_offered_offset_ns=accum_ns,
            ))
        return points


class ParetoWorkloadGenerator(WorkloadGenerator):
    """Heavy-tailed burst arrival process with shape parameter alpha."""

    def __init__(self, alpha: float = 1.5, mean_rate_hz: float = 200.0, seed: int = 42):
        if alpha <= 1.0:
            raise ValueError(f"Pareto shape parameter must be > 1.0 for finite mean, got {alpha}")
        if mean_rate_hz <= 0.0:
            raise ValueError(f"Mean rate must be positive, got {mean_rate_hz}")
        self.alpha = float(alpha)
        self.mean_rate_hz = float(mean_rate_hz)
        self.seed = int(seed)
        # Expected value of Pareto(x_m, alpha) = alpha * x_m / (alpha - 1)
        mean_sec = 1.0 / self.mean_rate_hz
        self.x_m = mean_sec * (self.alpha - 1.0) / self.alpha

    def generate(self, count: int, sample_ids: Sequence[str] | None = None) -> list[SchedulePoint]:
        rng = random.Random(self.seed)
        points = []
        accum_ns = 0

        for i in range(count):
            sid = sample_ids[i] if (sample_ids and i < len(sample_ids)) else f"s_{i+1:06d}"
            u = max(1e-15, min(1.0 - 1e-15, rng.random()))
            # Pareto quantile: x_m * u^(-1/alpha)
            delta_sec = self.x_m * math.pow(u, -1.0 / self.alpha)
            delay_ns = max(1, int(round(delta_sec * 1_000_000_000.0)))
            accum_ns += delay_ns
            points.append(SchedulePoint(
                event_id=i + 1,
                sample_id=sid,
                delay_ns=delay_ns,
                t_offered_offset_ns=accum_ns,
            ))
        return points


class BurstStepWorkloadGenerator(WorkloadGenerator):
    """Dual-state alternating schedule transitioning between baseline rate and burst rate."""

    def __init__(
        self,
        rate_low_hz: float = 50.0,
        rate_high_hz: float = 2000.0,
        low_count: int = 50,
        high_count: int = 200,
        seed: int = 42,
    ):
        if rate_low_hz <= 0.0 or rate_high_hz <= 0.0:
            raise ValueError("Both low and high arrival rates must be positive")
        if low_count <= 0 or high_count <= 0:
            raise ValueError("Phase event counts must be positive integers")
        self.rate_low_hz = float(rate_low_hz)
        self.rate_high_hz = float(rate_high_hz)
        self.low_count = int(low_count)
        self.high_count = int(high_count)
        self.seed = int(seed)

    def generate(self, count: int, sample_ids: Sequence[str] | None = None) -> list[SchedulePoint]:
        rng = random.Random(self.seed)
        points = []
        accum_ns = 0
        cycle_len = self.low_count + self.high_count

        for i in range(count):
            sid = sample_ids[i] if (sample_ids and i < len(sample_ids)) else f"s_{i+1:06d}"
            pos = i % cycle_len
            is_burst = pos >= self.low_count
            current_rate = self.rate_high_hz if is_burst else self.rate_low_hz

            u = max(1e-15, min(1.0 - 1e-15, rng.random()))
            delta_sec = -math.log(u) / current_rate
            delay_ns = max(1, int(round(delta_sec * 1_000_000_000.0)))
            accum_ns += delay_ns
            points.append(SchedulePoint(
                event_id=i + 1,
                sample_id=sid,
                delay_ns=delay_ns,
                t_offered_offset_ns=accum_ns,
            ))
        return points


def create_generator(
    workload_type: str,
    cohort_path: pathlib.Path | None = None,
    rate_hz: float = 200.0,
    time_scale: float | None = None,
    max_delay_us: float | None = None,
    alpha: float = 1.5,
    rate_low_hz: float = 50.0,
    rate_high_hz: float = 2000.0,
    low_count: int = 50,
    high_count: int = 200,
    seed: int = 42,
) -> WorkloadGenerator:
    wtype = workload_type.lower().strip()
    if wtype == "replay":
        if cohort_path is None:
            raise ValueError("Replay workload generator requires cohort_path")
        scale = time_scale if time_scale is not None else (1.0 if rate_hz == 1.0 else (1.0 / rate_hz))
        return ReplayWorkloadGenerator(cohort_path=cohort_path, time_scale=scale, max_delay_us=max_delay_us)
    elif wtype == "poisson":
        return PoissonWorkloadGenerator(rate_hz=rate_hz, seed=seed)
    elif wtype == "pareto":
        return ParetoWorkloadGenerator(alpha=alpha, mean_rate_hz=rate_hz, seed=seed)
    elif wtype in ("burst_step", "burst"):
        return BurstStepWorkloadGenerator(
            rate_low_hz=rate_low_hz,
            rate_high_hz=rate_high_hz,
            low_count=low_count,
            high_count=high_count,
            seed=seed,
        )
    else:
        raise ValueError(f"Unknown workload type: {workload_type}. Must be replay, poisson, pareto, or burst_step.")


def write_schedule_csv(points: Sequence[SchedulePoint], output_path: pathlib.Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["event_id", "sample_id", "delay_ns", "t_offered_offset_ns"])
        for pt in points:
            writer.writerow([pt.event_id, pt.sample_id, pt.delay_ns, pt.t_offered_offset_ns])


def main():
    parser = argparse.ArgumentParser(description="KLStream Non-Stationary Workload Arrival Generator")
    parser.add_argument("--type", "-t", required=True, choices=["replay", "poisson", "pareto", "burst_step"], help="Workload schedule type")
    parser.add_argument("--output", "-o", required=True, help="Output schedule CSV path")
    parser.add_argument("--count", "-n", type=int, default=1000, help="Number of events to generate")
    parser.add_argument("--cohort", default=None, help="Cohort CSV for replay workload")
    parser.add_argument("--rate", type=float, default=200.0, help="Arrival rate in Hz for Poisson / Pareto")
    parser.add_argument("--alpha", type=float, default=1.5, help="Pareto shape parameter")
    parser.add_argument("--rate-low", type=float, default=50.0, help="Low arrival rate in Hz for burst_step")
    parser.add_argument("--rate-high", type=float, default=2000.0, help="Burst arrival rate in Hz for burst_step")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    cohort_path = pathlib.Path(args.cohort).resolve() if args.cohort else None
    gen = create_generator(
        workload_type=args.type,
        cohort_path=cohort_path,
        rate_hz=args.rate,
        alpha=args.alpha,
        rate_low_hz=args.rate_low,
        rate_high_hz=args.rate_high,
        seed=args.seed,
    )
    points = gen.generate(count=args.count)
    write_schedule_csv(points, pathlib.Path(args.output).resolve())
    print(f"Generated {len(points)} schedule points ({args.type}) to {args.output}")


if __name__ == "__main__":
    main()
