
# Project Overview

KLStream is a Kafka-less Parallel Stream Processing Runtime for Multi-Core Systems.

# File: README.md

```markdown
# KLStream

**Kafka-less Parallel Stream Processing Runtime for Multi-Core Systems**

A high-performance, single-node stream processing runtime that executes continuous dataflow graphs using bounded queues, explicit backpressure, and cooperative scheduling—without external infrastructure like Kafka.

## Features

- **No External Dependencies**: Pure C++20 implementation with no message broker required
- **Bounded Memory**: Fixed-capacity queues prevent unbounded memory growth
- **Backpressure**: Automatic flow control when downstream operators slow down
- **Parallel Execution**: Worker thread pool with configurable scheduling policies
- **Modular Operators**: Composable source, map, filter, and sink operators
- **Metrics Collection**: Built-in performance monitoring and statistics

## Quick Start

### Prerequisites

- C++20 compatible compiler (GCC 11+, Clang 14+)
- CMake 3.20+
- Ninja (recommended) or Make
- Docker (for x86_64 Linux development on macOS ARM)

### Building Locally (Native)

```bash
# Clone and enter directory
cd brolq

# Make dev script executable
chmod +x scripts/dev.sh

# Build (Debug by default)
./scripts/dev.sh build

# Build Release
./scripts/dev.sh build --release

# Run tests
./scripts/dev.sh test

# Run benchmarks
./scripts/dev.sh bench
```

### Building with Docker (x86_64 Linux on macOS ARM)

For M1/M2/M3 Mac users who need to target x86_64 Linux:

```bash
# Enter Docker development shell
./scripts/dev.sh docker shell

# Inside container, build and test
cmake -B build -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel
cd build && ctest --output-on-failure
```

Or build everything in one command:

```bash
docker compose build build
```

### Running the Example

```bash
# After building
./build/klstream_example_pipeline
```

## Project Structure

```
brolq/
├── include/klstream/        # Public headers
│   ├── core/
│   │   ├── event.hpp       # Event types
│   │   ├── queue.hpp       # Bounded thread-safe queues
│   │   ├── operator.hpp    # Base operator interfaces
│   │   ├── scheduler.hpp   # Scheduling policies
│   │   ├── worker_pool.hpp # Worker thread management
│   │   ├── runtime.hpp     # Main runtime coordination
│   │   └── metrics.hpp     # Metrics collection
│   └── operators/
│       ├── source.hpp      # Source operators
│       ├── sink.hpp        # Sink operators
│       ├── map.hpp         # Map transformations
│       └── filter.hpp      # Filter predicates
├── src/core/               # Implementation files
├── examples/               # Example applications
├── tests/                  # Unit and integration tests
├── benchmarks/             # Performance benchmarks
├── scripts/                # Development scripts
├── CMakeLists.txt          # Build configuration
├── Dockerfile              # Multi-stage Docker build
└── docker-compose.yml      # Docker Compose configuration
```

## Architecture

### Stream Graph Model

```
Source → Operator → Operator → ... → Sink
           ↑           ↑
        Queue       Queue
      (bounded)   (bounded)
```

### Key Components

1. **Events**: Immutable data units with optional metadata (key, timestamp)
2. **Queues**: Bounded MPMC queues with blocking/non-blocking operations
3. **Operators**: Processing units (Source, Map, Filter, Sink)
4. **Scheduler**: Distributes work to worker threads (Round-Robin, Work-Stealing)
5. **Runtime**: Coordinates graph execution and lifecycle

### Example Pipeline

```cpp
#include "klstream/klstream.hpp"

int main() {
    klstream::Runtime runtime;
    klstream::StreamGraphBuilder builder;
    
    // Source: generate integers 1..1000
    klstream::SequenceSource::Config src_cfg;
    src_cfg.count = 1000;
    builder.add_source(std::make_unique<klstream::SequenceSource>("src", src_cfg));
    
    // Map: square each number
    builder.add_operator(klstream::make_int_map("square", 
        [](int64_t x) { return x * x; }));
    
    // Filter: keep even numbers
    builder.add_operator(klstream::make_filter("even", 
        klstream::filters::even()));
    
    // Sink: aggregate results
    auto sink = std::make_unique<klstream::AggregatingSink>("agg");
    auto* sink_ptr = sink.get();
    builder.add_sink(std::move(sink));
    
    // Connect operators
    builder.connect("src", "square")
           .connect("square", "even")
           .connect("even", "agg");
    
    // Run pipeline
    runtime.init(std::move(builder));
    runtime.start();
    // ... wait for completion
    runtime.stop();
    
    std::cout << "Sum: " << sink_ptr->sum() << std::endl;
    return 0;
}
```

## Configuration

### Runtime Configuration

```cpp
klstream::RuntimeConfig config;
config.num_workers = 4;  // Worker threads (0 = auto-detect)
config.scheduling_policy = klstream::SchedulingPolicy::RoundRobin;
config.enable_metrics = true;
```

### Build Options

| Option | Default | Description |
|--------|---------|-------------|
| `KLSTREAM_BUILD_TESTS` | ON | Build unit tests |
| `KLSTREAM_BUILD_BENCHMARKS` | ON | Build benchmarks |
| `KLSTREAM_BUILD_EXAMPLES` | ON | Build examples |
| `KLSTREAM_ENABLE_SANITIZERS` | OFF | Enable ASan/UBSan |
| `KLSTREAM_ENABLE_LTO` | OFF | Enable Link Time Optimization |

## Performance

Run benchmarks to measure:

- **Throughput**: Events processed per second
- **Latency**: End-to-end processing time
- **Queue efficiency**: Push/pop operations

```bash
./scripts/dev.sh bench
```

## Development

### Code Formatting

```bash
./scripts/dev.sh format
```

### Static Analysis

```bash
./scripts/dev.sh lint
```

### Clean Build

```bash
./scripts/dev.sh clean
./scripts/dev.sh build
```

## License

MIT License - See LICENSE file for details.

## References

- Based on concepts from Apache Flink, StreamIt, and SEDA
- Implements bounded MPMC queues with backpressure
- Uses cooperative scheduling similar to OpenMP runtime

```

# File: KLStream_Research.md

```markdown
# KLStream-AdaptiveWindow

## Pressure-Adaptive Window Sizing for Streaming Financial Anomaly Detection

### Complete Implementation & Research Guide

> Working paper title: **"Pressure-Adaptive Windowing: Using Internal Pipeline
> Backpressure as a Control Signal for Streaming Anomaly Detection"**
>
> Target venue: IT4D 2026 (deadline Aug 15, 2026, 5-day internal buffer → submit Aug 10)
>
> This document assumes **KLStream is already built and working** — the C++17
> runtime with `IOperator`/`OpStatus`, `SPSCQueue`/`MPMCQueue`, the `Runtime`/
> `WorkerThread` scheduler, the standard operator library (`Source`, `Map`,
> `Filter`, `Aggregate`, `TumblingCountWindow`, `TumblingTimeWindow`, `Sink`),
> and — critically — `backpressure.hpp`'s `EMAOccupancyTracker<Queue>` and
> `TokenBucketRateLimiter`, exactly as specified in the prior **KLStream
> Complete Implementation Guide**. Every class name, file path, and header
> referenced below matches that guide so the two documents compose without
> translation.
>
> This document is self-sufficient: an agent (human or AI) with no other
> context should be able to implement the entire research extension — code,
> data pipeline, experiments, evaluation, and paper — from this file alone.

---

## Table of Contents

1. [Relationship to KLStream and to the Prior Research Dossier](#1-relationship-to-klstream-and-to-the-prior-research-dossier)
2. [Design Decision Log — Reconciling ONNX vs. Native C++](#2-design-decision-log--reconciling-onnx-vs-native-c)
3. [The One-Sentence Pitch](#3-the-one-sentence-pitch)
4. [Prior Art Survey (Consolidated + New Findings)](#4-prior-art-survey-consolidated--new-findings)
5. [The Precise Gap and Research Question](#5-the-precise-gap-and-research-question)
6. [Why This Is Hard Enough to Be a Paper](#6-why-this-is-hard-enough-to-be-a-paper)
7. [System Architecture — The Resolved Design](#7-system-architecture--the-resolved-design)
8. [Data Sourcing — LOBSTER and yfinance, In Full Detail](#8-data-sourcing--lobster-and-yfinance-in-full-detail)
9. [Synthetic Anomaly Injection Methodology](#9-synthetic-anomaly-injection-methodology)
10. [Feature Engineering](#10-feature-engineering)
11. [Python Offline Preprocessing Pipeline (Complete Script)](#11-python-offline-preprocessing-pipeline-complete-script)
12. [Native C++ Isolation Forest — Complete Implementation](#12-native-c-isolation-forest--complete-implementation)
13. [New KLStream Types — FeatureVector and WindowBatch](#13-new-klstream-types--featurevector-and-windowbatch)
14. [AdaptiveWindowOp — The Core Contribution](#14-adaptivewindowop--the-core-contribution)
15. [DataDrivenWindowOp — The Literature-Style Baseline](#15-datadrivenwindowop--the-literature-style-baseline)
16. [FixedWindowOp — Reusing Existing KLStream Code](#16-fixedwindowop--reusing-existing-klstream-code)
17. [InferenceOp — Wrapping the Isolation Forest](#17-inferenceop--wrapping-the-isolation-forest)
18. [TickSource — Replaying Financial Data](#18-ticksource--replaying-financial-data)
19. [Sink and Result Logging](#19-sink-and-result-logging)
20. [Repository Structure](#20-repository-structure)
21. [CMake Integration](#21-cmake-integration)
22. [Full Pipeline Wiring (main.cpp for Each Architecture)](#22-full-pipeline-wiring-maincpp-for-each-architecture)
23. [Evaluation Methodology — Metrics in Full](#23-evaluation-methodology--metrics-in-full)
24. [The Point-Adjustment Trap and How This Project Avoids It](#24-the-point-adjustment-trap-and-how-this-project-avoids-it)
25. [Experiment Design — Five Experiments in Full](#25-experiment-design--five-experiments-in-full)
26. [Isolation Forest Validation Plan](#26-isolation-forest-validation-plan)
27. [Statistical Rigor — Runs, Warmup, Confidence Intervals](#27-statistical-rigor--runs-warmup-confidence-intervals)
28. [Risks and Honest Difficulty Assessment](#28-risks-and-honest-difficulty-assessment)
29. [8-Week Build Timeline](#29-8-week-build-timeline)
30. [Paper Outline and Writing Guidance](#30-paper-outline-and-writing-guidance)
31. [Full Reference List](#31-full-reference-list)
32. [Glossary of New Terms](#32-glossary-of-new-terms)
33. [Appendix — Task Breakdown for a Coding Agent](#33-appendix--task-breakdown-for-a-coding-agent)

---

## 1. Relationship to KLStream and to the Prior Research Dossier

Three documents now exist for this project. This is the fourth and the one
that should drive implementation:

| Document | What it contains | Status |
|---|---|---|
| **KLStream Complete Implementation Guide** | Core runtime: queues, operators, scheduler, metrics, backpressure infrastructure | **Built and working** (your own report) |
| **KLStream Research Brief** | Prior-art landscape for the *runtime itself* (FastFlow, BriskStream, WindFlow, etc.) and four candidate research directions | Superseded for direction — you picked Option 1 |
| **Option 1 Research Dossier** (pasted into this conversation) | Deep prior-art survey, system design sketch, and experiment plan specifically for pressure-adaptive windowing | **This document absorbs, corrects, and completes it** |
| **This document (KLStream-AdaptiveWindow)** | Single, code-complete, internally consistent implementation guide | **Use this one** |

The dossier you pasted is excellent research and roughly 90% of its content is
preserved here unchanged. This document exists because three things needed
resolving before a coding agent could act on it without ambiguity:

1. **The model-loading mechanism was inconsistent** between your one-line
   Option 1 description ("Isolation Forest via ONNX Runtime") and the
   dossier's own Section 6.1, which documents a real, currently-open
   `skl2onnx` conversion bug and recommends avoiding ONNX entirely. Section 2
   below resolves this explicitly.
2. **The dossier's `AdaptiveWindowOp` sketch did not specify how "window
   size" mechanically connects to "inference cost" and "queue occupancy"** —
   it gestured at the relationship without pinning down what data structure
   crosses the queue boundary, which is the single most load-bearing design
   decision in the whole system (Section 7 resolves this with a concrete,
   bounded-memory data structure and a precise causal chain from window size
   to backpressure).
3. **The dossier did not yet reflect the 2022 AAAI finding on point-adjustment
   evaluation bias**, which is directly relevant because your headline metric
   is F1 on a labeled, segment-style anomaly dataset — exactly the setting
   where naive point-adjustment is known to silently inflate scores (Section
   24). Skipping this would be a real, catchable methodological weakness.

Everything else from the dossier — the prior-art survey, the AIMD-inspired
shrink-fast/grow-slow asymmetry, the novel metrics (PATR, WOR, LBA), the
8-week timeline shape, and the reference list — is retained and extended
below.

---

## 2. Design Decision Log — Reconciling ONNX vs. Native C++

**Decision: native C++ Isolation Forest. No ONNX Runtime dependency anywhere
in this project.**

Reasoning, for the record (cite this directly in your paper's implementation
section as a stated design choice, not an oversight):

- `skl2onnx`'s conversion of `sklearn.ensemble.IsolationForest` has a
  documented, currently open failure mode: the converter raises an
  unspecified-op-version error when no calibration data is supplied to the
  converter, and a separate converter error when the model's effective
  `max_features` differs from the total input feature count — both tracked
  as live issues on the `onnx/sklearn-onnx` GitHub repository as of January
  2024, with no resolution as of this writing.
- Even where conversion succeeds, ONNX Runtime introduces a second runtime
  dependency, a second build-system integration (CMake `find_package` or
  `FetchContent` for `onnxruntime`, platform-specific shared-library
  packaging on macOS), and a second execution-provider configuration surface
  — all surface area that contributes nothing to the actual research
  question, which is about **window sizing**, not about **model deployment
  format**.
- The Isolation Forest algorithm itself (Liu, Ting & Zhou, 2008) is short
  enough to implement correctly in under 300 lines of C++: random
  axis-aligned splits, no gradient computation, no weight matrices — there is
  no meaningful "hard part" that ONNX would be saving you from.
- Writing it natively keeps the **entire system in one statically-linked C++
  binary**, consistent with KLStream's existing zero-external-dependency,
  header-only design philosophy (Section 2.1 of the Implementation Guide).
- It also removes an entire confound from Experiment 5 (controller overhead):
  if you used ONNX Runtime, any measured overhead difference between
  architectures could be partly attributed to ONNX Runtime's own threading
  and memory-arena behavior rather than to your window-size mechanism. A
  native, single-threaded, allocation-free inference path removes that
  confound entirely.

If a future reviewer specifically asks "why not use a standard ML runtime,"
the answer is in Section 6.1 of the dossier (preserved as Section 28 here)
and is a legitimate, citable engineering decision, not an oversight.

---

## 3. The One-Sentence Pitch

> When a streaming pipeline's internal queue starts backing up — meaning the
> downstream anomaly-detection model cannot keep pace with the data rate —
> shrink the detection window so each batch of scoring work costs less and
> the pipeline drains faster; when the queue is calm, grow the window back to
> capture more context and improve detection quality. The control signal is
> KLStream's own `EMAOccupancyTracker`, already built for source-side
> backpressure, repurposed here — unmodified — to drive a completely
> different actuator: window size instead of emission rate.

---

## 4. Prior Art Survey (Consolidated + New Findings)

This section keeps the dossier's five-literature structure and adds findings
from additional research conducted specifically for this implementation
guide (marked **[NEW]**).

### 4.1 Window Size Selection — Driven by Data Statistics, Never by System Pressure

Unchanged from the dossier. Key citations: Ermshaus, Schäfer & Leser's 2023
window-size-selection survey/benchmark; Adaptive Sliding Window Normalization
(ASWN, *Information Systems*, 2025); AFMF (2024). All of these derive window
size from properties of the **data** (periodicity, AIC, detected drift), never
from the **system's own processing backlog**. This is the literature your
related-work section opens with, specifically to draw the contrast in its
first paragraph.

### 4.2 Backpressure-Driven Adaptation in Stream Processing — Adapts Rate or Parallelism, Never Window Size

Unchanged. ASWB (*ETRI Journal*, 2026) remains the closest systems-level
near-miss: backpressure-driven **sampling rate** control plus a
**variable-size window used only for hash-collision reduction**, not for
inference-cost control. Flink's adaptive scheduler, Hazelcast Jet's bounded
queues with TCP-style receive-window throttling, and the Spark Streaming
data-driven latency controller (*Sensors*, 2022) all throttle **admission**,
never a downstream operator's **semantic window size**.

### 4.3 Accuracy-Latency Trade-off in ML Serving — Adjacent Concept, Different Lever

Unchanged. Tolerance Tiers (arXiv 1906.11307, 2019) validates "trade
inference cost against latency budget" as a recognized systems contribution,
but its lever is model selection (swap to a cheaper model), not window size
for a fixed model.

### 4.4 Active Queue Management — Conceptual Ancestor

Unchanged. RED and CoDel use smoothed queue-occupancy estimates to act
*before* saturation. This is the direct intellectual ancestor of
`EMAOccupancyTracker`, and the lineage is worth one explicit sentence in your
methodology section.

### 4.5 Distributed Elastic Scaling — Different Granularity, Scoping Citation Only

Unchanged. Demeter, Justin, AutoFlow all operate at the
add/remove-operator-instance granularity in distributed deployments. One
sentence of scoping, not deep engagement.

### 4.6 [NEW] Time-Series Anomaly Detection Evaluation — The Point-Adjustment Trap

Kim, Choi, Choi, Lee & Yoon, **"Towards a Rigorous Evaluation of Time-series
Anomaly Detection"** (AAAI 2022), is directly relevant and was not in the
original dossier. The paper shows that the standard "point adjustment" (PA)
protocol — where detecting *any single point* inside a labeled anomaly
segment counts the *entire segment* as correctly detected — can make even a
**random anomaly score** achieve state-of-the-art-looking F1. The paper
proposes **PA%K**, a stricter protocol requiring at least K% of an anomaly
segment's points to be individually flagged before the segment counts as
detected. This is now load-bearing for your evaluation methodology (Section
24) and is a citation a TAD-literate reviewer will specifically look for —
its absence would be a visible gap, its presence is a strong positive signal
that you know the field.

### 4.7 [NEW] Financial Anomaly Feature Literature

Two literatures inform the concrete feature set used in Section 10:

- **Order-flow toxicity / VPIN** (Easley, López de Prado & O'Hara, "The
  Microstructure of the 'Flash Crash'," 2011): order-flow imbalance and
  trade-intensity-based toxicity estimation are shown to correlate with the
  pre-crash buildup on May 6, 2010, and remain the standard reference feature
  for flash-crash precursor detection in the market-microstructure
  literature. A 2025 study of the October 10, 2025 crypto flash crash
  similarly finds order-book imbalance to be a potent predictor of imminent
  price moves, with the caveat that widespread adoption of imbalance-based
  signals can itself create a reflexive feedback loop that exacerbates
  crashes — a finding worth one sentence in your discussion section, since it
  bears on real-world deployment implications of exactly this kind of
  detector.
- **Wash trading detection** requires, in essentially every paper surveyed
  (the NFT wash-trading study, the meme-coin manipulation study, the
  Markov-modulated Hawkes-process study of HFT wash trading), either
  **counterparty/wallet identity** or **account-level trade attribution** —
  none of which is present in LOBSTER, NASDAQ ITCH, or yfinance data, all of
  which are anonymized at the order level with no persistent trader identity.
  **This is an honest, load-bearing limitation you must state explicitly**
  (Section 9.3): this project does not detect true wash trading. It detects
  a stylized, citable **proxy pattern** — anomalous volume with anomalously
  *flat* price — directly modeled on the heuristic used in the meme-coin
  manipulation study (>500% volume increase paired with <5% price change
  flagged as suspicious). State this as a scoping decision, not a discovery.

### 4.8 The Gap Table (Unchanged from Dossier, Reproduced for Completeness)

| Dimension | Window-size literature (4.1) | Backpressure systems (4.2) | Tolerance Tiers (4.3) | **Your gap** |
|---|---|---|---|---|
| What drives adaptation | Data statistics | Queue/scheduling-delay | Latency SLA | **Own output-queue occupancy (EMA)** |
| What gets adapted | Window size | Admission rate / parallelism | Model choice | **Window size** |
| Target metric | Accuracy | Throughput / fairness | Latency-accuracy Pareto | **Latency AND accuracy jointly, under load** |
| Granularity | Single operator | Whole pipeline / cluster | Whole service | **Single operator, single node** |
| Models swapped? | No | No | Yes | **No — one pretrained forest, variable batch size only** |

---

## 5. The Precise Gap and Research Question

> **Can a streaming anomaly-detection operator use its own output queue's
> occupancy (EMA-smoothed, via KLStream's existing `EMAOccupancyTracker`) as
> a feedback signal to adaptively size the batch of feature vectors it sends
> for Isolation Forest scoring — shrinking under load to bound detection
> latency, expanding when idle to improve detection quality — and does this
> outperform both a fixed-size window and a volatility-driven adaptive
> window on the combined latency/accuracy trade-off, under bursty synthetic
> financial-anomaly workloads, evaluated with a point-adjustment-aware
> protocol that resists the F1-inflation failure mode documented by Kim et
> al. (AAAI 2022)?**

No paper in the seven surveyed literatures asks this question. The closest
near-miss (ASWB, Section 4.2) applies the closest mechanism (backpressure
signal) to a different actuator (sampling rate, not window size) for a
different purpose (frequency-estimation collision reduction, not ML inference
cost).

---

## 6. Why This Is Hard Enough to Be a Paper

Unchanged from the dossier's Section 4, all four points remain valid and are
restated briefly:

1. **Stability is a real problem you must solve and demonstrate**, not
   assume. Aggressive reaction to occupancy causes window-size oscillation.
   The deadband design in Section 14 and the Window Oscillation Rate (WOR)
   metric in Section 23 directly address this.
2. **Window size affects accuracy non-monotonically.** Too small → noisy
   per-tick scores feeding into a per-window max that triggers on noise; too
   large → genuine short-duration anomalies get diluted by being scored
   alongside many calm points before the window fires. This must be measured
   and reported honestly, including cases where it does not pay off.
3. **The control signal is architecturally free.** `EMAOccupancyTracker` is
   already computed by KLStream's existing infrastructure for an unrelated
   purpose (source-side admission control). Reusing it here costs one
   `occupancy()` read per tick — no separate statistics pass, no AIC
   computation, no DBSCAN clustering, unlike the data-driven baseline you are
   comparing against. Experiment 5 (Section 25) measures and reports this
   overhead difference directly.
4. **Generalization claims require a sensitivity sweep**, not one tuned
   operating point. Experiment 4 (Section 25) is not optional.

---

## 7. System Architecture — The Resolved Design

This is the most important section in the document. It resolves the one real
ambiguity in the dossier's sketch: **what data structure crosses the queue
boundary, and how, mechanically, does a larger window cause more
backpressure?**

### 7.1 The Pipeline

```text
TickSource ──▶ FeatureExtractOp ──▶ [WindowOp variant] ──▶ InferenceOp ──▶ Sink
  (replays         (MapOperator,         ▲                  (scores the
   LOBSTER-          per-tick             │ reads occupancy   ENTIRE batch,
   derived CSV,       features,           │ of ITS OWN         one forest
   bursty rate-       O(1) per tick)      │ output queue       query per
   controlled)                            │                    point)
                                          AdaptiveWindowOp
                                          (this operator only —
                                           the other two WindowOp
                                           variants do not read
                                           any occupancy signal)
