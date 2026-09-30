# KLStream Rehabilitation Plan

**Project:** KLStream / `brolq`  
**Factory baseline:** Software Factory v2.2.0  
**Plan date:** 2026-08-26  
**Plan status:** Proposed rehabilitation and publication-readiness roadmap  
**Primary rule:** Preserve the existing project as evidence. Do not rewrite it as though the pre-Factory work never happened.

---

## 1. Executive determination

KLStream should be rehabilitated, not restarted.

The repository already contains a meaningful C++17 streaming runtime, lock-free queues, operators, benchmarks, an adaptive-window research application, preprocessing and analysis code, experimental outputs, and a manuscript. That is valuable work. The correct use of Software Factory v2.2.0 is to make the existing codebase the input to a controlled recovery: preserve its history and unfinished work, establish a truthful baseline, organize it into a factory-compatible shape, repair engineering defects, rebuild the scientific evidence chain, and release only what survives deterministic and adversarial verification.

The project is not currently publication-ready. That conclusion is not based on polish or style. It follows from several stop-condition-level findings in the present tree:

1. The manuscript describes the evaluation data as LOBSTER AAPL observations with synthetic anomalies, but the current `data/replay/replay_AAPL_20120621.csv` has the schema and initial values produced by `preprocessing/synthetic_generator.py`, while no acquisition or provenance manifest exists. The synthetic generator and the real-data preprocessor both target the same filename. Until provenance proves otherwise, the file must be treated as synthetic. Existing LOBSTER-based claims and all downstream results are therefore quarantined, not accepted as publication evidence.
2. `scripts/reproduce_all.sh` accepts any existing replay file solely because the filename exists. It does not distinguish real-derived, synthetic, stale, or corrupted data. This is precisely the silent-substitution failure that the Factory's C54, D-019 through D-023, acquisition audit, and Reality Gate are designed to prevent.
3. A clean current build succeeds, but `ctest --test-dir build` reports `No tests were found`. The 21 existing GoogleTests pass only when CTest is run from `build/tests`. `scripts/dev.sh test` uses the root invocation, so the normal advertised test command can report success without executing a test.
4. The current experiment and metric pipeline does not support several manuscript descriptions. It stores one maximum score per window, then expands a positive window across all of its ticks; it cannot implement the paper's description of PA%K as checking how many individual tick scores cross the threshold. It selects the 95th-percentile threshold from the same run it evaluates. It trains and evaluates from one underlying replay series, and the 30 runs repeat that same series rather than providing 30 independent data units.
5. A 10-second result file contains sequence numbers near 2.9 million while the ground-truth file has 100,000 rows. The source loops the replay repeatedly, while analysis masks are sized to one copy. Only predictions falling in the first 100,000 sequence positions affect the tick masks, even though thresholds and latency summaries use much more output. This must be redesigned before the current statistical results are trusted.
6. The paper's latency explanation contradicts the code. `FinancialTickSource` creates `Event` timestamps from `steady_clock`; the original CSV timestamp is not propagated into `Event`. `InferenceOp` reuses the last event's pipeline-entry timestamp for a window. For an earlier flagged point this understates, rather than overstates, the flagged point's end-to-end latency. Dividing the result by the replay speed factor would not turn it into real-market latency.
7. The current `occupancy_at_decision` output field is always written as zero, despite comments saying adaptive wiring fills it. The `is_burst_period` column is parsed but not used to implement the documented burst override. Claims derived from those signals need new, direct evidence.
8. The paper states one default controller configuration while `adaptive_window/main.cpp` and existing result summaries use another. It also uses words such as “guarantee,” “bounds,” “causal,” and “first” more strongly than the current evidence permits. An observed P95 of 19 ms alongside a recorded maximum of 141 ms is not a strict latency guarantee.
9. The public runtime and build surface contain substantial rehabilitation work: stale uncompiled `src/core/*.cpp` files reference removed architecture, advertised CMake options do not exist, Docker and developer scripts name nonexistent binaries, install/export rules are absent, the README names removed headers, the claimed MIT license file is missing, and version data is duplicated manually.
10. Several high-risk correctness areas lack semantic or adversarial coverage: C++17 object lifetime in raw queue storage, full-queue MPMC occupancy, invalid-capacity behavior in release builds, repeated shutdown, queue draining and event loss, cumulative versus interval metrics, rate-limiter recovery, adaptive-controller parameter validation, model serialization validation, exact per-point latency, data/model leakage, and statistical test semantics.

These findings do not mean the project has failed. They determine the order of rehabilitation. Phase 1 must make the repository and evidence truthful before later phases optimize, rerun, or publish anything.

---

## 2. Completion definition

The rehabilitation is complete only when all three deliverables are simultaneously ready:

### 2.1 Software deliverable

- A clean, documented C++17 KLStream library and adaptive-window application build from a fresh clone using the documented commands.
- The supported compiler and platform matrix passes in CI.
- Unit, semantic, integration, concurrency, sanitizer, packaging, and install-consumer tests all run from one top-level test command.
- Public headers compile independently and do not depend on accidental transitive includes.
- Runtime lifecycle, queue contracts, backpressure, metrics, event-loss behavior, and shutdown semantics are explicitly specified and verified.
- CMake install/export, examples, benchmarks, Docker, scripts, and README agree on target names and options.
- License, contribution, security, citation, versioning, and changelog artifacts exist and are internally consistent.

### 2.2 Scientific deliverable

- Every data artifact has an identity, kind (`real-derived`, `synthetic`, or `fixture`), checksum, provenance chain, transformation manifest, license/release status, and immutable run association.
- No synthetic artifact can occupy the path or identity of real-derived data.
- The Reality Gate passes before training or full evaluation.
- Training, validation, calibration, and test units are separated without leakage.
- The window mechanism's actual semantics are stated correctly. If window size only changes batching and decision aggregation for a pointwise Isolation Forest, the project is reframed accordingly; if a context-dependent detection claim is retained, the model must genuinely use window context and be tested as such.
- At least the venue-required operational, statistical, and learned baselines are competently implemented and fairly tuned.
- Thresholds, controller parameters, hypotheses, primary outcomes, effect-size targets, and falsification rules are declared before the final test run.
- Metric implementations have independent known-answer tests. The unit of analysis matches the statistical test, and multiple comparisons, effect sizes, confidence intervals, ties, and seed/data variance are handled explicitly.
- Every comparative or causal claim maps to raw evidence, an immutable result artifact, an independent recomputation, and an appropriate Factory Scientific Claim Tier.

### 2.3 Publication and release deliverable

- The manuscript is rewritten from certified evidence rather than repaired around legacy numbers.
- Every title adjective and abstract claim maps to a named validating test.
- Every citation, DOI, venue fact, data statement, number, table, and figure is traceable and checked.
- A reviewer can reproduce the claimed results from a clean environment using documented inputs and commands, subject to clearly stated licensed-data steps.
- Generated data and large raw outputs live outside Git; small manifests, schemas, configurations, checksums, and release summaries remain tracked.
- `release-check` passes, all contracts are complete, `release-certify` produces `project/RELEASE_CERTIFICATION.md`, and the certificate's proof boundaries are stated accurately.
- A tagged source release, reproducibility bundle, manuscript/supplement bundle, and archived evidence package use the same version and checksums.

Passing only the software checklist is not publication readiness. Passing only the manuscript checklist is not software readiness. The Factory's C51 principle applies: scientific validity precedes engineering completion for a research release.

---

## 3. Audit basis and current-state record

This plan is grounded in direct inspection of both repositories, not only their READMEs.

### 3.1 Software Factory v2.2.0 material reviewed

- `factory.md`
- `bootstrap.sh`
- `factory/bootstrap_manifest.yaml`
- `factory/constitution.md`
- `factory/factory_spec.md`
- `factory/architect_spec.md`
- `factory/implementor_spec.md`
- `factory/gatekeeper_spec.md`
- `factory/gatekeeper.py`
- `factory/dynamic_rules.md`
- `factory/domain_checklists.md`
- `factory/venue_requirements_TEMPLATE.md`
- `factory/key_facts_TEMPLATE.md`
- v2.2.0 changelog and Gatekeeper test inventory

The Factory is a two-role system: Architect and Implementor, with the Human holding approval and a deterministic Gatekeeper enforcing only what it can actually check. The Factory itself explicitly discloses that Allowed File Validation, Reality Gate, and Methodology Adversarial Review are not fully automated. The rehabilitation plan therefore includes manual raw-diff review, manual Reality Gate production, and an adversarial methodology pass rather than assuming Gatekeeper provides protections it does not implement.

### 3.2 KLStream material reviewed

- Git history, status, tracked/ignored state, and repository size
- Root build, Docker, Compose, formatting, linting, editor, and developer-script configuration
- All public core, operator, adaptive-window, and Isolation Forest headers
- Stale `src/core` implementation files
- Examples, unit/integration tests, benchmarks, runtime research experiments, and their saved outputs
- Preprocessing, model-training, validation, experiment-running, metric, aggregation, correlation, and plotting scripts
- Current replay/model/results artifacts and representative raw output files
- README, legacy implementation/research guides, generated description, study guide, report, manuscript, result summary, and reproduction script
- Normal build and CTest behavior

### 3.3 Baseline observations to preserve in the first Factory report

| Area | Observed state on 2026-08-26 | Consequence |
|---|---|---|
| Git | `main` at `bc095f0`, tracking `origin/main`; no tags | Create a preservation tag/branch before migration; never rewrite canonical history by default. |
| Worktree | 9 modified tracked files, 1 deleted notebook, 5 untracked work files before this plan | Existing changes belong to the project and must be dispositioned, not discarded. |
| Tracked tree | 104 tracked files | Small enough for file-by-file classification rather than broad deletion. |
| Generated tree | About 2,878 non-Git files; 490 files under `results/raw`; about 2,207 files under build directories | Inventory and checksum before archival; do not commit or casually delete. |
| Disk usage | `results/` about 2.5 GB; `data/` about 22 MB; build trees about 45 MB total | Results require external artifact storage and manifests; Git should contain only selected summaries/fixtures. |
| Build | Current Release build completes on AppleClang 21 | Useful baseline, not proof of correctness or portability. |
| Tests | Root CTest finds 0 tests; `build/tests` runs 21/21 passing | Repair test discovery immediately; record the misleading front door as a regression test. |
| Sanitizers | `build_asan` and `build_tsan` are incomplete and contain no runnable test tree | Sanitizer claims are currently unverified. |
| Python environment | No project dependency manifest or lock; behavior can vary with optional `prts` availability | Pin environment and remove semantic fallbacks that silently change metrics. |
| Data identity | No `data_manifest.json`, `acquisition_provenance.json`, input checksums, or license record | Current data cannot support real-observation claims. |
| Result identity | Outputs overwrite stable filenames and do not carry code/data/config/environment hashes | Existing result lineage is incomplete. |
| Packaging | `cmake/klstream-config.cmake.in` exists but no install/export rules consume it | Packaging is unfinished. |
| Release metadata | README claims MIT but no `LICENSE`; no `CITATION.cff`, `CONTRIBUTING.md`, `SECURITY.md`, or project changelog | Public release is incomplete and legally ambiguous. |

### 3.4 Current claims that must be suspended pending re-verification

The following are hypotheses or legacy observations, not approved release claims:

- “The evaluation uses LOBSTER AAPL data.”
- “KLStream processes 100% of incoming tuples.”
- “The adaptive controller strictly bounds or guarantees tail latency.”
- “P95 is 19.0 ms under a reproducible, externally valid workload.”
- “The controller's causal mechanism is empirically validated.”
- “Larger windows improve Isolation Forest accuracy through additional context.”
- “PA%20 is implemented as described in the manuscript.”
- “Thirty runs provide 30 independent statistical samples.”
- “The paired Wilcoxon p-value is below `10^-9` under an appropriate exact/tie-aware protocol.”
- “The sub-22 ns measurement represents the production C++ controller in a controlled benchmark.”
- “The data-driven baseline is a fair implementation of a competitive prior method.”
- “The method is the first use of backpressure to actuate semantic window size.”
- “The project is reproducible from `scripts/reproduce_all.sh`.”

Each can become a release claim later, but only through the claim-to-evidence process in this plan.

---

## 4. Rehabilitation principles

### 4.1 Preserve truth and history

