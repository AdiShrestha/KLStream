# Second audit of the active research foundation — 2026-10-01

## Conclusion and scope

The migrated foundation was **not free of correctness or methodology errors**.
This audit found and repaired additional engine defects and factory acceptance
failures. The active tree is a better engineering foundation; it remains an
incomplete research system. No accepted market dataset, experiment, performance
result, anomaly-detection claim or research certificate was created by these
repairs. Absence of another observed defect is not proof of mathematical perfection.

The review covered every active C++ implementation header and the active factory
implementation, with producing-path analysis, parameter/lifecycle review, regression
inspection and counterexamples. Tests and policy documents were also inspected;
the complete supplied suite now includes previously omitted function-style tests.
`active_inventory.json` identifies file bytes, line counts and dispositions. It
is a census, not an assertion of measured branch coverage or proof about every
possible input. Historical factory-v2 code and legacy evidence remain quarantined
and were not promoted into current experiments. Large historical inventories and
compiled/cache artifacts are not manually certified by their existence.

The Deep Research input and critique are in `research_context/`. Its repository
claims were not independently verified by that report, and several recommendations
were scientifically incorrect. User instructions authorized substantive repairs;
incorrect subordinate factory rules were corrected with reasons and tests rather
than retained to pressure favorable results.

## Engine findings and repairs

| ID | Finding in the migrated foundation | Repair and practical boundary |
|---|---|---|
| A01 | Queue `close()` and `stop()` shared one boolean. A cancelled empty input became drained EOS, and the sink reported Finished | Separate Open/Closed/Cancelled states; cancellation cannot be converted to EOS. Operators reject cancelled inputs and prematurely closed outputs. Producer quiescence is still required before close |
| A02 | A callback using default `Event::make` could emit repeated zero sequence IDs | Source assigns its own sequence ID and rejects wraparound. Business/raw-record identity belongs in the payload; multi-source identity requires a source namespace |
| A03 | Rate changes credited the entire preceding interval at the new rate | Refill at the old rate before changing it. Deterministic clock APIs check backward time. An explicit initial clock supports independent budget tests |
| A04 | Atomic effective rate did not protect mutable tokens/clock state against concurrent setter/consumer calls | Mutex protects accounting; current rate remains atomically inspectable. This adds measurable overhead; no performance advantage is claimed |
| A05 | EMA began at zero and instantaneous pressure could come from a second, different observation | Initialize from the first valid sample, validate fractions, retain one raw snapshot, expose configurable thresholds. Approximate occupancy remains approximate |
| A06 | The batch deadline opened after controller selection, omitting selector time | Open at first-item receipt before selection. Controller cost is included. Scheduler and output backpressure can still delay publication; a deadline is not an end-to-end guarantee |
| A07 | Binary floating fractions could move nearest-rank histogram selection by one observation | Integer rational ranks; exact p50/p95/p99 fractions and a documented 1e-9 convenience grid. Histogram values remain coarse bucket bounds, not publication-grade tails |
| A08 | Event fields were uninitialized under default construction; counters could wrap silently | Initialize metadata/payload and fail on diagnostic count overflow. Source time is creation time, not offered time or admission time |
| A09 | Negative drain timeout requested source termination before rejecting the timeout | Validate before any state change. Runtime coordination remains serialized; callbacks must return for cancellation to join |
| A10 | Unrecognized operator status could produce an endless no-progress loop; comments described an unimplemented backoff algorithm | Reject unknown status; describe actual round/yield semantics and partial progress accurately |
| A11 | Forest split sampling lost precision through float rounding, and variant/parity claims were insufficiently specific | Retain double thresholds, use integer tree-height calculation, document varying-feature axis-aligned sampling and exact harmonic correction. No EIF or sklearn bit-parity claim |
| A12 | Score sanity checks did not independently reconstruct fitted tree structure and path scores | Read-only node/sample-count inspection plus a separate Python oracle validates partitions, leaf corrections, depth limits and score formula on fixtures. Persistence, cross-library RNG parity and broad model benchmarking remain future work |

The controlled historical executable `active_engine_counterexamples.cpp` was built
against the original foundation tag and against the repaired headers. The retained
`active_engine_before.json` and `active_engine_after.json` show:

- Cancelled drained/Finished changed from true/true to false/false.
- For 100 ascending microsecond buckets, the 7% nearest-rank value changed from
  7 to the correct lower bucket 6.
- A full-token interval at the preceding high rate was lost by a later rate
  reduction; the repaired implementation preserves that credit.

These are audit fixtures. The 20 ms sleep in the credit counterexample is a test
stimulus, not a measured performance claim. The deterministic rate-transition
regression is the principal budget check. Release, sanitizers, concurrent queues,
partial batches, callback failures and the independent forest oracle provide
bounded evidence for the documented supported contracts, not a universal proof.

## Factory findings and repairs

