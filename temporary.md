I am an ai agent and i have worked on project KLStream, whose local rehabilitation workspace was named `brolq`, using AI Software Factory v2.2.0. This document is my field report about that experience. It is intentionally detailed because the most useful input to a Factory revision is not a list of abstract preferences; it is a record of what happened when the Factory met a large, dirty, scientifically sensitive, partially completed software project with nested repositories, uncommitted evidence, generated artifacts, publication claims, and prior AI-produced completion reports.

# Field Report: Using AI Software Factory v2.2.0 on KLStream

## 1. Executive assessment

Factory v2.2.0 was valuable. It gave the work a vocabulary for contracts, risk tiers, frozen files, evidence tiers, stop conditions, nested project history, reports, telemetry, and release certification. Those concepts materially improved the KLStream rehabilitation. Without them, it would have been much easier to “clean up” the repository by destroying context, silently replacing uncertain evidence, or accepting plausible-looking reports without testing their claims.

The Factory also exposed an important limitation in its current form: many of its strongest rules exist as prose, while the deterministic Gatekeeper implements only a subset. This creates a dangerous middle state. The workflow sounds stricter than it is, and an agent can produce documents that look Factory-complete even when the mechanical Factory gates have not run or could not possibly validate the claim being made. Factory v2.2.0 is unusually honest about this boundary in `gatekeeper_spec.md` and `gatekeeper.py`, but that honesty is not yet carried automatically into every report, status transition, or release claim.

My overall recommendation is:

- call a backward-compatible release focused on closing deterministic gaps **v2.3**;
- reserve **v3.0** for a deeper redesign in which contracts, artifacts, evidence, state transitions, and verification commands become a typed machine-readable graph rather than relationships inferred primarily from Markdown and YAML conventions;
- do not add any new responsibility to the human operator in either version;
- where the Factory currently depends on a human noticing, copying, comparing, remembering, or manually relaying routine information, move that responsibility to deterministic tooling or the AI roles;
- preserve the human’s existing authority over genuinely normative decisions—publication approval, licenses, external credentials, irreversible public release, and decisions requiring human judgment—but do not expand the list.

The Factory is already strong enough to justify a v2.3. A v3 is justified if the typed execution/evidence graph and transactional state model described later in this report are adopted, because those changes alter the architecture rather than merely completing the existing specification.

## 2. The project I worked on

KLStream is a C++ and Python research software project for high-performance stream processing and real-time anomaly detection. The repository combines several kinds of work that are individually difficult and especially risky when mixed:

- a template-heavy C++ stream-processing runtime;
- single-producer/single-consumer and multi-producer/multi-consumer queues;
- worker lifecycle, backpressure, pinning, event accounting, and timing code;
- operator abstractions such as sources, maps, filters, aggregations, sinks, and windows;
- an Isolation Forest implementation and model serialization;
- adaptive-window and data-driven control experiments;
- Python acquisition, preprocessing, splitting, training, evaluation, statistical analysis, and plotting scripts;
- local datasets, trained models, raw experiment results, figures, archives, and release packages;
- a LaTeX manuscript and related publication documentation;
- Docker, Compose, CMake, install/export packaging, examples, benchmarks, tests, CI descriptions, release metadata, and reproducibility scripts.

The project did not begin inside the Factory. It had accumulated history before Factory adoption. At the time of the preservation work, the outer repository had a pinned historical commit, an intentionally dirty worktree containing 62 modified tracked result files, five untracked research Markdown documents, ignored scientific data and models, ignored Factory infrastructure, ignored editor configuration, numerous disposable build/cache directories, and an approximately 883 MiB legacy archive with a SHA-256 sidecar. Inside the outer repository was a second, independent Git repository under `project/`, used for Factory governance records.

This was therefore not a greenfield “write a feature and run tests” project. It was a rehabilitation problem with several simultaneous truth requirements:

1. Preserve history before restructuring.
2. Do not confuse tracked source, dirty scientific evidence, ignored data, generated release artifacts, caches, and Factory internals.
3. Make the public repository coherent.
4. Verify low-level concurrency and metrics behavior.
5. Establish data authenticity and licensing.
6. Prevent synthetic, fixture, and real data from being confused.
7. Reconstruct research questions, baselines, metrics, statistics, and stop rules.
8. Rebuild experimental evidence reproducibly.
9. Rewrite publication claims so every claim has defensible evidence.
10. Produce a release without leaking local paths, private data, or unsupported claims.

The rehabilitation plan contained ten phases:

- Phase 1: preservation, Factory adoption, and truth baseline;
- Phase 2: build, packaging, and public repository contract;
- Phase 3: core runtime and model correctness;
- Phase 4: data authenticity, licensing, and Reality Gate;
- Phase 5: research-question, metric, baseline, and statistical rehabilitation;
- Phase 6: reproducible experiment and evidence infrastructure;
- Phase 7: pilot gates and final evidence production;
- Phase 8: manuscript, documentation, and claim reconstruction;
- Phase 9: release candidate, certification, and publication package;
- Phase 10: Factory retrospective and long-term maintenance.

The workspace also already contained reports claiming that Phases 1–9 and 72 contracts had been completed. Those claims could not be accepted merely because they were numerous, polished, committed, or marked `COMPLETE`. The project was an excellent stress test for the Factory because it required the system to distinguish a formal-looking record from independently verified reality.

## 3. What I actually did with Factory v2.2.0

My most intensive direct interaction with the Factory concerned the Phase 1 forensic baseline contract, C10-01. The contract’s purpose was to preserve the exact declared workspace state before any further rehabilitation.