- Keep the existing Git history. Use `git mv` for structural moves so similarity tracking remains useful.
- Make the factory migration an explicit rehabilitation commit series. Do not falsify provenance by rewriting history to make the repository literally appear Factory-generated in the past.
- “Looks like it came from the Factory” means the present tree, contracts, evidence, and release process are Factory-consistent. It does not mean erasing how the project actually developed.
- Before touching generated artifacts, create checksums and a manifest. Before touching tracked files, preserve the dirty diff and untracked work in a reviewable recovery point.
- Never delete a legacy document solely because it is messy. First determine whether it contains unique decisions, claims, or citations. Preserve useful historical material under the Factory project's nested history; remove duplicate generated concatenations only after the unique-content check.

### 4.2 Separate facts, hypotheses, and recommendations

Every rehabilitation report should label findings as:

- **Observed:** directly verified from files, commands, hashes, or outputs.
- **Inferred:** the most likely interpretation, with its evidence and uncertainty.
- **Required:** mandated by Factory, a selected venue, a license, or an accepted project invariant.
- **Recommended:** an engineering choice that still needs Architect/Human approval.

Legacy result prose must never be used as raw evidence. Raw CSV/JSON/log data and exact commands are the evidence; summaries are interpretations.

### 4.3 One source of truth per responsibility

- One version source, from which CMake/package/header/version output is generated.
- One controller-default configuration, stored in a machine-readable file and echoed into every run manifest.
- One metric implementation per named metric, with an independent verifier.
- One canonical experiment schema and run-ID format.
- One data identity per artifact; real and synthetic datasets cannot share paths.
- One canonical architecture document and one append-only decision log.
- One public README that is mechanically checked against actual target names/options where feasible.

### 4.4 Generated artifacts are not source

Build products, editor caches, Python caches, raw datasets, trained binaries, run CSVs, figures, profiler output, sanitizer output, notebooks executed in place, and logs should not live in Git merely because they are useful locally. Their schemas, generating code, configurations, checksums, small test fixtures, and selected release summaries should live in Git.

Ignoring a file is not a substitute for ownership. Every ignored artifact class needs:

- an owning command or external source;
- a documented location;
- a retention policy;
- a reproducibility or reacquisition path;
- a manifest/checksum policy if it supports a claim.

### 4.5 Fail closed on science

- Unknown provenance means “not valid for real-data claims,” not “probably real.”
- Missing optional metric dependencies must fail the requested metric, not silently select a different algorithm.
- Failed acquisition must block; it must never invoke a synthetic fallback unless the contract explicitly requests a separately labeled simulation experiment.
- A null or below-threshold core result invokes the pre-registered action. It is not rewritten into success after the fact.
- A P95 observation is described as an observed percentile, never as a strict guarantee without a formal bound and worst-case evidence.

### 4.6 Keep Factory internals distinct from the public project

Software Factory v2.2.0 deliberately separates:

- `factory/`: reusable process infrastructure, ignored by the outer repository;
- `project/`: Factory planning/evidence artifacts, ignored by the outer repository but maintained in its own nested Git repository;
- `source/`: project implementation tracked by the outer repository;
- `DROP_HERE/` and `TAKE_THIS/`: ignored transfer directories.

KLStream's public repository may still contain root-level release metadata, build entry points, CI, documentation, scripts, paper, and data manifests. Actual implementation will be consolidated under `source/`. This preserves a normal public clone while satisfying the Factory's implementation boundary.

---

## 5. Target repository architecture

The exact tree is finalized in `project/architecture.md`, but the recommended end state is:

```text
brolq/
├── .git/                            # existing outer history, preserved
├── .github/
│   ├── workflows/                   # build, test, sanitizers, analysis smoke, release
│   └── ISSUE_TEMPLATE/
├── .clang-format
├── .clang-tidy
├── .dockerignore
├── .gitattributes
├── .gitignore                       # Factory internals + generated artifacts
├── CMakeLists.txt                   # small top-level build entry point
├── CMakePresets.json                # supported build/test presets
├── Dockerfile
├── compose.yaml
├── LICENSE
├── README.md
├── CHANGELOG.md
├── CITATION.cff
├── CONTRIBUTING.md
├── SECURITY.md
├── REPRODUCIBILITY.md
├── pyproject.toml                   # analysis package/dependencies/tooling
├── lockfile-or-constraints          # exact Python resolution selected by Architect
├── cmake/
│   ├── KLStreamConfig.cmake.in
│   ├── KLStreamOptions.cmake
│   └── KLStreamWarnings.cmake
├── source/
│   ├── include/klstream/
│   │   ├── core/
│   │   ├── model/
│   │   ├── operators/
│   │   └── window/
│   ├── apps/
│   │   └── adaptive_window/
│   ├── examples/
│   ├── tests/
│   │   ├── unit/
│   │   ├── semantic/
│   │   ├── concurrency/
│   │   ├── integration/
│   │   ├── regression/
│   │   └── fixtures/
│   ├── benchmarks/
│   │   ├── micro/
│   │   └── system/
│   └── experiments/
│       ├── configs/
│       ├── schemas/
│       ├── preprocessing/
│       ├── runners/
│       ├── analysis/
│       └── verification/
├── data/
│   ├── README.md                    # acquisition/licensing instructions
│   ├── manifests/                   # tracked identities/checksums/provenance
│   ├── fixtures/                    # tiny redistributable test-only data
│   ├── raw/                         # ignored
│   ├── interim/                     # ignored
│   ├── processed/                   # ignored except manifests
│   └── models/                      # ignored except manifests
├── artifacts/
│   ├── README.md                    # layout and external archive mapping
│   ├── runs/                        # ignored
│   ├── figures/                     # generated, ignored unless release-selected
│   └── releases/                    # staged bundles, ignored
├── docs/
│   ├── architecture/
│   ├── api/
│   └── design/
├── paper/
│   ├── manuscript/
│   ├── bibliography/
│   ├── tables/
│   └── figures/                     # generated from certified artifacts
├── scripts/
│   ├── bootstrap_dev.sh
│   ├── build.sh
│   ├── test.sh
│   ├── reproduce.sh
│   ├── verify_release.sh
│   └── archive_run.sh
├── factory/                         # installed v2.2.0; outer-Git ignored
├── project/                         # nested Git; outer-Git ignored
├── DROP_HERE/                       # ignored
├── TAKE_THIS/                       # ignored
├── bootstrap.sh                     # ignored per Factory
└── rehabilitation_plan.md           # Phase 1 only — see §5.1 disposition; moves to
                                      # project/legacy/specifications/ once roadmap.md exists
```

The tree should not be created mechanically in one enormous move. It should be reached through a migration manifest that maps every existing path to `keep`, `move`, `consolidate`, `archive`, `externally archive`, or `delete after proof`.

### 5.1 Existing-path disposition

| Existing path | Planned disposition | Rationale |
|---|---|---|
| `.clang-format` | Keep at root; align declared standard with C++17 and CI clang-format version | Current file says C++20 while the project claims C++17. |
| `.clang-tidy` | Keep at root; version-pin checks and integrate into CI | Useful policy, currently not a reliable release gate. |
| `.vscode/` | Remove local copies from working tree; keep ignored. Optionally add a minimal tracked editor-recommendation policy only if the team chooses it | Current launch targets are stale and the directory is already ignored. |
| `.cache/`, `.DS_Store` | Remove after snapshot; keep ignored | Pure local/generated state. |
| `CMakeLists.txt` | Retain as top-level entry; reduce to coherent options, dependencies, install/export, tests, apps, and subdirectories | Current build is functional but contradicts README/scripts and fetches test/benchmark dependencies unconditionally. |
| `cmake/klstream-config.cmake.in` | Rename consistently and activate through install/export tests, or remove if packaging is explicitly rejected | An unused template is misleading. |
| `include/klstream/` | Move with history to `source/include/klstream/` | Canonical public API implementation. |
| `src/core/` | Quarantine and audit; likely remove as obsolete in a dedicated contract | These files reference removed types/headers and are not compiled. Their presence falsely suggests a second runtime implementation. |
| `adaptive_window/` | Move to `source/apps/adaptive_window/` | It is the research application, not an unrelated root module. |
| `examples/` | Move to `source/examples/`; update every target and README command | Keep examples as executable API tests. |
| `tests/` | Move to structured `source/tests/`; register tests at the top level | Current tests omit the adaptive application/model/metrics semantics and are invisible to root CTest. |
| `benchmarks/` | Move to `source/benchmarks/`; separate correctness-independent microbenchmarks from research experiments | Benchmarks are not tests and should not be built by default. |
| `research/adaptive_backpressure/`, `research/core_pinning/` | Move to `source/experiments/runtime/` if retained; otherwise archive with a decision record | Existing saved results are invalid as headline evidence and expose several metrics defects. |
| `research/results/*.csv` | Remove from Git index after external archival and checksum; retain only curated, schema-valid summaries if justified | They are generated, currently tracked despite matching ignore rules, and some final throughput lines are zero because the reporter resets counters. |
| `analysis/` | Consolidate under `source/experiments/analysis/` as an importable/tested Python package | Current scripts rely on working directory and optional package behavior. |
| `preprocessing/` | Move to `source/experiments/preprocessing/`; split real acquisition/preprocessing from explicit synthetic generation | Prevent data-kind collisions and silent fallback. |
| `scripts/` | Keep root public front doors, rewrite against presets and canonical target names | `dev.sh bench`, `dev.sh test`, and Docker flows currently use wrong or ineffective commands. |
| Root `check_correlation.py`, `analysis/check_correlation.py`, `analysis/check_correlation_v2.py` | Preserve all three during audit, select one verified implementation, add semantic tests, then delete superseded copies in a recorded consolidation | Multiple near-duplicate scripts and “replaces” comments create uncertain authority. |
| `generate_notebook.py` and deleted `analysis/results_notebook.ipynb` | Decide in the dirty-worktree disposition. Prefer generated notebooks outside source, with a tracked clean template only if it adds value | Avoid committing stale execution output and duplicate result prose. |
| `data/` | Replace with documented tiered layout; externalize licensed/raw/processed/model binaries; track manifests and tiny fixtures | Current blanket ignore hides the absence of provenance. |
| `results/` | Rename conceptually to `artifacts/`; checksum and externally archive the 2.5 GB legacy set as `legacy-unverified`; do not use it for release claims | It remains valuable diagnostic history even though its scientific status is unverified. |
| `paper/draft.md` | Preserve, mark `LEGACY EVIDENCE — NOT SUBMISSION READY`, then rewrite from validated artifacts under `paper/manuscript/` | Do not patch around invalid evidence. |
| `README.md` | Rewrite after the build/API contract stabilizes; add a mechanical docs-sync test | Current structure, files, binaries, CMake options, license, and examples are inconsistent. |
| `report.md` | Move to `project/legacy/status/` after Factory bootstrap | Historical progress log, not public project documentation. |
| `KLStream_Complete_Implementation_Guide.md`, `KLStream_Research.md` | Import into `project/legacy/specifications/` and synthesize durable knowledge into `project_knowledge.md` | Useful design history currently ignored by filename. |
| `study.md` | Import into `project/legacy/reviews/`; do not treat its “resolved” labels as evidence | It contains useful findings as well as incorrect latency/provenance statements. |
| `full_description.md` | Verify it is generated concatenation; preserve one archival copy, then remove from working root | It duplicates thousands of lines of source/docs and should not be a source of truth. |
| `Dockerfile`, `docker-compose.yml` | Retain at root, repair and rename Compose file to current convention | Current build args are unused and runtime copies a nonexistent binary. |
| `rehabilitation_plan.md` (this document) | Preserve at root through Phase 1. Once `project/roadmap.md`, `project/project_knowledge.md`, and `project/invariants.md` exist and pass the Step 4 cross-consistency check, import this document into `project/legacy/specifications/` and leave a one-paragraph root-level pointer to its successor artifacts | It is architecturally the same kind of thing as `KLStream_Complete_Implementation_Guide.md` and `KLStream_Research.md` above: a pre-Factory planning document. Leaving it live at root indefinitely alongside `project/roadmap.md` creates exactly the two-sources-of-truth problem Section 4.3 warns against, since the two will diverge the moment any Architecture Amendment or Fix Package changes the plan of record. |

### 5.2 Git ignore policy

The new `.gitignore` should be explicit and path-scoped. Avoid broad rules such as global `*.csv`, `*.bin`, or named-document ignores, because those hide legitimate fixtures, manifests, or documentation.

Required categories include:

