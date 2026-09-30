# KLStream / Brolq: research rehabilitation and submission plan

**Audit date:** 2026-09-30. **Active project:** this new folder and its replacement GitHub main. **Author hardware:** Apple M3 MacBook Air, 8 CPU cores, 10 GPU cores, 16 GB unified memory, 512 GB storage, as supplied by the author. **Current status:** correctness foundation migrated; research system incomplete; no submission readiness or new empirical result claimed. **Audience:** the author, an Architect session and an Implementor session with access only to this repository.

This plan is deliberately detailed. It records observed defects, the boundaries of the audit, the engine migration, the factory integration problem, a defensible research design, executable implementation contracts and release criteria. It must not be shortened into a checklist that discards its assumptions. The goal is an honest, reproducible systems study. A negative, null, mixed or inconclusive result is acceptable. No desired speedup, AUC, stability property, significance verdict or publication outcome is a requirement.

## 1. Decision and scientific status

The legacy repository cannot currently support its strong scientific claims. The most serious problems are demonstrated rather than inferred from unattractive coding style: the academic-sample files match a local generator byte for byte; the main experiment matrix computes simulated quantities without invoking the C++ engine; an ROC/PR figure generator constructs curves without predictions; the verdict path declares support despite a multiplicity-adjusted nonsignificant result; selected statistical and split functions fail small counterexamples; native lifecycle/model defects are reproducible; and the supplied factory accepts a signature-deleted execution while claiming sealed assurance.

These defects invalidate the affected evidence and its interpretations. They do not establish the author's intent, prove that every legacy measurement is invented, or mean that the underlying idea has no merit. Some legacy microbenchmarks really execute C++ and collect clock values. They still do not validate the separate simulator-based paper matrix, market authenticity or matched comparison design. Treat evidence by producing path and scope, not by the presence of a file named `verified`, a large result directory, a certificate, a manuscript or a successful exit code.

The active tree therefore starts with a small, reviewed engine foundation rather than all legacy applications. Legacy research data, results, plots, models, simulator runners, paper claims and verification certificates remain historical. Reusing them as confirmatory evidence is forbidden. The new engine has tested corrections, but is not an assurance that every possible error is fixed. The complete research application must be implemented and validated through the contracts below.

The likely research subject is **adaptive microbatching under bounded queues and realistic offered load on a resource-constrained multicore machine**. Isolation Forest can provide one legitimate pointwise inference workload. Market replay can provide one authentic input trace if acquired lawfully. Neither is evidence that the system detects spoofing, wash trading, intent or real market anomalies without an independently justified labelled task. Adaptive batching itself has substantial prior art; novelty must be established before building a large experimental campaign.

## 2. How future agents must use this repository

Start with `README.md`, this entire plan, `project/agent_handoff.md`, `docs/ENGINE_CONTRACT.md`, `docs/audit/AUDIT_SCOPE.md` and the active factory documents. The authority chain remains user instructions → factory constitution → applicable specification → frozen methodology and machine plan → implementation. This plan supplies project requirements and identifies gaps in the current machine implementation; it does not invent a new executable schema by assertion.

Use numbered contracts KLS-01 through KLS-15. The Architect writes estimands, admissible evidence, dependencies and acceptance rules; the Implementor writes actual source, tests and run receipts. Either may challenge an invalid specification. A contract is accepted only with inspectable artifacts and executed checks. Do not declare completion because the expected headings exist. Every contract report lists what passed, failed and was not executed.

Keep exploration and confirmation separate. The old results, this audit and future pilot runs are already observed. A new freeze timestamp does not erase that exposure. No frozen test may be reused for tuning or selecting a narrative. Amendments preserve earlier epochs and include the observations that motivated them. Missing data or an unsupported machine profile blocks the dependent scientific claim, while unrelated engineering may continue.

The supplied `project/research_plan.json` remains an invalid template. `project/methodology.md` explicitly says DRAFT / NOT FROZEN. Do not populate either with convenient invented cohort counts, fake labels, placeholder source IDs, copied winning metrics or commands that do not exist. Do not run `certify` to manufacture project status during rehabilitation.

## 3. Scope, coverage and evidence map

The legacy root was `/Users/adi/adi/brolq`. Its local rehabilitation branch was at `83545b7c845454af309794d08a1ec2d41220a7db`; public main was `bc095f0be747216b59de08ec0bbf06163cf67553`. The new root initially contained the supplied Software Factory 3.3.0 template, empty project source/data and a placeholder research plan. There was no new engine implementation or Git history in that folder.

The census covered every non-`.git` filesystem file: **12,844 files**, including **11,735 generated/build/cache/snapshot files** inventoried by path and size. The other **1,109 files** were hashed. **537 text files** were scanned, Python ASTs were parsed, **94 JSON files** were parsed and **537 CSV files** were streamed through their bodies. The inventory groups 163 legacy source files, 632 historical evidence files, 266 historical claim/control files, 37 other files and 11 superseded factory-v2 files. Counts describe the census, not research sample sizes. The full categorized inventory and source disposition appendix allow a later agent to locate every item.

This is not a claim that every binary, every generated trace row or every historical paper sentence was manually semantically verified. Generated files and old compiled objects were not trusted merely because their existence was indexed. Unknown pickle artifacts were not executed. Manual inspection prioritized complete producing paths and high-risk native code; independent counterexamples then tested specific defects. There may be additional defects outside those paths. An honest scope statement is preferable to saying that a scan proved perfection.

| Evidence | What it supports | What it does not support |
|---|---|---|
| `docs/audit/legacy_inventory.json` | File identity, size, classification, hashes where specified | Authenticity, correctness, completeness of a scientific result |
| `legacy_text_index.json` | Authored text/function scan and suspicious-path triage | Proof that a searched string has the same meaning everywhere |
| `legacy_json_index.json`, `legacy_csv_index.json` | Parsed schemas, headers, dimensions, streamed body diagnostics | Valid measurement origin or valid statistical units |
| `legacy_evidence_excerpts.md` | Exact selected legacy paths and line-numbered producing code | An executable replacement for all legacy source |
| `defect_probes.json`, `probe_legacy.py` | Reproducible split, metric, authenticity and factory counterexamples | New research performance or a valid market cohort |
| `legacy_cpp_counterexamples.*` | Controlled native defect examples against legacy headers | The frequency of those defects in every previous run |
| `verification_summary.json` | Commands, environments and checks executed in this migration | Research readiness, universal race freedom, benchmark results |
| `git_migration.json` | Exact legacy refs and replacement commit boundaries | A scientific endorsement of preserved artifacts |

Audit scripts belong to the forensic audit directory, not the research acquisition/runtime path. They deliberately invoke legacy functions on fixtures and must never be dispatched as a research experiment. Their successful reproduction of a defect is a software observation with a narrow interpretation.

## 4. Finding severity and interpretation

**P0** means the affected evidence or release assurance is inadmissible until repaired; **P1** means a major correctness, comparison or inference risk; **P2** means reproducibility, maintainability or claim-boundary work that still matters for submission. “Confirmed” means an inspected producing path or executed counterexample establishes the stated behavior. “Unverified” means a claim is unsupported by the examined evidence, not automatically false.

Findings below name legacy paths relative to the preserved legacy root. Their bytes/hashes and excerpts are available in this folder. The future active implementation may use new paths. Do not silently resurrect an old function with its original name and assume its previous certification transfers.

### F01 — Generated observations labelled as an academic market sample (P0, confirmed)

`source/experiments/preprocessing/download_sample.py` imports a network library but generates local deterministic data when the files are absent. The receipt names the LOBSTER academic benchmark, supplies a source URL and a literal retrieval date. The operation producing the CSV files is not an authenticated retrieval of provider bytes. The generator is visible at lines 30 onward; generation is invoked around lines 84–86 and observational-sounding receipt fields around 103–109 in the preserved excerpt.

The audit regenerated both CSV files in a temporary directory. Message SHA-256 `8038464096ec981209fe3e2518bb1b033aa0ee1ce0cb34d0320f5345cace2bfd` and order-book SHA-256 `0e5e2482d24927272120ca4d67edd747964c5af25bfe38e1a52c6c78f9ec7613` exactly match the existing legacy files. This establishes that these particular files are the generator's output. Calling them an observational academic sample is inadmissible. Preserve them as disclosed fixtures only. Acquire fresh provider bytes through KLS-04; never “fix” the old receipt's date and relabel the same bytes.

### F02 — Main matrix measures an algebraic simulation rather than the engine (P0, confirmed)

`source/experiments/run_full_matrix.py` constructs the headline matrix through `simulate_test_run`. It does not dispatch the native application. Constants such as 500 ns fixed cost and 50 ns point cost feed a formula. Occupancy depends on a feature called volume and simple queue-depth arithmetic; latency components include terms proportional to occupancy and batch size, and fixed cost divided by batch size. Dropped events are assigned zero rather than reconciled through event identities.

This could be a declared analytical model, but it is not observed hardware latency. The resulting p99 is a percentile of computed values, not a percentile of measured per-event completion times. It has no valid finite-buffer, arrival/service or clock model. The `volume` feature is log-transformed top-book depth, not measured incoming queue pressure. Small integer queue increments can remain zero on these values, keeping adaptive W near 10. The resulting preference for certain windows is partly built into the chosen equations. Quarantine the matrix; replace its producing path with KLS-07 native execution.

### F03 — Amortized service cost is confused with event latency (P0, confirmed)

The term `t_fixed / W + t_point` is an amortized work estimate per event. It does not represent how long a particular point waits to form a batch, waits behind earlier work, then completes. A batch can have lower amortized cost and worse oldest-event latency. Adding a guessed freshness term does not turn the formula into a measured service process. The main matrix therefore cannot substantiate statements about bounded end-to-end tails, congestion or runtime responsiveness.

Keep analytical equations as declared models with explicit assumptions, units and error checks against measurements. Do not choose their constants to reproduce the old headline. Measure batching, queue waiting and service separately, reconcile them to pointwise timestamps, and report both throughput and latency under a fixed offered workload.

### F04 — Evaluation split can become its own training/tuning data (P0, confirmed path)

`source/experiments/runners/experiment_runner.py` fits a model on normal-labelled rows of the selected evaluation split and chooses a threshold using that same split. If the count is small, training can use all rows. This is evaluation leakage. Separately, `load_dataset_split` falls back to the whole dataset when its manifest or matching dataset information is missing. The probe requested test data with a missing manifest and received 10,000 rows.

The full-matrix runner has a separate training-slice path, so do not inaccurately say every training path has this exact leakage. Its simulation remains invalid for the separate reasons above. Replace both paths with a strict split/cohort join that fails closed on missing or mismatched manifests. Fit preprocessing, model and threshold from allowed train/validation partitions only. Make it impossible for labels from test to reach any fitting callback.

### F05 — Detection curves are constructed without predictions (P0, confirmed)

`source/experiments/plot_figures.py:generate_figure_4_roc_pr` takes an output directory, not raw scores and labels. It creates an ROC using `fpr ** 0.35`, a PR curve using a square-root expression, chosen AUC labels and a chosen chance prevalence. These are illustrative equations, not empirical detection curves. The ROC expression's area also differs from its displayed 0.85 label, reinforcing that the figure has no traceable metric computation.

Remove these curves from any paper evidence. A figure must reference immutable prediction hashes, filter rules and the exact plotting command. Independently computed scalar metrics must match the plotted curves and conventions. A fixture plot may be used to test rendering only if visibly marked and excluded from release manifests and claim ledgers.

### F06 — Verdict ignores multiplicity and can ignore direction (P0, confirmed)

`source/experiments/evaluate_falsification.py` checks raw p values rather than the adjusted comparison family and uses absolute effect magnitude where direction matters. The preserved fixed-W500 summary has raw p=0.03125, adjusted p=0.25 and `is_significant=false`; the verdict path can nevertheless declare support. The Markdown writer includes unconditional supported/zero-drop assertions that do not faithfully render all possible computed verdicts.

Verdicts must be generated by one frozen machine-readable decision function, with direction, uncertainty, multiplicity and all required conditions. The independent analysis must verify that function's inputs. “Not significant” is not equivalent; “large absolute effect” is not necessarily beneficial. A report must render the actual computed state, including unsupported, contradicted, inconclusive, unavailable and failed.

### F07 — Research claims and executable criteria disagree (P0/P1, confirmed)

Research framing, falsification criteria and verdict implementation use differing comparator sets, percentages, effect cutoffs and meanings of the claims. Fixed W10 versus W500 is not an interchangeable contrast. A hash of one criteria file does not bind the full producing code, input cohort, selection procedure, outcomes and evidence interpretation. An anti-HARKing sentence is not a preregistration receipt.

Create a single claim ledger that joins each claim to its population, estimand, comparison, metric, direction, minimum meaningful effect, uncertainty rule, multiplicity family and experiment IDs. Render prose from that ledger. The freeze includes code/data/config/environment/analysis and discloses all prior observations. Registering it locally establishes a byte boundary; stronger timestamp/external registration remains a separate procedural property.

### F08 — Exact testing, sample units and statistical interpretation are unsound (P1, confirmed)

The legacy protocol speaks of five independent datasets/seeds while the statistics can use six corpus summaries, including the mislabeled academic fixture. With five nonzero independent pairs, the smallest ordinary two-sided exact signed-rank tail probability is 2/2^5=0.0625; with six it is 0.03125. Thus the observed probability pattern does not establish broad significance. Holm correction makes it less favorable. Five or six summaries are not enough merely because a document requires five seeds.

Different synthetic seeds measure conditional generator variability; a market day, a training seed, an event and a repeated hardware trial are different units. Cliff's delta treats marginal samples and does not replace a paired contrast. The implementation's large-n Wilcoxon path ignores relevant ties, while prose overstates exactness or absence of assumptions. Tight bootstraps over deterministic computed formulas do not quantify real hardware uncertainty. Choose the correct independent units and a justified precision/power strategy in KLS-09/KLS-12.

### F09 — AUROC and PR computations conceal degenerate cases (P1, confirmed)

The legacy metric implementation returns AUROC 0.5 for a single-class cohort, concealing that AUROC is undefined there. Its PR integration depends on order within tied scores. For labels `[0,1]` and scores `[0.5,0.5]`, the audit obtained 0.25; reversing labels gave 1.0. Standard average precision for this two-row tie group is 0.5. Changing row order must not change a ranking metric.

