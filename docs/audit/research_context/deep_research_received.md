# KLStream/Brolq: Independent Scientific Assessment

**Executive Verdict:** The proposed direction—adaptive microbatching under bounded queues for streaming inference—faces substantial prior art and open challenges. Similar ideas already exist in both practice and research (e.g. BentoML’s adaptive batching and the BATCH framework), limiting straightforward novelty. The math and concurrency claims are subtle and demand rigorous formalization (e.g. Little’s Law or coordinated-omission issues). Available data (e.g. LOBSTER) has schema and usage constraints but no ground-truth anomaly labels, so any “detection” study would be synthetic or proxy. An end-to-end evaluation must carefully avoid measurement bias (e.g. backpressure and coordinated omission) and treat null results as publishable. Overall, a **skeptical stance** is warranted: either narrow the focus (e.g. demonstrating a well-verified bounded-queue streaming engine) or pivot. **Confidence:** low–medium (0.4–0.6), given uncertainties in achievable novelty. **Unresolved questions:** How to tie adaptive batching to a meaningful detection task without labels? Can theoretical guarantees (stability, invariants) be proved? How to validate the isolation forest implementation rigorously? 

**Material Access:** We reviewed the high-level description and audit summary provided in the prompt. We *attempted* to inspect the GitHub revision and attached docs (plan.md, ENGINE_CONTRACT.md, audit JSON files), but the analysis environment did not permit direct code retrieval. Thus we *could not open actual repository files or attached audit JSON*. We rely on the user’s summary of findings and documentation names. Our conclusions assume these audit findings are accurate; any direct code behavior is unknown. 

## Prior Art and Novelty

We surveyed adaptive-batching and streaming-inference literature. Modern ML serving platforms already use dynamic batching: for instance, BentoML’s adaptive batching “continuously adjusts batch size ... based on real-time traffic” to balance throughput and latency. In research, Ali *et al.* (SC20) present **BATCH**, a formal framework for inference on serverless platforms that uses an optimizer to satisfy tail-latency SLOs while adaptively batching incoming requests. Both works assume bursty, real-time arrivals and show strong performance gains (vs. fixed batching). This suggests KLStream’s goal overlaps established work.  

Another vein is adaptive batching in training: *SimiGrad* (NeurIPS 2021) and *JABAS* (Eurosys 2025) dynamically adjust batch sizes or parallelism for DNN training efficiency; though in training contexts, their principles (adapting workload for stability/efficiency) echo KLStream’s aims. For streaming systems, Wang *et al.* (USENIX ATC 2022) study **concurrent bounded queues**: their *BBQ* ring-buffer design partitions a queue to eliminate enqueue–dequeue contention and achieves 11–42× higher throughput than Linux or Folly queues. This work highlights that careful concurrent queue design yields dramatic performance gains, which is more impactful than simply adjusting batch sizes. 