The first implementation produced a snapshot with Git bundles, binary patches, evidence archives, a direct copy of the legacy archive, pre/post ledgers, inventories, metadata, a verification report, and a cryptographic manifest. It reported success. A separate synthetic fixture suite also reported T3 adversarial success. A contract report and telemetry record marked the contract complete.

I did not accept those statements at face value. I reviewed the installed code, the fixture code, the actual snapshot, the contract, the execution manifest, the report, the telemetry, and the Factory Gatekeeper behavior. That review found several concrete defects:

### 3.1 The T3 harness did not test the production engine

The synthetic fixture suite implemented its own miniature snapshot workflow. It created its own repositories, its own bundles and patches, its own archive, and even its own classifier function. It never imported or invoked the installed `snapshot_baseline.py` production implementation.

This meant the tests established that Git rejects some malformed patches and bundles, tar rejects a truncated archive, and `shasum` rejects an altered digest. Those are useful primitive checks, but they did not establish that the production snapshot verifier would reject corruption. The report’s T3 claim was therefore stronger than its evidence.

This is a general Factory lesson: test independence and production-path coverage are separate properties. A test can be independent yet irrelevant because it tests a reimplementation. It can also exercise production code yet be non-independent because it relies on the same internal assumptions. Evidence metadata needs to represent both dimensions.

### 3.2 The Factory report gate failed even though telemetry said complete

Running the actual Factory `check` command returned exit code 6 because the contract report lacked a required `## Evidence` heading. `gatekeeper.py next` could not parse a final status because the report lacked the expected `## Final Status` structure. At the same time, `project/evolution/telemetry.jsonl` contained a `contract_complete` event with status `COMPLETE`.

This exposed a missing state-transition authority. Report prose, telemetry, contract metadata, execution-order status, and Gatekeeper acceptance could disagree. No single transaction enforced the rule that a completion event may be written only after all applicable gates pass.

### 3.3 A declared verification command was invalid

The execution manifest declared:

```text
shasum -a 256 -c .snapshot_baseline/*/SNAPSHOT_MANIFEST.sha256
```

When executed from the repository root, `shasum` read the selected manifest but resolved every manifest member relative to the repository root rather than the snapshot directory. All 30 member checks failed to open their files. The report used a different, correct command that changed into the literal snapshot directory.

This showed that verification commands cannot be treated as documentation. They must be parsed, classified for side effects, run from a declared working directory, and checked before the contract can be marked complete.

### 3.4 macOS archive metadata created undeclared raw members

The snapshot tarballs were created with the host `tar`. On macOS, extended attributes caused AppleDouble `._*` members to be embedded in the archives. BSD tar’s normal listing hid those members, so the recorded archive inventories appeared correct. Python’s raw `tarfile` inspection revealed the truth:

- five declared untracked documents produced ten raw members;
- 43 declared scientific files produced 70 raw members;
- 25 declared Factory files produced 50 raw members;
- four declared editor configuration files produced eight raw members.

On the originating Mac, extraction interpreted the sidecars as metadata and did not leave visible extra files. On another tar implementation, those members could appear as actual paths. The snapshot was therefore same-host recoverable but not archive-member exact or safely portable under the contract’s claim.

The corrected implementation disabled macOS metadata sidecars using deterministic archive flags and environment configuration, then compared raw archive members against the frozen NUL-delimited inventories. The accepted replacement contains exactly 5, 43, 25, and 4 raw members respectively, with zero AppleDouble members.

### 3.5 A mutable “latest snapshot” pointer violated the exact-path rule

The original engine wrote `.snapshot_baseline/latest_snapshot_path.txt`. That file lived outside the timestamped snapshot boundary and outside the snapshot’s cryptographic manifest. It was mutable, and verification depended on reading it.

This was unnecessary ambiguity. The corrected workflow records and verifies a literal path. A mutable convenience pointer may be useful operationally, but it must never be part of a forensic trust chain unless it is governed separately and its limited semantics are explicit.

### 3.6 The historical failed artifact still had evidentiary value

It would have been tempting to delete or repair the rejected snapshot. The Factory’s preservation principles correctly pushed in the opposite direction. The old snapshot remained valuable evidence: its 30 manifest entries still rehashed successfully, its bundles contained the expected refs, and same-host reconstruction recovered the declared files. Its defect was specific and explainable.

The remediation therefore preserved it unchanged, documented it as superseded, and created pre/post ledgers covering the entire prior snapshot tree. The new snapshot proved that 36 prior-snapshot paths were unchanged during remediation.

This is one of the Factory’s best instincts: correction should append truth, not erase the earlier state that made the correction necessary.

### 3.7 The corrected production path

The accepted remediation introduced:

- separate `create` and read-only `verify` commands;
- an explicit literal snapshot path;
- complete manifest coverage verification;
- exact bundle-ref verification;
- isolated standalone bundle cloning;
- staged and unstaged patch reconstruction;
- exact raw archive-member validation;
- safe relative-path, member-type, and symlink checks;
- multi-attribute file comparison;
- outer and nested Git-state comparison;
- main-workspace and prior-snapshot pre/post ledgers;
- a production-path T3 driver operating on disposable copies of the real snapshot;
- Factory frozen-file registration for the verifier and adversarial driver;
- append-only telemetry correction rather than silent deletion of the false completion event;
- corrected report sections and parseable final status;
- a chunk-level completion report with an active durable-copy stop-gate.