Use explicit metric names and conventions. AUROC gives half credit to tied positive/negative score pairs and is unavailable without both classes. Average precision groups equal thresholds and is not trapezoidal PR area. Return structured unavailable status with a reason instead of a numeric success surrogate. Retain prevalence and sample counts. An unlabelled systems trace is valid input without becoming a fabricated binary-classification task.

### F10 — “Shuffled occupancy” is not the stated causal control (P1, confirmed)

The shuffled baseline selects random windows rather than applying the same controller to a shuffled observation trace with matched support and sampling. That intervention changes multiple mechanisms. A periodic control uses batch-count updates despite an event-period name. Controller dispatch uses substring rules that can route descriptions containing “adaptive” incorrectly. These controls cannot identify the causal role claimed for occupancy feedback.

Use enumerated policy IDs, exact schemas and explicit units. Mechanism ablations must alter the specified component and keep the others fixed. Distinguish an open-loop random-window policy from shuffled-feedback, time-shifted-feedback and constant-feedback controls. A permuted trace intervention is a diagnostic; do not assert closed-loop causal equivalence when the controller also changes the subsequent observations.

### F11 — Python and native adaptive policies implement opposite behavior (P1, confirmed)

The Python EMA policy grows windows under pressure and starts near minimum W10; the native controller shrinks windows under pressure and starts near maximum 256. They use different ranges and possibly different observed edges. These are different algorithms, not an implementation/reference pair. A paper cannot describe one while reporting the other.

Feedback sign depends on the controlled plant. Larger batches may increase throughput and clear an input backlog, but increase formation delay; downstream queue pressure may require another action. Fix the observation edge, event-versus-batch capacity units and actuation path before choosing a sign. The new controller requires explicit direction and claims neither sign is universally correct.

### F12 — Sensitivity and “10× burst” are not closed-loop workload tests (P1, confirmed)

`run_sensitivity.py` drives imposed noisy occupancy phases, invokes formula-based costs and emits a literal `limit_cycle_detected: false`. Rise/recovery diagnostics can default to zero. Changing occupancy from 0.1 to 0.9 is not proof of a tenfold offered arrival rate. The workload does not close the loop through measured native queueing and service.

Use actual arrival schedules with measured release/admission timestamps, a fixed denominator for “10×”, measured queue trajectories and an operational oscillation detector. Report unavailable recovery when thresholds were not crossed, rather than zero. Sensitivity curves may be flat; that is acceptable. Fabricating varied curves to demonstrate effort would repeat the failure.

### F13 — Market units, identities and row pairing need correction (P1, confirmed)

The newer preprocessing path divides LOBSTER integer prices by 100 where official dollar-price encoding is 10,000. Another older path intentionally works in cents; those conventions need explicit names rather than an accusation that all numeric operations are wrong. Message field two is order ID, not a chronological row number. Order IDs can recur, so using them as unique sample IDs corrupts joins. `zip` can truncate a mismatched message/book pair silently.

Parse and validate provider schema, integer price ticks, decimal exchange seconds, row ordinal identity, order ID identity and line-count equality. Account for sentinel/empty levels, halts, event types, ordering, crossed books and nonfinite values with reason-coded policies. Retain original rows and rejected-row diagnostics. Never silently zero missing features or round small variances to zero before modeling.

### F14 — Feature meaning and synthetic truth are overstated (P1, confirmed boundary)

The legacy feature named volume is a log transform of displayed top-book sizes; it is neither traded volume nor measured incoming work. Rolling volatility is an exponentially weighted variance without a declared time/standard-deviation convention. Synthetic time scaling starts from milliseconds interpreted as seconds in one generator, and uniform gaps are not a Poisson arrival process. Injected extreme features are not independent labels of real wash trading, spoofing or flash crashes.

Create a feature dictionary with equations, units, state initialization and dependency times. Rename depth and variance honestly. Declared stress traces can test systems and known injections can test sensitivity to those injections. They cannot establish real market detection quality. Preserve clean/raw origins and perturbation overlays so a label never ambiguously means observed intent.

### F15 — Model format and feature interfaces disagree (P1, confirmed)

Python artifacts can wrap pickled estimator payloads under the same KLIF magic/version used by native tree nodes, while the two payloads are incompatible. Native and Python paths use different feature dimensions. A manifest may record configured psi=256 despite fewer fitting rows and seed descriptions do not always identify actual estimator RNG. An unknown pickle loader is also an unsafe authenticity boundary.

Do not migrate model blobs or these loaders. Use a new portable format with declared dimension, feature schema/hash, exact tree nodes, effective psi, scoring convention, seed/RNG algorithm, compiler/tool provenance and whole-file checksum. Reject wrong versions, counts, indices, cycles, nonfinite thresholds, oversized allocation and incompatible schemas before use. Golden hand-written trees test scoring independently of training.

### F16 — Native Isolation Forest normalization and fitting accept invalid states (P1, reproduced)

The old native forest normalizes paths using configured psi even when actual training rows are much fewer. With one tree, configured psi=256 and two training points, the probe score was approximately 0.934579; path length one with effective psi two gives 0.5. Fixed feature-resampling retries can stop prematurely despite a varying feature. Empty/unfitted/zero-tree states and malformed loaded trees are not rigorously rejected.

The new in-memory forest uses actual effective psi, validated finite inputs, enumerated varying features, reproducible fresh fitting RNG and explicit preconditions. It uses exact harmonic c(n), which is a documented mathematical convention rather than silently interchangeable with an asymptotic reference implementation. KLS-06 still owes portable serialization, reference comparisons and a learning/selection procedure. Correctness examples are not evidence of better market accuracy.

### F17 — Native queue storage and release-mode validation are flawed (P1, confirmed/reproduced)

Old queues allocate raw storage and assign typed objects without an adequate C++17 lifetime construction story; per-slot atomics are implicated too. Capacity checks rely on asserts that disappear under NDEBUG. The probe accepted SPSC capacity three in release mode, violating its ring-mask requirement. SPSC uses C−1 usable slots while MPMC uses C, so matching nominal capacity alone is unfair.

The migrated queues construct typed arrays and reject invalid capacities in release mode. Use comparable usable capacity and bytes in experiments. Close follows producer quiescence; destruction follows joins. Approximate occupancy is not a losslessness proof. A mutex-free implementation does not establish a formal lock-freedom theorem; the original bounded MPMC algorithm's author explicitly distinguishes that guarantee.

### F18 — Runtime stop can strand work after downstream exit (P1, reproduced)

Old runtime stop proceeds through workers sequentially in reverse order. The old drain mechanism is a finite number of local tick passes and treats temporary idle as completion. In a deterministic fixture, a delayed upstream map waits until downstream shutdown, then emits during residual draining: the sink receives zero and one event remains in its output queue. This establishes an attainable loss mode, not the exact loss count of every old experiment.

The new runtime distinguishes temporary Idle from permanent Finished, uses propagated closed/drained edges and joins completion, and separates graceful drain from immediate cancellation. Tests cover natural EOS, early drain, non-topological registration, small queues and exact IDs. KLS-01 must still review graph constraints, cancellation behavior and broader concurrency interleavings. A stop return code alone never implies zero loss.

### F19 — Window metadata, tails and batch limits distort semantics (P1, confirmed)

Legacy adaptive/fixed paths use different representative event timestamps, sometimes the latest point rather than oldest. A window's maximum anomaly score can be broadcast to members as if it were each point's score. Final partial windows may be lost. Controller maxima can exceed a fixed 256-event storage bound. Time windows can grow without an adequate resource policy.

The new batch primitive retains every constituent event and validates its maximum. Count windows flush final partials. Aggregates remain aggregates and need explicit member lineage before research use. Pointwise inference must score and output every point. If a window-level detector is studied, define that different task, its truth aggregation, size-dependent threshold and evaluation unit in a separate claim.

### F20 — Replay and sink behavior can alter the workload or misstate decision time (P1, confirmed)

Old replay can loop rather than publish EOS, can crash on empty rows, accepts problematic speed factors and caps sleeps in ways that change the declared offered process. Source timestamp reused as detection timestamp is not measured decision time. Silent sink I/O failure and repeated sequence behavior can hide missing output. These issues prevent a defensible offered/admitted/completed reconciliation.

No financial replay application was carried forward. KLS-07 implements finite replay with a frozen schedule, explicit scaling, unique IDs, measured lateness, monotonic process clocks and checked output writes. File buffering must be separated from inference completion. A source constrained by backpressure cannot be represented as if its offered arrival rate stayed unchanged.

### F21 — Telemetry can race, quantize or conceal tails (P1, confirmed)

An old app reads controller state concurrently without synchronization. Global telemetry paths are reused across runs. Occupancy divides by nominal capacity in places where usable capacity differs. Histogram quantiles described as exact are quantized; overflow can clip a real tail to 10 ms; empty data returns zero. Reporter rates use a nominal interval rather than measured elapsed time. An undefined race cannot be accepted because a graph looks smooth.

The foundation diagnostic histogram retains actual mean observations, represents overflow by infinity and errors on empty data. It does not replace lossless event telemetry. Research quantiles must be recomputed offline under a fixed definition. State snapshots use atomics or synchronized immutable messages. Record actual timing intervals and distinct run directories. The trace's missing rows and overflow must be audited, not silently dropped.

### F22 — Hardware/scheduler and microbenchmark claims exceed executed scope (P1/P2)

Apple QoS requests are not guaranteed P/E-core affinity. Advertised work stealing is not substantiated by static worker assignment. An auto-selected M3 build flag on any ARM target is not a valid hardware identity. Small microbenchmarks use differing tree counts, subsample sizes and feature dimensions from the headline task, with incomplete warm-up/repetition/thermal documentation.

Keep any real microbenchmark as exploratory evidence of its exact command/configuration. Do not combine it with simulation results as if all rows came from one end-to-end pipeline. The new engine names scheduling hints honestly, downloads no dependencies and makes no M3 speed claim. Hardware must be measured at runtime and unavailable fields recorded as unavailable. The ten GPU cores are not used by this CPU implementation.

### F23 — “Independent verification” often prints expected counts or verdicts (P0/P1, confirmed)

Examples include `paper/verify_eval_independent.py`, `source/benchmarks/verify_e2e_independent.py`, `scripts/verify_cert_independent.py` and `scripts/verify_bundle_independent.py`. Some paths print constant claimed results/counts; others check headings, JSON existence or list lengths and call that independent verification. Additional paper/defense/TeX/plan/receipt scripts repeat this pattern. A constant 98.02%, zero-drop value, 69/67/60/10/5/8 count or TOTAL_ARTIFACTS value is not a raw-data recomputation.

Do not migrate these scripts as release gates. Structural checks may still be useful if named as structural. For each claim, mutate raw data, labels, order, IDs, timestamps, executable and signatures, and require the independent verifier to detect the corresponding failure. It must fail nonzero on inconsistency and report diagnostic evidence rather than a hardcoded successful conclusion.

### F24 — Paper audit and historical release artifacts are not scientific attestation (P0/P1)

`paper/audit_claims.py` uses expected constants and aggregate comparison rather than a full raw-origin join. Its output can include unconditional pass language and perfect match-rate claims. Manuscripts and certification files contain stale claims from different producing versions. Bibliography key existence does not establish accurate author/year/title or relevance.

Rebuild the paper only after actual results and independent analysis exist. A claim graph binds each sentence/table/figure to accepted evidence. Every cited primary source must be read for the statement it supports. Correct old public claims where the author had previously distributed them, using an explicit rehabilitation notice rather than silently suggesting the earlier evidence was valid.

### F25 — Packaging, clean clone and license scope are inconsistent (P2, confirmed)

Legacy README says MIT while actual engine license/metadata indicate AGPL. Ignoring results does not remove previously tracked files. Dependency downloads, compiler defaults, missing acquisition and ignored outer-factory state undermine clean-clone reproducibility. There are large self-snapshot bundles in other local refs; copying them into the new tree would amplify repository size without producing evidence.

The active engine retains AGPL in `source/LICENSE`; supplied factory terms are preserved separately in `factory/LICENSE`; root LICENSE explains scopes. No new data is migrated. Builds are offline. KLS-13 validates a clean checkout and lawful data access; KLS-14 chooses licenses for new research artifacts without assuming all third-party bytes can be redistributed. Preserve Git history with tags rather than force deleting the scientific record.

## 5. Factory 3.3.0: compatibility and blocking gaps

The factory's objectives align with this rehabilitation: immutable attempts, strict paths, frozen decisions, independent metrics, honest negative results and minimal human workflow. However, an objective written in a constitution is not an implemented enforcement property. The existing full self-test suite passed **276 tests** when permitted local Unix sockets; a restricted-sandbox run had one socket PermissionError. Both facts must be reported accurately. Passing self-tests does not negate the independent counterexample below.

### G01 — Streaming claims have no native machine domain (P0)

`factory/engine/plan.py` accepts `binary_classification`, its fixed list of classification metrics and seed-based fixed-test comparisons. Latency, throughput, deadline completion, backlog and ID conservation are not native profile metrics. A latency claim cannot be encoded as accuracy or a fake prediction score merely to pass the parser. An unlabelled real trace should not receive manufactured anomaly labels to satisfy both-class floors.

Implement a versioned streaming-systems domain adapter with lossless native event observations, exact cohort/ID joins, metric definitions and an independently implemented recomputation path. Use a separate classification sub-study only when legitimate labels exist. The adapter must participate in the actual `freeze → run → record → audit → certify → bundle verification` lifecycle, not just validate a standalone JSON shape. Retain strict classification behavior for existing projects.

### G02 — Native execution and typed/legacy command paths disagree (P0/P1)

The typed runtime whitelist currently contains only `python-cpu-v1`. It uses isolated Python execution including `-S`, so installed site packages are not automatically usable. No native compiler/binary runtime is attested. Typed argument dictionaries resolve by ordering values rather than treating key names as command-line flags. Plans retain a legacy command requirement, while audit compares recorded argv against the legacy command even when typed execution resolved another argv.

Add a native-cpu runtime contract bound to source/build/binary hashes, toolchain, library resolution and allowed executable. Define one canonical argument representation and use it for execution and audit. Legacy conversion must pass the same validation, not become an escape hatch. Reject shell/inline executable substitution and unbound external binaries. Document Python package/runtime isolation honestly instead of silently assuming a requirements file is active under `-S`.

### G03 — Missing signature still yields sealed assurance (P0, reproduced)