| **Work (Year)**               | **Problem & Assumptions**                                           | **Variables/Signals**                               | **Workload/Platform**                             | **Claims/Findings**                              | **Baselines/Evaluation**                 | **Relation to KLStream**                                           | **Unanswered**                                    |
|-------------------------------|--------------------------------------------------------------------|-----------------------------------------------------|---------------------------------------------------|--------------------------------------------------|-------------------------------------------|--------------------------------------------------------------------|--------------------------------------------------|
| BentoML adaptive batching (blog) | Dynamically batch HTTP inference requests (assumes stateless model, known latency cost) | Throughput, request latency, batch size, batch window | Generic model server (CPU/GPU), variable traffic | Adaptive algorithm learns trends to maximize throughput under latency constraint | Static vs adaptive batching on real workloads | Illustrates industry use of adaptive batching for latency-constraint serving | Formal analysis of algorithm, robustness, e.g. oscillations |
| BATCH (Ali *et al.*, SC20) | ML inference on serverless with bursty load; need SLO (tail latency) guarantees | Provisioned threads, batch size, arrival rate        | AWS Lambda + TensorFlow/PyTorch inference         | Optimizer ensures tail-latency SLOs; batching cost-effective; adaptive batching enabled | State-of-art (MArk), AWS SageMaker, static batch | Formal guarantees of latency/cost with adaptive batching | Static analysis vs dynamic queues; running on local multicore |
| SimiGrad (NeurIPS 2021) | DNN training: large-batch vs convergence tradeoff | Batch size, gradient noise, convergence             | Multi-GPU clusters, large models                  | Fine-grained (per-batch) adaptive sizing based on gradient similarity | Hand-tuned static large batch              | Similar concept of adaptively adjusting batch for efficiency | Different domain (training vs inference streaming) |
| JABAS (Eurosys 2025) [pending] | DNN training on hetero cluster, co-control of batch and workers | Same as above plus resource count                  | Heterogeneous GPUs/CPUs                          | Jointly adapt batch size and parallelism for throughput, convergence | Static scaling, AoI (adaptive parallelism)   | Again training context; shows joint optimization can help throughput | Not applied to real-time inference streaming |
| Wang *et al.* (USENIX ATC 2022) (BBQ) | Concurrent bounded queue performance under multithreading | Enqueue/dequeue contention, ring buffer layout     | Multi-producer/consumer on Linux, DPDK etc.       | Block-based queue improves throughput 11–42× | Linux kernel queue, DPDK, Folly, Disruptor        | Relevant for KLStream’s queue design; shows advanced queues beat naive queueing | KLStream’s simplicity may lag such optimized structures |
| Hariri *et al.* (ICLR 2018, EIF) | Isolation Forest score anisotropy in high dims; use random hyperplane | Feature splits vs hyperplane splits               | Synthetic data                                     | Extended IF improves score consistency           | Original iForest                        | Caveat: standard IF uses axis-aligned splits        | KLStream uses custom IF; must validate its output consistency |
| Coordinated Omission (Gil Tene) | Measurement bias when source stops sending under overload | Arrival pattern (open vs closed loop)             | Web request benchmarks                           | Closed-loop testing hides tail latencies, making results look better | Open-loop correct measurement            | Warns that “busy-waiting” traffic can mask delays in streaming tests | KLStream should emulate open-loop arrival to expose queueing delays |

**Novelty Assessment:** Adaptive batching per se is well-known (see BentoML and BATCH) and often combined with autoscaling in cloud systems. The novel angle could only be a **specific new algorithm or guarantee for multicore CPU streaming inference**. But any claim of novelty must clearly exceed existing work: e.g. providing a theoretical stability proof, or demonstrating superior latency-throughput tradeoffs under realistic microbenchmarks. Absent that, the project risks being an *engineering implementation* rather than publishable research. The strongest plausible contribution might be a rigorous queueing/control-theoretic analysis of adaptive batching. Alternative directions: focus on formal correctness of the C++ engine, or integrating streaming metrics natively, or pivot to a more tractable anomaly problem (see Data section below). Without clear new theory or demonstrable significant advantage, proceeding as-is is unlikely to yield a defensible publication.

## Mathematical and Algorithmic Analysis

We unpack the streaming/batching model. Consider a stream of single-point events entering a bounded queue. Let λ(t) be the offered rate; let each batch of size *b* take (random) service time S(b). The **per-event latency** includes queue waiting, batch formation delay, service, and publication. By *Little’s Law*, average queue length ≈ λ·(average latency). A dynamic controller (e.g. EMA-based) must react to signals (observed S(·), queue occupancy) with delay and smoothing; formal stability requires *control theory* (linear/quasi-linear model, bounded delay). Without a theorem, one risks oscillations or instability under sudden load changes. Key signal definitions: *offered* (arrivals at source), *admitted* (enqueued), *completed* (output delivered), *rejected* (queue full drop), etc. Coordinated omission occurs if testing stops arrivals when the queue is full, leading to underreported latencies; thus experiments must use open-loop traffic to correctly measure backlog effects. 