```gitignore
# Factory v2.2.0 outer-repository isolation
/factory/
/project/
/bootstrap.sh
/DROP_HERE/
/TAKE_THIS/
/.factory_temp/

# Operating-system and editor state
.DS_Store
.AppleDouble
Thumbs.db
.idea/
.vscode/
*.swp
*.swo
*~

# CMake and compiler output at any supported local build root
/build/
/build-*/
/cmake-build-*/
/out/
/compile_commands.json
CMakeCache.txt
CMakeFiles/
Testing/

# Python environment and caches
__pycache__/
*.py[cod]
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
htmlcov/
.venv/
venv/

# Sanitizer, profiler, coverage, benchmark temporary output
*.profraw
*.profdata
*.gcda
*.gcno
*.gcov
coverage/

# Local data and models; tracked manifests/fixtures live elsewhere
/data/raw/
/data/interim/
/data/processed/
/data/models/

# Generated experiment/release artifacts
/artifacts/runs/
/artifacts/figures/
/artifacts/releases/

# Logs and temporary files
*.log
*.tmp
*.temp
```

The migration contract must also run `git ls-files -ci --exclude-standard` and remove already-tracked generated files from the index only after their preservation manifest exists. The current tracked `analysis/__pycache__/*.pyc` and `research/results/*.csv` are known examples.

The `.dockerignore` should independently exclude Factory internals, nested project history, build trees, raw data, run artifacts, editor/cache state, and `.git`, while retaining any release metadata the image actually needs. It should not use `*.md` as a proxy for “irrelevant documentation.”

---

## 6. Factory operating model for the rehabilitation

### 6.1 Authority and roles

| Role | KLStream rehabilitation responsibility |
|---|---|
| Human | Approve the target venue, license, public/private data policy, release scope, and any architecture amendment; provide licensed data or credentials; perform independent data spot checks; approve release. |
| Architect | Create founding artifacts, make all architecture and scientific-method decisions, assign risk/claim tiers, implement High-risk contracts, conduct MAR and Chunk Reviews, inspect raw evidence, write fix packages. |
| Implementor | Execute Low/Medium contracts exactly as written, run real verification, preserve allowed/frozen boundaries, report failures and evidence, never redesign or silently substitute. |
| Gatekeeper | Run deterministic checks that v2.2.0 actually implements: snapshots, frozen hashes, report structure, repository checks, tier inference, verification reruns, lint, recomputation, stamps, evidence checks, acquisition audit, release checks, and release certification. |

No standing third role should be invented. Because the project targets publication, the Human should arrange a one-time genuinely independent methodology review for MAR-4 through MAR-7 if practical. That is a project-specific strengthening, not a new Factory role.

Section 6.5's risk-tier rules concentrate a large share of KLStream's highest-stakes work — queue memory ordering, runtime lifecycle, decision thresholds, dataset splits, metric semantics, statistical protocol, and claim wording — into the Architect-owned High-risk category. Across the 76 contracts proposed in Sections 7-15, this plan currently states an explicit Owner for only 19 of them (all 10 in Chunk 01 and all 9 in Chunk 02); Chunks 03 through 09 name a Risk/Claim tier but not an Owner (Section 6.7 makes completing this a Chunk 01 deliverable). Applying Section 6.1's own rule (High risk → Architect) to the tiers Chunk 03 already states implies the Architect personally implements essentially all nine of that chunk's contracts, not merely reviews them. That is the right call given the concurrency and scientific-validity stakes involved, but it is a substantive hands-on implementation commitment, not only a review commitment, and should be planned as such — as a count of Architect sessions this actually costs — rather than left as an implication of a risk table discovered contract-by-contract.

### 6.2 Factory installation and isolation

Factory adoption must occur on a preservation branch after the dirty state is secured. Use the audited v2.2.0 bootstrap, record its version and commit in `project/factory_info.*`, and leave the supplied `/Users/adi/Downloads/factory_v2_2_0` tree read-only.

Bootstrap is idempotent but does not migrate existing KLStream files into `source/`. The migration remains explicit project work. After bootstrap:

- verify `factory/VERSION` is `2.2.0`;
- run `python3 factory/gatekeeper.py self-check` and preserve literal output;
- confirm Factory files match the recorded provenance;
- confirm `project/.git` exists and is independent of the outer repository;
- commit every founding/project artifact with `gatekeeper.py commit-project`;
- confirm Factory paths are ignored by the outer repository;
- do not place source files in `DROP_HERE/`; use normal contract execution or Factory materialization for Architect-owned High-risk work.

### 6.3 Founding artifacts

Before Chunk 01, the Architect produces mutually consistent versions of:

- `project/project_description.md`
- `project/architecture.md`
- `project/roadmap.md`
- `project/project_knowledge.md`
- `project/invariants.md`
- `project/venue_requirements.md`
- `project/key_facts.md`
- `project/methodology_adversarial_review.md`

The target venue must be named, not merely “IEEE.” `venue_requirements.md` must contain at least three actually reviewed recent papers from the chosen venue, their data units, baselines, methodology, and statistical conventions. If the venue is undecided, MAR-5 fails and Chunk 01 publication work does not start; engineering-only rehabilitation may proceed under an explicitly non-submission scope.

### 6.4 Proposed project invariants

The Architect should formalize at least these invariants with IDs, reasons, verification methods, and failure impacts:

| Proposed invariant | Meaning |
|---|---|
| INV-001 Data-kind identity | Every dataset is explicitly real-derived, synthetic, or fixture; kinds never share an identity/path. |
| INV-002 No silent substitution | Acquisition failure blocks. Synthetic generation is never an automatic fallback. |
| INV-003 Immutable raw evidence | Raw inputs and certified result artifacts are content-addressed and never overwritten. |
| INV-004 Provenance continuity | Every model feature traces to raw input and named transformations. |
| INV-005 Split isolation | Test data cannot affect preprocessing statistics, model fitting, threshold tuning, hyperparameters, or stopping decisions. |
| INV-006 Configuration identity | Every run records code, data, model, config, dependency, compiler, host, and seed identity. |
| INV-007 Event accounting | Emitted, queued, processed, dropped, and flushed event counts reconcile under the declared shutdown policy. |
| INV-008 Queue contract | Capacity, producer/consumer topology, object lifetime, ordering, and memory semantics are explicit and tested. |
| INV-009 Runtime lifecycle | Each operator initializes and shuts down exactly once on the documented thread; stop/drain semantics are deterministic. |
| INV-010 Exact latency semantics | A reported latency names its start/end clocks and is computed from the correct event, without undocumented interpolation. |
| INV-011 Metric identity | A named metric is backed by one specified algorithm/version and independent known-answer tests. |
| INV-012 Fair comparison | All architectures use the same eligible data, model, threshold-selection protocol, instrumentation, and resource controls unless a declared ablation changes one. |
| INV-013 Claims trace to evidence | Every number/adjective in release artifacts maps to an immutable artifact and exact recomputation. |
| INV-014 Build/documentation sync | Public target names, options, examples, version, and platform claims match the actual build. |
| INV-015 Generated-state exclusion | Build/cache/raw-run artifacts never enter Git except approved tiny fixtures and release summaries. |
| INV-016 Release hygiene | No secret, local path, machine identity, prohibited data, or unlicensed material appears in a release. |
| INV-017 Version singularity | Project version has one canonical source and is reflected consistently everywhere. |
| INV-018 Reproducible clean clone | A documented clean environment can build, test, and reproduce the permitted result path. |

Scientific validity invariants SVI-001 through SVI-007 from Factory v2.2.0 apply in addition to these project invariants.

### 6.5 Contract discipline

Every formal contract must include Objective, Context, Dependencies, Risk Tier, Implementation Owner, Scientific Claim Tier, Allowed Files, Frozen Files, Inputs, Outputs, Implementation Instructions, Verification Scripts, Required Verification Commands where applicable, Invariant Checklist, Predicted Failure Modes, Definition of Done, Stop Condition, and `Traces To`.

For KLStream:

- Queue memory ordering, runtime lifecycle, shutdown/drain, decision thresholds, dataset splits, metric semantics, statistical protocol, and claim wording are High-risk.
- Build cleanup, packaging, Python refactors, container repair, and most new tests are Medium-risk unless they affect a Frozen scientific invariant.
- Pure moves, ignore entries, formatting, and boilerplate metadata may be Low-risk after their migration manifest is frozen.
- Any contract reporting a metric is at least T-DESC.
- Any architecture comparison is T-COMP.
- Any claim that backpressure causes a latency/accuracy outcome, that a mechanism is robust, or that an ablation establishes causality is T-CAUSAL.

T-COMP and T-CAUSAL contracts must use exact required verification commands, independent recomputation, linting, a valid report stamp, and the Mandatory Mechanical Gate. `tier-check` runs on every drafted contract before handoff and again at completion.

### 6.6 Per-contract execution loop

Each Implementor-owned contract follows Factory Phases 1 through 4:

1. **Planning:** verbatim comprehension check, repository validation, risk/failure-mode review, checkpoint and verification plan; no implementation.
2. **Implementation:** change only Allowed Files; verify at each checkpoint with literal commands and outputs.
3. **Self Review:** audit allowed/frozen files, Definition of Done, fresh verification, invariants, predicted failures, stop conditions, and quality. Five attempts maximum; never weaken a test.
4. **Reporting:** self-contained contract report, telemetry, decisions, repository state, and honest final status.

At chunk end, the Implementor compiles a self-contained chunk report. The Architect then reviews raw diffs and raw verification for every Medium/High contract, manually checks Allowed Files because Gatekeeper v2.2.0 does not fully automate that check, performs scientific drift/baseline/title audits, and returns `APPROVED` or a Fix Package for the next chunk.

### 6.7 Owner and tier completeness before materialization

Sections 7.8 and 8.3 (Chunks 01-02) state an explicit Owner per contract. Section 9.7 (Chunk 03) states a Risk/Claim tier but not an Owner. Sections 10.8 and 11.9 (Chunks 04-05) follow the same reduced pattern. Sections 12.8, 13.7, 14.6, and 15.5 (Chunks 06-09) are unstructured lists with no Risk tier, Claim tier, or Owner stated at all. This is a real gap, not a formatting preference: Section 6.5 makes Risk Tier and Scientific Claim Tier mandatory fields on every formal contract, and Section 6.1 ties Owner directly to Risk Tier, so a chunk table that omits Owner is silently deferring a decision this plan itself says must be made deliberately.

Before any contract in Chunks 03 through 09 is drafted as a formal Factory artifact, its proposed-contract entry in this plan must carry the same fields Chunk 01 already does: Risk Tier, Scientific Claim Tier, and Owner, with Owner assigned by Section 6.1's rule (High → Architect; Medium/Low → Implementor, subject to a named Human action where one is required). Section 9.7's table is corrected below as the worked example — its tiers were already stated, so Owner follows mechanically. Chunks 04 through 09 do not yet state enough to derive Owner mechanically and must be completed by the Architect at Chunk 01 time, not invented here; `tier-check` (Section 6.5) is the deterministic backstop that catches an under-tiered contract once each chunk's real contracts are drafted, but it cannot catch a missing Owner, which is why this is a plan-level completeness rule rather than something left to Gatekeeper.

---

## 7. Phase 1 — Existing-project preservation, Factory adoption, and truth baseline

This is the mandatory starting phase. It begins with the current project exactly as it exists. It is not a cleanup sprint that assumes files can be deleted because they look irrelevant.

### 7.1 Phase 1 objective

Create a recoverable, factory-governed KLStream workspace whose repository shape is clean, whose legacy work is preserved, whose current build/test/data/result/manuscript state is accurately documented, and whose unverified claims and artifacts cannot accidentally flow into later publication work.

### 7.2 Entry conditions

- No command discards the current dirty state.
- The supplied Factory v2.2.0 directory remains read-only.
- Current `results/`, `data/`, and build trees remain in place until their inventory/checksum step completes.
- No legacy result is described as valid LOBSTER evidence.
- No full experiment is rerun during Phase 1; doing so would only create more evidence under an invalid protocol.

### 7.3 Step 1 — Preserve the current outer repository

1. Record `git status --short --branch`, remotes, HEAD, branch list, tag list, recent history, and `git diff --stat` in a preservation report.
2. Export the complete tracked diff and list every untracked file. Do not assume the deleted notebook or untracked documents are disposable.
3. Review the nine modified files, one deletion, and five pre-plan untracked files. Classify each as `retain as WIP`, `supersede after import`, `generated`, or `needs Human decision`.
4. Create a non-destructive rehabilitation branch using the `codex/` branch prefix or the Human's chosen naming policy.
5. Make a preservation commit containing the existing WIP exactly as accepted by the Human, or store a clearly named patch plus checksum if the Human does not want the WIP committed yet. A mixed half-staged state is not an acceptable base for Factory bootstrap.
6. Create a signed/annotated legacy-baseline tag after the preservation state is clean. Record its commit and tree hash in `project/project_knowledge.md` after bootstrap.
7. Run a repository integrity check and record its literal output. Do not garbage-collect or rewrite history during rehabilitation.