`factory/engine/supervisor.py` has receipt signing/verification functions, but the audited lifecycle does not require successful cryptographic verification of the complete execution binding. The independent fixture removed `supervisor_receipt` from `execution.json`. Audit had no errors before or after removal. `_compute_assurance_level` then returned `SEALED_EVALUATION_ATTESTED`.

Fix acceptance, not just presence checking. Verify signature and canonical signed fields, nonce uniqueness, project/epoch/experiment/attempt/seed, resolved argv, frozen source, runtime/binary, dependencies, input manifests, output root/hash, exit status and actual timing fields. Reject missing, malformed, expired/unbound, replayed or altered receipts. Add the exact counterexample as a full lifecycle regression. The acceptance state must reflect what was checked, not infer sealing from a result-path field.

### G04 — Signing and holdout threat boundaries are overstated (P1)

A signer key readable by a worker running under the same user is not inaccessible merely because it is outside the project tree. Environment-selected key paths can also be shared. In the HMAC fallback a `.pub` file stores secret-equivalent bytes, not a safe public verification key. A same-user worker can inspect local test data unless an actual access boundary prevents it. A signed run is not automatically a sealed evaluation.

Require clear assurance levels: structurally consistent evidence; verified supervisor execution; independently controlled holdout; independently reviewed science. If the Mac cannot enforce a separate trust boundary, explicitly keep the lower assurance. Do not call an ordinary local freeze a sealed holdout. Prefer asymmetric verification with no public secret material. Test secret accessibility and holdout visibility under the documented adversary, and export only verification material that is safe to distribute.

### G05 — Hardware/resource receipt fields are not measured as named (P1)

The gatekeeper currently passes monotonic elapsed wall time as `cpu_time` and literal zero as peak memory. Those are not measured CPU seconds or RSS bytes. Resource limits can be unavailable/swallowed; a `network_disabled` field is not itself an enforced network sandbox. Native descendants need their own resource scope and lifecycle accounting.

Use actual child/process-tree CPU and memory observations with platform units and method, or structured unavailable fields. Record wall time separately. Declare enforcement failures. A rlimit acceptance test needs evidence that the worker was constrained; a network restriction needs an actual access test. No invented memory or energy figure can fill a schema requirement.

### G06 — Language scans and policy consistency do not cover this project (P1)

Some scanning assumes every code path is Python AST input; C++ then produces a syntax error rather than meaningful native provenance analysis. Frozen source hashing can protect header bytes but does not demonstrate that claim-producing C++ paths were executed or inspected. Attack registry counts and pattern matching are not lifecycle coverage. The active constitution permits declared simulation while a subordinate protocol broadly excludes synthetic artifacts from any claim. Epoch/loss requirements describe iterative training and do not map literally to Isolation Forest.

Add language-aware dispatch and executed native-origin joins. Preserve constitution authority: disclosed simulation can support explicitly simulation-scoped claims; undisclosed fallback and test fixtures cannot. Record a domain-appropriate training-sufficiency rationale using tree/subsample budgets and stability instead of fictional ten-epoch losses. Do not weaken genuinely relevant floors. Version and test any clarified domain rule, documenting why it applies and which checks remain procedural.

### G07 — Review and readiness levels overclaim independence (P0/P1)

Certification can promote structural success to READY and review can elevate assurance to INDEPENDENT despite same-model review. Model/session independence, independent statistical recomputation and independent execution are separate properties. Review JSON with the required keys does not establish cold examination of raw evidence.

Keep these properties distinct and derived from verified evidence. Same-model review remains same-model. A complete bundle can be structurally valid while scientific claims remain unready. A null/negative scientific result may be ready if design and evidence are sound; an unsupported positive result is not. Certificate wording must be a faithful bounded record of executed checks and judgments, never a publishing guarantee.

### Required factory integration strategy

Retain the supplied factory as the starting version; do not rewrite its history to imply these gaps were fixed earlier. KLS-02 creates a reviewed, versioned adapter and core integration changes. Existing classification fixtures must retain meaningful behavior. Add adversarial positive/negative full-lifecycle tests around signing, execution, metrics, lineage, assurance and packaging. Update constitution coverage with actual callable checks and explicit procedural boundaries. Update factory version/changelog and hash the policy/runtime into each epoch.

The correction is an extension of the factory's authorized integrity goals, not permission to lower gates. A policy change that actually loosens a mandatory relevant requirement remains a documented decision under the user's/factory's authority. Normal fixes that make enforcement match its existing claims do not require agents to stop for speculative permission.

## 6. Migration completed and what remains deliberately absent

The active C++17 foundation builds through root `CMakeLists.txt` without network downloads. It includes queues, explicit lifecycle, source/map/filter/sink/running aggregate/count windows, retained-event batching, an explicitly configured occupancy controller and validated in-memory Isolation Forest. It omits the old research application, market loader, simulator, model serialization, score-broadcast batching, paper plotting, result processing and self-certification scripts.

Concrete corrections include typed queue allocation and release-mode capacity validation; source EOS and exactly-once pending retries; propagated operator completion; cancellation distinguished from successful drain; exception propagation; final partial-window/batch flushing; constituent IDs/timestamps preserved; explicit feedback direction and finite parameters; actual-psi model normalization; varying-feature selection; unfitted/nonfinite rejection; future-clock rejection; and diagnostic overflow/empty-data handling.

Tests use disclosed generated fixtures. Release correctness checks, ASan/UBSan checks and a ThreadSanitizer fixture run passed on this Mac. Each of 20 public headers compiled independently. Queue tests reconcile 40,000 concurrent fixture values; runtime tests reconcile a finite 15,000-event pipeline and early drain. These counts describe tests, not study observations. Formal memory-model proof, external-platform execution, exhaustive race/scheduler coverage and performance characterization have not been established. A sanitizer pass covers the exercised fixture paths, not every possible interleaving.

The engine is intentionally an auditable foundation. Its count/running aggregates are nonkeyed; count output metadata is not complete lineage; queue close requires producer quiescence; callbacks must return; runtime calls are serialized; the runtime is one-shot; MPMC occupancy includes reservation effects; scheduling is QoS hints; the model has no portable disk format; histogram quantiles are lower bucket estimates and unsuitable as research tails. These limitations are specified in `docs/ENGINE_CONTRACT.md`. KLS-01/KLS-06/KLS-07 turn them into accepted contracts or explicit exclusions.

An engine-free-of-known-fabrication path means no result-producing defaults, hidden fake-data acquisition, expected effects, label access, forced winning verdict or copied measurement. It does not mean an absolute proof of no bugs. Future changes must preserve this boundary and be subjected to targeted counterexamples. A parameter constant such as cache padding, maximum batch size or random seed is allowed if documented/configured and not disguised as an observed outcome.

## 7. Research question, novelty and honest claim boundaries

Before a large implementation campaign, write a prior-art matrix. Adaptive stream batching and dynamic batch/parallelism control exist in earlier work. A low-overhead C++ engine with an EMA knob is not automatically a new scientific contribution. A finance-themed demonstration does not establish novelty or detection validity.

Evaluate three candidate contributions: (A) an experimentally validated controller/operating-region model for bounded microbatching under changing offered load; (B) an integrity-preserving measurement/evidence architecture that exposes coordinated omission and pipeline loss; (C) a careful negative study showing when a simple tuned fixed policy dominates or when feedback fails. Candidate B needs more than applying the supplied factory; demonstrate a new technically meaningful enforcement/property if making it a primary contribution. Candidate C needs a clear mechanism, broad enough contrast and rigorous limits, not merely a controller that was implemented poorly.

The recommended initial question is: **For a fixed semantic pointwise inference workload and fixed offered stream, can a selected adaptive batching policy improve a prespecified tail-latency/throughput tradeoff relative to credible fixed and prior adaptive policies, without losing or changing events?** A valid answer can be no. Separate feasibility from superiority: a policy may preserve semantics but fail a latency SLO; another may succeed only for certain offered rates. Map that operating region rather than averaging away overload.

Require a precise contribution statement before confirmation. Examples of allowed conditional wording: “On the declared M3 machine and these independent replay/trial units, policy A changed offered-to-decision p99 by an estimated paired ratio with the reported interval.” Forbidden wording: “KLStream guarantees real-time anomaly detection,” “zero loss at any rate,” “GPU optimized” when GPU unused, or “improved AUC” when the only intervention is batching an invariant pointwise scorer.

The following candidate claim IDs are placeholders to be concretized from pilot decisions, not promised findings:

| Claim | Estimand / boundary | Minimum evidence | Possible outcome |
|---|---|---|---|
| C-SEM | Per-ID scores/decisions equal the reference within declared arithmetic tolerance for identical features/model | Golden model, complete ID join, batch/order variations | Validated semantics or a failed engine |
| C-TAIL | Paired ratio/difference of trial-level offered-to-decision p99 under fixed workload and comparison family | Native timestamps, independent trial blocks, fixed comparator selection, CI | Better, worse, practically similar, inconclusive |
| C-CAP | Sustainable completion rate under a fixed backlog/latency/resource rule | Offered/admitted/completed IDs, steady-state trajectories, drain, overload policy | A bounded operating region or no feasible setting |
| C-CTRL | Feedback mechanism changes the measured transient response under a declared intervention | Matched policy, closed-loop traces, replication, stability diagnostic | Useful mechanism, no effect, instability |
| C-DET | Performance on a genuinely justified labelled prediction task | Authentic labels, untouched groups, train/val/test isolation, AP/AUROC definitions | Positive, negative, degenerate/unavailable |

C-DET is optional and must be dropped or limited if genuine labels are unavailable. C-SEM is mainly engineering validity; it is not by itself a top-tier novelty claim. C-TAIL and C-CAP cannot inherit significance or thresholds from the old result files.

## 8. Mathematical and queueing contract

For batch size w, a simple service approximation is `S(w)=a+b*w`, with a,b estimated from native measurements at the actual inference configuration. It implies amortized service cost `S(w)/w=a/w+b` and nominal batch-service capacity `mu(w)=w/S(w)`. These are model terms, not fabricated nanosecond observations. If memory/cache/vectorization changes make the model inaccurate, report residuals and use a richer validated model or abandon its analytical claim.

For event i, record intended offered time `o_i`, actual release time `r_i`, admission `a_i`, batch-ready `b_i`, service start `s_i`, inference finish `f_i`, decision publication `d_i`, and optionally durable-write acknowledgement `z_i`. All comparable process times use one monotonic clock. The foundation Event::make
stamps source creation before a possible blocked push; that timestamp is not a
measured successful-admission time. The research harness records distinct fields
rather than retiming an old event and hiding source delay. Definitions include offered-to-decision `d_i-o_i`, source lateness `r_i-o_i`, admission delay `a_i-r_i`, batch wait `b_i-a_i`, service queueing `s_i-b_i`, and completion `d_i-s_i`. If a term cannot be measured, do not fill it from a convenient cost model.

The identity `d_i-o_i=(r_i-o_i)+(a_i-r_i)+(b_i-a_i)+(s_i-b_i)+(d_i-s_i)` must hold up to documented clock/read precision and stage conventions. Durable output latency `z_i-o_i` is a distinct metric; do not include CSV flushing for one baseline and exclude it for another. For a sequential batch, per-point finish may differ from batch finish; fix which convention represents the actual application publication semantics.

At constant arrival rate lambda without other delays, fill waiting for a full batch grows approximately with w/lambda; mean/oldest waiting require their own assumptions. This explains a throughput/formation-delay tension, not an optimality theorem in arbitrary bursty queues. Service capacity above offered rate is necessary for long-run stability in a simplified stationary queue, but finite deadlines, blocking, burst sizes and multistage contention still matter. A growing queue under sustained overload must not be summarized as a healthy low-latency steady state.

Define each queue edge's unit: events, batches, tasks or bytes. A batch queue of C slots can hold up to C*w events; using a larger w increases hidden event backlog if only slot occupancy is reported. Report usable slots, event-equivalent backlog, staged/pending items and allocated bytes. Saturation/backlog conservation includes in-service events and pending outputs. MPMC reserved slots are not the same as published payloads. Control observations must specify approximation error and sample/update cadence.

EMA uses `qbar_t=alpha*q_t+(1-alpha)*qbar_(t-1)` at an explicit update interval. A per-batch alpha changes effective time smoothing when w changes. Prefer time-normalized `alpha(dt)=1-exp(-dt/tau)` when the hypothesis concerns temporal responsiveness, or report the batch-index convention explicitly and test its implications. Deadbands, gain, minimum/maximum and actuation delay are part of the policy. Saturation handling and recovery must be measured. Do not describe an EMA-only heuristic as PID, stability proof or optimal controller.

If batching preserves the feature vector x_i, model M and scorer g, then `score_i=g(M,x_i)` is invariant to grouping under deterministic arithmetic/order-independent evaluation. A change in AUROC/AP in that setting indicates changed IDs/features/model, arithmetic ties, dropped points or a bug, not a semantic batching benefit. A deadline-aware utility can legitimately change while score ranking stays fixed; define it separately, with late and missing points treated according to a frozen rule.

## 9. Data acquisition, labels and provenance

KLS-04 begins from authentic provider bytes. Verify the official current sample structure and terms. The LOBSTER official Data Structure page specifies prices scaled by 10,000 and distinguishes order IDs from sequence position. A public sample download does not automatically license redistribution or establish suitable labels. Preserve URL, retrieval timestamp, HTTP/status/redirect metadata where available, archive and extracted-file hashes, provider documentation version, permitted use and acquisition command. A manual supplied file can be valid if its origin/terms are honestly documented; an absent origin stays unknown.

Separate source kinds in the schema: observational provider data, declared simulation/stress trace, deterministic test fixture, and perturbation overlay. A synthetic stress arrival schedule can be scientifically appropriate for a systems study when declared; its empirical results are real measurements of a system under that schedule. It cannot be passed off as an observed market sequence or evidence of real misconduct. The factory's constitution supports this distinction; its inconsistent subordinate prose must be clarified in KLS-02.

Raw row IDs derive from source fingerprint plus row ordinal, never from mutable feature values or recurring order ID alone. Keep `source_id`, source hash, archive-member name, row ordinal, exchange time, order ID, instrument/day group and origin. Derived rows retain ancestry IDs and transformation hash. Labels have a separate source/definition, availability time, granularity and confidence. A source event type is not automatically a market-anomaly truth label.