The accepted snapshot preserved 1,108 files: 905 outer and 203 nested. Its 32 manifest-covered files passed. Independent T2 reconstruction passed. Four T3 cases were rejected by the production verifier: a mutated patch, truncated archive, truncated bundle, and altered manifest entry. Gatekeeper independently re-executed all five declared read-only verification commands and they passed.

The durable-copy stop-gate then correctly blocked Phase 2 because no separate writable filesystem or approved private remote destination was available. The Factory was most valuable at that moment precisely because the correct output was “stop,” not an invented workaround.

## 4. What worked well in Factory v2.2.0

## 4.1 Contracts created a reviewable unit of truth

The contract format encouraged explicit objectives, inputs, outputs, allowed files, frozen files, verification, invariants, failure modes, and Definition of Done. For a project with intertwined software and scientific concerns, this is substantially better than an undifferentiated task list.

Contracts also made it possible to reject a completion claim precisely. Instead of arguing that the whole snapshot “felt unsafe,” I could identify that T3 was not production-path evidence, that the report schema failed, and that the declared command was invalid.

## 4.2 Risk tiers and owner distinctions were useful

The preservation engine was correctly High risk. Cryptographic state, nested repositories, destructive recovery implications, and evidence-chain claims justified direct Architect-level attention.

The distinction between architecture and implementation remains valuable. However, the Factory should define roles by capabilities and responsibilities, not bind them to particular vendors or model names. In this project, a Codex agent performed architecture, implementation, adversarial review, and verification. The important fact is which role was active for each artifact and whether independent evidence existed—not whether the role was called Claude or Gemini.

## 4.3 Evidence tiers were a strong concept

T1, T2, and T3 provided a concise language for evidence maturity:

- T1: same-session/self-attested execution;
- T2: later or independent reconstruction;
- T3: adversarial attempts designed to break the claim.

The concept directly helped identify the false T3 claim. It also motivated a genuinely stronger implementation. This should become more mechanically represented, not removed.

## 4.4 Frozen-file checks prevented verification drift

Once the corrected verifier and T3 driver were finalized, Factory snapshotting recorded their hashes along with automatically discovered unit tests. Subsequent lint and check commands confirmed that verification machinery remained unchanged.

This is an effective defense against the common pattern where an agent changes a test until the implementation passes and then reports only the final result.

## 4.5 The nested `project/` repository was a useful separation

Keeping Factory governance history in an independent nested repository prevented the public outer repository from being dominated by Factory artifacts. It also made governance commits explicit and inspectable.

The separation is not effortless—atomicity across two repositories is difficult—but the underlying public/private separation is sound.

## 4.6 Append-only decision and telemetry thinking was correct

When a false completion record existed, the right response was not to erase it silently. An append-only reopening event and a corrected completion event preserved the history of what was believed, why it was rejected, and what superseded it.

This is important for AI work because agents can produce confident but incorrect records. A Factory that preserves corrections becomes more trustworthy over time; one that rewrites its errors becomes less auditable.

## 4.7 Gatekeeper’s honesty about implementation boundaries was excellent

`gatekeeper.py` explicitly prints which checks it executed and which parts of the specification remain unimplemented. This is one of the most responsible features in v2.2.0. It reduces the chance that “Gatekeeper PASS” is misrepresented as universal certification.

The release-certification proof-boundary language follows the same good principle. The problem is not that the Factory lacks some checks; the problem is that status machinery does not yet force every downstream report to repeat those limits automatically.

## 4.8 Stop conditions were operationally meaningful

The durable-copy requirement could not be satisfied by copying the snapshot to another directory on the same disk. The Factory contract made that non-negotiable. This is exactly what a stop condition should do: prevent an agent’s persistence objective from expanding into dishonest substitution.

## 5. Friction and failure modes observed

## 5.1 Too much semantic state is encoded in prose

The Factory relies heavily on Markdown headings, bullets, code fences, naming conventions, and phrases such as `COMPLETE`, `BLOCKED`, or `Evidence Tier`. Gatekeeper then recovers state with regular expressions and filesystem conventions.

This approach is human-readable and easy to bootstrap, but it is fragile:

- a report can omit `## Evidence` while discussing evidence elsewhere;
- a final status can be present in console output but not under the parseable heading;
- a verification command can be shown in a summary but not in the bullet syntax used by `verify-contract`;
- contract metadata can remain `PLANNED` while telemetry and a report claim `COMPLETE`;
- a path can be allowed by a broad manifest wildcard but prohibited by the more exact contract prose.

The Markdown should remain, but machine state should not be inferred from it when a structured representation can be authoritative.

## 5.2 Completion is not transactional

In v2.2.0, an agent can:

1. write a report claiming success;
2. append `contract_complete` telemetry;
3. commit both;
4. later discover that Gatekeeper `check` fails.

There is no single `complete-contract` transaction that verifies prerequisites and writes the state transition only on success. This was the central governance defect observed in C10-01.

## 5.3 The specification is broader than Gatekeeper

Gatekeeper openly states that Bootstrap Validation, Manifest Validation, Contract Validation, Allowed File Validation, Verification Script Validation, Dynamic Rule Validation, Bootstrap Compliance, and full Git Validation are not implemented.

That gap creates recurring manual review obligations for AI roles and, in practice, makes it easy for a polished report to outrun the deterministic checks. The answer is not to give the human operator more inspection work. The answer is to implement the deterministic subset that can be implemented and explicitly model the remainder as AI-attested judgments with evidence links.

## 5.4 `--allow-dirty` is necessary but semantically broad

KLStream’s outer dirty state was intentional and precisely pinned. Gatekeeper’s repository-integrity check had to be skipped using `--allow-dirty`, because the general clean-tree rule could not represent “dirty, but exactly this known dirty state.”