Isolation Forest (IF) specifics: Standard IF draws **max_samples** = min(256, n) per tree, so on small datasets it uses all data, and on larger it subsamples 256. The anomaly score uses path lengths:  $s(x) = 2^{-E[h(x)]/c(m)}$ where $E[h(x)]$ is average path length and $c(m)$ is the expected path length in a random BST of $m$ points.  Thus, IF with *φ* subsample size normalizes by $c(φ)$ (harmonic-based). Implementation variants matter: e.g. if one tree uses different random splits (due to feature ordering or RNG state), results can vary. *Convergence:* IF assumes independent random splits; if features have duplicates or constant values, some splits do nothing. Batching should **not** change scores if features and model are unchanged: if the C++ code yields different results for batched vs singleton calls, that signals a bug. Any deviation from, say, scikit-learn’s algorithm must be explicitly justified (e.g. fully random hyperplane splits vs axis-aligned, different *c(ψ)* conventions). For any such design choice, we should reference primary sources: e.g. Liu *et al.* (2008) describing the $c(m)$ formula, and note that deviations (like using $\ln(ψ)$ approximation) must be documented. 

On concurrency: The engine’s bounded queue and threading require attention to memory models and progress guarantees. Recent work (BBQ) shows even “simple” queues can have subtle contention issues. We must ensure our atomic queue truly has the claimed *lock-free* or wait-free semantics (which requires proving no hidden locks). The explicit *shutdown* and *drain* semantics need formal description: who “owns” the queue on shutdown? Are producers still allowed or blocked? On cancellations: any batch formation in flight must either complete or abort cleanly. Memory visibility (fences) should match the assumed concurrency model (e.g. C++17’s sequential consistency or weaker). *Hysteresis/EMA:* The controller’s update rule ($n_i = α n_{i-1} + (1-α) Δ$, etc.) should be clearly defined; the effect of smoothing or low-pass filtering on response time must be analyzed. Without a proof, we should at least show a sketch (queue length as state, batch size as control). If a formal *theorem of stability* is needed, it should cite a canonical source (e.g. queueing-feedback control papers). 

**No Proof without Specification:** Crucially, to justify claims like “latency guaranteed” or “throughput optimum”, we need precise assumptions (arrival distribution type, bounded service variation) and either a mathematical proof (beyond scope?) or exhaustive simulation under varied conditions. If offering “deadline-aware utility”, that implies a different priority than pure anomaly score – an uncommon twist not explored by prior IF literature, so it would require full explication (e.g. define a utility function combining timeliness vs detection accuracy). Without such detail, these claims remain vague. 

## Data, Tasks, and Labels

The only explicit domain data mentioned is LOBSTER (NASDAQ limit order book). Official LOBSTER **schema** (Huang & Polak 2011) provides *order events* with nanosecond timestamps and granular price/size levels. A free **sample** of LOBSTER data exists for academic use: it “provide[s] anonymized limit order book event data” for selected stocks, which “are open-access and suitable for academic reproducibility”. However, full LOBSTER data is paid, so reliance must be on the public sample or similar datasets. Usage: one must respect licensing (Huang & Polak do not imply free use beyond sample). Price units are typically integers in tenth of a cent; timestamps are nanosecond-precision epoch. We should confirm (via LOBSTER docs) what constitutes a “day” and whether data is contiguous. There is no mention of real anomaly labels in LOBSTER – it is raw trading data. **No genuine fraud or manipulation flags are provided.** Thus, a classification task with true labels is infeasible. 

If no true anomaly labels exist, we must avoid fabricating labels. Alternatives: (a) Use LOBSTER as *unlabeled streaming data for performance testing only* (focusing on throughput and latency, ignoring anomalies), or (b) define a synthetic *surrogate task*: for example, inject artificial “spikes” or model-based anomalies and detect them. For fairness, any synthetic anomalies must be declared synthetic (not called “market anomalies”), and all pipeline effects on detection (false positives/negatives) must be measured. A predictive task could be forward price or imbalance prediction, but again no public label (maybe use future price move as label). For static classification, one could use commodity-level features to predict known outcomes (like near-term volatility surges) if that label is externally defined. 