```

Three interchangeable window-stage implementations, swapped via a
command-line flag, all producing the same `Event<WindowBatch>` type so
`InferenceOp` and everything downstream is **completely unaware** which
window strategy is active:

| Variant | File | Sizing logic |
|---|---|---|
| `FixedWindowOp` | reuses `klstream/operators/window.hpp` unmodified | Constant `window_size_` |
| `DataDrivenWindowOp` | new, `klstream/window/data_driven_window_op.hpp` | EMA of rolling realized volatility |
| `AdaptiveWindowOp` | new, `klstream/window/adaptive_window_op.hpp` | EMA of **its own output queue's occupancy** |

### 7.2 The Causal Chain That Makes This Work (Read This Before Writing Any Code)

This is the mechanism that makes "window size" and "inference cost" and
"backpressure" actually connect, end to end, with no hand-waving:

1. `InferenceOp::tick()` pops **one** `Event<WindowBatch>` per call. A
   `WindowBatch` holds up to `MAX_WINDOW_SIZE` `FeatureVector`s (Section 13).
2. Inside that single `tick()` call, `InferenceOp` scores **every point in
   the batch** against the pretrained Isolation Forest, in a tight loop —
   `W` calls to `IsolationForest::anomaly_score()`, each `O(log ψ)` where
   `ψ` is the forest's sub-sample size (256 by default). Total cost per
   `tick()` call: **`O(W log ψ)`**.
3. Because KLStream's cooperative scheduler (`WorkerThread::run()`, Section
   7.9 of the Implementation Guide) calls `tick()` in a tight loop with no
   preemption, **a larger `W` makes this one `tick()` call take measurably
   longer in wall-clock time**. This is the entire mechanism — there is no
   separate "cost model," the cost is the literal loop.
4. While `InferenceOp` is busy inside one long `tick()`, it is not popping
   its input queue. If the window operator upstream keeps producing
   `WindowBatch`es at its usual rate, **`InferenceOp`'s input queue — which
   is the window operator's OUTPUT queue — starts filling up**.
5. `AdaptiveWindowOp` owns an `EMAOccupancyTracker` wrapping **exactly this
   queue** (its own output, `InferenceOp`'s input). When `InferenceOp` is
   running slow because `W` was large, this queue's occupancy rises, the EMA
   tracks it, `AdaptiveWindowOp::tick()` reads `tracker_.ema()` and lowers
   the target window size for the **next** window it starts buffering.
6. The next window is smaller → `InferenceOp`'s next `tick()` call over that
   batch is shorter → it drains its input faster → occupancy falls → the EMA
   falls → `AdaptiveWindowOp` grows the window back. This is the full
   feedback loop, and it is literally the same `EMAOccupancyTracker` class
   already validated and running in your `SourceOperator`'s adaptive
   backpressure path — applied here to a different operator and a different
   actuator (window size instead of token-bucket rate).

This causal chain is what you describe, with a diagram, in your paper's
System Design section. It is mechanistic and falsifiable — Experiment 1
(Section 25) exists specifically to demonstrate it happens as described.

### 7.3 Why `WindowBatch` Must Be a Fixed-Size Array, Not a `std::vector`

KLStream's `SPSCQueue<T>` has a hard `static_assert(std::is_trivially_copyable_v<T>)`
(Section 7.3 of the Implementation Guide). A `std::vector<FeatureVector>` is
**not** trivially copyable (it owns a heap pointer), so it cannot be a queue
payload as-is.

The fix is also the *correct* fix architecturally, not just a workaround:
cap the maximum window size at a compile-time constant
(`MAX_WINDOW_SIZE = 256`, matching `AdaptiveWindowController::w_max_`'s
sensible upper bound) and store the batch as a fixed
`std::array<FeatureVector, MAX_WINDOW_SIZE>` plus a runtime `count`. This is
trivially copyable, lives entirely on the queue's pre-allocated ring buffer
(zero heap allocation per window, consistent with KLStream's whole
bounded-memory philosophy from Section 2.5 of the Implementation Guide), and
costs exactly `sizeof(FeatureVector) * MAX_WINDOW_SIZE + 8` bytes per queue
slot.

**Sizing consequence you must account for:** with `FeatureVector` at
~40 bytes (Section 13) and `MAX_WINDOW_SIZE = 256`, one `Event<WindowBatch>`
is roughly **10 KB**. A queue of the default capacity (4096) would be ~40 MB
— wasteful for a queue that only ever needs to hold a handful of in-flight
windows. **Use a small capacity (32–64) for the window-stage → `InferenceOp`
queue specifically.** This is a one-argument change at construction and is
called out explicitly in Section 22's wiring code.

### 7.4 Latency Measurement — Which Timestamp Travels Downstream

`InferenceOp` emits one `Event<DetectionResult>` per window. The
`timestamp_ns` on that event is **not** the window's first-tick timestamp —
it is the timestamp of whichever individual tick inside the window achieved
the maximum anomaly score (Section 17.2). This means `Event::latency_ns()`
at the sink directly measures **"how long after the single worst event in
this window occurred did the system finish flagging it"** — the
operationally meaningful latency number, and the one the Latency-Bounded
Accuracy metric (Section 23.4) is built on.

### 7.5 Pretraining, Not Online Training

The Isolation Forest is trained **once, offline, in Python**, on the "calm"
(non-injected-anomaly) portion of the preprocessed dataset, then re-trained
**natively in C++ at startup** using the identical algorithm and
hyperparameters so the deployed forest never depends on a serialized format
(Section 12). The **same fitted forest is reused across all three window
architectures and every experiment run** — window size never changes what
the forest *is*, only how many points get scored per inference call and how
those scores get aggregated. This is essential for a clean comparison: if
the model itself changed across conditions you would no longer be isolating
the effect of window size.

---

## 8. Data Sourcing — LOBSTER and yfinance, In Full Detail

### 8.1 LOBSTER — Primary Data Source

LOBSTER (Limit Order Book System — The Efficient Reconstructor, Humboldt
University of Berlin) reconstructs full limit order book state from NASDAQ's
historical TotalView-ITCH feed and has offered free academic sample files
since 2013. The free tier covers five tickers — **AAPL, AMZN, GOOG, INTC,
MSFT** — with a well-documented one-day sample (June 21, 2012) used
throughout the market-microstructure literature, which means your data
source is independently citable and reproducible by reviewers.

Download portal: `https://lobsterdata.com` (academic sample request form).

**Exact file format** (verified against the LOBSTER technical report and
multiple peer-reviewed papers using it):

For each requested ticker/day, LOBSTER provides **two row-aligned files**:

**Message file** (`*_message_*.csv`), dimension `N × 6`, one row per
order-book event:

| Column | Meaning |
|---|---|
| 1 | Timestamp — seconds after midnight, decimal precision from milliseconds to nanoseconds depending on sample period |
| 2 | Event type — see table below |
| 3 | Order ID — unique per resting limit order |
| 4 | Size — number of shares |
| 5 | Price — dollar price × 10000 (i.e., divide by 10000 to get dollars) |
| 6 | Direction — `1` = buy limit order, `-1` = sell limit order |

Event type codes (column 2):

| Code | Meaning |
|---|---|
| 1 | Submission of a new limit order |
| 2 | Cancellation (partial deletion of a limit order) |
| 3 | Deletion (total deletion of a limit order) |
| 4 | Execution of a visible limit order |
| 5 | Execution of a hidden limit order |
| 7 | Trading halt (and related indicators — drop these rows; they do not represent order book state changes) |

**Order book file** (`*_orderbook_*.csv`), dimension `N × (4 × NumLevels)`,
**row-aligned 1:1 with the message file** (row *i* of the order book file is
the book state *immediately after* row *i* of the message file is applied).
For `NumLevels = 1` (all you need — Section 10 only uses top-of-book), each
row is exactly 4 columns:

| Column | Meaning |
|---|---|
| 1 | Level-1 ask price (× 10000) |
| 2 | Level-1 ask size |
| 3 | Level-1 bid price (× 10000) |
| 4 | Level-1 bid size |

**This row-alignment is what makes the C++ side trivial**: you never need to
reconstruct the order book yourself — LOBSTER already did it. Feature
engineering (Section 10) is a function purely of corresponding rows from
these two files, computed once, offline, in Python (Section 11).

### 8.2 yfinance — Calm-Period Fallback Only, With Real Limitations Stated

`yfinance` (free Python package wrapping Yahoo Finance's public endpoints)
is **not** tick data and should not be described as such in your paper. Its
finest granularity is **1-minute OHLCV bars**, and Yahoo's backend only
serves 1-minute granularity for **the most recent 7 days** — anything older
than that is only available at coarser granularity (5m/15m for 60 days,
daily beyond that). There is no way to retrieve 1-minute (let alone tick)
data for an arbitrary historical date range from `yfinance` — this is a hard
platform limitation, not a library bug.

**Correct use of yfinance in this project**: as a low-frequency, low-stakes
filler for the "steady-state, low-information" segments of synthetic replay
construction (Section 9), or for a sanity-check secondary dataset at daily
granularity. It is **not** a substitute for LOBSTER's tick-level order-flow
data, and your data section should state this distinction explicitly rather
than letting a reviewer infer it. If you want a continuous multi-day replay
at tick-level granularity, LOBSTER's five-ticker sample is genuinely your
only free academic option; do not attempt to stitch together yfinance
1-minute bars and present them as tick data.

```python
# Minimal yfinance fallback fetch — only for calm-period filler segments
import yfinance as yf
df = yf.download("AAPL", period="7d", interval="1m")
# df has Open/High/Low/Close/Volume per minute — aggregate-bar granularity,
# NOT individual order events. Use only where Section 9 calls for
# low-information filler, never as a substitute for LOBSTER's tick stream.
```

### 8.3 Practical Acquisition Checklist

- [ ] Week 1, Day 1: Submit the LOBSTER academic sample request and confirm
      AAPL or MSFT message+orderbook files for June 21, 2012 download
      successfully.
- [ ] Confirm row counts match between the message and orderbook files for
      the same ticker/day (they must be identical — if not, the download is
      corrupted).
- [ ] Spot-check 10 rows by hand: event type 4 (execution) rows should
      always correspond to a size decrease on the corresponding side of the
      book between consecutive orderbook rows.
- [ ] If LOBSTER access is delayed, fall back immediately to a synthetic
      random-walk-with-injected-anomalies generator (Section 9.4) so Phase 1
      of the timeline (Section 29) is never blocked on a third-party form.

---

## 9. Synthetic Anomaly Injection Methodology

Real LOBSTER sample days are calm trading days with no documented flash
crash or known manipulation event — you cannot get ground-truth anomaly
labels "for free" from this data. **All anomaly labels in this project are
synthetically injected, and this must be stated plainly in your paper's
data section**, not discovered by a reviewer. This is standard practice in
the TAD literature (most public TAD benchmarks supplement real signal with
injected anomalies precisely because real, labeled anomalies are rare) but
it must be described, not implied.

### 9.1 Flash-Crash-Precursor Injection (Label = 1)

Modeled directly on the VPIN/order-flow-imbalance literature's description
of the actual May 6, 2010 flash crash buildup (Easley, López de Prado &
O'Hara, 2011) and the October 2025 crypto flash crash case study (both cited
in Section 4.7): real flash-crash precursors are characterized by **rising
order-flow imbalance, widening bid-ask spread, and a sequence of
same-direction executions that erode top-of-book liquidity** before the
price gap occurs.

At each injection point (chosen at random, non-overlapping, away from file
boundaries), synthetically rewrite **N consecutive rows** (`N` drawn
uniformly from, e.g., 20–80 events) as follows:

```python
def inject_flash_crash_precursor(rows, start_idx, n_events, rng):
    """
    rows: list of dicts with keys ask_px, ask_sz, bid_px, bid_sz (level-1, in cents)
    Mutates rows[start_idx : start_idx+n_events] in place.
    Models a one-sided liquidity-erosion buildup: bid size decays,
    bid price steps down, spread widens, consistent with pre-flash-crash
    order-flow-imbalance buildup described in Easley et al. (2011).
    """
    decay = rng.uniform(0.85, 0.95)   # per-event bid-size decay factor
    step_prob = 0.15                  # probability bid price steps down 1 tick
    for i in range(n_events):
        r = rows[start_idx + i]
        r['bid_sz'] = max(1, int(r['bid_sz'] * decay))
        if rng.random() < step_prob:
            r['bid_px'] -= 1            # one tick (price units of $0.01)
        r['ask_sz'] = int(r['ask_sz'] * rng.uniform(1.0, 1.05))  # ask side calm/growing
        r['label'] = 1
    return rows
```

### 9.2 Wash-Trading-Style Proxy Injection (Label = 2) — Explicit Caveat Required

As established in Section 4.7, **true wash trading cannot be labeled from
LOBSTER, ITCH, or yfinance data** because none of these sources carry
counterparty identity. This project instead injects the **observable proxy
pattern** used in the meme-coin manipulation literature: a sharp,
short-lived volume spike with anomalously *flat* price — the opposite
signature from a flash-crash precursor, and a genuinely distinct pattern for
the Isolation Forest to separate.

```python
def inject_wash_trade_proxy(rows, start_idx, n_events, rng):
    """
    Models the literature's volume-spike / flat-price wash-trading proxy
    heuristic (cf. meme-coin manipulation study, Section 4.7): volume
    increases sharply while price barely moves.
    EXPLICIT LIMITATION (state in paper): this is a stylized proxy pattern,
    not verified wash trading, because public market data lacks
    counterparty/account identity.
    """
    base_px = rows[start_idx]['bid_px']
    for i in range(n_events):
        r = rows[start_idx + i]
        r['bid_sz'] = int(r['bid_sz'] * rng.uniform(3.0, 6.0))   # volume spike
        r['ask_sz'] = int(r['ask_sz'] * rng.uniform(3.0, 6.0))
        r['bid_px'] = base_px + rng.choice([-1, 0, 0, 0, 1])      # price ~flat
        r['ask_px'] = r['bid_px'] + (rows[start_idx]['ask_px'] - rows[start_idx]['bid_px'])
        r['label'] = 2
    return rows
```

### 9.3 Injection Density and Placement

- Target **2–4% of total events** labeled anomalous, split roughly evenly
  between the two pattern types — high enough to get statistically stable F1
  estimates from a single-day sample, low enough to remain a genuine
  minority-class detection problem (matching the realistic "few and
  different" assumption Isolation Forest is built on).
- Enforce a minimum gap of 500 normal events between injected segments so
  windows of up to `MAX_WINDOW_SIZE = 256` never straddle two different
  injected segments.
- Record, per injected segment: `start_seq`, `end_seq`, `label` (1 or 2) in a
  separate `injection_log.csv` — this is your ground truth for every
  evaluation metric in Section 23.

### 9.4 Fallback: Pure Synthetic Generator (If LOBSTER Access Is Delayed)

A minimal synthetic order-flow generator (geometric Brownian motion mid-price
plus Poisson order arrivals) is sufficient to unblock Phase 1 of the
timeline while the LOBSTER request is pending. This is precedented in this
project's own prior research output (the BankSentinel benchmarking plan used
an analogous synthetic-regime-switch fallback when real data access was
delayed). Do not let data acquisition block Week 1's actual engineering
work — implement against the synthetic generator first, swap in real
LOBSTER-derived data the moment it arrives (the downstream CSV schema is
identical either way, by design — see Section 11).

---

## 10. Feature Engineering

Five features, computed **per event**, each `O(1)` amortized (a rolling EMA,
not a full recomputation), forming the fixed-dimensionality
`FeatureVector` (`D = 5`) that both the Isolation Forest and every window
operator operate on:

| # | Feature | Formula | Why it matters for these anomaly types |
|---|---|---|---|
| 1 | `log_return` | `ln(mid_t / mid_{t-1})`, where `mid_t = (ask_px + bid_px) / 2` | Direct price-move signal; flash-crash precursors show a building sequence of same-sign small returns before the gap |
| 2 | `rolling_vol` | EMA of squared `log_return`, `vol_t = β·r_t² + (1-β)·vol_{t-1}`, `β = 0.05` | Captures the volatility buildup that VPIN-style toxicity correlates with (Easley et al. 2011) |
| 3 | `order_imbalance` | `(bid_sz − ask_sz) / (bid_sz + ask_sz)` ∈ [−1, 1] | The single most-cited flash-crash precursor feature in the microstructure literature (Section 4.7) |
| 4 | `spread_bps` | `10000 · (ask_px − bid_px) / mid_t` | Widening spread is a documented precursor signal; also the feature most informative for the wash-trade proxy (spread stays roughly flat while size spikes) |
| 5 | `volume` | `bid_sz + ask_sz` (level-1 total depth) — log-scaled: `ln(1 + volume)` | The wash-trade proxy's primary signal; log-scaling prevents the IF's random splits from being dominated by raw magnitude |

All five are simple closed-form functions of the current and immediately
preceding row — **no lookback window is required to compute them**, which is
intentional and important: the *per-tick* feature computation is
window-size-independent (`O(1)` always), so any latency or accuracy effect
you measure downstream is attributable purely to the **window operator's**
behavior, not to feature computation cost scaling with window size. This is
a clean separation of concerns that strengthens the internal validity of
every experiment in Section 25.

```cpp
// Definition matches Section 13's FeatureVector struct exactly.
// This pure function is implemented in Python for offline preprocessing
// (Section 11) and does NOT need to be reimplemented in C++ — the C++
// TickSource reads pre-computed feature columns directly from CSV.
```

---

## 11. Python Offline Preprocessing Pipeline (Complete Script)

This script runs **once per ticker/day**, offline, before any C++ code runs.
It produces a single flat CSV that the C++ `TickSource` (Section 18) streams
directly — no LOB reconstruction logic needs to exist in C++ at all, since
LOBSTER already reconstructs the book and this script already computes
features and injects labels.

**Output schema** (`replay_<ticker>_<date>.csv`):

```
seq,timestamp_ns,mid_price,log_return,rolling_vol,order_imbalance,spread_bps,volume,label,is_burst_period
```

```python
#!/usr/bin/env python3
"""
preprocess_lobster.py — Convert raw LOBSTER message+orderbook files into
a single replay-ready CSV with engineered features and injected anomaly
labels. Run once per ticker/day. Output feeds klstream's TickSource directly.

Usage:
    python preprocess_lobster.py \
        --message AAPL_2012-06-21_34200000_57600000_message_1.csv \
        --orderbook AAPL_2012-06-21_34200000_57600000_orderbook_1.csv \
        --out replay_AAPL_20120621.csv \
        --seed 42
"""
import argparse
import math
import random
import pandas as pd
import numpy as np

MSG_COLS = ["time_sec", "event_type", "order_id", "size", "price", "direction"]
OB_COLS  = ["ask_px", "ask_sz", "bid_px", "bid_sz"]   # NumLevels=1

# Event type 7 = trading halt; these rows carry no real book update.
DROP_EVENT_TYPES = {7}


def load(message_path, orderbook_path):
    msg = pd.read_csv(message_path, header=None, names=MSG_COLS)
    ob  = pd.read_csv(orderbook_path, header=None, names=OB_COLS)
    assert len(msg) == len(ob), "message/orderbook row count mismatch — corrupted download"
    df = pd.concat([msg, ob], axis=1)
    df = df[~df["event_type"].isin(DROP_EVENT_TYPES)].reset_index(drop=True)
    # LOBSTER prices are dollars * 10000 -> convert to cents (integers) for
    # the synthetic injectors in Section 9, then back to dollars for output.
    for c in ("price", "ask_px", "bid_px"):
        df[c] = df[c] / 100.0   # dollars * 100 == cents
    return df


def inject_flash_crash_precursor(df, start_idx, n_events, rng):
    decay = rng.uniform(0.85, 0.95)
    step_prob = 0.15
    for i in range(n_events):
        idx = start_idx + i
        df.at[idx, "bid_sz"] = max(1, int(df.at[idx, "bid_sz"] * decay))
        if rng.random() < step_prob:
            df.at[idx, "bid_px"] -= 1
        df.at[idx, "ask_sz"] = int(df.at[idx, "ask_sz"] * rng.uniform(1.0, 1.05))
        df.at[idx, "label"] = 1


def inject_wash_trade_proxy(df, start_idx, n_events, rng):
    base_px = df.at[start_idx, "bid_px"]
    base_spread = df.at[start_idx, "ask_px"] - df.at[start_idx, "bid_px"]
    for i in range(n_events):
        idx = start_idx + i
        df.at[idx, "bid_sz"] = int(df.at[idx, "bid_sz"] * rng.uniform(3.0, 6.0))
        df.at[idx, "ask_sz"] = int(df.at[idx, "ask_sz"] * rng.uniform(3.0, 6.0))
        df.at[idx, "bid_px"] = base_px + rng.choice([-1, 0, 0, 0, 1])
        df.at[idx, "ask_px"] = df.at[idx, "bid_px"] + base_spread
        df.at[idx, "label"] = 2


def inject_anomalies(df, rng, target_fraction=0.03, min_gap=500, max_window=256):
    n = len(df)
    df["label"] = 0
    n_target = int(n * target_fraction)
    placed = 0
    attempts = 0
    occupied = np.zeros(n, dtype=bool)
    while placed < n_target and attempts < n_target * 20:
        attempts += 1
        start = rng.randrange(min_gap, n - max_window - min_gap)
        n_events = rng.randint(20, 80)
        window = slice(start - min_gap, start + n_events + min_gap)
        if occupied[window].any():
            continue
        occupied[start:start + n_events] = True
        if rng.random() < 0.5:
            inject_flash_crash_precursor(df, start, n_events, rng)
        else:
            inject_wash_trade_proxy(df, start, n_events, rng)
        placed += n_events
    return df


def mark_burst_periods(df, rng, n_bursts=4, burst_len_events=2000):
    """Marks dense replay-rate segments for the bursty-source experiments
    (Section 25, reusing the original KLStream bursty-source pattern)."""
    n = len(df)
    df["is_burst_period"] = 0
    for _ in range(n_bursts):
        start = rng.randrange(0, max(1, n - burst_len_events))
        df.loc[start:start + burst_len_events, "is_burst_period"] = 1
    return df


def compute_features(df):
    mid = (df["ask_px"] + df["bid_px"]) / 2.0
    log_return = np.log(mid).diff().fillna(0.0)

    beta = 0.05
    rolling_vol = np.zeros(len(df))
    v = 0.0
    r2 = (log_return ** 2).values
    for i in range(len(df)):
        v = beta * r2[i] + (1 - beta) * v
        rolling_vol[i] = v

    order_imbalance = (df["bid_sz"] - df["ask_sz"]) / (df["bid_sz"] + df["ask_sz"]).clip(lower=1)
    spread_bps = 10000.0 * (df["ask_px"] - df["bid_px"]) / mid
    volume = np.log1p(df["bid_sz"] + df["ask_sz"])

    out = pd.DataFrame({
        "seq": np.arange(len(df)),
        "timestamp_ns": (df["time_sec"] * 1e9).astype(np.int64),
        "mid_price": mid,
        "log_return": log_return,
        "rolling_vol": rolling_vol,
        "order_imbalance": order_imbalance,
        "spread_bps": spread_bps,
        "volume": volume,
        "label": df["label"],
        "is_burst_period": df["is_burst_period"],
    })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--message", required=True)
    ap.add_argument("--orderbook", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    df = load(args.message, args.orderbook)
    df = inject_anomalies(df, rng)
    df = mark_burst_periods(df, rng)
    out = compute_features(df)
    out.to_csv(args.out, index=False)

    n_anom = (out["label"] != 0).sum()
    print(f"Wrote {len(out)} events to {args.out}")
    print(f"  Flash-crash-precursor events: {(out['label']==1).sum()}")
    print(f"  Wash-trade-proxy events:      {(out['label']==2).sum()}")
    print(f"  Total anomalous fraction:     {n_anom/len(out):.3%}")


if __name__ == "__main__":
    main()
```

This script also doubles as the **calibration-set generator** for training
the Isolation Forest (Section 26): filter `out[out.label == 0]` to get the
calm-period training set.

---

## 12. Native C++ Isolation Forest — Complete Implementation

Algorithm: Liu, Ting & Zhou, "Isolation Forest," ICDM 2008. Default
hyperparameters match the paper's own recommendation (and `sklearn`'s
defaults): `n_estimators = 100`, sub-sample size `ψ = 256`, height limit
`l = ⌈log2(ψ)⌉ = 8`.