**Stop condition:** any current change cannot be attributed or safely classified. Pause structural work until it is preserved independently; never resolve uncertainty by discarding it.

### 7.4 Step 2 — Inventory and quarantine generated evidence

Produce a machine-readable legacy artifact manifest before moving or deleting anything. For every file under `data/`, `results/`, `research/results/`, `build*`, and caches, record at least:

- relative path;
- size;
- modification time;
- SHA-256 for data/results and any artifact that supports a claim;
- tracked/ignored/untracked state;
- guessed producer, labeled as inference if not proven;
- data kind if known;
- retention class;
- release eligibility (`no`, `unknown`, or `candidate`);
- external archive destination once assigned.

Create an external or local immutable archive named like `klstream-legacy-unverified-<date>-<tree-hash>`. Store its own manifest and checksum separately. `results/` should then be labeled `legacy-unverified`; do not rename or delete it until archive verification succeeds.

The quarantine report must explicitly state:

- current replay provenance is unproved and strongly indicates synthetic generation;
- current `forest.bin` inherits that uncertainty;
- all current result files inherit the uncertainty of replay/model/protocol;
- tracked research benchmark files include host metadata and known counter-reset problems;
- the paper and summary files are interpretations, not evidence;
- no legacy artifact is automatically approved for a release even if a number can be recomputed from it.

**Stop condition:** archive hash verification fails or a claim-supporting artifact lacks enough identity to preserve. Do not remove the original.

### 7.5 Step 3 — Bootstrap Factory v2.2.0

1. Run the audited bootstrap on the preservation branch.
2. Confirm it creates/fills `factory/`, `project/`, `project/chunks/`, `source/`, `DROP_HERE/`, and `TAKE_THIS/` without overwriting the existing tree.
3. Verify Factory version/provenance and run self-check.
4. Verify outer ignore rules and nested `project/.git` isolation.
5. Commit Factory initialization in the nested project repository.

Do not move KLStream source in the same commit as bootstrap. Bootstrap provenance and code migration should remain independently reviewable.

### 7.6 Step 4 — Write the founding artifacts from observed reality

The founding documents must describe both current state and intended end state. They must not copy the legacy guide's aspirational statements as if already implemented.

`project_description.md` should distinguish three related products:

1. **KLStream runtime:** bounded single-node stream processing in C++17.
2. **Adaptive-window application:** a research mechanism layered on the runtime.
3. **Reproducibility/publication package:** data transforms, experiments, analysis, and manuscript.

It should also state non-goals until evidence changes them: distributed execution, Kafka compatibility, Windows support, production HFT deployment, actual wash-trade attribution, and strict real-time guarantees.

`architecture.md` should decide and document:

- header-only versus compiled-library boundaries;
- public versus experimental namespaces/APIs;
- queue capacity semantics;
- runtime ownership and lifecycle;
- event/clock/sequence model;
- exact window and detection semantics;
- data identity and split model;
- experiment artifact model;
- packaging and supported platforms;
- manuscript/evidence boundary.

`roadmap.md` should use the chunks in this plan as architectural milestones, not calendar weeks.

`project_knowledge.md` should import stable knowledge from the two large implementation/research guides, Git history, current code, and audit reports while marking unverified assumptions. It remains living and append-only for newly discovered assumptions.

`invariants.md` should formalize the proposed invariants above and their executable verification methods.

`venue_requirements.md` and `key_facts.md` must be real, populated artifacts. Key facts should include dataset identity/count, model configuration, controller defaults, queue capacity, run unit, sample count, primary metric, main latency definition, and every headline number once the final protocol is frozen.

### 7.7 Step 5 — Run Methodology Adversarial Review

MAR must attack the project as it exists, not the project the team hopes it becomes.

Required hostile-review questions include:

1. Is the current replay genuinely derived from LOBSTER, or a synthetic generator that shares its filename?
2. Does window size affect model context, or only batching/max aggregation and prediction expansion?
3. Why would scoring every point in smaller batches reduce total compute when total per-point forest work remains similar and fixed per-batch overhead may increase?
4. Does the PA%K code implement the cited protocol using individual point scores?
5. Are 30 scheduler repetitions on one deterministic dataset valid independent units for the stated statistical claim?
6. Was the detection threshold selected without test-set information?
7. Are baseline methods fair, venue-appropriate, and independently sourced?
8. Does P95 evidence justify “guarantee” or “bounds” language?
9. Is the latency timestamp the exact flagged event's pipeline-entry time?
10. Can a reader legally and practically reproduce the real-data path?

Expected initial outcome is at best `CONDITIONAL PASS`, with conditions becoming mandatory Chunk 01 or later contracts. The observed synthetic/LOBSTER contradiction is a FAIL for any real-data publication path until resolved.

### 7.8 Proposed Chunk 01 contracts

Formal artifacts will be generated by the Architect, but the intended contract split is:

| Contract | Objective | Risk | Claim tier | Owner | Principal evidence |
|---|---|---:|---:|---|---|
| C01-01 | Preserve dirty WIP, branch, tag, and repository evidence | Medium | NONE | Implementor | Clean preservation state; hashes; recovery instructions |
| C01-02 | Manifest and externally archive all legacy generated artifacts | Medium | T-DESC | Implementor | Artifact inventory; archive checksum verification |
| C01-03 | Determine current replay/model/result provenance and write quarantine verdict | High | T-DESC | Architect | Independent file/script comparison; provenance report; no unsupported upgrade |
| C01-04 | Install and verify Factory v2.2.0 isolation | Low | NONE | Implementor | Self-check; factory info; nested/outer Git tests |
| C01-05 | Produce and cross-check founding artifacts and invariants | High | NONE | Architect | Six founding cross-consistency checks; decision log |
| C01-06 | Run MAR and create conditions/falsification register | High | T-DESC | Architect | Per-gate verdicts; hostile reviewer simulation |
| C01-07 | Create and execute the complete file-migration manifest | Medium | NONE | Implementor | Before/after path inventory; no lost tracked files; history similarity check |
| C01-08 | Replace broad ignore rules and remove tracked generated state from the index | Low | NONE | Implementor | `git check-ignore`; tracked-ignored audit; clean tree |
| C01-09 | Repair the top-level build/test front door without redesigning runtime semantics | Medium | T-DESC | Implementor | Fresh Release/Debug build; root CTest executes all current tests; regression for zero-test failure |
| C01-10 | Write the baseline rehabilitation report and technical-debt register | Medium | T-DESC | Implementor | Self-contained observed-state report; raw command outputs |

C01-03, C01-05, and C01-06 are Architect-owned because data identity, claim scope, and founding invariants are expensive to get subtly wrong. C01-07 may not delete `src/core` or scientific code merely because the target tree says it is likely obsolete; those deletions receive their own later correctness contracts.

### 7.9 Phase 1 verification

Minimum commands/artifacts include:

- clean outer and nested project Git status;
- archived pre-migration status/diff/hash report;
- full before/after path manifest;
- external archive checksum verification;
- `git ls-files -ci --exclude-standard` returns only deliberately grandfathered entries, ideally none;
- root build succeeds in a fresh build directory;
- root CTest discovers and executes the expected named tests; zero tests is a hard failure;
- Factory self-check literal output;
- Factory snapshot/check for every Chunk 01 contract;
- manual Allowed/Frozen diff audit;
- MAR report and condition-to-contract mapping;
- no manuscript/result/data claim silently upgraded.

### 7.10 Phase 1 exit criteria

Phase 1 ends only when:

- the pre-rehabilitation state is recoverable;
- the dirty work is explicitly preserved or dispositioned;
- Factory v2.2.0 is installed and verified without modifying its supplied source;
- all founding artifacts exist, are cross-consistent, and are committed in `project/`;
- MAR has no unresolved FAIL for work scheduled in the next phase;
- current evidence is visibly quarantined from release evidence;
- the repository matches the agreed clean structure;
- generated/cached/large files are absent from Git but not lost;
- one documented top-level build/test command runs real tests;
- Chunk 01 receives Architect `APPROVED`, not merely Implementor `COMPLETE`.

---

## 8. Phase 2 — Build, packaging, and public repository contract

### 8.1 Objective

Turn the reorganized source into a coherent software product whose build, API, dependency, installation, container, documentation, and CI surfaces agree. This phase deliberately avoids changing concurrency or scientific semantics except where required to make them testable.

### 8.2 Architecture decisions

The Architect must resolve the current hybrid state: CMake declares KLStream header-only, while stale `.cpp` files imply a compiled runtime. The recommended near-term decision is:

- keep template-heavy queues/operators header-based;
- either keep the runtime/metrics genuinely header-only and delete obsolete sources, or move non-template implementation into a real compiled target;
- never retain uncompiled incompatible `.cpp` files as decoration;
- expose experimental adaptive-window APIs separately from stable core APIs until their contracts settle.

Whichever option is chosen must be verified by an install-consumer test, not only by in-tree examples.

### 8.3 Proposed Chunk 02 contracts

| Contract | Scope | Risk/owner | Required result |
|---|---|---|---|
| C02-01 | Freeze public target/API/library architecture; disposition obsolete `src/core` | High / Architect | One implementation path; no dead parallel architecture; decision recorded |
| C02-02 | Rebuild CMake options and presets | Medium / Implementor | `BUILD_TESTING`, examples, benchmarks, research apps, sanitizers, LTO, warnings, native tuning all work and are documented |
| C02-03 | Add install/export/package config and external consumer smoke test | Medium / Implementor | `find_package(KLStream CONFIG REQUIRED)` works from an installed prefix |
| C02-04 | Make public headers self-contained and warning-clean | Medium / Implementor | Each header compiles alone under supported compilers; include-what-you-use defects fixed |
| C02-05 | Normalize version, package metadata, and changelog | Medium / Implementor | One canonical version generates CMake/header/package/CITATION values |
| C02-06 | Repair developer scripts and target names | Medium / Implementor | Build/test/bench/format/lint commands call existing targets and fail on zero work |
| C02-07 | Repair Docker/Compose reproducibility | Medium / Implementor | Builder runs tests; runtime copies an existing binary; non-root run; pinned base/toolchain policy |
| C02-08 | Establish CI platform/compiler matrix | Medium / Implementor | Linux GCC, Linux Clang, macOS AppleClang at minimum; supported claims match passing jobs |
| C02-09 | Add legal/community/release metadata | Low, with Human license decision | LICENSE, citation, contributing, security, code/release policy |

### 8.4 Build-system requirements

- Do not overwrite `CMAKE_CXX_FLAGS_RELEASE`; use target-scoped compile/link options.
- Do not enable `-march=native` for distributable release binaries by default. Provide an opt-in native preset for local benchmarks.
- Use `find_package(Threads REQUIRED)` and `Threads::Threads` instead of raw `pthread`.
- Fetch GoogleTest only when tests are enabled and Google Benchmark only when benchmarks are enabled.
- Pin dependency versions and support an offline/pre-fetched path.
- Reject incompatible sanitizer combinations at configure time.
- Use top-level `include(CTest)` so root CTest owns discovery.
- Treat warnings as errors in CI-owned code while avoiding that policy for third-party dependencies.
- Add a configure-time summary showing every option and selected compiler/platform.
- Add `cmake --build`, `ctest`, `cmake --install`, and package-consumer presets.
- Explicitly declare supported platforms. Windows remains out of scope unless it gains a real port and CI evidence.

### 8.5 Documentation/release-surface requirements

README examples must be compiled as tests. Target names such as `basic_pipeline`, `ysb_pipeline`, and `adaptive_window_main` must agree across README, scripts, Docker, CI, and CMake. Advertised options must exist. The license statement must point to an actual Human-approved license file. Benchmarks must describe the tested hardware/configuration and must not be marketed as general performance promises.

### 8.6 Phase 2 exit criteria

- Fresh Debug and Release configurations succeed without using old build caches.
- Top-level CTest runs all tests.
- Disabled tests/benchmarks do not download their dependencies.
- ASan/UBSan and TSan presets configure as intended on their supported hosts.
- Installation and external consumer build pass.
- Docker builder and runtime smoke tests pass.
- CI is green on every platform the README claims.
- The tree contains no uncompiled obsolete implementation files.
- README build commands are executed in CI.