**Data pipeline:** Input features must be carefully constructed (e.g. price levels, volumes, order book imbalances). Time splits: ensure **chronological** splits to simulate real deployment (e.g. train on 2019 data, test on 2020 sample). No “future leakage”: if using windows, drop samples whose prediction horizon overlaps next window’s labels. For backtesting anomalies, hide future label information from the model. All provenance must be logged (source file, filter parameters, any heuristic transformations). If synthetic, fully describe injection mechanism (timing, magnitude) so experiments are reproducible. 

## Experimental Design and Baselines

We propose two intertwined goals: (1) measure *system performance* (throughput, end-to-end latency) under controlled load, and (2) (optionally) measure *detection performance* if a task is defined. 

**Experimental factors:**  
- *Controller algorithm:* e.g. current EMA-based adaptive batching vs fixed-batch vs no-batch (size=1).  
- *Traffic intensity:* vary offered rate (λ) from low (well below saturation) to overload (observed queueing). Possibly use Poisson or recorded order-book replay.  
- *Workload randomness:* vary event sizes or service time (if IF inference cost is variable). Use the Apple M3 as consistent platform.  
- *Seeds/Trials:* Each config should be repeated with multiple random seeds (for RNG and/or arrival jitter).  

**Metrics:**  
- *Throughput:* events/sec processed (after all filtering).  
- *Latency:* distribution (percentiles) of per-event end-to-end time (arrival to output). Especially the *95th/99th percentile* under sustained load.  
- *Resource usage:* CPU utilization (per core), memory.  
- *Detection quality:* if using anomaly labels, measure ROC-AUC or F1 with appropriate tie handling. Use adjusted p-value (e.g. ROC comparisons) properly.  

**Baselines:** At minimum, compare:  
1. **No batching** (process each event immediately, batch size=1).  
2. **Fixed batching** (set batch_size constant, tune a few representative values, e.g. 10, 50, 100).  
3. **Adaptive controller** (current EMA approach).  
If possible, a more sophisticated adaptive (e.g. a variant from literature, or the BentoML heuristic) would be a strong baseline. Also consider **parallelism baseline**: e.g. fixed number of worker threads vs single-thread (to isolate batching impact from parallel throughput).  

Other baselines might be domain-specific models (one-class SVM, statistical threshold) for anomaly detection, but *only if a genuine task is defined*. If purely systems-focused, then detection quality is irrelevant. 

**Protocol details:** Always warm up the system (e.g. discard initial transient until queue reaches steady state). Run sufficiently long to capture stable behavior (e.g. tens of seconds or minutes of simulated trading). Use *open-loop* arrival (e.g. timed loop or realistic event trace) to avoid coordinated omission. Randomize policy order if multiple run segments (to avoid bias in time-of-day or data order). Collect enough samples to compute confidence intervals: likely ≥10 runs per condition (monitor variance across runs). For latencies, ensure log-scale plots or tail quantiles (coordinated omission can severely bias means). 

**Ablations:** Test turning off key features: e.g. disable queue bound (infinite queue) to show effect of backpressure, remove adaptive control (compare fixed vs dynamic). Vary controller parameters (smoothing factor, reaction threshold). If using simulator, test different arrival patterns (Poisson vs bursty). For “OOD/limits”, inject pathological loads (e.g. constant overload, sudden drop) to see overshoot or oscillation. 

**Core vs Extensions:** The core study should be achievable on the M3 Air: e.g. a few-minute streaming runs, maybe using a condensed dataset (one stock, few levels). GPU use seems irrelevant as implementation is CPU. If ambitious, one could emulate multiple “sources” via threads to stress multicore. An optional extension: implement the experiment on a cheap cloud CPU and compare scaling (but not required). The source schedule should mimic realistic inter-arrival times from LOBSTER data (use the timestamps to drive the feeder).  

## Statistical Analysis