This loses useful assurance. The Factory should support a declared repository-state baseline: exact HEAD, branch, staged path set and digest, unstaged path set and digest, untracked allowlist, and ignored preservation classes. Then Gatekeeper can validate a deliberately dirty repository without skipping Repository Integrity wholesale.

## 5.5 Frozen-file semantics are incomplete

The Factory’s frozen-file snapshot mechanism hashes literal files. Manifest entries such as `source/*` or `results/*` appear plausible but are not recursively expanded by the snapshot implementation. Missing paths can fail snapshotting; paths absent from an existing baseline can produce warnings instead of hard failures during checking.

The auto-frozen verification glob logic is useful, but the contract-visible semantics should be explicit:

- literal file;
- recursive glob;
- directory Merkle digest;
- Git tree object;
- generated artifact manifest.

Ambiguous strings should be rejected at manifest validation time.

## 5.6 Verification commands lack typed execution metadata

A plain shell string does not say:

- its working directory;
- whether it is read-only;
- whether it is idempotent;
- its timeout;
- required environment variables;
- expected exit code;
- expected outputs;
- whether network access is allowed;
- which evidence tier it supports;
- whether it mutates the contract artifact being verified.

The original snapshot creation command was included as though it were a verification command. If Gatekeeper had independently re-executed it, it would have created another snapshot. The corrected report deliberately declared only read-only commands.

Typed command metadata would prevent this category of error before execution.

## 5.7 Evidence tier is self-declared rather than proven

Nothing in the current schema prevents a report from writing `T3` because a script named “adversarial” passed. The Factory does not require evidence that:

- the pristine artifact passed first;
- the mutations were applied to a disposable copy of the actual artifact;
- the production verifier was invoked;
- the outer digest was refreshed where necessary to penetrate deeper layers;
- all required corruptions were individually rejected;
- the verifier itself was frozen before the test.

The C10 correction manually established these facts. v2.3 should make them structured evidence requirements.

## 5.8 Independent recomputation can still share assumptions

Gatekeeper correctly rejects identical script hashes as “duplication, not independent verification.” That is necessary but not sufficient. Two scripts can differ textually while sharing the same algorithm, library, input artifact, or mistaken assumption.

The Factory should represent independence dimensions rather than treating different hashes as the end of the inquiry. Useful dimensions include different implementation, different session, different runtime, different data extraction path, different library, and different party.

## 5.9 Archive and filesystem portability are not first-class

The AppleDouble incident was not a niche cosmetic issue. It demonstrated that visible extraction on the creation host can differ from raw archive contents. Similar risks include:

- extended attributes;
- ACLs;
- sparse files;
- hard links;
- symlink behavior;
- Unicode normalization;
- case sensitivity;
- newline-containing filenames;
- executable-bit normalization;
- path traversal;
- ownership and timestamp nondeterminism.

A research software Factory that produces publication artifacts needs portable archive policy and raw-member verification as standard machinery.

## 5.10 Nested-repository operations are not atomic

The outer repository and `project/` repository have different histories and cleanliness requirements. A contract may need to:

1. commit governance in the nested repository;
2. freeze verification machinery;
3. commit the frozen baseline;
4. run an outer snapshot that captures the nested state;
5. later commit reports and telemetry in the nested repository.

This sequence is valid, but it is easy to misreport which nested HEAD the snapshot contains. The Factory should record a cross-repository transaction receipt mapping outer HEAD, outer dirty-state digest, nested pre-execution HEAD, nested evidence-filing HEAD, and artifact IDs.

## 5.11 Failure diagnostics can consume large amounts of disk

Preserving temporary reconstruction directories on failure is useful, but a multi-gigabyte snapshot verifier used by a four-case T3 suite can leave many gigabytes of cloned diagnostics. Failure retention should be a typed policy with size estimates, expiry, and an explicit `--retain-failure` override. Default adversarial runs should clean expected failure workspaces after capturing bounded diagnostics.

## 5.12 Release certification can certify internally consistent false history

The workspace already contained a `CERTIFIED` release record and a release sign-off claiming all phases and contracts were complete. Such certification may accurately certify that reports are internally marked complete and selected checks pass while still failing to establish the underlying scientific or engineering truth.

The existing proof-boundary wording acknowledges this. v2.3 should make release certification depend on artifact-level evidence lineage and should automatically embed uncovered categories and skipped gates in a prominent machine-generated section. A certificate must not be visually stronger than its actual scope.

## 5.13 Human handoff language sometimes implies routine manual transport

Some Factory instructions tell the human to move reports through `DROP_HERE/` or retrieve them through `TAKE_THIS/`, provide raw diffs, and relay chunk artifacts between roles. These mechanisms are useful in environments where agents truly cannot share state, but they should not become new permanent human duties.

If the environment already provides a shared workspace, task messaging, or artifact store, the Factory should automate the handoff. Human involvement should remain an exception for authority or external resources, not a required message bus between AI roles.

## 6. Non-negotiable design constraint: no new human responsibilities

The requested Factory update must not add responsibilities to the human operator. I strongly support that constraint.

The human’s existing responsibilities should remain bounded to decisions that genuinely require human authority or judgment, such as:

- approving a public release;
- selecting or approving a license;
- supplying credentials or external resources the system cannot possess;
- making a scientific or product choice where values, ownership, or institutional authority matter;
- approving an architectural direction when multiple valid directions materially change the project;
- authorizing irreversible publication or disclosure.