---

## 9. Phase 3 — Core runtime and model correctness

### 9.1 Objective

Make the runtime semantics strong enough that later scientific measurements can trust event flow, scheduling, timestamps, and metrics. Performance comes after correctness.

### 9.2 Queue contracts

The SPSC and MPMC queues require High-risk review because they combine C++ object lifetime and concurrent memory ordering.

The queue contract must define:

- whether `capacity()` means allocated slots or usable elements;
- whether SPSC and MPMC have identical capacity semantics;
- accepted `T` requirements beyond “trivially copyable”;
- construction/destruction rules for elements in raw storage under C++17;
- behavior for invalid capacities in Release builds;
- full/empty/occupancy behavior, including MPMC full state;
- counter wraparound assumptions;
- null-output behavior;
- blocking-operation cancellation/shutdown behavior;
- exact single-producer/single-consumer obligations;
- memory-order proof or authoritative algorithm basis.

Known-answer and adversarial tests must include capacity 2, wraparound, full-to-pop-to-push, MPMC full occupancy, many producers/consumers with unique item IDs, duplicate/loss detection, forced tight races, long runs under TSan, and invalid constructor inputs with assertions disabled.

### 9.3 Runtime lifecycle and event accounting

Define a lifecycle state machine such as `Created -> Started -> StopRequested -> Draining -> Stopped`. Verify:

- `init` and `shutdown` occur exactly once;
- callbacks occur on the documented thread;
- `stop()` is idempotent without calling `shutdown` repeatedly;
- worker destruction cannot repeat lifecycle callbacks;
- a worker's affinity is not unpredictably overwritten by the last registered operator;
- stopping either drains all complete queued work or reports exact dropped/partial counts according to a declared policy;
- partial windows have a documented flush/discard behavior;
- sink files open successfully, flush exactly once, and report failures;
- exceptions inside operators/threads cannot silently terminate or fabricate success;
- Runtime cannot start with invalid worker/operator topology;
- the metrics reporter cannot add one-second shutdown latency unless explicitly configured.

The current statement “processes 100% of incoming tuples” remains forbidden until event-accounting tests reconcile source generation, every queue, every operator, sink results, partial windows, and stop-time drops.

### 9.4 Metrics correctness

Separate cumulative counters from interval reporter deltas. The reporter must never destroy the only cumulative measurement. Repair percentile calculation using a mathematically correct rank convention; do not return zero for a one-sample nonzero latency because the rank target truncates to zero. Treat histogram overflow as censored/overflow data, not an exact 10 ms observation. Either widen/use a dynamic HDR-style structure or report overflow counts and avoid claims beyond the measurable range.

Metrics tests must cover:

- one and two samples;
- exact percentile boundaries;
- overflow;
- concurrent record/snapshot;
- reporter interval output;
- cumulative final value after reporting;
- stable machine-readable output without host leakage in public summaries.

### 9.5 Backpressure and controller correctness

- Set and preserve `SourceOperator::original_rate_`; the current recovery path can clamp the rate to zero.
- Validate positive rates/bursts and define whether changing the rate changes burst capacity.
- Test hard and soft pressure at actual usable capacity.
- Validate controller parameters: `w_min > 0`, `w_min <= w_max <= MAX_WINDOW_SIZE`, `0 <= occ_low < occ_high <= 1`, `0 < shrink < 1`, `grow > 1`, and valid EMA alpha.
- Prevent `WindowBatch::push_back` overflow in every build mode.
- Record the actual EMA occupancy and controller decision into output evidence.
- Verify update-at-window-start semantics with deterministic occupancy traces.
- Add hysteresis, monotonic response, boundary, clamp, and metamorphic tests.

### 9.6 Isolation Forest correctness and serialization

The named mathematical model requires semantic tests, not merely rank correlation with a different randomly constructed sklearn model.

Required work includes:

- known-answer small-tree path-length and `c(n)` tests;
- deterministic seed/repeat tests;
- constant-feature and small-dataset behavior;
- empty-data/model validation;
- correct normalization when actual sample count is below configured `psi`;
- finite/non-NaN score guarantees;
- independent reference comparisons on frozen fixtures with documented tolerance;
- train/test leakage tests;
- versioned, endian/size-safe model format with magic, schema version, dimensions, estimator count, checksum, and validation;
- corrupted/truncated/untrusted model rejection;
- model manifest tying binary to training data/config/code.

### 9.7 Proposed Chunk 03 contracts

Owner is derived from Risk tier per Section 6.1 (High → Architect; Medium → Implementor); this column was previously omitted (Section 6.7).

| Contract | Risk/tier | Owner | Core verification |
|---|---|---|---|
| C03-01 SPSC storage/capacity/memory-order correctness | High / NONE | Architect | Semantic + adversarial + sanitizer tests; exact contract proof |
| C03-02 MPMC storage/occupancy/memory-order correctness | High / NONE | Architect | Full-state test; unique-item race test; TSan |
| C03-03 Runtime state machine, drain, and exactly-once lifecycle | High / NONE | Architect | Forced backpressure/stop tests with event reconciliation |
| C03-04 Metrics and percentile semantics | High / T-DESC | Architect | Independent percentile verifier and overflow tests |
| C03-05 Source backpressure/rate limiting | High / T-DESC | Architect | Deterministic fake-clock token/EMA tests |
| C03-06 Window/controller bounds and evidence signals | High / T-DESC | Architect | Trace-driven known-answer tests; occupancy output not always zero |
| C03-07 Isolation Forest semantic behavior | High / T-DESC | Architect | Independent implementation/known-answer agreement |
| C03-08 Versioned model serialization | High / NONE | Architect | Round-trip, cross-build, corruption tests |
| C03-09 Full sanitizer/concurrency regression suite | Medium / NONE | Implementor | ASan/UBSan/TSan jobs with zero findings |

All nine Chunk 03 contracts but one are High-risk, which means the Architect — not the Implementor — is the one implementing eight of the project's nine queue/runtime/model correctness contracts directly. See Section 6.1's added note on what this means for session planning.

### 9.8 Phase 3 exit criteria

- All queue/runtime/model contracts are explicit and tested.
- No known race, object-lifetime, repeated-shutdown, silent-drop, or counter-reset defect remains open.
- Event accounting passes under normal completion, time-bounded stop, backpressure, and injected failure.
- Every public numerical metric has semantic known-answer tests.
- Sanitizer results are fresh and tied to the current commit.
- Performance results from before this phase remain quarantined because correctness changes invalidate them.

---

## 10. Phase 4 — Data authenticity, licensing, and Reality Gate

### 10.1 Objective

Create an auditable data supply chain that makes it impossible to confuse synthetic, real-derived, and test-fixture data, then pass the Factory Reality Gate before any new model training or headline experiment.

### 10.2 Human decisions/actions

The Human must decide and record:

1. The target publication venue.
2. Whether the final paper is a real-observation study or an explicitly simulation-based systems study.
3. Whether valid LOBSTER AAPL June 21, 2012 files are legally accessible for this project.
4. What LOBSTER-derived artifacts may be redistributed under the applicable terms.
5. Whether additional days/symbols or another public dataset can supply independent evaluation units.
6. The public repository license and any separate data/code license obligations.

If real raw data cannot be acquired or redistributed, the project can still be publishable only after claims, title, venue requirements, and methodology are explicitly reframed around simulation. It must never call synthetic base observations LOBSTER data.

### 10.3 Data identity design

Use distinct paths and immutable dataset IDs, for example:

```text
data/raw/lobster/aapl/2012-06-21/<licensed files>
data/raw/synthetic/gbm-v1/seed-42/<generated files>
data/processed/<dataset-id>/<transform-id>/replay.csv
data/manifests/<dataset-id>.data_manifest.json
data/manifests/<dataset-id>.acquisition_provenance.json
data/manifests/<dataset-id>.transform_manifest.json
```

No generator may write a file named as though it were LOBSTER-derived. The current synthetic generator must require an explicit output directory and emit `dataset_kind: synthetic` in its manifest. The real preprocessor must reject a synthetic input manifest and vice versa.

### 10.4 Acquisition provenance

For each externally acquired raw file, capture:

- provider and authoritative URL/interface;
- access date and authentication method without secrets;
- query/product/symbol/date/level parameters;
- HTTP/status or download evidence where available;
- exact filename, byte size, and SHA-256;
- license/terms reference and redistribution decision;
- connectivity pre-check result;
- no-fallback stop behavior;
- Human three-point independent spot-check record.

Run `gatekeeper.py acquisition-audit` against acquisition, preprocessing, statistical, and report files. Findings for `generate_`, `simulate_`, `fallback_`, random sampling feeding metrics, or simulation language are investigated explicitly. Legitimate synthetic generation lives in a separate declared contract and cannot be exempted into a real-data flow.

### 10.5 Transform provenance and schemas

Each processing step must be a pure or explicitly stateful transformation with:

- input dataset ID/checksum;
- code commit and command;
- complete parameters/seed;
- output schema, units, column order, ranges, counts, missing values, and checksum;
- dropped-row rules;
- anomaly-injection log with segment IDs/types/start/end/parameters;
- burst-generation log separate from anomaly labels;
- prevention of overlap and out-of-range injection;
- evidence that feature statistics used for normalization/calibration came only from eligible training data.

The manuscript currently names `injection_log.csv`, but the tree contains no such source-of-truth file. The new injection manifest must be generated and validated, not reconstructed from prose.

### 10.6 Split design

Split at the genuine independent-unit boundary before data-derived tuning. Depending on available data, that should be day/symbol/session or a blocked temporal region, not random rows from one already processed stream. At minimum:

- training: model fitting and training-only feature statistics;
- validation: anomaly threshold, controller configuration, baseline tuning, and early decisions;
- test: one final locked evaluation path;
- optional stress/simulation set: explicitly secondary and never substituted for test.

Injected anomalies need independently seeded realizations assigned before final testing. Replaying one seeded injection 30 times measures runtime variability, not anomaly-sample generalization.

### 10.7 Reality Gate checks adapted to KLStream

`project/chunks/<data-chunk>/data_manifest.json` and `reality_gate_report.md` should verify:

- row counts before/after event-type filtering;
- timestamp monotonicity, duplicates, gaps, trading-session range, and impossible jumps;
- top-of-book relationships (`ask >= bid`, positive sizes, valid event codes);
- units and plausible price/spread/volume distributions from cited domain sources;
- exact temporal/symbol/depth coverage;
- real-versus-synthetic identity and source hashes;
- feature distribution variance/entropy and suspicious perfection;
- channel/column order and type/units;
- every feature's raw-to-processed provenance chain;
- anomaly-injection and burst labels are synthetic overlays, not original market truth;
- train/validation/test isolation;
- license and release eligibility.

Because Reality Gate is currently manual in Factory v2.2.0, its script and report must be independently reviewed and frozen. A PASS is not inferred from “the file looks realistic.”

### 10.8 Proposed Chunk 04 contracts

| Contract | Risk/tier | Result |
|---|---|---|
| C04-01 Data-source/license decision and external-service contract | High / NONE | Approved data path and Human actions |
| C04-02 Real-data acquisition with fail-closed provenance | Medium / T-DESC | Acquisition manifest and hashes, or honest Human-action block |
| C04-03 Explicit synthetic dataset generator and isolation | Medium / T-DESC | Separate synthetic identity; deterministic manifest; no shared filename |
| C04-04 Schema-validated preprocessing and injection manifests | High / T-DESC | Transform lineage, known-answer feature tests |
| C04-05 Leakage-safe split assignment | High / NONE | Frozen split manifest; disjoint independent units |
| C04-06 Reality Gate implementation for KLStream | High / T-DESC | Independent checks and per-check report |
| C04-07 Human authenticity spot check | Human Action / T-DESC | Three-point independent comparison |
| C04-08 Data release policy and reacquisition guide | Medium / NONE | Legal public bundle without prohibited raw data |

### 10.9 Phase 4 exit criteria

- SVI-001 and SVI-006 pass.
- Real and synthetic data are unambiguously separated.
- No shared fallback path remains.
- Raw/processed/model files have manifests and checksums.
- Split isolation is mechanically verified.
- Human spot check passes or the project is explicitly simulation-only.
- Training remains blocked until Reality Gate PASS.

---

## 11. Phase 5 — Research-question, metric, baseline, and statistical rehabilitation

### 11.1 Objective

