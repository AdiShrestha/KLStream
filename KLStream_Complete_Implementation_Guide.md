# KLStream — Complete Implementation Guide

### A Kafka-less Parallel Stream Processing Runtime for Multi-Core Systems (Apple M3 Target)

This document is the single source of truth for the KLStream project. It contains the
full architecture, every core data structure, every operator, the build system, the
example pipelines, the testing and benchmarking strategy, and the research extensions
that turn this from a class project into a systems-research platform. Everything here
is derived from the architectural spec you started with, plus deep research into prior
art (FastFlow, BriskStream, WindFlow, LightSaber, StreamBox, the Zeuch VLDB'19 hardware
analysis paper) and Apple Silicon (M3) specifics.

If you follow this document section by section, you can rebuild the entire project
from nothing — no other reference material is required.

---

## Table of Contents

1. [Project Overview & Goals](#1-project-overview--goals)
2. [Design Philosophy — Why These Choices](#2-design-philosophy--why-these-choices)
3. [System Architecture](#3-system-architecture)
4. [Repository File Structure](#4-repository-file-structure)
5. [Development Environment Setup (Apple M3 MacBook Air)](#5-development-environment-setup-apple-m3-macbook-air)
6. [Core Concepts & Terminology (Glossary)](#6-core-concepts--terminology-glossary)
7. [Core Runtime Library](#7-core-runtime-library)
   - 7.1 [`config.hpp` — Shared Constants](#71-confighpp--shared-constants)
   - 7.2 [`event.hpp` — The Event Type](#72-eventhpp--the-event-type)
   - 7.3 [`spsc_queue.hpp` — Lock-Free SPSC Ring Buffer](#73-spsc_queuehpp--lock-free-spsc-ring-buffer)
   - 7.4 [`mpmc_queue.hpp` — Bounded MPMC Queue](#74-mpmc_queuehpp--bounded-mpmc-queue)
   - 7.5 [`operator.hpp` — The Operator Interface](#75-operatorhpp--the-operator-interface)
   - 7.6 [`pinning.hpp` — Core Affinity Hints for Apple Silicon](#76-pinninghpp--core-affinity-hints-for-apple-silicon)
   - 7.7 [`metrics.hpp` — Counters & Latency Histogram](#77-metricshpp--counters--latency-histogram)
   - 7.8 [`backpressure.hpp` — EMA Tracker & Adaptive Rate Limiter](#78-backpressurehpp--ema-tracker--adaptive-rate-limiter)
   - 7.9 [`worker.hpp` — Worker Thread & Execution Loop](#79-workerhpp--worker-thread--execution-loop)
   - 7.10 [`runtime.hpp` — The Runtime](#710-runtimehpp--the-runtime)
8. [Standard Operator Library](#8-standard-operator-library)
   - 8.1 [Source Operator](#81-source-operator)
   - 8.2 [Map Operator](#82-map-operator)
   - 8.3 [Filter Operator](#83-filter-operator)
   - 8.4 [Aggregate Operator](#84-aggregate-operator)
   - 8.5 [Tumbling Count Window](#85-tumbling-count-window)
   - 8.6 [Tumbling Time Window](#86-tumbling-time-window)
   - 8.7 [Sink Operator](#87-sink-operator)
9. [Build System — CMakeLists.txt](#9-build-system--cmakeliststxt)
10. [Example 1 — Basic End-to-End Pipeline](#10-example-1--basic-end-to-end-pipeline)
11. [Example 2 — Yahoo Streaming Benchmark (YSB) Pipeline](#11-example-2--yahoo-streaming-benchmark-ysb-pipeline)
12. [Testing Strategy (GoogleTest)](#12-testing-strategy-googletest)
13. [Benchmarking Strategy (Google Benchmark)](#13-benchmarking-strategy-google-benchmark)
14. [Research Extensions](#14-research-extensions)
    - 14.1 [Adaptive Backpressure Evaluation](#141-adaptive-backpressure-evaluation)
    - 14.2 [P-core / E-core Aware Scheduling Evaluation](#142-p-core--e-core-aware-scheduling-evaluation)
    - 14.3 [Consistent-Hashing Operator Placement (Advanced)](#143-consistent-hashing-operator-placement-advanced)
    - 14.4 [GraphBuilder DSL (Future Work)](#144-graphbuilder-dsl-future-work)
15. [Phased Implementation Roadmap](#15-phased-implementation-roadmap)
16. [Build & Run Cheat Sheet](#16-build--run-cheat-sheet)
17. [Key Design Decisions & Trade-offs](#17-key-design-decisions--trade-offs)
18. [References & Prior Art Mapping](#18-references--prior-art-mapping)

---

## 1. Project Overview & Goals

KLStream is a **stream processing runtime** — not an application. It executes a
**dataflow graph** of long-running **operators** connected by **bounded, lock-free
queues**, processing an unbounded sequence of **events** with **explicit backpressure**
and **multi-core scheduling**, entirely in-process, with no external broker (no Kafka,
no network, no persistence layer).

### What KLStream Must Do (Functional Goals)

- Execute a directed acyclic graph (DAG) of operators: `Source → Map → Filter → Aggregate → Sink` (and arbitrary variations).
- Process events with **at-most-once-per-queue ordering** (FIFO within a single queue; no global ordering guarantee).
- Enforce **bounded memory** — every queue has a fixed capacity decided at construction time. Nothing grows unbounded.
- Propagate **backpressure** automatically: if a downstream operator's input queue is full, the upstream operator blocks (or self-throttles) rather than dropping data or growing memory.
- Run on a **fixed-size worker thread pool**, statically assigned to operators, executing a cooperative scheduling loop.
- Expose **metrics**: events/sec per operator, queue occupancy, and latency percentiles (p50/p99).
- Build and run correctly on an **Apple M3 MacBook Air** (8-core: 4 Performance + 4 Efficiency cores, 128-byte cache lines, ARM64/AArch64).

### What KLStream Must NOT Do (Non-Goals)

- No distributed execution, no network communication, no multi-node coordination.
- No persistence / durability / exactly-once fault tolerance (this is what makes it "Kafka-less" — and it's an intentional simplification, not a missing feature).
- No JVM, no garbage collector, no dynamic language runtime.
- No support for cyclic graphs (the dataflow graph is a DAG by construction).

### The One-Sentence Summary

> KLStream is a Kafka-less parallel stream processing runtime that executes continuous
> dataflow graphs on multi-core systems using bounded lock-free queues, explicit
> backpressure, and cooperative multi-threaded scheduling — with two research
> extensions (adaptive backpressure and Apple-Silicon-aware operator placement) that
> give it genuine novelty beyond a standard class project.

---

## 2. Design Philosophy — Why These Choices

Every significant design decision below is backed by something found in the prior-art
research. This section exists so that when you (or a reviewer) ask "why did you do it
this way?", you have a documented answer.

### 2.1 Why C++17 (not Rust, not Java, not C++20-only features)

- WindFlow (the most complete modern C++ streaming library, IEEE TPDS 2021) is C++17, header-only. Matching this makes KLStream comparable and lets you read WindFlow's source as a reference without language-version friction.
- The Zeuch et al. VLDB 2019 paper's central finding is that **JVM-based engines carry up to 80x overhead** versus hand-written C++. This is KLStream's foundational justification for using C++ at all.
- C++17 gives us everything we need: `std::atomic`, aligned `operator new` (`std::align_val_t`), `std::function`, structured bindings, `if constexpr`. We deliberately avoid `std::jthread`/`std::stop_token` (C++20) because Apple Clang's libc++ support for these has historically lagged — `std::thread` + `std::atomic<bool>` is more portable and just as correct.

### 2.2 Why Virtual-Dispatch Operators (not CRTP / templates-only)

Research into FastFlow and WindFlow revealed two competing designs:

- **CRTP / template-based (zero virtual-call overhead)** — used internally by FastFlow for its lowest layer. Extremely fast but produces enormous template-instantiation complexity and compile times, and is much harder to extend as a student project.
- **Virtual dispatch (`IOperator` base class with a `tick()` virtual method)** — one indirect call per operator per scheduling tick. For I/O- and memory-bound streaming workloads (which is almost all of them — the bottleneck is the queue, not the dispatch), the overhead of a single virtual call (a few nanoseconds) is negligible compared to the cost of a cache miss on the queue (tens to hundreds of nanoseconds).

**Decision: virtual dispatch.** It matches the original architecture spec's
`init()/process()/shutdown()` interface, it is dramatically simpler to implement and
extend, and the performance cost is not the bottleneck. If you later want to explore
CRTP as its own research question ("does static polymorphism measurably help in a
bounded-queue runtime?"), that is a clean fifth research extension — but it is not
required for the MVP.

### 2.3 Why a Ring-Buffer SPSC Queue with Cached Indices (rigtorp-style)

The classic naive queue uses a single `std::atomic<size_t> count` that both producer
and consumer increment/decrement — this creates **false sharing**: every push and every
pop touches the *same* cache line from *different* cores, causing constant cache-line
ping-pong (MESI invalidation traffic) across the core-to-core interconnect.

The **rigtorp SPSCQueue** design (a widely-used, heavily-benchmarked open-source
single-producer/single-consumer queue) solves this with two techniques:

1. **Separate `write_idx` and `read_idx` atomics**, each on its own cache line (`alignas(128)` on Apple Silicon, vs. `alignas(64)` on x86).
2. **Cached copies**: the producer keeps a *local, non-atomic* cached copy of `read_idx` and only re-reads the real atomic when the cache says "might be full." The consumer does the mirror image for `write_idx`. This means that in the common case (queue neither full nor empty), **neither thread ever touches the other thread's cache line.**

This is why Section 7.3 below pads each atomic index to its own 128-byte line and
maintains the cached counterparts.

### 2.4 Why 128 Bytes for Cache Line Padding (not 64)

On x86 (Intel/AMD), the L1 cache line is 64 bytes, and `std::hardware_destructive_interference_size` is typically 64. **Apple Silicon (M1/M2/M3) reports a 128-byte cache line** (`sysctl -n hw.cachelinesize` returns `128`). Padding to 64 bytes on an M3 would put two "independent" atomics in the *same* 128-byte line, reintroducing false sharing. KLStream therefore defines `CACHE_LINE_SIZE = 128` centrally (Section 7.1) and uses it for every `alignas()` in the hot path.

### 2.5 Why Bounded Queues + Blocking Backpressure as the Baseline

This is directly from the original architecture spec (Section 8 of the original
problem description) and is also how FastFlow's lowest layer behaves: `push()` either
succeeds or fails (queue full); a failed push means the operator's `tick()` returns
`Blocked`, and on the *next* tick it retries the *same* event (it never popped its
input, so nothing is lost). This single mechanism gives you, for free:

- **Bounded memory** (queue capacity is fixed at construction).
- **Backward propagation of slowdown** — if the sink can't keep up, the operator before it stops popping its input, which fills *that* queue, which stops the operator before *that* — all the way back to the source.
- **No explicit "backpressure protocol"** is needed between operators; it emerges from the queue's `push()`/`pop()` contract.

### 2.6 Why Add Adaptive (EMA-based) Backpressure as an Extension, Not the Baseline

The literature (GOVERNOR/ICAC 2017 for Spark, Flink's credit-based flow control) shows
that **binary block/unblock backpressure causes latency spikes** — the queue fills
completely before anything slows down, and then the source is fully blocked until the
queue drains. A **gradual, predictive** approach (exponential moving average of queue
occupancy feeding a token-bucket rate limiter on the source) should reduce p99 latency
variance. No prior work has evaluated this specifically in a single-node, in-memory
C++ runtime — this is Gap 2 from the research brief, and Section 14.1 gives you the
full experimental design.

### 2.7 Why Apple QoS Classes Instead of `pthread_setaffinity_np` for "Pinning"

On Linux/x86, you'd use `pthread_setaffinity_np` to pin a thread to a specific core
index. **macOS does not expose this for arbitrary core pinning** on Apple Silicon —
`thread_affinity_policy` exists but is a *hint* for cache-affinity grouping, not a
P-core/E-core selector, and Apple's own guidance is that **Quality of Service (QoS)
classes are the supported mechanism** for influencing whether a thread is scheduled on
a Performance or Efficiency core. `QOS_CLASS_USER_INTERACTIVE` biases strongly toward
P-cores; `QOS_CLASS_BACKGROUND` biases strongly toward E-cores. Section 7.6 wraps this
in a small `CoreAffinity` enum so the rest of the codebase never touches `pthread`
directly — and so that the code still compiles (as a no-op) on non-Apple platforms.

---

## 3. System Architecture

KLStream is organized into the same conceptual layers as the original specification,
mapped onto concrete C++ headers:

```text
┌─────────────────────────────────────────────────────────────────┐
│                     7. Stream Graph Definition                    │
│   (main.cpp wires queues + operators; optional GraphBuilder DSL)  │
├─────────────────────────────────────────────────────────────────┤
│  8. Standard Operator Library                                      │
│   Source │ Map │ Filter │ Aggregate │ Window │ Sink                │
│   (each is an IOperator subclass — operators/*.hpp)                │
├─────────────────────────────────────────────────────────────────┤
│  7.5 Operator Execution Layer                                       │
│   IOperator: init() / tick() -> OpStatus / shutdown()               │
├─────────────────────────────────────────────────────────────────┤
│  7.3 / 7.4 Communication Layer (Queues)                              │
│   SPSCQueue<T>  (1 producer, 1 consumer — default)                  │
│   MPMCQueue<T>  (N producers, N consumers — multi-instance ops)     │
├─────────────────────────────────────────────────────────────────┤
│  7.8 Backpressure & Flow Control Layer                               │
│   Baseline: push() returns false -> OpStatus::Blocked               │
│   Extension: EMAOccupancyTracker + AdaptiveRateLimiter               │
├─────────────────────────────────────────────────────────────────┤
│  7.9 / 7.10 Threading & Scheduling Layer                             │
│   WorkerThread (1 per core, executes assigned operators)            │
│   Runtime (assigns operators -> workers, start/stop)                 │
│   Backoff: spin (ARM `yield`) -> std::this_thread::yield -> sleep    │
├─────────────────────────────────────────────────────────────────┤
│  7.6 Runtime Coordination / Core-Affinity Layer                      │
│   CoreAffinity hints via macOS QoS classes (P-core vs E-core)        │
├─────────────────────────────────────────────────────────────────┤
│  7.7 Metrics & Monitoring Layer                                      │
│   Counter (events/sec), LatencyHistogram (p50/p99)                   │
└─────────────────────────────────────────────────────────────────┘
```

### 3.1 Data Flow Through the System

```text
   [Source]──push──>(SPSCQueue)──pop──>[Map]──push──>(SPSCQueue)──pop──>[Filter]
       ▲                  │ full?            │              │ full?         │
       │                  ▼                  │              ▼               ▼
   (rate limiter,     Blocked = upstream  (Blocked         Blocked     ──push──>(SPSCQueue)──pop──>[Sink]
    Section 14.1)      retries same event  propagates)     propagates)
```

Every arrow that says "push" can fail. A failed push means: don't advance, don't drop
data, return `OpStatus::Blocked` from `tick()`, and try again on the next scheduling
round. This is the entire backpressure mechanism in its baseline form.

### 3.2 Threading Model at a Glance

On an 8-core M3 (4P + 4E):

```text
Worker 0 (P-core hint) → [Source, Map]
Worker 1 (P-core hint) → [Filter]
Worker 2 (P-core hint) → [Aggregate]
Worker 3 (E-core hint) → [Sink]
```

Operator-to-worker assignment is **static** (decided once at startup), matching the
"static pinning recommended initially" guidance from the original spec, and matching
how FastFlow's lowest layer operates (one thread per pipeline stage).

---

## 4. Repository File Structure

This is the complete directory layout. Every file referenced anywhere in this document
has its exact path shown here.

```text
KLStream/
├── CMakeLists.txt
├── README.md
├── .gitignore
│
├── include/
│   └── klstream/
│       ├── core/
│       │   ├── config.hpp
│       │   ├── event.hpp
│       │   ├── spsc_queue.hpp
│       │   ├── mpmc_queue.hpp
│       │   ├── operator.hpp
│       │   ├── pinning.hpp
│       │   ├── metrics.hpp
│       │   ├── backpressure.hpp
│       │   ├── worker.hpp
│       │   └── runtime.hpp
│       └── operators/
│           ├── source.hpp
│           ├── map.hpp
│           ├── filter.hpp
│           ├── aggregate.hpp
│           ├── window.hpp
│           └── sink.hpp
│
├── examples/
│   ├── CMakeLists.txt
│   ├── basic_pipeline/
│   │   └── main.cpp
│   └── yahoo_streaming_benchmark/
│       └── main.cpp
│
├── tests/
│   ├── CMakeLists.txt
│   ├── test_spsc_queue.cpp
│   ├── test_mpmc_queue.cpp
│   ├── test_operators.cpp
│   ├── test_backpressure.cpp
│   └── test_pipeline_integration.cpp
│
├── benchmarks/
│   ├── CMakeLists.txt
│   ├── bench_spsc_queue.cpp
│   ├── bench_pipeline_throughput.cpp
│   └── bench_ysb.cpp
│
├── research/
│   ├── adaptive_backpressure/
│   │   ├── main.cpp
│   │   └── run_experiment.sh
│   ├── core_pinning/
│   │   ├── main.cpp
│   │   └── run_experiment.sh
│   └── results/
│
└── scripts/
    ├── check_environment.sh
    └── run_all_benchmarks.sh
```

**Total core library:** 10 headers in `core/` + 6 in `operators/` = 16 header-only
files. No `.cpp` files needed for the library itself. This mirrors WindFlow's
header-only design: anything that includes `klstream/...` headers only needs
`-I include` and `-pthread`.

---

## 5. Development Environment Setup (Apple M3 MacBook Air)

Run through this once before writing any code.

### 5.1 Install the Toolchain

```bash
# Apple Clang + make, ar, ranlib
xcode-select --install

# Homebrew
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# CMake and Ninja (faster than make for large rebuilds)
brew install cmake ninja

# Optional: newer LLVM for latest sanitizer diagnostics
brew install llvm
```

### 5.2 Verify Hardware Assumptions

KLStream bakes in two hardware constants: `CACHE_LINE_SIZE = 128` and the
4P+4E core layout. Confirm them on your machine:

```bash
# Must print 128 on any Apple Silicon Mac
sysctl -n hw.cachelinesize

# Total logical cores — 8 on base M3 MacBook Air
sysctl -n hw.ncpu

# Performance cores (fastest tier)
sysctl -n hw.perflevel0.physicalcpu     # expect 4

# Efficiency cores (slower/low-power tier)
sysctl -n hw.perflevel1.physicalcpu     # expect 4
```

If `hw.cachelinesize` ever returns `64` (e.g., you test on an Intel Mac or a Linux
x86 CI box), change `CACHE_LINE_SIZE` in `config.hpp` to `64`. Everything else
adapts automatically because every `alignas()` in the hot path references that
one constant.

### 5.3 Confirm Compiler Version and CPU Flag

```bash
clang++ --version
# Apple clang version 15.x or later (Xcode 15+) is recommended

# Verify -mcpu=apple-m3 is recognized
echo 'int main(){return 0;}' | clang++ -mcpu=apple-m3 -x c++ - -o /tmp/t && echo OK
```

If `-mcpu=apple-m3` is not recognized (older Xcode), use `-mcpu=apple-m1` instead
(ISA is forward-compatible) or `-march=native`. The CMakeLists.txt in Section 9
does an automatic `check_cxx_compiler_flag` probe for exactly this.

### 5.4 Sanitizer Check

ThreadSanitizer (TSan) is non-negotiable for a lock-free-queue project. A single
wrong `memory_order` will produce a data race that is otherwise nearly impossible
to reproduce. Confirm TSan works before writing any concurrent code:

```bash
cat > /tmp/tsan_test.cpp << 'EOF'
#include <thread>
int x = 0;
int main() {
    std::thread t([]{ x = 1; });
    x = 2;
    t.join();
    return x;
}
EOF
clang++ -fsanitize=thread -std=c++17 /tmp/tsan_test.cpp -o /tmp/tsan_test
/tmp/tsan_test
# Expect "WARNING: ThreadSanitizer: data race" — confirms TSan is active.
```

---

## 6. Core Concepts & Terminology (Glossary)

Every term below is used precisely and consistently throughout the entire codebase.

| Term | Definition |
|---|---|
| **Event** | The atom of data: `klstream::Event<Payload>` holding a `timestamp_ns`, `key`, `seq`, and `data` field. |
| **Operator** | An `IOperator` subclass that reads from input queues, applies user logic, and writes to output queues. Never terminates on its own. |
| **Edge / Queue** | A bounded, lock-free queue connecting one operator's output to another's input. Default: `SPSCQueue`. Multi-instance operators use `MPMCQueue`. |
| **DAG** | The pipeline topology. Operators are nodes; queues are directed edges. Cycles are forbidden. |
| **`tick()`** | The single method every operator implements. Does one unit of work and returns an `OpStatus`. Called repeatedly by the owning `WorkerThread`. |
| **`OpStatus`** | Three-value return of `tick()`: `Idle` (no input), `Processed` (one event handled), `Blocked` (output queue full — backpressure). |
| **Backpressure** | Implicit mechanism: a full output queue returns `Blocked`, the operator does not pop its input, and retries the same event next `tick()`. Propagates backwards automatically. |
| **Bounded Queue** | Every queue has a fixed `capacity` set at construction. This is what makes memory usage bounded regardless of runtime duration or input burstiness. |
| **Cache Line / False Sharing** | Smallest unit of cache-coherency tracking (128 bytes on Apple M-series, 64 bytes on most x86). False sharing occurs when two cores write to variables on the same cache line, causing constant invalidation traffic. Avoided using `alignas(CACHE_LINE_SIZE)`. |
| **EMA** | Exponential Moving Average: `ema = alpha * current + (1 - alpha) * ema_prev`. Used to smooth queue-occupancy into a trend for adaptive backpressure. |
| **QoS Class** | macOS scheduling hint: `QOS_CLASS_USER_INTERACTIVE` biases the thread toward P-cores; `QOS_CLASS_BACKGROUND` biases toward E-cores. The only way to influence P/E assignment on macOS. |
| **P-core / E-core** | Apple M3's asymmetric core types. 4 Performance cores (~4 GHz, high IPC) and 4 Efficiency cores (~2.75 GHz, much lower power). |
| **Worker Thread** | One `std::thread` owning a fixed list of operators, running the scheduling loop for the program's lifetime. |
| **Runtime** | Top-level object that accepts `(operator, affinity)` pairs, assigns them to `WorkerThread`s, and manages start/stop. |
| **Tumbling Window** | Non-overlapping fixed-size grouping of events, either by count (every N events) or by time (every T nanoseconds). |
| **Throughput** | Events processed per second. Primary benchmark metric. |
| **p50 / p99 Latency** | Latency values below which 50% / 99% of events fall. Measured from `Event::timestamp_ns` (set at source) to sink processing time. |
| **SPSC / MPMC** | Single-Producer-Single-Consumer / Multi-Producer-Multi-Consumer queue variants. SPSC is always preferred; MPMC is used only when multiple operator instances share one queue. |
| **Spin / Yield / Sleep Backoff** | Three-tier idle strategy in `WorkerThread`: ARM `yield` instruction → `std::this_thread::yield()` → `sleep_for(100ns)`. Balances latency vs. power. |
| **Static Operator Assignment** | Operators are assigned to worker threads once at startup and never migrate. Matches FastFlow's one-thread-per-stage model. |

---

---

## 7. Core Runtime Library

All files live in `include/klstream/core/`. Each section below gives the complete
header — copy it verbatim into the corresponding file.

---

### 7.1 `config.hpp` — Shared Constants

This is the single file that every other header includes. All hardware-dependent
constants live here so that porting to a different machine means changing exactly
one file.

```cpp
// include/klstream/core/config.hpp
#pragma once
#include <cstddef>
#include <cstdint>

namespace klstream {

// ── Cache line size ────────────────────────────────────────────────────────
// Apple Silicon (M1/M2/M3): hw.cachelinesize = 128.
// x86-64 (Intel/AMD):        64.
// Verify on your machine:  sysctl -n hw.cachelinesize
//
// IMPORTANT: Every alignas() in the hot path uses this constant.
// If you port to x86 change this to 64 — everything else adapts automatically.
#if defined(__aarch64__)
  inline constexpr std::size_t CACHE_LINE_SIZE = 128;
#else
  inline constexpr std::size_t CACHE_LINE_SIZE = 64;
#endif

// ── Queue defaults ─────────────────────────────────────────────────────────
// Default capacity for all queues created without an explicit size argument.
// Must be a power of 2 (required by the MPMC queue's bitmask trick).
// 4096 events × sizeof(Event<uint64_t>) = ~64 KB per queue — fits in L2 cache.
inline constexpr std::size_t DEFAULT_QUEUE_CAPACITY = 4096;

// ── Backpressure thresholds ────────────────────────────────────────────────
// Soft threshold: when EMA occupancy fraction exceeds this, start throttling.
inline constexpr double BP_SOFT_THRESHOLD = 0.70;
// Hard threshold: when instantaneous occupancy exceeds this, block immediately.
inline constexpr double BP_HARD_THRESHOLD = 0.95;

// ── Worker backoff parameters ──────────────────────────────────────────────
// How many ARM `yield` spins before escalating to std::this_thread::yield().
inline constexpr int SPIN_BEFORE_YIELD = 64;
// How many std::this_thread::yield() calls before escalating to sleep.
inline constexpr int YIELD_BEFORE_SLEEP = 32;
// Sleep duration in nanoseconds when all operators are Idle.
inline constexpr int SLEEP_NS = 100;

// ── Metrics ───────────────────────────────────────────────────────────────
// Reporting interval in seconds for the metrics printer.
inline constexpr int METRICS_INTERVAL_SEC = 1;

// ── Latency histogram ─────────────────────────────────────────────────────
// Number of buckets. Each bucket covers 1 microsecond up to MAX_LATENCY_US,
// then a final overflow bucket.
inline constexpr std::size_t HISTOGRAM_BUCKETS = 10000;
inline constexpr std::size_t MAX_LATENCY_US    = 10000; // 10 ms

} // namespace klstream
```

---

### 7.2 `event.hpp` — The Event Type

```cpp
// include/klstream/core/event.hpp
#pragma once
#include "config.hpp"
#include <cstdint>
#include <chrono>

namespace klstream {

// ── Event<Payload> ────────────────────────────────────────────────────────
//
// The atom of data in KLStream. Templated on Payload so the type system
// prevents accidentally routing an Event<AdEvent> into an operator that
// expects Event<uint64_t>.
//
// Design notes:
//   * timestamp_ns: set by the source at creation time using a monotonic clock.
//     Used to compute end-to-end latency at the sink. Never modified by
//     intermediate operators.
//   * key: for keyed streams (e.g., consistent-hashing placement, Section 14.3).
//     Ignored by stateless operators (Map, Filter). Stateful operators
//     (Aggregate, Window) use it to group events.
//   * seq: monotonically increasing sequence number set by the source. Used in
//     tests to verify ordering is preserved within a single queue.
//   * data: the user-defined payload. Must be trivially copyable for lock-free
//     queue correctness (no internal pointers, no vtable, no reference counting).
//
// Alignment: alignas(CACHE_LINE_SIZE) would waste space for small payloads.
// We leave the struct naturally aligned and rely on the queue's own ring
// buffer being cache-line aligned. The struct should be kept small (<=64 bytes
// including the three metadata fields) so it fits in one or two cache lines.
template <typename Payload>
struct Event {
    std::uint64_t timestamp_ns;  // nanoseconds since epoch (monotonic)
    std::uint64_t key;           // routing / grouping key
    std::uint64_t seq;           // sequence number (set by source, monotonic)
    Payload       data;          // user payload — must be trivially copyable

    // ── Factory helpers ───────────────────────────────────────────────────
    static Event make(Payload d, std::uint64_t k = 0, std::uint64_t s = 0) {
        using namespace std::chrono;
        auto now_ns = static_cast<std::uint64_t>(
            duration_cast<nanoseconds>(
                steady_clock::now().time_since_epoch()
            ).count()
        );
        return Event{ now_ns, k, s, std::move(d) };
    }

    // Elapsed nanoseconds since this event was created (call at the sink).
    std::uint64_t latency_ns() const {
        using namespace std::chrono;
        auto now_ns = static_cast<std::uint64_t>(
            duration_cast<nanoseconds>(
                steady_clock::now().time_since_epoch()
            ).count()
        );
        return (now_ns >= timestamp_ns) ? (now_ns - timestamp_ns) : 0;
    }
};

// Convenience alias for the common case of a plain 64-bit integer payload.
using IntEvent = Event<std::uint64_t>;

} // namespace klstream
```

---

### 7.3 `spsc_queue.hpp` — Lock-Free SPSC Ring Buffer

This is the most performance-critical file in the project. Read the inline comments
carefully before modifying anything — a single wrong `memory_order` produces silent
data corruption that TSan may or may not catch depending on timing.

The design is based on rigtorp's SPSCQueue (MIT-licensed, widely cited in lock-free
programming literature). Two key adaptations for Apple Silicon:

1. `alignas(CACHE_LINE_SIZE)` uses 128 (not 64) — see `config.hpp` Section 7.1.
2. The ARM AArch64 memory model is weaker than x86's TSO model. On x86, plain stores
   are implicitly `release` and plain loads are implicitly `acquire`. On ARM, they
   are not — we must use explicit `memory_order_release`/`acquire`.

```cpp
// include/klstream/core/spsc_queue.hpp
#pragma once
#include "config.hpp"
#include <atomic>
#include <cassert>
#include <cstddef>
#include <memory>
#include <new>
#include <optional>
#include <type_traits>

namespace klstream {

// ── SPSCQueue<T> ─────────────────────────────────────────────────────────
//
// A bounded, lock-free, single-producer / single-consumer ring buffer.
//
// CORRECTNESS CONTRACT (do not violate):
//   * Exactly one thread calls push() or try_push() at a time (the producer).
//   * Exactly one thread calls pop() or try_pop() at a time (the consumer).
//   * These two threads may be different OS threads — that is the whole point.
//   * T must be trivially copyable (POD-like). For complex types, wrap them
//     in a std::shared_ptr before putting them in an Event.
//
// MEMORY LAYOUT (cache-line padded to prevent false sharing):
//
//   [padding 0]          <- start on cache line boundary
//   write_idx_           <- producer writes, consumer reads (release/acquire)
//   [padding 1]          <- isolate write_idx_ from read_idx_
//   write_idx_cached_    <- producer's local shadow of read_idx_ (relaxed)
//   [padding 2]
//   read_idx_            <- consumer writes, producer reads (release/acquire)
//   [padding 3]          <- isolate read_idx_ from write_idx_
//   read_idx_cached_     <- consumer's local shadow of write_idx_ (relaxed)
//   [padding 4]
//   capacity_            <- const after construction
//   buffer_              <- the actual ring, heap-allocated, cache-line aligned
//
// WHY CACHED INDICES:
//   In the fast path (queue neither full nor empty), the producer only ever
//   reads its own write_idx_ and its cached copy of read_idx_. It never
//   touches the cache line that the consumer is modifying. This eliminates
//   MESI "RFO" (Request For Ownership) cache-line ping-pong, which is the
//   dominant cost in naive implementations.

template <typename T>
class SPSCQueue {
    static_assert(std::is_trivially_copyable_v<T>,
        "SPSCQueue<T>: T must be trivially copyable. "
        "Wrap complex types in std::shared_ptr.");

public:
    // capacity must be a power of 2 and >= 2.
    explicit SPSCQueue(std::size_t capacity = DEFAULT_QUEUE_CAPACITY)
        : capacity_(capacity)
        , buffer_(static_cast<T*>(
            ::operator new(capacity * sizeof(T),
                           std::align_val_t{CACHE_LINE_SIZE})))
    {
        assert(capacity >= 2 && "SPSCQueue capacity must be >= 2");
        assert((capacity & (capacity - 1)) == 0 &&
               "SPSCQueue capacity must be a power of 2");
    }

    ~SPSCQueue() {
        ::operator delete(buffer_,
            std::align_val_t{CACHE_LINE_SIZE});
    }

    // Non-copyable, non-movable (contains raw pointer + atomics).
    SPSCQueue(const SPSCQueue&)            = delete;
    SPSCQueue& operator=(const SPSCQueue&) = delete;
    SPSCQueue(SPSCQueue&&)                 = delete;
    SPSCQueue& operator=(SPSCQueue&&)      = delete;

    // ── Producer side ─────────────────────────────────────────────────────

    // try_push: returns true on success, false if the queue is full.
    // Call from exactly ONE producer thread.
    [[nodiscard]] bool try_push(const T& val) noexcept {
        const std::size_t wi = write_idx_.load(std::memory_order_relaxed);
        const std::size_t next_wi = (wi + 1) & (capacity_ - 1);

        // Fast path: use cached read index.
        if (next_wi == write_idx_cached_) {
            // Cached value says queue might be full. Re-read the real index.
            write_idx_cached_ = read_idx_.load(std::memory_order_acquire);
            if (next_wi == write_idx_cached_) {
                return false; // Queue is actually full.
            }
        }
        buffer_[wi] = val;
        // Release: make the write visible to the consumer before we advance
        // write_idx_. The consumer will see the updated index and then read
        // the element we just wrote.
        write_idx_.store(next_wi, std::memory_order_release);
        return true;
    }

    // Blocking push: spins with three-tier backoff until space is available.
    // Not recommended in the hot path — prefer try_push() + OpStatus::Blocked.
    void push(const T& val) noexcept {
        int spin = 0, yields = 0;
        while (!try_push(val)) {
            if (spin < SPIN_BEFORE_YIELD) {
                ++spin;
#if defined(__aarch64__)
                __asm__ volatile("yield" ::: "memory");
#elif defined(__x86_64__)
                __asm__ volatile("pause" ::: "memory");
#endif
            } else if (yields < YIELD_BEFORE_SLEEP) {
                ++yields;
                std::this_thread::yield();
            } else {
                std::this_thread::sleep_for(
                    std::chrono::nanoseconds(SLEEP_NS));
            }
        }
    }

    // ── Consumer side ─────────────────────────────────────────────────────

    // try_pop: writes the front element into *out and returns true, or
    // returns false if the queue is empty. out must not be null.
    [[nodiscard]] bool try_pop(T* out) noexcept {
        const std::size_t ri = read_idx_.load(std::memory_order_relaxed);

        // Fast path: use cached write index.
        if (ri == read_idx_cached_) {
            read_idx_cached_ = write_idx_.load(std::memory_order_acquire);
            if (ri == read_idx_cached_) {
                return false; // Queue is actually empty.
            }
        }
        *out = buffer_[ri];
        read_idx_.store((ri + 1) & (capacity_ - 1),
                        std::memory_order_release);
        return true;
    }

    // Convenience: returns std::nullopt when empty.
    std::optional<T> pop() noexcept {
        T val;
        if (try_pop(&val)) return val;
        return std::nullopt;
    }

    // ── Inspection ────────────────────────────────────────────────────────

    // Approximate occupancy [0.0, 1.0]. Approximate because read and write
    // indices are read with relaxed ordering — the result may be stale.
    // Good enough for the EMA tracker in backpressure.hpp.
    [[nodiscard]] double occupancy() const noexcept {
        const std::size_t wi = write_idx_.load(std::memory_order_relaxed);
        const std::size_t ri = read_idx_.load(std::memory_order_relaxed);
        const std::size_t used = (wi - ri + capacity_) & (capacity_ - 1);
        return static_cast<double>(used) / static_cast<double>(capacity_);
    }

    [[nodiscard]] std::size_t capacity() const noexcept { return capacity_; }

    [[nodiscard]] bool empty() const noexcept {
        return write_idx_.load(std::memory_order_acquire)
            == read_idx_.load(std::memory_order_acquire);
    }

private:
    // Each hot atomic lives on its own 128-byte cache line.
    // The layout is: pad | atomic | cache-shadow | pad | atomic | cache-shadow | pad
    // so that no two of these four values share a cache line.

    alignas(CACHE_LINE_SIZE) std::atomic<std::size_t> write_idx_{0};
    alignas(CACHE_LINE_SIZE) std::size_t              write_idx_cached_{0};
    alignas(CACHE_LINE_SIZE) std::atomic<std::size_t> read_idx_{0};
    alignas(CACHE_LINE_SIZE) std::size_t              read_idx_cached_{0};

    const std::size_t capacity_;
    T*                buffer_;   // heap-allocated, CACHE_LINE_SIZE-aligned
};

} // namespace klstream
```

---

### 7.4 `mpmc_queue.hpp` — Bounded MPMC Queue

Used only when an operator has multiple parallel instances (e.g., three instances of
`FilterOperator` all reading from the same upstream queue). Based on Dmitry Vyukov's
bounded MPMC queue design — the most widely used lock-free MPMC implementation in
systems software. Uses sequence numbers stored per slot to allow multiple producers
and consumers to CAS-contend on individual slots rather than on a global counter.

```cpp
// include/klstream/core/mpmc_queue.hpp
#pragma once
#include "config.hpp"
#include <atomic>
#include <cassert>
#include <cstddef>
#include <new>
#include <optional>
#include <type_traits>

namespace klstream {

template <typename T>
class MPMCQueue {
    static_assert(std::is_trivially_copyable_v<T>,
        "MPMCQueue<T>: T must be trivially copyable.");

    // Each slot holds the data and a sequence number.
    // The sequence number encodes whether the slot is:
    //   empty (seq == slot_index)        -> enqueuer can claim it
    //   filled (seq == slot_index + 1)   -> dequeuer can consume it
    struct Slot {
        alignas(CACHE_LINE_SIZE) std::atomic<std::size_t> seq;
        T data;
    };

public:
    explicit MPMCQueue(std::size_t capacity = DEFAULT_QUEUE_CAPACITY)
        : capacity_(capacity)
        , mask_(capacity - 1)
        , buffer_(static_cast<Slot*>(
            ::operator new(capacity * sizeof(Slot),
                           std::align_val_t{CACHE_LINE_SIZE})))
    {
        assert(capacity >= 2);
        assert((capacity & (capacity - 1)) == 0 &&
               "MPMCQueue capacity must be a power of 2");
        for (std::size_t i = 0; i < capacity; ++i) {
            buffer_[i].seq.store(i, std::memory_order_relaxed);
        }
    }

    ~MPMCQueue() {
        ::operator delete(buffer_,
            std::align_val_t{CACHE_LINE_SIZE});
    }

    MPMCQueue(const MPMCQueue&)            = delete;
    MPMCQueue& operator=(const MPMCQueue&) = delete;

    [[nodiscard]] bool try_push(const T& val) noexcept {
        std::size_t pos = enqueue_pos_.load(std::memory_order_relaxed);
        for (;;) {
            Slot& slot = buffer_[pos & mask_];
            std::size_t seq = slot.seq.load(std::memory_order_acquire);
            std::ptrdiff_t diff = static_cast<std::ptrdiff_t>(seq)
                                - static_cast<std::ptrdiff_t>(pos);
            if (diff == 0) {
                // Slot is free — try to claim it.
                if (enqueue_pos_.compare_exchange_weak(
                        pos, pos + 1, std::memory_order_relaxed)) {
                    slot.data = val;
                    slot.seq.store(pos + 1, std::memory_order_release);
                    return true;
                }
                // CAS failed — another producer claimed it; retry.
            } else if (diff < 0) {
                return false; // Queue is full.
            } else {
                pos = enqueue_pos_.load(std::memory_order_relaxed);
            }
        }
    }

    [[nodiscard]] bool try_pop(T* out) noexcept {
        std::size_t pos = dequeue_pos_.load(std::memory_order_relaxed);
        for (;;) {
            Slot& slot = buffer_[pos & mask_];
            std::size_t seq = slot.seq.load(std::memory_order_acquire);
            std::ptrdiff_t diff = static_cast<std::ptrdiff_t>(seq)
                                - static_cast<std::ptrdiff_t>(pos + 1);
            if (diff == 0) {
                if (dequeue_pos_.compare_exchange_weak(
                        pos, pos + 1, std::memory_order_relaxed)) {
                    *out = slot.data;
                    slot.seq.store(pos + mask_ + 1,
                                   std::memory_order_release);
                    return true;
                }
            } else if (diff < 0) {
                return false; // Queue is empty.
            } else {
                pos = dequeue_pos_.load(std::memory_order_relaxed);
            }
        }
    }

    std::optional<T> pop() noexcept {
        T val;
        if (try_pop(&val)) return val;
        return std::nullopt;
    }

    [[nodiscard]] double occupancy() const noexcept {
        const std::size_t ep = enqueue_pos_.load(std::memory_order_relaxed);
        const std::size_t dp = dequeue_pos_.load(std::memory_order_relaxed);
        const std::size_t used = (ep - dp + capacity_) & mask_;
        return static_cast<double>(used) / static_cast<double>(capacity_);
    }

    [[nodiscard]] std::size_t capacity() const noexcept { return capacity_; }

private:
    const std::size_t capacity_;
    const std::size_t mask_;
    Slot*             buffer_;

    alignas(CACHE_LINE_SIZE) std::atomic<std::size_t> enqueue_pos_{0};
    alignas(CACHE_LINE_SIZE) std::atomic<std::size_t> dequeue_pos_{0};
};

} // namespace klstream
```

---

### 7.5 `operator.hpp` — The Operator Interface

```cpp
// include/klstream/core/operator.hpp
#pragma once
#include <cstdint>
#include <string>

namespace klstream {

// ── OpStatus ─────────────────────────────────────────────────────────────
//
// Return value of IOperator::tick(). The worker thread uses this to decide
// what to do next:
//
//   Processed -> reset backoff counter, immediately call tick() again.
//   Idle      -> increment backoff counter, apply spin/yield/sleep policy.
//   Blocked   -> output queue was full; do NOT pop input on the next tick()
//               (the operator must remember the un-pushed event internally).
//               Increment backoff counter to give the downstream time to drain.
enum class OpStatus : std::uint8_t {
    Processed = 0,  // One event was successfully processed and pushed.
    Idle      = 1,  // Input queue was empty; nothing to do.
    Blocked   = 2,  // Output queue was full; event is held inside operator.
};

// ── IOperator ─────────────────────────────────────────────────────────────
//
// The abstract base class for every operator in the pipeline.
//
// Lifecycle:
//   1. Construct the operator (pass queue pointers, lambda, etc. in ctor).
//   2. Runtime calls init() once on the owning thread before the first tick().
//   3. Runtime calls tick() in a tight loop for the operator's lifetime.
//   4. Runtime calls shutdown() once when stopping (after setting stop flag).
//
// Threading: init(), tick(), and shutdown() are always called from the same
// worker thread. The operator does not need to protect its own state with
// locks — the queues are the synchronisation boundary.
//
// The operator OWNS a "pending" slot: when tick() returns Blocked, it means
// the operator has popped an event from its input queue and stored it in an
// internal field (e.g., `pending_`). On the next tick() call, it attempts
// to push the pending event again without popping a new one. This guarantees
// at-most-once-pop: we never lose data by popping something we could not push.
class IOperator {
public:
    explicit IOperator(std::string name) : name_(std::move(name)) {}
    virtual ~IOperator() = default;

    // Called once by the worker thread before the first tick().
    virtual void init() {}

    // Core scheduling unit. Called repeatedly. See OpStatus for semantics.
    [[nodiscard]] virtual OpStatus tick() = 0;

    // Called once after the stop flag is set. Flush, close files, etc.
    virtual void shutdown() {}

    const std::string& name() const { return name_; }

    // Unique integer ID assigned by the Runtime at registration time.
    std::uint64_t id = 0;

private:
    std::string name_;
};

} // namespace klstream
```

---

### 7.6 `pinning.hpp` — Core Affinity Hints for Apple Silicon

```cpp
// include/klstream/core/pinning.hpp
#pragma once
#include <cstdint>

// macOS-specific QoS thread affinity. Compiles to no-ops on other platforms.
#if defined(__APPLE__)
#  include <pthread.h>
#endif

namespace klstream {

// ── CoreAffinity ─────────────────────────────────────────────────────────
//
// Which type of core the worker thread should prefer.
// On Apple M3: Performance cores are ~4 GHz, Efficiency cores ~2.75 GHz.
//
// Use Performance for compute-heavy operators (Map with expensive transforms,
// Aggregate with complex state, Window with large buffers).
// Use Efficiency for lightweight operators (Source with rate limiting,
// simple Filter, Sink that just counts or writes a counter).
// Use Any to let the OS decide (default — identical to not calling anything).
enum class CoreAffinity : std::uint8_t {
    Any         = 0,  // OS-managed (default).
    Performance = 1,  // Prefer P-cores (QOS_CLASS_USER_INTERACTIVE on macOS).
    Efficiency  = 2,  // Prefer E-cores (QOS_CLASS_BACKGROUND on macOS).
};

// ── apply_affinity ────────────────────────────────────────────────────────
//
// Call this at the START of a worker thread's execution (before any work).
// It sets the calling thread's QoS class so the macOS scheduler routes it
// to the requested core type.
//
// On non-Apple platforms this is a compile-time no-op. The rest of the
// codebase never calls any platform-specific API directly — only this function.
inline void apply_affinity(CoreAffinity affinity) noexcept {
#if defined(__APPLE__)
    switch (affinity) {
        case CoreAffinity::Performance:
            pthread_set_qos_class_self_np(QOS_CLASS_USER_INTERACTIVE, 0);
            break;
        case CoreAffinity::Efficiency:
            pthread_set_qos_class_self_np(QOS_CLASS_BACKGROUND, 0);
            break;
        case CoreAffinity::Any:
        default:
            break; // Leave the OS to decide.
    }
#else
    (void)affinity; // Suppress unused-parameter warning.
#endif
}

// ── AffinityMap ──────────────────────────────────────────────────────────
//
// Convenience struct used by Runtime (Section 7.10) to pair an operator ID
// with the affinity hint for the worker thread that will run it.
struct AffinityConfig {
    std::uint64_t operator_id;
    CoreAffinity  affinity;
};

} // namespace klstream
```

---

### 7.7 `metrics.hpp` — Counters & Latency Histogram

```cpp
// include/klstream/core/metrics.hpp
#pragma once
#include "config.hpp"
#include <atomic>
#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>
#include <chrono>
#include <iostream>
#include <iomanip>

namespace klstream {

// ── Counter ───────────────────────────────────────────────────────────────
//
// A cache-line-aligned atomic counter for counting events.
// Each operator has one Counter for events_processed and one for
// events_blocked (backpressure occurrences).
//
// memory_order_relaxed is used everywhere because:
//   a) We only care about approximate throughput, not exact synchronisation.
//   b) Relaxed atomics do not generate memory fence instructions on ARM,
//      so they cost essentially nothing in the hot path.
//   c) We snapshot counters from a reporter thread using relaxed loads,
//      which is fine because we only need "recent" values, not "exact" values.
struct Counter {
    alignas(CACHE_LINE_SIZE) std::atomic<std::uint64_t> value{0};

    void increment() noexcept {
        value.fetch_add(1, std::memory_order_relaxed);
    }

    std::uint64_t load() const noexcept {
        return value.load(std::memory_order_relaxed);
    }

    // Atomically reset and return the old value (used by the reporter to
    // compute per-interval throughput without cumulative growth).
    std::uint64_t reset() noexcept {
        return value.exchange(0, std::memory_order_relaxed);
    }
};

// ── LatencyHistogram ──────────────────────────────────────────────────────
//
// A fixed-width histogram for end-to-end latency. Each bucket covers 1 us.
// Bucket index = latency_us = latency_ns / 1000.
// Values beyond MAX_LATENCY_US go into an overflow bucket.
//
// Not lock-free: uses a single compare_exchange_weak per record. Suitable
// for the sink operator (single consumer thread increments buckets).
// If multiple sinks need to share a histogram, protect with a mutex or
// use per-thread histograms merged periodically.
struct LatencyHistogram {
    std::array<std::atomic<std::uint64_t>, HISTOGRAM_BUCKETS + 1> buckets{};

    LatencyHistogram() {
        for (auto& b : buckets) b.store(0, std::memory_order_relaxed);
    }

    void record(std::uint64_t latency_ns) noexcept {
        std::size_t idx = latency_ns / 1000; // convert ns -> us
        if (idx >= HISTOGRAM_BUCKETS) idx = HISTOGRAM_BUCKETS; // overflow
        buckets[idx].fetch_add(1, std::memory_order_relaxed);
    }

    // Returns the latency_us value below which `pct` fraction of events fall.
    // E.g., percentile(0.99) returns p99 latency in microseconds.
    double percentile(double pct) const noexcept {
        std::uint64_t total = 0;
        for (const auto& b : buckets)
            total += b.load(std::memory_order_relaxed);
        if (total == 0) return 0.0;
        const std::uint64_t target = static_cast<std::uint64_t>(pct * total);
        std::uint64_t cumulative = 0;
        for (std::size_t i = 0; i < HISTOGRAM_BUCKETS; ++i) {
            cumulative += buckets[i].load(std::memory_order_relaxed);
            if (cumulative >= target) return static_cast<double>(i);
        }
        return static_cast<double>(MAX_LATENCY_US); // overflow bucket
    }
};

// ── OperatorMetrics ───────────────────────────────────────────────────────
//
// One per operator instance. Attached to the operator at construction and
// read by the MetricsReporter thread.
struct OperatorMetrics {
    Counter events_processed;   // successfully processed events
    Counter events_blocked;     // tick() returned Blocked (backpressure)
    Counter events_idle;        // tick() returned Idle (no input)
    std::string op_name;        // set at construction, never modified after

    OperatorMetrics() = default;
    explicit OperatorMetrics(std::string name) : op_name(std::move(name)) {}
};

// ── MetricsReporter ───────────────────────────────────────────────────────
//
// Runs on its own background std::thread. Every METRICS_INTERVAL_SEC seconds
// it samples all registered OperatorMetrics instances and prints a summary
// table to stdout.
//
// To use: create one MetricsReporter, call add(metrics_ptr) for each operator,
// then call start(). Call stop() on shutdown.
class MetricsReporter {
public:
    void add(OperatorMetrics* m) { entries_.push_back(m); }

    void start() {
        running_.store(true);
        thread_ = std::thread([this]{ run(); });
    }

    void stop() {
        running_.store(false);
        if (thread_.joinable()) thread_.join();
    }

    ~MetricsReporter() { stop(); }

private:
    void run() {
        while (running_.load(std::memory_order_relaxed)) {
            std::this_thread::sleep_for(
                std::chrono::seconds(METRICS_INTERVAL_SEC));
            print();
        }
    }

    void print() {
        using namespace std;
        cout << "\n── KLStream Metrics ─────────────────────────────────\n";
        cout << left
             << setw(22) << "Operator"
             << setw(16) << "Events/sec"
             << setw(14) << "Blocked/sec"
             << setw(12) << "Idle/sec" << "\n";
        cout << string(64, '-') << "\n";
        for (auto* m : entries_) {
            cout << setw(22) << m->op_name
                 << setw(16) << m->events_processed.reset()
                 << setw(14) << m->events_blocked.reset()
                 << setw(12) << m->events_idle.reset()
                 << "\n";
        }
        cout << flush;
    }

    std::vector<OperatorMetrics*> entries_;
    std::atomic<bool>             running_{false};
    std::thread                   thread_;
};

} // namespace klstream
```

---

### 7.8 `backpressure.hpp` — EMA Tracker & Adaptive Rate Limiter

This is the research-extension header. It provides two things: (a) an
`EMAOccupancyTracker` that any operator can query to get a smoothed reading of
its output queue's occupancy, and (b) a `TokenBucketRateLimiter` that the
`SourceOperator` uses to implement gradual rate reduction before the queue is
completely full. Together they implement Gap 2 from the research brief —
predictive, gradual backpressure rather than binary block/unblock.

```cpp
// include/klstream/core/backpressure.hpp
#pragma once
#include "config.hpp"
#include <atomic>
#include <chrono>
#include <thread>
#include <cstdint>

namespace klstream {

// ── EMAOccupancyTracker ───────────────────────────────────────────────────
//
// Wraps any Queue that exposes .occupancy() and tracks an exponential
// moving average of its fill fraction.
//
// The EMA alpha parameter controls smoothing:
//   Small alpha (e.g. 0.05): slow to react, very smooth — good for
//     predicting slow-building pressure from sustained overload.
//   Large alpha (e.g. 0.30): reacts quickly — better for bursty workloads.
//
// Default alpha = 0.10 is a sensible starting point. The research extension
// (Section 14.1) sweeps alpha values and measures the effect on p99 latency.
//
// USAGE:
//   EMAOccupancyTracker tracker(my_queue, 0.10);
//   // In the source's tick() loop:
//   tracker.update();
//   if (tracker.ema() > BP_SOFT_THRESHOLD) { /* slow down */ }

template <typename Queue>
class EMAOccupancyTracker {
public:
    explicit EMAOccupancyTracker(Queue& queue, double alpha = 0.10)
        : queue_(queue), alpha_(alpha), ema_(0.0) {}

    // Call once per tick() to update the EMA.
    void update() noexcept {
        double occ = queue_.occupancy();
        ema_ = alpha_ * occ + (1.0 - alpha_) * ema_;
    }

    [[nodiscard]] double ema() const noexcept { return ema_; }

    // Returns true if the EMA exceeds the soft backpressure threshold.
    // When this returns true the source should reduce its emission rate.
    [[nodiscard]] bool soft_pressure() const noexcept {
        return ema_ > BP_SOFT_THRESHOLD;
    }

    // Returns true if occupancy is critically high (hard threshold).
    // When this returns true the source should stop emitting entirely
    // and wait, identical to the baseline blocking behaviour.
    [[nodiscard]] bool hard_pressure() const noexcept {
        return queue_.occupancy() > BP_HARD_THRESHOLD;
    }

private:
    Queue&      queue_;
    double      alpha_;
    double      ema_;
};

// ── TokenBucketRateLimiter ────────────────────────────────────────────────
//
// A simple token-bucket used by SourceOperator to smoothly rate-limit event
// generation when adaptive backpressure is enabled.
//
// tokens are replenished at a configurable rate (tokens_per_sec).
// Each call to try_consume() uses one token. When the bucket is empty,
// try_consume() returns false and the source should pause.
//
// The rate can be reduced at runtime via set_rate(). This is how the adaptive
// backpressure controller gradually slows the source when soft pressure is
// detected (before the queue is actually full).
class TokenBucketRateLimiter {
public:
    explicit TokenBucketRateLimiter(double tokens_per_sec,
                                    double max_burst = 0.0)
        : rate_(tokens_per_sec)
        , tokens_(tokens_per_sec) // start full
        , max_tokens_(max_burst > 0 ? max_burst : tokens_per_sec)
        , last_(std::chrono::steady_clock::now())
    {}

    // Refill tokens based on elapsed time, then try to consume one.
    [[nodiscard]] bool try_consume() noexcept {
        refill();
        if (tokens_ >= 1.0) {
            tokens_ -= 1.0;
            return true;
        }
        return false;
    }

    void set_rate(double tokens_per_sec) noexcept {
        rate_ = tokens_per_sec;
    }

    double rate() const noexcept { return rate_; }

private:
    void refill() noexcept {
        auto now     = std::chrono::steady_clock::now();
        double elapsed = std::chrono::duration<double>(now - last_).count();
        last_    = now;
        tokens_ += elapsed * rate_;
        if (tokens_ > max_tokens_) tokens_ = max_tokens_;
    }

    double rate_;
    double tokens_;
    double max_tokens_;
    std::chrono::steady_clock::time_point last_;
};

} // namespace klstream
```

---

### 7.9 `worker.hpp` — Worker Thread & Execution Loop

```cpp
// include/klstream/core/worker.hpp
#pragma once
#include "operator.hpp"
#include "pinning.hpp"
#include "config.hpp"
#include <atomic>
#include <chrono>
#include <memory>
#include <thread>
#include <vector>

namespace klstream {

// ── WorkerThread ──────────────────────────────────────────────────────────
//
// One OS thread (std::thread) that owns a list of IOperator* and executes
// them cooperatively in a round-robin loop.
//
// Scheduling policy (cooperative round-robin with three-tier backoff):
//
//   while (running):
//       for each operator in assigned_operators:
//           status = operator.tick()
//           if status == Processed:  reset idle counter
//           else:                    increment idle counter
//       if all operators were Idle or Blocked this round:
//           apply_backoff(idle_rounds)
//
// The backoff escalates:
//   idle_rounds < SPIN_BEFORE_YIELD  →  ARM `yield` / x86 `pause`
//   idle_rounds < SPIN + YIELD_CAP   →  std::this_thread::yield()
//   idle_rounds >= above             →  sleep_for(SLEEP_NS nanoseconds)
//
// This keeps latency low (the ARM yield instruction is ~1 ns) while
// not burning 100% CPU indefinitely when the pipeline is truly idle.

class WorkerThread {
public:
    WorkerThread() = default;

    // Non-copyable, non-movable (contains std::thread + atomics).
    WorkerThread(const WorkerThread&)            = delete;
    WorkerThread& operator=(const WorkerThread&) = delete;
    WorkerThread(WorkerThread&&)                 = delete;
    WorkerThread& operator=(WorkerThread&&)      = delete;

    // Add an operator to this worker's scheduling list.
    // Must be called BEFORE start().
    void assign(IOperator* op) {
        operators_.push_back(op);
    }

    // Set the core affinity hint for this worker.
    // Must be called BEFORE start().
    void set_affinity(CoreAffinity aff) { affinity_ = aff; }

    // Start the worker thread. Calls init() on all operators, then enters
    // the scheduling loop.
    void start() {
        running_.store(true, std::memory_order_relaxed);
        thread_ = std::thread([this]{ run(); });
    }

    // Signal the worker to stop and wait for it to join.
    void stop() {
        running_.store(false, std::memory_order_release);
        if (thread_.joinable()) thread_.join();
        for (auto* op : operators_) op->shutdown();
    }

    ~WorkerThread() { stop(); }

private:
    void run() {
        // Apply core-affinity hint at the very beginning of the thread.
        apply_affinity(affinity_);

        // Initialise all owned operators.
        for (auto* op : operators_) op->init();

        int idle_rounds = 0;
        const int YIELD_CAP = SPIN_BEFORE_YIELD + YIELD_BEFORE_SLEEP;

        while (running_.load(std::memory_order_relaxed)) {
            bool any_progress = false;
            for (auto* op : operators_) {
                OpStatus s = op->tick();
                if (s == OpStatus::Processed) any_progress = true;
            }
            if (!any_progress) {
                ++idle_rounds;
                if (idle_rounds < SPIN_BEFORE_YIELD) {
#if defined(__aarch64__)
                    __asm__ volatile("yield" ::: "memory");
#elif defined(__x86_64__)
                    __asm__ volatile("pause" ::: "memory");
#endif
                } else if (idle_rounds < YIELD_CAP) {
                    std::this_thread::yield();
                } else {
                    std::this_thread::sleep_for(
                        std::chrono::nanoseconds(SLEEP_NS));
                }
            } else {
                idle_rounds = 0;
            }
        }
    }

    std::vector<IOperator*>  operators_;
    CoreAffinity             affinity_{CoreAffinity::Any};
    std::atomic<bool>        running_{false};
    std::thread              thread_;
};

} // namespace klstream
```

---

### 7.10 `runtime.hpp` — The Runtime

```cpp
// include/klstream/core/runtime.hpp
#pragma once
#include "operator.hpp"
#include "pinning.hpp"
#include "worker.hpp"
#include "metrics.hpp"
#include <cstdint>
#include <memory>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

namespace klstream {

// ── OperatorRegistration ──────────────────────────────────────────────────
struct OperatorRegistration {
    IOperator*   op;
    CoreAffinity affinity;
    int          worker_id; // which worker thread to assign this op to
};

// ── Runtime ───────────────────────────────────────────────────────────────
//
// The top-level coordinator. Responsibilities:
//   1. Accept (operator, affinity, worker_id) registrations.
//   2. Assign operators to WorkerThreads.
//   3. Start all workers (and the MetricsReporter).
//   4. Provide a blocking wait() method for main() to call.
//   5. Stop cleanly on request.
//
// USAGE PATTERN:
//
//   klstream::Runtime rt;
//   rt.add_worker();                         // Worker 0
//   rt.add_worker();                         // Worker 1
//   rt.register_op(&my_source, 0, CoreAffinity::Efficiency);
//   rt.register_op(&my_map,    0, CoreAffinity::Performance);
//   rt.register_op(&my_sink,   1, CoreAffinity::Efficiency);
//   rt.metrics().add(&source_metrics);
//   rt.metrics().add(&sink_metrics);
//   rt.start();
//   rt.wait_for(std::chrono::seconds(10));
//   rt.stop();
//
// Thread safety: add_worker(), register_op(), start(), stop(), and wait_for()
// must all be called from the same thread (typically main()).
class Runtime {
public:
    // Add a worker thread slot. Returns its 0-based index.
    int add_worker(CoreAffinity default_affinity = CoreAffinity::Any) {
        int idx = static_cast<int>(workers_.size());
        workers_.emplace_back(std::make_unique<WorkerThread>());
        workers_.back()->set_affinity(default_affinity);
        return idx;
    }

    // Register an operator with a specific worker thread.
    void register_op(IOperator* op, int worker_id,
                     CoreAffinity affinity = CoreAffinity::Any)
    {
        if (worker_id < 0 ||
            worker_id >= static_cast<int>(workers_.size())) {
            throw std::out_of_range(
                "Runtime::register_op: invalid worker_id " +
                std::to_string(worker_id));
        }
        op->id = next_op_id_++;
        // Override the worker's default affinity if a per-op affinity is given.
        if (affinity != CoreAffinity::Any) {
            workers_[worker_id]->set_affinity(affinity);
        }
        workers_[worker_id]->assign(op);
    }

    MetricsReporter& metrics() { return reporter_; }

    // Start all workers and the metrics reporter.
    void start() {
        if (started_) throw std::logic_error("Runtime::start() called twice");
        started_ = true;
        reporter_.start();
        for (auto& w : workers_) w->start();
    }

    // Block the calling thread until duration elapses, then return.
    template <typename Rep, typename Period>
    void wait_for(std::chrono::duration<Rep, Period> duration) {
        std::this_thread::sleep_for(duration);
    }

    // Stop all workers and the metrics reporter.
    void stop() {
        for (auto& w : workers_) w->stop();
        reporter_.stop();
    }

    ~Runtime() { if (started_) stop(); }

private:
    std::vector<std::unique_ptr<WorkerThread>> workers_;
    MetricsReporter                            reporter_;
    std::uint64_t                              next_op_id_{0};
    bool                                       started_{false};
};

} // namespace klstream
```

---

## 8. Standard Operator Library

All files in `include/klstream/operators/`. Each operator derives from `IOperator`
and owns a raw pointer to each of its input and output queues (the queue objects are
allocated in `main()` and live longer than any operator).

---

### 8.1 Source Operator

```cpp
// include/klstream/operators/source.hpp
#pragma once
#include "../core/operator.hpp"
#include "../core/event.hpp"
#include "../core/spsc_queue.hpp"
#include "../core/metrics.hpp"
#include "../core/backpressure.hpp"
#include <functional>
#include <atomic>
#include <cstdint>

namespace klstream {

// ── SourceOperator<T> ─────────────────────────────────────────────────────
//
// Generates events from a user-supplied generator function and pushes them
// into a single output queue. Has no input queue.
//
// The generator function is called once per tick() to produce one event.
// When the generator returns false, the source is exhausted (finite source).
// When it returns true and populates `out`, the source pushes `out` downstream.
//
// Rate limiting:
//   If a TokenBucketRateLimiter is attached (via enable_rate_limiting()),
//   the source checks the bucket before calling the generator. This is the
//   mechanism for both:
//     (a) basic rate control (cap at N events/sec for testing)
//     (b) adaptive backpressure (reduce rate when EMA occupancy rises)
//
// Backpressure:
//   If the output queue is full (try_push returns false), the source caches
//   the generated event in pending_ and returns Blocked. On the next tick()
//   it attempts to push pending_ again without generating a new event.
template <typename T>
class SourceOperator : public IOperator {
public:
    using Queue     = SPSCQueue<Event<T>>;
    using Generator = std::function<bool(Event<T>& out, std::uint64_t seq)>;

    SourceOperator(std::string name, Queue* output, Generator gen)
        : IOperator(std::move(name))
        , output_(output)
        , gen_(std::move(gen))
    {}

    void enable_rate_limiting(double events_per_sec) {
        limiter_ = std::make_unique<TokenBucketRateLimiter>(events_per_sec);
        ema_tracker_ = std::make_unique<EMAOccupancyTracker<Queue>>(*output_);
    }

    void attach_metrics(OperatorMetrics* m) { metrics_ = m; }

    OpStatus tick() override {
        // ── Adaptive backpressure (if enabled) ───────────────────────────
        if (ema_tracker_) {
            ema_tracker_->update();
            if (ema_tracker_->hard_pressure()) {
                if (metrics_) metrics_->events_blocked.increment();
                return OpStatus::Blocked;
            }
            if (ema_tracker_->soft_pressure() && limiter_) {
                // Reduce rate to 50% of configured rate.
                limiter_->set_rate(limiter_->rate() * 0.5);
            } else if (limiter_) {
                // Recover rate gradually (5% per tick toward original).
                limiter_->set_rate(
                    std::min(limiter_->rate() * 1.05, original_rate_));
            }
        }

        // ── Rate limiter check ────────────────────────────────────────────
        if (limiter_ && !limiter_->try_consume()) {
            if (metrics_) metrics_->events_idle.increment();
            return OpStatus::Idle;
        }

        // ── Push pending event from previous Blocked tick ─────────────────
        if (has_pending_) {
            if (output_->try_push(pending_)) {
                has_pending_ = false;
                if (metrics_) metrics_->events_processed.increment();
                return OpStatus::Processed;
            }
            if (metrics_) metrics_->events_blocked.increment();
            return OpStatus::Blocked;
        }

        // ── Generate a new event ──────────────────────────────────────────
        Event<T> ev;
        if (!gen_(ev, seq_++)) {
            return OpStatus::Idle; // Generator exhausted or throttling.
        }

        if (output_->try_push(ev)) {
            if (metrics_) metrics_->events_processed.increment();
            return OpStatus::Processed;
        }

        // Could not push — cache and report Blocked.
        pending_     = ev;
        has_pending_ = true;
        if (metrics_) metrics_->events_blocked.increment();
        return OpStatus::Blocked;
    }

private:
    Queue*             output_;
    Generator          gen_;
    std::uint64_t      seq_{0};
    Event<T>           pending_{};
    bool               has_pending_{false};
    double             original_rate_{0.0};
    OperatorMetrics*   metrics_{nullptr};
    std::unique_ptr<TokenBucketRateLimiter>          limiter_;
    std::unique_ptr<EMAOccupancyTracker<Queue>>      ema_tracker_;
};

} // namespace klstream
```

---

### 8.2 Map Operator

```cpp
// include/klstream/operators/map.hpp
#pragma once
#include "../core/operator.hpp"
#include "../core/event.hpp"
#include "../core/spsc_queue.hpp"
#include "../core/metrics.hpp"
#include <functional>

namespace klstream {

// ── MapOperator<In, Out> ─────────────────────────────────────────────────
//
// Stateless 1-to-1 transform. Pops one Event<In> from the input queue,
// applies the user function to the payload, and pushes one Event<Out>
// to the output queue. Metadata (timestamp_ns, key, seq) is forwarded
// unchanged so latency measurement is accurate end-to-end.
//
// Example:
//   MapOperator<uint64_t, uint64_t> squarer(
//       "squarer",
//       &q_in, &q_out,
//       [](uint64_t x) -> uint64_t { return x * x; });
template <typename In, typename Out>
class MapOperator : public IOperator {
public:
    using InQueue  = SPSCQueue<Event<In>>;
    using OutQueue = SPSCQueue<Event<Out>>;
    using Fn       = std::function<Out(const In&)>;

    MapOperator(std::string name, InQueue* input, OutQueue* output, Fn fn)
        : IOperator(std::move(name))
        , input_(input), output_(output), fn_(std::move(fn))
    {}

    void attach_metrics(OperatorMetrics* m) { metrics_ = m; }

    OpStatus tick() override {
        // If we have a pending output from a previous Blocked tick, try again.
        if (has_pending_) {
            if (output_->try_push(pending_)) {
                has_pending_ = false;
                if (metrics_) metrics_->events_processed.increment();
                return OpStatus::Processed;
            }
            if (metrics_) metrics_->events_blocked.increment();
            return OpStatus::Blocked;
        }

        Event<In> in_ev;
        if (!input_->try_pop(&in_ev)) {
            if (metrics_) metrics_->events_idle.increment();
            return OpStatus::Idle;
        }

        Event<Out> out_ev;
        out_ev.timestamp_ns = in_ev.timestamp_ns; // forward original timestamp
        out_ev.key          = in_ev.key;
        out_ev.seq          = in_ev.seq;
        out_ev.data         = fn_(in_ev.data);

        if (output_->try_push(out_ev)) {
            if (metrics_) metrics_->events_processed.increment();
            return OpStatus::Processed;
        }

        pending_     = out_ev;
        has_pending_ = true;
        // Put in_ev back? No — we have already consumed it. The pending_
        // slot holds the computed output. We never re-run fn_ on the same input.
        if (metrics_) metrics_->events_blocked.increment();
        return OpStatus::Blocked;
    }

private:
    InQueue*          input_;
    OutQueue*         output_;
    Fn                fn_;
    Event<Out>        pending_{};
    bool              has_pending_{false};
    OperatorMetrics*  metrics_{nullptr};
};

} // namespace klstream
```

---

### 8.3 Filter Operator

```cpp
// include/klstream/operators/filter.hpp
#pragma once
#include "../core/operator.hpp"
#include "../core/event.hpp"
#include "../core/spsc_queue.hpp"
#include "../core/metrics.hpp"
#include <functional>

namespace klstream {

// ── FilterOperator<T> ─────────────────────────────────────────────────────
//
// Stateless selective pass-through. Pops one Event<T> from input. If the
// predicate returns true, pushes it to output unchanged. If false, the event
// is dropped (this is one of the few operators that intentionally discards
// events — it is correct by design, not a data-loss bug).
//
// Example:
//   FilterOperator<uint64_t> even_only(
//       "even_filter", &q_in, &q_out,
//       [](uint64_t x) { return x % 2 == 0; });
template <typename T>
class FilterOperator : public IOperator {
public:
    using Queue     = SPSCQueue<Event<T>>;
    using Predicate = std::function<bool(const T&)>;

    FilterOperator(std::string name, Queue* input, Queue* output, Predicate pred)
        : IOperator(std::move(name))
        , input_(input), output_(output), pred_(std::move(pred))
    {}

    void attach_metrics(OperatorMetrics* m) { metrics_ = m; }

    OpStatus tick() override {
        if (has_pending_) {
            if (output_->try_push(pending_)) {
                has_pending_ = false;
                if (metrics_) metrics_->events_processed.increment();
                return OpStatus::Processed;
            }
            if (metrics_) metrics_->events_blocked.increment();
            return OpStatus::Blocked;
        }

        Event<T> ev;
        if (!input_->try_pop(&ev)) {
            if (metrics_) metrics_->events_idle.increment();
            return OpStatus::Idle;
        }

        if (!pred_(ev.data)) {
            // Filtered out — count as processed (we consumed it) but don't push.
            if (metrics_) metrics_->events_processed.increment();
            return OpStatus::Processed;
        }

        if (output_->try_push(ev)) {
            if (metrics_) metrics_->events_processed.increment();
            return OpStatus::Processed;
        }

        pending_     = ev;
        has_pending_ = true;
        if (metrics_) metrics_->events_blocked.increment();
        return OpStatus::Blocked;
    }

private:
    Queue*           input_;
    Queue*           output_;
    Predicate        pred_;
    Event<T>         pending_{};
    bool             has_pending_{false};
    OperatorMetrics* metrics_{nullptr};
};

} // namespace klstream
```

---

### 8.4 Aggregate Operator

```cpp
// include/klstream/operators/aggregate.hpp
#pragma once
#include "../core/operator.hpp"
#include "../core/event.hpp"
#include "../core/spsc_queue.hpp"
#include "../core/metrics.hpp"
#include <functional>

namespace klstream {

// ── AggregateOperator<In, State, Out> ────────────────────────────────────
//
// Stateful incremental aggregation. Maintains an internal `State` and
// calls user-supplied functions for accumulation and extraction.
//
// This is NOT windowed — it maintains a running aggregate over all events
// seen so far (e.g., a running sum, count, or max). For windowed
// aggregation use TumblingCountWindow (Section 8.5) or TumblingTimeWindow
// (Section 8.6).
//
// Example — running sum:
//   AggregateOperator<uint64_t, uint64_t, uint64_t> summer(
//       "summer", &q_in, &q_out,
//       0ULL,                                   // initial state
//       [](uint64_t& st, uint64_t x){ st += x; },  // accumulate
//       [](const uint64_t& st){ return st; });      // extract
template <typename In, typename State, typename Out>
class AggregateOperator : public IOperator {
public:
    using InQueue    = SPSCQueue<Event<In>>;
    using OutQueue   = SPSCQueue<Event<Out>>;
    using AccumFn    = std::function<void(State&, const In&)>;
    using ExtractFn  = std::function<Out(const State&)>;

    AggregateOperator(std::string name,
                      InQueue*   input,
                      OutQueue*  output,
                      State      init_state,
                      AccumFn    accum,
                      ExtractFn  extract)
        : IOperator(std::move(name))
        , input_(input), output_(output)
        , state_(std::move(init_state))
        , accum_(std::move(accum))
        , extract_(std::move(extract))
    {}

    void attach_metrics(OperatorMetrics* m) { metrics_ = m; }

    OpStatus tick() override {
        if (has_pending_) {
            if (output_->try_push(pending_)) {
                has_pending_ = false;
                if (metrics_) metrics_->events_processed.increment();
                return OpStatus::Processed;
            }
            if (metrics_) metrics_->events_blocked.increment();
            return OpStatus::Blocked;
        }

        Event<In> in_ev;
        if (!input_->try_pop(&in_ev)) {
            if (metrics_) metrics_->events_idle.increment();
            return OpStatus::Idle;
        }

        accum_(state_, in_ev.data);

        Event<Out> out_ev;
        out_ev.timestamp_ns = in_ev.timestamp_ns;
        out_ev.key          = in_ev.key;
        out_ev.seq          = in_ev.seq;
        out_ev.data         = extract_(state_);

        if (output_->try_push(out_ev)) {
            if (metrics_) metrics_->events_processed.increment();
            return OpStatus::Processed;
        }

        pending_     = out_ev;
        has_pending_ = true;
        if (metrics_) metrics_->events_blocked.increment();
        return OpStatus::Blocked;
    }

private:
    InQueue*         input_;
    OutQueue*        output_;
    State            state_;
    AccumFn          accum_;
    ExtractFn        extract_;
    Event<Out>       pending_{};
    bool             has_pending_{false};
    OperatorMetrics* metrics_{nullptr};
};

} // namespace klstream
```

---

### 8.5 Tumbling Count Window

```cpp
// include/klstream/operators/window.hpp  (first half — count window)
#pragma once
#include "../core/operator.hpp"
#include "../core/event.hpp"
#include "../core/spsc_queue.hpp"
#include "../core/metrics.hpp"
#include <functional>
#include <vector>
#include <chrono>
#include <cstddef>
#include <cstdint>

namespace klstream {

// ── TumblingCountWindow<T, Out> ───────────────────────────────────────────
//
// Collects events into a non-overlapping window of fixed size (window_size).
// When the window is full, calls the user's aggregation function to produce
// one Out event and clears the buffer.
//
// Memory: stores up to window_size events in a std::vector (pre-reserved).
// The window fires and emits exactly one Out event per window_size inputs.
//
// Example — window average over every 100 integers:
//   TumblingCountWindow<uint64_t, double> avg_window(
//       "avg_100", &q_in, &q_out, 100,
//       [](const std::vector<uint64_t>& buf) -> double {
//           uint64_t sum = 0;
//           for (auto v : buf) sum += v;
//           return static_cast<double>(sum) / buf.size();
//       });
template <typename T, typename Out>
class TumblingCountWindow : public IOperator {
public:
    using InQueue   = SPSCQueue<Event<T>>;
    using OutQueue  = SPSCQueue<Event<Out>>;
    using AggrFn    = std::function<Out(const std::vector<T>&)>;

    TumblingCountWindow(std::string name,
                        InQueue*    input,
                        OutQueue*   output,
                        std::size_t window_size,
                        AggrFn      aggr)
        : IOperator(std::move(name))
        , input_(input), output_(output)
        , window_size_(window_size), aggr_(std::move(aggr))
    {
        buffer_.reserve(window_size_);
    }

    void attach_metrics(OperatorMetrics* m) { metrics_ = m; }

    OpStatus tick() override {
        if (has_pending_) {
            if (output_->try_push(pending_)) {
                has_pending_ = false;
                if (metrics_) metrics_->events_processed.increment();
                return OpStatus::Processed;
            }
            if (metrics_) metrics_->events_blocked.increment();
            return OpStatus::Blocked;
        }

        Event<T> in_ev;
        if (!input_->try_pop(&in_ev)) {
            if (metrics_) metrics_->events_idle.increment();
            return OpStatus::Idle;
        }

        if (buffer_.empty()) {
            window_start_ts_ = in_ev.timestamp_ns; // track for latency
        }
        buffer_.push_back(in_ev.data);

        if (buffer_.size() >= window_size_) {
            Event<Out> out_ev;
            out_ev.timestamp_ns = window_start_ts_;
            out_ev.key          = in_ev.key;
            out_ev.seq          = in_ev.seq;
            out_ev.data         = aggr_(buffer_);
            buffer_.clear();

            if (output_->try_push(out_ev)) {
                if (metrics_) metrics_->events_processed.increment();
                return OpStatus::Processed;
            }
            pending_     = out_ev;
            has_pending_ = true;
            if (metrics_) metrics_->events_blocked.increment();
            return OpStatus::Blocked;
        }

        if (metrics_) metrics_->events_processed.increment();
        return OpStatus::Processed; // buffered, not yet emitted
    }

private:
    InQueue*          input_;
    OutQueue*         output_;
    std::size_t       window_size_;
    AggrFn            aggr_;
    std::vector<T>    buffer_;
    std::uint64_t     window_start_ts_{0};
    Event<Out>        pending_{};
    bool              has_pending_{false};
    OperatorMetrics*  metrics_{nullptr};
};

} // namespace klstream
```

---

### 8.6 Tumbling Time Window

```cpp
// (append to window.hpp after TumblingCountWindow)

namespace klstream {

// ── TumblingTimeWindow<T, Out> ────────────────────────────────────────────
//
// Like TumblingCountWindow but fires every `window_ns` nanoseconds regardless
// of how many events arrived. On each tick() it:
//   1. Checks if the window has expired (now - window_open_time >= window_ns).
//   2. If yes: fires the aggregation, clears the buffer, opens a new window.
//   3. If no: pops and buffers one event (if available), returns Processed.
//
// An empty window (no events arrived in the interval) is not emitted.
//
// Example — 1-second tumbling window summing integers:
//   TumblingTimeWindow<uint64_t, uint64_t> one_sec(
//       "1sec_sum", &q_in, &q_out,
//       std::chrono::seconds(1),
//       [](const std::vector<uint64_t>& v) {
//           uint64_t s = 0; for (auto x : v) s += x; return s; });
template <typename T, typename Out>
class TumblingTimeWindow : public IOperator {
public:
    using InQueue   = SPSCQueue<Event<T>>;
    using OutQueue  = SPSCQueue<Event<Out>>;
    using AggrFn    = std::function<Out(const std::vector<T>&)>;

    TumblingTimeWindow(std::string name,
                       InQueue*    input,
                       OutQueue*   output,
                       std::chrono::nanoseconds window_duration,
                       AggrFn      aggr)
        : IOperator(std::move(name))
        , input_(input), output_(output)
        , window_ns_(window_duration.count())
        , aggr_(std::move(aggr))
    {
        reset_window();
    }

    void attach_metrics(OperatorMetrics* m) { metrics_ = m; }

    OpStatus tick() override {
        if (has_pending_) {
            if (output_->try_push(pending_)) {
                has_pending_ = false;
                if (metrics_) metrics_->events_processed.increment();
                return OpStatus::Processed;
            }
            if (metrics_) metrics_->events_blocked.increment();
            return OpStatus::Blocked;
        }

        // Check if the window has expired.
        std::uint64_t now = now_ns();
        if ((now - window_open_ns_) >= static_cast<std::uint64_t>(window_ns_)) {
            if (!buffer_.empty()) {
                Event<Out> out_ev;
                out_ev.timestamp_ns = window_open_ns_;
                out_ev.key          = 0;
                out_ev.seq          = window_count_++;
                out_ev.data         = aggr_(buffer_);
                buffer_.clear();
                reset_window();
                if (output_->try_push(out_ev)) {
                    if (metrics_) metrics_->events_processed.increment();
                    return OpStatus::Processed;
                }
                pending_     = out_ev;
                has_pending_ = true;
                if (metrics_) metrics_->events_blocked.increment();
                return OpStatus::Blocked;
            }
            reset_window();
        }

        // Buffer one event if available.
        Event<T> in_ev;
        if (!input_->try_pop(&in_ev)) {
            if (metrics_) metrics_->events_idle.increment();
            return OpStatus::Idle;
        }
        buffer_.push_back(in_ev.data);
        if (metrics_) metrics_->events_processed.increment();
        return OpStatus::Processed;
    }

private:
    void reset_window() {
        window_open_ns_ = now_ns();
    }

    static std::uint64_t now_ns() {
        using namespace std::chrono;
        return static_cast<std::uint64_t>(
            duration_cast<nanoseconds>(
                steady_clock::now().time_since_epoch()).count());
    }

    InQueue*          input_;
    OutQueue*         output_;
    std::int64_t      window_ns_;
    AggrFn            aggr_;
    std::vector<T>    buffer_;
    std::uint64_t     window_open_ns_{0};
    std::uint64_t     window_count_{0};
    Event<Out>        pending_{};
    bool              has_pending_{false};
    OperatorMetrics*  metrics_{nullptr};
};

} // namespace klstream
```

---

### 8.7 Sink Operator

```cpp
// include/klstream/operators/sink.hpp
#pragma once
#include "../core/operator.hpp"
#include "../core/event.hpp"
#include "../core/spsc_queue.hpp"
#include "../core/metrics.hpp"
#include <functional>
#include <cstdint>

namespace klstream {

// ── SinkOperator<T> ───────────────────────────────────────────────────────
//
// Terminal operator. Pops events from its input queue and hands them to the
// user-supplied consumer function. Has no output queue.
//
// The consumer function receives the full Event<T> (not just the payload)
// so it has access to timestamp_ns for latency measurement.
//
// Example:
//   SinkOperator<uint64_t> printer(
//       "printer", &q_in,
//       [&hist](const Event<uint64_t>& ev) {
//           hist.record(ev.latency_ns()); });
template <typename T>
class SinkOperator : public IOperator {
public:
    using Queue      = SPSCQueue<Event<T>>;
    using ConsumerFn = std::function<void(const Event<T>&)>;

    SinkOperator(std::string name, Queue* input, ConsumerFn consumer)
        : IOperator(std::move(name))
        , input_(input)
        , consumer_(std::move(consumer))
    {}

    void attach_metrics(OperatorMetrics* m) { metrics_ = m; }

    OpStatus tick() override {
        Event<T> ev;
        if (!input_->try_pop(&ev)) {
            if (metrics_) metrics_->events_idle.increment();
            return OpStatus::Idle;
        }
        consumer_(ev);
        if (metrics_) metrics_->events_processed.increment();
        return OpStatus::Processed;
    }

private:
    Queue*           input_;
    ConsumerFn       consumer_;
    OperatorMetrics* metrics_{nullptr};
};

} // namespace klstream
```

---

## 9. Build System — CMakeLists.txt

### 9.1 Root `CMakeLists.txt`

```cmake
cmake_minimum_required(VERSION 3.17)
project(KLStream VERSION 0.1.0 LANGUAGES CXX)

# ── Language standard ────────────────────────────────────────────────────
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)   # no GNU extensions; keeps us portable

# ── Platform-specific optimisation flags ────────────────────────────────
include(CheckCXXCompilerFlag)

if(CMAKE_SYSTEM_PROCESSOR MATCHES "arm64|aarch64")
    # On Apple Silicon: prefer -mcpu=apple-m3; fall back through m2, m1,
    # and finally -march=native if none are recognised (older Xcode).
    check_cxx_compiler_flag("-mcpu=apple-m3" HAS_M3)
    check_cxx_compiler_flag("-mcpu=apple-m2" HAS_M2)
    check_cxx_compiler_flag("-mcpu=apple-m1" HAS_M1)
    if(HAS_M3)
        set(NATIVE_CPU_FLAG "-mcpu=apple-m3")
    elseif(HAS_M2)
        set(NATIVE_CPU_FLAG "-mcpu=apple-m2")
    elseif(HAS_M1)
        set(NATIVE_CPU_FLAG "-mcpu=apple-m1")
    else()
        set(NATIVE_CPU_FLAG "-march=native")
    endif()
else()
    # x86-64 (CI, porting, Intel Mac)
    set(NATIVE_CPU_FLAG "-march=native")
endif()

# ── Build-type flags ─────────────────────────────────────────────────────
# Release: maximum optimisation + native CPU tuning
set(CMAKE_CXX_FLAGS_RELEASE "-O3 ${NATIVE_CPU_FLAG} -DNDEBUG")

# Debug: no optimisation, full debug info
set(CMAKE_CXX_FLAGS_DEBUG "-O0 -g3")

# RelWithDebInfo: moderate optimisation + debug info (useful for profiling
# with Instruments — symbols present without full -O0 penalty)
set(CMAKE_CXX_FLAGS_RELWITHDEBINFO "-O2 -g ${NATIVE_CPU_FLAG}")

# Default to Release if the user does not specify
if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
endif()

# ── Compiler warnings ────────────────────────────────────────────────────
add_compile_options(
    -Wall -Wextra -Wpedantic
    -Wno-unused-parameter      # common in operator stubs during development
    -Wno-gnu-anonymous-struct  # GCC extension; irrelevant on clang
)

# ── Sanitizer support ────────────────────────────────────────────────────
# Build with -DKLSTREAM_TSAN=ON to enable ThreadSanitizer.
# Build with -DKLSTREAM_ASAN=ON to enable AddressSanitizer.
# Do NOT combine TSan and ASan — they are incompatible.
option(KLSTREAM_TSAN "Enable ThreadSanitizer" OFF)
option(KLSTREAM_ASAN "Enable AddressSanitizer" OFF)

if(KLSTREAM_TSAN)
    add_compile_options(-fsanitize=thread -fno-omit-frame-pointer)
    add_link_options(-fsanitize=thread)
    message(STATUS "ThreadSanitizer ENABLED")
endif()

if(KLSTREAM_ASAN)
    add_compile_options(-fsanitize=address -fno-omit-frame-pointer)
    add_link_options(-fsanitize=address)
    message(STATUS "AddressSanitizer ENABLED")
endif()

# ── KLStream header-only interface library ───────────────────────────────
# All source code lives in headers. This CMake target just exposes the
# include directory so that every subdirectory (examples, tests, benchmarks)
# can link against klstream::klstream and get the headers.
add_library(klstream INTERFACE)
target_include_directories(klstream INTERFACE
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>
)
target_link_libraries(klstream INTERFACE pthread)
add_library(klstream::klstream ALIAS klstream)

# ── FetchContent: GoogleTest ─────────────────────────────────────────────
include(FetchContent)

FetchContent_Declare(
    googletest
    GIT_REPOSITORY https://github.com/google/googletest.git
    GIT_TAG        v1.14.0
    GIT_SHALLOW    TRUE
)
set(INSTALL_GTEST OFF CACHE BOOL "" FORCE)
set(BUILD_GMOCK   OFF CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(googletest)

# ── FetchContent: Google Benchmark ───────────────────────────────────────
FetchContent_Declare(
    googlebenchmark
    GIT_REPOSITORY https://github.com/google/benchmark.git
    GIT_TAG        v1.8.4
    GIT_SHALLOW    TRUE
)
set(BENCHMARK_ENABLE_TESTING       OFF CACHE BOOL "" FORCE)
set(BENCHMARK_ENABLE_INSTALL       OFF CACHE BOOL "" FORCE)
set(BENCHMARK_DOWNLOAD_DEPENDENCIES ON  CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(googlebenchmark)

# ── Subdirectories ────────────────────────────────────────────────────────
add_subdirectory(examples)
add_subdirectory(tests)
add_subdirectory(benchmarks)
```

### 9.2 `tests/CMakeLists.txt`

```cmake
enable_testing()

set(TEST_SOURCES
    test_spsc_queue.cpp
    test_mpmc_queue.cpp
    test_operators.cpp
    test_backpressure.cpp
    test_pipeline_integration.cpp
)

foreach(src ${TEST_SOURCES})
    get_filename_component(name ${src} NAME_WE)
    add_executable(${name} ${src})
    target_link_libraries(${name}
        PRIVATE klstream::klstream GTest::gtest_main)
    gtest_discover_tests(${name})
endforeach()
```

### 9.3 `benchmarks/CMakeLists.txt`

```cmake
set(BENCH_SOURCES
    bench_spsc_queue.cpp
    bench_pipeline_throughput.cpp
    bench_ysb.cpp
)

foreach(src ${BENCH_SOURCES})
    get_filename_component(name ${src} NAME_WE)
    add_executable(${name} ${src})
    target_link_libraries(${name}
        PRIVATE klstream::klstream benchmark::benchmark_main)
endforeach()
```

### 9.4 `examples/CMakeLists.txt`

```cmake
add_executable(basic_pipeline basic_pipeline/main.cpp)
target_link_libraries(basic_pipeline PRIVATE klstream::klstream)

add_executable(ysb_pipeline yahoo_streaming_benchmark/main.cpp)
target_link_libraries(ysb_pipeline PRIVATE klstream::klstream)
```

---

## 10. Example 1 — Basic End-to-End Pipeline

This is the pipeline from the original specification:
`Source → Map → Filter → Aggregate → Sink`

```cpp
// examples/basic_pipeline/main.cpp
#include "klstream/core/config.hpp"
#include "klstream/core/event.hpp"
#include "klstream/core/spsc_queue.hpp"
#include "klstream/core/metrics.hpp"
#include "klstream/core/runtime.hpp"
#include "klstream/operators/source.hpp"
#include "klstream/operators/map.hpp"
#include "klstream/operators/filter.hpp"
#include "klstream/operators/aggregate.hpp"
#include "klstream/operators/sink.hpp"

#include <atomic>
#include <chrono>
#include <cstdint>
#include <iostream>

int main() {
    using namespace klstream;
    using namespace std::chrono;

    // ── Queues ────────────────────────────────────────────────────────────
    // Each queue is SPSC (one producer, one consumer).
    // Capacity: 4096 events (the DEFAULT_QUEUE_CAPACITY constant).
    // Changing this to 64 or 16384 is a one-argument change — experiment here.
    SPSCQueue<Event<uint64_t>> q_src_map(4096);   // source  → map
    SPSCQueue<Event<uint64_t>> q_map_flt(4096);   // map     → filter
    SPSCQueue<Event<uint64_t>> q_flt_agg(4096);   // filter  → aggregate
    SPSCQueue<Event<uint64_t>> q_agg_snk(4096);   // aggregate → sink

    // ── Metrics ───────────────────────────────────────────────────────────
    OperatorMetrics m_src("source");
    OperatorMetrics m_map("square_map");
    OperatorMetrics m_flt("even_filter");
    OperatorMetrics m_agg("running_sum");
    OperatorMetrics m_snk("sink");
    LatencyHistogram latency_hist;

    // ── Operators ─────────────────────────────────────────────────────────
    std::atomic<uint64_t> global_seq{0};

    // Source: generates integers 0, 1, 2, 3, ... (unlimited)
    SourceOperator<uint64_t> source(
        "source", &q_src_map,
        [&global_seq](Event<uint64_t>& out, uint64_t /*seq*/) -> bool {
            out = Event<uint64_t>::make(global_seq.fetch_add(1));
            return true;
        });
    source.attach_metrics(&m_src);
    // Optional rate cap: uncomment to limit to 1,000,000 events/sec
    // source.enable_rate_limiting(1'000'000.0);

    // Map: square each value
    MapOperator<uint64_t, uint64_t> squarer(
        "square_map", &q_src_map, &q_map_flt,
        [](uint64_t x) -> uint64_t { return x * x; });
    squarer.attach_metrics(&m_map);

    // Filter: keep only even-squared values (i.e., even x, since odd^2 is odd)
    FilterOperator<uint64_t> even_filter(
        "even_filter", &q_map_flt, &q_flt_agg,
        [](uint64_t x) -> bool { return (x % 2 == 0); });
    even_filter.attach_metrics(&m_flt);

    // Aggregate: running sum of all even-squared values
    AggregateOperator<uint64_t, uint64_t, uint64_t> summer(
        "running_sum", &q_flt_agg, &q_agg_snk,
        0ULL,
        [](uint64_t& st, const uint64_t& x) { st += x; },
        [](const uint64_t& st) { return st; });
    summer.attach_metrics(&m_agg);

    // Sink: record latency and count events
    SinkOperator<uint64_t> sink(
        "sink", &q_agg_snk,
        [&latency_hist](const Event<uint64_t>& ev) {
            latency_hist.record(ev.latency_ns());
        });
    sink.attach_metrics(&m_snk);

    // ── Runtime ───────────────────────────────────────────────────────────
    // Four workers:
    //   Worker 0 (P-core): runs source + squarer  (generation + transform)
    //   Worker 1 (P-core): runs even_filter       (selective pass-through)
    //   Worker 2 (P-core): runs running_sum        (stateful accumulation)
    //   Worker 3 (E-core): runs sink               (lightweight I/O)
    Runtime rt;
    rt.add_worker(CoreAffinity::Performance);  // Worker 0
    rt.add_worker(CoreAffinity::Performance);  // Worker 1
    rt.add_worker(CoreAffinity::Performance);  // Worker 2
    rt.add_worker(CoreAffinity::Efficiency);   // Worker 3

    rt.register_op(&source,      0, CoreAffinity::Performance);
    rt.register_op(&squarer,     0, CoreAffinity::Performance);
    rt.register_op(&even_filter, 1, CoreAffinity::Performance);
    rt.register_op(&summer,      2, CoreAffinity::Performance);
    rt.register_op(&sink,        3, CoreAffinity::Efficiency);

    rt.metrics().add(&m_src);
    rt.metrics().add(&m_map);
    rt.metrics().add(&m_flt);
    rt.metrics().add(&m_agg);
    rt.metrics().add(&m_snk);

    // ── Run for 10 seconds ────────────────────────────────────────────────
    std::cout << "KLStream basic_pipeline running for 10 seconds...\n";
    rt.start();
    rt.wait_for(seconds(10));
    rt.stop();

    // ── Print final latency percentiles ───────────────────────────────────
    std::cout << "\nLatency percentiles (end-to-end, microseconds):\n"
              << "  p50:  " << latency_hist.percentile(0.50) << " us\n"
              << "  p99:  " << latency_hist.percentile(0.99) << " us\n"
              << "  p999: " << latency_hist.percentile(0.999) << " us\n";

    return 0;
}
```

---

## 11. Example 2 — Yahoo Streaming Benchmark (YSB) Pipeline

The Yahoo Streaming Benchmark is the standard comparison point for all papers in
this field (BriskStream, WindFlow, LightSaber, Zeuch et al. all report on it). It
models an ad-analytics system: `Source → Filter → Join → TumblingWindow → Sink`.

```cpp
// examples/yahoo_streaming_benchmark/main.cpp
#include "klstream/core/config.hpp"
#include "klstream/core/event.hpp"
#include "klstream/core/spsc_queue.hpp"
#include "klstream/core/metrics.hpp"
#include "klstream/core/runtime.hpp"
#include "klstream/operators/source.hpp"
#include "klstream/operators/filter.hpp"
#include "klstream/operators/map.hpp"
#include "klstream/operators/window.hpp"
#include "klstream/operators/sink.hpp"

#include <array>
#include <chrono>
#include <cstdint>
#include <iostream>
#include <random>
#include <string>
#include <unordered_map>

namespace ysb {

// ── YSB event types ───────────────────────────────────────────────────────
// The benchmark specifies these fields for each ad event.
struct AdEvent {
    uint32_t ad_id;
    uint32_t campaign_id;
    uint8_t  event_type;  // 0=view, 1=click, 2=purchase
};

// The aggregated result pushed to the sink.
struct CampaignResult {
    uint32_t campaign_id;
    uint64_t view_count;
};

// Simulate a campaign lookup table (replaces Kafka join in the original YSB).
// In the original benchmark this is a Redis lookup; we model it as a flat array.
static constexpr int N_CAMPAIGNS = 100;
static constexpr int ADS_PER_CAMPAIGN = 10;
static constexpr int N_ADS = N_CAMPAIGNS * ADS_PER_CAMPAIGN;

// campaign_table[ad_id] = campaign_id
static std::array<uint32_t, N_ADS> campaign_table;

void build_campaign_table() {
    for (int i = 0; i < N_ADS; ++i) {
        campaign_table[i] = i / ADS_PER_CAMPAIGN;
    }
}

} // namespace ysb

int main() {
    using namespace klstream;
    using namespace std::chrono;
    using namespace ysb;

    build_campaign_table();

    std::mt19937 rng(42);
    std::uniform_int_distribution<uint32_t> ad_dist(0, N_ADS - 1);
    std::uniform_int_distribution<uint8_t>  type_dist(0, 2);

    // ── Queues ────────────────────────────────────────────────────────────
    // YSB pipeline:
    //   Source<AdEvent> -> Filter<AdEvent> -> Map<AdEvent,CampaignResult>
    //     -> TumblingCountWindow<CampaignResult,CampaignResult>
    //     -> Sink<CampaignResult>
    SPSCQueue<Event<AdEvent>>         q_src_flt(4096);
    SPSCQueue<Event<AdEvent>>         q_flt_map(4096);
    SPSCQueue<Event<CampaignResult>>  q_map_win(4096);
    SPSCQueue<Event<CampaignResult>>  q_win_snk(4096);

    OperatorMetrics m_src("ysb_source");
    OperatorMetrics m_flt("view_filter");
    OperatorMetrics m_map("campaign_join");
    OperatorMetrics m_win("10sec_window");
    OperatorMetrics m_snk("ysb_sink");
    LatencyHistogram latency;
    std::atomic<uint64_t> total_out{0};

    // Source: generates random AdEvents
    SourceOperator<AdEvent> source(
        "ysb_source", &q_src_flt,
        [&rng, &ad_dist, &type_dist]
        (Event<AdEvent>& out, uint64_t seq) -> bool {
            out = Event<AdEvent>::make(
                AdEvent{ ad_dist(rng), 0, type_dist(rng) }, 0, seq);
            return true;
        });
    source.attach_metrics(&m_src);

    // Filter: keep only event_type == 0 (view events)
    FilterOperator<AdEvent> view_filter(
        "view_filter", &q_src_flt, &q_flt_map,
        [](const AdEvent& e) { return e.event_type == 0; });
    view_filter.attach_metrics(&m_flt);

    // Map (replaces the distributed join): look up campaign_id
    MapOperator<AdEvent, CampaignResult> join(
        "campaign_join", &q_flt_map, &q_map_win,
        [](const AdEvent& e) -> CampaignResult {
            return { campaign_table[e.ad_id], 1 };
        });
    join.attach_metrics(&m_map);

    // Window: count views per campaign over every 1000 events
    // (replaces the original 10-second tumbling window for benchmark clarity)
    TumblingCountWindow<CampaignResult, CampaignResult> win(
        "1k_window", &q_map_win, &q_win_snk, 1000,
        [](const std::vector<CampaignResult>& buf) -> CampaignResult {
            std::unordered_map<uint32_t, uint64_t> counts;
            for (const auto& r : buf) counts[r.campaign_id] += r.view_count;
            // Return the campaign with most views in this window.
            auto it = std::max_element(counts.begin(), counts.end(),
                [](const auto& a, const auto& b){ return a.second < b.second; });
            return { it->first, it->second };
        });
    win.attach_metrics(&m_win);

    // Sink
    SinkOperator<CampaignResult> sink(
        "ysb_sink", &q_win_snk,
        [&latency, &total_out](const Event<CampaignResult>& ev) {
            latency.record(ev.latency_ns());
            total_out.fetch_add(1, std::memory_order_relaxed);
        });
    sink.attach_metrics(&m_snk);

    // ── Runtime ───────────────────────────────────────────────────────────
    Runtime rt;
    rt.add_worker(CoreAffinity::Performance);  // 0: source + filter
    rt.add_worker(CoreAffinity::Performance);  // 1: join + window
    rt.add_worker(CoreAffinity::Efficiency);   // 2: sink

    rt.register_op(&source,      0);
    rt.register_op(&view_filter, 0);
    rt.register_op(&join,        1);
    rt.register_op(&win,         1);
    rt.register_op(&sink,        2);

    for (auto* m : {&m_src, &m_flt, &m_map, &m_win, &m_snk})
        rt.metrics().add(m);

    std::cout << "KLStream Yahoo Streaming Benchmark — 30 seconds\n";
    rt.start();
    rt.wait_for(seconds(30));
    rt.stop();

    std::cout
        << "Total window results: " << total_out.load() << "\n"
        << "p50 latency: " << latency.percentile(0.50) << " us\n"
        << "p99 latency: " << latency.percentile(0.99) << " us\n";

    return 0;
}
```

---

## 12. Testing Strategy (GoogleTest)

Each test file lives in `tests/`. Run all tests with:

```bash
cd build && ctest --output-on-failure
```

Run with ThreadSanitizer (the most important mode for this project):

```bash
cmake -B build_tsan -DKLSTREAM_TSAN=ON -DCMAKE_BUILD_TYPE=Debug
cmake --build build_tsan
cd build_tsan && ctest --output-on-failure
```

### 12.1 `test_spsc_queue.cpp` — What to Test

```
Test 1: SingleThreaded_PushPop
   Push N items on one thread, pop them on the same thread.
   Assert: all items returned in FIFO order, none lost.

Test 2: CapacityRespected
   Fill the queue to capacity. Assert try_push returns false on the next call.
   Pop one. Assert try_push now returns true.

Test 3: ConcurrentProducerConsumer
   Producer thread pushes 1,000,000 sequential integers.
   Consumer thread pops them.
   Assert: all integers received in order, no integer received twice.
   Run with TSan enabled to verify no data races.

Test 4: OccupancyApproximate
   Push capacity/2 items. Assert occupancy() is approximately 0.5.
   (Within 5% tolerance — occupancy() is deliberately approximate.)

Test 5: PowerOfTwoEnforced
   Assert that constructing SPSCQueue(3) either asserts or throws.
   (Capacity must be a power of 2.)
```

### 12.2 `test_operators.cpp` — What to Test

```
Test 1: MapOperator_Squares
   Queue pair, push {1,2,3,4,5}, run map tick() 5 times, pop outputs.
   Assert: outputs are {1,4,9,16,25}.

Test 2: FilterOperator_Evens
   Push {1,2,3,4,5}, run filter(even) tick() 5 times.
   Assert: output queue contains only {2,4}.

Test 3: AggregateOperator_RunningSum
   Push {1,2,3,4,5}, run aggregate tick() 5 times.
   Assert: running sums are {1,3,6,10,15}.

Test 4: TumblingCountWindow_Fires
   window_size=3. Push {10,20,30,40,50,60}.
   Assert: two outputs produced: sum(10,20,30)=60, sum(40,50,60)=150.

Test 5: Operator_BlockedWhenOutputFull
   Create output queue of capacity 2. Push until full.
   Assert next tick() returns OpStatus::Blocked.
   Pop one from output. Assert next tick() returns Processed.

Test 6: SourceOperator_PendingRetry
   Output queue capacity = 1. Fill it.
   Run source tick() — should generate event, fail to push, cache as pending,
   return Blocked.
   Pop from output queue.
   Run source tick() again — should push the SAME cached event (not generate new),
   return Processed.
```

### 12.3 `test_pipeline_integration.cpp` — What to Test

```
Test 1: Source_Map_Sink_E2E
   Wire: Source → Map(square) → Sink
   Run runtime for 100 ms.
   Assert: sink received > 0 events, all values are perfect squares.

Test 2: BackpressurePropagates
   Wire: Source → Sink (capacity=4, slow sink)
   Slow the sink artificially (sleep 1ms per event).
   Assert: source metrics show events_blocked > 0 within 500ms.

Test 3: OrderPreserved
   Wire: Source → Map(identity) → Sink
   Assert: seq numbers at the sink are monotonically increasing.
   (Ordering guarantee within a single SPSC queue.)

Test 4: ShutdownClean
   Start a pipeline, run for 200ms, call rt.stop().
   Assert: no crash, no TSan warnings, all threads joined.
```

---

## 13. Benchmarking Strategy (Google Benchmark)

Run all benchmarks in Release mode without TSan:

```bash
cmake -B build_release -DCMAKE_BUILD_TYPE=Release
cmake --build build_release -j
./build_release/benchmarks/bench_spsc_queue
./build_release/benchmarks/bench_pipeline_throughput
./build_release/benchmarks/bench_ysb
```

### 13.1 `bench_spsc_queue.cpp`

```cpp
// benchmarks/bench_spsc_queue.cpp
#include <benchmark/benchmark.h>
#include "klstream/core/spsc_queue.hpp"
#include "klstream/core/event.hpp"
#include <thread>

using namespace klstream;

// ── Raw throughput: how fast can one SPSC queue push+pop? ────────────────
// Expected on M3: 200–500 million events/sec (this is the upper bound for
// the entire runtime — no pipeline can be faster than its queues).
static void BM_SPSC_Throughput(benchmark::State& state) {
    SPSCQueue<IntEvent> q(static_cast<size_t>(state.range(0)));
    IntEvent ev = IntEvent::make(42);
    IntEvent out;
    auto producer = std::thread([&]{
        for (auto _ : state) {
            q.push(ev);  // blocks if full — this is the paired throughput test
        }
    });
    for (auto _ : state) {
        while (!q.try_pop(&out)) {}
    }
    producer.join();
    state.SetItemsProcessed(state.iterations());
}
BENCHMARK(BM_SPSC_Throughput)
    ->Arg(64)->Arg(256)->Arg(1024)->Arg(4096)->Arg(16384)
    ->UseRealTime()->ThreadRange(1, 1);

// ── Latency: round-trip time for one event through a SPSC queue ──────────
// (ping-pong between two threads)
static void BM_SPSC_RTT_Latency(benchmark::State& state) {
    SPSCQueue<IntEvent> q_fwd(256);
    SPSCQueue<IntEvent> q_bck(256);
    IntEvent ping = IntEvent::make(0);
    IntEvent pong;
    bool running = true;
    auto echo = std::thread([&]{
        IntEvent e;
        while (running) {
            if (q_fwd.try_pop(&e)) q_bck.push(e);
        }
    });
    for (auto _ : state) {
        q_fwd.push(ping);
        while (!q_bck.try_pop(&pong)) {}
    }
    running = false;
    echo.join();
    state.SetLabel("RTT ns per event");
}
BENCHMARK(BM_SPSC_RTT_Latency)->UseRealTime();

BENCHMARK_MAIN();
```

### 13.2 `bench_pipeline_throughput.cpp` — Key Experiments

```
Experiment 1: Worker count scaling
   Pipeline: Source → Map → Filter → Sink
   Vary: 1 worker (all ops on one thread), 2 workers, 3 workers, 4 workers.
   Measure: total sink events/sec over 5 seconds.
   Expected: throughput increases up to 3-4 workers, then levels off.

Experiment 2: Queue size sensitivity
   Pipeline: Source → Map → Sink (2 workers)
   Vary queue capacity: 64, 256, 1024, 4096, 16384.
   Measure: throughput and p99 latency.
   Expected: very small queues increase latency but may improve cache footprint;
   very large queues reduce backpressure but increase memory and latency.

Experiment 3: Operator compute cost
   Replace Map(x*x) with Map(expensive_fn) where expensive_fn does
   100 / 1000 / 10000 iterations of a floating-point computation.
   Measure: throughput degradation as operator cost increases.
   Expected: at some cost threshold, the bottleneck shifts from queue
   bandwidth to CPU, and adding more workers starts helping.

Experiment 4: Affinity vs. no-affinity (Section 14.2 preview)
   Run the basic pipeline with all workers set to CoreAffinity::Any
   vs. the configured P/E assignment.
   Measure: throughput and p99.
```

### 13.3 Reporting Format

All benchmark results should be saved to CSV and plotted. The `run_all_benchmarks.sh`
script handles this:

```bash
#!/usr/bin/env bash
# scripts/run_all_benchmarks.sh
set -e

BUILD=./build_release
RESULTS=./research/results
mkdir -p $RESULTS

echo "Running SPSC queue benchmarks..."
$BUILD/benchmarks/bench_spsc_queue \
    --benchmark_format=csv \
    --benchmark_out=$RESULTS/spsc_queue.csv

echo "Running pipeline throughput benchmarks..."
$BUILD/benchmarks/bench_pipeline_throughput \
    --benchmark_format=csv \
    --benchmark_out=$RESULTS/pipeline_throughput.csv

echo "Running YSB benchmark..."
$BUILD/benchmarks/bench_ysb \
    --benchmark_format=csv \
    --benchmark_out=$RESULTS/ysb.csv

echo "All benchmarks complete. Results in $RESULTS/"
```

---

## 14. Research Extensions

These three sections convert KLStream from an implementation project into a research
platform. Each provides a concrete experimental design with a testable hypothesis and
specific measurements.

---

### 14.1 Adaptive Backpressure Evaluation

**Hypothesis:** EMA-based predictive backpressure with a token-bucket rate limiter
reduces p99 latency variance and average p99 latency under bursty workloads compared
to binary block/unblock backpressure, at the cost of a small throughput reduction.

**Background from prior art:**
- GOVERNOR (ICAC 2017) showed a PID-based adaptive controller reduced Spark Streaming
  latency spikes by up to 40% under bursty Kafka inputs.
- Flink's credit-based flow control (1.5, 2019) reduced latency spikes by decoupling
  backpressure from TCP blocking.
- **No prior work** has evaluated gradual vs. binary backpressure in a single-node,
  in-memory C++ runtime — this is the gap KLStream fills.

**Experimental design:**

Step 1: Implement two pipeline modes, selectable via a command-line flag.
- Mode A (Baseline): Binary block — source pushes until output queue is full,
  then blocks (default `try_push()` behavior already implemented).
- Mode B (Adaptive): Source uses `EMAOccupancyTracker` + `TokenBucketRateLimiter`
  to detect rising pressure and reduce its rate before the queue fills.

Step 2: Implement a "bursty source" generator that alternates between:
- High-rate phase: emits events as fast as possible for `burst_duration_ms`.
- Low-rate phase: emits at `baseline_rate` events/sec for `quiet_duration_ms`.

```cpp
// research/adaptive_backpressure/main.cpp (key snippet)

// Bursty generator: burst at full speed for 200ms, quiet at 10% rate for 800ms
std::atomic<bool> in_burst{false};
auto bursty_gen = [&in_burst](Event<uint64_t>& out, uint64_t seq) -> bool {
    // Burstiness is toggled by a timer thread running in the background.
    if (!in_burst.load(std::memory_order_relaxed)) {
        std::this_thread::sleep_for(std::chrono::microseconds(100)); // ~10k/sec
    }
    out = Event<uint64_t>::make(seq, 0, seq);
    return true;
};
```

Step 3: Measure for 60 seconds under both modes with 3 queue capacities (256, 1024,
4096) and 3 burst intensities.

**Metrics to collect:**
- p50, p99, p999 end-to-end latency (from `LatencyHistogram` at sink)
- Total throughput (events/sec — from `OperatorMetrics::events_processed`)
- Backpressure frequency (events_blocked/sec — from `OperatorMetrics::events_blocked`)
- Queue occupancy over time (sample `q.occupancy()` every 10ms from a reporter thread)

**Expected results table:**

| Mode     | Burst Intensity | p99 Latency | Throughput | Blocked/sec |
|----------|-----------------|-------------|------------|-------------|
| Baseline | High            | HIGH        | HIGH       | HIGH        |
| Adaptive | High            | LOWER       | SLIGHTLY↓  | LOWER       |
| Baseline | Low             | LOW         | HIGH       | ZERO        |
| Adaptive | Low             | LOW         | HIGH       | ZERO        |

**Sweep script:**

```bash
#!/usr/bin/env bash
# research/adaptive_backpressure/run_experiment.sh

BUILD=./build_release/research/adaptive_backpressure
RESULTS=./research/results

for MODE in baseline adaptive; do
  for QSIZE in 256 1024 4096; do
    for BURST in low medium high; do
      echo "Mode=$MODE QSize=$QSIZE Burst=$BURST"
      $BUILD/adaptive_bp_experiment \
          --mode=$MODE \
          --queue_size=$QSIZE \
          --burst_level=$BURST \
          --duration=60 \
          --output=$RESULTS/bp_${MODE}_q${QSIZE}_${BURST}.csv
    done
  done
done
```

**What to write in the paper:**
- Section "Methodology": describe the bursty workload model, the two BP modes,
  and the metrics.
- Section "Results": present a 2×3 table of p99 latency (mode × queue size).
  Plot queue occupancy over time for one representative run of each mode side-by-side.
- Section "Discussion": explain why the EMA helps (queue never hits 100% so blocking
  is shorter), and why throughput is marginally lower (rate limiter adds overhead).
- Related work: cite GOVERNOR (ICAC 2017), Flink credit-based flow control.

---

### 14.2 P-core / E-core Aware Scheduling Evaluation

**Hypothesis:** Assigning compute-heavy operators (Map, Aggregate) to Performance
cores and lightweight operators (Source, Sink) to Efficiency cores improves total
throughput and reduces p99 latency compared to the OS-default assignment on the
Apple M3 MacBook Air.

**Background from prior art:**
- Bindi et al. (IJPP 2026, preprint November 2025) showed thread pinning significantly
  affects throughput in WindFlow/FastFlow on x86. No Apple Silicon / ARM AMP work exists.
- PMCSched (2023) and COLAB (2020) study AMP scheduling but at OS level, not for
  streaming runtimes.
- **No prior paper** has studied operator-to-core-type assignment for stream processing
  on Apple M-series — this is the most novel contribution KLStream can make.

**Experimental design:**

Define four affinity configurations tested as command-line parameters:

| Config | Source | Map/Filter | Aggregate/Window | Sink |
|--------|--------|------------|-----------------|------|
| `all_any`  | Any | Any | Any | Any |
| `all_perf` | Performance | Performance | Performance | Performance |
| `optimised`| Efficiency | Performance | Performance | Efficiency |
| `reversed` | Performance | Efficiency | Efficiency | Performance |

`optimised` is the hypothesis: heaviest compute on P-cores, I/O boundary on E-cores.
`reversed` is a deliberate worst case: I/O boundary (with rate limiting overhead) on
P-cores, compute on E-cores.

```cpp
// research/core_pinning/main.cpp (key snippet)

struct AffinityConfig {
    CoreAffinity source;
    CoreAffinity compute;  // Map, Filter, Aggregate
    CoreAffinity sink;
};

AffinityConfig configs[] = {
    { CoreAffinity::Any,         CoreAffinity::Any,         CoreAffinity::Any         }, // all_any
    { CoreAffinity::Performance, CoreAffinity::Performance, CoreAffinity::Performance }, // all_perf
    { CoreAffinity::Efficiency,  CoreAffinity::Performance, CoreAffinity::Efficiency  }, // optimised
    { CoreAffinity::Performance, CoreAffinity::Efficiency,  CoreAffinity::Performance }, // reversed
};
```

**Metrics to collect:**
- Total throughput (events/sec) over 30 seconds
- p50 and p99 latency
- Whether the M3 thermal throttles under `all_perf` mode (watch CPU frequency via
  `sudo powermetrics --samplers cpu_power -i 1000` during the run)

**Why this is publishable:**
The Apple M3 is in millions of developer laptops. There is literally zero published
work on stream processing performance on Apple Silicon. A paper titled "Stream
Processing Operator Placement on Asymmetric ARM Cores: The Apple M3 Case Study"
would be the first of its kind in any venue.

**What to write in the paper:**
- Describe the M3 core asymmetry (4P at 4.05GHz, 4E at 2.75GHz, 128-byte cache lines).
- Describe the QoS API and its limitations (hint-based, not hard pinning).
- Present a 4×3 table (config × metric: throughput, p50, p99).
- Discussion: identify which operators benefit most from P-cores (aggregation with
  large state, windowed aggregation); identify which operators waste P-cores (source
  with rate limiting is mostly sleeping, sink is mostly doing a counter increment).

---

### 14.3 Consistent-Hashing Operator Placement (Advanced)

**Hypothesis:** Using a DHT-inspired consistent hash ring to assign keyed events to
parallel operator instances reduces load imbalance (measured as standard deviation of
queue depths) more effectively than modulo-hash assignment under Zipf-skewed key
distributions.

**Background from prior art:**
- Partial Key Grouping (PKG, ICDE 2015) applied power-of-two-choices to distributed
  stream partitioning. Up to 60% better throughput than modulo hashing on Storm.
- DPA Load Balancer (arxiv 2023) used consistent hashing for distributed actor systems.
- **No prior work** has applied consistent hashing to single-node, single-process
  parallel operator instances sharing an in-process queue.

**Only attempt this after Sections 14.1 and 14.2 are complete.** It requires
restructuring the pipeline to support multiple parallel instances of stateful operators.

**Implementation overview:**

```cpp
// A hash ring with V virtual nodes per physical instance.
// For a stateful operator with N parallel instances, the ring assigns
// each key to one of the N instances by hashing the key onto the ring.

class ConsistentHashRing {
    static constexpr int VIRTUAL_NODES = 150;
public:
    ConsistentHashRing(int n_instances) {
        for (int i = 0; i < n_instances; ++i) {
            for (int v = 0; v < VIRTUAL_NODES; ++v) {
                std::string label = "instance_" + std::to_string(i)
                                  + "_vnode_" + std::to_string(v);
                std::size_t h = std::hash<std::string>{}(label);
                ring_[h] = i;
            }
        }
    }

    int instance_for_key(std::uint64_t key) const {
        auto it = ring_.lower_bound(key);
        if (it == ring_.end()) it = ring_.begin();
        return it->second;
    }

private:
    std::map<std::size_t, int> ring_;
};
```

**What changes in the pipeline:**
- Instead of one `SPSCQueue` between Map and Aggregate, there are N `SPSCQueue`s —
  one per parallel Aggregate instance.
- A new `PartitioningOperator<T>` sits between Map and the N Aggregate instances.
  It pops each event and routes it to `instance_for_key(event.key)`.

**Baseline to compare against:**
- Modulo partitioning: `instance = event.key % N`
- Round-robin: `instance = (++counter) % N`

**Workload:** Zipf-distributed keys (a few "hot keys" get the vast majority of events).
The parameter `zipf_s` controls skew: `s=0` is uniform, `s=2` is highly skewed.

---

### 14.4 GraphBuilder DSL (Future Work)

The MVP wires the pipeline by hand in `main()`. For a larger project, a fluent DSL
makes the code dramatically more readable and eliminates wiring errors:

```cpp
// Conceptual API — not implemented in MVP, sketch only
auto [runtime, metrics] =
    klstream::GraphBuilder{}
        .source<uint64_t>("src", gen_fn)
            .with_affinity(CoreAffinity::Efficiency)
            .with_rate_limit(1'000'000)
        .map<uint64_t, uint64_t>("square", [](uint64_t x){ return x*x; })
            .with_affinity(CoreAffinity::Performance)
        .filter<uint64_t>("even", [](uint64_t x){ return x%2==0; })
        .window<uint64_t, uint64_t>("sum_100", 100, sum_fn)
        .sink<uint64_t>("out", consumer_fn)
            .with_affinity(CoreAffinity::Efficiency)
        .queue_capacity(4096)
        .workers(4)
        .build();

runtime.start();
runtime.wait_for(std::chrono::seconds(30));
runtime.stop();
```

Implementing this DSL requires a chain of operator-builder objects, each holding a
pointer to the previous stage's output queue. Defer this to a second phase after the
MVP is validated.

---

## 15. Phased Implementation Roadmap

Follow these phases strictly. Do not start Phase 2 until Phase 1 tests pass with TSan.

```
Phase 1: Core Infrastructure (Week 1-2)
  [x] Setup CMake, directory structure, .gitignore
  [x] Write config.hpp, event.hpp
  [x] Write spsc_queue.hpp
  [x] Write tests/test_spsc_queue.cpp
  [x] Run tests with -DKLSTREAM_TSAN=ON — zero races
  [x] Write mpmc_queue.hpp
  [x] Write tests/test_mpmc_queue.cpp — zero races
  [x] Write operator.hpp (IOperator + OpStatus)
  [x] Write pinning.hpp + verify QoS calls compile on macOS

Phase 2: Operator Library (Week 2-3)
  [x] Write source.hpp (no rate limiter yet)
  [x] Write map.hpp
  [x] Write filter.hpp
  [x] Write aggregate.hpp
  [x] Write window.hpp (count window first, then time window)
  [x] Write sink.hpp
  [x] Write tests/test_operators.cpp
  [x] Run all operator tests with TSan — zero races

Phase 3: Runtime & Integration (Week 3-4)
  [x] Write metrics.hpp
  [x] Write worker.hpp
  [x] Write runtime.hpp
  [x] Write tests/test_pipeline_integration.cpp
  [x] Write examples/basic_pipeline/main.cpp
  [x] Run basic pipeline — confirm it produces output without crashing
  [x] Run with MetricsReporter — confirm events/sec printed every second

Phase 4: Benchmarking (Week 4-5)
  [x] Write benchmarks/bench_spsc_queue.cpp — establish queue baseline
  [x] Write benchmarks/bench_pipeline_throughput.cpp
  [x] Write examples/yahoo_streaming_benchmark/main.cpp
  [x] Run YSB, record baseline throughput + latency numbers

Phase 5: Research Extension 1 — Adaptive Backpressure (Week 5-6)
  [x] Write backpressure.hpp (EMAOccupancyTracker + TokenBucketRateLimiter)
  [x] Add enable_rate_limiting() to source.hpp
  [x] Write research/adaptive_backpressure/main.cpp
  [x] Run sweep experiments, save CSVs
  [x] Plot results (Python matplotlib or even Excel)

Phase 6: Research Extension 2 — Core Pinning (Week 6-7)
  [x] Write research/core_pinning/main.cpp with 4 affinity configs
  [x] Run 30-second trials of each config, record throughput + latency
  [x] Run powermetrics during each trial to capture frequency/power
  [x] Plot: bar chart of throughput by config, line chart of p99 by config

Phase 7: Write-up (Week 7-8)
  [ ] Write architecture section (your system design)
  [ ] Write related work section (cite all papers in Section 18)
  [ ] Write methodology + results sections
  [ ] Submit to target venue
```

---

## 16. Build & Run Cheat Sheet

```bash
# ── Clone and setup ────────────────────────────────────────────────────
git clone <your_repo> KLStream && cd KLStream
mkdir -p build_release build_debug build_tsan

# ── Release build (for benchmarks and examples) ───────────────────────
cmake -B build_release -DCMAKE_BUILD_TYPE=Release
cmake --build build_release -j$(sysctl -n hw.ncpu)
./build_release/examples/basic_pipeline
./build_release/examples/ysb_pipeline

# ── Debug build ───────────────────────────────────────────────────────
cmake -B build_debug -DCMAKE_BUILD_TYPE=Debug
cmake --build build_debug -j$(sysctl -n hw.ncpu)
cd build_debug && ctest --output-on-failure

# ── ThreadSanitizer build (run this before every commit) ──────────────
cmake -B build_tsan -DCMAKE_BUILD_TYPE=Debug -DKLSTREAM_TSAN=ON
cmake --build build_tsan -j$(sysctl -n hw.ncpu)
cd build_tsan && ctest --output-on-failure

# ── AddressSanitizer build ────────────────────────────────────────────
cmake -B build_asan -DCMAKE_BUILD_TYPE=Debug -DKLSTREAM_ASAN=ON
cmake --build build_asan -j$(sysctl -n hw.ncpu)
cd build_asan && ctest --output-on-failure

# ── All benchmarks (release only) ─────────────────────────────────────
bash scripts/run_all_benchmarks.sh

# ── Hardware check ────────────────────────────────────────────────────
bash scripts/check_environment.sh
```

### `scripts/check_environment.sh`

```bash
#!/usr/bin/env bash
echo "=== KLStream Environment Check ==="
echo "OS:            $(uname -srm)"
echo "Compiler:      $(clang++ --version | head -1)"
echo "CMake:         $(cmake --version | head -1)"
echo "Cache line:    $(sysctl -n hw.cachelinesize) bytes"
echo "Logical CPUs:  $(sysctl -n hw.ncpu)"
echo "P-cores:       $(sysctl -n hw.perflevel0.physicalcpu 2>/dev/null || echo N/A)"
echo "E-cores:       $(sysctl -n hw.perflevel1.physicalcpu 2>/dev/null || echo N/A)"
echo "RAM:           $(($(sysctl -n hw.memsize) / 1024 / 1024 / 1024)) GB"
```

---

## 17. Key Design Decisions & Trade-offs

| Decision | Choice Made | Alternative | Why This Choice |
|---|---|---|---|
| Language | C++17 | Rust, Java, C++20 | Matches WindFlow; avoids jthread/stop_token portability issues; maximally comparable to FastFlow/BriskStream |
| Operator dispatch | Virtual `tick()` | CRTP templates | Simpler; virtual call overhead negligible vs. queue cache miss; easier to extend |
| Queue type | SPSC (default) | MPMC (multi-instance) | SPSC is 2-3x faster; MPMC provided for multi-instance operators |
| Cache line padding | 128 bytes (arm64) | 64 bytes (x86) | `sysctl -n hw.cachelinesize` returns 128 on all Apple Silicon; wrong padding = false sharing |
| Core affinity API | macOS QoS classes | `sched_setaffinity` (Linux) | macOS does not expose per-core pinning; QoS is the only supported mechanism |
| Backpressure (baseline) | Blocking `try_push` + `OpStatus::Blocked` | Drop events, grow queue | Bounded memory is a hard requirement; dropping would invalidate the aggregate results |
| Operator assignment | Static (set at startup) | Dynamic (work stealing) | Matches original spec's "static pinning recommended initially"; simpler TSan story; matches FastFlow |
| Queue capacity | Power of 2, set at construction | Dynamic resizing | Power-of-2 enables bitmask modulo (fast); fixed capacity is what gives you bounded memory |
| Worker threads | One per pipeline stage (initially) | One per core, all operators shared | Simpler static assignment; easier to reason about affinity; matches FastFlow model |
| Shutdown | `std::atomic<bool> running_` | `std::jthread` + `stop_token` | `std::jthread` requires C++20; `std::thread` + atomic flag is universally supported |
| Metrics | Relaxed atomic counters | Mutex-protected structs | `memory_order_relaxed` generates zero fence instructions on ARM; negligible overhead |
| Pending event pattern | Each operator holds one `pending_` slot | Re-push into input queue | Re-pushing into input queue would break SPSC contract (producer = upstream, not self) |

---

## 18. References & Prior Art Mapping

These are the papers you must cite. The "Section in KLStream" column shows where each
paper's ideas appear in this implementation.

| Paper | Authors | Venue | Year | Section in KLStream |
|---|---|---|---|---|
| Analyzing Efficient Stream Processing on Modern Hardware | Zeuch et al. | VLDB | 2019 | Motivation for C++ over JVM (Section 2.1) |
| FastFlow: high-performance streaming in multi-core | Aldinucci, Torquati, Danelutto et al. | Euro-Par | 2011 | SPSC queue design (7.3), static operator assignment (7.9) |
| BriskStream: scaling stream processing on NUMA systems | Zhang He Zhou He | SIGMOD | 2019 | Core-type-aware placement insight → Section 14.2 |
| LightSaber: efficient window aggregation | Theodorakis, Koliousis, Pietzuch, Pirk | SIGMOD | 2020 | Worker thread + task queue model (7.9), tumbling window (8.5/8.6) |
| StreamIt: a language for streaming apps | Thies, Karczmarek, Amarasinghe | CC | 2002 | Operator DAG model (Section 3) |
| WindFlow: parallel C++ streaming library | Mencagli, Torquati, Cardaci et al. | IEEE TPDS | 2021 | C++17 operator interface (7.5), MetricsReporter (7.7) |
| Enabling pinning strategies for DSP on multicores | Bindi, D'Amico, Mencagli, Torquati | IJPP | 2026 | Direct inspiration for Section 14.2 |
| GOVERNOR: smooth backpressure for Spark Streaming | Floratou, Floratou, Narayanan | ICAC | 2017 | Adaptive backpressure concept (14.1) |
| Operator scheduling in data stream systems | Babcock, Datar, Motwani | VLDB | 2003 | Formal scheduling model (7.9), OpStatus semantics |
| Partial key grouping | Nasir, Morales, Garcia-Soriano et al. | ICDE | 2015 | Consistent hashing placement (14.3) |
| Vyukov bounded MPMC queue | Dmitry Vyukov | 1024cores.net | 2010 | MPMC queue algorithm (7.4) |
| Flink credit-based flow control | Krettek et al. (Apache Flink 1.5) | Apache Blog | 2019 | Backpressure framing (14.1 related work) |

---

*End of KLStream Complete Implementation Guide.*

*This document was compiled from three phases of deep research into the stream processing
literature, lock-free data structures, Apple Silicon hardware architecture, and the
code-level design of FastFlow, BriskStream, LightSaber, WindFlow, and Scabbard.*

*If you implement every section of this guide, you will have: a correct and benchmarked
parallel stream processing runtime, two reproducible research experiments, and enough
material for a workshop or conference short paper.*