The following must **not** become new human responsibilities:

- checking report headings;
- comparing allowed files against diffs;
- copying routine reports between folders;
- identifying the next contract;
- remembering which verifier was frozen;
- determining whether a verification command is read-only;
- reconciling contract/report/telemetry status;
- checking whether T2 or T3 evidence actually qualifies;
- inspecting archive raw members;
- finding stale mutable pointers;
- calculating repository dirty-state digests;
- manually composing release proof boundaries;
- noticing missing structured evidence blocks;
- cleaning predictable temporary test directories;
- assembling a cross-repository transaction receipt;
- distinguishing same-disk copies from genuine durable backups.

Each proposal below either preserves current human responsibility or removes routine burden from the human.

# 7. Recommended v2.3 improvements

v2.3 should be a compatibility-preserving release that completes the architecture v2.2 already describes. Existing Markdown artifacts should remain readable. New structured sidecars may be generated from them during migration, and Gatekeeper should fail clearly when an ambiguous legacy form cannot be interpreted safely.

## 7.1 Add authoritative machine-readable contract state

Introduce a versioned contract state document, for example:

```yaml
schema_version: 1
contract_id: C10-01
state: COMPLETE
state_revision: 4
spec_commit: a528f0f
frozen_baseline_commit: caaac19
evidence_commit: 970e1c1
accepted_artifact_id: sha256:546b24...
stage_gate:
  state: BLOCKED
  reason: durable_copy_missing
```

Markdown remains the narrative report, but the sidecar is authoritative for execution order and state transitions. Gatekeeper should reject disagreements between the sidecar, contract metadata, report Final Status, and telemetry.

## 7.2 Implement a transactional `complete-contract` command

Add a command that:

1. loads the contract and manifest;
2. validates schemas;
3. confirms frozen-file integrity;
4. validates allowed-file scope;
5. runs declared read-only verification commands;
6. runs applicable lint, tier, evidence, recompute, and stamp checks;
7. confirms required reports and evidence receipts;
8. verifies repository-state policy;
9. writes the final state sidecar;
10. appends telemetry;
11. optionally commits the nested governance repository;
12. does none of steps 9–11 if any earlier gate fails.

This would have prevented the false C10 completion record. It also reduces human burden because the human no longer needs to interpret whether a collection of partial passes is enough to mark completion.

## 7.3 Implement Manifest and Contract Validation

These are already specified but unimplemented. v2.3 should validate:

- required fields and types;
- supported risk, scientific-claim, and evidence tiers;
- contract ID format;
- dependency existence and acyclicity;
- execution-order completeness;
- allowed/frozen path syntax;
- report destination conventions;
- verification command schema;
- owner compatibility with risk tier;
- stage-gate declarations;
- no placeholder tokens such as `<PENDING>` in an executable final manifest;
- no duplicate report path declarations;
- no contract/report filename mismatch.

## 7.4 Implement deterministic Allowed File Validation

Allowed File Validation should compare an exact pre-contract repository receipt with the post-contract state across both repositories. It should account for:

- tracked modifications;
- staged modifications;
- untracked files;
- deletions;
- renames;
- nested repository changes;
- declared generated-output roots;
- temporary files that were created and cleaned.

The result should be a machine-readable diff receipt. Medium/High raw-diff review by the Architect remains valuable, but routine scope checking should no longer depend solely on AI inspection or human relay.

## 7.5 Replace `--allow-dirty` with state policies

Support policies such as:

```yaml
repository_state:
  outer:
    head: 83545b7...
    branch: rehabilitation/phase-1
    staged:
      count: 0
      diff_sha256: e3b0c442...
    unstaged:
      count: 62
      diff_sha256: 71537cb4...
    untracked_allowlist_digest: ...
  nested:
    clean: true
```

Then Repository Integrity can pass a deliberately dirty but exact state instead of being skipped.

## 7.6 Define typed frozen-path semantics

Replace ambiguous strings with entries such as:

```yaml
frozen_files:
  - kind: file
    path: CMakeLists.txt
  - kind: recursive_glob
    pattern: source/include/**/*.hpp
  - kind: directory_merkle
    path: source/tests
  - kind: git_tree
    repository: project
    revision: caaac19
```

Unknown kinds fail closed. Empty globs fail unless `allow_empty: true` is explicit. Every frozen entry must appear in the baseline; a missing baseline entry should be a failure, not merely a warning, once the contract claims the baseline exists.

## 7.7 Define typed verification commands

Use structured commands:

```yaml
verification:
  - id: independent_snapshot_verify
    argv:
      - python3
      - project/chunks/chunk10/scripts/snapshot_baseline.py
      - verify
      - --snapshot
      - .snapshot_baseline/20260830_231745-83545b7
    cwd: repository_root
    side_effect: read_only
    idempotent: true
    network: forbidden
    timeout_seconds: 300
    expected_exit_codes: [0]
    supports_evidence: T2
```

Avoid shell interpretation by default. Permit a shell command only with `shell: true` and explicit justification. Gatekeeper should refuse to put a mutating `create`, `publish`, `upload`, or `commit` command into independent verification unless a dedicated sandbox policy is declared.

## 7.8 Make T1/T2/T3 evidence structural

An evidence receipt should record:

- claim ID;
- artifact identity;
- verifier identity and frozen hash;
- session identity;
- input identities;
- execution environment;
- independence dimensions;
- adversarial mutation IDs;
- pristine-control result;
- expected rejection layer;
- actual rejection layer;
- timestamps and exit codes.

Gatekeeper can then calculate the attained tier. Reports should not self-assign a tier stronger than the receipts justify.