Repair the evaluation specification before building the final experiment machinery. This is the phase where the project earns the right to rerun experiments.

### 11.2 Architecture amendment decision: what does a window mean?

The current Isolation Forest scores each feature vector independently and `InferenceOp` takes the maximum within a `WindowBatch`. The model does not consume temporal context or a window-level representation. Therefore the current narrative that a larger window gives the model richer context and improves model accuracy is not established by the implementation.

The Architect must choose one evidence-backed path:

#### Recommended conservative path A — Reframe around batching and decision aggregation

- Define window size as a systems/decision batching parameter.
- State that point scores are unchanged; window size changes batch service time, queue dynamics, aggregation, and alert coverage.
- Evaluate point-level and window-level decisions separately.
- Avoid claiming context-dependent model accuracy.
- Retain the pointwise Isolation Forest if this narrower contribution meets venue standards.

#### Higher-cost path B — Implement genuine window-context detection

- Define a window-level feature/model that mathematically depends on multiple points or temporal structure.
- Add fair context-aware baselines.
- Train and validate it without leakage.
- Re-run every experiment; legacy results no longer address the new model.

No contract may quietly mix these paths. If the venue requires a semantic adaptive-window detection contribution and path A is insufficient, that is a real Architecture Amendment, not a documentation tweak.

### 11.3 Mechanism validity

Shrinking W shortens one batch call, but scoring all incoming points can leave total per-point forest work similar, and smaller batches can increase fixed overhead and batch arrival rate. The causal mechanism therefore requires direct system identification, not only a Python sklearn timing regression.

Required experiments include:

- native C++ inference time versus W with warmup, randomized order, controlled affinity, and raw samples;
- total points/s and batches/s versus W;
- fixed per-batch and per-point cost decomposition;
- queue arrival/service rate and Little's-law-consistent accounting;
- fixed W at min/default/max;
- adaptive controller versus controller-disabled instrumentation-equivalent control;
- real occupancy versus shuffled/delayed/synthetic occupancy signals;
- queue-capacity sensitivity;
- EMA-alpha and hysteresis/factor ablations;
- deterministic artificial inference-delay fixture with a known causal response;
- event-loss and full-drain verification in every condition.

If smaller W does not improve sustainable service rate or the expected latency target under controlled conditions, the current core causal claim is falsified and must be reframed.

### 11.4 Metric rehabilitation

For every named metric, create a written mathematical definition, canonical implementation, independent verifier, and tiny known-answer fixture.

Critical corrections:

- Store per-point scores if PA%K truly depends on individual point threshold crossings. A window maximum alone is insufficient.
- Decide whether a positive max flags only `flagged_seq`, the whole window, or a specified alert range; never infer it differently across metrics.
- Use actual sequence keys rather than assuming row index equals sequence number.
- Bound-check and explicitly handle repeated loops or, preferably, make evaluation runs finite and single-pass.
- Select thresholds on validation data only and freeze them before test.
- Pin PRTS and its parameters if used. Missing PRTS must fail that metric, not choose a simplified fallback.
- Correct Range Precision/Recall alpha/cardinality semantics and stop calling a thresholded metric threshold-agnostic.
- Define LBA@T precisely for late true positives, false positives, missed detections, and alert ranges.
- Add random, constant-score, perfect, delayed-perfect, all-negative, all-positive, overlapping-range, boundary, and multi-loop known-answer cases.
- Preserve enough raw output to independently recompute every metric.

### 11.5 Exact latency design

Each point needs its own pipeline-entry timestamp if latency is reported for the maximum-scoring point. Options include a fixed timestamp array parallel to `WindowBatch::points`, or an equivalent structure whose cost is measured and disclosed. The result should record:

- source/pipeline-entry timestamp of the exact flagged point;
- inference start/end;
- sink receipt;
- queue wait if measurable;
- window formation delay as a separate metric where relevant;
- replay source timestamp separately from wall-clock pipeline timestamps;
- clock type/resolution and whether cross-thread timestamps share one monotonic domain.

Do not divide wall-clock pipeline latency by replay acceleration. Report observed system latency under the stated synthetic workload rate.

### 11.6 Baseline design

Final baselines must come from `venue_requirements.md`, not from convenience. The minimum categories are:

1. Operational baseline: fixed window and/or standard admission throttling/backpressure behavior.
2. Statistical non-learned baseline: a competently tuned data-driven window rule drawn from a real cited method.
3. Learned recent baseline: appropriate to the selected venue and task.
4. Proposed pressure-adaptive method.

Every baseline needs its own provenance, tuning budget, validation-only tuning, implementation fidelity check, and resource parity statement. A homemade “literature-style” rule without evidence of fidelity cannot be the only competitive baseline.

### 11.7 Statistical protocol

- Define the independent unit: dataset/day/symbol/session/injection seed, not merely process rerun.
- Use paired tests only when conditions share the same independent unit and pairing is declared.
- Report effect sizes compatible with the chosen test, confidence intervals, exact sample counts, missing/failed runs, and raw paired values.
- Pre-register primary and secondary outcomes.
- Correct for multiple comparisons or use a pre-registered hierarchical/composite rule.
- Do not interpret non-significance as equivalence. Use an equivalence/non-inferiority design with a declared margin if that is the claim.
- Separate data variability, model-seed variability, and systems/runtime variability.
- Randomize or block execution order to control thermal/load drift.
- Never run competing repetitions concurrently on the same constrained machine unless interference is itself the studied factor. Current Experiment 4's concurrent processes can confound latency.
- Treat failed runs as data with reasons; never silently exclude or overwrite them.
- Calculate power/sample requirements from the venue and meaningful effect, not the Factory's generic minimum alone.

### 11.8 Pre-registered hypotheses and stop rules

Illustrative hypotheses, to be finalized rather than copied blindly:

- H1: Under a specified overload trace, pressure adaptation reduces a pre-declared latency percentile/effect size relative to a fixed-window baseline without event loss.
- H2: The effect persists across the required independent units and queue capacities.
- H3: The method's accuracy/alert-quality cost remains within a pre-declared acceptable margin, or the paper is explicitly a trade-off/negative-result study.
- H4: The occupancy signal contributes beyond a schedule-only or shuffled-signal control.

Every hypothesis needs a falsifying threshold and action. If accuracy is materially worse than the allowed margin, the project may still publish an honest negative systems result if MAR-7 has identified that contribution, but it may not claim a superior detector.

### 11.9 Proposed Chunk 05 contracts

| Contract | Risk/tier | Result |
|---|---|---|
| C05-01 Window/model semantic architecture amendment | High / NONE | Path A or B frozen with claim boundaries |
| C05-02 Exact point-score and alert semantics | High / NONE | Machine-readable output schema and semantic tests |
| C05-03 Exact latency instrumentation | High / T-DESC | Known-delay tests and clock contract |
| C05-04 Canonical metric package | High / T-DESC | Known-answer corpus and independent verifier |
| C05-05 Baseline fidelity implementations | High / T-COMP | Venue-backed baseline reports and tuning parity |
| C05-06 Frozen statistical analysis plan | High / T-COMP/T-CAUSAL | Unit, tests, effects, corrections, missing-run rules |
| C05-07 Pre-registration and falsification criteria | High / T-CAUSAL | Frozen hypotheses and stop actions |
| C05-08 Native mechanism microbenchmark/causal fixture | High / T-CAUSAL | Direct evidence or architecture stop |

### 11.10 Phase 5 exit criteria

- The research question matches the implementation.
- Metric semantics pass independent known-answer tests.
- Threshold and split leakage are impossible by construction.
- Venue-required baselines exist and are fair.
- Statistical units and pairing are valid.
- Hypotheses, meaningful effects, and falsification actions are frozen before full runs.
- A native pilot supports proceeding; otherwise the documented Architecture Amendment/reframe is complete.

---

## 12. Phase 6 — Reproducible experiment and evidence infrastructure

### 12.1 Objective

Build one deterministic experiment pipeline that produces content-addressed evidence rather than overwriting `results/*.csv`.

### 12.2 Run identity

Each run receives an immutable ID derived from or accompanied by:

- Git commit/tree and dirty flag;
- Factory/project chunk/contract;
- dataset and split manifest checksums;
- model checksum and training manifest;
- canonical config checksum;
- executable checksum/build preset/compiler/version/flags;
- Python environment lock checksum;
- architecture/baseline name;
- all seeds;
- host CPU/OS/kernel, core/affinity policy, memory, thermal/power mode if available;
- start/end timestamps;
- exit code and failure reason;
- raw output checksums.

Runs write to a new directory and fail if it exists. No result command overwrites prior evidence.

### 12.3 Machine-readable configuration

Replace scattered constants with validated config files for:

- dataset/split IDs;
- architecture;
- window/controller parameters;
- queue sizes;
- replay mode/rate and finite event count;
- forest/model identity;
- threshold identity;
- warmup and measurement policy;
- metrics and latency bounds;
- seed/block/pair ID;
- output location.

The binary prints the resolved config as JSON and embeds its hash in each result. Defaults exist in one file and are tested against docs and key facts.

### 12.4 Pipeline stages

Use explicit, resumable, independently verifiable stages:

1. environment preflight;
2. acquire/locate raw data;
3. verify raw checksums/license/identity;
4. preprocess and produce transform manifest;
5. Reality Gate;
6. freeze splits;
7. train and validate model;
8. freeze threshold/config;
9. build measured executable;
10. run warmup;
11. run randomized/blocked measurements;
12. validate raw output schema/event accounting;
13. compute canonical metrics;
14. independently recompute core metrics;
15. render tables/figures from certified summaries;
16. archive and checksum the run.

Every stage checks the previous artifact identity. “File exists” is never enough.

### 12.5 Python environment

Turn analysis/preprocessing into a tested package. Pin Python and direct/transitive dependencies with a selected lock strategy. Include pandas, NumPy, SciPy, matplotlib, scikit-learn, PRTS if retained, schema validation, and test/lint tools. Add:

- `pytest` unit/semantic tests;
- formatting/lint/type checks;
- CLI entry points rather than cwd-dependent scripts;
- explicit random generators passed through functions;
- no broad swallowed exceptions;
- stable CSV/JSON schemas and versions;
- a minimal smoke dataset that is redistributable.

### 12.6 Performance protocol

- Use Release binaries with recorded flags and no accidental metrics logging unless that is part of the condition.
- Separate correctness tests from performance runs.
- Warm up explicitly and record discarded samples.
- Randomize/block configurations.
- Avoid concurrent experiment processes unless testing contention.
- Record machine load and failures.
- On fanless development hardware, record SoC thermal/power state per run (for example `powermetrics` or `pmset -g therm` on macOS) and flag any run showing throttling; treat sustained multi-minute or multi-block runs as throttling-suspect by default rather than assuming OS scheduling noise is the only source of timing variance. This is not a hypothetical: Experiment 1's own Window Oscillation Rate is already reported at mean 48.3, std 64.0, range 6-276 across the 30-run ensemble, a coefficient of variation over 100% that a sustained-load thermal event would also produce. See the Risk register (Section 19).
- Report distribution and confidence, not one favorable number.
- Validate counters and event accounting before accepting timing.
- Keep local native tuning out of portable release builds.
- Distinguish per-event, per-window, queue-wait, compute, formation, and end-to-end latency.

### 12.7 Independent recomputation

For every T-COMP/T-CAUSAL core result, implement a second analysis path that does not share the original script. It may use a straightforward reference implementation on the same frozen raw artifacts. Its source hash must differ, and `gatekeeper.py recompute` must compare declared values within pinned tolerance.

### 12.8 Proposed Chunk 06 contracts

- C06-01 config/schema and run-ID system;
- C06-02 finite single-pass replay runner;
- C06-03 event-accounting/output validator;
- C06-04 Python package and lock;
- C06-05 canonical staged reproduction CLI;
- C06-06 immutable artifact/archive tooling;
- C06-07 independent metric recomputation;
- C06-08 controlled performance preflight;
- C06-09 clean-container reproduction smoke.

### 12.9 Phase 6 exit criteria

- One command can execute a tiny end-to-end fixture from clean environment to archived report.
- Every stage records identities and refuses mismatches.
- No output is overwritten.
- Canonical and independent metrics agree.
- Failed/missing runs are visible.
- Clean-container smoke passes without private data.
- Licensed real-data flow blocks cleanly with exact Human action when data is absent.

---

## 13. Phase 7 — Pilot gates and final evidence production

### 13.1 Objective

Run the frozen protocol in increasing cost order, stop on invalidating evidence, and produce the only result set eligible for the manuscript.

