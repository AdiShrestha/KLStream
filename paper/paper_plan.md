# KLStream Publication Plan & Claim Mapping Specification

**Target Venues:** IEEE Transactions on Parallel and Distributed Systems (TPDS) / ACM Distributed and Event-Based Systems (DEBS) / KUSET  
**Framing:** Systems Research Path A (Queue-driven batch adaptation for stream inference)  
**Governing Invariants:** INV-001 through INV-012, SVI-001 through SVI-006, NFR-001 through NFR-005, MAR-1..7, MAR-X1..X7  

---

## 1. Manuscript Metadata

- **Working Title:** *KLStream: Backpressure-Aware Dynamic Batch Adaptation for Low-Latency Stream Anomaly Detection in Financial Tick Feeds*
- **Primary Authors:** Adarsh Shrestha, et al.
- **Keywords:** Stream Processing, Dynamic Batching, Adaptive Windowing, Lock-Free Queues, Anomaly Detection, Isolation Forest, Backpressure.

---

## 2. Formal Abstract

> Real-time anomaly detection over high-frequency financial market feeds presents a fundamental systems conflict between latency and throughput. Point-wise tuple-at-a-time stream processing minimizes freshness lag under sparse load but collapses under arrival bursts due to per-event dispatch overhead, while static micro-batching achieves high amortized execution throughput during surges at the expense of intolerable queuing delays during baseline traffic. We present **KLStream**, a high-performance C++17 stream processing runtime that dynamically adapts batch window boundaries driven by real-time lock-free queue occupancy feedback. KLStream couples cache-aligned Single-Producer Single-Consumer (SPSC) ring buffers with a closed-loop Exponential Moving Average (EMA) window controller, modulating batch sizes $W \in [10, 500]$ to balance service amortization against queuing delays. 
> 
> To ensure absolute scientific integrity, our evaluation is governed by a fail-closed "Reality Gate" protocol that guarantees deterministic temporal separation across 60% training, 20% validation, and 20% test partitions with zero leakage. Across a pre-registered 54-run experimental evaluation matrix spanning five independent synthetic data seeds and an academic limit order book market benchmark (99,000 processed events with 100% exact event accounting and zero loss), KLStream demonstrates that: (1) adaptive windowing reduces tail latency ($P_{99}$) by **98.02%** relative to fixed large batching ($p = 0.0312$, Cliff's $\delta = 1.000$); (2) anomaly detection accuracy is strictly invariant across windowing regimens ($\Delta\text{AUC} = 0.000$); and (3) dynamic closed-loop feedback provides a **97.72%** tail latency reduction over an open-loop shuffled-occupancy control, rigorously isolating the causal value of queue feedback. Micro-benchmarks verify that KLStream's lock-free queues sustain **22.14 Million ops/sec** under single-producer/single-consumer workloads, and point-wise model scoring completes in **270.99 ns**. All empirical claims, pre-registered falsification verdicts, and raw data are packaged into an automated one-command reproduction artifact.

---

## 3. Section Outline and Objectives

### Section 1: Introduction
- **§1.1 The High-Frequency Financial Streaming Dilemma:** Millisecond market shifts, bursty non-stationary arrival rates, and the trade-off between point-wise dispatch overhead and batch queuing latency.
- **§1.2 Limitations of Existing Approaches:** Static micro-batching (Apache Flink, Spark Streaming) vs. unadaptive streaming; vulnerability to heavy-tailed arrival shocks.
- **§1.3 The Path A Systems Framing:** Clarifying that adaptive batching is a queuing-latency optimization, not a statistical learning method that creates algorithmic accuracy.
- **§1.4 Summary of Contributions:**
  1. Formal mathematical model decoupling queuing delay, freshness lag, and execution service time.
  2. The KLStream runtime architecture with cache-aligned lock-free SPSC/MPMC queues.
  3. Closed-loop EMA window controller with deadband filtering to prevent high-frequency limit-cycle chattering.
  4. The Reality Gate protocol and open science reproduction package verifying Claims 1, 2, and 3.

### Section 2: System Model and Queuing Dynamics
- **§2.1 Stream Ingestion & Non-Stationary Burst Formulation:** Arrival point process $A(t)$, time-varying arrival rate $\lambda(t)$, queue occupancy $\rho_t$.
- **§2.2 Latency Decomposition Identity:**
  $$\mathbb{E}[T_{\text{e2e}}] = \mathbb{E}[T_q] + \mathbb{E}[T_{\text{freshness}}] + \mathbb{E}[T_{\text{exec}}]$$
  Proof of batch-size convexity: $T_{\text{freshness}}$ increases monotonically with $W$, while $T_{\text{exec}}$ decreases per event with $W$.
- **§2.3 Closed-Loop Controller Specification:**
  EMA smoothing $\bar{\rho}_t = \alpha \rho_t + (1-\alpha)\bar{\rho}_{t-1}$, deadband thresholding $\Delta\rho$, proportional window modulation $w_{t+1} = \text{clamp}(w_t + \kappa(\bar{\rho}_t - \rho^*), w_{\min}, w_{\max})$.

### Section 3: KLStream Engine Architecture
- **§3.1 Memory Model & Lock-Free Ring Buffers:** Cache-line aligned SPSC and Dmitry Vyukov turn-based MPMC queues with acquire/release memory semantics (INV-008).
- **§3.2 Pipeline Lifecycle & Zero-Loss Semantics:** State machine transitions, finite replay mode, and exact event accounting (INV-007).
- **§3.3 Model Serialization & Integrity:** The 64-byte `KLIF` binary header format and SHA-256 payload checksums for Isolation Forest models (INV-004, FR-010).

### Section 4: Data Supply Chain and Reality Gate
- **§4.1 Dataset Taxonomy & Data-Kind Classification:** Strict separation of synthetic replay streams (`data/processed/replay_synthetic_*.csv`) and real-derived academic benchmark samples (INV-001, INV-002).
- **§4.2 Deterministic Chronological Partitioning:** Disjoint 60% Train, 20% Validation, 20% Test partitioning without lookahead bias (INV-005, SVI-002).
- **§4.3 The Reality Gate Verification Protocol:** Automated validation of schema, monotonically increasing timestamps, price positivity, and zero test leakage.

### Section 5: Experimental Methodology and Pre-Registration
- **§5.1 Full Matrix Evaluation Design:** 6 datasets $\times$ 9 controller regimens (Fixed $W \in \{10, 50, 100, 200, 500\}$, Unadaptive $W=1$, Adaptive EMA, Shuffled-Occupancy, Periodic Control) = 54 benchmark runs.
- **§5.2 Adversarial Control Baselines:** Decoupling real queue occupancy from batch sizing via shuffled controls (MAR-2, MAR-X1).
- **§5.3 Statistical Testing Protocol:** Non-parametric Wilcoxon signed-rank tests, Cliff's delta effect sizes ($\delta$), bootstrap confidence intervals, and Bonferroni-Holm family-wise error rate control (INV-006, MAR-3).
- **§5.4 Cryptographic Pre-Registration:** Frozen evaluation rules sealed under SHA-256 digest `6bf83d66...` (SVI-004, MAR-7).

### Section 6: Empirical Evaluation
- **§6.1 Claim 1 Evaluation (Tail Latency Reduction):** P99 latency results showing 98.02% reduction vs Fixed-500 ($p=0.0312, \delta=1.000$, SUPPORTED).
- **§6.2 Claim 2 Evaluation (Metric Invariance):** Mathematical proof and empirical evidence that detection AUC-ROC remains invariant ($\Delta\text{AUC} = 0.000$, SUPPORTED).
- **§6.3 Claim 3 Evaluation (Causal Feedback Value):** Comparative analysis against shuffled-occupancy controls confirming a 97.72% tail latency reduction ($p=0.0312, \delta=1.000$, SUPPORTED).
- **§6.4 Latency Decomposition Breakdown:** Analysis of Figure 2 stacked bars confirming $T_q, T_{\text{freshness}}, T_{\text{exec}}$ proportions across regimens.

### Section 7: Parameter Sensitivity, Dynamic Stability & Dual MAR Defense
- **§7.1 Parameter Sensitivity Sweeps:** Robustness over $\alpha \in [0.01, 0.50]$ and window boundaries across 60 configurations.
- **§7.2 Step-Load Transient Shock Analysis (MAR-X4):** 10x arrival surge response demonstrating 10-step monotonic rise time and 0.00 chattering index.
- **§7.3 Defense Against Internal Attack Surfaces (MAR-1..7):** Full refutation of data leakage, static evaluation, multiple testing, and baseline weakness.
- **§7.4 Defense Against External Attack Surfaces (MAR-X1..X7):** Rigorous isolation of controller value, distribution shift, hardware ground truth, and anti-HARKing verification.

### Section 8: Related Work and Conclusion
- **§8.1 Related Work:** Streaming batching engines (Spark, Flink), adaptive rate control in networks (TCP Vegas, CoDel), online stream anomaly detection.
- **§8.2 Open Science Release:** Canonical single-command reproduction via `bash scripts/reproduce_all.sh`.
- **§8.3 Conclusion:** Summary of findings and implications for financial streaming architectures.

---

## 4. Section-by-Section Claim & Evidence Mapping

| Section | Claim / Requirement | Governing Invariant | Key Artifact / Empirical Evidence |
|---|---|---|---|
| **Abstract & §1** | Path A Systems Framing | DL-002, DL-006 | `source/experiments/research_framing.md` |
| **§2** | Latency Decomposition Identity | INV-010, INV-011 | `results/latency_decomposition_report.json` |
| **§3** | Lock-Free Queue Correctness | INV-008, NFR-001 | `results/hardware_benchmark_report.json` (22.14M ops/sec) |
| **§3** | Model Binary Serialization | INV-004, FR-010 | `models/training_manifest.json` ('KLIF' headers) |
| **§4** | Reality Gate Data Integrity | INV-001, INV-002, INV-005 | `project/chunks/chunk04/reality_gate_report.json` |
| **§4** | Zero Leakage Threshold Tuning | SVI-002, MAR-3 | `results/validation_calibration.json` |
| **§5** | Event Accounting Integrity | INV-007 | `results/execution_summary.json` (0 drops / 99k events) |
| **§5** | Non-Parametric Statistics | INV-006, MAR-3 | `results/statistical_summary.json` |
| **§6.1** | Claim 1 Latency Reduction | SVI-003, SVI-004 | `results/falsification_verdicts.json` (Claim 1 SUPPORTED) |
| **§6.2** | Claim 2 Metric Invariance | SVI-003, SVI-004 | `results/falsification_verdicts.json` (Claim 2 SUPPORTED) |
| **§6.3** | Claim 3 Causal Feedback Value | MAR-2, MAR-X1 | `results/falsification_verdicts.json` (Claim 3 SUPPORTED) |
| **§6.4** | Latency Breakdown Figures | INV-010 | `results/figures/fig1_tradeoff_pareto.png`, `fig2_latency_decomposition.png` |
| **§7.1** | Parameter Sensitivity Sweeps | MAR-X4 | `results/sensitivity_analysis.json` (60 configurations) |
| **§7.2** | Dynamic Stability (10x Surge) | MAR-X4 | `results/step_load_dynamics.csv`, `results/figures/fig3_step_load_stability.png` |
| **§7.3-7.4**| Dual MAR 14 Attack Surfaces | MAR-1..7, MAR-X1..X7 | `project/methodology_adversarial_review.md` |
| **§8** | One-Step Reproducibility | INV-003, SVI-006 | `source/experiments/reproducibility_receipt.md`, `scripts/reproduce_all.sh` |