A labelled market claim requires a defensible annotation or public benchmark with a documented target, independent adjudication/source where applicable, and no circular label rule equivalent to the score. If truth is a future price movement, define horizon, overlapping-label purging and causal feature cutoff; do not call the target fraud. If truth is an injected perturbation, state the perturbation task and stratify by mechanism/strength rather than claiming real-world anomaly detection.

Never synthesize positives because the factory requires both labels. Use unlabelled replay for C-TAIL/C-CAP and an independently justified labelled cohort for C-DET, or omit C-DET. Evaluate event counts and label availability before planning precision. A small public sample may be sufficient for parser/engineering work but inadequate for broad generalization. Missing authentic data can be a blocker for research scope, not a reason to resume the old fixture fallback.

## 10. Preprocessing, causal state and split construction

Treat preprocessing as a scientific model with testable semantics. Specify price tick/dollar conversion, sizes, event filters, trading halts, empty-level sentinels, timestamp precision, crossed-book handling, duplicate row policy and nonfinite values. Parse decimals without converting exchange seconds through a lossy nanosecond float multiplication. Strictly pair message/order-book row counts; reject mismatch instead of truncating. Keep rejection counts and reasons by source/group/type.

For each feature write equation, unit, raw dependencies and state initialization. Candidate features include spread, depth imbalance, properly defined microprice, causal returns and EW variance/standard deviation. Top-book depth is depth. Trade volume requires a declared execution-event definition. Time-weighted and event-indexed volatility are distinct. Scale/normalization fits only training data. Preserve enough precision to prevent small returns/variances from becoming literal zeros through presentation rounding.

Test causality by mutating every later raw row and checking earlier features remain unchanged. Add finite/empty/sentinel/gap/order fixtures and an independent parser/feature golden reference. Verify raw→feature IDs and ancestry. State warm-up is explicitly excluded or marked. Historical context can legitimately precede a split boundary, but fitting/calibration labels cannot leak. The factory adapter must distinguish causal history ancestors from forbidden label/test-derived fitting dependencies.

Split at meaningful independent groups and time boundaries. Recommended hierarchy is instrument/day or a documented contiguous source block, with chronological train/validation/test and a justified gap/purge for overlapping features/labels. A random row split across overlapping windows is not independent. No globally computed quantile threshold, normalization, anomaly injection selection or fitted feature statistic may see test before freeze.

The test set must be fresh relative to prior tuning. Old exposed source bytes can remain development data; a new split file over already inspected results does not automatically create independence. For a pure systems replay, timing trials on a fixed trace can estimate performance conditional on that trace, but do not multiply the number of independent market days. Record both the conditional timing target and the source-population limit.

## 11. Model contract and training sufficiency

Use Isolation Forest only if it is a reasonable workload/task for the selected study. Document tree count T, requested/effective psi, dimension/schema, seed/RNG, feature selection, split convention, height limit, duplicate handling, c(n) convention and score orientation. Explain why normal-only training was possible: using true normal labels is privileged supervision/cleaning, not ordinary unsupervised access. Compare it only under matching information availability.

For the current exact-harmonic convention, `c(n)=2*H_(n-1)-2*(n-1)/n` for n>1 and c(0)=c(1)=0. A leaf contributes path depth plus c(leaf count), average over trees; anomaly score is `2^(-mean_path/c(psi_eff))`. Two-point and constant-feature examples constrain implementation. Record the reference implementation's approximation where it differs. Do not silently mix normalization conventions in model export/import.

Isolation Forest does not train by gradient epochs. Training sufficiency evidence includes tree/subsample budget curves on train/validation, score/ranking/checkpoint stability under increased budget, runtime/resource observations and a selection rule fixed before test. Do not fabricate epoch losses to satisfy a generic template. If another iterative model is added, use appropriate optimization/convergence diagnostics, validation-only stopping and extended-budget checks.

Anomaly scores are rankings, not calibrated probabilities. AUROC/AP accept rankings; Brier/log-loss require justified probabilities and an independently fitted calibration procedure. Thresholds use validation under a specified utility, false-positive budget or label-free contamination assumption; threshold choice is frozen. A per-window max-score threshold generally depends on w and changes the task. Keep pointwise and window-level detectors separate.

Serialization is new and strictly bounded. Store schema/version, feature hash, effective psi/T, normalized numeric encoding, RNG metadata and complete node validation. No pickle in the native trust path. Check round-trip score agreement, corruption/malformed graphs, endian portability and resource exhaustion. The same model bytes must be used by all batching policies in a paired systems comparison. Model retraining per policy would confound the intervention.

## 12. Native harness, offered load and conservation

Build one execution harness used by all policies. Freeze source code, compilation command/options, dependency state, binary hash and model/data/config hashes. The executable must actually be invoked by the supervisor. Preserve stderr/stdout and every attempt, including failures. Do not call a Python simulator a native benchmark because it emits a field named hardware.

Support finite trace replay and a declared synthetic load generator, each with an independently reconstructible arrival schedule. For replay, decide whether exchange inter-arrival gaps are scaled, compress idle regions or preserve them; publish the transformation and actual release deviations. A tenfold rate means a measured/frozen factor relative to an explicit baseline, not a tenfold occupancy ratio. Reject empty schedules, invalid speeds, timestamp reversal and silent sleep caps.

Distinguish open-loop offered work from a closed-loop blocked producer. Blocking after a full queue delays admission; it must not erase original offered timestamps or drop events from the denominator. If the generator itself cannot release on schedule, record source lateness and failed schedule fidelity. Separate an admissible backpressure experiment from a claim that the original arrival process was sustained. Avoid coordinated omission by retaining scheduled events even while the source is delayed.

For every offered ID assign a terminal outcome: completed decision, explicit policy rejection, intentional semantic filter, cancelled/failed attempt, or unresolved missing/duplicate. At successful finite completion require full reconciliation, no duplicate output, valid ordering semantics and no hidden pending/in-service work. The conservation identity is `offered = completed + intentional exclusions + explicit rejections + unresolved`, with all terms disjoint and reason-coded. A zero drop counter alone proves nothing.

Log every point's needed times/IDs/scores in a lossless format. Batch telemetry records batch ID, members, target/actual size, flush reason, controller observation/update, queue edge and sampled state. Memory/CPU/resource observations name process scope and method. Runtime observers must not race mutable controller internals. Trace overhead must be quantified with a matched configuration; disabling trace only for the proposed policy invalidates fairness. Sampling is allowed only for metrics for which a frozen estimator and uncertainty justify it; conservation requires complete identities.

Use a preallocated/bounded logging strategy or explicitly account for its buffer pressure. Checked file writes and close/flush errors fail evidence acceptance. A performance run that finishes but loses the evidence stream is unavailable, not success. Exact offline quantiles use one declared definition (for example nearest-rank), with event counts and interval conventions; keep diagnostic histograms out of headline measurement.

## 13. Fair baselines, mechanisms and tuning parity

Required simple baselines are per-event W1 with the same code/model/queues/output and fixed windows on a prespecified development grid. Include at least one validation-selected fixed policy and a latency-deadline flush variant if the proposal has a deadline. Do not make W500 the sole comparison while starting adaptive near W10; that can manufacture a trivial formation-delay advantage. The grid spans the relevant validated batch capacity and operating region.

Historical/canonical adaptive policies require a literature-backed specification or faithful reimplementation, not a label in a plot legend. Candidate families include AIMD, a carefully tuned feedback controller, and a published dynamic batching policy whose plant/workload assumptions can be matched. Pick a small credible set rather than a large list of intentionally weak algorithms. Document differences when full system replication is impractical.

An external streaming framework comparison is conditional: it must process the same semantic task, use comparable resources and distinguish framework/adapter overhead. A distributed broker or remote JVM cluster is not automatically a fair competitor to one local native pipeline. Lightweight multicore stream systems may be more relevant. If unavailable, state the external-comparison limitation and restrict the claim to in-framework policy behavior; do not use incomparable plots to assert a universal engine advantage.

Each policy gets comparable validation/tuning opportunity and resource constraints. Record candidate count, time budget, data access, failed settings and selection utility. Equal numeric parameters are not equal tuning opportunity. Freeze tie-breaking and feasibility criteria. Run the selected fixed comparator on test even if a different fixed W later looks better; post-test best fixed may be reported as exploratory oracle only.

Mechanism interventions include feedback enabled versus fixed matched W; smoothing/response timescale; deadband/hysteresis; observation edge; deadline flush; and, if central, scheduling/parallelism. Keep at most five independently meaningful components for a full 2^N factorial where required by the factory. Do not make meaningless invalid variants merely to fill combinations. If components cannot be toggled independently, define a different hypothesis or document a policy-level comparison. Interaction estimates must use actual factorial contrasts and uncertainty, not an all-combinations count.

For shuffled-feedback controls, describe the exact trace permutation, what is held fixed, causal dependency changes and why the intervention answers the question. Open-loop replay of historical observations is not a closed-loop plant test. Include a negative control that should preserve semantics, and challenge the detector with conditions expected to fail to reveal whether the verifier can distinguish outcomes.

## 14. Workloads, stability, sensitivity and OOD

The workload matrix crosses meaningful factors: offered load relative to measured service capacity, burst magnitude/duration, input gap variability, feature/model service variability, queue capacity and active worker count. Reference capacity comes from a separate pilot configuration and is disclosed; do not normalize each policy by its own test throughput if the target is a matched arrival comparison.

Distinguish underload, near-capacity, transient overload and sustained overload. A bounded finite experiment can finish after draining while failing its real-time SLO. Report time-to-drain, peak/event-equivalent backlog, completion fraction and latency over offered points. State stability operationally for the tested horizon; do not infer asymptotic stability from a short trace. A controller that oscillates or stays saturated must be reported without forcing a winner.

Sensitivity follows the factory's ±10/25/50% principle for meaningful continuous settings and feasible discrete neighbors for integers. Never round multiple nominal settings to one and call that coverage. Include alpha/time constant, gain, bands, W bounds, queue capacity and deadline when they are fixed influential choices. Keep parameter definitions and workloads constant. All sweeps produce actual runs with resource/attempt receipts; a diagram of planned settings is not executed sensitivity.

Define rise/recovery time thresholds before runs, including sustained crossing duration and censored cases. Oscillation detection requires a rule based on measured trajectories, detrending/window/duration and a tolerance tied to application relevance. Literal `false` is never a measurement. Do not confuse tenfold burst traffic with depth-feature shocks or forced occupancy.

OOD can mean a new instrument/day, new arrival burst process, service distribution or resource configuration, depending on the claim. Name which dimension is held out and why it tests generalization. One machine limits hardware generalization. A legitimate narrow in-framework result with explicit OOD limitations is preferable to fabricated coverage. If a second platform is unavailable, record that limit and choose a venue/contribution whose claim scope fits it.

## 15. Statistics, uncertainty and decision rules

Define the primary endpoint and family before confirmation. Recommended primary systems endpoint is a paired trial-level offered-to-decision p99 ratio at a specified feasible load/SLO, plus an explicit conservation gate. Secondary endpoints include completion throughput, p50/p95/p99.9 if adequately sampled, source lateness, batch wait, CPU and RSS. Avoid dozens of primary comparisons whose interpretation is selected after seeing the plots.

A timing trial/block is a repeated execution under one frozen schedule and machine condition. Randomize or counterbalance policy order within independent blocks to reduce thermal/background drift. Source day/instrument is a higher hierarchy. Training seeds are conditional model variation and can be nested rather than treated as independent market populations. Events within a run are correlated; millions of events do not create millions of independent algorithm comparison replicates.

For positive tail latencies use a paired log ratio where justified, report exponentiated mean log contrast/geometric ratio with uncertainty and raw-scale summaries. Retain each trial's quantile and counts. For zero/unavailable/censored outcomes choose a predeclared appropriate method rather than adding an arbitrary epsilon. Bootstrap independent trial/source blocks according to the target hierarchy, not individual overlapping events. Keep service/arrival time dependence intact when assessing within-run quantile uncertainty.

Choose tests for their assumptions. Signed-rank assumes the relevant paired-difference symmetry and handles ties/zeros under a declared exact/permutation method. A sign/permutation test may be more defensible for small awkward distributions; randomization tests require an actual design and exchangeability. Report exact method/seed and sufficient statistics. A p value cannot establish a practically important improvement without effect and interval, and a failure to reject cannot prove equivalence.

Holm adjustment or another predeclared familywise/FDR method applies to the actual comparison family. Direction must be retained. Confidence intervals and equivalence/noninferiority margins have a substantive pretest rationale. A small minimum p calculation gives a warning, not a power guarantee: for m comparisons at first Holm threshold alpha/m, the idealized two-sided discrete lower bound `2^(1-n)` must at least permit that threshold. For m=8 and alpha=.05, n=9 permits a sufficiently small tail; it says nothing about the sample size needed for reliable detection at the expected effect/noise.

KLS-09 pilot estimates variability and feasible duration on development data, then chooses a prospective precision/power/stopping rule. An initial engineering pilot of roughly 10–30 timing blocks can estimate noise if resources permit; that number is a starting budget, not a sufficient published sample by fiat. Freeze planned independent units, target interval width or minimum effect/power, maximum budget and handling of infeasible/noisy results. If precision remains inadequate, report inconclusive. Do not stop when p first becomes favorable unless a valid sequential procedure was preregistered.

Detection metrics use AP and AUROC with prevalence, counts and group uncertainty when valid labels exist. Chance is prevalence for AP, not always .05. AUROC without both classes is unavailable. F1/accuracy require validation-selected thresholds. Brier/log-loss require calibrated probabilities. Subgroup and error analyses join actual IDs and source metadata; categories in a dict literal do not demonstrate measured failure counts.

## 16. M3 Air execution and storage budget

The author's stated platform is the primary local development/test machine. Record actual OS build, CPU/model identity, memory, compiler, CMake, Python, architecture, process limits, disk space and scheduling mode from named tools when executing research. Store unavailable observations explicitly. Do not copy “M3/16 GB” into every receipt as measured fact if the executable ran elsewhere. Existing build output identifies AppleClang 21.0.0.21000101 for this migration, not a guaranteed future toolchain.

Use CPU inference initially. The presence of ten GPU cores does not accelerate ordinary C++ trees. A GPU study is optional and would need a real implementation, synchronization, transfer/resource accounting and fair CPU comparison; it is not a free improvement claim. Unified memory is shared with the OS and any GPU workloads. Avoid concurrent research runs and background model workloads while timing unless they are a declared stress factor.