Given likely small sample size (runs, possible data days), careful stats are needed. We treat *run replicates* as independent blocks. Within each run, individual events are *within-run* units (but not independent if queue interactions). We will probably use the run means (or tail quantiles) as primary data points. If comparing two policies on the same traffic trace, use a *paired test* (paired t-test or Wilcoxon signed-rank) on run-level metrics, or paired CIs for difference in latency. For more than two, ANOVA or repeated-measures if assumptions hold.  

For latency distributions: report medians and 90/99th percentiles, but statistical testing on quantiles is tricky. We may bootstrap quantiles per-run to estimate variability, or use nonparametric comparisons of empirical distributions (e.g. Kolmogorov-Smirnov, though tied values and CIs must be handled with care). Avoid relying solely on “average latency” if the distribution is heavy-tailed (likely).  

Multiplicity: If dozens of comparisons (controller vs baseline, multiple load levels), adjust via Tukey or Holm-Bonferroni for *families* of related hypotheses. Emphasize effect size (e.g. throughput increase, latency reduction) rather than just *p*-values. If sample size is small, consider exact or permutation tests.  

Power/Precision: Predefine what minimum effect is “meaningful” (e.g. adaptive must cut 99th% latency by >10%). If pilot data shows huge variance, may decide more runs are needed or warn if underpowered. A **negative result** can still be informative if the CI excludes any practically significant benefit of adaptation. 

Plot and interpret errors: e.g. show error bars or CIs on tails (which may be wide). If results are inconclusive (e.g. overlapping CIs), do *not* claim success; instead highlight that difference may be negligible.  

## Software Factory and Verification

The project mentions an “evidence factory” with signing and replay protections. We must assess if it truly enforces reproducibility:

- **Schema integrity:** Are inputs/outputs checksummed? Ideally, the pipeline should hash raw data and model parameters, and record these hashes with results (as the Engine Contract might specify). If the factory only logs a signature *after* running, it’s weak; it must be tied to specific code/data versions.  
- **Verified execution:** Signatures on the native executable are only meaningful if the factory verifies the hash of the compiled binary *matches* the signed artifact. The audit noted a counterexample where removing a supervisor signature still passed; this suggests the procedure is flawed. We need an *adversarial test*: modify a single line of the engine code (e.g. change how queue fullness is handled) and see if the factory’s “certify” command flags it or silently approves.  
- **Recomputation:** Measurements (AUC, latency) should be recomputed independently. If the factory script just checks for expected outputs or structure, it’s insufficient. For each claimed metric, the factory should run the calculation on the logged raw outputs. For example, if the experiment claims AUC=0.85, the factory must recompute ROC curves from predictions to confirm 0.85, not just trust a text file.  
- **Holdout isolation:** The factory’s pipeline must ensure any “held-out” data was never seen during training. This means strict control of data splits (perhaps using cryptographic seals on data subsets). Without that, the train/test separation could be accidentally violated. An adversarial test: shuffle training labels and see if model outputs change (they shouldn’t if truly isolated test).  
- **Provenance:** The chain from raw data → features → model → scores must be logged. For instance, feature normalization parameters, random seeds, and even the path of code execution. Without it, reproducibility suffers.  

Concrete acceptance tests: we could attempt a “phantom modification” – e.g. run the declared factory with an unreported source change and see if it passes. Also test “replay protection”: if one tries to feed the same output twice, does the factory detect it? (It should, or at least ensure fresh timestamps or run IDs.) 

For unlabelled streaming or simulations: The factory should allow experiments to declare “synthetic labels injected” or “benchmark mode” without punishing them as if they were mislabeled real data. But this requires a metadata flag. We should ensure that declaration is explicit in the experiment artifact. The factory should not simply require a binary classification framework; it should accommodate regression or simulation outputs by verifying the process rather than fixed outputs.

## Roadmap and Decision Gates

Based on the above, we recommend the following phased plan:

- **Phase 1: Theory & Preliminary Evaluation.** Conduct basic queueing analysis (even simulation in Python) to model adaptive batching feedback. Test the Isolation Forest implementation on synthetic known anomalies to validate *pointwise invariance* (features held constant, does batch vs no-batch give same score?). Develop unit tests for queue close/drain behavior (e.g. pushing `n` items then shutting down yields exactly `n` completions, no deadlock). If fundamental issues (e.g. race conditions, IR inconsistencies) are found, fix them before further work.

- **Gate 1:** Achieve a self-consistent specification: all queue semantics and algorithmic details must be documented and unit-tested. Is the controller’s update rule stable under simple synthetic arrival patterns? Has the IF model been cross-checked against scikit-learn on static data? If not, major work needed; else proceed.

- **Phase 2: Prototype Experiments on M3.** Assemble a minimal test harness: simulate an open-loop source feeding the engine. Use the LOBSTER sample data at reduced scale (maybe one day of one ticker). Run the three policies (no-batch, fixed-batch, adaptive) under light and heavy load. Measure throughput/latency and ensure no coordinated omission (using our own timing loop). Also record model scores for a synthetic anomaly task (e.g. randomly label 1% of points as anomalies and see if IF scores correlate). 

- **Gate 2:** Evaluate results. If adaptive batching shows *no significant improvement* over a simple baseline (or worse, shows instability), reconsider direction. If it *does* show improvement, check if it’s due to something trivial (e.g. just parallelism). Only if a non-trivial and reproducible effect is seen would it warrant a larger study.

- **Phase 3: Expanded Study & Verification.** With working code, run full experiments (multiple runs, seeds, maybe a few stocks). Rigorously apply statistical analysis. Meanwhile, solidify the factory: write end-to-end tests (modify code to see if factory catches it). Possibly propose changes to factory scripts or add a feature-test routine. 

- **Gate 3:** If experiments yield novel insights (e.g. quantifiable benefit under certain patterns, with solid stats) *and* factory robustness is proven (adversarial tests passed), proceed toward write-up. If not, either pivot scope (e.g. drop anomaly detection focus and present as a systems paper on verified streaming engine) or cut losses.

## M3 Hardware Resource Plan

On the Apple M3 Air (8 CPU, no discrete GPU usage assumed):  

- **Software:** Use C++17 (as already) compiled with `-fsanitize=address,undefined,thread` to catch bugs early (the repo already has sanitizer check). Use data in-memory; no heavy I/O needed beyond loading (the data sizes are small). 

- **Batching workloads:** The CPU alone can likely handle the small LOBSTER sample easily; if needed, saturate it by artificially parallelizing workload generation (launch multiple source threads). The 10-core GPU is not relevant unless rewriting parts for GPU, which is out-of-scope.  

- **Memory:** 16 GB RAM is ample for in-memory queues and batch buffers. For isolation forest, even a few thousand trees with subsamples of 256 is fine on CPU. If we accidentally try large ensembles, ensure to tune `n_trees` downward for feasibility.  

- **Monitoring:** Use lightweight logging (stdout or CSV) for timestamps; avoid heavy traces unless debugging. If doing profiling, use built-in `time` or simple counters. TSan/ASan runs can be slow (perform only in debug mode, not all trials).  

- **Time Budget:** Each experiment might run a minute or two of simulated streaming. With multiple seeds (say 10) and a few configs, total runtime likely a few hours, well within desktop limits. 

- **Python/Tools:** If doing any data prep or plotting, use Python on the same machine. But ensure versions (e.g. scikit-learn for IF comparisons). Plan to use only free/open tools (no proprietary data).  

- **Risks:** The M3’s performance may differ from typical x86, but for our purposes (latency vs throughput *trends*) it should suffice. GPUs can be ignored unless future work involves deep learning models. 

## Venue Fit and Recommendations

At present, there is **no clear novel research claim**. Suitable venues depend on actual contributions:

- If the end result is primarily a **streaming systems implementation (engine)**, a venue might be a workshop or conference on real-time data processing (e.g. DEBS, ICDM workshop). Many mainstream conferences (NeurIPS, KDD) expect a strong algorithmic novelty or ML advance, which is not evident here. A systems paper (e.g. USENIX ATC, Middleware) would require proving a significant throughput or latency improvement with rigorous systems evaluation; given the foundation is incremental, this seems unlikely.