```cpp
// include/klstream/model/isolation_forest.hpp
#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <limits>
#include <memory>
#include <random>
#include <vector>

namespace klstream {

// ── IsolationTree ─────────────────────────────────────────────────────────
//
// A single random partition tree. Built once at training time from a
// random sub-sample of D-dimensional points. Each internal node picks a
// random feature and a random split value strictly between that feature's
// min and max within the current node's subset.
//
// Stored as a flat array of nodes (not pointer-linked) for cache locality
// during the scoring hot path — this matters because InferenceOp calls
// path_length() up to MAX_WINDOW_SIZE times per tick() (Section 7.2).
template <std::size_t D>
class IsolationTree {
public:
    using Point = std::array<float, D>;

    struct Node {
        int   feature   = -1;   // -1 marks a leaf
        float split      = 0.0f;
        int   left       = -1;  // index into nodes_, -1 if unset
        int   right      = -1;
        int   size_at_leaf = 0; // number of points that landed here (for c(n) correction)
    };

    // Builds the tree from `points` (a sub-sample already drawn by the
    // caller — IsolationForest::fit handles sampling, Section 12 below).
    void build(std::vector<Point> points, int height_limit, std::mt19937& rng) {
        nodes_.clear();
        nodes_.reserve(2 * points.size());
        root_ = build_node(points, 0, height_limit, rng);
    }

    // Path length for a single query point, with the Liu et al. correction
    // term c(size_at_leaf) added when recursion stops early due to the
    // height limit rather than true isolation (Eq. 2 in their paper).
    double path_length(const Point& x) const {
        int node_idx = root_;
        int depth = 0;
        while (true) {
            const Node& n = nodes_[node_idx];
            if (n.feature == -1) {
                return depth + c_factor(n.size_at_leaf);
            }
            ++depth;
            node_idx = (x[n.feature] < n.split) ? n.left : n.right;
        }
    }

    // c(n): average path length of an unsuccessful search in a BST of n
    // points (Liu et al. 2008, Eq. 2). Used both for leaf-size correction
    // above and for the forest-level normalisation in IsolationForest::score.
    static double c_factor(int n) {
        if (n <= 1) return 0.0;
        if (n == 2) return 1.0;
        constexpr double EULER_GAMMA = 0.5772156649015329;
        return 2.0 * (std::log(static_cast<double>(n - 1)) + EULER_GAMMA)
             - 2.0 * static_cast<double>(n - 1) / static_cast<double>(n);
    }

private:
    int build_node(std::vector<Point>& points, int depth, int height_limit,
                    std::mt19937& rng) {
        Node n;
        if (depth >= height_limit || points.size() <= 1) {
            n.size_at_leaf = static_cast<int>(points.size());
            nodes_.push_back(n);
            return static_cast<int>(nodes_.size()) - 1;
        }

        // Pick a random feature with non-degenerate range; bail to a leaf
        // after a bounded number of failed attempts (handles the case
        // where most/all features are constant in this subset).
        int feature = -1;
        float lo = 0.0f, hi = 0.0f;
        std::uniform_int_distribution<int> feat_dist(0, static_cast<int>(D) - 1);
        for (int attempt = 0; attempt < 8; ++attempt) {
            int f = feat_dist(rng);
            float mn = std::numeric_limits<float>::max();
            float mx = std::numeric_limits<float>::lowest();
            for (const auto& p : points) {
                mn = std::min(mn, p[f]);
                mx = std::max(mx, p[f]);
            }
            if (mx > mn) { feature = f; lo = mn; hi = mx; break; }
        }
        if (feature == -1) {
            n.size_at_leaf = static_cast<int>(points.size());
            nodes_.push_back(n);
            return static_cast<int>(nodes_.size()) - 1;
        }

        std::uniform_real_distribution<float> split_dist(lo, hi);
        float split = split_dist(rng);

        std::vector<Point> left_pts, right_pts;
        left_pts.reserve(points.size());
        right_pts.reserve(points.size());
        for (const auto& p : points) {
            (p[feature] < split ? left_pts : right_pts).push_back(p);
        }
        // Degenerate split guard (all points landed on one side).
        if (left_pts.empty() || right_pts.empty()) {
            n.size_at_leaf = static_cast<int>(points.size());
            nodes_.push_back(n);
            return static_cast<int>(nodes_.size()) - 1;
        }

        n.feature = feature;
        n.split   = split;
        int self_idx = static_cast<int>(nodes_.size());
        nodes_.push_back(n);                       // reserve slot first
        int left_idx  = build_node(left_pts,  depth + 1, height_limit, rng);
        int right_idx = build_node(right_pts, depth + 1, height_limit, rng);
        nodes_[self_idx].left  = left_idx;
        nodes_[self_idx].right = right_idx;
        return self_idx;
    }

    std::vector<Node> nodes_;
    int                root_ = -1;
};

// ── IsolationForest ────────────────────────────────────────────────────────
//
// An ensemble of IsolationTree<D>. Trained ONCE offline (Section 7.5) and
// reused, unmodified, across every window-strategy comparison.
//
// anomaly_score() implements Eq. 1 from Liu et al. 2008:
//     s(x, psi) = 2 ^ ( -E[h(x)] / c(psi) )
// Score approaches 1.0 for anomalies (short average path), approaches 0.5
// or below for normal points (path length near c(psi)).
template <std::size_t D>
class IsolationForest {
public:
    using Point = typename IsolationTree<D>::Point;

    IsolationForest(int n_estimators = 100, int sub_sample_size = 256,
                    std::uint32_t seed = 42)
        : n_estimators_(n_estimators)
        , psi_(sub_sample_size)
        , rng_(seed)
    {}

    // points: the full calm-period training set (Section 26 covers
    // validating this against sklearn on a held-out split).
    void fit(const std::vector<Point>& points) {
        int height_limit = static_cast<int>(std::ceil(std::log2(
            static_cast<double>(std::max(2, psi_)))));
        trees_.clear();
        trees_.reserve(n_estimators_);
        std::uniform_int_distribution<std::size_t> idx_dist(0, points.size() - 1);

        for (int t = 0; t < n_estimators_; ++t) {
            std::vector<Point> sample;
            sample.reserve(psi_);
            // Sampling without replacement within one tree, as in the
            // original paper; reseed per tree off the forest's own rng so
            // results are reproducible given a fixed `seed`.
            std::vector<std::size_t> indices(points.size());
            for (std::size_t i = 0; i < indices.size(); ++i) indices[i] = i;
            std::shuffle(indices.begin(), indices.end(), rng_);
            int take = std::min(psi_, static_cast<int>(points.size()));
            for (int i = 0; i < take; ++i) sample.push_back(points[indices[i]]);

            IsolationTree<D> tree;
            tree.build(std::move(sample), height_limit, rng_);
            trees_.push_back(std::move(tree));
        }
        c_psi_ = IsolationTree<D>::c_factor(psi_);
    }

    [[nodiscard]] double anomaly_score(const Point& x) const {
        double total = 0.0;
        for (const auto& tree : trees_) total += tree.path_length(x);
        double avg_path = total / static_cast<double>(trees_.size());
        return std::pow(2.0, -avg_path / c_psi_);
    }

    [[nodiscard]] std::size_t n_trees() const { return trees_.size(); }

private:
    int                            n_estimators_;
    int                            psi_;
    std::mt19937                   rng_;
    double                         c_psi_ = 1.0;
    std::vector<IsolationTree<D>>  trees_;
};

} // namespace klstream
```

**Complexity note for Section 7.2's causal chain:** `anomaly_score()` costs
`O(n_estimators × average_tree_depth)` ≈ `O(100 × 8)` = a fixed ~800
node-visits per point, completely independent of window size. Scoring a
`WindowBatch` of `W` points therefore costs `O(W × 800)` — **linear in `W`**,
which is exactly the "inference cost scales with window size" property the
whole research question depends on.

---

## 13. New KLStream Types — FeatureVector and WindowBatch

```cpp
// include/klstream/window/types.hpp
#pragma once
#include <array>
#include <cstdint>

namespace klstream {

// ── FeatureVector ─────────────────────────────────────────────────────────
// D = 5, matching Section 10's feature table exactly. Order matters: this
// order must match the column order written by preprocess_lobster.py
// (Section 11) and read by TickSource (Section 18).
struct FeatureVector {
    float log_return;
    float rolling_vol;
    float order_imbalance;
    float spread_bps;
    float volume;          // already log1p-scaled by the Python preprocessor

    static constexpr std::size_t kDim = 5;

    // Conversion to the array type IsolationTree/IsolationForest operate on.
    std::array<float, kDim> to_point() const {
        return { log_return, rolling_vol, order_imbalance, spread_bps, volume };
    }
};
static_assert(sizeof(FeatureVector) == 5 * sizeof(float),
    "FeatureVector must stay a flat POD — no padding tricks, it crosses queues");

// ── WindowBatch ────────────────────────────────────────────────────────────
// Fixed-capacity, trivially-copyable container — see Section 7.3 for why
// this cannot be a std::vector. MAX_WINDOW_SIZE caps every window
// strategy's upper bound (AdaptiveWindowController::w_max_,
// DataDrivenWindowOp's max, and FixedWindowOp's constant must all be
// <= MAX_WINDOW_SIZE).
inline constexpr std::size_t MAX_WINDOW_SIZE = 256;

struct WindowBatch {
    std::array<FeatureVector, MAX_WINDOW_SIZE> points{};
    std::uint32_t count = 0;
    std::uint64_t first_seq = 0;   // seq of points[0] — for ground-truth join
    std::uint64_t last_seq  = 0;   // seq of points[count-1]

    void push_back(const FeatureVector& fv, std::uint64_t seq) {
        if (count == 0) first_seq = seq;
        points[count++] = fv;
        last_seq = seq;
    }
    bool full(std::size_t target_size) const { return count >= target_size; }
};
static_assert(std::is_trivially_copyable_v<WindowBatch>,
    "WindowBatch must remain trivially copyable to cross SPSCQueue boundaries");

// ── DetectionResult ──────────────────────────────────────────────────────
// Emitted by InferenceOp (Section 17), consumed by Sink (Section 19).
struct DetectionResult {
    double        max_score        = 0.0;
    std::uint32_t window_size_used = 0;
    std::uint64_t first_seq        = 0;
    std::uint64_t last_seq         = 0;
    std::uint64_t flagged_seq      = 0;   // seq of the point that produced max_score
    float         occupancy_at_decision = 0.0f; // EMA reading at window-start time, 0 for non-adaptive variants
};
static_assert(std::is_trivially_copyable_v<DetectionResult>);

} // namespace klstream
```

---

## 14. AdaptiveWindowOp — The Core Contribution

This is the operator the entire paper is about. It reuses
`EMAOccupancyTracker<Queue>` from `klstream/core/backpressure.hpp`
**completely unmodified** — the novelty is entirely in *what reads the
tracker and what it does with the reading*, not in the tracker itself.

```cpp
// include/klstream/window/adaptive_window_op.hpp
#pragma once
#include "../core/operator.hpp"
#include "../core/event.hpp"
#include "../core/spsc_queue.hpp"
#include "../core/metrics.hpp"
#include "../core/backpressure.hpp"   // EMAOccupancyTracker — reused as-is
#include "types.hpp"
#include <algorithm>
#include <cstdint>

namespace klstream {

// ── AdaptiveWindowController ─────────────────────────────────────────────
//
// Pure control logic, separated from the operator so it can be unit-tested
// without any queue/threading machinery (Section 27 covers testing this
// in isolation with synthetic occupancy traces).
//
// Asymmetric shrink-fast / grow-slow update, directly modeled on TCP's
// AIMD congestion control (cited explicitly in your methodology section —
// this is a principled choice, not an arbitrary tuning knob). The deadband
// between occ_low_ and occ_high_ is what prevents oscillation (Section 6,
// point 1) — do not remove it even if it looks redundant in early testing.
class AdaptiveWindowController {
public:
    AdaptiveWindowController(std::uint32_t w_min, std::uint32_t w_max,
                             double occ_low, double occ_high,
                             double shrink_factor = 0.70,
                             double grow_factor   = 1.15)
        : w_min_(w_min), w_max_(w_max)
        , occ_low_(occ_low), occ_high_(occ_high)
        , shrink_factor_(shrink_factor), grow_factor_(grow_factor)
        , current_w_(w_max)   // start wide: assume calm until proven otherwise
    {}

    // Call exactly once per window START (Section 14's tick() logic below
    // captures this once and holds it for the whole window's fill duration
    // — never mid-window, to avoid a window "shrinking out from under
    // itself").
    std::uint32_t update(double ema_occupancy) {
        if (ema_occupancy > occ_high_) {
            current_w_ = std::max(w_min_,
                static_cast<std::uint32_t>(current_w_ * shrink_factor_));
            ++shrink_events_;
        } else if (ema_occupancy < occ_low_) {
            current_w_ = std::min(w_max_,
                static_cast<std::uint32_t>(current_w_ * grow_factor_));
            ++grow_events_;
        }
        // else: deadband — hold steady. This branch existing (doing
        // nothing) is the whole anti-oscillation mechanism.
        track_direction(ema_occupancy);
        return current_w_;
    }

    std::uint32_t current() const { return current_w_; }

    // Window Oscillation Rate support (Section 23.2) — counts direction
    // *changes*, not raw shrink/grow events, which is the metric that
    // actually captures thrashing.
    std::uint64_t direction_changes() const { return direction_changes_; }

private:
    void track_direction(double ema_occupancy) {
        int dir = 0;
        if (ema_occupancy > occ_high_) dir = -1;       // shrinking
        else if (ema_occupancy < occ_low_) dir = 1;    // growing
        else return;                                     // deadband: no direction sample
        if (last_dir_ != 0 && dir != last_dir_) ++direction_changes_;
        last_dir_ = dir;
    }

    std::uint32_t w_min_, w_max_;
    double        occ_low_, occ_high_;
    double        shrink_factor_, grow_factor_;
    std::uint32_t current_w_;
    std::uint64_t shrink_events_{0};
    std::uint64_t grow_events_{0};
    std::uint64_t direction_changes_{0};
    int           last_dir_{0};
};

// ── AdaptiveWindowOp ───────────────────────────────────────────────────────
//
// Implements the IOperator interface (Section 7.5 of the Implementation
// Guide) — same tick()/OpStatus contract as every other KLStream operator,
// so it slots into Runtime::register_op() with no special handling.
class AdaptiveWindowOp : public IOperator {
public:
    using InQueue  = SPSCQueue<Event<FeatureVector>>;
    using OutQueue = SPSCQueue<Event<WindowBatch>>;

    AdaptiveWindowOp(std::string name, InQueue* input, OutQueue* output,
                     std::uint32_t w_min = 16, std::uint32_t w_max = MAX_WINDOW_SIZE,
                     double occ_low = 0.30, double occ_high = 0.70)
        : IOperator(std::move(name))
        , input_(input), output_(output)
        , controller_(w_min, w_max, occ_low, occ_high)
        , tracker_(*output)   // reads occupancy of ITS OWN output queue —
                                // this is the load-bearing line, see Section 7.2
    {}

    void attach_metrics(OperatorMetrics* m) { metrics_ = m; }
    const AdaptiveWindowController& controller() const { return controller_; }

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

        // At the START of a new window, capture this window's target size
        // ONCE from the current EMA reading. Held fixed until this window
        // fires (Section 7.2's "shrink for FUTURE windows" rule).
        if (buffer_.count == 0) {
            tracker_.update();
            target_w_ = controller_.update(tracker_.ema());
        }

        Event<FeatureVector> in_ev;
        if (!input_->try_pop(&in_ev)) {
            if (metrics_) metrics_->events_idle.increment();
            return OpStatus::Idle;
        }

        buffer_.push_back(in_ev.data, in_ev.seq);

        if (!buffer_.full(target_w_)) {
            if (metrics_) metrics_->events_processed.increment();
            return OpStatus::Processed;   // buffered, window not yet ready
        }

        Event<WindowBatch> out_ev;
        out_ev.timestamp_ns = in_ev.timestamp_ns;  // last tick's timestamp;
                                                     // InferenceOp overwrites
                                                     // this with the flagged
                                                     // tick's own timestamp
                                                     // before re-emitting
                                                     // (Section 7.4, 17.2)
        out_ev.key  = 0;
        out_ev.seq  = in_ev.seq;
        out_ev.data = buffer_;
        buffer_ = WindowBatch{};   // reset for next window

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
    InQueue*                       input_;
    OutQueue*                      output_;
    AdaptiveWindowController       controller_;
    EMAOccupancyTracker<OutQueue>  tracker_;
    WindowBatch                    buffer_{};
    std::uint32_t                  target_w_{0};
    Event<WindowBatch>             pending_{};
    bool                            has_pending_{false};
    OperatorMetrics*               metrics_{nullptr};
};

} // namespace klstream
```

### 14.1 Recommended Default Thresholds (Starting Point for Experiment 4's Sweep)

| Parameter | Default | Rationale |
|---|---|---|
| `w_min` | 16 | Small enough to meaningfully cut per-window inference cost (16/256 ≈ 16× cheaper than max), large enough that the Isolation Forest still sees a non-trivial batch |
| `w_max` | 256 | Equals `MAX_WINDOW_SIZE` — uses the full compile-time budget when calm |
| `occ_low` | 0.30 | Below this, the downstream `InferenceOp` is comfortably keeping up |
| `occ_high` | 0.70 | Matches `BP_SOFT_THRESHOLD` already defined in `config.hpp` — reuse the existing constant rather than inventing a new one |
| `shrink_factor` | 0.70 | Asymmetric: shrink by 30% per triggering tick |
| `grow_factor` | 1.15 | Asymmetric: grow by only 15% per triggering tick — classic AIMD shape, recovers cautiously to avoid immediately re-triggering shrink |

---

## 15. DataDrivenWindowOp — The Literature-Style Baseline

