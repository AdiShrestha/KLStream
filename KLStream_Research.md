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