## 7.9 Add production-path coverage checks

For T2/T3, require the receipt to prove that the declared production verifier executable was invoked. A test that imports no production module and invokes no production CLI cannot qualify as production-path T3.

This can be checked by command identity, frozen hash, and invocation receipt. It does not require the human to inspect test code merely to establish that basic fact.

## 7.10 Add portable archive primitives

Provide a Factory-owned archive helper that:

- disables AppleDouble/macOS metadata unless explicitly required;
- rejects absolute and parent-traversal paths;
- uses NUL-delimited source inventories;
- records raw member inventories using a cross-platform parser;
- rejects duplicates and unsupported types;
- controls timestamps, owners, groups, modes, and gzip metadata for reproducibility;
- verifies extraction in a fresh directory;
- optionally verifies on a second archive implementation in CI;
- emits a standard receipt.

Projects should not have to rediscover archive portability individually.

## 7.11 Add cross-repository transaction receipts

For nested Factory projects, record:

```text
outer repository identity
outer semantic dirty-state identity
nested specification commit
nested frozen-baseline commit
artifact creation identity
nested evidence-filing commit
```

Gatekeeper should display this chain in one command. This would make it immediately clear why a snapshot legitimately contains nested HEAD `caaac19` while the final report is committed later at `970e1c1`.

## 7.12 Add append-only correction semantics

Define standard telemetry events:

- `contract_planned`;
- `contract_started`;
- `contract_blocked`;
- `contract_reopened`;
- `contract_superseded`;
- `contract_complete`;
- `completion_corrected`;
- `stage_gate_opened`;
- `stage_gate_closed`.

Each event should reference the event it supersedes when applicable. Gatekeeper should derive current state by replaying the log and compare it with the authoritative state sidecar.

## 7.13 Validate report schemas without relying only on headings

Keep Markdown, but generate or validate it against a structured report sidecar. Required fields should include:

- objective;
- actual input identities;
- actual outputs;
- files changed;
- evidence receipt IDs;
- commands actually run;
- checks skipped and why;
- final status;
- remaining risks;
- active stop-gates;
- proof boundaries.

The rendered Markdown can be standardized automatically. Humans receive a readable report without being asked to repair formatting conventions.

## 7.14 Make proof boundaries mandatory and generated

Every PASS or CERTIFIED output should contain:

- checks executed;
- checks applicable but skipped;
- checks unavailable in this Factory version;
- AI-attested judgments;
- human-authority decisions still pending;
- external-state dependencies.

The information already exists in places. v2.3 should propagate it automatically into reports and certification so polished prose cannot visually obscure a narrow proof scope.

## 7.15 Add durable-copy support without adding human work

The human should not be asked to design a backup procedure. The Factory should:

1. detect mounted filesystems and configured approved remotes;
2. distinguish another directory from another filesystem;
3. estimate space;
4. classify artifact sensitivity and size;
5. propose eligible existing destinations;
6. perform the copy when an already-authorized destination exists;
7. run verification at the destination;
8. write the receipt;
9. open the stage gate automatically.

If no authorized destination exists, the existing human responsibility remains only to provide or authorize an external resource. That is not a new responsibility. All procedural work after the resource appears belongs to the Factory.

## 7.16 Add large-artifact policy

Before suggesting Git or a public remote, Gatekeeper should detect:

- files exceeding host limits;
- potentially licensed or sensitive data;
- ignored content;
- archives containing local paths or credentials;
- whether Git LFS is configured;
- whether an object-store or release-asset destination is private;
- expected transfer and verification size.

The KLStream snapshot was too large and potentially too sensitive to push casually to the configured GitHub origin. The correct action was to block, not upload.

## 7.17 Improve temporary-workspace policy

Add command-level options:

- `retain_on_unexpected_failure`;
- `clean_on_expected_rejection`;
- `max_retained_bytes`;
- `diagnostic_summary_path`;
- `retention_expiry`.

T3 expected failures should preserve bounded error receipts, not multi-gigabyte clones.

## 7.18 Make model/provider bindings configurable

Replace prose such as “Architect currently bound to Claude” and “Implementor currently bound to Gemini” with capability profiles:

- role: Architect;
- minimum reasoning/tool capabilities;
- permitted risk tiers;
- required independence relationship;
- model/session identity recorded at runtime.

This preserves role separation while allowing Codex or another capable agent to perform the role. Vendor names can remain recommended profiles, not constitutional identity.

## 7.19 Improve self-check precision

The v2.2 self-check correctly found no implemented/spec command drift, but produced version-reference and naming warnings that include intentional historical references and permissive-input examples. Improve it by distinguishing:

- normative current-version declarations;
- historical changelog references;
- compatibility examples;
- intentionally accepted unpadded input;
- worked examples that should be canonical.

Warnings should include a stable finding ID and suppression mechanism with rationale. This reduces noise without giving the human a new review obligation.

## 7.20 Make Gatekeeper output composable

Every command should support `--json`. Human-readable output remains the default, but machine output should contain stable keys, exit classification, checks run, skipped checks, artifacts, and finding IDs.

Agents currently have to parse long terminal prose. JSON output would reduce context usage, prevent transcription errors, and make aggregate certification more reliable.

# 8. Scientific and publication improvements for v2.3

KLStream is not only software; it is research software. The Factory’s scientific layer is one of its most important differentiators, but several mechanisms remain procedural or heuristic.

## 8.1 Make claim identity explicit

Assign stable claim IDs to title, abstract, method, result, table, figure, and limitation claims. Every claim should link to:

- scientific tier;
- supporting artifact IDs;
- dataset identity;
- run-set identity;
- metric definition version;
- statistical protocol version;
- verdict and effect size;
- supersession status.

This prevents two individually valid but inconsistent numbers from coexisting without a declared authoritative result.

## 8.2 Treat supersession as first-class

Research rehabilitation often recomputes a metric with a corrected pipeline. The old number should not disappear, but it must be marked:

- active;
- superseded;
- invalidated;
- exploratory-only;
- fixture-only;
- legacy-unverified.

Gatekeeper should reject a manuscript that cites a superseded result as active evidence.

## 8.3 Make data class impossible to confuse

Data manifests should use immutable IDs and classes:

- REAL_LICENSED;
- REAL_PUBLIC;
- SYNTHETIC;
- FIXTURE;
- LEGACY_UNVERIFIED.

Directory names alone are insufficient. Acquisition, transform, split, training, evaluation, and manuscript artifacts should carry the data identity. A Reality Gate pass must never upgrade synthetic data into real data.

## 8.4 Separate property validation from authenticity

The Factory learned from earlier projects that simulated data can satisfy every schema and distribution check. Therefore Reality Gate should report separate dimensions:

- authenticity/provenance;
- license/authorization;
- schema validity;
- temporal validity;
- distribution sanity;
- leakage checks;
- transformation lineage.

No aggregate PASS should conceal an unknown authenticity dimension.

## 8.5 Strengthen statistical evidence receipts

Record the unit of analysis, pairing keys, exclusions, multiplicity family, test, effect size, confidence interval method, random seed, stop rule, and exact included run IDs. Independent recomputation should read raw or minimally processed evidence rather than an already aggregated scalar whenever the claim concerns a distribution.

## 8.6 Add claim-language lint tied to evidence

The existing tier inference is useful but heuristic. Add bounded checks for words such as “real-time,” “guarantees,” “significant,” “causes,” “outperforms,” “generalizes,” “production-ready,” and “real-world.” Each term should require an appropriate claim/evidence record or produce a finding.

This is not open-ended semantic truth checking. It is a fail-closed requirement that strong recurring words have declared evidence.

## 8.7 Require clean-environment reproduction receipts

A release should distinguish:

- fixture reproduction;
- synthetic full-pipeline reproduction;
- real-data reproduction requiring licensed inputs;
- performance reproduction on declared hardware;
- manuscript build reproduction.

Each mode needs a separate receipt. “One command works locally” is not sufficient evidence for all modes.

# 9. Candidate v3 architecture

If the Factory adopts the following changes together, they justify v3.0 because they change the core execution model.

## 9.1 From document workflow to typed artifact graph

The central object should become an append-only graph:

```text
Requirement -> Contract -> Change Set -> Artifact -> Verification Run
            -> Evidence Receipt -> Claim -> Release Certificate
```

Every node has a stable ID and content digest. Every edge has a typed meaning such as `implements`, `freezes`, `verifies`, `supersedes`, `supports`, `contradicts`, `derived_from`, or `blocks`.

Markdown becomes a generated and editable view of the graph, not the only database.

## 9.2 Transactional execution engine

A contract run should have phases enforced by one engine:

1. resolve and validate inputs;
2. capture repository and artifact baselines;
3. create an isolated work context where appropriate;
4. execute allowed changes;
5. calculate the actual change set;
6. reject out-of-scope changes;
7. run verification;
8. produce evidence receipts;
9. run independent/adversarial gates required by risk;
10. atomically file report, telemetry, and state;
11. commit or roll back governance state;
12. expose a clear blocked state when external resources are missing.

This would replace the current sequence of loosely coordinated commands.

## 9.3 Policy engine instead of scattered prose checks

Policies should be machine-readable and versioned:

- High risk requires T2 plus targeted T3;
- T-COMP requires recomputation and stamp;
- external acquisition forbids synthetic fallback;
- public release requires secret/path/license scan;
- intentionally dirty repository requires an exact state baseline;
- large artifacts require an approved storage class;
- stop-gates block dependency edges automatically.

The Constitution remains human-readable and authoritative, but executable policies implement its deterministic subset.

## 9.4 Evidence-capability negotiation

Before executing a contract, the Factory should determine whether the current environment can satisfy its evidence requirements:

- required compiler/platform;
- network access;
- external credentials;
- independent session availability;
- storage capacity;
- container runtime;
- hardware counters;
- separate filesystem;
- publication toolchain.

If not, the contract enters a typed blocked state before implementation begins. Independent work on nondependent contracts can continue automatically.

## 9.5 First-class multi-repository support

The v3 engine should treat the outer project repository, nested governance repository, and external artifact store as one logical transaction with multiple commit domains. It should never pretend they are atomically committed, but it can issue a signed transaction receipt mapping their identities.

## 9.6 Built-in retrospective learning

After a chunk or project, the Factory should aggregate:

- which predicted failure modes occurred;
- which failures were not predicted;
- false-positive and false-negative Gatekeeper findings;
- verification runtime and storage cost;
- reopened contracts;
- evidence-tier downgrades;
- human-action blockers;
- repeated correction patterns.

It can then draft—but not automatically activate—Factory changes. Existing human approval of Factory evolution remains unchanged. The system does the analysis and drafting; the human retains approval authority without receiving new operational chores.

# 10. Suggested implementation priority

## v2.3 release blockers

