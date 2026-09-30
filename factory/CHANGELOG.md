# CHANGELOG

This document records the evolution of the AI Software Factory.

Its purpose is to preserve the history of the Factory itself.

It does **not** record project changes.

Project changes belong inside the project repository.

---

# Versioning Philosophy

The Factory evolves only through evidence.

Ideas do not justify a new version.

Completed projects, measured improvements, and reproducible engineering experience do.

Every version entry should answer

- What changed?
- Why was it changed?
- What evidence justified it?
- Is it backward compatible?

---

# Change Categories

Each change belongs to one of the following categories.

## Added

New Factory capability.

---

## Changed

Modification of existing behavior.

---

## Deprecated

Feature scheduled for removal.

---

## Removed

Feature removed from the Factory.

---

## Fixed

Correction of a defect.

---

## Documentation

Documentation only.

No Factory behavior changed.

---

## Internal

Refactoring or implementation improvements.

No user-visible behavior changed.

---

# Version Format

```
## vMajor.Minor.Patch

Release Date

YYYY-MM-DD
```

Every release contains the appropriate categories.

Unused categories may be omitted.

---

# Patch Releases

Patch releases

```
v1.0.x
```

May include

- bug fixes
- wording improvements
- clarification of specifications
- documentation improvements
- deterministic refinements

Patch releases must not introduce architectural changes.

---

# Minor Releases

Minor releases

```
v1.1

v1.2
```

Represent evidence-backed improvements to the Factory workflow.

Requirements

- at least one completed project
- measurable evidence
- retrospective review
- backward compatibility whenever practical

---

# Major Releases

Major releases

```
v2.0

v3.0
```

Represent architectural redesign.

Major releases may

- replace workflows
- redesign ownership
- replace major Factory components
- introduce incompatible changes

Major releases should preserve migration paths whenever practical.

---

# Backward Compatibility

Whenever possible

New Factory versions should continue understanding artifacts created by previous versions.

If compatibility cannot be preserved

The breaking change must be documented.

---

# Release Template

```
## vX.Y.Z

Release Date

YYYY-MM-DD

### Added

-

### Changed

-

### Deprecated

-

### Removed

-

### Fixed

-

### Documentation

-

### Internal

-

### Evidence

-

### Notes

-
```

---

# Release History

## v1.0.0

Release Date

2026-07-14

### Added

- Initial AI Software Factory architecture
- Constitution
- Factory Specification
- Dynamic Rules
- Project Architecture
- Contract-based workflow

### Notes

Initial Factory release.

---

## v1.0.1

Release Date

2026-07-14

### Added

- Evolution layer
- Bootstrap Manifest
- Project Bootstrap Specification
- Gatekeeper Specification
- Factory artifact lifecycle
- Ownership model
- Continuous telemetry
- Decision logging
- Metrics collection
- Experiment tracking

### Changed

- Moved Constitution completely to the Factory layer.
- Formalized repository bootstrap process.
- Clarified artifact ownership.
- Clarified project initialization responsibilities.

### Documentation

- Expanded Factory Specification.
- Expanded Dynamic Rules documentation.
- Defined Bootstrap procedure.
- Defined Gatekeeper responsibilities.

### Evidence

Derived from iterative design and review of the Factory architecture prior to the first production project.

### Notes

This release freezes Factory v1.0.1.

No further structural changes should be made until at least one complete project has been executed and reviewed through the Factory. Future improvements should be proposed, evaluated, and versioned according to the Factory's evidence-first philosophy.

---

## v1.1.0

Release Date

2026-07-18

### Added

- `gatekeeper.py` — a real, partial implementation (frozen-file hash validation, report validation, repository integrity check). Previously spec-only.
- `VERSION` file (was referenced everywhere, including as a hard requirement in `bootstrap.sh`, but did not exist).
- Enforcement Level (A/B/C) and Related Rules tagged on all 50 Constitution rules (C01–C50). Section 7 required these fields since the document existed; none of the 50 rules carried them until now.
- `Risk Tier` and `Implementation Owner` fields on the Contract Specification, with a corresponding exception to Claude's implementation ban for `High` tier contracts.
- Architecture Amendment as an explicit, named path back from Contract Execution to Chunk Planning, distinct from a Fix Package.
- A dedicated Chunk Review section (previously a named box in the pipeline diagram with no elaboration anywhere) requiring raw-artifact inspection for Medium/High tier contracts, not just the self-authored chunk report.
- `AI_Note.md` defined (previously appeared once, in the Artifact Lifecycle table, with no elaboration anywhere else).
- A worked schema/example for `execution_manifest.yaml` and for `telemetry.jsonl` (including `model_id`/`model_version` fields). Neither had one before; both were referenced as load-bearing.
- Lightweight Chunk Designation — an explicit, still-verified, lower-ceremony path for small/low-risk work.
- A retry ceiling on the Phase 2 ↔ Phase 3 loop (escalates to Claude after 2 failed cycles on the same contract).
- A `Performance` definition in the Constitution disambiguating computational performance from research/benchmark results.

### Changed

- `bootstrap_manifest.yaml`: `idempotent` changed from `false` to `true`.
- `bootstrap.sh`: now actually reads `bootstrap_manifest.yaml` (idempotent flag, `copy_factory_files` list) instead of hardcoding behavior; checks `factory/`, `project/`, `source/` individually and fills only what's missing instead of refusing to run if any exist; rollback on failure now only removes what the run itself created; copies exactly the files `copy_factory_files` lists instead of the entire `factory/` directory; supports `FACTORY_BOOTSTRAP_YES=1` for non-interactive use.
- The undefined "Splitter" role (referenced in the Artifact Lifecycle table, defined nowhere) is now explicitly Claude's responsibility, performed as the last step of Chunk Planning.
- Constitution's "Constitutional Priority" section rewritten to explicitly map onto Section 1/4's precedence order instead of standing as a second, unreconciled hierarchy.
- Constitution's Contract definition ("acceptance criteria") reconciled with `factory_spec.md`'s and `gatekeeper_spec.md`'s "Definition of Done" terminology.
- `notes/` and `scripts/` in the Chunk Specification now have an assigned owner (Gemini); previously unowned.

### Fixed

- Three-way contradiction between `bootstrap_manifest.yaml` (`idempotent: false`), `factory_spec.md`'s prose ("must always be safe to run"), and `bootstrap.sh`'s actual behavior (hard failure on any existing target directory).
- `bootstrap.sh` never read `bootstrap_manifest.yaml` despite the Bootstrap Procedure listing that as its first step.

### Evidence

No project has executed against v1.0.1 yet, so none of the above rests on the "at least one completed project" evidence bar C50/the Minor Release requirements normally call for — the same gap that let v1.0.1 itself ship several structural additions as a patch. That gap isn't resolved here; it's disclosed instead of repeated silently. What justifies these specific changes is closer to design review than field evidence: every item above is a contradiction confirmed by direct inspection of this repository's own files (bootstrap tested end-to-end against a throwaway local repo; `gatekeeper.py` tested against real hash-mismatch, missing-report, and clean-tree scenarios), not a hypothetical or a preference. Treat the process-shaped additions (Risk Tier routing, Architecture Amendment, Lightweight Chunk, the Phase 2/3 retry ceiling) as `PROPOSED` in spirit even though this document doesn't have a formal proposed/active split the way `dynamic_rules.md` does — they haven't been exercised on a real project yet either.

### Notes

This release intentionally bundles fixes discovered before any project ran against v1.0.1, rather than deferring them. Whether that satisfies the spirit of the Minor Release gate is a human judgment call, not something this entry can settle on its own — flagged explicitly per the Evidence note above rather than left implicit the way v1.0.1's own capability additions were.

---

## v1.1.1

Release Date

2026-07-18

### Fixed

- Phase 3's retry-ceiling mechanism assumed Claude is reachable mid-chunk (`ESCALATE TO CLAUDE` after 2 failures). It isn't, under the human's actual usage pattern (Claude used only at chunk start and chunk end). Replaced with an autonomous graceful-degradation protocol: up to 5 total attempts with an explicitly more conservative strategy from attempt 3 onward, then mark the contract `COMPLETE — FLAGGED` (safe partial pass) or `BLOCKED — CARRIED FORWARD` (no honest pass exists), never a fabricated clean pass, and continue with whatever the dependency graph allows. Escalation is deferred to Chunk Review, which is a real chunk-boundary Claude touchpoint.

### Added