Default builds use `--parallel 2`; correctness tests can run normally, but empirical timing policies run serially. Stream large CSV/telemetry rather than loading all traces/models into Python lists at once. A proposed process-tree RSS target below about 8 GB leaves headroom on the stated 16 GB machine; this is a design budget to measure and revise, not an observed memory result. Chunk features, offline metric calculations and compression with deterministic row/ID order.

Before acquisition estimate and measure storage. Reserve space for raw immutable inputs, processed lineage, every failed attempt, telemetry, bundles and a second verification copy. A starting raw-data budget around 20–40 GB may be practical, but obtain actual free space and provider sizes first. Do not let “512 GB storage” imply that all 512 GB is free. Large legacy self-bundles remain outside active Git. Backups must not recursively include themselves.

Pilot warm-up and steady-state durations rather than asserting a universal 60-second run. Sustained trials might require tens of seconds to minutes depending on rate/thermal effects; justify by observed stationarity and tail sample counts. Separate cold-start/compilation/model load from steady-state endpoints. Record policy order, power source, background activity and observable temperature/frequency if available. Unsupported thermal/energy telemetry is unavailable. Do not estimate joules from CPU utilization or label QoS as exact core pinning.

## 17. Target repository and evidence layout

The existing active `source/include/klstream` foundation is retained. Future source directories should make producing paths obvious rather than mirror every legacy name:

```text
source/include/klstream/       # engine primitives, independent of labels/results
source/apps/replay/            # native finite replay/inference harness, to implement
source/tests/                  # engine/semantic fixtures; never research inputs
source/research/               # acquisition, causal transforms, analysis, rendering
source/requirements.lock      # genuine hashed dependency closure before freeze
factory/engine/                # versioned native runtime/domain enforcement
project/research_plan.json     # valid machine study only after adapter/design
project/methodology.md         # equations, units, target population and procedures
project/claims.json            # ledger, no promised outcomes
project/contracts/KLS-XX/      # specification/report/evidence references
project/pilot/                 # explicitly exploratory summaries and decisions
project/review.json            # actual review mode and raw-evidence objections
project/.factory/              # immutable epochs/attempts, locally managed
data/source_records.csv       # lawful provenance and source identities
data/cohort.csv               # real cohort/split declarations if applicable
docs/audit/                   # historical audit, scope and defect counterexamples
docs/reproduction/            # quickstart, full run, environment and troubleshooting
paper/                        # evidence-derived manuscript only after KLS-12
```

Do not create every empty directory and call the system complete. Final layout can be refined before freeze if the actual executable paths and hashes stay explicit.

Raw/processed data, runtime artifacts, credentials, caches and build outputs are excluded from ordinary Git by default. Some small openly licensed data may be intentionally published after terms review. Factory handoff code must independently enforce the release manifest: `.gitignore` is not an evidence-export policy. Published traces must not contain secrets, restricted data or unreviewed source material. Include public hashes and deterministic reconstruction where source bytes cannot be redistributed.

## 18. Implementation contracts and dependency order

These are implementation-ready contract requirements, not fabricated completion records. The Architect may refine outputs before freeze, preserving scientific intent and this audit. Each report has inputs/hashes, exact commands, outputs/hashes, observed validation, unexecuted checks, resource use and acceptance rationale. No contract fills a planned metric with a plausible number.

### KLS-00 — Preserve and replace legacy repository (migration task)

Preserve public legacy main, latest local rehabilitation and the current tracked changes/author documents before replacing main. Avoid force rewriting history and avoid copying huge self-snapshot blobs. Record exact annotated tags, parent commits, snapshot scope, excluded local caches/bundles, unchanged old working tree and new branch commit. Verify remote refs after push. Preserve engine/factory license scopes. Acceptance is the remote readback plus receipt, not a command merely attempted.

### KLS-01 — Engine semantic/concurrency contract

**Inputs:** migrated headers/tests and F16–F22. **Deliverables:** reviewed API/lifecycle/ownership document; invariants per edge/operator; meaningful correctness and failure tests; sanitizer/compilation results; decisions about supported graph topology, key state, close ownership and progress claims.

Test tiny/full/empty queues, release-mode invalid parameters, source EOS and finish requests, backpressure pending state, duplicate/cancelled IDs, partial batch/window flush, exception paths, shutdown order, mixed workers and natural completion. Challenge MPMC reservations and close after producer quiescence. Add TSan or supported alternative race diagnostics where feasible; disclose unsupported environments rather than claim a pass. A failed callback/run must never be certified as lossless. Keep tests active with NDEBUG. Acceptance requires no known contradicted invariants in supported scope; a limitation can be explicit if the research harness never relies on it.

### KLS-02 — Factory streaming adapter and truthful assurance

**Dependencies:** KLS-01 API, current G01–G07 counterexamples. **Deliverables:** versioned streaming profile/metric schemas, native execution contract, canonical argv, full receipt verification, measured/unavailable resources, language-aware scans, actual acquisition/lineage/metrics dispatch, bounded assurance levels and truthful review/certificate rendering.

Regression fixtures must execute the real lifecycle with valid evidence, then remove signature; alter signed argv/model/input/output/binary; replay nonce; substitute fixture for declared source; delete an offered ID; duplicate completion; reverse/future timestamps; alter output score/metric; supply single-class labels; forge READY or independent review; use an unsupported runtime; and bypass typed validation via legacy command. Every corruption fails the relevant actual release gate. Include one genuine declared-simulation systems case that is correctly scoped and one observational fabrication case that fails. Run existing factory suite plus new tests; report exact counts from execution. No headline benchmark can run as confirmatory before this contract's acceptance.

### KLS-03 — Literature, feasibility and frozen claim specification draft

**Dependencies:** audit; can proceed while KLS-01/02 run. **Deliverables:** primary-source related-work matrix, feasibility memo, selected question, claim/estimand table, scope/novelty decision, candidate venues and explicit what-would-falsify statements.

Read prior dynamic batch/parallelism work and comparable multicore stream runtimes. Distinguish engineering rehabilitation from novelty. State whether a controller model, negative operating-region result or another mechanism can be defended beyond prior work. Narrow or pivot claims before confirmation if no credible novelty remains. Acceptance is an evidence-backed question that the planned experiment can answer, not a sentence asserting top-tier novelty.

### KLS-04 — Authentic acquisition and rights

**Dependencies:** KLS-03 population/data needs. **Deliverables:** acquisition commands with no fallback; byte receipts; source/terms/data cards; immutable raw manifests; scope of lawful use/redistribution; distinct origins for replay/stress/fixtures.

Reproduce downloads or documented manual input, verify hash/archive extraction, fail on missing files, verify official schema and keep provider documentation references. A sample cannot enter observational evidence from a generator. Missing legal/authentic/label information remains a blocking diagnostic for that claim; independent engine work continues. Acceptance includes independently inspected raw files and actual source identity, not just a URL field.

### KLS-05 — Causal parser, features, cohort and splits

**Dependencies:** KLS-04 and claim dictionary. **Deliverables:** strict paired-row parser, feature/units spec, ancestry, rejection diagnostics, group/time split/cohort, independent golden transform and future-mutation tests.

Test prices×10,000, repeating order IDs, decimal times, sentinels/halts, malformed lines, crossed books, missing/nonfinite features, file-length mismatch and warm-up. Verify earlier features unchanged by future edits. Freeze threshold/fit access restrictions. Support unlabelled streaming cohorts without fake labels. Acceptance includes exact raw→processed row joins and split independence rationale at the actual population unit.

### KLS-06 — Model reference, export and selection

**Dependencies:** KLS-05 feature schema; KLS-01 model core. **Deliverables:** golden small trees/scores, trusted reference comparison, portable bounded model format, malformed-input tests, deterministic fitting/seed documentation, train/validation budget curves and selected checkpoint hash.

Compare effective psi, c(n), depth/leaf, variable-feature selection, score orientation and train-sample convention. Treat known approximation differences explicitly. Test binary round trip and corrupted graph/allocation metadata. No unsafe pickle or same-magic incompatible payload. Acceptance requires pointwise reference agreement under a stated convention/tolerance and a real validation-only selection procedure. Test-set performance is not selection evidence.

### KLS-07 — Native measurement and ID-conserving execution harness

**Dependencies:** KLS-01,02,05,06. **Deliverables:** native finite replay and declared stress schedule, actual binary attestation, pointwise/batch telemetry, checked persistence, full terminal-ID accounting, measured clock/resource scope and independent offline quantiles.

Verify source timing with controlled gaps, artificial generator overload, blocked admission, partial tails, deliberate I/O error, cancellation, duplicated IDs and a delayed sink. Require the acceptance verifier to reject each corresponding corruption. Measure tracing overhead with matched paths. Acceptance is the executed native path and reconstructible per-ID observations, not a pretty summary or zero counter.

### KLS-08 — Credible baselines and isolated controllers

**Dependencies:** KLS-03 and KLS-07; implementation can prepare against APIs earlier. **Deliverables:** enumerated policy registry, W1/fixed grid/deadline policies, credible prior adaptive/mechanism controls, common model/output/queues, tuning opportunity ledger and exact controller equations.

Validate feedback sign/edge/units, update cadence, bounds, transient behavior, trace snapshots and dispatch. Test shuffled/random/periodic semantics rather than naming them. Reject invalid batch maxima. Acceptance includes semantic equality, usable-capacity/byte fairness and literature-backed comparator reasons. Every policy shares the same measurement path.

### KLS-09 — Exploratory calibration and prospective precision

**Dependencies:** KLS-07/08, authentic development data. **Deliverables:** clearly labelled pilot attempts, resource/stationarity/overhead diagnostics, model/policy selection, meaningful margins, measurement durations, workload feasibility and prospective sample/stopping plan.

Use development data only. Estimate paired variability and select a trial hierarchy/precision target that the machine budget can support. Document warm-up, thermal/order control, feasible throughput, source lateness and quantile counts. Retain failed settings. If the plan cannot afford meaningful precision, narrow the target or acknowledge inconclusive scope rather than invent independent samples. Acceptance is a reasoned pretest design, not a favorable pilot effect.

### KLS-10 — Confirmatory epoch freeze and controlled execution

**Dependencies:** KLS-02 accepted; KLS-03–09 accepted; fresh holdout availability. **Deliverables:** valid research plan/methodology, acquisition/cohort/model/binary/policy/dependency hashes, prior-exposure statement, fixed comparison family, blocked/randomized schedule, signed attempts and complete raw evidence.

Freeze all decisions, run only allowed commands, keep every failed attempt and log the decision rule for retry. Do not alter frozen source/data/analysis to rescue a result. A discovered engineering defect invalidates affected attempts and requires a new disclosed epoch; it does not disappear after rewriting outputs. Holdout sealing is claimed only under an actual independently controlled boundary. Acceptance is auditable execution under the frozen contract, regardless of result direction.

### KLS-11 — Factorial mechanisms, sensitivity and limits

**Dependencies:** KLS-10 frozen planned experiment matrix or separately frozen exploratory follow-up. **Deliverables:** full meaningful factorial evidence where required, specified sensitivity runs, transient/stability diagnostics, declared OOD/limits and measured subgroup/failure joins.

Distinguish confirmatory secondary analyses from post-hoc exploration. Preserve censored/failed/unstable settings. Give intervals for interactions and feedback-response diagnostics. If sensitivity is flat or the mechanism fails, report it. Acceptance requires raw execution coverage and scientific interpretation consistent with intervention semantics, not every cell being successful.

### KLS-12 — Independent analysis and verdicts

**Dependencies:** complete admissible attempts and frozen analysis. **Deliverables:** separate metric/statistical implementation, paired/hierarchical uncertainty, multiplicity, directional practical-effect decisions, conservation audit, raw-derived tables/figures and claim graph.

Recompute from lossless telemetry/predictions rather than submitted summaries. Mutation-test tied scores, missing IDs, unknown labels, altered times, invalid p/CI/verdict and constant figure paths. Render failed/unavailable/inconclusive cases. Independent code can still share an assumption bug; manually check golden examples and equation semantics. Acceptance does not require positive effects; it requires honest conclusions inside the registered boundary.

### KLS-13 — Cold reproduction and artifact integrity

**Dependencies:** KLS-12 and lawful release manifest. **Deliverables:** clean-checkout build, quick correctness/demo path, complete reproduction path, independent bundle verification, recorded review mode and unresolved external limits.

Use a separate directory/environment and fresh process state; do not rely on ignored local files, prebuilt binaries, implicit package caches or the old folder. Verify no credentials/restricted bytes and no key-secret export. Rebuild/hash binary under stated equivalence rules, reproduce metric checks and representative research results. A different session on the same hardware is useful but not a different physical-platform replication. Acceptance records the actual scope and any remaining incompatibility.

### KLS-14 — Manuscript, licenses and venue artifact

**Dependencies:** KLS-12/13; confirmed contribution/claim scope. **Deliverables:** manuscript with evidence-derived results, real related work, limitations/threats, data/model cards, public artifact package, precise license scopes and reproducibility instructions aligned with current venue policy.

Every quantitative sentence links internally to an immutable accepted result. Clearly distinguish analytical, synthetic-stress and observational findings. Report old evidence rehabilitation as needed and never reintroduce the old fabricated curves. Use real figures/tables, accessible axes/units, uncertainty and all relevant comparison directions. Verify bibliography metadata and cited statement. A short quickstart and longer complete workflow both work; restricted data gets lawful access/reconstruction instructions. Acceptance is reviewer-ready evidence and clear limits, not acceptance by a journal/conference.

### KLS-15 — Final scientific review and submission decision

**Dependencies:** all required claims/contract evidence; no unresolved P0 for the proposed scope. **Deliverables:** actual nine-check factory review, at least three substantive objections/responses, same-model/independence disclosure, bounded certificate, selected venue requirements and final author decision package.

The reviewer examines raw evidence before the narrative. Objections must include provenance/task validity, fairness/novelty and measurement/statistical independence. Resolve each with evidence or narrow the claim; do not merely write a reassuring response. The author decides where/when to submit and handles required external statements. A negative study may pass; an impressive but unsupported study fails. No certificate promises acceptance.

## 19. Dependency graph and practical staging