| ID | Finding | Repair and remaining limit |
|---|---|---|
| A13 | Successful audit did not require receipt signature verification | Verify every accepted execution receipt in record/audit. The original signature-removal fixture now produces BLOCKED |
| A14 | Unsigned execution metadata could diverge from the smaller signed payload | Sign an execution digest and independently check project, epoch, attempt ledger, nonce, seed, command, snapshot, dependencies, output, exit and wall-time bindings |
| A15 | Freeze inventory/root and key identity were not authenticated together | Authenticate freeze and verify its tree root; pin the epoch key. A same-user party possessing the key can still forge local records |
| A16 | Signature metadata was excluded from the signature; verification could create keys or accept a scheme differing from stored metadata | Version-2 signature covers scheme and full key fingerprint; strict decoding; verification never generates keys; incomplete key pairs never silently rotate |
| A17 | HMAC `.pub` contained the secret with ordinary file permissions; Ed25519 absence could silently downgrade signing | Both secret-bearing files use mode 0600. No Ed25519 downgrade. HMAC is explicitly symmetric and its verification file must never be publicly distributed |
| A18 | Typed argument dictionaries sorted values into a different order; legacy conversion discarded literal arguments; run and audit used different argv rules | Ordered arguments, one canonical resolver and validator for typed/legacy launches, source-contained entrypoint, rejection of unsupported wrappers. Python/stdlib is the only active runtime |
| A19 | Network-disabled policy was accepted without isolation; memory/process limits could be swallowed | Unsupported enforcement requests fail before execution. CPU limit is explicitly per process. Wall timeout kills the launched process group; this is not a malicious-worker sandbox |
| A20 | Worker inherited signer-key path and unrelated environment credentials | Worker receives a bounded environment; signed record binds its digest. Same-user filesystem access remains possible and is disclosed |
| A21 | Wall elapsed time was called CPU time and literal zero was called peak memory | Record wall time separately; unavailable CPU/memory are null. No fabricated resource measurement substitutes for an unimplemented collector |
| A22 | Binary/bytecode outputs could be omitted from output hashing; cache bytecode could escape frozen input review | Hash all regular outputs, including cache/binary files; reject importable frozen bytecode also inside `__pycache__`. Native dependencies require a future reviewed adapter |
| A23 | “Merkle root” was flat concatenation, and factory code hashing lacked explicit boundaries | SHA256 tree with length-prefixed leaves and distinct internal-node domain; validate leaf hashes. These digests establish byte bindings under cryptographic assumptions, not data authenticity |
| A24 | Result-path existence became SEALED assurance; a review boolean became INDEPENDENT assurance | Derive only structural/local authentication states. Review disclosure remains separate; READY status requires valid local authentication plus the prescribed review, and still does not certify scientific truth |
| A25 | Failed attempts could be retried without a new design; deletion could erase local attempt history | Authenticated attempt ledger, membership/nonce checks, and an amendment before retrying a failed attempt. Outside-workspace experiments and a malicious key holder remain procedural limits |
| A26 | Ranking scores were forced through probability calibration metrics | Declare score kind. Ranking mode computes discrimination/threshold metrics without Brier/log loss; probability comparisons alone may use calibration metrics |
| A27 | Sign-flip extremeness used an absolute 1e-14 tolerance, making p-values depend on measurement units | Normalize contrast magnitudes for the extremeness calculation; verify unchanged p-value when a contrast is scaled to 1e-20 |
| A28 | F1, precision and accuracy were assigned universal chance thresholds; NOT_SUPPORTED matched the word supported | Restrict the relevant ranking chance diagnostic and use exact verdict tokens. Negative results retain their meaning |
| A29 | Flat sensitivity or fewer than three failure categories could cause failure | Flat response is a diagnostic; zero failures require declared search coverage; valid observed categories need no invented minimum count. Invalid prevalence still fails |
| A30 | Budget-limited nonconvergence blocked comparisons indiscriminately | Preserve the registered budget result with a diagnostic; reject an explicit unsupported convergence claim. Training needs method-specific rationale rather than an arbitrary epoch guarantee |
| A31 | Hardware service-time rate was called throughput; phase/warmup exclusions and whole-run durations could distort denominators | Require explicit trial endpoints and one-batch counts; separate aggregate service rate from completion rate over the observed inference horizon. Neither is an offered-load systems guarantee |
| A32 | Code directories could evade source scans; non-Python text was parsed as Python | Expand declared code directories; identify unsupported source languages as review requirements. A native provenance adapter remains unimplemented |
| A33 | Some alleged attack tests checked only setup inequalities or metadata existence; registry presence was mistaken for executed coverage | Replace weak source-mutation, runtime-substitution, deletion and reproduction tests with actual rejection paths. Registry verifies fixture definitions, not execution or all possible attacks |
| A34 | Standalone verifier used different signature bytes, loose JSON and wrong receipt nesting | Independent strict verifier handles signed freeze/ledger/nested execution records and execution digests. Embedded release labels are untrusted; byte integrity alone never validates assurance |
| A35 | Test runner omitted module-level test functions and some tests leaked key-directory environment state | Execute the supplied function fixtures too, isolate keys per test, reject optimized assertion-disabled test execution. Exact observed results are in the validation receipt |
| A37 | Coverage output called every mapped principle mechanized, with unrelated attribution for authorization and reproduction identity | Describe static mapping scope, record procedural/shared-check rationales, and attribute actual receipt/attempt validation. Correct module identities replace mislabeled engine callables. Nontrivial code is not semantic enforcement proof |
| A38 | Finite negative losses and valid early-stopping budget exhaustion were rejected | Accept signed minimized objectives and registered cap outcomes with diagnostics; premature runs and unsupported convergence claims still fail |
| A39 | Quantile interpolation could overflow across finite extremes; standardized effects could underflow variance after a unit change | Use bounded-sign interpolation and normalized standard deviation; independent extreme/tiny-scale vectors check the result |
| A36 | Numeric coercion, nonfinite nested p-values and vacuous helper contracts had inconsistent acceptance | Strict plan numeric fields and plausibility values; safe numeric-overflow rejection; empty contracts and unsupported deep nesting fail; no matched trace IDs cannot silently pass |

