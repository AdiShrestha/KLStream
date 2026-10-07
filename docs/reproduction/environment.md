# Experimental Environment & System Specifications

## 1. Primary Hardware Testbed

All experimental benchmarks and confirmatory evaluations reported in the manuscript were executed on the following reference testbed:

| Component | Specification |
|---|---|
| **System Model** | Apple MacBook Pro / Apple Silicon |
| **SoC / Processor** | Apple M3 (ARM64 architecture) |
| **CPU Core Topology** | 8 cores (4 Performance cores @ up to 4.05 GHz, 4 Efficiency cores @ up to 2.75 GHz) |
| **L1 Instruction / Data Cache** | 192 KB / 128 KB per performance core |
| **L2 Cache** | 16 MB shared across performance cluster; 4 MB across efficiency cluster |
| **System Memory (RAM)** | 16 GB Unified LPDDR5 Memory |
| **Memory Bandwidth** | Up to 100 GB/s unified bandwidth |
| **Storage** | 512 GB Apple APFS NVMe SSD |

---

## 2. Operating System & Software Stack

| Software Layer | Specification / Version |
|---|---|
| **Operating System** | macOS 14.7 (Darwin Kernel Version 27.0.0, ARM64) |
| **C++ Compiler** | Apple Clang version 16.0.0 (`clang-1600.0.26.4`) |
| **C++ Standard** | ISO C++20 (`-std=c++20`) |
| **Optimization Flags** | `-O3 -DNDEBUG` (Sanitizer builds: `-O1 -g -fsanitize=address,undefined`) |
| **Build System** | CMake 3.28.3 / Unix Makefiles |
| **Python Runtime** | Python 3.12.8 (CPython 64-bit ARM64) |
| **Python Dependencies** | Standard Library only (`math`, `csv`, `json`, `os`, `sys`, `hashlib`, `unittest`) |

---

## 3. Memory Footprint & Concurrency Characteristics

- **Resident Set Size (RSS):**
  - Native Engine (`engine_runner`): Peak RSS $< 65\,\text{MB}$.
  - Python Streaming Runner (`runner.py`): Peak RSS $< 180\,\text{MB}$.
  - Full Factorial Sweep (`run_sensitivity.py`): Peak RSS $< 350\,\text{MB}$.
  - Memory ceiling remains well under $8\,\text{GB}$ under all workloads.
- **Thread Pinning & QoS Constraints:**
  - On macOS, background tasks may experience thread migration between Performance and Efficiency cores under OS Quality of Service (QoS) throttling.
  - For lowest-jitter benchmarking, run benchmarks under High Performance QoS or disable background energy-saver throttling.
  - On Linux platforms, thread pinning via `taskset` or `pthread_setaffinity_np` to isolated cores is recommended.