This baseline exists **specifically to isolate** what pressure-awareness
contributes (Section 5.4 of the dossier's reasoning, preserved here). Keep
its engineering effort proportionate — it is not your contribution.

Sizing logic: window shrinks when **rolling realized volatility** is high
(in the spirit of ASWN's anomaly-triggered shrinking, Section 4.1), with no
awareness of pipeline occupancy whatsoever.

```cpp
// include/klstream/window/data_driven_window_op.hpp
#pragma once
#include "../core/operator.hpp"
#include "../core/event.hpp"
#include "../core/spsc_queue.hpp"
#include "../core/metrics.hpp"
#include "types.hpp"
#include <algorithm>
#include <cstdint>

namespace klstream {

class DataDrivenWindowOp : public IOperator {
public:
    using InQueue  = SPSCQueue<Event<FeatureVector>>;
    using OutQueue = SPSCQueue<Event<WindowBatch>>;

    DataDrivenWindowOp(std::string name, InQueue* input, OutQueue* output,
                       std::uint32_t w_min = 16, std::uint32_t w_max = MAX_WINDOW_SIZE,
                       float vol_low = 0.0001f, float vol_high = 0.001f)
        : IOperator(std::move(name))
        , input_(input), output_(output)
        , w_min_(w_min), w_max_(w_max)
        , vol_low_(vol_low), vol_high_(vol_high)
        , target_w_(w_max)
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

        if (buffer_.count == 0) {
            // Linear interpolation between w_max (calm) and w_min (volatile),
            // clamped — the literature-baseline analogue of Section 14's
            // EMA-occupancy read, but driven by the FeatureVector's own
            // rolling_vol field rather than any queue state.
            float vol = last_vol_;
            float frac = std::clamp((vol - vol_low_) / (vol_high_ - vol_low_), 0.0f, 1.0f);
            target_w_ = static_cast<std::uint32_t>(
                w_max_ - frac * static_cast<float>(w_max_ - w_min_));
        }

        Event<FeatureVector> in_ev;
        if (!input_->try_pop(&in_ev)) {
            if (metrics_) metrics_->events_idle.increment();
            return OpStatus::Idle;
        }
        last_vol_ = in_ev.data.rolling_vol;
        buffer_.push_back(in_ev.data, in_ev.seq);

        if (!buffer_.full(target_w_)) {
            if (metrics_) metrics_->events_processed.increment();
            return OpStatus::Processed;
        }

        Event<WindowBatch> out_ev;
        out_ev.timestamp_ns = in_ev.timestamp_ns;
        out_ev.seq  = in_ev.seq;
        out_ev.data = buffer_;
        buffer_ = WindowBatch{};

        if (output_->try_push(out_ev)) {
            if (metrics_) metrics_->events_processed.increment();
            return OpStatus::Processed;
        }
        pending_ = out_ev;
        has_pending_ = true;
        if (metrics_) metrics_->events_blocked.increment();
        return OpStatus::Blocked;
    }

private:
    InQueue*       input_;
    OutQueue*      output_;
    std::uint32_t  w_min_, w_max_;
    float          vol_low_, vol_high_;
    std::uint32_t  target_w_;
    float          last_vol_{0.0f};
    WindowBatch    buffer_{};
    Event<WindowBatch> pending_{};
    bool           has_pending_{false};
    OperatorMetrics* metrics_{nullptr};
};

} // namespace klstream
```

`vol_low_`/`vol_high_` defaults are placeholders — calibrate them in Week 3
(Section 29) against the actual `rolling_vol` distribution observed in your
preprocessed LOBSTER data (e.g., set `vol_low_` to its 25th percentile and
`vol_high_` to its 95th percentile on the calm-period training set), so the
baseline is genuinely tuned rather than a strawman. A strawman baseline
would undermine, not strengthen, your headline comparison.

---

## 16. FixedWindowOp — Reusing Existing KLStream Code

No new file. This baseline is `TumblingCountWindow<FeatureVector, WindowBatch>`
from `klstream/operators/window.hpp`, **completely unmodified**, with an
identity aggregation function that just packs the buffered vector into a
`WindowBatch`:

```cpp
// In your pipeline wiring file (Section 22), not a new header:
#include "klstream/operators/window.hpp"
#include "klstream/window/types.hpp"

klstream::TumblingCountWindow<klstream::FeatureVector, klstream::WindowBatch>
    fixed_window(
        "fixed_window", &q_feat_win, &q_win_inf,
        /* window_size = */ 128,   // a representative mid-point between w_min and w_max
        [](const std::vector<klstream::FeatureVector>& buf) -> klstream::WindowBatch {
            klstream::WindowBatch wb;
            for (const auto& fv : buf) wb.push_back(fv, 0 /* seq filled below */);
            return wb;
        });
```

**One real wrinkle**: `TumblingCountWindow`'s aggregation lambda signature
(Section 8.5 of the Implementation Guide) only receives
`const std::vector<T>&`, not the original `Event<T>` sequence numbers, so it
cannot fill in `WindowBatch::first_seq`/`last_seq`/per-point `seq` directly.
**Fix**: extend `TumblingCountWindow`'s buffer to store `Event<T>` instead of
bare `T` — a 4-line change to the existing header (store `Event<T>` in
`buffer_`, pass `const std::vector<Event<T>>&` to `AggrFn`). This is the
**one** sanctioned modification to existing KLStream code in this entire
project; document it as such in your commit history so it is easy to find
and review. Everything else in Sections 14–19 is purely additive.

---

## 17. InferenceOp — Wrapping the Isolation Forest

### 17.1 Full Implementation

```cpp
// include/klstream/window/inference_op.hpp
#pragma once
#include "../core/operator.hpp"
#include "../core/event.hpp"
#include "../core/spsc_queue.hpp"
#include "../core/metrics.hpp"
#include "../model/isolation_forest.hpp"
#include "types.hpp"

namespace klstream {

class InferenceOp : public IOperator {
public:
    using InQueue  = SPSCQueue<Event<WindowBatch>>;
    using OutQueue = SPSCQueue<Event<DetectionResult>>;
    using Forest   = IsolationForest<FeatureVector::kDim>;

    InferenceOp(std::string name, InQueue* input, OutQueue* output,
               const Forest* forest)
        : IOperator(std::move(name))
        , input_(input), output_(output), forest_(forest)
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

        Event<WindowBatch> in_ev;
        if (!input_->try_pop(&in_ev)) {
            if (metrics_) metrics_->events_idle.increment();
            return OpStatus::Idle;
        }

        // ── The O(W log psi) hot loop — Section 7.2's causal mechanism ───
        const WindowBatch& wb = in_ev.data;
        double   max_score   = -1.0;
        uint32_t max_idx     = 0;
        for (std::uint32_t i = 0; i < wb.count; ++i) {
            double s = forest_->anomaly_score(wb.points[i].to_point());
            if (s > max_score) { max_score = s; max_idx = i; }
        }

        Event<DetectionResult> out_ev;
        // Re-stamp with the FLAGGED point's own timestamp, not the window's
        // arrival timestamp (Section 7.4) — this is what makes downstream
        // latency() measure "time since the actual anomalous tick occurred."
        //
        // NOTE: per-point timestamps are not retained inside WindowBatch
        // (FeatureVector intentionally omits a timestamp field to keep it
        // exactly 5 floats / 20 bytes for cache-friendly scoring). We
        // approximate the flagged point's wall-clock arrival time by linear
        // interpolation between the window's first and last event
        // timestamps — out_ev.timestamp_ns = in_ev.timestamp_ns
        // (the window's LAST-tick arrival time) is used as a conservative
        // (slightly pessimistic, never optimistic) stand-in. State this
        // approximation explicitly in your methodology section: it means
        // reported latency is an upper bound, not an exact per-tick figure,
        // which is the safe direction to bias an evaluation.
        out_ev.timestamp_ns = in_ev.timestamp_ns;
        out_ev.seq = in_ev.seq;
        out_ev.data = DetectionResult{
            max_score,
            wb.count,
            wb.first_seq,
            wb.last_seq,
            wb.first_seq + max_idx,
            0.0f   // filled in by the wiring code for the Adaptive variant only
        };

        if (output_->try_push(out_ev)) {
            if (metrics_) metrics_->events_processed.increment();
            return OpStatus::Processed;
        }
        pending_ = out_ev;
        has_pending_ = true;
        if (metrics_) metrics_->events_blocked.increment();
        return OpStatus::Blocked;
    }

private:
    InQueue*       input_;
    OutQueue*      output_;
    const Forest*  forest_;   // owned by main(), lives for the runtime's lifetime
    Event<DetectionResult> pending_{};
    bool           has_pending_{false};
    OperatorMetrics* metrics_{nullptr};
};

} // namespace klstream
```

### 17.2 The Timestamp Approximation, Stated Plainly

Section 7.4 promised "the timestamp of whichever tick achieved the max
score." The honest implementation note: `FeatureVector` deliberately has no
per-point timestamp field (keeping it a flat 5-float/20-byte struct matters
for the scoring loop's cache behavior — adding a 64-bit timestamp per point
would grow `WindowBatch` by `8 × MAX_WINDOW_SIZE` = 2 KB per event for no
benefit to the algorithm itself). The implementation above uses the
**window's last-event timestamp** for every detection result, which is a
deliberate, declared **upper bound** on true detection latency (the real
flagged tick is always at or before the window's last tick). Report it as
such — "latency reported here is the time from window completion to
detection, which upper-bounds true per-tick detection latency by at most one
window's wall-clock duration" — this is honest and still supports every
claim in Section 25's experiments, since the bias is **identical across all
three architectures being compared** (it does not favor any one of them).

---

## 18. TickSource — Replaying Financial Data

```cpp
// include/klstream/window/financial_tick_source.hpp
#pragma once
#include "../core/operator.hpp"
#include "../core/event.hpp"
#include "../core/spsc_queue.hpp"
#include "../core/metrics.hpp"
#include "../core/backpressure.hpp"
#include "types.hpp"
#include <fstream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace klstream {

// One row of the CSV produced by preprocess_lobster.py (Section 11).
struct TickRow {
    std::uint64_t seq;
    std::uint64_t timestamp_ns;
    float         log_return, rolling_vol, order_imbalance, spread_bps, volume;
    std::uint8_t  label;          // 0=normal, 1=flash_crash, 2=wash_trade_proxy
    std::uint8_t  is_burst_period;
};

// Loads the entire replay CSV into memory once at startup. LOBSTER sample
// days are at most a few hundred thousand events — comfortably fits in RAM
// on an 8GB+ machine; no streaming file I/O needed during the actual run,
// which keeps TickSource's tick() allocation-free and fast.
inline std::vector<TickRow> load_replay_csv(const std::string& path) {
    std::ifstream f(path);
    if (!f) throw std::runtime_error("cannot open replay CSV: " + path);
    std::string line;
    std::getline(f, line); // header
    std::vector<TickRow> rows;
    while (std::getline(f, line)) {
        std::stringstream ss(line);
        std::string cell;
        TickRow r{};
        std::getline(ss, cell, ','); r.seq = std::stoull(cell);
        std::getline(ss, cell, ','); r.timestamp_ns = std::stoull(cell);
        std::getline(ss, cell, ','); /* mid_price, unused downstream */
        std::getline(ss, cell, ','); r.log_return = std::stof(cell);
        std::getline(ss, cell, ','); r.rolling_vol = std::stof(cell);
        std::getline(ss, cell, ','); r.order_imbalance = std::stof(cell);
        std::getline(ss, cell, ','); r.spread_bps = std::stof(cell);
        std::getline(ss, cell, ','); r.volume = std::stof(cell);
        std::getline(ss, cell, ','); r.label = static_cast<std::uint8_t>(std::stoi(cell));
        std::getline(ss, cell, ','); r.is_burst_period = static_cast<std::uint8_t>(std::stoi(cell));
        rows.push_back(r);
    }
    return rows;
}

// ── FinancialTickSource ───────────────────────────────────────────────────
//
// Wraps SourceOperator<FeatureVector>'s generator-function pattern
// (Section 8.1 of the Implementation Guide) around the preloaded replay
// data. Two replay modes:
//   PreserveTiming — sleeps between events to approximate the original
//     LOBSTER inter-event gaps (scaled by speed_factor). Realistic but slow
//     to reach high sustained throughput; good for latency-fidelity runs.
//   MaxRate — no sleeping; emits as fast as the downstream rate limiter (if
//     any) and queue backpressure allow. Good for the bursty-source / stress
//     experiments (Section 25, reusing the original Section 14.1 pattern).
//
// Bursty behavior: rows flagged is_burst_period=1 are emitted at MaxRate
// regardless of the configured mode; calm rows respect the configured mode.
// This directly reproduces the "alternates between high-rate burst and
// low-rate quiet phases" generator from the original adaptive-backpressure
// research extension (Section 14.1 of the Implementation Guide), now driven
// by real injected-anomaly placement instead of an artificial timer.
enum class ReplayMode { PreserveTiming, MaxRate };

class FinancialTickSource {
public:
    FinancialTickSource(std::vector<TickRow> rows, ReplayMode mode,
                        double speed_factor = 1.0)
        : rows_(std::move(rows)), mode_(mode), speed_factor_(speed_factor)
    {}

    // Generator function passed to SourceOperator<FeatureVector>'s ctor
    // (Section 8.1 of the Implementation Guide) — matches
    // SourceOperator<T>::Generator's exact signature.
    bool operator()(Event<FeatureVector>& out, std::uint64_t /*unused_seq*/) {
        if (idx_ >= rows_.size()) return false;   // replay finished

        const TickRow& r = rows_[idx_];
        bool burst = (r.is_burst_period != 0);
        if (mode_ == ReplayMode::PreserveTiming && !burst && idx_ > 0) {
            std::uint64_t gap_ns = r.timestamp_ns - rows_[idx_ - 1].timestamp_ns;
            auto scaled = std::chrono::nanoseconds(
                static_cast<std::int64_t>(static_cast<double>(gap_ns) / speed_factor_));
            // Cap any single sleep at 1ms so a multi-second LOBSTER gap
            // (e.g., overnight, or a quiet pre-market period) never stalls
            // the whole pipeline for real wall-clock seconds.
            if (scaled < std::chrono::milliseconds(1)) {
                std::this_thread::sleep_for(scaled);
            }
        }

        FeatureVector fv{ r.log_return, r.rolling_vol, r.order_imbalance,
                          r.spread_bps, r.volume };
        out = Event<FeatureVector>{ r.timestamp_ns, /*key=*/0, r.seq, fv };
        ground_truth_label_ = r.label;   // exposed via last_label() for the
                                          // optional online-eval harness
        ++idx_;
        return true;
    }

    std::uint8_t last_label() const { return ground_truth_label_; }
    std::size_t  remaining() const { return rows_.size() - idx_; }

private:
    std::vector<TickRow> rows_;
    ReplayMode            mode_;
    double                speed_factor_;
    std::size_t           idx_{0};
    std::uint8_t          ground_truth_label_{0};
};

} // namespace klstream
```

Wiring this into a `SourceOperator<FeatureVector>` (Section 22 shows the full
`main()`):

```cpp
auto rows = klstream::load_replay_csv("replay_AAPL_20120621.csv");
klstream::FinancialTickSource tick_src(std::move(rows),
    klstream::ReplayMode::MaxRate, /*speed_factor=*/1.0);

klstream::SourceOperator<klstream::FeatureVector> source(
    "tick_source", &q_src_feat,
    [&tick_src](klstream::Event<klstream::FeatureVector>& out, std::uint64_t seq) {
        return tick_src(out, seq);
    });
```

---

## 19. Sink and Result Logging

```cpp
// include/klstream/window/result_sink.hpp
#pragma once
#include "../core/operator.hpp"
#include "../core/event.hpp"
#include "../core/spsc_queue.hpp"
#include "../core/metrics.hpp"
#include "types.hpp"
#include <fstream>
#include <iomanip>

namespace klstream {

// Writes one CSV row per DetectionResult. Joined against
// injection_log.csv (Section 9.3) offline in Python (Section 23/25's
// analysis notebook) — this operator does NOT compute F1/PATR/WOR/LBA
// itself; it only records ground truth needed to compute them later,
// keeping the hot C++ path free of any evaluation-metric logic.
class ResultSink : public IOperator {
public:
    using InQueue = SPSCQueue<Event<DetectionResult>>;

    ResultSink(std::string name, InQueue* input, std::string out_csv_path)
        : IOperator(std::move(name))
        , input_(input)
        , out_(out_csv_path)
    {
        out_ << "seq,detect_timestamp_ns,latency_ns,max_score,window_size_used,"
                "first_seq,last_seq,flagged_seq,occupancy_at_decision\n";
    }

    void attach_metrics(OperatorMetrics* m) { metrics_ = m; }

    OpStatus tick() override {
        Event<DetectionResult> ev;
        if (!input_->try_pop(&ev)) {
            if (metrics_) metrics_->events_idle.increment();
            return OpStatus::Idle;
        }
        const auto& r = ev.data;
        out_ << ev.seq << ','
             << ev.timestamp_ns << ','
             << ev.latency_ns() << ','
             << std::setprecision(8) << r.max_score << ','
             << r.window_size_used << ','
             << r.first_seq << ','
             << r.last_seq << ','
             << r.flagged_seq << ','
             << r.occupancy_at_decision << '\n';
        if (metrics_) metrics_->events_processed.increment();
        return OpStatus::Processed;
    }

    void shutdown() override { out_.flush(); }

private:
    InQueue*      input_;
    std::ofstream out_;
    OperatorMetrics* metrics_{nullptr};
};

} // namespace klstream
```

---

## 20. Repository Structure

Additive to the existing KLStream repository — every file below is new
except the one four-line modification to `window.hpp` noted in Section 16.

```text
KLStream/
├── (... everything from the Implementation Guide, unchanged ...)
│
├── include/klstream/
│   ├── window/                              # NEW
│   │   ├── types.hpp                        # Section 13
│   │   ├── adaptive_window_op.hpp           # Section 14
│   │   ├── data_driven_window_op.hpp        # Section 15
│   │   ├── inference_op.hpp                 # Section 17
│   │   ├── financial_tick_source.hpp        # Section 18
│   │   └── result_sink.hpp                  # Section 19
│   │
│   ├── model/                               # NEW
│   │   └── isolation_forest.hpp             # Section 12
│   │
│   └── operators/
│       └── window.hpp                       # MODIFIED — see Section 16's
│                                              # 4-line Event<T> buffer change
│
├── preprocessing/                            # NEW
│   ├── preprocess_lobster.py                # Section 11
│   └── train_forest_reference.py            # Section 26 — sklearn validation
│
├── data/
│   ├── raw/                                 # raw LOBSTER message+orderbook CSVs
│   └── replay/                              # preprocess_lobster.py outputs
│       ├── replay_AAPL_20120621.csv
│       └── injection_log_AAPL_20120621.csv
│
├── adaptive_window/                          # NEW — experiment driver, parallel
│   ├── CMakeLists.txt                        # to existing examples/ structure
│   ├── main.cpp                              # Section 22 — full pipeline wiring
│   ├── train_forest.cpp                      # native-C++ offline training entry point
│   └── harness.cpp                           # Section 25 — runs all architectures × loads
│
├── analysis/                                  # NEW
│   ├── compute_metrics.py                    # Section 23/24 — F1, PA%K, PATR, WOR, LBA
│   └── results_notebook.ipynb                # plots for the paper
│
├── results/                                   # NEW (gitignored)
│   └── raw/                                  # per-run CSVs from ResultSink
│
└── paper/                                     # NEW
    └── draft.md
```

---

## 21. CMake Integration

```cmake
# adaptive_window/CMakeLists.txt
# Appended as a new add_subdirectory() call in the project root CMakeLists.txt,
# alongside the existing add_subdirectory(examples) / tests / benchmarks calls.

add_executable(adaptive_window_main main.cpp)
target_link_libraries(adaptive_window_main PRIVATE klstream::klstream)

add_executable(train_forest train_forest.cpp)
target_link_libraries(train_forest PRIVATE klstream::klstream)

add_executable(adaptive_window_harness harness.cpp)
target_link_libraries(adaptive_window_harness PRIVATE klstream::klstream)
```

No new external dependencies — `isolation_forest.hpp` is pure `<random>`/
`<cmath>`/STL, consistent with Section 2's decision to avoid ONNX Runtime
entirely. `target_link_libraries(... klstream::klstream)` already pulls in
`-pthread` and the include path; nothing else is required.

---

## 22. Full Pipeline Wiring (main.cpp for Each Architecture)

A single `main.cpp`, parameterized by `--architecture={fixed,datadriven,adaptive}`
so the harness (Section 25) can drive all three from one binary without code
duplication. This is the file a coding agent should treat as the
integration point that proves every other section is correct.

```cpp
// adaptive_window/main.cpp
#include "klstream/core/runtime.hpp"
#include "klstream/core/metrics.hpp"
#include "klstream/operators/source.hpp"
#include "klstream/operators/window.hpp"
#include "klstream/window/types.hpp"
#include "klstream/window/adaptive_window_op.hpp"
#include "klstream/window/data_driven_window_op.hpp"
#include "klstream/window/inference_op.hpp"
#include "klstream/window/financial_tick_source.hpp"
#include "klstream/window/result_sink.hpp"
#include "klstream/model/isolation_forest.hpp"

#include <chrono>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

using namespace klstream;

// Loads a pretrained forest written by train_forest.cpp (Section 26) as a
// flat binary blob — see that section for the (de)serialisation format.
IsolationForest<FeatureVector::kDim> load_forest(const std::string& path);

int main(int argc, char** argv) {
    std::string architecture = "adaptive";   // fixed | datadriven | adaptive
    std::string replay_csv   = "data/replay/replay_AAPL_20120621.csv";
    std::string forest_path  = "data/forest.bin";
    std::string out_csv      = "results/raw/run.csv";
    int         duration_sec = 60;
    ReplayMode  mode         = ReplayMode::MaxRate;

    for (int i = 1; i < argc; ++i) {
        std::string a = argv[i];
        auto val = [&](const char* flag){ return a.rfind(flag, 0) == 0; };
        if (val("--architecture=")) architecture = a.substr(15);
        else if (val("--replay=")) replay_csv = a.substr(9);
        else if (val("--forest=")) forest_path = a.substr(9);
        else if (val("--out=")) out_csv = a.substr(6);
        else if (val("--duration=")) duration_sec = std::stoi(a.substr(11));
        else if (val("--preserve-timing")) mode = ReplayMode::PreserveTiming;
    }

    auto forest = load_forest(forest_path);
    auto rows   = load_replay_csv(replay_csv);

    // ── Queues ────────────────────────────────────────────────────────────
    SPSCQueue<Event<FeatureVector>> q_src_feat(4096);   // source -> feature extract (identity here: TickSource already emits FeatureVector)
    SPSCQueue<Event<WindowBatch>>   q_win_inf(64);       // window stage -> InferenceOp
                                                            // SMALL capacity — see Section 7.3
    SPSCQueue<Event<DetectionResult>> q_inf_snk(4096);

    OperatorMetrics m_src("tick_source"), m_win("window_op"),
                    m_inf("inference"),   m_snk("result_sink");

    // ── Source ────────────────────────────────────────────────────────────
    FinancialTickSource tick_src(std::move(rows), mode);
    SourceOperator<FeatureVector> source("tick_source", &q_src_feat,
        [&tick_src](Event<FeatureVector>& out, std::uint64_t seq) {
            return tick_src(out, seq);
        });
    source.attach_metrics(&m_src);

    // ── Window stage (the variable under test) ──────────────────────────
    std::unique_ptr<IOperator> window_op;
    AdaptiveWindowOp*    adaptive_ptr = nullptr;   // kept for occupancy logging below

    if (architecture == "fixed") {
        auto* op = new TumblingCountWindow<FeatureVector, WindowBatch>(
            "fixed_window", &q_src_feat, &q_win_inf, 128,
            [](const std::vector<FeatureVector>& buf) {
                WindowBatch wb;
                for (const auto& fv : buf) wb.push_back(fv, 0);
                return wb;
            });
        window_op.reset(op);
    } else if (architecture == "datadriven") {
        window_op = std::make_unique<DataDrivenWindowOp>(
            "data_driven_window", &q_src_feat, &q_win_inf);
    } else { // adaptive
        auto* op = new AdaptiveWindowOp("adaptive_window", &q_src_feat, &q_win_inf);
        adaptive_ptr = op;
        window_op.reset(op);
    }
    // NOTE: attach_metrics() needs a per-type call here in real code (the
    // base IOperator* erases the concrete type) — either give IOperator a
    // virtual attach_metrics(OperatorMetrics*) hook, or attach metrics
    // before erasing to the base pointer above. Pick the former for
    // consistency with how the rest of KLStream already does metrics.

    // ── Inference + Sink ─────────────────────────────────────────────────
    InferenceOp inference("inference", &q_win_inf, &q_inf_snk, &forest);
    inference.attach_metrics(&m_inf);

    ResultSink sink("result_sink", &q_inf_snk, out_csv);
    sink.attach_metrics(&m_snk);

    // ── Runtime ───────────────────────────────────────────────────────────
    Runtime rt;
    rt.add_worker(CoreAffinity::Performance);   // 0: source
    rt.add_worker(CoreAffinity::Performance);   // 1: window stage
    rt.add_worker(CoreAffinity::Performance);   // 2: inference (heaviest compute)
    rt.add_worker(CoreAffinity::Efficiency);    // 3: sink

    rt.register_op(&source, 0);
    rt.register_op(window_op.get(), 1);
    rt.register_op(&inference, 2);
    rt.register_op(&sink, 3);

    for (auto* m : {&m_src, &m_win, &m_inf, &m_snk}) rt.metrics().add(m);

    std::cout << "Running architecture=" << architecture
              << " for " << duration_sec << "s, output=" << out_csv << "\n";
    rt.start();
    rt.wait_for(std::chrono::seconds(duration_sec));
    rt.stop();

    if (adaptive_ptr) {
        std::cout << "Window-size direction changes: "
                  << adaptive_ptr->controller().direction_changes() << "\n";
    }
    return 0;
}
```

**Implementation-agent note**: the `attach_metrics` virtual-dispatch wrinkle
flagged in the comment above is a real, small gap versus the Implementation
Guide's existing operators (which all expose a concrete, non-virtual
`attach_metrics`). The clean fix is adding
`virtual void attach_metrics(OperatorMetrics*) {}` to `IOperator` itself
(Section 7.5 of the Implementation Guide) as a second sanctioned, minimal,
additive change to existing KLStream code (alongside Section 16's
`TumblingCountWindow` change) — call it out explicitly in your commit
history for the same reason.

---

## 23. Evaluation Methodology — Metrics in Full

All metrics are computed **offline, in Python**, from the joined
`results/raw/<run>.csv` (Section 19's `ResultSink` output) and
`data/replay/injection_log_<ticker>_<date>.csv` (Section 9.3's ground truth).
Keeping evaluation entirely out of the C++ hot path is intentional — it keeps
`InferenceOp`'s `tick()` free of any logic unrelated to the actual research
question.

### 23.1 Pressure-Adaptive Throughput Retention (PATR)

```
PATR = throughput(during burst window) / throughput(during steady-state window)
```
Computed per architecture per run, from `ResultSink`'s row arrival rate
during `is_burst_period == 1` segments versus `is_burst_period == 0`
segments. **Why novel** (unchanged from dossier Section 10.1): no paper in
the window-size-selection literature reports throughput retention under
varying *system* load, since none of those methods respond to system load at
all.

### 23.2 Window Oscillation Rate (WOR)

```
WOR = AdaptiveWindowController::direction_changes() / run_duration_minutes
```
Directly exposed by the controller (Section 14). A low, stable WOR under
sustained marginal occupancy (occupancy hovering near `occ_high_`) is
evidence the deadband design works; a high WOR indicates thrashing and
should be disclosed as a real finding if observed, not hidden.

### 23.3 Tick-Level F1 (With and Without Point Adjustment — See Section 24)

Ground truth is per-tick (`label ∈ {0,1,2}` from `injection_log.csv`).
Predictions are per-window (`DetectionResult.max_score` thresholded at a
chosen operating point, e.g., the 95th percentile of scores on the calm
training set — same threshold reused across all three architectures for a
fair comparison). A window's binary prediction is propagated to every tick
in `[first_seq, last_seq]` it covers, producing a tick-level predicted-label
series directly comparable to the tick-level ground truth.

### 23.4 Latency-Bounded Accuracy (LBA)

```
LBA = F1 computed only over ground-truth-anomalous ticks whose covering
      window's detection arrived within a fixed SLA (e.g., 100ms of the
      window's last-tick timestamp — recall Section 17.2's stated upper-bound
      latency semantics); ticks detected later than the SLA count as misses
      regardless of eventual correctness.
```
Directly adapted from the BankSentinel research plan's Alert Completion Rate
(ACR) metric (cited in the dossier's Section 10.3), now applied to financial
anomaly detection. This is the metric that fairly penalizes a
fixed-large-window architecture for being "eventually right but
operationally too late" — exactly the failure mode pressure-adaptive sizing
is designed to avoid.

### 23.5 Controller Overhead (Supporting Experiment 5)

```
overhead_ns_per_tick(architecture) = total wall-clock time spent inside
    AdaptiveWindowOp::tick() or DataDrivenWindowOp::tick(), divided by
    total ticks processed, EXCLUDING the time spent in input_->try_pop()
    and output_->try_push() (queue-call time, which is common to both
    and not part of the sizing-logic cost being measured).
```
Measure with `std::chrono::steady_clock` wrapped tightly around just the
sizing-decision branch (the `if (buffer_.count == 0) { ... }` block in
both operators) — not the whole `tick()` body, which would also count
queue-call time common to both architectures and dilute the comparison.

---

## 24. The Point-Adjustment Trap and How This Project Avoids It

This section did not exist in the original dossier and is one of the two
substantive additions this guide makes (the other being the precise
queue-occupancy causal chain in Section 7). It matters because it is exactly
the kind of methodological detail a TAD-literate reviewer checks first.

**The problem, stated precisely** (Kim et al., AAAI 2022): if your
ground-truth anomalies are labeled as *segments* (which yours are — each
injected flash-crash or wash-trade pattern spans 20–80 consecutive ticks),
and your scoring protocol counts a segment as "detected" the moment **any
single tick** inside it is flagged, then F1 scores become severely
optimistic — the paper shows a literal **random anomaly score** can match
state-of-the-art F1 under this protocol, because hitting *at least one* tick
in a 20–80-tick segment by chance is easy.

**What this project does about it — three concrete, mandatory steps:**

1. **Report raw, unadjusted tick-level F1 as the primary number.** No
   segment-level credit. A window's detection only "counts" for the specific
   ticks it covers (Section 23.3) — this is already how `ResultSink`'s
   output is structured, so no special handling is needed beyond *not*
   adding a point-adjustment step in `compute_metrics.py`.
2. **Additionally report PA%K** (Kim et al.'s own proposed corrected
   protocol) at K=20% and K=50%, as a secondary, clearly-labeled number — this
   demonstrates awareness of the standard literature debate without relying
   on the inflated version as your headline claim.
3. **Run the random-baseline sanity check from the paper itself**: score
   every window with a `std::uniform_real_distribution(0,1)` random number
   instead of the Isolation Forest, run it through the exact same evaluation
   pipeline, and confirm its raw (non-point-adjusted) F1 is low and
   near-chance. **If it is not low, your evaluation pipeline has a bug** —
   this check is cheap (minutes of runtime) and is exactly the kind of
   internal-validity safeguard a careful reviewer will ask whether you did.
   Include this as a literal one-paragraph subsection in your paper's
   evaluation section: "As a sanity check following Kim et al. (2022), we
   verified a random-score baseline achieves near-chance F1 under our
   (non-point-adjusted) protocol."

```python
# analysis/compute_metrics.py — relevant excerpt
import numpy as np
import pandas as pd

def tick_level_f1(predictions_df, ground_truth_df, threshold):
    """predictions_df: one row per DetectionResult (window-level).
       ground_truth_df: one row per tick, columns [seq, label]."""
    n_ticks = len(ground_truth_df)
    pred = np.zeros(n_ticks, dtype=bool)
    for _, row in predictions_df.iterrows():
        if row["max_score"] >= threshold:
            pred[int(row["first_seq"]):int(row["last_seq"]) + 1] = True
    truth = (ground_truth_df["label"].values != 0)

    tp = np.sum(pred & truth)
    fp = np.sum(pred & ~truth)
    fn = np.sum(~pred & truth)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall    = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return precision, recall, f1


def pa_k_f1(predictions_df, ground_truth_df, threshold, k_fraction, segments):
    """segments: list of (start_seq, end_seq) ground-truth anomaly segments
       from injection_log.csv. Implements Kim et al. (AAAI 2022) PA%K:
       a segment counts as detected only if at least k_fraction of its
       ticks are individually flagged — NOT just one."""
    n_ticks = len(ground_truth_df)
    raw_pred = np.zeros(n_ticks, dtype=bool)
    for _, row in predictions_df.iterrows():
        if row["max_score"] >= threshold:
            raw_pred[int(row["first_seq"]):int(row["last_seq"]) + 1] = True

    adjusted_pred = raw_pred.copy()
    for (s, e) in segments:
        seg_hits = raw_pred[s:e + 1].mean()
        if seg_hits >= k_fraction:
            adjusted_pred[s:e + 1] = True   # credit the whole segment
        # else: leave as-is (NOT credited) — this is the part naive PA skips
    truth = (ground_truth_df["label"].values != 0)
    tp = np.sum(adjusted_pred & truth)
    fp = np.sum(adjusted_pred & ~truth)
    fn = np.sum(~adjusted_pred & truth)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall    = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return precision, recall, f1


def random_baseline_sanity_check(ground_truth_df, n_windows, window_size, seed=0):
    """Kim et al.'s own recommended check: confirm a random score achieves
       near-chance RAW (non-adjusted) F1 under your pipeline. Run this once
       and report the result in the paper as a methodology footnote."""
    rng = np.random.default_rng(seed)
    fake_scores = rng.uniform(0, 1, size=n_windows)
    # ... wire fake_scores through tick_level_f1 the same way real
    # DetectionResult.max_score values are, confirm F1 stays low (e.g. < 0.15
    # for a 3% base anomaly rate) ...
```

---

## 25. Experiment Design — Five Experiments in Full

All five carry over from the dossier with the protocol details now fully
concrete given Sections 7–24 above.

### Experiment 1 — Window Size Tracks Occupancy (Mechanism Validation)

**Protocol**: run the `adaptive` architecture against a replay CSV with one
clearly demarcated burst region (`is_burst_period == 1` for a contiguous
block). Log, every 100ms, via a lightweight background reporter thread (you
already have `MetricsReporter`'s pattern to copy from, Section 7.7 of the
Implementation Guide): `AdaptiveWindowController::current()`,
`q_win_inf.occupancy()`, and `q_win_inf`'s raw depth.

**Expected finding**: window size visibly shrinks within a small number of
windows after occupancy crosses `occ_high_` (0.70 default), and grows back
after occupancy drops below `occ_low_` (0.30 default), without rapid
oscillation (`direction_changes()` should be low relative to total windows
fired). **This is the figure you generate before making any performance
claim** — it is the proof the causal chain in Section 7.2 actually happens,
not just a story.

### Experiment 2 — Latency Under Burst (Headline Result #1)

**Protocol**: run all three architectures (`fixed`, `datadriven`, `adaptive`)
against the same burst-containing replay, 5 warmup runs + 30 measurement runs
each (Section 27). Compute P50/P95/P99 of `ResultSink`'s `latency_ns` column,
restricted to rows whose `[first_seq, last_seq]` overlaps the burst region.

**Expected finding**: `adaptive` shows materially lower P95/P99 than both
baselines during the burst, since it is the only architecture that responds
to the *consequence* of slow inference (queue backup) rather than to a proxy
for it (volatility) or not at all (fixed).

### Experiment 3 — Accuracy Cost of Adaptation (Headline Result #2 — Report Honestly)

**Protocol**: compute tick-level F1 (Section 23.3, both raw and PA%K) for
all three architectures, separately for calm-period ticks and burst-period
ticks.

**Expected, and required, honest framing**: some F1 degradation for
`adaptive` during the burst (smaller windows → noisier per-window
max-score) is anticipated and **must be reported as a real measured cost**,
not minimized. The paper's claim is a **favorable trade** (bounded latency
for a small, measured accuracy cost), not a free lunch. If `datadriven`
sometimes wins on raw accuracy during bursts, report that too — a result
that engages honestly with a mixed outcome is more credible than one that
only shows favorable comparisons, and is much harder for a reviewer to
poke a hole in.

### Experiment 4 — Sensitivity Sweep (Generalization Check — Not Optional)

**Protocol**: sweep `occ_low_`/`occ_high_` over `{0.2/0.6, 0.3/0.7, 0.4/0.8}`
and `shrink_factor_`/`grow_factor_` over `{0.6/1.1, 0.7/1.15, 0.8/1.2}` — a
3×3 grid, 9 configurations, each run through Experiments 2 and 3's full
protocol. Report how the latency/accuracy Pareto frontier moves across the
grid.

**Why mandatory**: a single tuned operating point is, per Section 6 point 4
and the dossier's own Section 11 risk assessment, "the single most common
weakness reviewers flag in adaptive-systems papers." Showing the
qualitative behavior (shrink-under-load, recover-when-idle, bounded
oscillation) holds across this grid — even if the *exact* Pareto point
moves — is what makes the contribution a mechanism, not a magic number.

### Experiment 5 — Controller Overhead

**Protocol**: using the timing methodology in Section 23.5, measure mean
`overhead_ns_per_tick` for `adaptive` (one `EMAOccupancyTracker::update()`
call plus the `AdaptiveWindowController::update()` branch) versus
`datadriven` (the volatility-fraction computation). Report both numbers and
their ratio.

**Expected finding, substantiating Section 6 point 3's "free signal" claim**:
`adaptive`'s overhead should be near-zero (reading an already-maintained EMA
is one floating-point comparison) while `datadriven`'s is comparable or
slightly higher (still cheap in absolute terms, but not "already being
computed for another purpose" the way occupancy is) — report the actual
measured numbers rather than assuming this without data.

---

## 26. Isolation Forest Validation Plan

**Do this in Week 1, before any KLStream integration work** — discovering a
scoring bug in Week 5 while interpreting Experiment 3's results is far more
costly than catching it now.

```python
# preprocessing/train_forest_reference.py
"""
Trains a reference sklearn IsolationForest on the SAME calm-period feature
CSV the native C++ forest will train on (Section 11's output, filtered to
label==0), with matching hyperparameters (n_estimators=100, max_samples=256,
random_state=42), and writes its anomaly scores on a held-out split to CSV
for direct comparison against the native C++ implementation's output on the
identical held-out points.
"""
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.model_selection import train_test_split

FEATURES = ["log_return", "rolling_vol", "order_imbalance", "spread_bps", "volume"]

df = pd.read_csv("data/replay/replay_AAPL_20120621.csv")
calm = df[df["label"] == 0]
train, holdout = train_test_split(calm, test_size=0.2, random_state=42)

clf = IsolationForest(n_estimators=100, max_samples=256, random_state=42)
clf.fit(train[FEATURES])

# sklearn's score_samples: HIGHER = more normal (opposite sign convention
# from Liu et al.'s raw s(x) formula used in Section 12's C++ code).
# Convert to the SAME convention before comparing: anomaly_score = -score_samples
holdout = holdout.copy()
holdout["sklearn_anomaly_score"] = -clf.score_samples(holdout[FEATURES])
holdout[["log_return","rolling_vol","order_imbalance","spread_bps","volume",
         "sklearn_anomaly_score"]].to_csv(
    "data/replay/isoforest_validation_holdout.csv", index=False)
```

**Validation criterion** (write a small C++ or Python harness that loads
this holdout CSV, runs each row through the native C++ `IsolationForest`
via the same training/scoring path used in production, and checks):

1. **Spearman rank correlation between native-C++ scores and sklearn scores
   on the holdout set ≥ 0.85.** Exact node-by-node tree agreement across two
   different language implementations with independent random splits is
   neither expected nor required — statistical agreement in anomaly
   *ranking* is what matters, since downstream thresholding (Section 23.3)
   only cares about relative ordering.
2. **Native C++ forest's own precision/recall on the synthetic injected
   labels (Section 9) is non-trivial** — e.g., recall ≥ 0.5 at a threshold
   set to the 95th percentile of calm-period scores. This is a sanity check
   on the *whole pipeline* (features → forest → scoring), not just the
   tree-construction code.
3. **Document both numbers in your paper's implementation section** as a
   one-paragraph validation statement — this preempts exactly the kind of
   "did you verify your from-scratch ML code is correct" question a
   reviewer is likely to ask given Section 2's decision to avoid a
   standard ML runtime.

---

## 27. Statistical Rigor — Runs, Warmup, Confidence Intervals

Matches the isolation discipline already established in this project's
BankSentinel benchmarking plan and the original KLStream benchmark
methodology (Section 13 of the Implementation Guide):

- **5 warmup runs, discarded**, then **30 measurement runs** per
  (architecture × load-profile) cell. This applies to Experiments 2, 3, and
  5; Experiment 1 is a single illustrative run (it is a mechanism-validation
  figure, not a statistical claim); Experiment 4's 9-configuration grid
  reuses the same 30-run protocol per cell — budget accordingly in the
  timeline (Section 29), this is the most compute-expensive experiment.
- **One architecture running at a time, never concurrently** — same
  isolation discipline as the BankSentinel plan, to avoid cross-architecture
  resource contention on the M3's shared 8 cores from confounding the
  comparison.
- **Report mean ± 95% confidence interval** (via a simple
  `t.interval(0.95, df=n-1, loc=mean, scale=sem)` in `scipy.stats`,
  `n=30`) for every headline latency/F1 number, not just point estimates —
  this is the difference between a number and a claim a reviewer can assess.
- **Fix the random seed per run index** (run 1 of every architecture uses
  seed 1, run 2 uses seed 2, etc.) so the 30 measurement runs are paired
  across architectures — this lets you additionally report a **paired**
  significance test (e.g., Wilcoxon signed-rank on the 30 paired
  latency-P99 differences between `adaptive` and `fixed`), which is more
  statistically powerful than an unpaired test and directly available given
  this design with no extra runs needed.

---

## 28. Risks and Honest Difficulty Assessment

Carried over from the dossier, updated with this guide's resolutions:

1. **Experiment 3's accuracy cost might not show a clean trade-off.**
   Unchanged risk — budget real interpretation time in Week 5, and recall
   Section 24's framing: a mixed result reported honestly is more credible
   than a clean result that doesn't survive scrutiny.
2. ~~**skl2onnx IsolationForest conversion is a known landmine.**~~
   **Resolved in Section 2** — avoided entirely by going native. No longer a
   live risk for this project; retained here only as a record of why the
   decision was made.
3. **`WindowBatch`'s fixed-array size cap (`MAX_WINDOW_SIZE = 256`,
   Section 13) constrains every window strategy's upper bound.** If Week 3
   tuning of `DataDrivenWindowOp` (Section 15) or further sensitivity
   analysis (Experiment 4) suggests a useful operating point above 256, this
   requires a recompile (changing one `constexpr`), not a redesign — low
   risk, but worth knowing the lever exists.
4. **The Section 17.2 timestamp approximation (window's last-tick time
   stands in for the flagged tick's own time) introduces a small, declared,
   architecture-symmetric upward latency bias.** This is a known, stated
   limitation, not a hidden one — Section 17.2 already specifies the exact
   sentence to put in your limitations section.
5. **Core pinning (P-core/E-core assignment) is not the focus of this
   option** (unlike the runtime-level pinning research direction in the
   original Research Brief) — `main.cpp`'s worker assignment in Section 22
   uses sensible defaults (compute-heavy `InferenceOp` and window stage on
   Performance cores, I/O-boundary `source`/`sink` on Efficiency cores) but
   is not itself an experimental variable here. This makes Option 1
   meaningfully lower-risk on the hardware-behavior axis than a pinning-
   focused paper would be — state this as a scoping decision if asked.
6. **LOBSTER's free tier covers only five tickers and one well-documented
   sample day per the most common citation pattern in the literature.** If
   your specific academic request grants access to a wider date range,
   prefer it — more trading days strengthens generalization claims in
   Experiment 4 — but one day across the five available tickers is
   sufficient for a workshop/short-paper-level contribution; do not let
   broader data access become a blocking dependency (Section 8.3's
   checklist already routes around this).

---

## 29. 8-Week Build Timeline

Refined from the dossier's Section 12, now informed by every concrete
decision in Sections 2–28.

| Week | Tasks |
|---|---|
| **1** | Submit LOBSTER academic request (Day 1). Implement `isolation_forest.hpp` (Section 12) against the synthetic fallback generator (Section 9.4) while waiting. Implement `train_forest_reference.py` and run the validation plan (Section 26) the moment real or synthetic data is available. |
| **2** | Implement `preprocess_lobster.py` (Section 11) end-to-end once real LOBSTER files arrive; confirm output schema and injection rates match Section 9.3's targets. Implement `types.hpp` (Section 13) and the `TumblingCountWindow` four-line modification (Section 16). |
| **3** | Implement `AdaptiveWindowOp`/`AdaptiveWindowController` (Section 14) and `DataDrivenWindowOp` (Section 15); calibrate `vol_low_`/`vol_high_` against the real preprocessed data's distribution. Implement `InferenceOp` (Section 17) and confirm Section 7.2's causal chain empirically (a minimal version of Experiment 1). |
| **4** | Implement `FinancialTickSource` (Section 18) and `ResultSink` (Section 19). Wire the full `main.cpp` (Section 22) for all three architectures. Get one full end-to-end run of each architecture producing a non-empty results CSV. |
| **5** | Implement `compute_metrics.py` including the PA%K protocol and random-baseline sanity check (Section 24). Run Experiments 1–3 at the default configuration (30 runs each per Section 27). Interpret Experiment 3's results honestly, including any unfavorable findings. |
| **6** | Run Experiment 4's 9-configuration sensitivity grid (the most compute-expensive step — start this early in the week). Run Experiment 5's overhead measurement. Begin Introduction + Related Work sections (Section 4 of this guide is your first draft). |
| **7** | Write System Design, Methodology, Results, Discussion sections. Generate all figures (`results_notebook.ipynb`). Get supervisor feedback; revise. |
| **8** | Final polish, IT4D formatting check, submit by Aug 10 (5-day buffer before the Aug 15 deadline). |

---

## 30. Paper Outline and Writing Guidance

A practical section-by-section outline mapped to where the source material
already lives in this document:

1. **Abstract** — the one-sentence pitch (Section 3), compressed to ~150
   words, ending with your two headline numbers once Experiments 2–3 are
   complete (e.g., "...reducing P99 detection latency by X% during bursty
   load at a measured F1 cost of Y%").
2. **Introduction** — open with the Section 4.1 contrast (data-driven vs.
   pressure-driven window adaptation), state the research question (Section
   5) verbatim or near-verbatim, list contributions as: (a) the mechanism,
   (b) the empirical latency/accuracy trade-off characterization, (c) the
   PA%K-aware evaluation methodology.
3. **Related Work** — Section 4's five-plus-two subsections, roughly one
   paragraph each, ending each subsection with the explicit gap sentence
   already drafted there.
4. **System Design** — Section 7 nearly verbatim, including the causal-chain
   diagram (7.1) and the fixed-array design justification (7.3) — reviewers
   of systems papers specifically reward this level of "why this data
   structure" reasoning.
5. **Methodology** — data sourcing and synthetic injection (Sections 8–9,
   with the wash-trading-proxy caveat from 9.2 stated plainly), feature
   engineering (Section 10), the Isolation Forest validation result (Section
   26's two numbers), and the evaluation protocol including PA%K (Section
   24).
6. **Experiments and Results** — Section 25's five experiments in order,
   each with its expected-finding paragraph replaced by your actual
   measured numbers and confidence intervals (Section 27).
7. **Discussion** — the honest accuracy-cost framing (Section 6 point 2,
   Experiment 3's results), the reflexive-feedback-loop caveat from the
   October 2025 flash-crash case study (Section 4.7) as a real-world
   deployment consideration, and explicit scoping limitations (no true wash
   trading, Section 4.7/9.2; the timestamp-approximation latency bias,
   Section 17.2/28 point 4).
8. **Conclusion** — restate the gap (Section 5) as now-filled, one sentence
   on future work (e.g., extending `MAX_WINDOW_SIZE` beyond a compile-time
   constant, or combining with the consistent-hashing operator placement
   direction from the original KLStream Research Brief as a natural next
   paper).
9. **Limitations** — consolidate every caveat already flagged throughout
   this guide (Sections 4.7, 8.2, 9.2, 17.2) into one explicit section
   rather than leaving them scattered — reviewers specifically look for a
   dedicated limitations section in systems papers and its absence reads as
   overclaiming even when individual caveats are mentioned elsewhere.

---

## 31. Full Reference List

Consolidated from the dossier and this guide's additional research,
deduplicated, in citation-ready form.

### Window Size Selection (Data-Driven)
- Ermshaus, A., Schäfer, P., Leser, U. "Window size selection in unsupervised
  time series analytics: A review and benchmark." *International Workshop on
  Advanced Analytics and Learning on Temporal Data*, 2023.
- Papageorgiou, G., Tjortjis, C. "Adaptive Sliding Window Normalization."
  *Information Systems*, vol. 129, March 2025.
- "Time series anomaly detection framework with modified forecasting"
  (AFMF). *ScienceDirect*, 2024.

### Backpressure-Driven Stream Processing
- Xiao, X. "Adaptive sampling-driven workload balancing for distributed data
  stream processing." *ETRI Journal*, 2026. (ASWB.)
- "Hazelcast Jet: Low-latency Stream Processing at the 99.99th Percentile."
  arXiv:2103.10169.
- "Performance Evaluation Analysis of Spark Streaming Backpressure for
  Data-Intensive Pipelines." *Sensors*, 2022.

### Accuracy-Latency Trade-offs in ML Serving
- "One Size Does Not Fit All: Quantifying and Exposing the Accuracy-Latency
  Trade-off in Machine Learning Cloud Service APIs via Tolerance Tiers."
  arXiv:1906.11307, 2019.

### Distributed Elastic Scaling (Scoping Citations)
- "Demeter: Resource-Efficient Distributed Stream Processing under Dynamic
  Loads with Multi-Configuration Optimization." arXiv:2403.02129.
- "Justin: Hybrid CPU/Memory Elastic Scaling for Distributed Stream
  Processing." arXiv:2505.19739.
- "AutoFlow: Hotspot-Aware, Dynamic Load Balancing for Distributed Stream
  Processing." arXiv:2103.08888.

### Time-Series Anomaly Detection Evaluation [NEW]
- Kim, S., Choi, K., Choi, H.-S., Lee, B., Yoon, S. "Towards a Rigorous
  Evaluation of Time-series Anomaly Detection." *AAAI*, 2022.
  (PA%K protocol — Section 24 of this guide.)
- Ghorbani, R., Reinders, M.J.T., Tax, D.M.J. "Towards Unbiased Evaluation
  of Time-series Anomaly Detectors." arXiv:2409.13053, 2024. (Balanced
  point adjustment — optional secondary citation.)

### Isolation Forest
- Liu, F.T., Ting, K.M., Zhou, Z.-H. "Isolation Forest." *IEEE ICDM*, 2008.
  (Original algorithm — Section 12's implementation follows this paper's
  Eq. 1–2 directly.)

### Financial Microstructure / Anomaly Features [NEW]
- Easley, D., López de Prado, M., O'Hara, M. "The Microstructure of the
  'Flash Crash': Flow Toxicity, Liquidity Crashes, and the Probability of
  Informed Trading." *Journal of Portfolio Management*, 2011. (VPIN —
  Section 4.7, 10.)
- "Explainable Patterns in Cryptocurrency Microstructure" (October 10, 2025
  flash crash case study). arXiv:2602.00776. (Reflexive feedback-loop
  caveat — Section 30, Discussion.)
- Rzayev, K., Ibikunle, G. "Order aggressiveness and flash crashes."
  (Order imbalance / bid-ask spread as crash precursors.)

### Wash Trading Detection [NEW]
- "A Midsummer Meme's Dream: Investigating Market Manipulations in the Meme
  Coin Ecosystem." arXiv:2507.01963. (Volume-spike/flat-price proxy
  heuristic — Section 9.2's direct source.)
- "Can AI Detect Wash Trading? Evidence from NFTs." arXiv:2311.18717.
  (Counterparty-identity requirement — Section 4.7's limitation citation.)
- "High-Frequency Market Manipulation Detection with a Markov-modulated
  Hawkes process." arXiv:2502.04027.

### Financial Tick Data Sources [NEW]
- Huang, R., Polak, T. "LOBSTER: Limit Order Book Reconstruction System."
  Humboldt University of Berlin, working paper, 2011. (Section 8.1's exact
  file-format citation.)
- `lobsterdata.com` — academic sample access portal.
- `yfinance` Python package documentation — interval/period limitations
  (Section 8.2).

### KLStream's Own Prior Art (From the Implementation Guide)
- Aldinucci, M., Torquati, M., et al. "FastFlow." *Euro-Par*, 2011.
- Mencagli, G., Torquati, M., et al. "WindFlow." *IEEE TPDS*, 2021.
- Zeuch, S., et al. "Analyzing Efficient Stream Processing on Modern
  Hardware." *VLDB*, 2019.
- Classical AQM literature (RED, CoDel) — cited generically for the
  smoothed-occupancy control-loop design pattern (Section 4.4).

---

## 32. Glossary of New Terms

Extends the Implementation Guide's Section 6 glossary — only terms
introduced by this research extension are listed here.

| Term | Definition |
|---|---|
| **`WindowBatch`** | Fixed-capacity (`MAX_WINDOW_SIZE = 256`), trivially-copyable container holding the `FeatureVector`s collected by one window before scoring. Section 13. |
| **`FeatureVector`** | The 5-dimensional, fixed-layout struct (`log_return`, `rolling_vol`, `order_imbalance`, `spread_bps`, `volume`) every window strategy and the Isolation Forest operate on. Section 10/13. |
| **Target window size `W(t)`** | The size a window operator is currently buffering toward, captured once at window start and held fixed until that window fires. Section 7.2/14. |
| **PATR** | Pressure-Adaptive Throughput Retention — burst-period throughput divided by steady-state throughput. Section 23.1. |
| **WOR** | Window Oscillation Rate — direction changes in window size per minute. Section 23.2. |
| **LBA** | Latency-Bounded Accuracy — F1 restricted to detections arriving within a fixed SLA. Section 23.4. |
| **PA%K** | Kim et al.'s (AAAI 2022) corrected point-adjustment protocol: a ground-truth anomaly segment only counts as detected if at least K% of its ticks are individually flagged. Section 24. |
| **Flash-crash-precursor injection** | Synthetic label-1 anomaly pattern: decaying bid size, occasional bid-price step-downs, modeling pre-crash order-flow-imbalance buildup. Section 9.1. |
| **Wash-trade-proxy injection** | Synthetic label-2 anomaly pattern: volume spike with near-flat price, modeling the observable proxy used in the meme-coin manipulation literature — explicitly **not** verified wash trading (no counterparty data exists in the source data). Section 9.2. |
| **Calm-period training set** | The `label == 0` subset of one preprocessed replay CSV, used to fit the Isolation Forest exactly once, offline. Section 7.5/26. |

---

## 33. Appendix — Task Breakdown for a Coding Agent

A literal, ordered task list, written so a VS Code Copilot agent (or any
other coding agent) can work through this guide mechanically. Each task
names its source section and its file path from Section 20's repository
structure.

```text
[ ] T1.  Implement include/klstream/model/isolation_forest.hpp        (§12)
[ ] T2.  Write preprocessing/train_forest_reference.py                 (§26)
[ ] T3.  Write a synthetic fallback tick generator (no LOBSTER needed)  (§9.4)
         to unblock T1/T2 validation if LOBSTER access is pending
[ ] T4.  Implement preprocessing/preprocess_lobster.py                 (§11)
[ ] T5.  Run preprocess_lobster.py against real LOBSTER files;          (§8, §9)
         verify injection rates and row-count parity
[ ] T6.  Implement include/klstream/window/types.hpp                   (§13)
[ ] T7.  Apply the 4-line Event<T> change to                            (§16)
         include/klstream/operators/window.hpp
[ ] T8.  Add `virtual void attach_metrics(OperatorMetrics*) {}`         (§22 note)
         to include/klstream/core/operator.hpp's IOperator
[ ] T9.  Implement include/klstream/window/adaptive_window_op.hpp      (§14)
[ ] T10. Implement include/klstream/window/data_driven_window_op.hpp   (§15)
[ ] T11. Implement include/klstream/window/inference_op.hpp            (§17)
[ ] T12. Implement include/klstream/window/financial_tick_source.hpp   (§18)
[ ] T13. Implement include/klstream/window/result_sink.hpp             (§19)
[ ] T14. Implement adaptive_window/train_forest.cpp                    (§26)
         (native C++ training entry point + binary serialization,
         loaded by load_forest() in T15)
[ ] T15. Implement adaptive_window/main.cpp                            (§22)
[ ] T16. Implement adaptive_window/CMakeLists.txt; wire into            (§21)
         root CMakeLists.txt via add_subdirectory(adaptive_window)
[ ] T17. Run Validation Plan §26's Spearman-correlation check against
         T2's sklearn reference output — DO NOT PROCEED past this gate
         until correlation >= 0.85
[ ] T18. Implement analysis/compute_metrics.py incl. PA%K and the       (§24)
         random-baseline sanity check
[ ] T19. Implement adaptive_window/harness.cpp                         (§25, §27)
         (drives all 3 architectures x N runs, writes results/raw/*.csv)
[ ] T20. Run Experiment 1, generate the mechanism-validation figure     (§25)
[ ] T21. Run Experiments 2-3 at default config, 30 runs each            (§25, §27)
[ ] T22. Run Experiment 4's 9-cell sensitivity grid                     (§25)
[ ] T23. Run Experiment 5's overhead measurement                        (§25)
[ ] T24. Build analysis/results_notebook.ipynb with all headline figures
[ ] T25. Draft paper/draft.md following §30's outline
```

Tasks T1–T8 have no dependency on real data and can start immediately.
Task T17 is a **hard gate** — its validation criteria (Section 26) exist
specifically so a coding agent does not silently propagate a scoring bug
through twenty subsequent tasks before anyone notices the numbers look
wrong.

---

*End of KLStream-AdaptiveWindow Complete Implementation Guide.*

*This document resolves every open ambiguity in the Option 1 Research
Dossier against the as-built KLStream API, adds the point-adjustment-aware
evaluation methodology the original dossier was missing, and adds the exact
LOBSTER file format, financial-anomaly feature literature, and wash-trading
counterparty-data limitation found through additional research conducted
specifically for this guide. Implementing every section in order, gated at
Task T17, produces a working system, five completed experiments, and a
methodology section a TAD-literate reviewer will not be able to fault on
evaluation-protocol grounds.*
```

# File: KLStream_Complete_Implementation_Guide.md

```markdown
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

```

# File: study.md

```markdown
# KLStream-AdaptiveWindow — Complete Study Guide
### *Prepared for examination readiness and IEEE journal submission*

---

> **How to use this document.** Read it top to bottom once. Every concept builds on the one before it. The document is self-contained — a reader or AI with no prior knowledge of the codebase should be able to understand and recreate every part of the project from this text alone.

---

## SECTION 1 — WHAT IS THIS PROJECT?

**KLStream-AdaptiveWindow** is a research system built in C++17 that asks and answers a specific question about real-time financial data processing:

> *Can a streaming pipeline use its own internal congestion signal — the fill level of an internal queue — to automatically shrink the size of its detection windows when the system is under pressure, so that tail latency is bounded while still processing 100% of incoming data?*

In plain language: imagine a pipe of water flowing through a series of buckets. If the third bucket is nearly full, you could respond by either blocking the pipe (traditional backpressure) or by changing the *size of the scoop* you use to fill it. This project does the second thing — it changes the scoop size.

The system processes financial market data (stock order-book events from NASDAQ), looks for anomalies (flash-crash precursors, suspicious trading patterns) using a machine learning model called an Isolation Forest, and demonstrates that this "scoop-size" approach keeps detection latency short even when the system is under heavy load — at the cost of some detection accuracy.

The code is entirely original C++17, written from scratch, with no external ML libraries. It runs on macOS (Apple Silicon M1/M2/M3) and x86-64 Linux via Docker. It is packaged as a CMake project with GoogleTest unit tests and Google Benchmark microbenchmarks.

---

## SECTION 2 — THE RESEARCH QUESTION

### The Problem
An Isolation Forest needs a *batch* (window) of data points to score anomalies reliably. Bigger windows = better accuracy but more computation per batch. When data arrives very fast ("bursty load"), a large window causes the inference step to fall behind. This fills up the queue between the windowing step and the inference step, which causes even larger tail latencies — a cascading failure.

### Existing Solutions and Their Gap
Prior work adjusts window size based on *data properties* (e.g., increase window when market volatility is high). But these methods are blind to whether the system itself is keeping up. A system can be bottlenecked *without* the data being especially volatile.

### The Novel Mechanism
The project introduces a window controller that watches the fill fraction (occupancy) of the inference operator's *own input queue*, computes an Exponential Moving Average (EMA) of that occupancy, and uses it to:
- **Shrink** the window (multiply current size by shrink_factor < 1) when the EMA exceeds a high threshold (occ_high)
- **Grow** the window (multiply by grow_factor > 1) when the EMA falls below a low threshold (occ_low)
- **Do nothing** when occupancy is in the "deadband" between the two thresholds — this prevents oscillation

This is directly analogous to AIMD (Additive Increase Multiplicative Decrease) congestion control in TCP (Jacobson, 1988) — shrink fast when congested, grow slowly when idle.

### Three Architectures Compared
| Name | Window sizing strategy |
|------|------------------------|
| Fixed | Always w = 128 ticks (no adaptation) |
| Data-Driven | Linear interpolation from market volatility feature |
| Pressure-Adaptive (the new mechanism) | Linear interpolation from EMA queue occupancy |

---

## SECTION 3 — REPOSITORY LAYOUT

```
brolq/
├── CMakeLists.txt               -- Root build file; pulls GoogleTest & Benchmark via FetchContent
├── Dockerfile / docker-compose.yml -- x86 Linux dev for macOS ARM users
├── README.md                    -- Quick-start instructions
├── report.md                    -- Commit history log
├── study.md                     -- THIS FILE
│
├── include/klstream/            -- ALL library code is header-only
│   ├── klstream.hpp             -- Single include-everything header
│   ├── core/                    -- The runtime engine (generic, reusable)
│   │   ├── config.hpp           -- Compile-time constants (cache line, thresholds)
│   │   ├── event.hpp            -- Templated event/message type
│   │   ├── spsc_queue.hpp       -- Lock-free single-producer/single-consumer ring buffer
│   │   ├── mpmc_queue.hpp       -- Lock-free multi-producer/multi-consumer ring buffer
│   │   ├── backpressure.hpp     -- EMAOccupancyTracker + TokenBucketRateLimiter
│   │   ├── operator.hpp         -- IOperator abstract base class + OpStatus enum
│   │   ├── worker.hpp           -- WorkerThread (one OS thread, cooperative round-robin)
│   │   ├── runtime.hpp          -- Runtime coordinator (owns workers, starts/stops)
│   │   ├── metrics.hpp          -- Counter, LatencyHistogram, MetricsReporter
│   │   └── pinning.hpp          -- Apple Silicon QoS thread affinity (CoreAffinity enum)
│   │
│   ├── operators/               -- Generic operator implementations
│   │   ├── source.hpp           -- SourceOperator<T> (generates events from a lambda)
│   │   ├── window.hpp           -- TumblingCountWindow, TumblingTimeWindow
│   │   ├── map.hpp              -- MapOperator (transform T to U)
│   │   ├── filter.hpp           -- FilterOperator (drop events failing a predicate)
│   │   ├── sink.hpp             -- SinkOperator (consumes, does not produce)
│   │   └── aggregate.hpp        -- AggregateOperator
│   │
│   ├── window/                  -- Application-specific operators for this research
│   │   ├── types.hpp            -- FeatureVector, WindowBatch, DetectionResult structs
│   │   ├── financial_tick_source.hpp -- Reads and replays LOBSTER replay CSV
│   │   ├── adaptive_window_op.hpp    -- THE NEW MECHANISM
│   │   ├── data_driven_window_op.hpp -- Volatility-based baseline
│   │   ├── inference_op.hpp          -- Runs Isolation Forest on each WindowBatch
│   │   └── result_sink.hpp           -- Writes DetectionResult rows to CSV
│   │
│   └── model/
│       └── isolation_forest.hpp -- Full Isolation Forest in C++, no external library
│
├── adaptive_window/             -- The research experiment entry points
│   ├── main.cpp                 -- Wires all operators; the main experiment runner
│   ├── train_forest.cpp         -- Trains and saves the Isolation Forest model
│   └── harness.cpp              -- Orchestrates all experimental runs
│
├── tests/                       -- Unit and integration tests (GoogleTest)
├── benchmarks/                  -- Performance benchmarks (Google Benchmark)
├── data/                        -- forest.bin + replay CSVs
├── results/                     -- All output files, figures, and analysis
│   ├── FINAL_DATA_SUMMARY.md
│   ├── aggregated_results.csv
│   ├── final_aggregate_output.txt
│   ├── inference_scaling.csv
│   ├── raw/                     -- 90 run CSVs (30 per architecture)
│   └── figures/                 -- Pareto scatter, hysteresis loop, scaling plots
│
└── paper/
    └── draft.md                 -- The full IEEE journal paper draft (Markdown, 584 lines)
```

---

## SECTION 4 — THE DATA

### Source: LOBSTER
LOBSTER (Limit Order Book System: The Efficient Reconstructor) is an academic service from Humboldt University Berlin. It reconstructs the full NASDAQ order book from TotalView-ITCH data. The project uses the free academic sample: **AAPL (Apple), June 21, 2012**.

After filtering trading halts (event type 7), the dataset contains **100,000 events**.

### The Replay CSV File
The raw LOBSTER data is preprocessed by a Python script into a CSV with these columns:

| Column | Meaning |
|--------|---------|
| seq | Monotonically increasing sequence number |
| timestamp_ns | Nanoseconds since epoch (original LOBSTER timestamp) |
| mid_price | (bid + ask) / 2 |
| log_return | ln(mid_t / mid_{t-1}) — price change magnitude |
| rolling_vol | EMA of log_return^2, alpha=0.05 — volatility proxy |
| order_imbalance | (bid_size - ask_size) / (bid_size + ask_size) |
| spread_bps | 10000 x (ask_price - bid_price) / mid_price |
| volume | ln(1 + bid_size + ask_size) |
| label | 0=normal, 1=flash-crash precursor, 2=wash-trade proxy |
| is_burst_period | 1 during injected anomaly, 0 otherwise |

### Anomaly Injection
Because the June 21, 2012 sample is a calm trading day with no documented real anomalies, anomalies are **synthetically injected**:
- **Flash-crash precursors** (label=1): bid-side decay, spread widening, one-sided executions — modeled on Easley et al. 2011
- **Wash-trading proxy** (label=2): volume spike with flat price — from meme-coin manipulation literature

3% of events are anomalous, split evenly, in **60 injected segments** of roughly 50 events each.

**Honest limitation explicitly stated in the paper:** wash-trading detection from LOBSTER data is a "stylized proxy" — LOBSTER has no counterparty identity, so actual wash trading cannot be verified.

---

## SECTION 5 — THE CORE RUNTIME

The core runtime (`include/klstream/core/`) is a general-purpose stream processing engine. It knows nothing about financial data or anomaly detection.

### 5.1 config.hpp — Global Constants

```cpp
// Cache line size varies by CPU
#if defined(__aarch64__)
  inline constexpr std::size_t CACHE_LINE_SIZE = 128;  // Apple M1/M2/M3
#else
  inline constexpr std::size_t CACHE_LINE_SIZE = 64;   // Intel/AMD x86
#endif

inline constexpr std::size_t DEFAULT_QUEUE_CAPACITY = 4096;  // power of 2
inline constexpr double BP_SOFT_THRESHOLD = 0.70;  // start throttling
inline constexpr double BP_HARD_THRESHOLD = 0.95;  // block immediately
inline constexpr int SPIN_BEFORE_YIELD  = 64;
inline constexpr int YIELD_BEFORE_SLEEP = 32;
inline constexpr int SLEEP_NS           = 100;     // 100 nanosecond sleep
inline constexpr int METRICS_INTERVAL_SEC = 1;
inline constexpr std::size_t HISTOGRAM_BUCKETS = 10000;  // 1 us per bucket
inline constexpr std::size_t MAX_LATENCY_US    = 10000;  // 10 ms max
```

**Why cache-line alignment matters:** Modern CPUs load memory in 64/128-byte "cache lines." If two threads share a variable in the same cache line, every write by one invalidates the other's cache — called "false sharing," extremely expensive. By placing each atomic on its own cache line with `alignas(CACHE_LINE_SIZE)`, threads never interfere.

### 5.2 event.hpp — The Atom of Data

Every piece of data flowing through the pipeline is wrapped in an `Event<Payload>`:

```cpp
template <typename Payload>
struct Event {
    std::uint64_t timestamp_ns;  // monotonic clock, set at creation
    std::uint64_t key;           // routing/grouping key
    std::uint64_t seq;           // sequence number (monotonically increasing)
    Payload       data;          // the actual content (MUST be trivially copyable)
};
```

**Key design decisions:**
- Payload must be **trivially copyable** — no std::vector, no std::string, no virtual functions, no reference-counted pointers. The lock-free queue copies data with `=` directly. Internal pointers would break under multi-threaded copying without synchronization.
- `timestamp_ns` uses `std::chrono::steady_clock` — monotonic, never goes backward. Latency = `now_ns - timestamp_ns` at the sink.
- The factory `Event<T>::make(data, key, seq)` timestamps at creation. Intermediate operators pass the timestamp through unchanged.
- `latency_ns()` computes elapsed time since creation: `(now >= timestamp_ns) ? (now - timestamp_ns) : 0`

### 5.3 spsc_queue.hpp — Lock-Free SPSC Ring Buffer

The most performance-critical data structure. **Single-Producer Single-Consumer (SPSC)** bounded ring buffer using atomic operations instead of mutexes.

**Ring buffer mechanics:** An array of `T` with capacity = power of 2. Two atomic indices:
- `write_idx_` — where the next push writes. Only the producer modifies this.
- `read_idx_` — where the next pop reads. Only the consumer modifies this.

Wrapping uses bitmasking: `(idx + 1) & (capacity - 1)` — faster than modulo.

**The cached-index trick (eliminates false sharing):**
```
Producer side:
  write_idx_      (cache line A) -- producer writes, consumer reads occasionally
  write_idx_cached_ (cache line B) -- producer's shadow of read_idx_; rarely refreshed

Consumer side:
  read_idx_       (cache line C) -- consumer writes, producer reads occasionally
  read_idx_cached_ (cache line D) -- consumer's shadow of write_idx_; rarely refreshed
```

Each is on its own cache line via `alignas(CACHE_LINE_SIZE)`. In the fast path (queue neither full nor empty), the producer reads only its own write_idx_ and its local cached copy of read_idx_. It never touches the consumer's cache line. This eliminates inter-thread cache-line ping-pong (the dominant cost in naive implementations).

**Memory ordering for correctness:**
- `try_push`: writes data to `buffer_[wi]`, then stores `write_idx_` with `memory_order_release`. This ensures the consumer cannot see the new index without also seeing the data that was written.
- `try_pop`: loads `write_idx_` with `memory_order_acquire` to synchronize with the producer's release. Then reads data, then stores new `read_idx_` with release.

**Blocking push** (for blocking use cases) applies a three-tier backoff:
1. `pause`/`yield` instruction (ARM `yield`, x86 `pause`) — hints CPU to reduce pipeline pressure while spinning
2. `std::this_thread::yield()` — give up OS time slice
3. `std::this_thread::sleep_for(100ns)` — genuinely sleep

**Design inspiration:** Documented in comments as "rigtorp-style" after Erik Rigtorp's public SPSC queue design. The implementation is original (written from scratch), not a copy.

### 5.4 mpmc_queue.hpp — Multi-Producer/Multi-Consumer Queue

For cases where multiple threads push or pop concurrently. Uses **sequence numbers per slot**:

```cpp
struct Slot {
    alignas(CACHE_LINE_SIZE) std::atomic<size_t> seq;
    T data;
};
```

State encoding:
- `seq == slot_index` → slot is empty (producer can claim it)
- `seq == slot_index + 1` → slot is filled (consumer can take it)

A producer reads `enqueue_pos_`, then does a CAS (compare-and-swap) to claim the slot. If CAS fails, another producer got it; retry with the new position. Once claimed, write data then set `seq = pos + 1` (release ordering) to signal consumer.

**Design inspiration:** Documented in comments as "Dmitry Vyukov-style" after his public lock-free MPMC design. Implementation is original.

**Note:** In the actual research pipeline, only SPSCQueue is used between adjacent operators (each pair is exactly one producer and one consumer thread).

### 5.5 backpressure.hpp — EMA Tracker + Token Bucket

**EMAOccupancyTracker<Queue>:** wraps any queue with an `occupancy()` method:
```
EMA_new = alpha * occupancy + (1 - alpha) * EMA_old
```
Default alpha = 0.10. Methods:
- `update()` — refresh EMA (call once per tick)
- `ema()` — current EMA value [0, 1]
- `soft_pressure()` — ema() > 0.70
- `hard_pressure()` — occupancy() > 0.95 (checked without EMA for immediacy)

**TokenBucketRateLimiter:** tokens accumulate at a configured rate (tokens/sec). Each event emission consumes one token. When empty, `try_consume()` returns false and the source pauses. Provides smooth output with burst absorption. The source uses this for optional rate capping.

### 5.6 operator.hpp — The Universal Operator Interface

```cpp
enum class OpStatus : uint8_t {
    Processed = 0,  // One event processed successfully
    Idle      = 1,  // No input available
    Blocked   = 2,  // Could not push to output queue (it's full)
};

class IOperator {
public:
    virtual void     init()     {}  // called once before first tick()
    virtual OpStatus tick() = 0;    // called repeatedly — the hot loop
    virtual void     shutdown() {}  // called once at stop; flush/close files
    virtual void     attach_metrics(OperatorMetrics*) {}
    const std::string& name() const;
    std::uint64_t id = 0;  // assigned by Runtime at registration
};
```

**The Blocked contract is critical:**
When `tick()` returns `Blocked`, the operator MUST:
1. Store the un-pushed event in `pending_` internally
2. On the next `tick()`, retry pushing `pending_` WITHOUT popping a new input event

This "at-most-once-pop" guarantee ensures no data is ever lost. If you popped from input but couldn't push to output, you will eventually push that event — even if it takes many ticks.

### 5.7 worker.hpp — Cooperative Worker Thread

One OS thread (`std::thread`) owning a list of `IOperator*`. Runs cooperative round-robin:

```
while (running):
    any_progress = false
    for each operator in assigned list:
        status = operator.tick()
        if status == Processed: any_progress = true
    if not any_progress:
        if idle_rounds < 64:   spin with pause/yield instruction
        elif idle_rounds < 96: std::this_thread::yield()
        else:                  sleep_for(100ns)
        idle_rounds++
    else:
        idle_rounds = 0
```

**Why cooperative:** Operators voluntarily yield by returning from `tick()`. No OS preemption. Related operators on the same thread share L1 cache and avoid context-switch overhead.

**Backoff hierarchy prevents 100% CPU burn:**
- First 64 rounds idle: spin with ARM `yield` / x86 `pause` (~1 cycle hint)
- Next 32 rounds: `this_thread::yield()` (give up time slice)
- Then: 100ns sleep (genuinely yield to OS)

### 5.8 runtime.hpp — The Top-Level Coordinator

```cpp
Runtime rt;
rt.add_worker(CoreAffinity::Performance);  // Worker 0
rt.add_worker(CoreAffinity::Performance);  // Worker 1
rt.add_worker(CoreAffinity::Performance);  // Worker 2
rt.add_worker(CoreAffinity::Efficiency);   // Worker 3

rt.register_op(&source,    0);  // source on worker 0
rt.register_op(&window_op, 1);  // window on worker 1
rt.register_op(&inference, 2);  // inference on worker 2 (heaviest)
rt.register_op(&sink,      3);  // sink on worker 3 (lightweight)

rt.metrics().add(&m_source);
rt.start();
rt.wait_for(std::chrono::seconds(60));  // blocks main thread
rt.stop();                              // joins all worker threads
```

`wait_for()` simply calls `std::this_thread::sleep_for()`. Workers run in background. `stop()` sets each worker's `running_` to false and calls `thread_.join()`.

### 5.9 metrics.hpp — Performance Measurement

**Counter:** cache-line-aligned atomic uint64_t. Incremented with `memory_order_relaxed` (no fence, cheapest). `reset()` atomically swaps to 0 and returns the old value for per-interval rate computation.

**LatencyHistogram:** 10,001 atomic counters, one per microsecond bucket. `record(latency_ns)` divides by 1000 to get microseconds, increments that bucket. `percentile(pct)` iterates to find the target cumulative count — giving p50, p95, p99, etc.

**MetricsReporter:** background thread waking every 1 second to print a formatted table of events/sec, blocked/sec, idle/sec for each registered operator.

### 5.10 pinning.hpp — CPU Core Affinity

Apple Silicon CPUs have Performance cores (~4 GHz) and Efficiency cores (~2.75 GHz). By setting the thread's QoS class, macOS biases it toward P-cores or E-cores:

```cpp
enum class CoreAffinity { Any, Performance, Efficiency };

void apply_affinity(CoreAffinity affinity) {
    // Performance → QOS_CLASS_USER_INTERACTIVE → P-core preference
    // Efficiency  → QOS_CLASS_BACKGROUND       → E-core preference
    // Any         → do nothing (OS decides)
}
```

On non-Apple platforms, this entire function is a compile-time no-op (`#if defined(__APPLE__)`). The code compiles and runs correctly on x86 Linux inside Docker.

---

## SECTION 6 — THE GENERIC OPERATORS

### 6.1 source.hpp — SourceOperator<T>

No input queue. Generates events from a user-supplied generator lambda:
```cpp
using Generator = std::function<bool(Event<T>& out, uint64_t seq)>;
```
Returns true if it produced an event, false if exhausted/throttled.

Each tick(): check hard/soft pressure → check rate limiter → retry pending if any → call generator → try to push → handle blocked.

### 6.2 window.hpp — TumblingCountWindow and TumblingTimeWindow

**TumblingCountWindow<T, Out>:** collects events until `window_size` accumulated, calls aggregation lambda → emits one `Event<Out>` → clears buffer. Uses `std::vector<Event<T>>` (not fixed-array — this operator doesn't need to cross SPSC boundaries as a payload).

**TumblingTimeWindow<T, Out>:** fires every `window_duration` nanoseconds. Checks `steady_clock::now()` on every tick. Used in the Yahoo Streaming Benchmark example, not the research pipeline.

Both implement the Blocked contract with a `pending_` field.

### 6.3 map.hpp, filter.hpp, sink.hpp

Standard stateless operators:
- **MapOperator<In, Out>:** applies `std::function<Out(In)>` to transform each event
- **FilterOperator<T>:** drops events failing the predicate; returns Processed without pushing
- **SinkOperator<T>:** consumes events, never pushes; calls user lambda for each event

---

## SECTION 7 — THE APPLICATION LAYER

### 7.1 types.hpp — FeatureVector, WindowBatch, DetectionResult

**FeatureVector — exactly 5 floats (20 bytes), trivially copyable:**
```cpp
struct FeatureVector {
    float log_return;
    float rolling_vol;
    float order_imbalance;
    float spread_bps;
    float volume;  // log1p-scaled
    static constexpr size_t kDim = 5;
    std::array<float, kDim> to_point() const { ... }
};
static_assert(sizeof(FeatureVector) == 5 * sizeof(float));  // no padding
```

**WindowBatch — fixed-capacity, trivially copyable:**
```cpp
struct WindowBatch {
    std::array<FeatureVector, 256> points{};
    uint32_t count = 0;
    uint64_t first_seq = 0;
    uint64_t last_seq  = 0;
};
static_assert(std::is_trivially_copyable_v<WindowBatch>);
```
Cannot use std::vector because WindowBatch must be trivially copyable to cross SPSCQueue boundaries. std::vector has internal heap pointers; copying without its copy constructor would corrupt memory.

**DetectionResult — one result per window:**
```cpp
struct DetectionResult {
    double   max_score;              // highest anomaly score in window
    uint32_t window_size_used;       // how many points were in this batch
    uint64_t first_seq;              // window start sequence number
    uint64_t last_seq;               // window end sequence number
    uint64_t flagged_seq;            // tick with max_score
    float    occupancy_at_decision;  // EMA reading at window start (adaptive only)
};
```

### 7.2 financial_tick_source.hpp — Replaying LOBSTER Data

**load_replay_csv(path):** loads the entire replay CSV into a `std::vector<TickRow>` at startup. LOBSTER days have at most a few hundred thousand events — fits in RAM. This makes tick() completely allocation-free in the hot loop.

**FinancialTickSource:** a callable object that wraps the loaded data. Two replay modes:
- `MaxRate` — emit as fast as downstream can accept (used in experiments)
- `PreserveTiming` — sleep between events to match original LOBSTER inter-event gaps

The source loops the dataset repeatedly. At each loop restart, `base_seq_` is incremented by the last seq + 1 to avoid sequence number collisions across loops.

### 7.3 adaptive_window_op.hpp — THE NEW MECHANISM

**AdaptiveWindowController — pure control logic (testable in isolation):**

Parameters:
- w_min, w_max — minimum and maximum window size (16 and 256 in experiments)
- occ_low, occ_high — occupancy thresholds defining the deadband
- shrink_factor — multiply current window by this when occupancy is high (< 1)
- grow_factor — multiply current window by this when occupancy is low (> 1)

```cpp
uint32_t update(double ema_occupancy) {
    if (ema_occupancy > occ_high) {
        current_w = max(w_min, uint32_t(current_w * shrink_factor));
        shrink_events_++;
    } else if (ema_occupancy < occ_low) {
        current_w = min(w_max, uint32_t(current_w * grow_factor));
        grow_events_++;
    }
    // deadband: do nothing (anti-oscillation — this "else" branch is the mechanism)
    track_direction(ema_occupancy);
    return current_w;
}
```

The controller also tracks direction_changes — every time control flips from "was growing" to "now shrinking" or vice versa. This is WOR (Window Oscillation Rate).

**AdaptiveWindowOp — implements IOperator:**

Contains: input/output SPSCQueues, AdaptiveWindowController, EMAOccupancyTracker watching its OWN output queue, a WindowBatch buffer.

The tick() logic:
1. If has_pending_ → try to push pending batch → return Processed or Blocked
2. If buffer is empty (start of new window):
   - Call tracker_.update() to refresh EMA
   - Call controller_.update(tracker_.ema()) to get new target window size
   - Record overhead timing of this call
3. Try to pop one event from input → if empty → return Idle
4. Add event to buffer
5. If buffer has reached target_w_: package as WindowBatch, push to output; handle Blocked
6. Else → return Processed (still filling)

**KEY INSIGHT:** Window size is captured ONCE at window start and never changes mid-window. This is the "shrink for FUTURE windows" rule. Changing mid-fill would produce inconsistent batches.

### 7.4 data_driven_window_op.hpp — Volatility-Based Baseline

Same structure as AdaptiveWindowOp but reads the `rolling_vol` field from the last received FeatureVector instead of queue occupancy:

```cpp
float frac = clamp((vol - vol_low) / (vol_high - vol_low), 0, 1);
target_w = w_max - frac * (w_max - w_min);
```

Low volatility → w_max = 256. High volatility → w_min = 16. Linear interpolation.

Thresholds: vol_low = 8.98e-9 (25th percentile), vol_high = 1.52e-8 (95th percentile) — calibrated from the calm portion of the dataset.

### 7.5 inference_op.hpp — Running the Isolation Forest

Pops a WindowBatch, scores all points, finds max_score:

```cpp
double max_score = -1.0;
uint32_t max_idx = 0;
for (uint32_t i = 0; i < wb.count; ++i) {
    double s = forest->anomaly_score(wb.points[i].to_point());
    if (s > max_score) { max_score = s; max_idx = i; }
}
```

This is O(W * n_trees * log(psi)) = O(W) for fixed forest parameters. This is the bottleneck that scales with window size and justifies the control mechanism.

The output event's timestamp is set to `in_ev.timestamp_ns` — the timestamp when the LAST event of the window arrived. This is documented as a **conservative upper bound on latency** (slightly pessimistic, never optimistic). Per-point timestamps are not stored in WindowBatch (FeatureVector is exactly 5 floats for cache efficiency).

### 7.6 result_sink.hpp — Writing Output CSV

Pops DetectionResult events, writes one CSV row per window:
```
seq, detect_timestamp_ns, latency_ns, max_score, window_size_used,
first_seq, last_seq, flagged_seq, occupancy_at_decision
```

Does NOT compute F1, precision, recall, or any evaluation metric — that is done offline in Python. This keeps the hot C++ path free of evaluation logic.

---

## SECTION 8 — THE ML MODEL: ISOLATION FOREST

### 8.1 isolation_forest.hpp

The complete Isolation Forest in ~240 lines of C++.

**Theory (Liu, Ting & Zhou, 2008):**
Anomalies are rare and different — they get isolated by random partitioning after very few splits. Normal points need many splits. The anomaly score:

```
s(x, psi) = 2 ^ (-E[h(x)] / c(psi))
```

Where:
- E[h(x)] = average path length across all trees to isolate point x
- c(psi) = expected path length for unsuccessful BST search in sample size psi
- psi = sub-sample size per tree = 256

Score → 1.0 = anomalous (short paths); Score → 0.5 = normal; Score < 0.5 = very normal.

The c(n) function (Liu et al. 2008, Eq. 2):
```cpp
static double c_factor(int n) {
    if (n <= 1) return 0.0;
    if (n == 2) return 1.0;
    const double EULER_GAMMA = 0.5772156649015329;
    return 2.0 * (log(n - 1) + EULER_GAMMA) - 2.0 * (n - 1) / n;
}
```

**IsolationTree<D> — stored as FLAT ARRAY for cache locality:**
```cpp
struct Node {
    int   feature   = -1;  // -1 = leaf
    float split     = 0.0f;
    int   left      = -1;  // index into nodes_[] array
    int   right     = -1;
    int   size_at_leaf = 0;  // for c(n) correction at height limit
};
std::vector<Node> nodes_;
int root_ = -1;
```

Flat array instead of pointer-linked tree: all nodes are contiguous in memory → cache-friendly during the scoring hot path (InferenceOp calls path_length() up to 256 times per tick).

**Building:** randomly pick a feature, find its min/max in current subset, pick a random split between them, partition, recurse. Up to 8 attempts to find a feature with non-degenerate range. Stop at `height_limit = ceil(log2(psi))` or when only 1 point remains.

**IsolationForest<D> — ensemble of 100 trees:**
```cpp
double anomaly_score(const Point& x) const {
    double total = 0.0;
    for (const auto& tree : trees_) total += tree.path_length(x);
    return std::pow(2.0, -total / trees_.size() / c_psi_);
}
```

Training: sampling without replacement per tree (shuffle index array, take first psi). Fixed seed=42 for reproducibility.

**Serialization:** binary format — raw bytes of all Node structs. Load and save in ~15 lines. No JSON, no text parsing overhead. `data/forest.bin` = 320 KB.

**Validation:** C++ vs. sklearn: Spearman rho = 0.947 on a holdout set.

### 8.2 train_forest.cpp

Standalone program:
1. Read `isoforest_validation_train.csv` (calm-period rows only)
2. Train IsolationForest<5> with n_estimators=100, psi=256
3. Save to `data/forest.bin`
4. Score holdout set, save scores to `isoforest_validation_cpp_scores.csv`

Python then computes Spearman correlation between these C++ scores and sklearn scores.

---

## SECTION 9 — EXPERIMENT DRIVER

### 9.1 main.cpp — The Wiring Code

Command-line flags:
| Flag | Default | Effect |
|------|---------|--------|
| --architecture= | adaptive | fixed / datadriven / adaptive |
| --replay= | data/replay/replay_AAPL_20120621.csv | Data file |
| --forest= | data/forest.bin | Pretrained model |
| --out= | results/raw/run.csv | Output CSV |
| --duration= | 60 | Run seconds |
| --occ_low= | 0.30 | Controller threshold |
| --occ_high= | 0.70 | Controller threshold |
| --shrink= | 0.70 | Shrink factor |
| --grow= | 1.15 | Grow factor |

Queue sizes:
- q_src_feat: 4096 events — source to window stage
- q_win_inf: **64 events** — window to inference (THE CONGESTION POINT; small by design)
- q_inf_snk: 4096 events — inference to sink

With window size 256, the 64-slot queue holds only ~16 full batches. This creates realistic pressure.

Thread assignment:
- Worker 0 (P-core): TickSource
- Worker 1 (P-core): Window operator
- Worker 2 (P-core): InferenceOp (heaviest compute)
- Worker 3 (E-core): ResultSink (lightweight I/O)

An occupancy logger background thread (for adaptive only) writes `(time_ms, window_size, occupancy, raw_depth)` every 100ms to `results/raw/occupancy_log.csv` — the raw data for the hysteresis loop figure.

### 9.2 harness.cpp — The Experiment Orchestrator

Launches the experiment binary via `system()` calls:
1. Experiment 1: 1 run of adaptive (5 seconds) — mechanism validation
2. Experiments 2, 3, 5: For each of {fixed, datadriven, adaptive}:
   - 5 warmup runs (5 seconds each) — let caches stabilize
   - 30 measurement runs (5 seconds each) — the actual data

Result files: `warmup_{arch}_{i}.csv` and `run_{arch}_{i}.csv`
Total: 5+30 runs × 3 architectures = 105 runs

---

## SECTION 10 — THE BUILD SYSTEM

CMake 3.17+, C++17 standard.

The library is **header-only**: CMake defines `klstream` as an `INTERFACE` library. Linking against `klstream::klstream` just adds `include/` to the include path — no `.a` or `.so` built.

External dependencies (auto-fetched by CMake FetchContent):
- GoogleTest v1.14.0 — unit testing
- Google Benchmark v1.8.4 — microbenchmarks

Platform-specific optimizations:
- Apple Silicon: tries -mcpu=apple-m3, falls back through m2, m1, -march=native
- x86: -march=native
- Release: -O3 -mcpu=... -DNDEBUG
- Debug: -O0 -g3

Sanitizer support:
- -DKLSTREAM_TSAN=ON → ThreadSanitizer
- -DKLSTREAM_ASAN=ON → AddressSanitizer

---

## SECTION 11 — EXPERIMENTAL RESULTS

### 11.1 Experiment 1: Controller Dynamics (60-second isolated run)

**Method:** Run adaptive at speed_factor=1460x, log occupancy and window size every 100ms.

**Findings:**
- System spends **92.1%** of wall-clock time completely drained (occupancy ~0), running at w_max=256
- When a burst arrives, occupancy spikes to **0.984** (63/64 of 64-slot queue)
- Controller immediately drops to **w_min=16**
- Within ~600ms, occupancy returns to 0 and window grows back to 256
- Only **4.6%** of wall-clock time above occ_high=0.7

**Relay-limit-cycle behavior (Astrom & Murray, 2021):** The controller behaves as a binary relay (on-off controller), not a proportional regulator. It does not try to stabilize occupancy at 0.5 — it latches to w_min during bursts and returns to w_max otherwise.

**Window Oscillation Rate (WOR):**
- 60-second dedicated run: 16 direction changes/minute
- 30-run ensemble (10s each): mean = 48.3 transitions/min, std = 64.0, range 6–276
- High variance is a reportable finding: oscillation is highly sensitive to OS scheduling noise

### 11.2 Experiments 2 & 3: Main Accuracy–Latency Evaluation (30 runs each)

All runs at speed_factor=1460x, 5 seconds each, 30 measurement runs per architecture.

| Metric | Fixed (w=128) | Data-Driven | Adaptive |
|--------|--------------|-------------|----------|
| Raw F1 | **0.1645** ± 0.0000 | 0.1616 ± 0.0011 | 0.1054 ± 0.0184 |
| PA%20 F1 | **0.2096** ± 0.0000 | 0.1805 ± 0.0012 | 0.1135 ± 0.0237 |
| Range-Precision | 0.1374 | 0.1180 | 0.0632 |
| Range-Recall | 0.2003 | 0.2041 | **0.4944** |
| Range-F1 | 0.1630 | 0.1495 | 0.1077 |
| LBA@10ms | 0.1583 ± 0.0212 | 0.1169 ± 0.0596 | 0.0944 ± 0.0316 |
| LBA@25ms | 0.1644 ± 0.0001 | 0.1390 ± 0.0392 | 0.1030 ± 0.0271 |
| LBA@50ms | **0.1645** ± 0.0000 | 0.1547 ± 0.0151 | 0.1053 ± 0.0189 |
| P50 latency | **0.97 ms** | 41.53 ms | 17.65 ms |
| P95 latency | 44.87 ms | 78.30 ms | **19.00 ms** |
| P99 latency | 56.74 ms | 96.76 ms | **23.49 ms** |
| Max latency | 410.78 ms | 265.94 ms | **141.14 ms** |

**Statistical significance (Wilcoxon signed-rank, paired, n=30):**
- All F1 comparisons (adaptive vs fixed, adaptive vs datadriven): p < 10^-9
- LBA@10ms adaptive vs. datadriven: p = 0.0577 (NOT significant at α=0.05 — the only exception)

**Key narratives:**
1. **Latency win:** Adaptive P95 (19.0ms) is 2.4x lower than Fixed (44.9ms) and 4.1x lower than Data-Driven (78.3ms)
2. **F1 cost:** Adaptive PA%20 F1 (0.114) is 46% lower than Fixed (0.210) — large, honest, statistically significant
3. **Data-Driven paradox:** Data-Driven EXPANDS windows during high volatility. Volatility bursts often overlap with system load. So data-driven makes the bottleneck WORSE. P95 = 78.3ms, worse than Fixed's 44.9ms.
4. **Why F1 drops so much:** ~85% of events arrive during burst periods (high-rate by definition). During bursts, controller uses w_min=16. Small windows produce noisier scores failing the PA%20 threshold (need ≥20% of ticks individually flagged). F1 loss is primarily recall loss — Range-Recall actually RISES to 0.494 (2.5x Fixed's 0.200).

### 11.3 Experiment 4: Sensitivity Sweep (9 cells × 30 runs = 270 runs)

Grid: occ_low ∈ {0.2, 0.3, 0.4}, occ_high ∈ {0.6, 0.7, 0.8}, shrink ∈ {0.6, 0.7, 0.8}, grow ∈ {1.1, 1.15, 1.2}

Run at MODERATE load (speed_factor=150x) to observe non-saturated behavior.

**Finding: The tradeoff is structural and unavoidable.**
Relaxing any parameter (e.g., higher occ_high, smaller shrink) recovers some F1 but destroys the latency guarantee. The paper states: "You cannot tune your way out of it."

Best config: occ_low=0.3, occ_high=0.7, shrink=0.8, grow=1.2 → PA%20 F1=0.159, P95=11.1ms.
Worst config: occ_low=0.3, occ_high=0.7, shrink=0.6, grow=1.1 → PA%20 F1=0.100, P95=210.5ms.

### 11.4 Experiment 5: Controller Overhead

| Architecture | Control overhead |
|---|---|
| Data-Driven (volatility read + interpolation) | 21.84 ns/call |
| Pressure-Adaptive (queue occupancy EMA + update) | 21.15 ns/call |

Both sub-22 ns — essentially free relative to inference cost (~2,000–3,000 µs per window).
**No efficiency advantage is claimed** for the pressure-adaptive signal. Both signals have indistinguishable overhead.

### 11.5 Inference Scaling Validation

Measurement: end-to-end inference time for W ∈ {16, 32, 64, 128, 256}.

| W | Mean (ns) | Std (ns) |
|---|-----------|----------|
| 16 | 2,027,875 | 60,615 |
| 32 | 2,042,473 | 38,589 |
| 64 | 2,133,713 | 46,301 |
| 128 | 2,402,831 | 49,317 |
| 256 | 2,850,054 | 54,074 |

Linear fit: `time_ns = 4119 * W + 2,224,749`, R^2 = 0.984 (see Note A-1 in Report A — the abstract claims 0.9953, which differs from this data).

The per-point-per-tree cost: ~41 ns (slope 4119 ns / 100 trees = 41 ns/point/tree).

---

## SECTION 12 — THE PAPER

`paper/draft.md` is 584 lines covering:
1. Abstract — all key numbers (P95, F1 loss, R^2, overhead)
2. Introduction — HFT latency requirements and window-size tension
3. Related Work — ASWB, ASWN, AFMF, Flink, Spark, RED/CoDel, Tolerance Tiers
4. System Design — causal chain, controller params, speed-factor calibration, C++ Isolation Forest motivation
5. Experimental Setup — LOBSTER dataset, 5 features with formulas, anomaly injection, all metrics with mathematical definitions
6. Results — all 5 experiments with tables and nuanced interpretation
7. Discussion — honest treatment of F1 loss, proof tradeoff is structural, all limitations
8. Conclusion
9. References — 10 references (note: some are incomplete — see Report B)

**The paper's headline claims (all verified against raw files):**
- "Bounds P95 to 19.0ms" — true, from aggregated_results.csv
- "F1 reduction statistically significant" — Wilcoxon p < 10^-9, true
- "Inference cost O(W)" — R^2 = 0.984 (see discrepancy note)
- "Controller overhead ~21ns" — from Experiment 5
- "Isolation Forest validated vs sklearn" — Spearman rho = 0.947

---

## SECTION 13 — THE FULL DATA FLOW, END TO END

```
[CSV file on disk: data/replay/replay_AAPL_20120621.csv]
        |
        v
load_replay_csv() --> std::vector<TickRow> (loaded ONCE at startup, all in RAM)
        |
        v
FinancialTickSource (callable, loops through rows at MaxRate)
        |
        v (generates Event<FeatureVector>)
SourceOperator<FeatureVector>  [Worker 0, P-core]
        |
        v  SPSCQueue<Event<FeatureVector>>  capacity=4096
        |
        v
[Window Operator]  [Worker 1, P-core]
        | fixed:      TumblingCountWindow (always w=128)
        | datadriven: DataDrivenWindowOp (reads rolling_vol, linear interp)
        | adaptive:   AdaptiveWindowOp (reads EMA of q_win_inf occupancy)
        |                   ^
        |                   | (reads occupancy of this very queue)
        v  SPSCQueue<Event<WindowBatch>>  capacity=64  <-- THE CONGESTION POINT
        |
        v
InferenceOp  [Worker 2, P-core]
        | scores all W points in batch against IsolationForest<5>
        | finds max_score point
        | creates DetectionResult
        |
        v  SPSCQueue<Event<DetectionResult>>  capacity=4096
        |
        v
ResultSink  [Worker 3, E-core]
        | writes one CSV row per window
        v
results/raw/run_{arch}_{i}.csv

Meanwhile (adaptive only):
OccupancyLogger thread --> results/raw/occupancy_log.csv
  (logs time_ms, window_size, occupancy, raw_depth every 100ms)

After stop():
Python analysis:
  - join run CSVs with injection_log.csv (ground truth)
  - compute F1, PA%20, Range-F1, LBA@T, latency percentiles
  - Wilcoxon signed-rank tests across 30 runs
  - produce aggregated_results.csv and figures (pareto, hysteresis, scaling)
```

---

## SECTION 14 — KEY VOCABULARY

| Term | Definition |
|------|-----------|
| SPSC queue | Single-Producer Single-Consumer ring buffer. Exactly one thread pushes, one pops. Lock-free via atomic indices with cache-line-padded cached shadows. |
| MPMC queue | Multi-Producer Multi-Consumer ring buffer. Multiple threads push/pop concurrently. Uses sequence-number CAS per slot. |
| Backpressure | Feedback where a full downstream queue signals upstream to slow down or stop. |
| EMA | Exponential Moving Average. EMA_new = alpha*sample + (1-alpha)*EMA_old. Smooths noisy signals. |
| OpStatus | Return value of tick(): Processed (made progress), Idle (no input), Blocked (output full). |
| Blocked contract | When tick() returns Blocked, store un-pushed event in pending_ and retry next tick. No data lost. |
| Cache-line alignment | Placing data on its own 64/128-byte boundary to prevent false sharing between threads. |
| False sharing | Two threads modifying unrelated data in the same cache line causes unnecessary cache invalidation. Extremely slow. |
| Cooperative scheduling | Operators voluntarily yield by returning from tick(). No OS preemption. Related operators share L1 cache. |
| Isolation Forest | ML algorithm scoring anomalies by path length in random partition trees. Score approaching 1.0 = anomalous. |
| Window batch | Fixed-size collection of FeatureVectors scored together by InferenceOp. |
| AIMD | Additive Increase Multiplicative Decrease. TCP congestion control. Our controller uses multiplicative both ways but with shrink-fast/grow-slow asymmetry analogous to AIMD. |
| PA%K | Point-Adjust %K protocol (Kim et al. AAAI 2022). A window's detection counts only if >=K% of its individual ticks are flagged above threshold. Prevents F1 inflation. |
| Raw F1 | Standard F1 score on tick-level binary predictions. No point adjustment. |
| Range-F1 | Tatbul et al. 2018. Credit proportional to overlap between predicted and actual anomaly ranges. Threshold-agnostic. |
| LBA@T | Latency-Bounded Accuracy at threshold T ms. F1 computed only for anomalies whose detection arrived within T ms. |
| WOR | Window Oscillation Rate. Direction changes per minute in the control signal. High WOR = thrashing. |
| Relay feedback controller | Binary switch controller (Astrom & Murray, 2021). Switches between two extreme states, forms a limit cycle. |
| LOBSTER | Limit Order Book System: The Efficient Reconstructor. Academic NASDAQ order book data service. |
| Speed factor | Replay acceleration factor. 1460x means 1 second experiment = 1460 seconds of market time. |
| Deadband | The occ_low to occ_high range where the controller does nothing. Prevents oscillation. |
| trivially copyable | C++ type with no user-defined constructors, no virtual functions, no internal pointers. Can be copied with memcpy. Required for lock-free queue payloads. |
| FetchContent | CMake module that downloads and builds GoogleTest and Google Benchmark from source. |
| c(n) factor | Liu et al. 2008 Eq. 2. Expected path length for unsuccessful BST search in n points. Normalizes Isolation Forest scores. |
| height_limit | ceil(log2(psi)). Maximum Isolation Forest tree depth. At this depth, the c(n) correction is added to path length. |

---

## SECTION 15 — IEEE ETHICAL COMPLIANCE & AI DISCLOSURE

### 15.1 Mandatory AI Tool Disclosure

IEEE policy (PSPB Operations Manual Section 8.2.4, effective 2023) requires disclosure of AI tool usage in the Acknowledgments section. AI tools cannot be listed as co-authors.

**Recommended Acknowledgments text:**

"The authors used large language model (LLM) AI assistants (including Google Gemini) during preparation of this manuscript. AI tools were used for: (1) writing assistance and phrasing suggestions for manuscript sections; (2) code scaffolding and review suggestions for the C++ implementation; (3) exploration of related literature and reference identification; (4) analysis and verification of experimental results. All code was reviewed, tested, and validated by the human authors. All experimental data was generated by the authors' own implementation on their own hardware. The authors take full responsibility for all content, claims, and data. AI-generated text was reviewed and edited for accuracy. No AI system is listed as an author, consistent with IEEE policy."

### 15.2 Research Ethics Checklist

- Data provenance: LOBSTER is an established academic resource with documented terms of use. The free academic sample is explicitly intended for research use.
- Anomaly injection transparency: The paper explicitly states anomaly labels are synthetic, wash-trading detection is a "stylized proxy," and the sample is a calm day with no documented real events.
- Limitations section: Section 6.3 honestly discloses narrow calibration window, single replay day/ticker, wash-trading proxy caveat, and timestamp approximation.
- Statistical methodology: 30 paired runs, Wilcoxon signed-rank (non-parametric), PA%20 protocol to prevent F1 inflation — all documented with citations.
- Negative results reported: The F1 loss is reported honestly throughout. The paper does not hide the accuracy cost.
- Code availability: Recommend making the codebase publicly available (e.g., GitHub) for reproducibility.

---

## SECTION 16 — ACADEMIC INTEGRITY REPORT A: SCIENTIFIC RIGOR WEAKNESSES

This section identifies specific places where a peer reviewer will push back, with recommended fixes.

---

### Finding A-1: R-squared Inconsistency Between Paper and Raw Data

**Location:** paper/draft.md Abstract (line 28) and Section 3.2 (lines 182-185); results/FINAL_DATA_SUMMARY.md (line 56); results/inference_scaling.csv.

**Issue:** The paper's abstract states "R^2 = 0.9953" for the inference cost linear fit. FINAL_DATA_SUMMARY.md (line 56) reports "R^2 = 0.984267" and adds the parenthetical "(must be > 0.99 to confirm O(W) claim)." The raw data in inference_scaling.csv computes to R^2 approximately 0.984 when fitted. This is a direct numerical contradiction between the abstract and the supporting data file. The note "must be > 0.99" makes this worse: the document explicitly marks 0.984 as failing its own threshold, yet the paper claims 0.9953, above that threshold.

Furthermore, R^2 = 0.984 for a 5-point linear fit is statistically weaker than it appears. A 5-point fit has 3 degrees of freedom; with so few points, high R^2 is expected even for moderate linearity. The paper should report the fit equation, p-value of the slope, and actual timing measurements.

The paper also says (line 189): "Timings use Python sklearn as a reference implementation; the native C++ forest has different absolute latencies but the same O(W) scaling property." But the scaling plot is presented as validating the C++ pipeline's latency behavior. This conflates sklearn timing with C++ timing.

**Recommended Fix:**
1. Re-run the inference scaling experiment clearly labeled as either C++ or Python sklearn. Report both if needed.
2. Replace R^2 in the abstract with the actual value from the data. If 0.984, say 0.984 everywhere consistently.
3. Report the fit equation with standard error and p-value, noting the small sample size.
4. Consider adding 2-3 more data points (W=48, 96, 192) to strengthen the fit.
5. Remove the internal threshold note from any shared document.

---

### Finding A-2: The Latency Approximation Is Understated as a Limitation

**Location:** paper/draft.md Section 6.3 (lines 525-531); include/klstream/window/inference_op.hpp (lines 52-66).

**Issue:** The timestamp used for latency computation is `in_ev.timestamp_ns` — set by `Event::make()` inside the source's `tick()`. This is the wall-clock time when the source created the event in the pipeline, not the original LOBSTER timestamp. The reported latency is therefore wall-clock pipeline latency at the replayed speed (1460x), not real-market latency.

More critically, per-point timestamps are NOT retained in WindowBatch (FeatureVector is exactly 5 floats by design). The flagged point's "latency" is approximated by the window's last-event creation timestamp — making reported latency a conservative upper bound (slightly pessimistic). This is acknowledged in the code comments but not clearly enough in the paper.

The limitation section says "the latency figures (P95 ~19 ms) reflect the replay's accelerated time, not real-market operational latency." But this is buried in Section 6.3 instead of being stated upfront in Section 4.2 (Metric Definitions) where the reader first encounters latency as a metric.

**Recommended Fix:**
1. Add a paragraph in Section 4.2 explaining exactly what latency measures: wall-clock time from when the source created the event (pipeline entry) to when the sink received the result.
2. Explicitly state that per-point timestamps are not propagated through WindowBatch and that the flagged point's latency is approximated by the window's last-event timestamp — making reported latency a conservative upper bound.
3. For the inference scaling validation: clearly separate C++ native scaling from Python sklearn reference. If values come from Python, label them as reference values, not direct C++ measurements.
4. Move the timestamp approximation caveat from Section 6.3 to Section 4.2 alongside the metric definitions.

---

### Finding A-3: The "85% of Events at w_min" Claim Has No Traceable Data Source

**Location:** paper/draft.md Section 6.1 (lines 494-498).

**Issue:** The paper states "~85% of all events arrive and are evaluated at w_min=16" and attributes this to a "cross-reference of the controller's burst timestamps against the injected anomaly segments." Specific figures "91.5% vs 85.2% for normal ticks" are given. Neither the 85% figure nor the 91.5%/85.2% figures appear in any file in the results directory. There is no analysis script output, no CSV, no table that produces these numbers.

A reviewer who asks for the supporting table will find none. If these numbers come from a one-off analysis that was not saved, they cannot be verified.

**Recommended Fix:**
1. Add a dedicated data analysis step that computes: (a) fraction of events processed at w_min in each 30-run file, and (b) fraction of anomalous vs. normal ticks occurring during burst periods. Save output as results/event_fraction_analysis.csv.
2. Report mean ± std across 30 runs for these figures.
3. Add a footnote or appendix entry referencing this file.
4. If the 85% figure is an estimate or model prediction rather than a measured value, say "estimated" not stated as fact.

---

### Finding A-4: The Default Parameters Are Inconsistent Between Paper, Code, and Experiments

**Location:** paper/draft.md Table 1 in Section 3.3 (lines 197-206); adaptive_window/main.cpp (lines 44-47); results/preflight_verification.txt (lines 21-24); results/FINAL_DATA_SUMMARY.md (line 70).

**Issue:** Three different "default" parameter sets are referenced:

1. Paper Table 1: shrink_factor=0.5, grow_factor=1.1, occ_low=0.2, occ_high=0.6
2. Actual main.cpp code defaults: shrink_factor=0.70, grow_factor=1.15, occ_low=0.30, occ_high=0.70
3. FINAL_DATA_SUMMARY.md sensitivity baseline note: occ_low=0.2, occ_high=0.6, shrink=0.5, grow=1.1

A reviewer will immediately ask: which parameter set produced the headline results (P95=19ms, PA%20 F1=0.114)? If the code defaults and the paper's stated defaults differ, the experimental results are not reproducible from the paper alone. This is either a bug or a documentation error — in either case, a critical reproducibility flaw.

**Recommended Fix:**
1. AUDIT IMMEDIATELY: Run the experiment with the code's current defaults (shrink=0.70, occ_low=0.30, occ_high=0.70) and verify these are the parameters that produced the headline numbers. If so, update Table 1 to match.
2. Add a reproducibility script (scripts/verify_defaults.sh) that prints the actual parameters from the compiled binary.
3. In Section 4.3, explicitly state: "All headline results use parameters: occ_low=X, occ_high=Y, shrink=Z, grow=G" — whatever the correct values are — and ensure these match main.cpp.
4. The sensitivity sweep's "baseline" row must correspond exactly to the Experiment 2/3 default. If not, explain why.

---

### Finding A-5: Wilcoxon p-values Need Variant Specification and Ties Handling

**Location:** paper/draft.md Section 5.2 (lines 394-402).

**Issue:** p-values are reported inconsistently (table says "p < 0.0001" but text says "p < 10^-9"). The Wilcoxon signed-rank test variant is not specified (exact, normal approximation, or ties-corrected). For Fixed architecture, F1 std = 0.0000 across 30 runs — all 30 runs produced identical F1. This means many tied differences when computing Wilcoxon between Adaptive and Fixed — ties require special handling (exact method, not normal approximation).

**Recommended Fix:**
1. Report p-values consistently as "p < 10^-9 (exact Wilcoxon signed-rank, n=30)" everywhere.
2. Specify in Section 4.3 which Wilcoxon implementation was used (e.g., scipy.stats.wilcoxon with method='exact') and how ties were handled.
3. Explain why Fixed architecture has zero std across 30 runs — because the Fixed pipeline is perfectly deterministic.

---

## SECTION 17 — ACADEMIC INTEGRITY REPORT B: PLAGIARISM, COPYRIGHT & ATTRIBUTION AUDIT

---

### Finding B-1: SPSC and MPMC Queue Designs Not Cited in the Paper

**Location:** include/klstream/core/spsc_queue.hpp (comment: "rigtorp-style"); include/klstream/core/mpmc_queue.hpp (comment: "Dmitry Vyukov-style"); paper/draft.md — no mention of these sources.

**Issue:** The code comments honestly acknowledge the design inspirations:
- Erik Rigtorp's SPSC queue: github.com/rigtorp/SPSCQueue (MIT License)
- Dmitry Vyukov's MPMC queue: 1024cores.net/home/lock-free-algorithms/queues/bounded-mpmc-queue

The implementations are written from scratch — not copied source code. However, the paper does not cite these designs at all. IEEE's authorship standards require attributing ideas, algorithms, and designs, not just copied text. If the cache-line-padded SPSC ring buffer and sequence-number MPMC queue are directly inspired by these prior designs, both must be cited.

This is NOT an allegation of plagiarism. The code is clearly original. It is a missing citation for algorithmic inspiration — a distinct but important IEEE requirement.

Copyright note: Rigtorp's SPSCQueue is MIT licensed (permits use). Vyukov's is less formally licensed — posted as a blog article — but permits research use. Neither exempts you from academic attribution.

**Recommended Fix:**
1. Add to the Related Work or Implementation section: "The bounded queues are implemented as SPSC and MPMC ring buffers following designs by Rigtorp [cite] and Vyukov [cite] respectively, rewritten from scratch in C++17."
2. Add references:
   - Rigtorp, E. (2019). SPSCQueue. GitHub. https://github.com/rigtorp/SPSCQueue
   - Vyukov, D. (2010). Bounded MPMC queue. 1024cores.net.

---

### Finding B-2: RED/CoDel Citation Is Incomplete for the EMA Concept; Unrun Alpha Sweep Referenced in Code

**Location:** paper/draft.md Section 2.4 (lines 119-122); include/klstream/core/backpressure.hpp (line 22 comment).

**Issue:** The paper cites RED and CoDel as the "direct intellectual ancestor" of EMAOccupancyTracker. This is correct. However, the actual EMA computation should cite the specific paper introducing EMA smoothing for queue occupancy: Floyd & Jacobson (1993) Random Early Detection (RED).

Additionally, the comment in backpressure.hpp says "The research extension (Section 14.1) sweeps alpha values and measures the effect on p99 latency" — but this alpha sweep does not appear anywhere in the paper's experimental results or the results directory. If this experiment was conducted, it should be in the paper. If not, the comment implies unpublished results.

**Recommended Fix:**
1. Add explicit citation: Floyd, S. & Jacobson, V. (1993). Random Early Detection gateways for congestion avoidance. IEEE/ACM Transactions on Networking, 1(4), 397-413.
2. If the alpha sweep was conducted, add it as a sub-experiment. If not, remove the reference from code comments.
3. Note whether alpha=0.10 was chosen by experiment or by analogy to RED's typical settings.

---

### Finding B-3: Astrom & Murray Section Reference Should Be Verified

**Location:** paper/draft.md Section 5.1 (lines 325-332).

**Issue:** The paper cites Astrom & Murray, Feedback Systems, 2nd ed., 2021, Section 10.4 for the relay feedback controller concept. This is a legitimate textbook citation. However, the specific claim about relay feedback controllers should be verified against the actual textbook section. If Section 10.4 covers the Ziegler-Nichols relay experiment for PID tuning (a different context), the citation would be technically misapplied.

**Recommended Fix:**
1. Verify the textbook section content. The 1st edition is available at cds.caltech.edu/~murray/amwiki.
2. As backup, add: Astrom, K.J. & Hagglund, T. (1984). Automatic tuning of simple regulators with specifications on phase and amplitude margins. Automatica, 20(5) — the original relay feedback paper.
3. Alternative: describe it as an on-off (bang-bang) controller and cite any standard control textbook.

---

### Finding B-4 [CRITICAL — SUBMISSION-BLOCKING]: Placeholder/Incomplete Citations

**Location:** paper/draft.md References section (lines 579-580); in-text citations to "AFMF (2024)" throughout.

**Issue:**
```
7. [ASWB] Adaptive Sliding Window Backpressure. ETRI Journal, 2026.
8. [ASWN] Adaptive Sliding Window Normalization. Information Systems, 2025.
```
These have no author names, no article title, no volume/issue/pages, no DOI. Additionally "AFMF (2024)" is cited in-text but has no corresponding entry in the References list at all.

IEEE journal submission cannot proceed with placeholder citations. IEEE editors will reject or return the paper immediately upon seeing these.

**Recommended Fix:**
1. For ASWB and ASWN: Find the actual papers. If they cannot be located (they may not exist under these names/venues), remove the citations and replace with clearly identified real papers on adaptive windowing with backpressure.
2. For AFMF: If this paper exists, add it to References with full bibliographic details. If it was a placeholder for a class of works, replace with a specific real paper.
3. Before final submission: use CrossRef or Google Scholar to verify every DOI and page number in the references list.

**This is the most directly submission-blocking issue in the entire paper.**

---

### Finding B-5: Liu et al. 2008 Reference Missing Full IEEE Bibliographic Data

**Location:** paper/draft.md Reference 6.

**Current entry:**
```
6. Liu, F.T., Ting, K.M. & Zhou, Z.H. (2008). Isolation Forest. IEEE International Conference on Data Mining.
```

**Issue:** Missing page numbers (413-422), DOI (10.1109/ICDM.2008.17), full conference name, and location. IEEE requires complete references.

**Recommended Fix:**
Replace with:
> Liu, F.T., Ting, K.M., & Zhou, Z.H. (2008). Isolation Forest. In Proc. 8th IEEE International Conference on Data Mining (ICDM 2008), Pisa, Italy, pp. 413-422. doi:10.1109/ICDM.2008.17.

Or cite the ACM TKDD journal version (2012) which is a peer-reviewed journal and contains the full c(n) derivation.

---

### Summary of All Findings

| ID | Severity | Issue | Blocks Submission? |
|----|----------|-------|-------------------|
| A-1 | High | R^2 = 0.9953 in abstract vs. 0.984 in data | Yes |
| A-2 | High | Latency approximation understated; sklearn vs C++ timing conflated | Yes |
| A-3 | Medium | "85% of events at w_min" has no traceable data source | Possibly |
| A-4 | High | Three different default parameter sets; code doesn't match paper | Yes |
| A-5 | Low | Wilcoxon variant not specified; ties not addressed; p-value format inconsistent | Minor |
| B-1 | Medium | SPSC/MPMC queue designs not cited in paper (only in code comments) | Minor |
| B-2 | Low | RED citation incomplete; alpha sweep referenced but not in results | Minor |
| B-3 | Low | Astrom & Murray section reference should be verified | Minor |
| B-4 | Critical | [ASWB], [ASWN], [AFMF] are incomplete/placeholder citations | YES (blocking) |
| B-5 | Medium | Liu et al. 2008 missing page numbers, DOI, conference details | Minor |

The two issues that will block IEEE submission if not fixed: **A-1** (R^2 inconsistency) and **B-4** (placeholder references).
The issue most likely to cause a major revision request: **A-4** (parameter mismatch between code and paper).

---

*End of KLStream-AdaptiveWindow Complete Study Guide.*
*Generated 2026-06-28. All numbers verified against raw project files.*

```

# File: report.md

```markdown
# KLStream Implementation Report

## Commits & Progress
- **Commit 1**: `chore: remove obsolete files from old architecture`
  - Deleted deprecated files including `queue.hpp`, `scheduler.hpp`, `worker_pool.hpp` and their respective tests.
- **Commit 2**: `feat(core): add config, pinning, and metrics modules`
  - Implemented core constants (`config.hpp`), Apple Silicon core affinity mapping (`pinning.hpp`), and metrics trackers (`metrics.hpp`).
- **Commit 3**: `feat(core): add event type and lock-free queues`
  - Implemented `event.hpp`, rigtorp-style `spsc_queue.hpp`, and Dmitry Vyukov-style `mpmc_queue.hpp`.
- **Commit 4**: `feat(core): add execution engine and backpressure trackers`
  - Implemented `operator.hpp`, thread manager `worker.hpp`, global coordinator `runtime.hpp`, and research extensions in `backpressure.hpp`.
- **Commit 5**: `feat(operators): add standard and window operators`
  - Implemented stateless operators (`source.hpp`, `map.hpp`, `filter.hpp`, `sink.hpp`) and stateful windowing operators (`aggregate.hpp`, `window.hpp`).
- **Commit 6**: `feat(examples): add CMake build system and example pipelines`
  - Added root `CMakeLists.txt` configuring fetchcontent for testing/benchmarking.
  - Implemented the `basic_pipeline` and `yahoo_streaming_benchmark` examples.
- **Commit 7**: `test: add unit and integration tests`
  - Implemented GoogleTest suites for queues, operators, backpressure, and pipeline integration.
- **Commit 8**: `bench: add google benchmark suites`
  - Implemented microbenchmarks for SPSC queue and end-to-end pipelines (basic and YSB).
- **Commit 9**: `feat(research): add research extensions and benchmark scripts`
  - Added scripts for automated benchmark execution and implemented the adaptive backpressure and core pinning research extensions.
- **Commit 10**: `fix(build): resolve ambiguous struct and gtest discovery`
  - Fixed ambiguous `AffinityConfig` struct definition in `core_pinning` research extension.
  - Ensured correct CMake target inclusion for `GoogleTest`.
- **Commit 11**: `test: fix capacities in queue and operator tests`
  - Fixed `Operator_BlockedWhenOutputFull` and `SourceOperator_PendingRetry` capacity logic.
  - Aligned GoogleTests with the strict bounds of `SPSCQueue` lock-free operations.

```

# Source: include/klstream/klstream.hpp

```cpp
#pragma once

/**
 * @file klstream.hpp
 * @brief Main header for KLStream - Kafka-less Parallel Stream Processing Runtime
 * 
 * Include this single header to access the full KLStream API.
 */

#include "klstream/core/event.hpp"
#include "klstream/core/queue.hpp"
#include "klstream/core/operator.hpp"
#include "klstream/core/runtime.hpp"
#include "klstream/core/scheduler.hpp"
#include "klstream/core/worker_pool.hpp"
#include "klstream/core/metrics.hpp"

#include "klstream/operators/source.hpp"
#include "klstream/operators/sink.hpp"
#include "klstream/operators/map.hpp"
#include "klstream/operators/filter.hpp"

namespace klstream {

/**
 * @brief Library version information
 */
constexpr const char* VERSION = "0.1.0";
constexpr int VERSION_MAJOR = 0;
constexpr int VERSION_MINOR = 1;
constexpr int VERSION_PATCH = 0;

} // namespace klstream

```

# Source: include/klstream/core/spsc_queue.hpp

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
#include <thread>
#include <chrono>

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

# Source: include/klstream/core/event.hpp

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

# Source: include/klstream/core/runtime.hpp

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

# Source: include/klstream/core/mpmc_queue.hpp

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

# Source: include/klstream/core/config.hpp

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

# Source: include/klstream/core/backpressure.hpp

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

# Source: include/klstream/core/worker.hpp

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

# Source: include/klstream/core/operator.hpp

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

    virtual void attach_metrics(struct OperatorMetrics*) {}

    const std::string& name() const { return name_; }

    // Unique integer ID assigned by the Runtime at registration time.
    std::uint64_t id = 0;

private:
    std::string name_;
};

} // namespace klstream

```

# Source: include/klstream/core/metrics.hpp

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

# Source: include/klstream/core/pinning.hpp

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

# Source: include/klstream/operators/map.hpp

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

    void attach_metrics(OperatorMetrics* m) override { metrics_ = m; }

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

# Source: include/klstream/operators/window.hpp

```cpp
// include/klstream/operators/window.hpp
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
    using AggrFn    = std::function<Out(const std::vector<Event<T>>&)>;

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

    void attach_metrics(OperatorMetrics* m) override { metrics_ = m; }

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
        buffer_.push_back(in_ev);

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
    std::vector<Event<T>>    buffer_;
    std::uint64_t     window_start_ts_{0};
    Event<Out>        pending_{};
    bool              has_pending_{false};
    OperatorMetrics*  metrics_{nullptr};
};

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

    void attach_metrics(OperatorMetrics* m) override { metrics_ = m; }

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

# Source: include/klstream/operators/filter.hpp

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

    void attach_metrics(OperatorMetrics* m) override { metrics_ = m; }

    OpStatus tick() override {
        if (has_pending_) {
            if (output_->try_push(pending_)) {
                has_pending_ = false;
                if (metrics_) metrics_->events_processed.increment();
                return OpStatus::Processed;
            }