- If focusing on the factory/infrastructure aspect, perhaps a workshop on reproducibility or an artifact evaluation track could be relevant, but again the “contribution” must be something we added. The current factory issues suggest perhaps a note or report, not a major publication.

- If anything novel emerges (e.g. a new latency/throughput model or control algorithm with proof), potential journals could be *Performance Evaluation* or *IEEE Transactions on Network Science and Engineering*. For anomaly detection, conferences like WSDM or an anomaly detection workshop might consider a rigorous negative result or system demonstration, but the heavy audit context and lack of labels make it a stretch.

**Recommendation:** *Defer aggressive publication.* First narrow the scope. For example, target a *short paper or poster* in a systems venue focusing on the verified concurrent engine (claiming bug fixes and a solid test harness as contributions). Or reframe as a *case study in reproducibility* highlighting lessons from the audit. Without a concrete new algorithmic insight or data label task, writing a full paper is premature. 

The highest-impact chance would be **pivoting**: perhaps apply the engine to a different domain with real labels, or switch focus entirely to “queued streaming inference under intermittent load” in a simulation context with well-defined load patterns (like measured from real traffic studies). 

Use current official deadlines/policies to gauge timeline, but do not assume acceptance anywhere. E.g. many systems conferences’ artifact tracks encourage thorough verification, so our factory focus might fit there if we deliver a “reproducible artifact.” But again, only after having solid content.

## Claim–Evidence Summary

| **Claim / Task**                                   | **Evidence / Citations**                                                   | **Needed Implementation**                     | **Acceptance Criteria**                                            | **Limitations**                                     |
|----------------------------------------------------|---------------------------------------------------------------------------|-----------------------------------------------|--------------------------------------------------------------------|-----------------------------------------------------|
| Adaptive batching improves throughput/latency tradeoff | BentoML docs and BATCH paper assert benefits of adaptive batching | Implement dynamic batch controller and metrics logging | Demonstrated throughput gain with maintained latency vs baseline | Gains may depend on workload; proofs are partial         |
| IF scores invariant to batching if features/model same | Scikit-learn docs: IF algorithm is deterministic given seed; design formula | Test IF with identical inputs in batched vs single calls   | Identical scores output; otherwise flag bug                     | Tied scores or stochastic RNG differences possible        |
| Factory script enforces execution integrity | Audit showed flaws; coordinator omission concept suggests we test it | Adversarial test: modify code/args and run factory        | Factory rejects mismatched code or replayed logs                | Factory design may require modification to catch issues    |
| LOBSTER sample data is accessible & unlabeled | Literature: “free-tier LOBSTER sample ... anonymized event data ... open-access” | Use free sample only; cite source                     | Able to download and parse sample files; respect license terms    | Only a subset of stocks/dates; no anomaly labels provided |

## Open Questions for the User

- **Repository Access:** Can you provide direct access (e.g. zip) to the specific revision 48f2b51c64c56db578ae1bf996a0176739f76e9d? Without inspecting code/algorithms, some assessments remain speculative.

- **Task Definition:** Is there any *specific detection task or performance metric* you ultimately aim to optimize? (E.g. F1 score on known fraud events, or end-to-end latency under X% load.) This will guide what experiments matter.

- **Factory Details:** Can you clarify exactly how the factory verifies signatures and runs experiments? For instance, how does it incorporate the Engine Contract? Any documentation of the factory’s certification logic would help identify gaps.

- **Data Plans:** Will you purchase or access full LOBSTER data, or only use the free sample? Are you open to using other labeled streams (e.g. synthetic data, or public anomaly benchmarks) if needed?

- **Performance Goals:** What *latency targets* are considered acceptable? For example, is sub-100ms end-to-end processing needed? This affects what “improvement” means.

Providing clarity on these will allow tighter recommendations and experiment design.