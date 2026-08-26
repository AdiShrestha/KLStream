#!/usr/bin/env python3
"""
capture_hardware_info.py — Captures system hardware metadata and compiles micro-benchmark report.

Governing Invariants:
- NFR-001: Performance target validation (>10M ops/sec SPSC, <500ns scoring)
- NFR-004: Hardware isolation and platform metadata documentation
- MAR-X5: Benchmarking grounded in exact hardware reality
"""

import argparse
import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

def get_cpu_info() -> Dict[str, Any]:
    info = {
        "machine": platform.machine(),
        "processor": platform.processor(),
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version()
    }
    
    if platform.system() == "Darwin":
        try:
            brand = subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"], text=True).strip()
            cores_phys = int(subprocess.check_output(["sysctl", "-n", "hw.physicalcpu"], text=True).strip())
            cores_log = int(subprocess.check_output(["sysctl", "-n", "hw.logicalcpu"], text=True).strip())
            mem_bytes = int(subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True).strip())
            info.update({
                "model_name": brand,
                "physical_cores": cores_phys,
                "logical_cores": cores_log,
                "ram_bytes": mem_bytes,
                "ram_gb": round(mem_bytes / (1024**3), 2)
            })
        except Exception as e:
            info["error"] = str(e)
    elif platform.system() == "Linux":
        try:
            with open("/proc/cpuinfo", "r") as f:
                lines = f.readlines()
            for line in lines:
                if "model name" in line:
                    info["model_name"] = line.split(":")[1].strip()
                    break
            info["logical_cores"] = os.cpu_count()
        except Exception as e:
            info["error"] = str(e)
            
    return info

def main():
    parser = argparse.ArgumentParser(description="Capture hardware platform metadata and compile benchmark report")
    parser.add_argument("--queue-bench", default="results/queue_benchmarks.json", help="Queue benchmark results JSON")
    parser.add_argument("--model-bench", default="results/model_benchmarks.json", help="Model benchmark results JSON")
    parser.add_argument("--output", default="results/hardware_benchmark_report.json", help="Output aggregated report JSON")
    args = parser.parse_args()
    
    cpu_meta = get_cpu_info()
    
    queue_data = {}
    q_path = Path(args.queue_bench)
    if q_path.exists():
        with open(q_path, "r") as f:
            queue_data = json.load(f)
            
    model_data = {}
    m_path = Path(args.model_bench)
    if m_path.exists():
        with open(m_path, "r") as f:
            model_data = json.load(f)
            
    spsc_mops = queue_data.get("spsc", {}).get("million_ops_per_sec", 0.0)
    scoring_mean_ns = model_data.get("mean_latency_ns", 0.0)
    
    spsc_pass = spsc_mops > 10.0
    scoring_pass = 0.0 < scoring_mean_ns < 500.0
    
    report = {
        "manifest_version": "1.0.0",
        "governing_invariants": ["NFR-001", "NFR-004", "MAR-X5"],
        "overall_status": "PASS" if (spsc_pass and scoring_pass) else "FAIL",
        "spsc_target_mops": 10.0,
        "scoring_target_max_ns": 500.0,
        "hardware_platform": cpu_meta,
        "compiler_info": {
            "cxx_standard": "C++17",
            "optimization_flags": "-O3 -DNDEBUG",
            "python_version": platform.python_version()
        },
        "microbenchmarks": {
            "queue_throughput": queue_data,
            "model_scoring": model_data
        },
        "performance_targets": {
            "spsc_target_mops": 10.0,
            "spsc_measured_mops": spsc_mops,
            "spsc_pass": spsc_pass,
            "scoring_target_max_ns": 500.0,
            "scoring_measured_mean_ns": scoring_mean_ns,
            "scoring_pass": scoring_pass,
            "overall_status": "PASS" if (spsc_pass and scoring_pass) else "FAIL"
        }
    }

    
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)
        
    print(f"Hardware benchmark report compiled to {out_path}")
    print(f"  CPU: {cpu_meta.get('model_name', 'Unknown')}")
    print(f"  SPSC Queue Throughput: {spsc_mops:.2f} Mops/sec (Target > 10.0 Mops/sec: {spsc_pass})")
    print(f"  Model Scoring Latency: {scoring_mean_ns:.2f} ns (Target < 500.0 ns: {scoring_pass})")
    print(f"  Overall Status: {report['performance_targets']['overall_status']}")

if __name__ == "__main__":
    main()