### 13.2 Gate A — deterministic preflight

- Factory checks and frozen hashes pass.
- Clean build/install/tests/sanitizers pass.
- Data and model manifests match.
- Reality Gate remains PASS.
- Config, thresholds, hypotheses, and analysis plan are frozen.
- Output directories are new.
- Host/resource preconditions pass.
- A dry-run fixture exercises every stage.

### 13.3 Gate B — one-unit pilot

Run one independent unit for all architectures in randomized order. Verify:

- exact event reconciliation and no silent drops;
- exact point/timestamp joins;
- nonempty output and finite metrics;
- latency components have plausible units;
- controller signal is actually recorded and changes when expected;
- baseline implementations execute correctly;
- independent recomputation agrees;
- raw artifacts fit the planned storage budget.

Pilot results are diagnostic and excluded from final inference unless the pre-registration explicitly includes them.

### 13.4 Gate C — falsification pilot

Run the native mechanism controls and the minimum data/seed set needed to test whether the core hypothesis is already null, below meaningful effect, or scientifically misconceived. If a pre-registered stop condition fires, stop full execution. Record the negative result and apply the declared reframe/amendment.

### 13.5 Full run

Only after A-C pass:

- generate the randomized/block schedule before execution;
- run each independent unit and paired architecture set;
- never rerun a failed observation silently; preserve failed artifact/reason and apply the declared retry policy;
- monitor temperature/load without changing the frozen protocol;
- validate and archive each block before the next;
- keep the final test set sealed from exploratory plotting or tuning;
- run the canonical and independent analyses after raw data freeze;
- apply multiple-comparison correction and effect-size/CI computation exactly as planned;
- create structured JSON verdict artifacts for Gatekeeper evidence checks.

### 13.6 Required result packages

Each claim package contains:

- claim/hypothesis ID and tier;
- raw artifact manifest;
- sample/unit counts;
- exclusions/failures;
- point estimates and uncertainty;
- effect size and test details;
- pre-registered criterion and verdict;
- canonical command/output;
- independent recomputation command/output;
- code/data/model/config/environment hashes;
- limitations and proof boundary;
- supersession relation to any prior result.

### 13.7 Proposed Chunk 07 contracts

- C07-01 deterministic preflight report (T-DESC);
- C07-02 pilot event/metric validation (T-DESC);
- C07-03 causal/falsification pilot (T-CAUSAL);
- C07-04 final randomized execution (T-COMP/T-CAUSAL);
- C07-05 canonical statistical analysis (T-COMP);
- C07-06 independent recomputation and evidence checks (T-COMP/T-CAUSAL);
- C07-07 certified tables/figure-data generation (T-DESC);
- C07-08 cross-contract supersession of all legacy metrics.

### 13.8 Phase 7 exit criteria

- No stop condition is unresolved.
- All planned units are present or transparently accounted for.
- Raw evidence is frozen and archived.
- Canonical and independent results agree.
- Every verdict matches its JSON artifact and pre-registered criterion.
- Legacy results are explicitly superseded or retained only as historical unverified work.
- Chunk Review validates actual raw diffs/output, not only reports.

---

## 14. Phase 8 — Manuscript, documentation, and claim reconstruction

### 14.1 Objective

Write the paper and public documentation from the certified evidence map. Do not start from the legacy abstract and replace numbers one by one.

### 14.2 Claim-evidence registry

For each title/abstract/contribution/result claim, track:

- stable claim ID;
- exact approved wording;
- Scientific Claim Tier;
- contract and hypothesis IDs;
- evidence artifact and checksum;
- recomputation artifact;
- figure/table location;
- key-fact anchor;
- permitted generalization;
- limitations;
- superseded wording.

This can be a simple tracked project artifact rather than a new Factory-wide registry. It exists because this research project has already demonstrated cross-document numeric drift.

### 14.3 Manuscript reconstruction rules

- Title must survive the Title-Claim Audit. Remove “real-time,” “causal,” “robust,” “guaranteed,” “first,” or financial-detection language unless the required tests pass.
- Abstract numbers are generated or mechanically checked against certified JSON summaries.
- Dataset section states exact real/synthetic composition and redistribution limitations.
- Method describes wall-clock pipeline latency correctly and separates original market timestamps.
- Model/window semantics match code.
- Statistical section states unit, pairing, test method/version, alternative, tie handling, correction, effect sizes, confidence intervals, and exclusions.
- Results include negative/null findings without reframing.
- Limitations include single/multiple data units, synthetic injection, replay acceleration, hardware specificity, scheduler variability, baseline fidelity, and any same-session MAR limitation.
- Code/data availability points to real release artifacts and exact licensed-data steps.
- No figure is manually edited in a way that breaks traceability to data.

### 14.4 Citation audit

Verify every current reference and in-text key against primary sources. Specifically:

- resolve the remaining `AFMF (2024)`-style unmatched citation or remove it;
- verify the 2025/2026 adaptive-window/backpressure papers, titles, claims, dates, volumes, pages, and DOIs;
- verify the claimed novelty against a reproducible literature search;
- correctly cite Rigtorp, Vyukov, RED, Isolation Forest, PA%K, range metrics, and any baseline code/algorithms;
- check licenses/attribution for borrowed algorithm designs and dependencies;
- use the chosen venue's bibliography format.

No “resolved” label in `study.md` counts as citation verification.

### 14.5 Public documentation

Produce and verify:

- concise README with honest scope and quick start;
- architecture/design documentation;
- API documentation for stable surface;
- reproducibility guide with real-data and fixture modes;
- data licensing/acquisition guide;
- benchmark methodology and non-generalization warning;
- contribution/security/version/release policies;
- citation metadata;
- examples compiled and run in CI.

### 14.6 Proposed Chunk 08 contracts

- C08-01 claim-evidence map and key facts;
- C08-02 manuscript rewrite from certified artifacts;
- C08-03 figure/table generation and cross-check;
- C08-04 primary-source citation/novelty audit;
- C08-05 README/API/reproducibility docs;
- C08-06 independent hostile reviewer pass;
- C08-07 release-bound path/identity/key-fact scan.

### 14.7 Phase 8 exit criteria

- Every number in manuscript/README maps to one certified artifact.
- No placeholder/unmatched citation remains.
- No title adjective lacks a validating test.
- Claims use observed/generalizable/causal language appropriate to evidence.
- Documentation commands pass in clean CI.
- Independent hostile review has no unresolved submission blocker.
- `gatekeeper.py release-check` passes for manuscript, reproducibility guide, and supplement.

---

## 15. Phase 9 — Release candidate, certification, and publication package

### 15.1 Objective

Create a clean, reproducible, legally releasable candidate and certify exactly what was checked.

### 15.2 Release contents

1. Source tag and source archive.
2. Installable/buildable KLStream package.
3. Reproducibility bundle with locked configs, manifests, schemas, scripts, and permitted fixtures.
4. Certified result summaries and figure source data.
5. Manuscript and supplementary material.
6. External large-artifact archive record/checksums/DOI where applicable.
7. SBOM/dependency/license report if selected by release requirements.
8. Release notes and known limitations.

Licensed raw LOBSTER data must not be included unless the Human's documented license review explicitly permits it.

### 15.3 Release verification matrix

- fresh clone in a path with spaces and no prior caches;
- Linux GCC and Clang Release builds;
- macOS AppleClang Release build;
- Debug/unit/integration/semantic tests;
- ASan/UBSan and supported TSan job;
- install and external consumer;
- Docker build/test/runtime smoke;
- fixture reproduction from clean container;
- real-data path produces exact Human-action instructions when data absent;
- artifact checksum verification;
- secrets, absolute paths, hostnames, usernames, raw licensed data, and large-file scan;
- docs links/commands and citation metadata;
- version consistency;
- release tarball content allowlist;
- manuscript/key-fact/recompute/evidence/tier checks.

### 15.4 Factory certification sequence

For every relevant report:

1. run required verification commands;
2. run `verify-contract`;
3. run `lint-contract`;
4. run `recompute` for T-COMP/T-CAUSAL results;
5. run `evidence-check` on structured verdicts;
6. run `tier-check`;
7. run `stamp-report` and verify stamps;
8. run per-contract/chunk `check`;
9. complete Architect Chunk Review using raw evidence;
10. run `release-check` on every external artifact;
11. run `release-certify` with chunks, manuscript, key facts, and scripts;
12. read and report the certificate's proof boundaries.

The project is called “certified” only if `project/RELEASE_CERTIFICATION.md` says `CERTIFIED`. That certificate does not certify scientific truth, venue acceptance, security completeness, or categories that were not invoked.

### 15.5 Proposed Chunk 09 contracts

- C09-01 release allowlist and artifact assembly;
- C09-02 clean-clone/platform/package verification;
- C09-03 dependency/license/secrets/data-release audit;
- C09-04 reproduction bundle verification;
- C09-05 manuscript/supplement release check;
- C09-06 Factory release certification;
- C09-07 signed tag/archive/checksum/release notes;
- C09-08 final Human approval.

### 15.6 Phase 9 exit criteria

- All CI/release matrix jobs pass on the tagged commit.
- Outer and nested project repositories are clean.
- Every release file is allowlisted and checksummed.
- No prohibited data or identity leak exists.
- Reproducibility bundle works as documented.
- All contract statuses are `COMPLETE` with no unresolved `FLAGGED` or `BLOCKED` item.
- Release certificate is `CERTIFIED` and accurately described.
- Human approves publication/upload.

---

## 16. Phase 10 — Factory retrospective and long-term maintenance

After release, conduct the Factory retrospective using `project/evolution/telemetry.jsonl`, `decision_log.md`, technical debt, chunk reports, fix packages, and release evidence.

Questions specific to KLStream:

- Which legacy defects were caught by deterministic checks versus manual review?
- Did the source/project separation help or hinder a public C++ research repository?
- Which contracts needed repeated self-review and why?
- Which scientific checks prevented invalid reruns or claims?
- Did Gatekeeper's partial Allowed File/Reality Gate limitations require burdensome manual work worth automating?
- Which legacy documents were useful after knowledge synthesis?
- Which artifact-storage approach was sustainable?
- Which rules should be proposed to the Factory only after this completed project supplies evidence?
- Which technical debt remains acceptable for the next release versus mandatory now?

Do not modify the Factory based on lessons during active rehabilitation. Record candidate observations, finish the project, then propose evidence-backed Factory changes for Human approval.

---

## 17. Cross-cutting verification strategy

### 17.1 Test layers

| Layer | Purpose | KLStream examples |
|---|---|---|
| Compile contract | Detect missing/transitive includes and platform/API drift | Compile each public header; README examples; external install consumer |
| Unit | Local behavior | config validation, controller traces, token bucket fake clock, serialization parser |
| Semantic/known-answer | Named algorithm correctness | queue capacity/full occupancy, Isolation Forest path lengths, PA%K, Range-F1, Wilcoxon/effect size fixtures |
| Metamorphic | Relation/invariance | repeat seed determinism, batch isolation, sequence-offset invariance, identical config hash |
| Concurrency/adversarial | Tight races and lifecycle | forced SPSC/MPMC boundaries, stop under full queues, producer/consumer uniqueness, TSan |
| Integration | Multi-component contracts | source-window-inference-sink finite run with exact event/score/timestamp reconciliation |
| System/reproduction | Clean real workflow | fixture pipeline and licensed-data blocked/available paths |
| Performance | Measured properties after correctness | queue throughput, native inference scaling, controller overhead, latency under controlled load |
| Release | Public artifact | install, Docker, allowlist, docs, checksums, release scans |

### 17.2 Regression tests required from observed defects

At minimum, add regressions for:

- top-level CTest discovering zero tests;
- README/Docker/dev script nonexistent target names;
- advertised CMake options having no effect;
- source rate limiter recovering to zero due to unset original rate;
- full MPMC occupancy reporting zero;
- invalid queue capacity accepted when `NDEBUG` is set;
- cumulative counters becoming zero after MetricsReporter reset;
- percentile of one nonzero sample returning zero;
- repeated Runtime/Worker shutdown callbacks;
- stop dropping unreported queued events;
- adaptive occupancy output always zero;
- burst flag parsed but unused;
- WindowBatch overflow;
- corrupt/empty Isolation Forest model/data;
- same filename used for synthetic and real-derived replay;
- reproduction script accepting unmanifested existing data;
- sequence IDs beyond ground-truth bounds;
- threshold learned from test output;
- PA%K computed without point scores;
- optional PRTS absence changing the metric silently;
- paper defaults differing from executable config;
- latency claim using the wrong timestamp/direction;
- unmatched citation/key fact drift.

