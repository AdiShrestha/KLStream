# Assessment of the supplied Deep Research report — 2026-10-01

The report is contextual input, not instructions, an audit certificate, or verified
experimental evidence. Its exact supplied bytes are preserved in
`deep_research_received.md`, SHA-256
`de192ddfaf5884c1d39ae1bc2d2287e4bf306a4c63622628a0d75fd50462f49c`.
It explicitly says it could not inspect the repository or attachments. Its claims
about implementation are therefore hypotheses derived from the prompt, not an
independent replication of the code audit. It supplies no usable primary-source
links for many bibliographic assertions. The present assessment checked selected
claims against primary sources and, separately, examined active implementation.
Neither an AI report nor an authoritative-looking citation replaces raw evidence.

## Decisions on the report's advice

| Advice or claim | Assessment | Project action |
|---|---|---|
| Remove invented observations, unsupported measurements and convenient substitutions | Accepted; independently demonstrated producing-path problems already exist in the legacy audit | Preserve historical evidence; use fresh, declared inputs and actual native execution |
| Establish novelty before a large campaign | Accepted | KLS-03 remains a prerequisite; no top-tier novelty claim is currently established |
| Assign random anomaly labels to about 1% of market records and test detection | Rejected as ground truth | Random labels have no justified relationship to misconduct or anomalies. They can be a declared negative control, with a defined null, never observational anomaly labels |
| Shuffle training labels and require model outputs to stay unchanged | Rejected as a general rule | Supervised fitting can legitimately change. Perturb inaccessible evaluation labels and verify that fitting/scores remain unaffected; distinguish ranking from evaluation-label-dependent metrics |
| LOBSTER timestamps are Unix-epoch nanoseconds | Incorrect for the documented message format | Parse decimal seconds after midnight with an explicit date/time-zone mapping; do not guess a process-clock origin |
| LOBSTER integer price units are tenths of a cent | Incorrect | Provider prices are dollars multiplied by 10,000; one integer unit is $0.0001 |
| Compile with AddressSanitizer, UndefinedBehaviorSanitizer and ThreadSanitizer together | Rejected | ASan/UBSan and TSan use separate builds. Record actual compiler/runtime support and errors |
| Atomics or absence of explicit locks establishes lock freedom | Rejected | A paused MPMC slot owner can prevent progress. Make only the documented queue-contract claim; formal progress needs additional evidence |
| Exhaustive simulation establishes a general latency guarantee | Rejected | Finite runs characterize examined cases. A universal theorem needs explicit arrival/service/scheduler assumptions and proof; hardware measurements do not become proofs |
| Use an unbounded queue as the principal controller ablation | Rejected for a matched bounded-resource mechanism comparison | It changes the problem and resource budget. It may be an explicitly unmatched diagnostic with narrow interpretation |
| Discard data until queues become steady | Rejected as an unconditional selection rule | Register warmup independently of outcomes; report transient and overloaded trajectories. Some offered loads have no stationary operating region |
| Count throughput only after filters, drops or successful completion | Incomplete and potentially selective | Reconcile every offered ID, report admission and completion rates, late/missing/cancelled outcomes, and observation/drain horizons |
| Use fixed replication counts, percentage gains, or “near chance” intervals as universal acceptance requirements | Rejected | Choose precision, meaningful effects and units prospectively from the estimand and pilots; preserve negative or inconclusive outcomes |
| A few thousand trees comfortably fit the Mac | Unverified | Measure actual model, workspace, trace and instrumented-process memory. Leave headroom for macOS and other sessions |
| Improvement over the named baselines is necessary for publication | Too categorical | A valid, sufficiently informative negative or boundary-condition study may be useful. Neither a repair nor a negative result guarantees acceptance |