- "Human Usage Model" section in `factory_spec.md` stating explicitly that Claude is used at exactly two points per chunk (start: chunk/contract generation; end: Chunk Review), and that fixes found at Chunk Review are folded into the *beginning* of the next chunk's contract list rather than requiring a separate round-trip.
- "Human Action Required" contract convention — for dependencies no AI in the Factory can resolve (e.g. training on hardware the Implementation Engineer doesn't have access to). Distinct from a Risk Tier or Claude-availability issue; the Implementation Engineer reports it plainly and works around it via the dependency graph rather than faking a substitute result.

### Evidence

Both changes were surfaced by the human describing an actual constraint (limited Claude usage; hardware constraints for GPU-dependent contracts) that v1.1.0's text couldn't have been checked against without that information. This is a correction of a wrong operating assumption discovered before first use, not a workflow redesign — treated as patch-level per the same reasoning as v1.1.0's other fixes, not gated on project-completion evidence.

### Notes

Nothing in `constitution.md`, `gatekeeper_spec.md`, or `dynamic_rules.md` changed in content — their version headers were bumped to 1.1.1 alongside `factory_spec.md` purely so every file in the Factory continues to report the same current version, not because their rules changed.

---

## v1.1.2

Release Date

2026-07-18

### Added

- `gatekeeper.py snapshot-chunk --manifest {{path}}` — snapshots every contract's `frozen_files` in a chunk in one command, reading directly from `execution_manifest.yaml` instead of the human retyping file lists per contract. The single-contract `snapshot` command still exists for re-freezing one contract after an Architecture Amendment.
- `gatekeeper.py next --manifest {{path}}` — reads `execution_order` plus each contract's `contract_report.md` Final Status and reports which contract is ready to run, correctly skipping *past* (not stopping at) contracts blocked on something that doesn't depend on them. This is a deterministic read of a dependency order Claude already resolved at chunk-generation time, not a new reasoning capability for Gatekeeper.
- Report file path convention formalized: `reports/{{CONTRACT_ID}}/contract_report.md` (`factory_spec.md`'s Chunk Specification — previously undefined; `gatekeeper.py`'s new commands needed it to exist unambiguously).
- `chunk_report_compilation_prompt.md` — the template `chunk_report.md` never had. Closes a gap flagged in the previous review, not one of the three items proposed this round, but low-cost to close while touching adjacent material.
- Fix Package Structure (`factory_spec.md`, Chunk Review section) — `fix_package.md` was referenced by name in four places in the frozen spec without ever being given a shape. Same category of gap as `chunk_report.md`, closed the same way.

### Fixed

- `gatekeeper_spec.md`'s Implementation Status section listed exit code 2 for Frozen File Validation failures; the actual code (and the Exit Codes table both sections are supposed to agree with) is 4. Caught while updating this section for the new commands, unrelated to this round's actual asks — fixed anyway since it was found.

### Evidence

All three additions were tested directly rather than asserted: `snapshot-chunk` against a 3-contract manifest with mixed frozen-file lists; `next` against fresh/partial/all-complete/blocked-with-independent-work-available/unparseable-status states. The blocked-contract-skipping behavior in `next` failed on first implementation (it stopped scanning entirely at the first `BLOCKED` contract instead of skipping past it to check independent later contracts) — caught by the test, fixed, re-verified. Not run against a real project yet; these are unit-tested in isolation, not proven under actual chunk execution.

### Notes

All three changes originated from an external second-opinion review (ChatGPT, shown the full v1.1.1 workflow), not from project evidence — same evidence-gate tension as v1.1.0 and v1.1.1, flagged again rather than left implicit. Evaluated independently rather than accepted at face value: the "let Gatekeeper drive execution" proposal in particular was reframed during implementation once it became clear `execution_order` already made it a lookup rather than a graph computation, which changed the risk assessment of adding it.

---

## v1.1.3

Release Date

2026-07-23

### Added

- `DROP_HERE/` — a gitignored inbox directory (`bootstrap_manifest.yaml`, `bootstrap.sh`) for handing files to the Implementation Engineer without the Human pre-sorting them into the project's real file structure by hand.
- `gatekeeper.py sort-dropbox` — deterministically files everything present in `DROP_HERE/` to the destination declared for it, by exact filename match, in `DROP_HERE/dropbox_manifest.json`. Refuses to overwrite an existing destination without `--force`; anything dropped that the manifest doesn't name is left in place and reported, never moved by inference. This is a deterministic Gatekeeper check, not Implementation Engineer judgment — see the Dropbox Specification's rationale (C01/C07/EP-002).
- Dropbox Specification (`factory_spec.md`) — defines `dropbox_manifest.json`'s schema, that Claude owns and generates it at Chunk Planning alongside `execution_manifest.yaml`, and how it relates to the Mailbox Protocol below.
- Mailbox Protocol (`contract_execution_autonomous_prompt.md`) — a short Human-supplied trigger phrase ("check your mailbox" or equivalent) that tells the Implementation Engineer to run `sort-dropbox`, then `gatekeeper.py next`, then proceed with the next contract exactly as if the Human had manually filled in and sent the full execution prompt. Documented inside the execution prompt itself so it travels with the document Gemini already reads once per session, rather than living in a separate file that could drift out of sync.
- Self-containment requirement on `contract_report.md` (Phase 4 of `contract_execution_autonomous_prompt.md`) and `chunk_report.md` (`chunk_report_compilation_prompt.md`): both now quote Objectives, Definition of Done items, and Invariants verbatim rather than referencing `contractNN.md`, and both close with a short Plain-Language Summary — so either file is readable and actionable on its own, without the rest of the chunk's artifacts open alongside it.

### Changed

- `bootstrap_manifest.yaml` / `bootstrap.sh`: `DROP_HERE/` added to `create_directories`, `outputs.directories`, and the `.gitignore` append list, following the exact same idempotent create-if-missing/leave-if-present pattern already used for `factory/`, `project/`, and `source/` — no new idempotency logic, reuse of the existing one.
- `chunk_planning_prompt.md`: Claude's chunk-planning output now includes `DROP_HERE/dropbox_manifest.json` alongside `execution_manifest.yaml` and the contract files — written even when empty, so "no dropbox needed this chunk" is explicit rather than an unexplained absence.
- `gatekeeper_spec.md`'s Implementation Status and Inputs sections updated to list Dropbox Sort and `dropbox_manifest.json`, matching the same disclosure pattern used for every other implemented-subset claim in that document.

### Evidence

None of this rests on completed-project evidence — no project has run through the Factory yet, the same disclosed gap as v1.1.0, v1.1.1, and v1.1.2. What justifies it here is the same category of justification those releases used: direct design review against a stated, concrete workflow problem (the Human describing, in real use, that manual file placement and prompt re-typing were the actual friction points — not a hypothetical), plus unit-level testing of the new mechanism in isolation. `sort-dropbox` was tested against a synthetic `dropbox_manifest.json` with a mix of matched, unmatched, and pre-existing-destination files; the unmatched and existing-destination cases were confirmed to leave files untouched and exit non-destructively rather than guessing. `bootstrap.sh`'s `DROP_HERE/` handling was tested end-to-end against a throwaway local repo, including a second idempotent run to confirm no duplication and no `.gitignore` drift.

### Notes

This release deliberately does not touch anything about verification, Risk Tier routing, Contract Specification, or the Phase 1–4 pipeline itself — every addition here is process-adjacent tooling (file placement, prompt re-invocation, report readability), not a change to what gets built or how it's checked. That's a conscious scope boundary, not an oversight: the person requesting this was explicit that Factory performance and results should see zero compromise, and the safest way to honor that was to keep this release entirely outside the verification-and-correctness surface area. Treat the Mailbox Protocol and Dropbox Sort as convenience layers sitting on top of an unchanged core pipeline, not as a new pipeline.

The Human has indicated more changes are coming in this vein (a "ClaudeInitialization.md" single-file onboarding document is the next one under discussion) — v1.1.3 is being released now rather than held to batch with that, since it's a complete, independently justified unit on its own and there's no reason to make it wait on a design that hasn't been finalized yet.

---

## v1.1.4

Release Date

2026-07-23

### Added

- `ClaudeInitialization.md` — a single consolidated onboarding document for the Architect role, replacing the need to locate and paste three separate prompt files (`project_initialization_prompt.md`, `chunk_planning_prompt.md`, `chunk_review_prompt.md`) at different points in a project. Attached once, alongside `project_description.md` (or raw project notes), at the start of a fresh Architect session; after that, chunk hand-offs can be informal ("here are chunk 1's reports, give me chunk 2").

### Changed

- None. `constitution.md`, `factory_spec.md`, `gatekeeper_spec.md`, `dynamic_rules.md`, and `gatekeeper.py` are unchanged in content this release — version headers bumped for cross-file consistency only, same convention used in v1.1.1's Notes.

### Deprecated

- `project_initialization_prompt.md`, `chunk_planning_prompt.md`, and `chunk_review_prompt.md` are superseded by `ClaudeInitialization.md` for new projects. They are not removed — a project already mid-flight on the three-file workflow can keep using them without migrating, and the individual per-step content they contained still exists (restated inside `ClaudeInitialization.md`'s sections 5a/5b/5c), so nothing about *what* the Architect does changed, only how much the Human has to paste to invoke it.

### Evidence

Same evidence-gate disclosure as every release since v1.0.1: no project has been completed through the Factory yet. This one has a narrower evidence claim than most, though — it doesn't add or change any Factory *behavior*, verification rule, or contract mechanic; it repackages instructions that already existed and were already exercised in design review during v1.1.0–v1.1.3's own drafting. The risk surface of "one document is harder to keep internally consistent than three focused ones" was mitigated by cross-checking `ClaudeInitialization.md`'s §5a/5b/5c against the three prompt files it replaces line-by-line rather than rewriting from memory — every requirement, field, and check present in the originals is present here.

### Notes

This keeps the same scope discipline v1.1.3 stated explicitly: nothing here touches verification, Risk Tier routing, the Contract Specification, or the Phase 1–4 pipeline. It is convenience-layer tooling for the Human-Architect interface only. The three deprecated prompt files remain in the repository and remain correct to use; `ClaudeInitialization.md` is the lower-friction default going forward, not a forced migration.

---

## v1.2.0

Release Date

2026-07-23

### Added

- `factory/gemini_spec.md` — a permanent, bootstrapped operating manual for the Implementation Engineer role, read once per Antigravity session. Contains everything that previously lived in `contract_execution_autonomous_prompt.md` and `chunk_report_compilation_prompt.md` (Rules 1–7, Phases 1–4, the five-attempt Self Review ceiling, evolution logging, contract/chunk report formats) unchanged in substance, plus: contract auto-discovery (finds the active chunk and next contract from `gatekeeper.py next` and on-disk filenames, with no fields hand-copied from a template), and a generalized Mailbox Protocol recognizing "check the mailbox," "chunk N is here, do it," "do the next one," and "compile the chunk report" as standing triggers rather than a single fixed phrase.
- Filename convention for every Architect-produced artifact, specified in both `ClaudeInitialization.md` §4 and `gemini_spec.md` §3: `chunkNN.md`, `execution_manifest_chunkNN.yaml`, `C{NN}-{seq}_contract.md`, `C{NN}-{seq}_contract_report.md`, `chunkNN_report.md`, `fix_package_chunkNN.md`, plus the five fixed project-init filenames. Chunk numbers are always zero-padded to 2 digits. This is what lets Gemini locate its own work without the Human typing a chunk or contract ID anywhere.
- `gatekeeper.py sort-dropbox` now supports **pattern-based rules** (regex, with `{1}`/`{2}` capture-group substitution into the destination path) alongside the existing exact-filename `entries`, and normalizes capture group 1 (the chunk number) to 2-digit zero-padding regardless of how it was typed in the dropped filename. This was required the moment filenames became convention-based rather than one-off — an exact-match-only dropbox couldn't recognize "any `C01-07_contract.md`-shaped file," only files it had been told about individually in advance.
- `bootstrap.sh` now seeds `DROP_HERE/dropbox_manifest.json` on first run with the fixed `rules` set matching the filename convention above. It is written once and never regenerated — idempotent exactly like every other bootstrapped artifact, left completely untouched on a re-run if it already exists (including any project-specific `entries` Claude has since appended).

### Changed

- `dropbox_manifest.json`'s role: from a document Claude wrote fresh per chunk (v1.1.3) to a permanent Factory file, bootstrapped once, that Claude only ever *appends project-specific `entries` to*. The fixed `rules` half is Factory infrastructure now, not something any chunk plan generates.
- `factory_spec.md`'s Dropbox Specification rewritten to describe the `rules`/`entries` split and the new ownership model (bootstrap owns `rules`; Claude owns `entries`; the Implementation Engineer only reads).
- `bootstrap_manifest.yaml`: `factory/gemini_spec.md` added to `copy_factory_files`; `DROP_HERE/dropbox_manifest.json` added to `generated_files` (seeded content, not empty); `ownership` gained an `execution` entry naming `gemini_spec.md` as what governs the Implementation Engineer role, replacing the old per-contract-prompt model implied there before.
- `ClaudeInitialization.md` rewritten: adds an explicit "two workspaces" section (§0a) making clear that Claude and Gemini share a repository but not a conversation, and that filename correctness is the entire mechanism holding the hand-off together; adds the full naming-convention table (§4); redefines its own relationship to `dropbox_manifest.json` as append-only.
- `gatekeeper_spec.md`'s Implementation Status updated to describe pattern-rule support in `sort-dropbox`.

### Deprecated → Removed

v1.1.4 deprecated `project_initialization_prompt.md`, `chunk_planning_prompt.md`, and `chunk_review_prompt.md` without removing them, on the reasoning that a project already mid-flight shouldn't be forced to migrate. This release goes further, per explicit Human direction: **all five of those Gemini/Claude-facing prompt files, plus `README_execution_prompts.md`, are deleted outright** — `project_initialization_prompt.md`, `chunk_planning_prompt.md`, `chunk_review_prompt.md`, `contract_execution_autonomous_prompt.md`, `chunk_report_compilation_prompt.md`, `README_execution_prompts.md`. Nothing about *what* either role does was lost — every requirement, field, phase, and check from all five is present in `ClaudeInitialization.md` and `gemini_spec.md`, cross-checked line-by-line during this rewrite rather than reconstructed from memory. What's gone is the requirement to locate, fill in, and paste a document per contract or per chunk milestone. There is no supported path back to the five-file workflow; a project on an older Factory version that still relies on them should stay on that version rather than mixing file sets.

### Evidence

Same evidence-gate disclosure as every release since v1.0.1: no project has been completed through the Factory yet. Unlike v1.1.4, this release *does* touch real mechanics — `sort-dropbox`'s matching logic changed, and the entire hand-off model between Claude and Gemini changed from "paste a filled-in template" to "produce a correctly-named file and say something generic." That is a materially larger surface than v1.1.3/v1.1.4 and is treated with more scrutiny here rather than less:

- `sort-dropbox`'s new pattern-matching path was unit-tested against a realistic simulated project lifecycle in one continuous session: project-init documents (5 files, all fixed-name rules), a full chunk drop (chunk plan, execution manifest, two contracts, all pattern-matched), a contract report and chunk report drop (pattern-matched), and an appended `entries` mapping for a dataset file (exact-match, verified to take priority over any rule). All landed at the expected path in one pass with zero manual intervention.
- The chunk-number zero-padding fix was caught *by this testing*, not anticipated in design: an early version of the substitution logic let `chunk1.md` and `C1-01_contract.md` resolve to `chunk1/` and `chunk01/` respectively — two different directories for the same chunk. Padding only capture group 1 (the convention-defined chunk-number position) closes this without renaming contract sequence numbers, which don't carry the same directory-identity risk.
- `bootstrap.sh`'s manifest seeding was caught failing on first attempt for an unrelated reason: an inline YAML comment on one `copy_factory_files` entry was parsed as part of the filename by the script's existing line-based parser, because every other entry in the file put its comment on a preceding line rather than trailing the value — a convention this file's own earlier entries already established and this draft briefly violated. Fixed and re-verified with a full bootstrap dry run against a throwaway local repo.
- What is *not* evidenced: real multi-session use of the trigger-phrase recognition itself (whether "check the mailbox" and its variants are reliably recognized across an actual multi-day, multi-chunk project) and real use of the naming convention by an Architect session that wasn't specifically told to follow it moment-to-moment. Both are design-reviewed and internally consistent, not field-proven.

### Notes

This is the first release since v1.0.1 that the Human explicitly authorized as an architectural change rather than a patch-shaped fix, and it is treated that way in scope: this is why it is versioned 1.2.0 rather than 1.1.5. The stated goal throughout — automation and reduced friction for the Human, with **no compromise to Factory performance or results** — was treated as a hard constraint on the *implementation*, not just the framing: nothing in Phases 1–4, Risk Tier assignment, Verification Scripts, Gatekeeper's existing checks, or the Self Review ceiling was loosened, shortened, or made optional anywhere in this release. Every rule that existed in the five deleted files exists in the two that replace them; what changed is discovery and invocation, not obligation.
---

## v1.2.1

Release Date

2026-07-24

### Added

- `TAKE_THIS/` — a gitignored outbox, the reverse direction of `DROP_HERE/`. Bootstrapped idempotently alongside it.
- `gatekeeper.py stage-takethis --chunk chunkNN` — copies a completed chunk's `chunk_report.md` and every `contract_report.md` into `TAKE_THIS/`, renamed flat (`chunkNN_report.md`, `C{NN}-{seq}_contract_report.md`) reusing the same naming convention `dropbox_manifest.json` already uses on the way in. Always a copy; the permanent record under `project/chunks/` is never touched.
- `gatekeeper.py clear-takethis` — empties `TAKE_THIS/`. Self-healing (creates the directory if missing). Never touches `project/`.
- `gemini_spec.md`'s Mailbox Protocol: `clear-takethis` runs automatically as the first step of the "chunk N is here, do it" trigger — deliberately not the generic "check the mailbox" trigger, which is also used mid-chunk for things like dataset drops where clearing would discard reports the Human hasn't grabbed yet.
- `factory_spec.md`'s TAKE_THIS Specification section, paired with the existing Dropbox Specification.

### Fixed

- `gemini_spec.md`'s Mailbox Protocol had a stale cross-reference: the "compile the chunk report" trigger pointed at "§8 below" when the actual Chunk Report Compilation section is §9 (§8 is the Contract Report format). Caught and fixed while editing this exact area for TAKE_THIS, unrelated to this release's actual ask.

### Evidence

No completed-project evidence, same disclosed gap as every release since v1.0.1. `stage-takethis`/`clear-takethis` were unit-tested against a realistic synthetic 3-contract chunk: staged, content-diffed against originals (byte-for-byte match confirmed), cleared, originals confirmed to survive the clear untouched, plus edge cases (clearing an already-empty folder, clearing a folder that doesn't exist yet, staging a chunk with no `chunk_report.md` yet — correctly errors rather than guessing). A full `bootstrap.sh` dry run and a second idempotent rerun both confirmed clean `TAKE_THIS/` creation and gitignore handling with no duplication.

### Notes

Same scope discipline as v1.1.3: nothing here touches verification, Risk Tier routing, or the Phase 1–4 pipeline. Convenience-layer tooling for the Human-facing hand-off only, addressing a friction point raised directly from real (manual) use of the Factory: hunting through nested `project/chunks/chunkNN/reports/` directories by hand after every chunk.

---

## v1.3.0

Release Date

2026-07-26

### Added

- `gatekeeper.py materialize --contract {{ID}}` — deterministically extracts `<!-- MATERIALIZE: path --> `-tagged code blocks from a contract markdown file and writes them to their declared destination, byte-for-byte. Exists specifically to close the highest-severity finding from the Factory's first completed-project test (RateLimiter, see Evidence): the Architect embedding High-tier source in a contract and the Implementation Engineer previously having no way to place it on disk except manual transcription — exactly the kind of interpretive step EP-002/C07 says should be mechanical wherever possible.
- Contract Specification additions (`factory_spec.md`): **Verification Parameters** (contracts asserting a formal/formula-based proof must pin exact numeric parameters, not just the formula and scale); **Adversarial Verification for Concurrency** (a `High` tier contract touching shared mutable state must specify an adversarial/boundary-condition test in its own Verification Scripts, not leave it for Chunk Review to construct after the fact); **Traces To** (a light, optional-but-recommended field linking a contract to the `FR-XXX`/`INV-XXX` IDs it implements or upholds); a proper **Frozen Files** subsection (previously only a field name in a list, never elaborated).
- **Architect-side logging requirements**: Claude must append its own `telemetry.jsonl` entry when it completes a `High` tier contract directly (the schema already supported `implementation_owner: architect`; nothing was appending to it in practice), and `decision_log.md`'s scope is explicitly extended to cover Claude's own significant Chunk Planning/Review decisions, not only the Implementation Engineer's.
- `project/technical_debt.md` — a lightweight, append-only, persistent register (ID, Description, Reason Accepted, Introduced In, Resolution Status) for debt knowingly deferred rather than fixed, populated by Claude at Chunk Review. Distinct from a contract report's Remaining Risks section, which is a point-in-time snapshot easy to lose track of across many chunks.
- `project_knowledge.md`'s Assumptions section is now explicitly documented as living/append-only across every chunk, not written once at Project Initialization and left static.
- `bootstrap.sh` auto-detects a non-interactive `stdin` (`[ ! -t 0 ]`) and proceeds automatically instead of hanging at the confirmation prompt — surfaced by a real autonomous-agent bootstrap run hanging with no TTY to read from. Announced explicitly in the script's own output, never silent. `FACTORY_BOOTSTRAP_YES=1` still works exactly as before.
- Four **PROPOSED** Dynamic Rules (`dynamic_rules.md` D-002 through D-005) — the Factory's first Dynamic Rule candidates ever produced from real project evidence rather than design review alone. Filed `PROPOSED`, not `ACTIVE`, per the Promotion Requirements' "observed in multiple situations" bar, which one project does not clear.

### Fixed

- `gatekeeper.py check --contract ... --manifest ...`: `required_reports` entries from the manifest are bare filenames (e.g. `contract_report.md`), not full paths — they were being resolved relative to the current working directory instead of the actual filed location (`project/chunks/chunkNN/reports/{contract_id}/`), producing real false missing-report failures. A bare filename now resolves against that standard location; an entry that already contains a path separator is left as given, for backward compatibility with anything that specified one deliberately.
- `gatekeeper.py`'s own module docstring had drifted: its STATUS line and Usage section still described v1.2.1's command set after `materialize` and the `check` fix were added. Caught during this release's own consistency pass, not by external report.

### Evidence

**This is the first Factory release with real completed-project evidence behind it.** Every release since v1.0.1 has disclosed the same gap — no project had been carried through the Factory end to end. That changed: RateLimiter, a deliberate 2-chunk C++17 mechanics test, ran start to finish (bootstrap → project init → 2 chunks, including one full chunk revert → Chunk Review × 2 → Human Action item on real hardware), independently verified by the Architect at each Chunk Review (hash reproduction, test re-execution with both identical and deliberately different parameters, an adversarial concurrency test constructed from scratch). Every addition in this release traces to a specific, named finding from that project, not a hypothetical:

- `materialize` and the loose-source-never-in-dropbox principle (D-002): the Architect dropped two loose implementation files into `DROP_HERE/`; neither matched a dropbox rule (by design); the Architect's first fix attempt (patching `dropbox_manifest.json` to accept them) was itself wrong and required Human correction; the project needed a full Chunk 1 revert.
- Parameter pinning (D-003): a formal-proof contract's Verification Scripts used unpinned bucket parameters; independent re-verification at Chunk Review used different numbers and both passed, confirming the formula generalizes but that two "PASS" runs weren't bit-for-bit reproducible against each other.
- Adversarial concurrency testing (D-004): a `High` tier contract's own smoke evidence proved no crash under loose contention but never constructed the maximally adversarial single-token race; that test had to be built from scratch at Chunk Review.
- Architect telemetry (D-005): `telemetry.jsonl` contained zero events for the one Architect-implemented `High` tier contract in the project — every event carried the Implementation Engineer's `model_id` specifically.
- The `materialize` mechanism itself and the `check` path fix were unit-tested this session: multi-file extraction from a realistic contract mimicking the actual RateLimiter embedding scenario, overwrite protection, `--force`, unpadded contract ID normalization, missing-contract handling, and no-tags handling all behave as documented; the `check` fix was verified end-to-end against a real manifest/report pair reproducing the exact false-failure shape reported.
- What is *not* yet evidenced: none of this release's own additions (materialize, parameter pinning, the adversarial-test requirement, Architect logging, `technical_debt.md`) have themselves been exercised on a second project. They are reasoned directly from RateLimiter's evidence, not yet confirmed to generalize.

### Notes

A companion document (ChatGPT's independent analysis of the RateLimiter retrospective) proposed a substantially larger set of changes than what shipped here — numeric confidence scores, a full source→contract→requirement→ADR traceability chain, per-phase telemetry richness, an RFC-style Dynamic Rule promotion process, risk burn-down tracking, and a separate ADR document type. Each was evaluated on its merits and most were declined, not accepted wholesale, per explicit Human instruction to apply judgment rather than defer to either source uncritically:

- Numeric confidence scores were rejected as unfalsifiable AI self-assessment theater, contrary to C01/EP-002 — the existing `COMPLETE — FLAGGED` status plus a mandatory, specific Remaining Risks section already serves the underlying need with grounded prose rather than fabricated precision.
- The full traceability chain and rich per-phase telemetry were judged oversized relative to demonstrated need — a light `Traces To` field and the one real, evidenced telemetry gap (Architect logging) were implemented instead; per the Factory's own Design Philosophy, a new artifact needs a real prevented failure, not a hypothetical one.
- An RFC-style Dynamic Rule promotion process was declined because `dynamic_rules.md` already has a fully specified Promotion Pipeline; the recommendation appears to have been made without visibility into that file.
- Risk burn-down counting was declined as process theater with no demonstrated failure it prevents; the existing named, specific Outstanding Risks section already conveys the same information without fake quantification.
- A separate ADR document type was declined in favor of extending `decision_log.md`'s existing scope to cover Architect decisions too — one running record is more useful than two that might drift apart.

This release is versioned 1.3.0 (Minor), not a patch, because — unlike every prior release — it now genuinely satisfies the Minor Release Requirements in full: at least one completed project, measurable evidence, retrospective review, and backward compatibility (confirmed: every addition here is additive to existing contracts/projects, nothing already written is invalidated).

---

## v1.3.1

Release Date

2026-07-26

### Added

- Two more **PROPOSED** Dynamic Rules (`dynamic_rules.md` D-006, D-007), from a second completed project (TeamNotes — a full-stack Express/React/Docker/CI validation run, deliberately scoped via a third-party recommendation to stress engineering concerns RateLimiter's single-header C++ library never touched: multi-file behavioral Frozen Files, a security-flavored `High` tier contract distinct from RateLimiter's concurrency-flavored one, documentation-drift risk, and deployment configuration).
- `factory_spec.md`'s Frozen Files section confirms, explicitly, that a Frozen File set spanning multiple files representing one behavioral contract (not just a single header) is a validated, supported pattern — TeamNotes's `INV-004` (an API surface spanning several route-handler files) is the first real test of this and held with zero hash drift across the chunk boundary.
- **Doc Sync as a named, reusable invariant pattern**: `ClaudeInitialization.md`'s `invariants.md` guidance now explicitly names this pattern (mechanically extract real routes/behavior from source, diff against documented claims) as worth considering for any project with user-facing documentation making specific claims — TeamNotes's `INV-005` is its first validated instance (7/7 exact route match, full comparison table).
- Chunk Review guidance broadened: raw-artifact requests now explicitly extend to deployment/config files (`docker-compose.yml`, Dockerfiles, CI configs) regardless of Risk Tier — these can't be verified by reading a report claiming PASS, and a logical review can catch real defects a script wouldn't (TeamNotes: a deprecated Docker Compose `version` key, a genuine if minor finding, visible in the Implementation Engineer's own terminal output). Also broadened to explicitly include every file materially responsible for an invariant a `Traces To` field points at, not only whichever files the Human happened to think to provide.
- Chunk Review guidance on diffing: comparisons must be made against an exact retained copy (MATERIALIZE-tagged content or an explicitly saved verbatim copy) — never a version reconstructed by retyping from memory. TeamNotes surfaced a real, if caught-in-session, false-positive: the Architect's own diff process briefly flagged a mismatch that was actually the Architect's transcription error while reconstructing a comparison baseline from memory, not any real drift in the Implementation Engineer's work.

### Fixed

- `ClaudeInitialization.md`'s `AI_Note.md` guidance now states explicitly that the filename is fixed (`AI_Note.md`, never chunk-suffixed) and that it is one single, permanent, append-only file for the whole project. TeamNotes produced `AI_Note_chunk01.md` instead, which sat unfiled in `DROP_HERE/` through the next chunk's mailbox sort — confirmed this was not a dropbox coverage gap (the exact-name rule for `AI_Note.md` was already correctly seeded by `bootstrap.sh` since v1.2.0) but purely an Architect filename-discipline error, so the fix is documentation placed at the exact point the mistake would be made, not a change to dropbox matching behavior.

### Evidence

Second completed project, deliberately chosen to differ in shape from the first rather than repeat it — per the Human's own selection criteria (shared verbatim in the source retrospective), RateLimiter validated Factory *mechanics* while TeamNotes was scoped specifically to validate whether those mechanics *generalize* to different engineering concerns: a second Risk Tier category (security/auth, not concurrency), multi-file Frozen Files, documentation sync, deployment config, and frontend/backend coordination. Findings are additive to, not a repeat of, RateLimiter's — every RateLimiter-era fix (materialize, High-tier report completeness, Architect telemetry) was reported as applied successfully from the start in TeamNotes, with no recurrence of any RateLimiter-era failure. The two new findings (`AI_Note.md` filename drift, memory-reconstruction diffing risk) are both first occurrences, filed `PROPOSED` per the same single-occurrence discipline as D-002 through D-005 — two projects' worth of evidence exists for the Factory as a whole now, but each individual rule still only has one occurrence behind it.

### Notes

No `gatekeeper.py` logic changed in this release — both fixes are documentation/guidance placed precisely where each mistake actually occurred, since both were Architect-discipline gaps rather than tooling gaps (confirmed for `AI_Note.md` by checking that its dropbox rule was already correctly seeded). This keeps the same scope discipline as v1.2.1/v1.3.0: nothing here touches verification rigor, Risk Tier routing, or the Phase 1–4 pipeline.

---

## v1.3.2

Release Date

2026-07-30

### Added

- **Project Repository Isolation**: `project/` is now its own independent, nested git repository, initialized idempotently by `bootstrap.sh` (`git init` inside `project/`, only if `project/.git` doesn't already exist). It remains gitignored from the outer repository — by explicit, deliberate Human requirement, not oversight — but now has complete, real, diffable git history of its own, scoped entirely to a repository nobody outside the project ever has reason to open.
- `gatekeeper.py commit-project [--message ...]` — the deterministic commit operation for `project/`'s nested repository (`git -C project add -A && git -C project commit`). Safe to call routinely; reports "nothing to commit" and exits cleanly rather than erroring when there's nothing staged, since that's an expected, common outcome for an operation meant to run after every contract and every chunk report compilation.
- `gemini_spec.md`'s per-contract routine (§8) and Chunk Report Compilation (§9) both now call `commit-project` at their natural completion points.
- `ClaudeInitialization.md` §3a, "What these rules are for — and what they are not": an explicit statement that the density of "never/must/violation" language throughout the Constitution and this file governs honesty and evidence, never length, depth, or creative range — and that no mechanism in this Factory penalizes thoroughness. Added directly in response to a stated Human concern that a capable Architect might read the ruleset's tone as license to write less, defensively, even with no actual rule requiring it.
- `ClaudeInitialization.md` §5b: explicit "reason before you structure" guidance for contract generation — think through the actual design first, with no reference to Contract Specification's field list, then organize into required fields as a distinct second pass. Forcing template compliance during the same pass as the underlying reasoning measurably costs depth; this was already true before this release, just never stated.
- `ClaudeInitialization.md` §5c: a Quality-axis Chunk Review check, distinct from and additional to the existing Compliance checks — did this contract's report actually rise to the difficulty of the work, or does it just technically satisfy every required field? Includes generating 2–4 adversarial scenarios for the component under review *before* reading the Implementation Engineer's own Predicted Failure Modes, specifically to avoid anchoring on what they already thought of.

### Changed

- `gatekeeper.py check`'s Repository Integrity check now verifies the outer repository *and* the nested `project/` repository independently (via `git -C project status --porcelain` rather than assuming a single repository root tied to the process's current directory). Either root being dirty fails the check, with the specific root named in the failure output.
- `SNAPSHOT_DIR` relocated from the repo-root `.gatekeeper/snapshots/` to `project/.gatekeeper/snapshots/`, inheriting `project/`'s nested-repo isolation and `commit-project` history automatically, with no new git machinery. Reads check the new location first and fall back to the pre-v1.3.2 repo-root location if a snapshot isn't found there — read-compatibility only, not an automatic migration, since moving a project's existing files is a decision worth the Human/Architect seeing happen rather than something silent.

### Fixed

- `project/` had zero git history at all prior to this release — a real defect, not the intended behavior even under the secrecy requirement that motivated gitignoring it. It was discovered when a Chunk Review tried to independently verify one specific file's edit history (`git log -p`) and got nothing back, for a reason that had nothing to do with the specific question being investigated: the entire directory had simply never been tracked, in any commit, since the Factory's original design. This release restores real history going forward without giving up the secrecy property that caused the directory to be gitignored in the first place.
- `.gatekeeper/snapshots/*.json` was tracked in the outer repository's history the entire time, in every project ever bootstrapped — never gitignored, never isolated, overlooked when Project Repository Isolation first shipped in this same release. A distinctively-named, structured artifact (`.gatekeeper/snapshots/C01-02.json`) sitting in the outer repo's history is exactly the kind of narrower but real fingerprint the rest of this release exists to eliminate. The fix folds it into `project/`'s existing nested repo rather than gitignoring it separately and reintroducing the original history-loss bug for a second directory.

### Evidence

This originates from a real Chunk Review finding (a Frozen File appeared to have been edited mid-contract with no way to independently confirm what changed), followed by the Human's own explicit design requirement once the root cause was traced to `project/`'s `.gitignore` entry. Two architectural alternatives were seriously evaluated and rejected before this one:

- **A separate "Company Repository" + private "Workspace" + explicit synchronization pipeline** (proposed by a third-party AI consultation, then independently reconsidered by the same source after critique): rejected because "sync when work is approved" is an unavoidable judgment call — either the Human manually triggers it (friction, against the Human's explicit "zero friction, fully autonomous" requirement for this change) or some AI role decides autonomously when work is "approved enough" to expose externally, which is a genuinely fuzzy decision nothing in this Factory currently makes, and analogous to exactly the kind of unnecessary AI decision point EP-001 says to eliminate wherever possible. It also targeted a problem this Factory didn't actually have: `source/` (the real deliverable) was never gitignored or fingerprinted in the first place, only `project/` (the metadata) was — meaning the elaborate clone/sync machinery was solving for an end state (a repo with source code only) that a much smaller fix already reaches.
- **A distinct "Factory" git identity for the nested repository's commits** (an earlier draft of this same fix): rejected on inspection, before shipping, as counterproductive — a commit author of `Software Factory <factory@local>` would be a bigger giveaway than the directory's mere existence, if the nested repository were ever seen by anyone. The nested repository uses the Human's own ordinary global git identity instead, with no override.

Mechanically tested this session: outer `git status --porcelain` confirmed to never see into `project/` at all, before or after the fix (isolation was never actually broken by this change — it was already correct; only the *history* half of the equation was missing). `commit-project` tested for a real commit, a clean no-op on a second call with nothing changed, and correct behavior when `project/.git` doesn't exist yet. `gatekeeper.py check`'s Repository Integrity tested against all four combinations of {outer clean/dirty} × {nested clean/dirty}, correctly reporting PASS/FAIL independently for each root. Full `bootstrap.sh` dry run and a second idempotent rerun both confirmed correct, non-disruptive nested-repository initialization. Separately, `.gatekeeper/`'s relocation was tested for a fresh project (writes and reads correctly against the new `project/.gatekeeper/snapshots/` location) and for backward compatibility (a snapshot manually placed at the pre-v1.3.2 repo-root location was correctly found and used by `check`, without needing manual migration). A full end-to-end run — bootstrap, snapshot, `commit-project`, `check` — confirmed the outer repository's tracked files never include `project/` or `.gatekeeper/` in any form.

A third proposal — a genuine architectural fork of `constitution.md` into separate per-role documents (`architect_constitution.md` / `implementation_constitution.md`, or a `factory/core/` + `factory/architect/` + `factory/implementation/` directory restructuring), raised across multiple rounds of third-party consultation — was considered and rejected for this release. Direct inspection of `constitution.md` found no length, brevity, or minimalism constraint anywhere in the text; the Human's own concrete example (contracts already run 500–600 honestly-detailed lines under the current, unforked rules) is evidence against the premise that these documents currently suppress depth, not for it. The rules that read as most restrictive (C01 fabrication, evidence handling, repository hygiene) are genuinely universal — a more capable, more creative Architect has *more* surface area for confident, well-formatted, fabricated reasoning to slip through, not less, making these rules more relevant to the Architect role, not less. A fork was already rejected once earlier in this same version's own development (`decision_log.md` was extended to cover Architect decisions instead of building a parallel ADR-style document, for the identical reason: one shared record beats two that can silently drift) — forking the Constitution now would contradict that precedent for a problem that direct inspection didn't confirm exists. The addressable part of the underlying concern (tone, not architecture) is handled directly in this release's `ClaudeInitialization.md` additions instead.

### Notes

This release directly overturns something this Factory itself had carried unquestioned since before this Architect ever touched it: `bootstrap_manifest.yaml`'s original `gitignore.append_if_missing` list included `project/` from the very first version, apparently by analogy to `factory/` (correctly gitignored, since it's regenerable infrastructure cloned in from elsewhere) — except `project/` is the opposite case, a project's own unique intellectual output, and analogy was the wrong basis for that decision. Neither of the two prior completed-project retrospectives (RateLimiter, TeamNotes) surfaced this, because neither one happened to try independently verifying a specific `project/`-scoped file's git history the way this Chunk Review did — worth noting as a small, separate lesson: some defects only surface under exactly the right kind of scrutiny, and their absence from two prior thorough reviews isn't evidence they don't exist.

---

## v1.3.3

Release Date

2026-08-01

### Added

- `ClaudeInitialization.md` §5a: a six-check founding-artifacts cross-check table, replacing the prior general "check for contradictions" instruction with specific document-pair checks (requirement-to-component mapping, success-criteria achievability, invariant-to-component grounding, component-to-chunk coverage, invariant-to-assumption contingency, cross-chunk dependency validity).
- `ClaudeInitialization.md` §5b: a Risk Tier tie-breaker question for contracts that don't obviously fit Low/Medium/High on inspection — what's the worst case if this is subtly wrong, and could a downstream contract's own verification plausibly catch that failure on its own. Deliberately scoped as a tie-breaker for ambiguous cases only, not a mandatory written procedure for every contract — a broader, always-mandatory version of this was considered and rejected as unnecessary overhead for the (usually large) majority of contracts that already fit a tier cleanly on inspection.
- `ClaudeInitialization.md` §5a/§9: a mandatory pass, at Project Initialization, to resolve every `Risk Tier: High` contract the roadmap will eventually need — embedded (full implementation written now) or explicitly scheduled, never left as a bare `Implementation Owner: Architect` label. Filed as `dynamic_rules.md` D-008, `PROPOSED`.
- `ClaudeInitialization.md` §5b/§5c/§9: Evidence Tiers (T0–T3) — an optional tag on Definition of Done claims describing how a claim was actually verified (asserted / self-attested / independently reproduced / adversarially tested), with minimum tiers by Risk Tier. Filed as `dynamic_rules.md` D-009, `PROPOSED`.
- `ClaudeInitialization.md` §5c: explicit `BLOCKED (architectural)` handling — when Gemini's execution concludes a contract can't be satisfied as written because an `architecture.md`/`invariants.md` assumption turned out wrong, this section now tells the Architect exactly what to do: review, confirm or reject the amendment, revise with a preserved dated history (never overwritten), re-split only affected contracts, log the decision. This restates `factory_spec.md`'s existing Architecture Amendment section (unchanged since v1.1.0) — the requirement already existed, but `ClaudeInitialization.md` never actually told the Architect what to do when it fires.
- `ClaudeInitialization.md` §5b: an explicit reminder that the Architect's own significant Chunk Planning/Review decisions belong in `decision_log.md` too — the same file Gemini uses, not a separate record. This restates `factory_spec.md`'s existing Evolution Specification (extended to cover Architect decisions in v1.3.0) — again, the requirement already existed; this file never surfaced it.
- `ClaudeInitialization.md` §5c: an explicit Allowed Files check in the Chunk Review checklist — confirm a contract's actual diff touches only its declared Allowed Files and leaves every Frozen File untouched. Closes a real, disclosed gap: `gatekeeper_spec.md`'s own Implementation Status lists Allowed File Validation as not yet implemented in `gatekeeper.py`, meaning the Architect's own inspection at Chunk Review is currently the only check — independent or otherwise — that exists for this at all.
- `dynamic_rules.md` D-008 and D-009 (see above), both `PROPOSED` with explicitly zero supporting occurrences from this Factory's own tracked project history — the weakest evidence basis of any Dynamic Rule filed so far, and disclosed as such rather than presented alongside D-002–D-007 as if equally evidenced.

### Fixed

- Two new PROPOSED Dynamic Rules (D-008, D-009) were written up in this release, but the practices they describe (the High Risk pre-resolution pass, Evidence Tiers) had already been merged into `ClaudeInitialization.md` in the prior session without going through `dynamic_rules.md` first — a real process gap in how this Architect handled that merge, caught during a later audit of the same content, not during the original merge. Every other new-and-unpiloted addition since v1.3.0 got a Dynamic Rule entry at the time it was added; these two didn't, until this release retroactively closed that gap.
- `VERSION` and `ClaudeInitialization.md`'s own internal version header had drifted out of sync (`VERSION` read `1.3.2` while `ClaudeInitialization.md` already read `1.3.3`) — the prior session's merge updated the file's content and its own header but never completed the actual release: no CHANGELOG entry, no cross-file version sync, no Dynamic Rule filing. This release completes that release properly rather than leaving the drift in place.

### Evidence

This release's own originating claim was independently, adversarially checked before any of it was accepted — worth recording in detail, since the checking process is itself the evidence this section exists to disclose. A separate audit pass raised six specific claims about `ClaudeInitialization.md`'s content, categorized by evidence status; each was verified against the actual files on disk rather than accepted on the strength of the categorization alone:

- The claim that `decision_log.md`'s Architect-coverage and `factory_spec.md`'s Architecture Amendment section already existed and were merely unsurfaced — confirmed accurate by direct inspection (`factory_spec.md` line 605 area / Evolution Specification, and the dedicated Architecture Amendment section respectively).
- The claim that Allowed File Validation is disclosed as unimplemented in `gatekeeper_spec.md` and was never checked for in `ClaudeInitialization.md`'s Chunk Review list — confirmed accurate by direct inspection of both files; genuinely absent, now added.
- The claim that `role_bindings.yaml` is referenced but doesn't exist as real infrastructure — confirmed accurate: absent from `bootstrap_manifest.yaml`'s `copy_factory_files`/`generated_files`, absent from anything `gatekeeper.py` reads. Disclosed in `ClaudeInitialization.md` §9 as a known gap rather than built preemptively, since nothing currently consumes it programmatically.
- **The claim that Project Repository Isolation was "a real feature from a parallel lineage of this Factory, not something in your current v1.3.1" was checked and found inaccurate.** This Architect's own current `factory_spec.md`, `gatekeeper.py`, and `ClaudeInitialization.md` already had this feature, fully shipped as v1.3.2 in an earlier session of this same continuous work — not foreign content requiring a fresh adoption decision. Treated as already-settled rather than re-litigated.
- **A claim made by this Architect itself, in conversation rather than in a shipped file — that the founding-artifacts cross-check table had "dropped two rows" from an earlier draft and was restored as a fix — was checked against the actual file state and found unsupported.** Direct inspection showed the table already had all six rows before the claimed fix; no evidence exists that a four-row version was ever actually in place. This was corrected in conversation at the time it was raised, and is recorded here because the same standard of "verify against the file, not against your own prior confident statement" applies to this Architect's own claims as much as to any external source's.

### Notes

Two things are worth stating plainly about how this release actually came together, since both are examples of the discipline this Factory exists to enforce, applied to its own process rather than to a project built with it. First: a wholesale content merge in a prior session skipped this Factory's own established practice (Dynamic Rule filing for new-and-unpiloted additions) — caught only because a later, separate audit checked the merge against `dynamic_rules.md` rather than assuming the merge was complete because the file read well. Second: over the course of settling exactly what this release should contain, this Architect made and then had to retract a specific, confidently-stated factual claim about file contents that turned out not to hold up under direct inspection — recorded above rather than quietly dropped, because a Factory that only discloses evidence gaps in *others'* proposals while treating its own prior statements as settled fact isn't actually running the same standard both directions.

---

## v1.3.4

Release Date

2026-08-09

### Fixed

- `gatekeeper.py` `parse_contract_status` read past the Final Status section to end-of-file with no upper bound, so a status word appearing later in Remaining Risks or the Plain-Language Summary could be matched instead of the actual Final Status value. The search is now bound to the Final Status section itself — from the `## Final Status` heading up to the next `## ` heading, whichever comes first.
- `gatekeeper.py` `parse_contract_status`'s bare `"COMPLETE"` pattern matched as a raw substring, so it also matched inside `"INCOMPLETE"`. It now matches only as a whole token.
- `gatekeeper.py` `_find_contract_file` already fell back between an as-given and zero-padded contract ID; `cmd_next`'s report-path lookup and `cmd_check`'s `required_reports` path resolution did not, using the caller's contract ID string verbatim with no fallback. The candidate-generation logic is now factored into a shared `_contract_id_candidates` helper used by all three call sites.
- `gatekeeper.py` `check_reports`'s `DEFAULT_REQUIRED_SECTIONS` matched lowercase substrings anywhere in a report's raw text, so a sentence like "no verification was possible" satisfied a required "verification" section. `gatekeeper_spec.md`'s Report Validation has always specified "required section headers present" — this was an under-delivery against the script's own spec, not a new requirement. Required sections are now matched against the report's actual `## `-level headers only.
- `gatekeeper.py` `cmd_sort_dropbox`'s file listing excluded every non-file entry (directories, etc.) from every reported category, including `[UNKNOWN]` — a dropped folder vanished from the output entirely rather than being visible anywhere. Non-file entries are now listed and reported under a new `[SKIPPED - NOT A FILE]` category.
- `gatekeeper.py` `cmd_check`'s composite exit code (`exit_code = exit_code or N`) only ever reflects the first-failing check category — correct and left unchanged, since something may already depend on that exact contract, but the single integer understated a failure spanning more than one category. A `Failure categories: [...]` summary line is now printed whenever more than one category fails, alongside the unchanged exit code.
- `gatekeeper.py` had no validation that it was being run from the repository root — every path in the script is cwd-relative, so running it from the wrong directory silently resolved `DROP_HERE/` etc. to a nonexistent path and produced a generic, misleading error. `main()` now checks for `bootstrap_manifest.yaml` at the top, before any command dispatch, and exits 9 with a specific message if it's missing.

### Documentation

- `gatekeeper_spec.md` Security and Git Validation sections claimed Gatekeeper is "read-only except for generating `gatekeeper_report.md`" and "never performs Git operations" — both false against `commit-project`, `materialize`, `sort-dropbox`, and `clear-takethis`, all of which the same document's own Implementation Status section already discloses. Rewritten to the true scope: read-only with respect to `source/` and contract semantics, with an enumerated list of the mutations `gatekeeper.py` actually performs, all scoped to `project/`, `DROP_HERE/`, and `TAKE_THIS/`; git operations scoped to `project/`'s nested repo only, never the outer repo, never history-rewriting.
- `gatekeeper_spec.md` Outputs section promised a `gatekeeper_report.md` file that is never actually written — the script only prints to stdout. Corrected to describe actual behavior, with the file itself noted as a still-undelivered future target rather than a claimed current one.
- `gatekeeper_spec.md` Inputs section listed `constitution.md`, `factory_spec.md`, and `dynamic_rules.md` as consumed by `gatekeeper.py`; the script never reads any of the three. Removed from the script's Inputs list, with a note that these are read by the Architect and Human as part of the judgement-based portions of the process, not by this script.
- `gatekeeper_spec.md` now discloses the new `self-check` subcommand in its Implementation Status section (see Added, below).
- `factory_spec.md`'s Artifact Lifecycle table listed `telemetry.jsonl`'s producer as `Gemini` only; corrected to `Gemini Claude`, matching the adjacent `decision_log.md` row and the v1.3.0 Architect-logging requirement (D-005) both already apply to.
- `factory_spec.md`'s `telemetry.jsonl` schema is now the sole authoritative schema owner (C29); `gemini_spec.md` §7 references it instead of maintaining its own divergent template. The undefined `approved` field — no type, semantics, or owner anywhere across ten documents — has been removed rather than left in place with no defined meaning. `self_review_attempts`, previously only in `gemini_spec.md`'s template, has been added to `factory_spec.md`'s canonical example so both documents agree.
- `factory.md` §6 and §7 described the Factory "as of v1.2.0," claimed "no project has been completed" and "no rule has been promoted yet" — all false as of two completed projects and eight PROPOSED Dynamic Rules. §7's Gatekeeper capability list omitted `commit-project` (v1.3.2) and the new `self-check` (v1.3.4) entirely. All three sections synced to current state.
- `experiments.yaml`, `metrics.csv`, and `evolution.md` removed from `factory_spec.md`'s Artifact Lifecycle table, Evolution Specification file list and subsections, and from the corresponding repository-shape diagrams in `factory.md` and `ClaudeInitialization.md`: zero writes across two completed real projects (RateLimiter, TeamNotes), failing C46's "must earn its place" test. `decision_log.md` and `telemetry.jsonl` already cover the stated space. `ClaudeInitialization.md`'s Lightweight Chunk Designation description and `gemini_spec.md`'s Metrics Summary template updated to match (the latter now reads from `telemetry.jsonl` instead of the deleted `metrics.csv`).
- `AI_Note.md` has a real, distinct purpose (Claude → Gemini context carryforward) and an already-correct producer/consumer row in the Artifact Lifecycle table; the gap was that `gemini_spec.md` never instructed Gemini to check it. One instruction added to the chunk-start procedure: read `project/AI_Note.md` if present, before Phase 1.
- `dynamic_rules.md`'s worked "Example Rule" (D-001, Status: ACTIVE, Projects: 3) sat as flat text with no distinguishing sub-header in an evidence-only file (per the file's own Purpose statement) — a future deterministic parser greping for `Status` + `ACTIVE`, including this release's own `self-check` naming lint, could ingest it as a real entry. Moved out of `dynamic_rules.md` into `factory_spec.md` as a schema illustration instead.
- `gemini_spec.md` §10 Known Limitations described the pre-TeamNotes evidence state ("none of this release's additions have been exercised on a second project"), contradicted by `CHANGELOG.md`'s own v1.3.1 TeamNotes entry and `ClaudeInitialization.md` §9. Corrected to state plainly what's validated on real projects (v1.3.0's contract mechanics, the full v1.2.x logistics layer) versus what still has zero real-project occurrences (`commit-project`/nested-repo isolation, Evidence Tiers, D-008).
- `factory_spec.md`'s `execution_manifest.yaml` example used unpadded contract IDs (`"C3-01"`, `"C3-02"`), contradicting `ClaudeInitialization.md` §4's own stated convention and setting a pattern a future Architect could copy directly into a real manifest. Corrected to `"C03-01"`/`"C03-02"` throughout, including the `telemetry.jsonl` schema example on the same page.

### Added

- `gatekeeper.py self-check` (v1.3.4) — a new, diagnostic-only subcommand, not a new script (C48: `gatekeeper.py` remains the Factory's single deterministic-enforcement entry point). Runs four diff targets: implemented commands/exit codes vs. `gatekeeper_spec.md`'s claims about them; `factory_spec.md`'s Artifact Lifecycle table vs. whether `gemini_spec.md`/`ClaudeInitialization.md` actually instruct the declared producer to write each artifact; every document's embedded version reference vs. `VERSION`; and worked-example contract IDs vs. the `^C\d{2}-\d{2}$` naming convention. Reports findings as prompts to investigate, never as proven defects, and never modifies any file — always exits 0. Wired into `bootstrap.sh`'s `[8/8] Finalizing` step (never fails bootstrap; a missing `python3` is reported as a skip). `factory/tests/` (new, containing this release's own regression suite) added to `bootstrap_manifest.yaml`'s `copy_factory_files` so the tests travel with the code they cover.
- `dynamic_rules.md` D-010, `PROPOSED`, one occurrence: an evidence claim about the Factory's own validation state must be re-derived from `CHANGELOG.md`'s Evidence sections directly, never accepted from another document's paraphrase of that state, however honest it reads. Root cause: this release's own source Hardening Report inherited `gemini_spec.md` §10's stale self-summary without cross-checking it against the primary evidence record sitting in the same document set.
- `dynamic_rules.md` Candidate Observations Awaiting Evidence — a new table, outside the numbered D-XXX registry, holding well-evidenced findings (INT-2 through INT-8, GOV-1 through GOV-9, and two findings from a second cross-model audit document) that fail the Minor Release bar today, so a future Factory Retrospective (C49) can evaluate them by lookup rather than reconstruction.

### Evidence

Every finding in this release was checked against `gatekeeper.py`'s actual source and the Factory's ten documents directly before being accepted, per a three-way cross-model audit (a first model's Hardening Report, a second model's independent Candidates document, and this Architect's own byte-level audit reconciling both). Each of the seven `Fixed` items ships with a regression test under `factory/tests/test_gatekeeper_v1_3_4.py` reproducing the exact failure mode, written and confirmed failing against the unpatched script before the corresponding fix was written, per this Factory's own stated practice (C14) — ten tests total, all passing against the patched script. `self-check` itself has twelve unit tests under `factory/tests/test_gatekeeper_self_check.py` against synthetic drift fixtures for each of its four diff targets, and was additionally smoke-tested against this release's own actual, real (not synthetic) document set in an isolated sandbox — which caught one genuine gap introduced during this release itself (`self-check` initially undisclosed in its own spec section) before ship, direct evidence the tool does what it claims rather than only what its own test fixtures assume. `self-check`'s evidence posture, stated plainly rather than overclaimed: unit-tested against synthetic drift scenarios and this release's real document set, not yet run against a project's document set produced independently of this audit.

Two items originally proposed by the source audit documents were explicitly investigated and found NOT to be bugs: the em-dash/hyphen pattern pairs in `STATUS_PATTERNS` (real UTF-8 em dashes plus ASCII-hyphen fallbacks — deliberate dual coverage, left untouched) and the "byte-for-byte" language describing `materialize`'s output in most of its documentation (accurate as shorthand; only the specific docstring claim of *zero* added bytes, contradicted by the trailing-newline normalization, was reworded).

### Notes

Every item in this release was checked against the C50 Versioning Policy gate before inclusion: does it require Claude, Gemini, or the Human to do anything procedurally different? Everything that does — a cross-project precedent ledger, an adversarial pre-decision pass, outer-repo commit discipline, a filing log with hashes across the DROP_HERE → project/ handoff, and nine governance-process additions (approval register, revert procedure, resume protocol, model-identity pinning, backup guidance, migration command, a PROVISIONAL pipeline state) — was filed in `dynamic_rules.md`'s new Candidate Observations table instead of smuggled into this patch release, regardless of how well-evidenced the underlying finding was. This release also corrects two things about its own source material rather than accepting them at face value: an implementation-status section believed by one of the source audit documents to already be current was found stale on direct inspection (D-010, above), and two proposed "fixes" were investigated and rejected as not actual bugs (see Evidence, above) — the same standard of verifying against the file rather than against a document's own confident description of itself, applied here to the audit process that produced this very release.

---

## v1.4.0

Release Date

2026-08-11

### Added

- Methodology Adversarial Review (MAR) — mandatory phase between Project Initialization and Chunk 01, performed by a session that did not write the founding artifacts. Seven gates (data authenticity, baseline sufficiency, statistical power, title-claim consistency, venue alignment, assumption stress test, negative result contingency). For projects targeting a peer-reviewed venue, gates 4–7 must be performed by at least one reviewer outside the Architect's own model family — the first time this Factory has required cross-model review anywhere, and a deliberate reversal of a decision `ClaudeInitialization.md` §9 had previously and explicitly left open pending evidence.
- Reality Gate — mandatory phase between data acquisition and model training. Four deterministic property checks (gap statistics, distribution/uniformity, temporal coverage, sensor coverage) against a `project/data_manifest.json` schema, plus a per-channel provenance-chain requirement. Specified with a concrete schema; not implemented in `gatekeeper.py` yet.
- `venue_requirements.md` and `project/key_facts.md` — two new Frozen Files created at Project Initialization for any project targeting a peer-reviewed venue or other external release. Full templates: `venue_requirements_TEMPLATE.md`, `key_facts_TEMPLATE.md`.
- Scientific Claim Tier — new Contract Specification field (T-DESC / T-COMP / T-CAUSAL) tying a claim's strength to its minimum required evidence, including a mandatory declared Stop Condition for any T-CAUSAL claim.
- Scientific Validity Invariant (SVI) category, six invariants, distinct from project invariants (INV-XXX), verified at MAR and Chunk Review.
- Three new mandatory Chunk Review checks: Methodology Drift Check, Baseline Completeness Check, Title-Claim Audit.
- Constitution C51 (Scientific Validity Before Engineering Completion), C52 (External Reference Before Internal Verification), C53 (A Null Or Below-Chance Core Result Is A Stop Condition), and EP-007 (The Factory Verifies Science, Not Just Code).
- `dynamic_rules.md` D-011 through D-018, `PROPOSED`, filed against the GLOF project's actual IEEE TGRS peer review — each rule cites the specific reviewer finding it addresses.
- `gatekeeper.py release-check` (D-017) — new subcommand, implemented and unit-tested. Scans a release-bound artifact (manuscript, `REPRODUCIBILITY.md`) for absolute local-path/machine-identity leaks (hard FAIL, new exit code 10) and for numeric drift against facts declared in advance in `project/key_facts.md` (WARNING — deliberately bounded to declared facts only, since open-ended semantic fact-checking of prose would require AI reasoning Gatekeeper's own Purpose forbids).
- **Post-Chunk-07 amendment, added during the same release cycle before freeze:** Reality Gate verifies data properties, not data provenance — a well-designed simulator passes every property check by construction. Evidenced by a second, distinct incident within the GLOF project rework (Chunk 07): an acquisition script defined `generate_fallback_timeseries`, called when the target API was network-blocked, producing simulated data that passed Reality Gate's full property check set. Caught only by the Architect reading free-text agent output and noticing the word "synthesize." Added to close this specific gap:
  - Constitution C54 (No Silent Data Substitution) — a data acquisition contract producing any value not directly returned by an external observation API is a C01 violation regardless of how realistic it looks, and the only acceptable responses to an unreachable API are retry, `BLOCKED — HUMAN ACTION REQUIRED`, or escalation.
  - `dynamic_rules.md` D-019 through D-023, `PROPOSED`: acquisition provenance manifests (`acquisition_provenance.json`, API-call-level evidence — endpoint, scene counts, HTTP status codes — distinct from and harder to fabricate than `data_manifest.json`'s self-reported per-channel provenance chain), a mandatory connectivity pre-check as the first Implementation Instruction of any contract calling an external API, a new `External Service Dependencies` Contract Specification field, and a Human spot-check protocol comparing 3 random data points against an independent second source.
  - `gatekeeper.py acquisition-audit` (D-022, D-023) — new subcommand, implemented and unit-tested against a synthetic reproduction of the Chunk 07 incident. Scans acquisition scripts for data-generation function definitions (hard FAIL, new exit code 11) and scans scripts/reports for simulation-indicating language (WARNING).

### Documentation

- `gatekeeper_spec.md` Implementation Status, Exit Codes, Inputs, and Security sections updated for `release-check` and `acquisition-audit` — verified clean via `self-check` before this release shipped.
- `factory_spec.md` gained a new Scientific Validity Specification section (MAR, Reality Gate, `acquisition_provenance.json`, External Service Dependencies, Release Artifact Scan, SVI invariants), inserted after Project Initialization; updated Contract Specification, Chunk Review, and Artifact Lifecycle table.
- `ClaudeInitialization.md` §5a, §5b, §5c, §4, and §9 updated for the full Scientific Validity Layer, with care taken not to overclaim: the note in §9 explaining why cross-model review of self-implemented High-tier contracts remains excluded was left standing and explicitly distinguished from MAR's new requirement — GLOF's evidence is about specification review, not implementation review, and settles only the former.
- `gemini_spec.md` updated for `data_manifest.json` production, the Chunk Report's new Scientific Validity Summary section, and version currency. The orphaned "Factory Manager" term (present in this file's header and in one `gatekeeper.py` error message, never defined anywhere in the Ownership Model) was replaced with "Human" in both locations — a small, independent finding from this Factory's original three-way audit, closed opportunistically while this file was already open for other reasons.
- `bootstrap.sh`'s seeded `dropbox_manifest.json` gained fixed-filename rules for all five new artifacts (`venue_requirements.md`, `key_facts.md`, `methodology_adversarial_review.md`, chunk-scoped `data_manifest.json`, chunk-scoped `reality_gate_report.md`), validated as parseable JSON before ship.

### Evidence

Every mechanism in this release traces to a specific, named finding in one of two sources: the GLOF project's actual IEEE TGRS peer review (D-011 through D-018, C51–C53), or Chunk 07 of the same project's rework under the v1.4.0 process itself (D-019 through D-023, C54) — the two are evidenced separately and this release does not conflate them. `release-check` and `acquisition-audit` were each smoke-tested against a synthetic reproduction of the exact incident that motivated them before their formal test suites were written: `release-check` reproduced both the leaked local path and the fatality-count discrepancy from the real review in one run; `acquisition-audit` reproduced the `generate_fallback_timeseries` function and its report's "synthesize" language in one run. Full regression suite: `factory/tests/test_gatekeeper_v1_4_0.py`, 18 tests. Combined with the carried-forward v1.3.4 and self-check suites, 40 tests pass against the patched script.

This release also received an external review during drafting (a second model's gap analysis) which was independently verified rather than accepted at face value: two of its citations (MAST, HippoRAG — from an earlier, related review of the base Factory) were confirmed as real, accurately-characterized published work; a later, separate third-party document claiming deep inspection of this project's actual execution logs was found to cite a `gatekeeper.py` line number that, checked directly, pointed at a code comment describing a bug already fixed in v1.3.4 — that document's verifiable technical claims were rejected, and only its independently-defensible ideas (a data-schema field, folded into `data_manifest.json`) were retained, with sourcing corrected to reflect that they are not evidenced by anything in this project's actual failure record.

### Notes

Classified Minor (v1.4.0), not Major, per C50: every mechanism above is a new capability or gate within the existing chunk/contract execution model and Claude-Architect/Gemini-Implementation-Engineer ownership model — nothing about who decides what has changed. The engineering-hardening backlog from the original three-way Factory audit (Allowed File Validation, cumulative regression, filing-log hashing, approval register, dual-repository commit discipline, crash/resume recovery) is unchanged by this release: nothing in either GLOF evidence source implicates a code-integrity failure, so nothing was pulled forward into this release's scope on the strength of proximity alone. It remains queued in `dynamic_rules.md`'s Candidate Observations table pending its own evidence trigger.

---

## v1.4.1

Release Date

2026-08-11

### Added

- `gatekeeper.py evidence-check` (D-024, D-025, D-027) — new subcommand, implemented and unit-tested. Reads a contract report's structured `## Verdict Cross-Check` block and cross-checks it against the JSON artifact it names: does the report's declared verdict word match the artifact's own value at the named key (D-024), and, if a bounded criterion is declared from a closed set (`count_gte`/`count_lte`/`value_gte`/`value_lte`/`bool_true`/`bool_false` — never a free-form expression, which would require AI reasoning), does the artifact's own number actually entail the stated verdict (D-025). Both are hard failures, new exit code 12. Separately flags any metric in the artifact's `metrics` array sitting on a degenerate boundary (0.0/0.5/1.0, within tolerance) computed on fewer than 30 samples (D-027, new invariant SVI-007) — a warning, not a failure, since a degenerate-looking value may still be genuine and only needs disclosure, not suppression.
- New Contract Specification field, the `## Verdict Cross-Check` block in `contract_report.md` (`verdict_word`/`artifact`/`artifact_key`, plus optional `criterion`/`criterion_field`/`criterion_threshold`), and a new `metrics` array convention (`{name, value, sample_count}`) for JSON evidence artifacts — both required for `evidence-check` to have anything to check. A report without the block gets no automated cross-check at all, silently — this is a declared interface, not an inferred one, the same tradeoff `release-check`'s `key_facts.md` already makes.
- Cross-Contract Metric Supersession Protocol (D-026) — a new Chunk Review check, not a Gatekeeper command: when a contract re-evaluates metrics an earlier contract already reported, the later report must state which contract's numbers it supersedes, why they differ, and which artifact is now authoritative; the earlier report gets an appended (not edited — C30) supersession note. Deliberately left AI-attested rather than automated — reliably detecting "this contract re-evaluates an earlier one" needs more context than a filename/key-name heuristic can safely provide, and a fragile pattern-match here would produce false confidence worse than no check.
- `acquisition_provenance.json`'s schema (v1.4.0) gained a `downloaded_file_manifest` field (file sizes and checksums), the one genuine addition from an independent review that otherwise restated D-019/the existing mechanism without having seen it.

### Fixed

- `gatekeeper.py`'s repo-root check (BUG-7, v1.3.4) looked for `bootstrap_manifest.yaml` at the current working directory. In a real bootstrapped project that file only ever exists at `factory/bootstrap_manifest.yaml` — the check could never have passed in production. Found during this release's own validation pass (`self-check` run against the real, complete document set, not just synthetic fixtures) rather than by any external report. Fixed; regression test added that specifically pins the wrong (bare-root) location as a non-satisfying case so it cannot silently regress back.

### Evidence

Three new findings (D-024, D-025, D-027) trace to a single contract (C08-08) in Chunks 08–09 of the GLOF project rework, discovered after v1.4.0 had already been presented as complete — a distinct evidence-gathering event from both the original IEEE review (v1.4.0's D-011–D-018) and the Chunk 07 incident (v1.4.0's D-019–D-023), which is why this is its own dated release rather than a retroactive edit to v1.4.0's entry. A fourth finding (D-026) traces to the same Chunks 08–09 window but a different contract set (C08-02 through C08-05). `evidence-check` was smoke-tested against a synthetic reproduction of the exact C08-08 incident (verdict-vs-artifact mismatch and logical inconsistency, in one run) before its formal suite was written. Full regression suite: `factory/tests/test_gatekeeper_v1_4_1.py`, 14 tests. Combined with the carried-forward v1.3.4, v1.4.0, and self-check suites, 54 tests pass against the patched script — including a new v1.3.4 test that specifically guards against the BUG-7 repo-root defect this release fixed.

An independent review proposing a fifth item ("CHECK 5: Acquisition Provenance Chain") was checked against what v1.4.0 already shipped rather than accepted as a novel finding: it substantially restated D-019/`acquisition_provenance.json`. Its one non-redundant contribution (file-manifest checksums) was folded into the existing schema; the review is credited for that specific addition, not for the mechanism, which already existed before the review was written.

### Notes

Classified Minor (v1.4.1), consistent with v1.4.0's own precedent (itself consistent with v1.3.2's `commit-project`): a third-digit version bump carrying a new reusable capability, not just a bug fix, is within this Factory's own established pattern when nothing about the ownership or execution model changes. No new Constitution rules — D-024 and D-025 are deterministic enforcement of existing C01 (Never Fabricate) and C08 (Separate Facts From Interpretation), not new principles; D-026 and D-027 are process/invariant additions. This is a meaningful signal on its own: four rounds of post-hoc evidence (original review, Chunk 07, Chunks 08–09, this release's own validation) have not yet required touching the Constitution again after C51–C54 — the foundational layer is holding, and what keeps arriving is new enforcement of principles already stated, which is the cheaper and more targeted kind of change. The engineering-hardening backlog (Allowed File Validation, cumulative regression, filing-log hashing, approval register, dual-repo atomic commit, crash/resume WAL) remains unchanged and unevidenced by anything in this release.

## v1.4.2

Release Date

2026-08-14

### Added

- `gatekeeper.py acquisition-audit`'s structural check broadened (D-028) to also flag a distribution-sampled value (`.normal`/`.uniform`/`.randn`) feeding a metrics function (`roc_auc_score`, `precision_recall_curve`, `roc_curve`, `f1_score`, `average_precision_score`) in the same file — a data-*computation* script fabricating its own intermediate inputs, distinct from D-022's data-*acquisition* trigger but the same underlying concern, so it extends the existing command and exit code (11) rather than adding a new one (C46).
- Four new mechanical guards, direct answers to independent review that report-artifact consistency checking (`evidence-check`) is not independent re-execution or recomputation: `gatekeeper.py verify-contract` (exit 13) re-executes every command a report declares under `## Verification` and checks the real exit code; `gatekeeper.py lint-contract` (exit 14) runs a deterministic AST scan for swallowed exceptions plus the broadened acquisition-audit scan plus frozen-verification-machinery tampering; `gatekeeper.py recompute` (exit 15) runs a report-declared independent script and compares its output to an artifact's claimed value, rejecting a same-hash "independent" script as duplication rather than verification; `gatekeeper.py stamp-report` / `verify-stamps` (exit 16) append a tamper-evident, hash-chained stamp to a contract report containing the real results of the above three plus `git diff` and frozen-file status — content above a stamp is hash-committed, and any later edit to it is detected the next time the report is stamped or checked.
- `snapshot`, `snapshot-chunk`, and `check` now automatically include a fixed path set (`source/tests/**`, `source/scripts/verify_*.py`, `factory/verifiers/**`) in every contract's frozen-file baseline and check, reusing the existing v1.3.2 snapshot/hash infrastructure rather than new machinery (C46) — no contract has to remember to declare its own verification machinery as frozen for it to be protected.
- `self-check`'s `SELF_CHECK_FILES` now includes `gatekeeper.py` and `bootstrap_manifest.yaml`, both of which carry a live version reference (`STATUS (Factory vX.Y.Z)`; `factory.version`) that nothing was monitoring — the same failure class the v1.4.1 fix already named (constitution.md/dynamic_rules.md drifted two release cycles undetected because neither file was in the dict). `_VERSION_HEADER_RE` gained a `^[ \t]*version:` alternative (with `re.MULTILINE`), scoped to a standalone `version:` key so it never matches the sibling `bootstrap_manifest_version:` field, which is independently-versioned by the manifest's own documented design and must not be flagged just because it differs from `VERSION`.
- `factory/tests/test_gatekeeper_v1_4_2.py` (fabrication check, self-check coverage) and `factory/tests/test_gatekeeper_v1_4_2_mechanical_guards.py` (the four new commands) added to `bootstrap_manifest.yaml`'s `copy_factory_files`.

### Fixed

- A defect introduced and caught within this release's own build, disclosed rather than silently corrected (C14/C30): while wiring the new commands into `main()`, an edit orphaned the v1.3.4 BUG-7 repo-root check as unreachable code trailing inside `cmd_verify_stamps`, after that function's own unconditional `sys.exit()` — meaning it was never executed by any code path, including `main()`, which no longer called it at all. Every unit test continued passing throughout, because the unit tests call each `cmd_*` function directly and never exercise `main()`'s dispatch path — only the CLI-level subprocess tests (`TestBug7RepoRootResolution`, `TestReleaseCheckCLIIntegration`) caught it, by design (this is exactly why those tests exist at the subprocess level and not only the unit level). Fixed by moving the check to the top of `main()`, before `parser.parse_args()`, where it originally belonged.
- `CHANGELOG.md`'s own historical test-count claims (v1.3.4: "ten tests total" / "twelve unit tests"; v1.4.1: "14 tests") do not match the actual current count when the real suite is run: `test_gatekeeper_v1_3_4.py` has 11, `test_gatekeeper_self_check.py` has 16, `test_gatekeeper_v1_4_1.py` has 13 (only `test_gatekeeper_v1_4_0.py`'s claimed 18 is exact). Found by actually running the suite rather than trusting the prior entries' stated counts. Not corrected in place (C30 — history is preserved, not edited); recorded here as a new, dated finding. Cause not investigated (test files were plausibly extended after each entry's text was finalized, or the original counts were simply wrong) — worth noting only as a small, ongoing reminder that a written test count is itself an unverified claim until re-run.

### Evidence

D-028's evidence is a fully independent finding, not inherited from either review document: the real `run_bootstrap_ci.py`, `statistical_significance.json`, `evaluation_summary_real_data.json`, and `sentinel_gl_manuscript.md` were inspected directly. The script was executed exactly as written, with its own documented seed (4096) and the artifact's own recorded `n_resamples` (100), against the real evaluation summary — producing a byte-for-byte identical `statistical_significance.json` to the one that shipped and was cited in `claim_evidence_map.json` (CL-16 through CL-21) and in the manuscript's abstract and RQ3 result. Two further, disclosed discrepancies in the same artifact set (an `n_resamples` value of 100 against the script's documented/default protocol and the manuscript's own stated N=2000; all seven methods' 95% CI lower bounds identically exactly 0.5000, independently explained by 5-lake-with-replacement bootstrapping colliding with only one positive-labelled lake — probability (4/5)^5 ≈ 0.328 of excluding it per resample, mechanically flooring the percentile regardless of method quality) are recorded under D-028 rather than treated as separate incidents, since both trace to the same script and the same audit pass.

The four mechanical guards (D-029, D-030, D-031) were not independently evidenced by a second, differently-shaped incident before being built — they were built directly at Human direction, following review of a second document that audited v1.4.1 specifically and whose four claims were checked directly against this file and `gatekeeper_spec.md`'s actual Implementation Status rather than accepted on their own framing; all four checked out as real, non-redundant gaps. This is a departure from this file's usual evidence bar for a Minor-shaped change (C45 ordinarily wants a completed project, not a review document) and is disclosed as a departure, not silently absorbed into the ordinary pattern — see the Third-party review disposition note in `dynamic_rules.md`, and the Human's own stated basis: multi-party confirmation (Human, both review documents, and the GLOF Implementation Engineer session) plus D-028 as this Architect's own independent, reproduced confirmation.

Full regression suite: `factory/tests/test_gatekeeper_v1_4_2.py` (14 tests: 7 self-check coverage, 6 fabrication-check, 1 structural) and `factory/tests/test_gatekeeper_v1_4_2_mechanical_guards.py` (25 tests across verify-contract, lint-contract, recompute, and stamp-report/verify-stamps). Combined with the carried-forward v1.3.4, v1.4.0, v1.4.1, and self-check suites: 96 tests pass against the patched script, actually run, not claimed — see the Fixed section above for exactly why that distinction mattered for this release in particular.

### Notes

Three items proposed by the first review document were evaluated and explicitly NOT implemented as new mechanisms: Scientific Claim Tiers (already shipped, v1.4.0, and stricter than proposed), independent adversarial review for research projects (already shipped, v1.4.0 — this is MAR), and a "smarter" Reality Gate (already specified this way in `venue_requirements_TEMPLATE.md`, not yet `gatekeeper.py`-implemented, already disclosed). Four more were recognized as already sitting in `dynamic_rules.md`'s Candidate Observations table since the v1.3.4 cross-model audit (Allowed File Validation, cumulative regression, negative-case testing, model-identity pinning) and were not re-added. Two were genuinely new and not yet evidenced (statistical-unit/independent-N metadata; an Unproven Assumption Register, filed with an independent critique that it is documentation, not enforcement) — filed to Candidate Observations, not implemented, per C42/C45/EP-005. See `dynamic_rules.md`'s Third-party review disposition note for the full, itemized disposition of both documents.

The second document's literal proposals were not implemented as specified in three places, each a deliberate, disclosed departure: (1) its "machine-generated report section" idea and its "re-execute verification scripts" idea were unified into one mechanism (`stamp-report`) rather than built as two, following the Human's own report-splitting design rather than the document's two-separate-command version — fewer moving parts for the same guarantee. (2) "Freeze all verification machinery automatically" was not built as new code; it is v1.3.2's existing snapshot/hash infrastructure applied to a fixed path set by default (C46). (3) Its `lint-contract` proposal ("detect suspicious patterns... unauthorized fallback behavior... swallowed exceptions") was scoped down to exactly what deterministic AST analysis can honestly prove — a caught exception with no `raise` and no logging call — rather than attempted as general fallback/mock detection, which is not achievable by static pattern matching without an unacceptable false-positive/negative rate; claiming otherwise would itself be the kind of overclaim D-028 was filed to catch. None of the four new commands is claimed to make fabrication "impossible" — each has a stated, honest scope limit in its own `gatekeeper_spec.md` entry and `dynamic_rules.md` rule, on the same terms every other check in this file already carries one.

Classification: this release does not cleanly fit Patch (C50's "no workflow changes" bar is exceeded by four new mandatory-capable commands) or ordinary Minor (C45/C49's usual bar — a completed project and retrospective — was not met before building D-029 through D-031). Recorded honestly as a Minor-shaped release built ahead of its usual evidence bar, at explicit, informed Human direction, rather than force-fit into either label. The engineering-hardening backlog (Allowed File Validation proper — distinct from the frozen-machinery auto-check above — filing-log hashing, approval register, dual-repo atomic commit, crash/resume WAL) remains unchanged and unevidenced by anything in this release.

---

## v1.4.2 — dated amendment

Amendment Date

2026-08-15

Kept at v1.4.2 rather than bumped to v1.4.3, at explicit Human direction, despite C50's own
versioning policy defaulting a workflow-enforcement change of this shape to a version bump. Logged
here as a dated amendment appended below the original entry, which is left completely unedited
above (C30) — not folded backward into it as though v1.4.2 always looked like this.

### Added

- `gatekeeper.py check`'s Mandatory Mechanical Gate (D-032): for a manifest contract whose
  `scientific_claim_tier` (existing v1.4.0 field, not a new taxonomy) is `T-COMP` or `T-CAUSAL`,
  `check` now mechanically requires, before the contract can read PASS: (1) every command in the
  contract's Required Verification Commands present in the report's own declared `## Verification`
  set (D-033); (2) `verify-contract`'s re-execution of every declared command passing; (3)
  `lint-contract` passing; (4) a well-formed `## Recompute Declaration` block present and passing —
  a *missing* block is itself a hard FAIL under this gate specifically, unlike the standalone
  `recompute` subcommand where no block is simply not checked; (5) at least one intact Gatekeeper
  Verification Stamp present on the report. New exit code 17, reported with per-sub-check detail so
  the failing one is named, not just the aggregate. A T-DESC contract, or a contract with no
  declared tier, is unaffected — the section prints `SKIPPED`, never silently omitted.
- New `required_verification_commands` contract field (D-033), read directly from
  `execution_manifest.yaml` alongside `scientific_claim_tier`, `risk_tier`, and `frozen_files` —
  the exact command(s) Claude freezes as required verification at Chunk Planning time, checked
  against what the report actually declares rather than trusting whatever it declares to be the
  right one. Closes the one gap `verify-contract` explicitly disclosed at the original v1.4.2
  release rather than concealed: re-execution proves *a* declared command exited 0, never that it
  was *the* command the contract required.
- `factory/tests/test_gatekeeper_v1_4_2_mandatory_gate.py` (11 tests) added to
  `bootstrap_manifest.yaml`'s `copy_factory_files`.
- `IMPLEMENTED_EXIT_CODES` now includes 17; the module docstring's Exit Codes list and
  `gatekeeper_spec.md`'s Exit Codes table both updated in the same amendment, so `self-check`
  itself does not flag this release's own new exit code as undisclosed — the exact class of gap
  D-032/D-033 exist to close for the *previous* review is not reopened for this one.

### Evidence

Built directly from a second-round independent review of the original v1.4.2 release, checked
against `gemini_spec.md`'s actual Phase 3 text rather than accepted on the review's own framing:
confirmed that Phase 3 Step 2 still only instructs `gatekeeper.py check`, and that
`verify-contract`/`lint-contract`/`recompute`/`stamp-report` are named nowhere in `gemini_spec.md`,
`factory_spec.md`, or `ClaudeInitialization.md`'s operative instructions — meaning a contract could
reach `COMPLETE` having built the v1.4.2 machinery without the ordinary workflow ever actually
exercising it. This exact gap was already self-disclosed in `gatekeeper_spec.md`'s own
Implementation Status section at the original release ("the remaining gap is that neither command
yet verifies a script's declared command matches what `gemini_spec.md` actually required it to
run"), so this amendment closes a gap this file had already named honestly, not one first
identified by the review. Zero real-project occurrences of a tiered contract actually completing
unverified under the pre-amendment workflow — built ahead of the usual evidence bar, at explicit
Human direction, the same disclosed-departure basis the original v1.4.2 release itself used for
D-029 through D-031 (see that entry's own Evidence section above).

Full regression suite: `factory/tests/test_gatekeeper_v1_4_2_mandatory_gate.py` (11 tests) —
T-DESC/untiered contracts confirmed to skip the gate; each of the five sub-checks confirmed to
independently hard-fail (no report, no declared Verification commands, no Recompute Declaration,
no stamp, a Required Verification Command substituted for a different passing command); the
full-pass case confirmed against a report genuinely stamped via the real `stamp-report` code path,
not a hand-authored stamp; exit code 17 confirmed present in `IMPLEMENTED_EXIT_CODES`. Combined
with the original v1.4.2 entry's 96 and all prior carried-forward suites: 107 tests pass against
the amended script, actually run — reconstructed independently from `bootstrap_manifest.yaml`'s
own `copy_factory_files` layout before any file was edited, matching the pre-amendment 96/96
baseline exactly before this amendment's changes were applied.

### Notes

The originating review proposed a "High-risk contract" concept as the gating criterion. Not
adopted as written: Scientific Claim Tier already exists and already is the precise, evidence-
backed concept for "makes a quantitative/comparative claim needing stronger evidence"
(`factory_spec.md`'s T-DESC/T-COMP/T-CAUSAL table, v1.4.0); introducing a second, parallel
taxonomy alongside it would itself be the kind of redundant terminology this file's Third-party
review disposition discipline exists to catch (several first-round-review items were dispositioned
as "already shipped" or "not a new principle" for exactly this reason — see `dynamic_rules.md`).
This is a deliberate, considered substitution made before implementation began, not an oversight
found afterward. See `dynamic_rules.md`'s Third-party review disposition, round two note for the
full basis, and D-032/D-033 for the formal rules.

---

## v2.2.0 — fork back to the two-role architecture

### Context

Between v1.4.2 and this entry, a parallel line (v1.5.0 → v2.0.0 → v2.1.0) grew this Factory in a
different direction: a third AI role (Auditor, alongside Architect and Implementor), and, across
those three releases, roughly thirty distinct registry/manifest file kinds (`requirement_registry`,
`cohort_manifest`, `evidence_ledger`, `assurance_policy`, `agent_registry`, `release_profile`,
`reproducibility_manifest`, `audit_policy`, `audit_report`, and more), three parallel generations of
`schemas/`/`templates/` directories (root, `v2/`, `v2_1/`), and a `gatekeeper.py` command surface
that grew from this file's own 18 commands (through v1.4.2) to roughly 64 across four dispatch
layers (`gatekeeper.py` itself plus `v15_core.py`/`v20_core.py`/`v21_core.py`), with 52 distinct
exit codes.

At the Human's direction, this release does not continue that line. It forks from v1.4.2 instead —
same two AI roles, same chunk/contract structure, same `DROP_HERE`/`TAKE_THIS` mechanics — and
carries forward, in deliberately smaller form, the specific lessons from the v1.5→v2.1 line that
survive a concrete test: does adopting this lesson require the Human to learn, remember, or operate
anything new, or can it be expressed as an extension of a mechanism this Factory already has? This
is not a new principle — it is EP-003 (Complexity Must Earn Its Place) and C46 (Remove Before
Adding), both already in `constitution.md` since early versions, applied to a case where a parallel
line had stopped applying them.

Two concrete, inspectable findings anchor "the v1.5→v2.1 line's complexity growth was not
proportionate to what it caught," rather than asserting this qualitatively:

- `factory_v2_1_0/factory/templates/contract_TEMPLATE.md` and
  `factory_v2_1_0/factory/templates/v2_1/contract_TEMPLATE.md` are byte-identical; the `v2/` and
  root generations of `schemas/audit_report.schema.json` differ from each other, and from the
  `v2_1/` generation, *only* in a hardcoded version-const string. Three maintained generations of
  the same schema/template, carrying zero incremental information beyond that one string, is
  duplication this Factory's own hygiene rules (C46, EP-003) would flag anywhere else.
- `factory_v1_5_0`'s own uploaded TDLCR test project, `project/chunks/chunk06/contracts/
  C06-03_contract.md` ("Pre-Registered Hypothesis Evaluator & Result Registry Compiler," computing
  a Wilcoxon test, a Cliff's delta effect size, and SUPPORTED/FALSIFIED/INCONCLUSIVE verdicts
  feeding `project/result_registry.json` for IEEE publication) declares `Scientific Claim Tier:
  NONE`, with a Verification Scripts entry that only confirms the module imports. This is the exact
  failure mode the v2.0 Design Rationale document names — a scientific claim self-declared as
  general/NONE — sitting undetected in a real project, under a Factory generation that had already
  added a three-role split and dozens of registries without closing this specific hole. More
  process was not, on this evidence, the same thing as more protection.

### Removed (relative to the v1.5→v2.1 line — never present in v1.4.2, so nothing here is a removal
from this file's own direct lineage)

- The Auditor role, and everything scoped to it: agent-separation metadata, "independent model
  family" bookkeeping for routine per-contract/per-chunk review, and the auditor_spec.md onboarding
  document. Its actual function — adversarial reading of raw artifacts, attacking evidence
  lineage — was, in v1.4.2, already the Architect's own job during Chunk Review; this release keeps
  it there rather than reintroducing a name for it (Constitution C55).
- The requirement/cohort/evidence-ledger/assurance-policy/agent-registry/release-profile registry
  family (and the rest of the roughly thirty file kinds named above). Where a piece of what they
  checked was worth keeping, it's kept as an extension of an existing mechanism — see Added, below —
  not as a hand-authored, hand-linked registry file.
- The `v2/`/`v2_1/` schema and template generations and the three-layer `v15_core.py`/
  `v20_core.py`/`v21_core.py` dispatch structure. `gatekeeper.py` in this release is a direct
  extension of the v1.4.2 file (same file, same 18 commands, unchanged), not a rewrite.
- MAR's hard requirement that gates 4–7 be performed by a reviewer outside the Architect's model
  family. With no standing third role, this became either a phantom requirement (nothing enforces
  it) or a reason to invent a role — neither acceptable. See Added, below, for what replaces it.

### Added

- **`gatekeeper.py tier-check` (new command) — Fail-Closed Tier Inference (D-034).** Mechanically
  infers a *minimum* `scientific_claim_tier` from a contract's own Objective/Context/Implementation
  Instructions/Outputs text (STRONG signals — named statistical tests/effect sizes, p-value/CI
  notation, "outperforms," SUPPORTED/FALSIFIED language — infer `T-COMP`; a distinct STRONG signal
  set for robustness/causal/ablation language infers `T-CAUSAL`; a WEAK signal alone, a bare metric
  name, infers `T-DESC`; no signal infers `NONE`) and hard-fails (new exit code 18) if the declared
  tier reads weaker than the inferred minimum. Wired unconditionally into `check`, alongside the
  existing v1.4.2 Mandatory Mechanical Gate, so a mis-declared tier is caught even when nothing else
  about the contract would have triggered T-COMP/T-CAUSAL machinery. Directly closes the C06-03-
  shaped gap above. New Constitution C56.
- **Three WARNING-only heuristics, bundled into the same `tier-check` command rather than three new
  ones (C46):** operation-class conflation (D-035 — an Objective opening with an implementation verb
  alongside empirical-claim language; new Constitution C57); statistical-protocol language (D-036 —
  non-significance-as-equivalence and undeclared-pairing patterns, drawn from the v2.1 Design
  Rationale document's failure table, cited as secondary evidence and honestly distinguished from
  this file's own first-hand GLOF/BPFeat incident trail); and semantic/operator-test presence (D-037
  — a contract naming a recognized mathematical operator, such as a graph Laplacian or a persistent-
  homology filtration, should carry a Verification Script matching a semantic-test naming pattern,
  not only an I/O-shape test; new Constitution C58).
- **`gatekeeper.py release-certify` (new command) — Release Certification (D-038).** Aggregates,
  across every `contract_report.md` under a given chunks directory: Final Status COMPLETE for every
  contract; existing `evidence-check`/`recompute` logic against every report carrying the relevant
  block; `tier-check`'s inference against every locatable contract; and, if given, `acquisition-
  audit` and `release-check`'s scans — into one CERTIFIED/NOT CERTIFIED verdict (new exit code 19),
  written unconditionally to `project/RELEASE_CERTIFICATION.md` naming exactly which categories were
  actually run. Distinct from, and never satisfied merely by, a chunk-level Gatekeeper PASS. Re-runs
  existing checks against existing artifacts — introduces no new registry or schema. New
  Constitution C59.
- **`domain_checklists.md` (new file).** ML-research, topology/geometry, and statistics review
  questions — data leakage, strawman baselines, Laplacian-vs-adjacency, witness-complex correctness,
  persistent-homology filtration monotonicity, boundary-operator nilpotence, batching semantics,
  pairing/effect-size compatibility, non-significance-as-equivalence — plus concrete guidance on
  writing a real semantic/operator test rather than a shape test. Consulted by the Architect at
  Chunk Planning/Review and the Implementor at Phase 1 for any T-COMP/T-CAUSAL contract or one
  `tier-check` flags as touching a named operator. Reference only — nothing in `gatekeeper.py` reads
  it or enforces it.
- **Methodology Adversarial Review, gates 4–7 (`factory_spec.md`'s MAR section, `architect_spec.md`
  §5a) now default to the Architect's own same-session adversarial self-review**, explicitly
  disclosed as such in `methodology_adversarial_review.md` rather than silently presented as
  equivalent to genuine cross-model review. The stronger version — a fresh session with a different
  model, or a human domain collaborator — remains recommended for peer-reviewed-venue projects
  specifically, invoked as an optional, project-specific addition the Human can arrange (never a
  standing role), per new Constitution C55.
- New Constitution Section 8 (C55 through C59) — Two-Role Discipline And Fail-Closed Assurance.
  Honestly dated and scoped as a Human-directed architectural decision confirmed against one
  retroactively-examined project (D-034's C06-03 evidence), not repeated evidence independently
  accumulated across several completed projects under this exact structure — this section's own
  preamble says so explicitly, rather than presenting it as satisfying this Constitution's usual
  Amendment Policy bar by default.
- New Dynamic Rules D-034 through D-038, all filed `PROPOSED` (none promoted — see each rule's own
  Evidence field for exactly what is and isn't backed by this Factory's own first-hand project
  history, distinguished from secondary evidence cited from the v2.1 Design Rationale document).
- `architect_spec.md` and `implementor_spec.md` are now the primary role-document filenames
  (`implementor_spec.md` already was, since v2.0.0; `ClaudeInitialization.md` is renamed to match).
  `ClaudeInitialization.md` and `gemini_spec.md` remain as short pointer files — no operational
  content, just a redirect — so an old bootstrap script or muscle memory pointed at the previous
  filename doesn't hit a missing file. `gatekeeper.py self-check`'s `SELF_CHECK_FILES` now points at
  the new filenames directly.
- `execution_manifest.yaml`'s `contracts` entries gain `scientific_claim_tier` as a documented field
  alongside the existing `risk_tier`/`implementation_owner` (the field already existed as contract-
  file prose since v1.4.0; this is the first release that also expects it in the manifest, mirroring
  how `risk_tier` already appears in both places).
- `factory/tests/test_gatekeeper_v2_2_0.py` (24 tests), added to `bootstrap_manifest.yaml`'s
  `copy_factory_files` — includes a fixture (`REAL_C06_03_EXCERPT`) reproducing the real, uploaded
  C06-03 contract's relevant fields verbatim, so D-034's motivating case is tested directly rather
  than only via a synthetic stand-in for it.

### Removed (in the literal sense of "deleted from this file," distinct from "not carried forward
from the parallel line," above)

- The `role_bindings.yaml` reference `ClaudeInitialization.md`/`gemini_spec.md` carried for two
  release cycles ("if attached / if present"), disclosed each time as aspirational language with no
  actual file, generator, or `gatekeeper.py` reader behind it. Removed outright per C46, rather than
  carried forward as a third release's worth of the same hedge — "Architect (currently Claude)" /
  "Implementor (currently Gemini or any sufficiently capable coding agent)" is now stated plainly in
  both role documents with no phantom config file gestured at.

### Backward compatibility

Every v1.4.2 mechanism — the 18 original `gatekeeper.py` commands, exit codes 0/4/6/8–17, the
Constitution through C54, Dynamic Rules through D-033, the T-DESC/T-COMP/T-CAUSAL Scientific Claim
Tier vocabulary, Reality Gate, MAR-1 through MAR-3, `DROP_HERE`/`TAKE_THIS`/`dropbox_manifest.json`,
every naming convention — carries forward unchanged. A v1.4.2 project's contracts, reports, and
manifests remain valid as-is; the new `scientific_claim_tier` manifest field and `tier-check`/
`release-certify` commands are additive, not a breaking schema change. A project bootstrapped under
v1.4.2 can adopt v2.2.0 by updating `factory/` in place; nothing under `project/` needs migration.

### Evidence

24 new tests (`test_gatekeeper_v2_2_0.py`), covering: `_infer_minimum_scientific_claim_tier`
directly against the real C06-03 excerpt (confirmed to infer `T-COMP`) and against a benign,
zero-signal data-loader contract (confirmed to infer `NONE`, not flagged); the three bundled
WARNING heuristics, each confirmed to fire on a constructed positive case and stay silent on a
matched negative case; `cmd_tier_check`'s exit code end-to-end (18 on the real under-tiered contract,
0 once correctly re-tiered); `check`'s new unconditional tier-inference wiring, confirmed not to
regress any of its pre-existing exit codes; and `cmd_release_certify`'s CERTIFIED/NOT CERTIFIED
verdict across the no-reports, all-complete, single-FLAGGED-contract, and single-under-tiered-
contract cases, including confirming `project/RELEASE_CERTIFICATION.md` is actually written in both
outcomes. Combined with the full carried-forward v1.3.x/v1.4.x suite: 131 tests pass, actually run
against the resulting script, not claimed.

The two-role fork itself, `tier-check`'s existence, and `release-certify`'s existence are Human-
directed design decisions responding to a direct request (restore the v1.4.2 operator experience;
exactly two AI roles; no added complexity; match or exceed v2.1's performance) — not independently
promoted through this file's own Dynamic Rules pipeline (Observation → repeated occurrence →
Evidence collected → Root cause identified → Candidate rule → Applied experimentally → Improvement
confirmed → Human approval → Promotion). Every new Dynamic Rule this release adds is filed
`PROPOSED`, not `ACTIVE`, and each one's Evidence field says plainly whether it rests on this
Factory's own first-hand history (D-034, via the C06-03 artifact), on secondary evidence cited from
the v2.1 Design Rationale document and honestly distinguished as such (D-035, D-036, D-037), or on
neither, being a direct consequence of C51/the Human's explicit instruction rather than a claim to
its own evidentiary basis (D-038, C55).

### Notes

Classification: this release does not fit Patch (C50 — a two-role architectural fork and four new
commands are not "no workflow changes") or ordinary Minor (C45/C49's usual bar — a completed project
and retrospective under the new structure — has not been met; this structure has not yet completed
a project). Recorded honestly as a Major-shaped change in scope (a deliberate fork, not a linear
continuation of either parent line) built and named as directed at explicit, informed Human request,
in the same spirit v1.4.2's own dated amendment and D-029 through D-031 disclosed their own
ahead-of-usual-evidence-bar status rather than force-fitting a label. The version number itself
(`2.2.0`) is the Human's own choice, continuing the numeral the Human already associates with this
lineage's most capable prior state (v2.1.0) rather than reverting to a `1.4.3`/`1.5.0` continuation
of the other parent — a naming decision, not a claim that this release is `v2.1.0` plus a patch.

The `factory_v2.1.0` Design Rationale and Adversarial Regression Cases documents were read in full
and are the source for D-035/D-036/D-037's motivating patterns and for `domain_checklists.md`'s
topology/geometry and statistics content; their proposed *mechanisms* (Evidence Ledger, Cohort
Manifest, Statistical Protocol registry, Agent Registry, Release Profile) were not adopted as
specified, for the reasons given under Context and Removed, above — this is a considered
disposition of that material, not an oversight of it.