```text
KLS-00 migration
   ├── KLS-01 engine ── KLS-02 factory integration
   └── KLS-03 literature/question ── KLS-04 acquisition ── KLS-05 causal data
                                      KLS-06 model ← KLS-01 + KLS-05
KLS-07 native harness ← KLS-01 + KLS-02 + KLS-05 + KLS-06
KLS-08 policies ← KLS-03 + KLS-07
KLS-09 pilot/design ← KLS-07 + KLS-08
KLS-10 freeze/run ← KLS-02 + accepted KLS-03..09 + fresh holdout
KLS-11 mechanisms/limits ← frozen matrix
KLS-12 analysis ← accepted evidence
KLS-13 cold reproduction → KLS-14paper/artifact → KLS-15 review/decision
```

The two future sessions are sufficient. Architect can pursue literature, scope, cohort and contract design while Implementor repairs engine/factory enforcement. They should exchange concrete file-based reports rather than rely on shared chat memory. Keep simultaneous source edits disjoint or serialized. Run timing experiments alone. Do not run a vast matrix before the harness conservation tests and factory acceptance tests are trustworthy.

No calendar date is promised. First estimate effort from accepted contracts and actual data availability. “Take extra time” means deeper review and executed validation where it matters, not an inflated number of result files. Stop work on an infeasible claim and document it while advancing the remaining honest system.

## 20. Factory command use and handoff protocol

Presently useful foundation commands are the README CMake/CTest commands and `python3 factory/run_self_tests.py`. The latter tests software, not a scientific study. `docs/audit/probe_legacy.py` requires the legacy folder and is only a preserved audit reproducer; future agents without that folder can review its output/excerpts. It is not a required research data source.

After KLS-02–09, the actual gatekeeper flow remains `freeze .`, `run . EXP_ID` (or all), automatic record, `audit .`, reviewed `certify .`, `handoff .` and receiving `verify-bundle <zip>`, with command syntax verified against the then-current CLI. Use project-root working directory, real plan IDs and immutable attempts. Do not write a command in the plan that is a nonexistent wrapper or different from the supervisor's argv. Typed resolution and audit must share one canonical command representation.

Each contract handoff includes frozen inputs, outputs, exact validation commands/exit codes, evidence hashes and unresolved conditions. Never strip failed attempts from a bundle merely to make it look clean. Release-file manifests need exact admissible paths, private/restricted exclusions and verification material. Receiving agents verify the bundle before relying on it; successful ZIP extraction is not verification.

The current `source/requirements.lock` marks that no research dependency lock exists yet; it is not a final resolved environment. Before research freeze, create genuinely pinned/hashes/platform-aware dependencies and compiler/build records. Installing a large package set is not a substitute for identifying the actual executed closure. Native binary/library hashes and Python runtime/site-package isolation are documented separately.

## 21. Failure taxonomy and honest stopping

**Engineering invalid:** crash, race/inconsistent state, output I/O loss, duplicate/missing unexplained IDs, malformed model, failed completion, invalid timestamp, wrong binary or verifier bypass. These runs cannot support performance superiority even if their printed latency is low.

**Workload infeasible:** source lateness/queue growth/sustained overload exceeds the prespecified admissibility rule. Retain the result as a capacity/failure boundary, not a comparable successful SLO trial. Clearly separate completed-after-drain from on-time processing.

**Scientific unavailable:** authentic input/labels/terms/holdout/independent units are missing. Report what claim cannot be evaluated. Do not generate substitute “real” data, change class definitions or claim the absence of errors proves accuracy.

**Negative/null:** admissible observations show harm, no useful effect or interval spanning the practical threshold. These are valid outcomes. **Inconclusive:** uncertainty/design limits prevent a decision; do not rename this equivalent, stable or supported.

**Scope-limited:** evidence is conditional on one machine, model, source day or stress process. State those dimensions. Future replication can extend them without retroactively claiming broader support.

Stoppage may be required by real data access, mandatory human policy decisions or unsupported infrastructure. Continue independent correction/documentation. The default is not to ask the author to reconfirm already authorized local engineering, preserved history or routine Git migration.

## 22. Submission-readiness acceptance matrix

| Gate | Required evidence | Present migration status |
|---|---|---|
| Authentic data/rights | Provider receipts, inspected bytes, terms, source cards | Not complete; old academic fixture rejected |
| Defined task/novelty | Primary-source matrix, valid target, constrained contribution | Draft direction only |
| Engine semantics | API/invariants, exact-ID/partial-tail/failure checks | Foundation passes; broader KLS-01 remains |
| Factory assurance | Native domain, verified execution/signatures, truthful levels | P0 gaps reproduced; KLS-02 required |
| Causal processing/splits | Strict parser, units, ancestry, fresh group/time test | Not implemented as research pipeline |
| Model validity | Golden reference, portable format, validation-only selection | In-memory normalization corrected; KLS-06 remains |
| Actual measurement | Native offered/admitted/completed traces, resources, quantiles | Harness not implemented |
| Fair comparisons | Tuned fixed and credible adaptive controls, same semantics/budget | Not implemented |
| Experimental design | Prospective independent units/precision/stopping | Not registered |
| Mechanisms/limits | Actual factorial/sensitivity/transient/OOD evidence | Not executed |
| Statistics/verdict | Independent raw recomputation, CI/effect/multiplicity | Legacy results rejected; new analysis absent |
| Reproduction | Clean checkout, lawful data, verified bundle | Engine build works locally; full study absent |
| Manuscript/review | Evidence-linked paper, actual objections, bounded certification | Not complete |

The final author package must show every row's actual state. A single unresolved P0 affecting a claim disqualifies that claim. The project may narrow claims rather than fabricate completeness. Submission-ready means the scientific/evidence/artifact requirements of the selected scope and venue are met; it does not mean the study had a positive outcome.

## 23. Venue strategy and primary sources

Candidate venues depend on the eventual contribution. A multicore systems mechanism may fit a systems or stream/data-processing venue; a database-centric insight needs substantial relevance beyond a toy runtime; a financial prediction study needs authentic task/labels and an appropriate empirical contribution. Do not target a top venue solely because a new folder has a long plan. Verify current policies/deadlines at the actual submission decision; the links below support requirements/prior art as reviewed on the audit date, not a promised future deadline.

