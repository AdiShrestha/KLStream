# Quickstart Reproduction Guide (< 60 Seconds)

This guide walks through verifying the core KLStream streaming engine and executing the quickstart streaming demo in less than 60 seconds.

---

## 1. Prerequisites Check

Ensure you have CMake, a C++20 compiler, and Python 3 installed:

```bash
cmake --version
clang++ --version || g++ --version
python3 --version
```

---

## 2. Build the C++ Engine

From the repository root:

```bash
# Configure and build native binaries in Release mode
cmake -B build -S . -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel 2
```

This compiles:
- `build/engine_runner`: Native streaming engine runner with microbatch controller.
- `build/engine_tests`: Comprehensive unit test suite.

---

## 3. Run Automated Tests

Execute all registered CTest targets:

```bash
ctest --test-dir build --output-on-failure
```

Expected result: All test targets report `Passed` (100% pass rate).

---

## 4. Run the Quickstart Streaming Demo

Execute the streaming demo:

```bash
python3 source/experiments/demo.py
```

### Expected Output
```text
================================================================================
KLSTREAM: QUICKSTART STREAMING DEMO
================================================================================
Evaluating adaptive microbatching vs fixed pointwise baseline...
Dataset: Authentic Binance BTC/USDT validation split (5233 events)

[1/2] Executing policy: adaptive_grow...
  -> Status: COMPLETE (5233/5233 events processed, 0 dropped)
  -> Latency: p50=18331.0 us, p90=33120.0 us, p99=36412.0 us, p99.9=36780.0 us
  -> Queue Wait p99: 36015.0 us | Service Time p99: 572.0 us

[2/2] Executing policy: fixed_w1...
  -> Status: COMPLETE (5233/5233 events processed, 0 dropped)
  -> Latency: p50=9950.0 us, p90=18105.0 us, p99=19420.0 us, p99.9=19730.0 us
  -> Queue Wait p99: 19380.0 us | Service Time p99: 31.0 us

--------------------------------------------------------------------------------
DEMO SUMMARY:
  Event Conservation: 100.0% (5233 offered == 5233 emitted, 0 drops)
  Adaptive Batching Throughput: 5233 events in 937.4 ms
  Demo completed successfully in < 1 second.
================================================================================
```