1. Transactional `complete-contract`.
2. Manifest and contract schema validation.
3. Allowed-file validation.
4. Exact repository-state baselines replacing broad dirty skips.
5. Typed read-only verification commands with working directories.
6. Structural T1/T2/T3 receipts and production-path enforcement.
7. Report/state/telemetry consistency validation.
8. Typed frozen-path semantics.
9. JSON output for Gatekeeper commands.
10. Portable archive helper and raw-member validation.

## v2.3 strongly recommended

11. Cross-repository transaction receipts.
12. Durable-copy destination detection and verification receipts.
13. Large-artifact storage/sensitivity policy.
14. Standard correction/supersession telemetry.
15. Generated proof boundaries.
16. Temporary-workspace retention policy.
17. Provider-neutral role capability profiles.
18. More precise self-check findings.

## v3 candidates

19. Typed artifact/evidence/claim graph.
20. Transactional execution engine spanning repositories and artifact stores.
21. Versioned executable policy engine.
22. Environment/evidence capability negotiation.
23. Generated Markdown views from authoritative structured state.
24. Built-in cross-project retrospective aggregation.

# 11. Migration strategy

## 11.1 Do not invalidate existing Factory projects

v2.3 should read existing v2.2 artifacts. A migration command should:

- scan manifests, contracts, reports, telemetry, snapshots, and stamps;
- infer structured fields only when unambiguous;
- mark ambiguous fields `UNRESOLVED` rather than guessing;
- generate a migration report;
- leave original Markdown unchanged;
- create structured sidecars;
- require no routine manual rewriting by the human.

The AI roles can resolve project-specific ambiguities through normal contracts. The human should be involved only if the ambiguity represents a real authority decision.

## 11.2 Introduce strictness in stages

Suggested compatibility modes:

- `legacy-read`: understand v2.2 artifacts and report gaps;
- `v2.3-warn`: generate structured state and warn on ambiguity;
- `v2.3-strict`: reject ambiguous finalization;
- `v3-native`: require typed graph/state artifacts.

New projects should default to strict mode. Existing projects can migrate without losing history.

## 11.3 Preserve evidence identities

Migration must never rehash rewritten content and present it as the original evidence. It should record:

- original artifact digest;
- migrated representation digest;
- transformation tool/version;
- semantic equivalence status;
- unresolved differences.

# 12. Metrics for judging whether v2.3 or v3 is better

The Factory should evaluate its own update with measurements rather than intuition. Useful metrics include:

- contracts falsely marked complete before a gate failure;
- report/state/telemetry disagreements;
- verification commands failing due to wrong working directory;
- out-of-scope file changes detected mechanically;
- missing frozen baseline entries;
- T2/T3 claims downgraded after review;
- production-path coverage failures;
- archive portability defects;
- average human handoff actions per chunk;
- human actions that were routine rather than authority-based;
- time spent parsing prose versus structured results;
- retained failure-diagnostic disk usage;
- reopened-contract rate;
- certification findings discovered only after release packaging;
- number of skipped gates hidden from final summaries;
- clean migration success rate from v2.2.

Success should include **no increase in human operational actions**. A stronger version that requires the human to perform more copying, formatting, comparing, or bookkeeping has failed an important design objective even if it adds more checks.

# 13. Recommended version decision

I recommend producing **v2.3 first**.

The immediate defects observed in KLStream are largely failures to mechanically enforce concepts that v2.2 already contains:

- completion should follow gates;
- manifests and contracts should validate;
- allowed files should be checked;
- evidence tiers should match evidence;
- verification commands should actually run correctly;
- frozen paths should mean what authors think they mean;
- proof boundaries should be explicit;
- corrections should be append-only;
- stop conditions should block dependencies.

Implementing those items can remain backward compatible and would be a substantial minor release justified by real project evidence.

I would call the next release **v3.0** only if it adopts the typed artifact graph, transactional execution engine, executable policy layer, and multi-domain transaction receipts. That is a genuine architectural redesign. It changes the Factory from a document-centered protocol with deterministic helpers into an evidence-centered workflow engine that also renders documents.

# 14. Final experience summary

Working with Factory v2.2.0 on KLStream was better than working without a Factory. It encouraged preservation before cleanup, made risk visible, supplied a vocabulary for independent and adversarial evidence, separated governance history from the public project, and made it legitimate to stop when an external durability requirement could not be satisfied.

Its greatest weakness was not bad principles. Its principles were often exactly right. Its weakness was the distance between those principles and the deterministic state machine actually enforced by Gatekeeper.

The most serious errors I encountered were not obscure compiler bugs. They were trust-chain errors:

- a T3 label attached to tests that did not invoke production code;
- a completion event written before the Factory report gate passed;
- a verification command that failed when executed exactly as declared;
- archive inventories that looked correct through the host tool while raw members disagreed;
- a mutable pointer inside a forensic workflow;
- a certified-looking project history whose underlying claims still required re-audit.

Those are precisely the kinds of failures an AI Software Factory should prevent. They are also fixable without burdening the human operator.

The best direction for the Factory is therefore:

1. keep the Constitution, contract discipline, evidence tiers, stop conditions, nested governance history, and proof-boundary honesty;
2. turn more of the existing prose rules into typed, deterministic checks;
3. make completion an atomic gated transition;
4. make evidence identity and production-path coverage explicit;
5. make reports rendered views of authoritative structured state;
6. automate routine handoffs, comparisons, receipts, and cleanup;
7. preserve or reduce human responsibilities, never expand them;
8. reserve human attention for genuine authority and judgment.

KLStream provided sufficient real-world evidence for a meaningful v2.3. If the deeper graph-and-transaction architecture is adopted, the experience also justifies planning v3.0.