1. [LOBSTER Data Structure](https://data.lobsterdata.com/info/DataStructure.php): official message/book schema and price scaling. Use this to resolve units/fields; it does not establish valid anomaly labels.
2. [LOBSTER Data Samples](https://data.lobsterdata.com/info/DataSamples.php): official source/sample information. Inspect actual acquisition and applicable terms separately.
3. [Vyukov bounded MPMC queue](https://www.1024cores.net/home/lock-free-algorithms/queues/bounded-mpmc-queue): original algorithm and its progress-boundary discussion. Do not infer formal lock freedom from atomics alone.
4. [Scikit-learn IsolationForest reference](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.IsolationForest.html): score/decision conventions and fitting parameters. Read source/conventions when comparing exact numerical implementations.
5. [Scikit-learn average precision](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.average_precision_score.html): AP convention distinguishes grouped threshold weighting from interpolated trapezoidal PR area.
6. [SciPy Wilcoxon reference](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.wilcoxon.html): paired signed-rank assumptions, ties/zeros and exact/permutation/asymptotic method constraints.
7. [Adaptive Stream Processing using Dynamic Batch Sizing, Berkeley report, 2014](https://www2.eecs.berkeley.edu/Pubs/TechRpts/2014/EECS-2014-133.html): prior adaptive stream batch sizing. Read the paper and identify differences before asserting novelty.
8. [Adaptive block and batch sizing for batched stream processing system, ICAC 2016](https://research.ibm.com/publications/adaptive-block-and-batch-sizing-for-batched-stream-processing-system): prior joint batching/parallelism work; useful to challenge an EMA-only novelty claim.
9. [StreamBox: Modern Stream Processing on a Multicore Machine](https://research.google/pubs/streambox-modern-stream-processing-on-a-multicore-machine/): relevant multicore stream runtime prior art. Verify final bibliographic metadata against the actual paper.
10. [WindFlow primary institutional record](https://arpi.unipi.it/handle/11568/1101954): another relevant multicore stream design; assess semantic/implementation comparability.
11. [LMStream, arXiv:2111.04289](https://arxiv.org/abs/2111.04289): prior dynamic GPU batching, relevant if expanding beyond the CPU-only scope.
12. [SCQ, arXiv:1908.04511](https://arxiv.org/abs/1908.04511): prior bounded queue progress/scalability work; queue novelty requires more than adopting another known ring.
13. [OSDI 2026 call for artifacts](https://www.usenix.org/conference/osdi26/call-for-artifacts): example artifact expectations, including a short quickstart and fuller reproduction. Check the selected venue's current version later.
14. [OSDI 2026 call for papers](https://www.usenix.org/sites/default/files/osdi26_cfp_120325.pdf): example systems contribution/relevance criteria, not a claim that this project qualifies.
15. [PVLDB 2027 submission guidelines](https://www.vldb.org/2027/submission-guidelines.html): current example database submission policy; reassess fit and exact rules before submitting.

These references are starting points, not a complete literature review. KLS-03 must read primary texts, compare problem/plant/baselines/guarantees, verify authors/years and add directly relevant recent work. Do not cite reported percentages from prior work as expected KLStream outcomes. Any theorem must state assumptions and be proved or appropriately sourced; a controller diagram is not a proof.

## 24. Publication and correction policy

The historical record should remain recoverable and visibly unverified. Annotated tags mean preserved state, not a validated release. New main should plainly explain why earlier results are not relied upon. Do not delete provenance simply because it is embarrassing; do not leave stale paper claims in the active README as if they still describe the system.

When writing a paper, include a complete account of valid methodology and limits. The old implementation's errors are an engineering/audit history, not a shortcut to novel contribution. If previously disseminated numbers/figures must be corrected, the author should prepare an explicit correction notice with affected artifacts and producing-path explanations. Claims of fabrication here concern the observable evidence path; do not speculate about motives.

A negative-result paper needs a real question, valid design, meaningful baselines, precise uncertainty and a clear explanation of the boundary learned. It cannot be made publishable by renaming an inconclusive underpowered experiment negative. The acceptance decision belongs to reviewers and the author; the factory does not replace them.

## 25. Agent anti-fabrication rules that apply to every contract

1. No missing-input fallback may create research observations. Test fixtures are marked at the producer and cannot enter a research release.
2. No hardware/memory/energy/temperature measurement comes from a literal constant or a copied result file. Unavailable means unavailable.
3. No latency metric is derived from a service-cost equation and called observed. Simulated predictions stay model-scoped.
4. No single-class metric is replaced by a reassuring number. No tie-order dependence is accepted.
5. No expected result count, function name, heading or checklist makes evidence scientifically independent.
6. No batch policy may alter feature/model/ID/truth semantics unnoticed. Missing and late points remain in denominators.
7. No favorable unadjusted p or directionless effect is promoted against the registered family/rule.
8. No training epoch, loss trace, convergence curve, baseline, ablation cell, signature or certificate is written without an actual producer and executed evidence.
9. No test-exposed architecture/threshold is treated as freshly independent because a new local freeze exists.
10. No destructive Git rewriting or deletion of failed attempts is needed for this rehabilitation. Preserve and label the record.
11. No same-model review is called independent. No signed execution is called a sealed holdout without an access boundary.
12. No plan-stage target is described as achieved. Every final report includes negative/unavailable/unexecuted states.

## 26. Complete legacy source disposition appendix

The following per-file dispositions are generated from the immutable audit census. “Historical” means excluded from the active producing path, not deleted from preserved refs. No legacy result, raw cohort or model transfers acceptance by being listed. Full non-source categories are recorded in `legacy_inventory.json`; generated/cache items remain inventory-only. Detailed affected paths are cross-referenced above and in the excerpts.

| Legacy source file | Disposition / active relation | Legacy SHA-256 prefix |
|---|---|---|
| `source/apps/adaptive_window/CMakeLists.txt` | Historical app only; new native harness required | `44564ffa4c20ef5e` |
| `source/apps/adaptive_window/harness.cpp` | Historical app only; new native harness required | `5235c7edeb4c42ca` |
| `source/apps/adaptive_window/main.cpp` | Historical app only; new native harness required | `f55ccfece2729fd8` |
| `source/apps/adaptive_window/train_forest.cpp` | Historical app only; new native harness required | `3beb07c4c139d6a1` |
| `source/benchmarks/CMakeLists.txt` | Historical benchmark/verifier; no migrated claim | `7f2426cec0791125` |
| `source/benchmarks/bench_pipeline_throughput.cpp` | Historical benchmark/verifier; no migrated claim | `8691a9662e5b34e5` |
| `source/benchmarks/bench_spsc_queue.cpp` | Historical benchmark/verifier; no migrated claim | `e8b1b503f689d603` |
| `source/benchmarks/bench_ysb.cpp` | Historical benchmark/verifier; no migrated claim | `2213eb3988f728e6` |
| `source/benchmarks/benchmark_model.cpp` | Historical benchmark/verifier; no migrated claim | `69faaf1f34dc2581` |
| `source/benchmarks/benchmark_pipeline_e2e.cpp` | Historical benchmark/verifier; no migrated claim | `0982fd8db8ff9dc2` |
| `source/benchmarks/benchmark_queues.cpp` | Historical benchmark/verifier; no migrated claim | `97d96175612cd81f` |
| `source/benchmarks/capture_hardware_info.py` | Historical benchmark/verifier; no migrated claim | `aa0901520f08ecec` |
| `source/benchmarks/verify_e2e_independent.py` | Historical benchmark/verifier; no migrated claim | `6896e32fd928b2a8` |
| `source/benchmarks/verify_e2e_original.py` | Historical benchmark/verifier; no migrated claim | `efd9768fe94369b9` |
| `source/benchmarks/verify_hardware_independent.py` | Historical benchmark/verifier; no migrated claim | `0614de2c0ac1dce8` |
| `source/benchmarks/verify_hardware_original.py` | Historical benchmark/verifier; no migrated claim | `98be17d6208861e1` |
| `source/examples/.DS_Store` | Historical source; not in active producing path | `049cfd6d4a4c15c2` |
| `source/examples/CMakeLists.txt` | Historical source; not in active producing path | `1b6f8ff42924c30e` |
| `source/examples/basic_pipeline/main.cpp` | Historical source; not in active producing path | `7e1985c9599327b3` |
| `source/examples/yahoo_streaming_benchmark/main.cpp` | Historical source; not in active producing path | `6cdaab8424bb9a6a` |
| `source/experiments/academic_sample_provenance.json` | Quarantined research producer; rebuild through KLS-04–12 | `1af275623075b00c` |
| `source/experiments/analysis/.DS_Store` | Quarantined research producer; rebuild through KLS-04–12 | `d65165279105ca67` |
| `source/experiments/analysis/aggregate_results.py` | Quarantined research producer; rebuild through KLS-04–12 | `e7d3f0d15f0f27fd` |
| `source/experiments/analysis/bench_inference_scaling.py` | Quarantined research producer; rebuild through KLS-04–12 | `9c3637413eea9407` |
| `source/experiments/analysis/calibrate_speed.py` | Quarantined research producer; rebuild through KLS-04–12 | `7af9ae71a587f1b9` |
| `source/experiments/analysis/check_correlation.py` | Quarantined research producer; rebuild through KLS-04–12 | `7e7a4215bfe90a77` |
| `source/experiments/analysis/check_correlation_root.py` | Quarantined research producer; rebuild through KLS-04–12 | `c868823be861bc6b` |
| `source/experiments/analysis/check_correlation_v2.py` | Quarantined research producer; rebuild through KLS-04–12 | `23df11a67aafa4bd` |
| `source/experiments/analysis/compute_metrics.py` | Quarantined research producer; rebuild through KLS-04–12 | `a596a13ca83937af` |
| `source/experiments/analysis/generate_notebook.py` | Quarantined research producer; rebuild through KLS-04–12 | `3f5b01a52ce41c9a` |
| `source/experiments/analysis/plot_experiment4.py` | Quarantined research producer; rebuild through KLS-04–12 | `aef3daf16ff676d4` |
| `source/experiments/analysis/plot_hysteresis.py` | Quarantined research producer; rebuild through KLS-04–12 | `e2ac438a0dda15e0` |
| `source/experiments/analysis/plot_pareto.py` | Quarantined research producer; rebuild through KLS-04–12 | `06ec5f64d9010ac0` |
| `source/experiments/analysis/run_experiment4.py` | Quarantined research producer; rebuild through KLS-04–12 | `9126ac507927c144` |
| `source/experiments/analysis/run_experiment5.py` | Quarantined research producer; rebuild through KLS-04–12 | `c58309ced6370179` |
| `source/experiments/analysis/run_experiments.py` | Quarantined research producer; rebuild through KLS-04–12 | `4f1c74eb87f6715b` |
| `source/experiments/analysis/validate_forest.py` | Quarantined research producer; rebuild through KLS-04–12 | `b08b35dd73af2fa4` |
| `source/experiments/baselines/__init__.py` | Quarantined research producer; rebuild through KLS-04–12 | `d66df996ec7f5e93` |
| `source/experiments/baselines/base_controller.py` | Quarantined research producer; rebuild through KLS-04–12 | `b4381279a8032b50` |
| `source/experiments/baselines/ema_window_controller.py` | Quarantined research producer; rebuild through KLS-04–12 | `14d1be63dc838fcc` |
| `source/experiments/baselines/fixed_window_controller.py` | Quarantined research producer; rebuild through KLS-04–12 | `2c99ecc54da940eb` |
| `source/experiments/baselines/periodic_schedule_controller.py` | Quarantined research producer; rebuild through KLS-04–12 | `ab7d1ddfb28765f3` |
| `source/experiments/baselines/shuffled_occupancy_controller.py` | Quarantined research producer; rebuild through KLS-04–12 | `193a13a354f8da50` |
| `source/experiments/baselines/unadaptive_streaming_controller.py` | Quarantined research producer; rebuild through KLS-04–12 | `fbbcf7f7e42f8bfc` |
| `source/experiments/calibrate_thresholds.py` | Quarantined research producer; rebuild through KLS-04–12 | `7bb8745bfa8c6245` |
| `source/experiments/compile_receipt.py` | Quarantined research producer; rebuild through KLS-04–12 | `646a7a9b389e5cd7` |
| `source/experiments/compute_statistics.py` | Quarantined research producer; rebuild through KLS-04–12 | `a4d8dade967cf17c` |
| `source/experiments/evaluate_falsification.py` | Quarantined research producer; rebuild through KLS-04–12 | `eb5b01577292449a` |
| `source/experiments/metrics/evaluation_metrics.py` | Quarantined research producer; rebuild through KLS-04–12 | `25f4c342146b7d37` |
| `source/experiments/plot_figures.py` | Quarantined research producer; rebuild through KLS-04–12 | `52e901ee278213e1` |
| `source/experiments/preprocessing/create_splits.py` | Quarantined research producer; rebuild through KLS-04–12 | `835a638355039468` |
| `source/experiments/preprocessing/download_sample.py` | Quarantined research producer; rebuild through KLS-04–12 | `1cc37fe8a1e1c656` |
| `source/experiments/preprocessing/preprocess.py` | Quarantined research producer; rebuild through KLS-04–12 | `d625bbb129082669` |
| `source/experiments/preprocessing/preprocess_lobster.py` | Quarantined research producer; rebuild through KLS-04–12 | `b033bc221c966108` |
| `source/experiments/preprocessing/reality_gate.py` | Quarantined research producer; rebuild through KLS-04–12 | `d397bafc35144417` |
| `source/experiments/preprocessing/synthetic_generator.py` | Quarantined research producer; rebuild through KLS-04–12 | `97f3252c55715821` |
| `source/experiments/preprocessing/train_forest_reference.py` | Quarantined research producer; rebuild through KLS-04–12 | `4d938c6841e9dbb7` |
| `source/experiments/preprocessing/validate_forest.py` | Quarantined research producer; rebuild through KLS-04–12 | `8de454783ea74b79` |
| `source/experiments/process_telemetry.py` | Quarantined research producer; rebuild through KLS-04–12 | `261694739a83ed8c` |
| `source/experiments/protocol/anomaly_verification.json` | Quarantined research producer; rebuild through KLS-04–12 | `6cdef8a101c053b5` |
| `source/experiments/protocol/preregistration_digest.json` | Quarantined research producer; rebuild through KLS-04–12 | `83bcac2f64f61d40` |
| `source/experiments/protocol/statistical_methods.py` | Quarantined research producer; rebuild through KLS-04–12 | `e0112679eb483ef2` |
| `source/experiments/protocol/statistical_verification.json` | Quarantined research producer; rebuild through KLS-04–12 | `e8a2387e6121a711` |
| `source/experiments/protocol/verify_anomaly_independent.py` | Quarantined research producer; rebuild through KLS-04–12 | `d6be57842fcbd6ed` |
| `source/experiments/protocol/verify_anomaly_original.py` | Quarantined research producer; rebuild through KLS-04–12 | `869b48a83ece5c5d` |
| `source/experiments/protocol/verify_preregistration_independent.py` | Quarantined research producer; rebuild through KLS-04–12 | `21a6da354ab0a860` |
| `source/experiments/protocol/verify_preregistration_original.py` | Quarantined research producer; rebuild through KLS-04–12 | `1df59074432dc2c7` |
| `source/experiments/protocol/verify_statistics_independent.py` | Quarantined research producer; rebuild through KLS-04–12 | `47ebfa2412700adf` |
| `source/experiments/protocol/verify_statistics_original.py` | Quarantined research producer; rebuild through KLS-04–12 | `5f83e533f6b16f76` |
| `source/experiments/research/.DS_Store` | Quarantined research producer; rebuild through KLS-04–12 | `643cd8ae18c9ea41` |
| `source/experiments/research/CMakeLists.txt` | Quarantined research producer; rebuild through KLS-04–12 | `eb576d3a83c15e19` |
| `source/experiments/research/adaptive_backpressure/CMakeLists.txt` | Quarantined research producer; rebuild through KLS-04–12 | `d8dff005fe1fb999` |
| `source/experiments/research/adaptive_backpressure/main.cpp` | Quarantined research producer; rebuild through KLS-04–12 | `55f275e8da1d7436` |
| `source/experiments/research/adaptive_backpressure/run_experiment.sh` | Quarantined research producer; rebuild through KLS-04–12 | `eccd36e276d41502` |
| `source/experiments/research/core_pinning/CMakeLists.txt` | Quarantined research producer; rebuild through KLS-04–12 | `b9894e558398050a` |
| `source/experiments/research/core_pinning/main.cpp` | Quarantined research producer; rebuild through KLS-04–12 | `c07a0ea1d87124e7` |
| `source/experiments/research/results/bp_adaptive_q1024_high.csv` | Quarantined research producer; rebuild through KLS-04–12 | `c18771a20d92a5d2` |
| `source/experiments/research/results/bp_adaptive_q1024_low.csv` | Quarantined research producer; rebuild through KLS-04–12 | `3f7c03a020c909a6` |
| `source/experiments/research/results/bp_adaptive_q1024_medium.csv` | Quarantined research producer; rebuild through KLS-04–12 | `6f39e798b3ce5683` |
| `source/experiments/research/results/bp_adaptive_q256_high.csv` | Quarantined research producer; rebuild through KLS-04–12 | `8daeefcc94dc62b9` |
| `source/experiments/research/results/bp_adaptive_q256_low.csv` | Quarantined research producer; rebuild through KLS-04–12 | `184afc7dd4bc143e` |
| `source/experiments/research/results/bp_adaptive_q256_medium.csv` | Quarantined research producer; rebuild through KLS-04–12 | `988e963769d53db0` |
| `source/experiments/research/results/bp_adaptive_q4096_high.csv` | Quarantined research producer; rebuild through KLS-04–12 | `036e39e5582c7feb` |
| `source/experiments/research/results/bp_adaptive_q4096_low.csv` | Quarantined research producer; rebuild through KLS-04–12 | `5533c133ea82430d` |
| `source/experiments/research/results/bp_adaptive_q4096_medium.csv` | Quarantined research producer; rebuild through KLS-04–12 | `d880f1fea6cebbf3` |
| `source/experiments/research/results/bp_baseline_q1024_high.csv` | Quarantined research producer; rebuild through KLS-04–12 | `db3aad2f8eb8c070` |
| `source/experiments/research/results/bp_baseline_q1024_low.csv` | Quarantined research producer; rebuild through KLS-04–12 | `17701a597a40968b` |
| `source/experiments/research/results/bp_baseline_q1024_medium.csv` | Quarantined research producer; rebuild through KLS-04–12 | `89d1c558a5f5c926` |
| `source/experiments/research/results/bp_baseline_q256_high.csv` | Quarantined research producer; rebuild through KLS-04–12 | `a0d361adaf33482f` |
| `source/experiments/research/results/bp_baseline_q256_low.csv` | Quarantined research producer; rebuild through KLS-04–12 | `2a2996de79b1a22a` |
| `source/experiments/research/results/bp_baseline_q256_medium.csv` | Quarantined research producer; rebuild through KLS-04–12 | `da7a2153dbec74d3` |
| `source/experiments/research/results/bp_baseline_q4096_high.csv` | Quarantined research producer; rebuild through KLS-04–12 | `7343d58e33824022` |
| `source/experiments/research/results/bp_baseline_q4096_low.csv` | Quarantined research producer; rebuild through KLS-04–12 | `8e948005837c202b` |
| `source/experiments/research/results/bp_baseline_q4096_medium.csv` | Quarantined research producer; rebuild through KLS-04–12 | `ec099811958a8879` |
| `source/experiments/research/results/pipeline_throughput.csv` | Quarantined research producer; rebuild through KLS-04–12 | `b6c1e42e66527d48` |
| `source/experiments/research/results/spsc_queue.csv` | Quarantined research producer; rebuild through KLS-04–12 | `2f17d9b3f3d98678` |
| `source/experiments/research/results/ysb.csv` | Quarantined research producer; rebuild through KLS-04–12 | `748422f4f5d3911f` |
| `source/experiments/research_framing_verification.json` | Quarantined research producer; rebuild through KLS-04–12 | `e70012463818328f` |
| `source/experiments/run_full_matrix.py` | Quarantined research producer; rebuild through KLS-04–12 | `e964d5a1ef7716f7` |
| `source/experiments/run_sensitivity.py` | Quarantined research producer; rebuild through KLS-04–12 | `8758f790d46ea015` |
| `source/experiments/runners/experiment_runner.py` | Quarantined research producer; rebuild through KLS-04–12 | `cae2580121eebf9a` |
| `source/experiments/train_models.py` | Quarantined research producer; rebuild through KLS-04–12 | `f3d346dda062744b` |
| `source/experiments/verify_calibration_independent.py` | Quarantined research producer; rebuild through KLS-04–12 | `36a54ab3bdb3bf7c` |
| `source/experiments/verify_calibration_original.py` | Quarantined research producer; rebuild through KLS-04–12 | `241fd1cec5d8ed66` |
| `source/experiments/verify_falsification_independent.py` | Quarantined research producer; rebuild through KLS-04–12 | `7bd798fae66165d9` |
| `source/experiments/verify_falsification_original.py` | Quarantined research producer; rebuild through KLS-04–12 | `2b8990e85c2a0da5` |
| `source/experiments/verify_framing_independent.py` | Quarantined research producer; rebuild through KLS-04–12 | `fe285821b7213401` |
| `source/experiments/verify_framing_original.py` | Quarantined research producer; rebuild through KLS-04–12 | `f643d1307a6d95fc` |
| `source/experiments/verify_matrix_independent.py` | Quarantined research producer; rebuild through KLS-04–12 | `508b4127332f184e` |
| `source/experiments/verify_matrix_original.py` | Quarantined research producer; rebuild through KLS-04–12 | `9cae81b3ed2bc15f` |
| `source/experiments/verify_receipt_independent.py` | Quarantined research producer; rebuild through KLS-04–12 | `8e62099cf515e164` |
| `source/experiments/verify_receipt_original.py` | Quarantined research producer; rebuild through KLS-04–12 | `0598961bce65b55e` |
| `source/experiments/verify_sensitivity_independent.py` | Quarantined research producer; rebuild through KLS-04–12 | `2cc7103d6ac5bf7a` |
| `source/experiments/verify_sensitivity_original.py` | Quarantined research producer; rebuild through KLS-04–12 | `84c43e7a2e3676ac` |
| `source/experiments/verify_statistics_independent.py` | Quarantined research producer; rebuild through KLS-04–12 | `128c1cef765c93e8` |
| `source/experiments/verify_statistics_original.py` | Quarantined research producer; rebuild through KLS-04–12 | `874fcc0423072df8` |
| `source/include/klstream/core/backpressure.hpp` | Modified/reviewed foundation; see engine contract | `dd454e003b8b7f6d` |
| `source/include/klstream/core/config.hpp` | Modified/reviewed foundation; see engine contract | `5939ebaecc2b0bc7` |
| `source/include/klstream/core/event.hpp` | Modified/reviewed foundation; see engine contract | `e1d0579755e51ed7` |
| `source/include/klstream/core/metrics.hpp` | Reimplemented foundation; old behavior not accepted | `1a883f725a2cb6af` |
| `source/include/klstream/core/mpmc_queue.hpp` | Modified/reviewed foundation; see engine contract | `d7c861e26bf0e030` |
| `source/include/klstream/core/operator.hpp` | Modified/reviewed foundation; see engine contract | `97f9de7430d1e98c` |
| `source/include/klstream/core/pinning.hpp` | Modified/reviewed foundation; see engine contract | `18665418d246a2da` |
| `source/include/klstream/core/runtime.hpp` | Reimplemented foundation; old behavior not accepted | `3fb7f90eac4e5b44` |
| `source/include/klstream/core/spsc_queue.hpp` | Modified/reviewed foundation; see engine contract | `181c43cdff279370` |
| `source/include/klstream/core/version.hpp` | Historical source; not in active producing path | `70b0d9592518217e` |
| `source/include/klstream/core/worker.hpp` | Reimplemented foundation; old behavior not accepted | `291d367ba2632e21` |
| `source/include/klstream/klstream.hpp` | Modified/reviewed foundation; see engine contract | `64c3bc9e58049e6d` |
| `source/include/klstream/model/isolation_forest.hpp` | Reimplemented foundation; old behavior not accepted | `a5ca6e8afd9ffd1e` |
| `source/include/klstream/operators/aggregate.hpp` | Modified/reviewed foundation; see engine contract | `ec4056cfb913ae51` |
| `source/include/klstream/operators/filter.hpp` | Modified/reviewed foundation; see engine contract | `41ac6fe15b3bdca2` |
| `source/include/klstream/operators/map.hpp` | Modified/reviewed foundation; see engine contract | `fd7582f051d8c049` |
| `source/include/klstream/operators/sink.hpp` | Modified/reviewed foundation; see engine contract | `2aaa96cbd22c5ee4` |
| `source/include/klstream/operators/source.hpp` | Reimplemented foundation; old behavior not accepted | `b3f3748b20ace443` |
| `source/include/klstream/operators/window.hpp` | Reimplemented foundation; old behavior not accepted | `9e1e4cfa3ff197f5` |
| `source/include/klstream/window/adaptive_window_op.hpp` | Removed legacy batching/detector; retained-event batching replaces it | `035e18b5b16de650` |
| `source/include/klstream/window/data_driven_window_op.hpp` | Removed legacy batching/detector; retained-event batching replaces it | `b6e553edd9a8001a` |
| `source/include/klstream/window/financial_tick_source.hpp` | Removed legacy batching/detector; retained-event batching replaces it | `72dbf6973af95025` |
| `source/include/klstream/window/inference_op.hpp` | Removed legacy batching/detector; retained-event batching replaces it | `2bdd0ce2f4573062` |
| `source/include/klstream/window/result_sink.hpp` | Removed legacy batching/detector; retained-event batching replaces it | `11f13069a5afbe72` |
| `source/include/klstream/window/types.hpp` | Removed legacy batching/detector; retained-event batching replaces it | `f2ab103262020a07` |
| `source/tests/CMakeLists.txt` | Historical tests; new fixture suite replaces acceptance | `3fc84d7677716823` |
| `source/tests/consumer/CMakeLists.txt` | Historical tests; new fixture suite replaces acceptance | `119ae1fa38396d9e` |
| `source/tests/consumer/main.cpp` | Historical tests; new fixture suite replaces acceptance | `d435aee35d35e9c6` |
| `source/tests/test_backpressure.cpp` | Historical tests; new fixture suite replaces acceptance | `51e2101b033b2875` |
| `source/tests/test_mpmc_queue.cpp` | Historical tests; new fixture suite replaces acceptance | `56d20d55bd98a12a` |
| `source/tests/test_operators.cpp` | Historical tests; new fixture suite replaces acceptance | `ec7f9c70724c17d7` |
| `source/tests/test_pipeline_integration.cpp` | Historical tests; new fixture suite replaces acceptance | `5e9744a32031ef6f` |
| `source/tests/test_spsc_queue.cpp` | Historical tests; new fixture suite replaces acceptance | `83873a6e29906159` |
| `source/tests/unit/test_adaptive_controller.cpp` | Historical tests; new fixture suite replaces acceptance | `b0ae7e6b78f654c2` |
| `source/tests/unit/test_anomaly_separability.py` | Historical tests; new fixture suite replaces acceptance | `8143883f5c142822` |
| `source/tests/unit/test_baselines.py` | Historical tests; new fixture suite replaces acceptance | `2cf6ba697834bc7a` |
| `source/tests/unit/test_data_leakage.py` | Historical tests; new fixture suite replaces acceptance | `e0c306fee163805b` |
| `source/tests/unit/test_evaluation_metrics.py` | Historical tests; new fixture suite replaces acceptance | `563a08b491122b08` |
| `source/tests/unit/test_experiment_runner.py` | Historical tests; new fixture suite replaces acceptance | `0d094e4996e73f51` |
| `source/tests/unit/test_header_compilation.cpp` | Historical tests; new fixture suite replaces acceptance | `80580dc2a68c0c7d` |
| `source/tests/unit/test_isolation_forest_math.cpp` | Historical tests; new fixture suite replaces acceptance | `224539fdb7051041` |
| `source/tests/unit/test_metrics_accuracy.cpp` | Historical tests; new fixture suite replaces acceptance | `d065ff09d482a997` |
| `source/tests/unit/test_model_serialization.cpp` | Historical tests; new fixture suite replaces acceptance | `1f25303646a965cd` |
| `source/tests/unit/test_preprocessing_schema.py` | Historical tests; new fixture suite replaces acceptance | `14f4ff0bde1436f6` |
| `source/tests/unit/test_reality_gate.py` | Historical tests; new fixture suite replaces acceptance | `198f226dfea9e703` |
| `source/tests/unit/test_runtime_lifecycle.cpp` | Historical tests; new fixture suite replaces acceptance | `dbb190e93faba3b2` |
| `source/tests/unit/test_statistical_methods.py` | Historical tests; new fixture suite replaces acceptance | `881979c3c78e1cfd` |

## 27. Preservation references and audit completion

The migration began on 2026-09-30 and its final handoff was completed on
2026-10-01 in Asia/Kathmandu. Legacy tag dates identify the preservation operation;
they are not dates of scientific validation. `docs/audit/git_migration.json` records
the exact refs and remote readback. The new main replaces the old active tree by a
normal descendant commit, retaining recoverable history. The old local folder and
its working index are preserved.

The legacy public state is `legacy-public-2026-09-30`; later local HEAD is
`legacy-local-2026-09-30`; the additional working snapshot is
`legacy-snapshot-2026-09-30`. It includes all 62 tracked dirty files, six author
guides and 228 authored ignored project/factory files. Caches, build outputs,
recursive self-snapshot bundles and the giant ignored archive remain local.
No preserved tag is presented as valid publication evidence. Check the migration
receipt for the final push/readback state rather than treating this paragraph as
proof of network success.

The standalone `docs/audit/probe_factory_signature.py` reproduces the critical
factory gap using only this new folder. Run it with a temporary output path and
`PYTHONDONTWRITEBYTECODE=1`; its data/key are temporary disclosed fixtures. Once
KLS-02 is corrected, that fixture should fail unsigned acceptance or report rejected
evidence, and the implementation report must preserve the old counterexample.

The next work is KLS-01/KLS-02 plus KLS-03, not another legacy result matrix.
No new experimental claim was generated to make this migration appear successful.

## 28. Proposed streaming adapter interface: concrete design input for KLS-02/KLS-07

This section specifies an interface to implement. It is not an accepted factory
schema today and is not an executable research plan. Do not insert it into the
current parser and then suppress UNSUPPORTED_PROFILE. The Architect/Implementor
must integrate and mutation-test the actual domain first.

**Proposed profile identifier:** `streaming_systems_v1`. **Proposed domain module:**
`factory/engine/domains/streaming_systems.py`, with an independently maintained
research analysis module under `source/research/analysis/`. Both use the same
published metric definitions, but must not simply call each other's headline
implementation. Golden examples and independently traced equations prevent two
copies of the same error from being called independent.

### Source/cohort schema

Keep source-level records separate from event rows. Required source fields are
`source_id`, byte fingerprint, provider/origin, acquisition receipt path/hash,
terms reference, raw schema/version, instrument/day or stress-process group,
usable row/time extent and origin enum. Event cohort fields include `sample_id`,
`source_id`, immutable raw row ordinal, group, split, raw exchange time where
available, feature-schema hash and feature ancestry. Label/task fields are nullable
and have a separate annotation source/hash/availability time when present.

An unlabelled streaming cohort is accepted only for systems metrics. A labelled
sub-study requires both its task schema and the existing classification checks.
Do not require every temporal split to be artificially balanced, nor invent class
members. Scope the relevant support floors to the actual claim and retain a
reason-coded unavailable classification result where appropriate.

### Attempt, schedule and model binding

Each attempt binds project/epoch/experiment/policy/source/model/feature/build
identities, independent trial block, model seed versus schedule seed, frozen
parameters, worker/queue configuration, expected offered IDs/schedule hash,
resolved argv/runtime, real supervisor nonce/signature, actual exit status and
terminal lifecycle reason. A schedule is immutable before dispatch and can be
reconstructed independently from its source plus declared timing transformation.
Changing source pacing changes the observed release/admission times, not the
original offered schedule. All configured bounds and units are in the receipt.

Do not repeat large hashes in every hot-path record if that distorts the workload.
A compact record may reference run metadata by immutable ID. Its lossless export
joins that metadata after the measured phase; the signed output manifest covers
both raw records and the deterministic conversion. Hashes do not establish the
provider's truth, so the source review remains a separate acceptance property.

### Pointwise terminal-observation schema

Required identity fields are attempt ID, sample ID/raw ordinal, source ID, group,
policy ID, batch ID if batched, output ordinal and terminal outcome/reason.
Required timing fields, when that stage occurred, are offered, actual release,
successful admission, batch-ready, service-start, inference-finish and publication
in explicitly named monotonic nanoseconds. A durable-write field is separate.
Missing stages are **null with a reason**, not zero. Score/decision/reference-model
identity are present for inference outputs; a systems-only payload has its own
semantic checksum or expected value. An optional label is joined from the frozen
cohort after execution, never fed to the policy.

Validate clock-domain identity, stage order, signed/nonnegative interval arithmetic,
finite scores, raw identity membership, duplicates and total terminal accounting.
If batching publishes all results only at batch finish, record that real convention
for every member rather than fabricating an individual finish. A rejected/cancelled
point has no completed latency unless completion actually occurred. Completion-only
latency distributions require a simultaneous offered-denominator/terminal report
so selective dropping cannot improve the headline unnoticed.

### Batch/controller observations

Record batch ID and member range/list mapping, target/actual size, first admission,
readiness time, flush reason (size/deadline/EOS), queued/start/finish times, queue
edge, observed usable slots/events/bytes, approximate occupancy, observation time,
EMA/time constant, proposed and clamped action, and policy update sequence.
A slot range cannot stand in for a membership list if reordering/filtering occurred.
Controller diagnostics are synchronized snapshots. Deadline is a readiness/flush
request; output blocking/scheduler delay can violate an application deadline and
must remain measured. A deadline parameter is not a hard timing guarantee.

### Resource observation schema

Every observation states tool, unit, process/process-tree scope, wall interval,
platform conversion and availability. Separate wall seconds, CPU seconds, peak
RSS bytes, allocated engine buffers and system memory pressure. macOS/Linux RSS
unit conventions are tested before conversion. CPU percentage has a declared core
normalization. Temperature/frequency/energy are absent/unavailable if unsupported;
no device-spec literal substitutes for a sample. The supervisor signs actual
measurement availability along with any enforcement failures.

### Independent metric return type and decision function

Return a structured object with metric ID/version, status, value when valid, unit,
numerator/denominator, source-observation hash, filters, quantile convention and
unavailable/failure reason. Never encode infinity/NaN into strict JSON without an
explicit state. Overflow of a diagnostic histogram cannot become a finite p99;
research raw integer observations avoid that clipping entirely.

For nearest-rank p99 of n valid integer durations, rank is `ceil(.99*n)` (one-based)
and the selected sorted value is at rank minus one. Freeze a numerically reliable
rational/integer implementation, not a row-order-dependent approximation. Validate
n>0 and distinguish uncertainty of that conditional sample quantile from the
uncertainty of the between-policy trial contrast. Throughput has a declared time
interval and terminal denominator. Backlog and drop metrics reconcile IDs, not
only counters. Recovery/oscillation include censoring/unavailable state.

The verdict consumes registered claim rules plus these accepted metrics and the
independent contrast analysis. It has distinct states for supported, contradicted,
practically equivalent only under an actual equivalence design, inconclusive,
unavailable and invalid evidence. A sign-flipped contrast, changed Holm family,
removed terminal event or forged signature must change acceptance/verdict as
specified. Paper rendering cannot override this state with a literal success.

### Integration acceptance, not schema theater

A positive end-to-end fixture must build/invoke a real tiny native program,
produce a known finite offered schedule and terminal trace, record authentic
supervisor execution, recompute its metrics, survive bundle verification and
receive only the assurance it actually earned. Its generated source events are
visibly fixtures, so it cannot be a scientific release. A declared-simulation
research fixture can exercise scope rules without becoming observational data.

Then execute the corruption matrix in KLS-02 against the real lifecycle. The
certification gate must actually reject each mutation rather than an isolated
helper returning a diagnostic that `certify` ignores. Verify positive evidence
is not rejected for lawful causal history or a legitimately unlabelled stream.
Document false-positive boundaries and procedural source-authenticity checks.
This is the point at which a machine plan becomes compatible with KLStream's
research domain; a renamed JSON field or another certificate template is not.