### 17.3 Evidence retention

For every verification run, retain:

- exact command;
- literal stdout/stderr;
- exit code;
- commit/config/data/model/environment identity;
- artifact hashes;
- test counts and names;
- duration;
- warnings and skipped checks;
- report stamp where required.

“All tests passed” without the named command and test count is not enough. “Gatekeeper PASS” must name the checks Gatekeeper actually ran.

---

## 18. Claim-to-evidence rehabilitation map

| Legacy/public claim | Current status | Claim Tier | Evidence required before reuse | Likely final wording if evidence remains narrow |
|---|---|---|---|---|
| Kafka-less single-node runtime | Plausible implementation fact | NONE | Clean install/example test; scope definition | “A single-node C++17 runtime with no external message broker.” |
| Bounded memory | Incomplete | NONE | Queue/window/sink allocation and capacity contracts; long-run memory test | State exactly which buffers are bounded and what is not. |
| Processes 100% of tuples | Unsupported | T-DESC | Exact event reconciliation through drain/stop/failure | “No loss observed under X” unless formally guaranteed. |
| LOBSTER AAPL evaluation | Contradicted by present artifact identity | N/A — SVI-001 | Real acquisition provenance, Reality Gate, legal record | Otherwise: “synthetic order-book simulation.” |
| Pressure-adaptive windowing | Implemented in some form | NONE | Signal recording, trace tests, architecture semantics | Describe the precise batching/decision actuator. |
| P95 19 ms | Legacy unverified | T-DESC | New frozen protocol, exact flagged timestamps, independent units | “Observed P95 was X under workload/config/hardware Y.” |
| Strict latency guarantee/bound | Unsupported | T-CAUSAL | Formal bound or stress envelope with explicit conditions and maximum accounting | Prefer “reduced observed P95” rather than “guaranteed.” |
| F1 trade-off | Legacy unverified | T-COMP | Correct metric semantics, leakage-free threshold, independent units | Report effect and uncertainty under exact task. |
| PA%20 compliance | Unsupported | T-DESC | Per-point scores and independent known-answer implementation | Use only after semantic tests. |
| Range-F1 corroborates | Unsupported | T-COMP | Pinned PRTS/reference, correct alpha/cardinality, independent recompute | Name exact metric variant. |
| Causal mechanism | Unsupported/at risk | T-CAUSAL | Native mechanism controls, ablations, queue/service accounting, T-CAUSAL gate | Possibly “consistent with the proposed mechanism.” |
| O(W) inference | Analytically plausible, empirical evidence mismatched | T-CAUSAL | Native C++ timing and cost decomposition | “Native batch time scaled approximately linearly over W=... on hardware X.” |
| Sub-22 ns controller overhead | Legacy unverified | T-DESC | Dedicated native benchmark with overhead subtraction/distribution | “Median/mean overhead observed under benchmark X.” |
| First/novel method | Unverified | N/A — citation audit | Systematic primary-source literature review and venue review | Use “we propose” unless priority is defensible. |
| Publication-ready | False today | N/A — release certification | All phases and release certification | State only after tagged certified release. |

Tiers follow Section 6.5’s own rule: a reported metric is at least T-DESC; a comparison is T-COMP; a robustness/causality claim is T-CAUSAL. Rows marked `N/A` sit outside that scale entirely — they are gated by SVI-001/Reality Gate, the citation/novelty audit (Section 14.4), or release certification (Section 15), not by a Scientific Claim Tier, and conflating the two would blur which mechanism actually catches a violation.

---

## 19. Risk register

| Risk | Impact | Mitigation/decision gate |
|---|---|---|
| Real LOBSTER data unavailable or non-redistributable | Core manuscript scope changes | Decide in Phase 1/4; support legal reacquisition; reframe as simulation if necessary. |
| Current scientific premise does not match pointwise model | Major architecture/paper change | Phase 5 path A/B amendment before experiments. |
| Core effect is null or accuracy cost exceeds meaningful limit | Headline claim fails | Pre-register negative-result contribution and stop/reframe action. |
| Concurrency fixes materially change performance | Legacy numbers invalid | Expected; correctness precedes new measurement. |
| Factory structure makes public repo awkward | Adoption friction | Keep clean public root metadata and implementation boundary; review at Chunk 01. |
| Large artifact archive is lost or too expensive | Evidence loss | Content-addressed archive with duplicate manifest/checksum and retention policy. |
| Hardware-specific results do not generalize | Reviewer concern | Multi-platform correctness; cautious performance scope; add independent hardware if venue requires. |
| Development hardware is a fanless M3 MacBook Air (16GB); sustained runs may thermal-throttle mid-measurement | Latency/throughput numbers reflect thermal state, not the mechanism under test — a different failure than the row above, since it corrupts a single machine's own results rather than limiting generalization to other machines | Log SoC thermal/power state per run (Section 12.6); insert cool-down pauses between blocked repetitions in Phase 6/7; treat Experiment 1’s existing Window Oscillation Rate variance (std 64.0 on mean 48.3) as throttling-suspect until ruled out; move Phase 7 full-run performance measurement to actively-cooled hardware (CI runner, desktop, or cloud instance) if local throttling cannot be controlled. |
| Optional Python dependencies change metrics | Irreproducible analysis | Locked environment; fail closed; reference verifier. |
| Dirty legacy WIP is accidentally overwritten | Irrecoverable user work | Preservation branch/tag/patch before bootstrap or moves. |
| History cleanup is mistaken for rehabilitation | Lost provenance | No history rewrite; separate clean release artifact if desired. |
| Factory tool is over-trusted | False assurance | Quote implemented checks; manual Allowed File, Reality Gate, MAR, and raw review. |
| Publication scope grows without bound | Never ships | Freeze project_description non-goals and venue requirements; use technical debt for nonblocking future work. |

---

## 20. Human decision register

These decisions are required, but none should be guessed during implementation:

| Decision | Needed by | Default recommendation |
|---|---|---|
| Target venue | Founding artifacts/MAR | Select one concrete systems/streaming/ML venue before scientific Chunk 01 approval. |
| Final research framing | Phase 1/5 | Preserve the systems trade-off contribution; do not promise detector superiority. |
| Real versus simulation evaluation | Phase 1/4 | Acquire and prove real-derived base data if legally/practically possible; otherwise explicitly reframe. |
| Licensed data redistribution | Phase 4/release | Publish manifests/acquisition instructions and tiny synthetic fixtures unless written terms clearly allow more. |
| Public project license | Phase 2 | Human chooses after dependency/data/IP audit; do not rely on README's current MIT sentence alone. |
| Header-only versus compiled core | Phase 2 | Choose the smallest coherent implementation; remove the unused alternative. |
| Stable API/version target | Phase 2/release | Do not claim 1.0 until API/lifecycle contracts and install tests are stable. |
| Independent MAR reviewer | Phase 1 | Recommended for publication gates 4-7; disclose if only self-adversarial review is used. |
| Additional datasets/hardware | Phase 4/venue requirements | Use enough independent units to support the selected venue and claim; one replay day is likely insufficient for broad claims. |
| Public artifact host | Phase 6/9 | Use a durable content-addressed research archive with checksums/DOI when appropriate. |

---

## 21. Milestone dependency order

```text
Phase 1: preserve + factory + truth + clean structure
    |
    +--> Phase 2: coherent build/package/repository contract
    |        |
    |        +--> Phase 3: runtime/model correctness -------------+
    |                                                              |
    +--> Phase 4: authentic data + splits + Reality Gate ---------+
                         |
                         +--> Phase 5: valid research/metrics/baselines/statistics
                                      |
                                      +--> Phase 6: reproducible experiment infrastructure
                                                   |
                                                   +--> Phase 7: pilots + final evidence
                                                                |
                                                                +--> Phase 8: manuscript/docs
                                                                             |
                                                                             +--> Phase 9: release/certification
                                                                                          |
                                                                                          +--> Phase 10: retrospective
```

Phase 5 depends on both Phase 3 and Phase 4, not on Phase 4 alone. Phase 4 establishes that the data is authentic; Phase 3 establishes that runtime timing and event-accounting evidence can be trusted at all — Section 9.8’s own exit criteria quarantine every pre-Phase-3 performance result, and Section 11.3’s native-timing and queue-accounting work is Phase 5 content that depends directly on Phase 3’s queue and metrics contracts. An earlier version of this diagram drew only the Phase 4 edge, which would have let Phase 5’s timing-sensitive contracts (C05-08 in particular) start on Phase 4 completion alone.

Some engineering work in Phases 2-3 can proceed while a Human obtains licensed data, but model training, final metric design against observed distributions, and headline experiments remain blocked on Phase 4 Reality Gate. The parts of Phase 5 that do not depend on timing evidence — most notably the window/model semantic architecture decision itself (Section 11.2) — can be drafted once Phase 4 closes even if Phase 3 is still open; everything downstream of Section 11.3’s mechanism-validity work cannot. Manuscript prose may be outlined earlier, but result/claim wording remains blocked on Phase 7.

---

## 22. Final rehabilitation Definition of Done

### Repository and Factory

- [ ] Legacy HEAD, dirty WIP, data/results, and migration mapping are recoverable.
- [ ] Factory v2.2.0 provenance/self-check pass is recorded.
- [ ] `project/` nested history is current and outer Factory paths are ignored.
- [ ] Every file has one responsibility and owner.
- [ ] No tracked generated/cache/host-specific artifact remains without explicit justification.
- [ ] No broad ignore rule hides legitimate source/evidence.
- [ ] All chunks received Architect review of raw Medium/High artifacts.

### Software

- [ ] Fresh configure/build/test/install succeeds on supported platforms.
- [ ] Root CTest executes a nonzero expected test set.
- [ ] Public headers compile standalone.
- [ ] Queue/runtime/lifecycle/event-accounting contracts are proven by adversarial tests.
- [ ] Sanitizer suite is clean on the release commit.
- [ ] Metrics, timestamps, controllers, model, and serialization pass semantic tests.
- [ ] Scripts, Docker, CI, README, CMake, targets, options, and version agree.
- [ ] License, citation, contribution, security, and changelog artifacts exist.

### Data and science

- [ ] Data identities, provenance, licenses, checksums, transforms, and splits are frozen.
- [ ] Real/synthetic/fixture paths cannot collide.
- [ ] Reality Gate and Human authenticity spot check pass, or simulation scope is explicit.
- [ ] No train/validation/test leakage exists.
- [ ] Window/model semantics match the research claim.
- [ ] Baselines satisfy venue requirements and are fair.
- [ ] Metrics pass known-answer and independent recomputation tests.
- [ ] Statistical unit, pairing, tests, effects, CIs, correction, exclusions, and stop rules are correct.
- [ ] Final runs follow the frozen schedule and preserve all failures.
- [ ] Every legacy metric has an explicit supersession status.

### Publication and release

- [ ] Every title/abstract/table/figure claim maps to certified evidence.
- [ ] No unsupported guarantee, causal, real-data, novelty, or generalization wording remains.
- [ ] Every reference and DOI is verified; no placeholder/unmatched citation remains.
- [ ] Reproducibility works from a clean environment in fixture mode and gives exact real-data actions.
- [ ] Release artifacts contain no secret, local identity, prohibited data, or unallowlisted large file.
- [ ] Release checks, evidence checks, tier checks, recomputations, and stamps pass.
- [ ] `project/RELEASE_CERTIFICATION.md` says `CERTIFIED` and its proof boundaries are reported.
- [ ] Human approves the tagged release and publication package.

---

## 23. Immediate next action after this plan is approved

Do not begin by editing `.gitignore` or moving directories.

Begin Phase 1 with the preservation contract:

1. capture and preserve the current dirty worktree and artifact identities;
2. create the rehabilitation branch and legacy baseline recovery point;
3. archive/checksum the current `data/` and `results/` as `legacy-unverified`;
4. bootstrap and verify Software Factory v2.2.0;
5. write truthful founding artifacts and run MAR;
6. generate formal Chunk 01 artifacts from the provisional contract list;
7. only then execute the migration and ignore-policy contracts.

That order is what turns KLStream from an unfinished pre-Factory project into a project that genuinely behaves as though the Factory governs it: not because the history was cosmetically hidden, but because from the rehabilitation boundary onward every decision, file, claim, test, and release has an owner, a contract, evidence, and an independently reviewed completion gate.