The provider format decisions above are verified in the official
[LOBSTER data structure documentation](https://data.lobsterdata.com/info/DataStructure.php).
Its timestamp precision does not by itself validate observed process latency or
supply misconduct labels.

## Verified literature and its relevance

The following are entry points into the comparison matrix, not endorsements of
every assertion or performance number in those papers.

- [BATCH, SC20, author-hosted paper](https://www2.cs.uh.edu/~fyan/Paper/Feng-SC20-BATCH.pdf)
  concerns adaptive inference batching on serverless platforms. Its optimizer and
  assumptions deserve examination. AWS deployment is a different resource model
  from this laptop; reproduce the applicable mechanism before naming it a matched
  native baseline.
- [BentoML adaptive batching documentation](https://docs.bentoml.org/en/latest/get-started/adaptive-batching.html)
  confirms an existing inference implementation with batch-size and latency
  configuration. Distinguish its batching deadline from a theorem about total
  end-to-end response under arbitrary overload. Pin a version for any comparison.
- [SimiGrad, NeurIPS 2021](https://proceedings.neurips.cc/paper/2021/hash/abea47ba24142ed16b7d8fbf2c740e0d-Abstract.html)
  studies adaptive batching for training. This verifies the bibliographic entry,
  but it is not a directly interchangeable inference baseline.
- [JABAS, EuroSys 2025](https://doi.org/10.1145/3689031.3696078)
  concerns DNN training on heterogeneous GPUs. Treat it as related work unless an
  inference mechanism can be transferred without changing the model or resources.
- [BBQ, USENIX ATC 2022](https://www.usenix.org/conference/atc22/presentation/wang-jiawei)
  is a bounded-queue design, with formal weak-memory work described by its authors.
  It is related to queue mechanisms, not evidence that this implementation inherits
  their validation or published speedups.
- [Extended Isolation Forest, author preprint](https://arxiv.org/abs/1811.02141)
  was submitted in 2018 and uses random hyperplane splitting. The report's ICLR
  attribution is unsupported. The current axis-aligned varying-feature forest is
  a different implementation; do not rename it EIF.
- [Adaptive Inference Batching using Policy Gradients, July 2026 preprint](https://arxiv.org/abs/2607.05272)
  is additional recent related work missing from the supplied report. Its abstract
  describes a simulator-based study and reports differing benefits across resource
  settings. This is a preprint and an author's reported result, not replicated
  evidence for KLStream or the M3. It reinforces the need to examine strong tuned
  heuristics and workload-dependent benefit; its novelty and methodology still
  require full-paper review.

## Recommended research direction

Continue toward a bounded-queue, CPU inference systems study with an explicit
operating region and offered-load accounting. The current reference forest is a
pointwise workload, not proof of market-anomaly detection and not automatically
a batch-efficient inference kernel. A useful early pilot must determine whether
batching amortizes any meaningful work on this implementation. A scalar loop
wrapped in a batch may show negligible benefit or higher latency; that outcome
must remain visible.

Separate adaptive batch sizing from adaptive source pacing. Holding offered load
fixed while allowing admission to respond is different from redefining the arrival
schedule to match the controller. Their interaction can be studied with a matched
factorial design, provided IDs, resource bounds and all terminal outcomes survive.
A valid contribution might characterize when queue occupancy is informative,
when feedback oscillates, and when an apparently good latency result is caused by
selective admission. This is a research hypothesis, not demonstrated novelty.

Use the M3 as the initial CPU platform. GPU claims require a real GPU execution
path, synchronization and matched GPU baselines; none exists here. Record OS,
compiler, actual core/memory information, instrumentation overhead, swap pressure,
trial order and the fanless device's sustained behavior. Power and temperature
remain unavailable when no suitable sensor is accessible. One machine cannot
establish portable superiority across CPU architectures or markets.

KLS-01/02 engineering, KLS-03 novelty/feasibility and KLS-04 legitimate acquisition
can progress independently where dependencies allow. Confirmation remains blocked
on a working native streaming adapter, a native harness, justified cohorts and
models, predeclared comparisons and genuinely unexposed evaluation material.