Old 3.3.0 signature receipts are not silently recertified under the repaired scheme.
The original Git tags preserve that implementation and evidence. A changed factory
hash requires a new explicit epoch for a real study. No active KLStream research
epoch exists to migrate or recertify.

A test-edit error during this audit temporarily removed classes by matching a
repeated method name. Diff/count inspection caught it; the original classes were
restored and edits applied by class/method. All 92 original methods in that file
remain. Intermediate failed runs were retained in the verification history; they
are not reported as successful checks.

## Scientific status and direction

Continue KLS-01/KLS-02 and the KLS-03 feasibility/novelty memo. The strongest
candidate is a transparent CPU systems study of bounded queues, adaptive batching,
source pacing and overload accounting. The reference forest is a legitimate
pointwise test workload, but wrapping scalar inference in batches does not by
itself create computational amortization. A pilot should be allowed to show no
benefit. Strong tuned fixed/deadline policies and matched memory/thread budgets
are essential; selecting an obviously weak fixed batch makes the study unfair.

Research blockers remain: a native streaming profile in the actual factory
lifecycle, attested source/build/binary identity, a finite native replay/inference
harness, independent raw event/score recomputation, offered-ID conservation,
authentic permitted data, frozen cohorts/model selection, complete offered-load
latency and censoring policy, justified independent units, pilot-informed precision,
and genuinely unexposed confirmation. No labels should be invented to squeeze a
systems study into the classification profile. Neither a signed result nor correct
AUC arithmetic establishes honest training, causal validity or label isolation.

The laptop bounds the first study. It does not establish GPU acceleration or
cross-machine performance. User-supplied M3 core/memory specifications are context;
actual platform metadata is recorded separately where readable. Restricted
`sysctl` access was initially unavailable; the final permitted query independently
confirmed Apple M3, eight logical CPUs and 17,179,869,184 bytes of memory. The GPU
core count remains author-supplied context, with no GPU execution claim. Storage availability is
a time-specific local observation, not a study budget guarantee. Avoid simultaneous
large model fits, swap and uncontrolled background work; choose concurrency and
retention budgets from measured pilots rather than guessed comfort margins.

For other agents, root `plan.md` remains the comprehensive implementation contract.
Its second-pass status section distinguishes repaired foundation properties from
unaccepted KLS contracts. The complete research system must still be built and
challenged. No guarantee of top-tier acceptance, universal stability, perfect
fairness, complete bug absence or honest external producers is warranted.

The independent bundle probe initially used the wrong execution field nesting and
raised KeyError before its mutation check. That failed fixture run is retained; the
probe was corrected to the actual top-level interpreter_sha256 binding.

After the coverage map was corrected to document two procedural/shared-check
rationales, an old test still expected all 23 entries to resolve to distinct
callables. Its failure is retained; the test now checks 21 actual callable
references plus both explicit rationales and the bounded scope disclosure.

## Final observed verification

The current verification receipt reports **326 factory tests passed**, two CTests
(primitive engine correctness and independent forest reference) in Release and
ASan/UBSan builds, a separate successful TSan fixture run, and **21 public headers**
compiled independently. Signature removal yields BLOCKED; a clean independently
packaged bundle verifies three local signatures, and a rehashed bundle with altered
execution metadata fails. The invalid root template refuses certification (31).
All source bytes covered by the receipt remained unchanged during that execution.

Intermediate failures are preserved with an explicit retention limit in
intermediate_verification/README.md. These observations are fixture verification,
not a scientific experiment, performance result or complete semantic proof.

The first clean-checkout source comparison included five ignored pytest-cache
files in the verification manifest. The clean build and all tests passed, but
the manifest comparison correctly failed. The verification tool now excludes
generated caches, and the census labels them inventory-only. This auditor-tool
correction does not change engine/factory code or make caches research inputs.
