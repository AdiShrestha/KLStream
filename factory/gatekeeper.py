#!/usr/bin/env python3
"""
gatekeeper.py -- AI Software Factory deterministic validation engine.

STATUS (Factory v2.2.0): PARTIAL IMPLEMENTATION.

v2.2.0 forks from v1.4.2 (two AI roles -- Architect, Implementor -- plus
this script, plus the Human; no separate Auditor role) rather than
extending v2.1.0's architecture (three AI roles; per-project registry
schemas for requirements/cohorts/evidence-lineage/agent-separation/etc.).
It carries forward every v1.4.2 mechanism unchanged and adds four new,
deliberately small mechanisms motivated by v2.0/v2.1's genuine findings:
tier-check (fail-closed minimum Scientific Claim Tier inference, D-034),
two WARNING-only heuristic scans bundled into that same command
(operation-class conflation D-035, statistical-protocol language D-036,
semantic/operator-test presence D-037), and release-certify (aggregate
CERTIFIED/NOT CERTIFIED gate, D-038). See CHANGELOG.md's v2.2.0 entry for
the full rationale, including what v2.0/v2.1 mechanisms were deliberately
NOT carried forward and why.

gatekeeper_spec.md describes the full, intended Gatekeeper. This script
implements only the subset listed in that document's "Implementation
Status" section:

    - Frozen File Validation  (sha256 hash comparison against a recorded
      baseline snapshot, stored at project/.gatekeeper/snapshots/ as of
      v1.3.2 -- see Project Repository Isolation)
    - Report Validation       (required report files exist and contain
      required section headers, matched as real "## "-level headings --
      v1.3.4 fix, was previously a raw substring search)
    - Repository Integrity    (clean git working tree -- checks the outer
      repo AND project/'s own nested repo independently, v1.3.2)
    - Execution-order lookup  (deterministic "what's next" from
      execution_manifest.yaml's execution_order + parsed contract_report.md
      statuses -- reads a precomputed order, does not compute dependency
      resolution itself)
    - Dropbox Sort (v1.1.3, revised v1.2.0)  (deterministic filing of files
      dropped in DROP_HERE/ to their manifest-declared destinations, via
      exact-filename entries and regex rules -- reads a mapping already
      committed, does not infer placement itself)
    - TAKE_THIS Staging / Clearing (v1.2.1)  (deterministic copying of a
      completed chunk's self-contained reports out to TAKE_THIS/ for the
      Human to grab, and deterministic clearing of that folder when the
      next chunk starts -- see stage-takethis / clear-takethis below)
    - Materialize (v1.3.0)  (deterministic extraction of MATERIALIZE-tagged
      code blocks from a contract file to their declared destination paths,
      written exactly as captured -- see materialize below)
    - Project Repository Commit (v1.3.2)  (commits everything staged in
      project/'s own nested git repository -- see commit-project below)
    - Self-Check (v1.3.4)  (diagnostic-only: diffs this script's actual
      implemented commands/exit codes/file operations against
      gatekeeper_spec.md's claims, cross-checks the Artifact Lifecycle
      table against operative instructions, checks version-header currency,
      and lints worked-example contract IDs -- never auto-fixes anything;
      see self-check below)
    - Release Check (v1.4.0)  (scans a release-bound artifact -- manuscript,
      REPRODUCIBILITY.md -- for local-path/machine-identity leaks
      [hard FAIL] and key-fact inconsistencies against a project-declared
      project/key_facts.md [WARNING, heuristic] -- see release-check below,
      D-017)
    - Acquisition Audit (v1.4.0, broadened v1.4.2)  (scans data-acquisition
      AND statistical-computation scripts and their contract reports for
      data-generation function definitions [hard FAIL, D-022], distribution-
      sampled values feeding a metrics function [hard FAIL, v1.4.2, D-028],
      and simulation-indicating language [WARNING, heuristic, D-023] -- see
      acquisition-audit below)
    - Evidence Check (v1.4.1)  (cross-checks a contract report's declared
      verdict and pre-registered criterion against its own backing JSON
      artifact [hard FAIL], and flags degenerate metrics computed on too
      few samples [WARNING] -- see evidence-check below, D-024, D-025,
      D-027, SVI-007)
    - Tier Check (v2.2.0)  (fail-closed minimum Scientific Claim Tier
      inference from a contract's own text [hard FAIL if the declared tier
      is weaker than the inferred minimum -- D-034], plus operation-class-
      conflation, statistical-protocol-language, and semantic/operator-
      test-presence heuristics [WARNING only -- D-035, D-036, D-037] -- see
      tier-check below)
    - Release Certify (v2.2.0)  (aggregates contract-completion status,
      evidence/recompute consistency, tier inference, and optionally
      acquisition-audit/release-check across an entire project into one
      CERTIFIED/NOT CERTIFIED verdict, written to
      project/RELEASE_CERTIFICATION.md -- distinct from, and never
      satisfied merely by, a chunk-level PASS -- see release-certify
      below, D-038)

Everything else in gatekeeper_spec.md -- Bootstrap Validation, Manifest
Validation, Contract Validation, Allowed File Validation, Verification
Script Validation, Dynamic Rule Validation, Bootstrap Compliance, Git
Validation beyond a clean-tree check, and the entire Scientific Validity
Layer (Methodology Adversarial Review, Reality Gate, Scientific Claim
Tier enforcement, acquisition_provenance.json revisit-frequency checking)
-- is NOT implemented here. The Scientific Validity Layer is
procedural/AI-attested by design for v1.4.0: MAR gates 4-7 require genuine
judgement (see v1_4_0_scientific_validity_layer.md Part 2) and Reality
Gate's checks require a project-specific data_manifest.json schema that
has not yet been built against a real project's data pipeline -- both are
specified, neither is implemented, and claiming otherwise would itself be
a C01 violation.

Reporting "Gatekeeper PASS" for a check this script does not run is itself
a Constitution C01 violation (fabricated verification). Quote this
script's own "Checks executed" list when reporting a result -- not the
full checklist in gatekeeper_spec.md.

Exit codes (per gatekeeper_spec.md's Exit Codes table):
    0  PASS
    4  Contract Failure                (frozen-file hash mismatch --
       bucketed here because gatekeeper_spec.md's Execution Order does not
       give Frozen File Validation its own code, and frozen files are a
       per-contract concern)
    6  Report Failure                  (required report missing, or
       missing a required section)
    8  Repository Integrity Failure   (dirty working tree)
    9  Unexpected Internal Error
    10 Release Artifact Failure       (v1.4.0 -- a local-path/machine-
       identity leak was found by release-check; key-fact mismatches are
       reported as warnings and do not by themselves produce this code)
    11 Acquisition Audit Failure      (v1.4.0, broadened v1.4.2 -- a
       data-generation function definition in an acquisition script
       (D-022), OR a distribution-sampled value feeding a metrics function
       in a statistical-computation script (v1.4.2, D-028), found by
       acquisition-audit; simulation-indicating text is reported as a
       warning and does not by itself produce this code)
    12 Evidence Inconsistency         (v1.4.1 -- a contract report's
       declared verdict contradicted its own backing JSON artifact, or its
       own declared numbers contradicted its own declared criterion, found
       by evidence-check; degenerate metrics are reported as a warning and
       do not by themselves produce this code)
    13 Verification Command Failure   (v1.4.2 -- a contract report's own
       declared '## Verification' command, independently re-executed by
       verify-contract, exited nonzero)
    14 Contract Lint Failure          (v1.4.2 -- a swallowed exception, an
       acquisition-audit finding, or frozen-verification-machinery
       tampering, found by lint-contract)
    15 Recompute Mismatch             (v1.4.2 -- an independent
       recomputation didn't match its artifact's claimed value, or wasn't
       actually independent (same-hash script), found by recompute)
    16 Stamp Tampering                (v1.4.2 -- content above an existing
       Gatekeeper Verification Stamp was modified after it was issued,
       found by stamp-report or verify-stamps)
    17 Mandatory Mechanical Gate Failure (v1.4.2 amendment, D-032/D-033 --
       a T-COMP/T-CAUSAL contract's `check` did not satisfy all of:
       Required Verification Commands present in the report's declared
       set, verify-contract, lint-contract, a passing Recompute
       Declaration, and an intact Gatekeeper Verification Stamp. Bucketed
       under one code the same way Frozen File Validation is bucketed
       under 4 -- the printed [Mandatory Mechanical Gate] detail lines
       distinguish which of the five sub-checks failed)

Usage
-----
Snapshot every contract's frozen files in a chunk in one command (v1.1.2 --
reads frozen_files straight out of the manifest instead of retyping paths):

    gatekeeper.py snapshot-chunk --manifest project/chunks/chunk03/execution_manifest.yaml

Or snapshot one contract at a time (still available -- e.g. after an
Architecture Amendment re-freezes a single contract mid-chunk):

    gatekeeper.py snapshot --contract C3-01 --frozen src/core/schema.py src/core/types.py

Ask what to work on next (v1.1.2 -- reads execution_order + each contract's
contract_report.md; does not decide anything, just reports what the
manifest and the reports already establish):

    gatekeeper.py next --manifest project/chunks/chunk03/execution_manifest.yaml

File everything currently sitting in DROP_HERE/ to its declared destination
(v1.1.3, revised v1.2.0 -- reads DROP_HERE/dropbox_manifest.json, a
permanent bootstrapped file with pattern rules + project-specific exact
entries; refuses to move anything matching neither rather than guessing):

    gatekeeper.py sort-dropbox

Stage one completed chunk's self-contained reports into TAKE_THIS/ for the
Human to grab (v1.2.1 -- copies every contract_report.md plus chunk_report.md
for the given chunk, renamed flat; never touches or deletes the originals):

    gatekeeper.py stage-takethis --chunk chunk03

Empty TAKE_THIS/ of whatever's currently staged there (v1.2.1 -- run when a
new chunk is starting; self-healing if TAKE_THIS/ doesn't exist yet; never
touches anything under project/, since TAKE_THIS only ever holds copies):

    gatekeeper.py clear-takethis

Extract embedded source from a contract's MATERIALIZE-tagged code blocks
(v1.3.0 -- writes each tagged block to its declared destination path,
byte-for-byte; refuses to overwrite an existing file without --force):

    gatekeeper.py materialize --contract C1-02

Commit everything staged in project/'s own nested repository (v1.3.2 --
project/ is gitignored from the outer repo by design, see Project
Repository Isolation; this is what gives it real history anyway. Safe to
call routinely -- a no-op, not an error, when nothing changed):

    gatekeeper.py commit-project --message "Complete contract C1-02"

Diagnose drift between this script's actual behavior and what
gatekeeper_spec.md / factory_spec.md / VERSION / CHANGELOG.md claim about it
(v1.3.4 -- diagnostic only, never modifies anything, reports diffs):

    gatekeeper.py self-check

Scan a manuscript (and optionally other release files) for local-path leaks
and inconsistencies against declared key facts before submission (v1.4.0 --
see D-017; --key-facts is optional, the local-path scan runs regardless):

    gatekeeper.py release-check --manuscript paper/manuscript.md \\
        --files paper/REPRODUCIBILITY.md --key-facts project/key_facts.md

Scan data-acquisition scripts and their contract reports for data-generation
function definitions and simulation-indicating language before trusting
their output (v1.4.0 -- see D-022, D-023; either --scripts or --reports
alone is fine, --scripts gets both checks, --reports gets only the textual
scan):

    gatekeeper.py acquisition-audit \\
        --scripts source/data/acquisition/*.py \\
        --reports project/chunks/chunk07/reports/*/contract_report.md

Cross-check a contract report's declared verdict and pre-registered
criterion against its own backing JSON artifact (v1.4.1 -- see D-024,
D-025, D-027; each report must contain a '## Verdict Cross-Check' block,
see factory_spec.md's Contract Specification):

    gatekeeper.py evidence-check \\
        --reports project/chunks/chunk08/reports/C08-08/contract_report.md

Check a contract before accepting it as complete (v1.3.0 fix: bare
required_reports filenames from --manifest now resolve against
project/chunks/chunkNN/reports/{contract_id}/ instead of the current
working directory, correcting a real false-missing-report failure):

    gatekeeper.py check --contract C3-01 \\
        --manifest project/chunks/chunk03/execution_manifest.yaml \\
        --reports project/chunks/chunk03/reports/C3-01/contract_report.md \\
        --allow-dirty          # only while Phase 2 work is still in progress

If no --manifest is given to `check`, pass --frozen and --reports directly.
"""

import argparse
import ast
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SNAPSHOT_DIR = Path("project/.gatekeeper/snapshots")
# v1.3.2 -- moved from the repo-root ".gatekeeper/snapshots" (pre-v1.3.2) into
# project/'s own nested repository, for the same reason project/ itself is
# isolated there: ".gatekeeper/snapshots/C01-02.json" sitting in the OUTER
# repo's tracked history is a distinctive, structured, Factory-shaped
# artifact -- exactly the kind of fingerprint Project Repository Isolation
# exists to avoid, and it was overlooked when that isolation first shipped.
# Rather than gitignoring ".gatekeeper/" separately (which would just
# reintroduce project/'s original bug -- history silently lost -- for a
# second directory), snapshots now live inside project/'s existing nested
# repo and are committed there via the same `commit-project` command,
# with zero new git machinery. See factory_spec.md's Project Repository
# Isolation section.
LEGACY_SNAPSHOT_DIR = Path(".gatekeeper/snapshots")


def _resolve_snapshot_path(contract_id, for_write=False):
    """Returns the snapshot path to use for a contract, handling the
    v1.3.2 relocation transparently.

    Writes always go to the new location (SNAPSHOT_DIR).

    Reads check the new location first; if not found there, fall back to
    the legacy repo-root location, so a project bootstrapped before v1.3.2
    (with existing snapshots already at the old path) keeps working exactly
    as before rather than silently treating its real, existing frozen-file
    history as missing. This is read-compatibility only -- it does not
    migrate anything automatically, since moving files is a decision worth
    the Human/Architect seeing happen, not something silent.
    """
    new_path = SNAPSHOT_DIR / f"{contract_id}.json"
    if for_write:
        return new_path
    if new_path.exists():
        return new_path
    legacy_path = LEGACY_SNAPSHOT_DIR / f"{contract_id}.json"
    if legacy_path.exists():
        return legacy_path
    return new_path  # neither exists -- report against the new (correct-going-forward) path
DROPBOX_DIR = Path("DROP_HERE")
DROPBOX_MANIFEST_NAME = "dropbox_manifest.json"
TAKETHIS_DIR = Path("TAKE_THIS")

# v1.3.0 -- see cmd_materialize for the full rationale. A code block is
# extracted when immediately preceded by a tag of the exact form
# "<!-- MATERIALIZE: path/relative/to/repo/root -->". The path is captured
# non-greedily up to the closing "-->"; content is captured DOTALL between
# the opening fence's newline and the closing fence.
MATERIALIZE_PATTERN = re.compile(
    r'<!--\s*MATERIALIZE:\s*(\S+?)\s*-->\s*\n```[a-zA-Z0-9_+\-]*\n(.*?)\n```',
    re.DOTALL
)

DEFAULT_REQUIRED_SECTIONS = [
    "objective",
    "verification",
    "evidence",
]


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_manifest_contract(manifest_path: Path, contract_id: str):
    try:
        import yaml
    except ImportError:
        print("ERROR: --manifest requires PyYAML (`pip install pyyaml --break-system-packages`).")
        print("Falling back: pass --frozen / --reports directly instead.")
        sys.exit(9)

    if not manifest_path.exists():
        print(f"ERROR: manifest not found: {manifest_path}")
        sys.exit(9)

    with open(manifest_path) as f:
        data = yaml.safe_load(f)

    contracts = data.get("contracts", [])
    match = next((c for c in contracts if c.get("id") == contract_id), None)
    if match is None:
        print(f"ERROR: contract '{contract_id}' not found in {manifest_path}")
        sys.exit(9)
    return match


def _snapshot_one(contract_id, frozen_paths, force=False):
    """Returns (status: str, message: str). status in {'created','skipped','error'}."""
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    snapshot_path = _resolve_snapshot_path(contract_id, for_write=True)

    if not frozen_paths:
        return "skipped", f"{contract_id}: no frozen_files listed -- nothing to snapshot."

    if snapshot_path.exists() and not force:
        return "skipped", (
            f"{contract_id}: snapshot already exists at {snapshot_path} -- left untouched. "
            f"Frozen means frozen; re-snapshotting silently would defeat the point. "
            f"A legitimate change here is an Architecture Amendment, not a re-snapshot."
        )

    hashes = {}
    missing = []
    for rel_path in frozen_paths:
        p = Path(rel_path)
        if not p.exists():
            missing.append(rel_path)
            continue
        hashes[rel_path] = sha256_of(p)

    if missing:
        return "error", f"{contract_id}: cannot snapshot -- these files do not exist: {missing}"

    payload = {"contract": contract_id, "files": hashes}
    with open(snapshot_path, "w") as f:
        json.dump(payload, f, indent=2, sort_keys=True)

    detail = "; ".join(f"{p}={h[:12]}..." for p, h in sorted(hashes.items()))
    return "created", f"{contract_id}: snapshot recorded ({len(hashes)} file(s)) -> {snapshot_path} [{detail}]"


def cmd_snapshot(args):
    frozen = sorted(set(list(args.frozen or []) + _auto_frozen_verification_paths()))
    status, message = _snapshot_one(args.contract, frozen, force=args.force)
    print(message)
    if status == "error":
        sys.exit(9)


def cmd_snapshot_chunk(args):
    try:
        import yaml
    except ImportError:
        print("ERROR: snapshot-chunk requires PyYAML (`pip install pyyaml --break-system-packages`).")
        sys.exit(9)

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print(f"ERROR: manifest not found: {manifest_path}")
        sys.exit(9)

    with open(manifest_path) as f:
        data = yaml.safe_load(f)

    contracts = data.get("contracts", [])
    if not contracts:
        print(f"ERROR: no contracts found in {manifest_path}")
        sys.exit(9)

    print(f"Snapshotting all frozen files for {len(contracts)} contract(s) in {manifest_path}")
    print("=" * 60)

    any_error = False
    for c in contracts:
        cid = c.get("id", "<missing id>")
        frozen = sorted(set((c.get("frozen_files", []) or []) + _auto_frozen_verification_paths()))
        status, message = _snapshot_one(cid, frozen, force=args.force)
        print(f"[{status.upper():7s}] {message}")
        if status == "error":
            any_error = True

    print("=" * 60)
    print(
        "Reminder: run 'gatekeeper.py commit-project' now. project/.gatekeeper/snapshots/ "
        "lives inside project/'s own nested repo (v1.3.2) -- an uncommitted snapshot reads "
        "as a dirty working tree there at the next Repository Integrity check."
    )
    if any_error:
        sys.exit(9)


def _load_dropbox_manifest():
    """Returns (manifest_dict, error_message_or_None).

    dropbox_manifest.json (v1.2.0) is a permanent, bootstrapped Factory file
    -- created once at bootstrap time with the fixed, well-known rules
    already populated, then only ever appended to (never regenerated from
    scratch) as the Architect's chunk planning introduces new one-off handoffs
    (a dataset, a credential file). Both the fixed "rules" entries and any
    per-chunk "entries" additions live in the same file so the Implementor only ever
    has one place to look.

    Schema:
    {
      "rules": [
        {"pattern": "^chunk(\\d+)\\.md$",
         "destination": "project/chunks/chunk{1}/chunk{1}.md"},
        {"pattern": "^C(\\d+)-(\\d+)_contract\\.md$",
         "destination": "project/chunks/chunk{1}/contracts/C{1}-{2}_contract.md"},
        {"pattern": "^execution_manifest_chunk(\\d+)\\.yaml$",
         "destination": "project/chunks/chunk{1}/execution_manifest.yaml"},
        {"pattern": "^C(\\d+)-(\\d+)_contract_report\\.md$",
         "destination": "project/chunks/chunk{1}/reports/C{1}-{2}/contract_report.md"},
        {"pattern": "^chunk(\\d+)_report\\.md$",
         "destination": "project/chunks/chunk{1}/chunk_report.md"},
        {"pattern": "^project_description\\.md$",
         "destination": "project/project_description.md"},
        ...
      ],
      "entries": [
        {"filename": "training_data.csv",
         "destination": "source/data/training_data.csv"}
      ]
    }

    Matching order: "entries" (exact filename) checked first -- these are
    one-off, Architect-authored, and take priority over a generic rule that
    might otherwise also match. Then "rules" (regex pattern against the
    filename, capture groups substituted into destination via {1}, {2}, ...).
    A dropped file matching neither is left exactly where it is and
    reported, never guessed at. No content sniffing, ever -- filename is
    the only signal this command is allowed to use.
    """
    manifest_path = DROPBOX_DIR / DROPBOX_MANIFEST_NAME
    if not manifest_path.exists():
        return None, f"no {manifest_path} found -- this should have been created by bootstrap.sh. Re-run bootstrap or restore it from factory/dropbox_manifest.json."

    try:
        with open(manifest_path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return None, f"{manifest_path} exists but is not valid JSON: {e}"

    rules = data.get("rules", [])
    entries = data.get("entries", [])
    if not rules and not entries:
        return None, f"{manifest_path} exists but has no rules and no entries -- nothing to sort against."

    return data, None


def _resolve_destination(filename, data):
    """Returns (destination_str_or_None, matched_via_str_or_None).

    Checks exact-filename entries first, then regex rules in file order
    (first match wins -- rules should be written non-overlapping, but if
    they aren't, order is the deterministic tiebreaker rather than an
    error, so this command never has to guess which rule "means" more).
    """
    for entry in data.get("entries", []):
        if entry.get("filename") == filename:
            return entry.get("destination"), "entries"

    for rule in data.get("rules", []):
        pattern = rule.get("pattern")
        dest_template = rule.get("destination")
        if not pattern or not dest_template:
            continue
        m = re.match(pattern, filename)
        if m:
            try:
                dest = dest_template
                for i, group in enumerate(m.groups(), start=1):
                    # By dropbox_manifest.json convention, capture group {1}
                    # is always the chunk number. It's zero-padded to 2
                    # digits here so "chunk1" and "chunk01" -- which the Architect
                    # or the Human might drop under either spelling -- can
                    # never resolve to two different chunk directories. Any
                    # other capture group (contract sequence number, etc.)
                    # is substituted exactly as captured, unpadded -- this is
                    # the one piece of normalization this command performs,
                    # not inference about *where* something goes.
                    value = group.zfill(2) if (i == 1 and group.isdigit()) else group
                    dest = dest.replace(f"{{{i}}}", value)
                return dest, f"rule: {pattern}"
            except (IndexError, TypeError):
                continue

    return None, None


def cmd_sort_dropbox(args):
    if not DROPBOX_DIR.exists():
        print(f"ERROR: {DROPBOX_DIR}/ does not exist. Nothing to sort.")
        sys.exit(9)

    data, err = _load_dropbox_manifest()
    if err:
        print(f"ERROR: {err}")
        print(
            "Dropbox Sort only files exactly what dropbox_manifest.json's rules/entries declare -- "
            "it never infers a destination from a file's content, and pattern rules are explicit "
            "regexes written by the Human or Architect, never inferred at sort time."
        )
        sys.exit(9)

    all_entries = [p for p in DROPBOX_DIR.iterdir() if p.name != DROPBOX_MANIFEST_NAME]
    present_files = [p for p in all_entries if p.is_file()]
    # v1.3.4 (BUG-4): non-file entries (directories, symlinks-to-directories,
    # etc.) used to be excluded from every reported category, including
    # [UNKNOWN] -- a dropped folder vanished from the output entirely.
    # They're now listed and reported under their own category instead.
    non_file_entries = [p for p in all_entries if not p.is_file()]

    print(f"Sorting {DROPBOX_DIR}/ against {len(data.get('entries', []))} exact entr(y/ies) "
          f"and {len(data.get('rules', []))} pattern rule(s).")
    print("=" * 60)

    moved, skipped_unknown, skipped_exists, errors = [], [], [], []

    for p in present_files:
        dest_str, matched_via = _resolve_destination(p.name, data)

        if dest_str is None:
            skipped_unknown.append(p.name)
            continue

        dest = Path(dest_str)

        if dest.exists() and not args.force:
            skipped_exists.append((p.name, str(dest)))
            continue

        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            p.replace(dest)
            moved.append((p.name, str(dest), matched_via))
        except OSError as e:
            errors.append(f"{p.name} -> {dest}: {e}")

    for fname, dest, matched_via in moved:
        print(f"[MOVED  ] {fname} -> {dest}  (matched via {matched_via})")
    for fname, dest in skipped_exists:
        print(f"[SKIPPED] {fname}: destination already exists at {dest} (use --force to overwrite deliberately)")
    for fname in skipped_unknown:
        print(f"[UNKNOWN] {fname}: matches no rule or entry in dropbox_manifest.json -- left in {DROPBOX_DIR}/, not moved.")
    for p in non_file_entries:
        print(f"[SKIPPED - NOT A FILE] {p.name}: directories are never sorted or moved by this command -- left in {DROPBOX_DIR}/.")
    for e in errors:
        print(f"[ERROR  ] {e}")

    print("=" * 60)
    print(f"Moved: {len(moved)}  Skipped (exists): {len(skipped_exists)}  "
          f"Unknown (left in place): {len(skipped_unknown)}  "
          f"Skipped (not a file): {len(non_file_entries)}  Errors: {len(errors)}")

    if skipped_unknown:
        print(
            f"\n{len(skipped_unknown)} file(s) left in {DROPBOX_DIR}/ because dropbox_manifest.json "
            f"doesn't name or pattern-match them. This is not a failure -- it's the deterministic "
            f"behavior working as intended (per C01/EP-002, a guessed placement is worse than an "
            f"honest 'unresolved'). Report this list to the Human/Architect rather than moving them "
            f"by inference. If this is a new artifact type the Factory should recognize going "
            f"forward, that's a dropbox_manifest.json rule addition, not a one-time workaround."
        )

    if errors:
        sys.exit(9)


def cmd_stage_takethis(args):
    """Copies one completed chunk's self-contained reports into TAKE_THIS/
    for the Human to grab in one place, instead of hunting through nested
    project/chunks/chunkNN/reports/C{NN}-{seq}/ directories by hand.

    This is always a COPY, never a move. The originals under
    project/chunks/chunkNN/ are the permanent record and are never touched,
    renamed, or deleted by this command -- TAKE_THIS/ is disposable staging,
    nothing more.

    Copied files are renamed flat, reusing the exact same naming convention
    dropbox_manifest.json already uses on the way IN (see Dropbox
    Specification) -- C{NN}-{seq}_contract_report.md and chunkNN_report.md
    -- so a file staged here is, by construction, already correctly named
    if it were ever dropped back into a DROP_HERE/ elsewhere.

    Scope: every contract_report.md under the chunk's reports/ directory,
    plus the chunk's own chunk_report.md. Does not include AI_Note.md or
    fix_package.md -- those are cross-chunk or forward-looking artifacts,
    not this-chunk-is-done reports.
    """
    chunk = args.chunk
    chunk_dir = Path("project/chunks") / chunk
    chunk_report_src = chunk_dir / "chunk_report.md"

    if not chunk_report_src.exists():
        print(f"ERROR: {chunk_report_src} not found.")
        print(
            "stage-takethis requires the chunk report to exist first -- "
            "compile the chunk report before staging it for handoff."
        )
        sys.exit(9)

    TAKETHIS_DIR.mkdir(parents=True, exist_ok=True)

    staged = []

    chunk_report_dest = TAKETHIS_DIR / f"{chunk}_report.md"
    shutil.copy2(chunk_report_src, chunk_report_dest)
    staged.append((chunk_report_src, chunk_report_dest))

    reports_dir = chunk_dir / "reports"
    if reports_dir.exists():
        for contract_dir in sorted(p for p in reports_dir.iterdir() if p.is_dir()):
            report_src = contract_dir / "contract_report.md"
            if report_src.exists():
                report_dest = TAKETHIS_DIR / f"{contract_dir.name}_contract_report.md"
                shutil.copy2(report_src, report_dest)
                staged.append((report_src, report_dest))

    print(f"Staged {len(staged)} self-contained report(s) into {TAKETHIS_DIR}/ for {chunk}:")
    for src, dest in staged:
        print(f"  [COPIED ] {src} -> {dest}")
    print(f"Originals remain permanently at their location under {chunk_dir}/ -- this was a copy only.")


def cmd_clear_takethis(args):
    """Empties TAKE_THIS/ of every file currently staged there. Run this
    when a new chunk is starting (per gemini_spec.md's Mailbox Protocol,
    the "chunk N is here, do it" trigger specifically -- not the generic
    "check the mailbox" trigger, which is also used mid-chunk for things
    like dataset drops where clearing TAKE_THIS would be wrong).

    Self-healing: if TAKE_THIS/ doesn't exist yet, this creates it empty
    rather than erroring, matching the Factory's general idempotent-bootstrap
    philosophy elsewhere (bootstrap.sh, sort-dropbox).

    Never touches anything under project/ -- TAKE_THIS only ever holds
    copies, so clearing it can never lose the permanent record.
    """
    if not TAKETHIS_DIR.exists():
        TAKETHIS_DIR.mkdir(parents=True, exist_ok=True)
        print(f"{TAKETHIS_DIR}/ did not exist -- created it (empty).")
        return

    present_files = [p for p in TAKETHIS_DIR.iterdir() if p.is_file()]

    if not present_files:
        print(f"{TAKETHIS_DIR}/ is already empty. Nothing to clear.")
        return

    print(f"Clearing {TAKETHIS_DIR}/ -- {len(present_files)} file(s) removed "
          f"(originals under project/ are untouched):")
    for p in sorted(present_files):
        print(f"  [REMOVED] {p.name}")
        p.unlink()
    print(f"{TAKETHIS_DIR}/ is now empty.")


def cmd_commit_project(args):
    """Commits everything currently staged in project/'s own nested
    repository (v1.3.2 -- see Project Repository Isolation in
    factory_spec.md). project/ is gitignored from the outer repo by design;
    this is the deterministic operation that gives it real git history
    anyway, scoped entirely to its own repo.

    Safe to call routinely -- if project/.git doesn't exist yet (a project
    bootstrapped before v1.3.2, or genuinely nothing to commit), this says
    so plainly rather than erroring, since "nothing to commit" is an
    expected, non-failure outcome for a command meant to be run after
    every contract.
    """
    project_git = Path("project/.git")
    if not project_git.exists():
        print(
            "No nested project/.git repository found. If this project was bootstrapped "
            "before v1.3.2, project/ isn't tracked anywhere -- re-run bootstrap.sh to "
            "add one (it only initializes what's missing, per its idempotency guarantee)."
        )
        sys.exit(9)

    add_result = subprocess.run(
        ["git", "-C", "project", "add", "-A"],
        capture_output=True, text=True,
    )
    if add_result.returncode != 0:
        print(f"ERROR: 'git -C project add -A' failed: {add_result.stderr.strip()}")
        sys.exit(9)

    status_result = subprocess.run(
        ["git", "-C", "project", "status", "--porcelain"],
        capture_output=True, text=True,
    )
    if not status_result.stdout.strip():
        print("Nothing to commit in project/ -- working tree already clean.")
        return

    message = args.message or "Update project/ artifacts"
    commit_result = subprocess.run(
        ["git", "-C", "project", "commit", "-m", message],
        capture_output=True, text=True,
    )
    if commit_result.returncode != 0:
        print(f"ERROR: 'git -C project commit' failed: {commit_result.stderr.strip()}")
        sys.exit(9)

    print(f"Committed to project/'s nested repository: \"{message}\"")
    print(commit_result.stdout.strip())


def _contract_id_candidates(contract_id):
    """Returns (chunk_num, seq_num, candidate_ids) or (None, None, None) if
    contract_id doesn't match the C{chunk}-{seq} naming convention.

    v1.3.4 (BUG-2): factored out of _find_contract_file so every caller that
    needs to resolve a contract ID against a directory-name component --
    _find_contract_file, cmd_next's report-path lookup, cmd_check's
    required_reports resolution -- shares the same padded/as-given fallback
    instead of each reimplementing (or omitting) it independently.

    chunk_num and seq_num are always returned zero-padded to 2 digits.
    candidate_ids is an ordered, de-duplicated list: the as-given ID first,
    then the fully-padded ID -- both are checked as literal directory/file
    name components by callers, since a report or contract file may have
    been filed under either spelling.
    """
    m = re.match(r'^C(\d+)-(\d+)$', contract_id)
    if not m:
        return None, None, None

    chunk_num = m.group(1).zfill(2)
    seq_num = m.group(2).zfill(2)
    padded_id = f"C{chunk_num}-{seq_num}"

    candidate_ids = [contract_id]
    if padded_id != contract_id:
        candidate_ids.append(padded_id)

    return chunk_num, seq_num, candidate_ids


def _find_contract_file(contract_id):
    """Returns (path_or_None, error_or_None).

    Given a contract ID like "C01-02", deterministically locates its
    contract file at project/chunks/chunkNN/contracts/C{NN}-{seq}_contract.md
    -- the chunk number is parsed directly out of the contract ID itself,
    per the naming convention (ClaudeInitialization.md Section 4), never
    searched for or guessed. Accepts an unpadded contract ID (e.g. "C1-2")
    and normalizes it the same way sort-dropbox normalizes chunk numbers.
    """
    chunk_num, seq_num, candidate_ids = _contract_id_candidates(contract_id)
    if chunk_num is None:
        return None, f"'{contract_id}' doesn't match the C{{chunk}}-{{seq}} naming convention (e.g. C01-02)."

    padded_id = f"C{chunk_num}-{seq_num}"
    chunk_dir = Path("project/chunks") / f"chunk{chunk_num}"

    for candidate_id in candidate_ids:
        candidate_path = chunk_dir / "contracts" / f"{candidate_id}_contract.md"
        if candidate_path.exists():
            return candidate_path, None

    return None, f"{chunk_dir / 'contracts' / (padded_id + '_contract.md')} not found."


def cmd_materialize(args):
    """Deterministically extracts MATERIALIZE-tagged code blocks from a
    contract markdown file and writes them to their declared destination
    paths, byte-for-byte.

    This exists to close a real, observed failure mode: a contract --
    especially a High-tier one the Architect implements directly -- embeds
    full implementation source inside its own markdown, because per the
    Dropbox Specification raw source files are never dropped loose into
    DROP_HERE/ (dropbox_manifest.json intentionally has no rule for that).
    Before this command existed, turning that embedded markdown into real
    files on disk was a manual, interpretive step: the Implementation
    Engineer reading code blocks in prose and retyping or copy-pasting them
    into place, with the exact boundary of "where does the code start/end"
    left to its own judgment. That is precisely the category of decision
    EP-002/C07 (determinism over interpretation) says should be made
    mechanical wherever it can be -- so as of v1.3.0, it is.

    Convention: a line of the exact form

        <!-- MATERIALIZE: path/relative/to/repo/root -->

    immediately before a fenced code block marks that block for extraction.
    The path is relative to the repository root, not the contract file's
    own location. Everything between the fence's opening and closing lines
    is written exactly as captured, with a trailing newline added if the
    captured block doesn't already end in one -- no other reformatting, no
    reinterpretation, no judgment about whether the code "looks right." A
    single contract may contain any number of these pairs (e.g. a High-tier
    contract embedding two related headers in one file).

    A destination that already exists is left untouched and reported unless
    --force is passed -- same overwrite discipline as sort-dropbox, for the
    same reason: silently clobbering an existing file is worse than making
    the Human/Architect say so explicitly.
    """
    contract_path, err = _find_contract_file(args.contract)
    if err:
        print(f"ERROR: {err}")
        sys.exit(9)

    try:
        text = contract_path.read_text()
    except OSError as e:
        print(f"ERROR: could not read {contract_path}: {e}")
        sys.exit(9)

    matches = list(MATERIALIZE_PATTERN.finditer(text))

    if not matches:
        print(f"No MATERIALIZE-tagged code blocks found in {contract_path}.")
        print(
            "Nothing to do -- this contract either has no embedded source to "
            "materialize, or uses a tag this command doesn't recognize. Check "
            "the exact convention: <!-- MATERIALIZE: path --> immediately "
            "before the fenced code block, with no blank line between them "
            "other than the newline the tag itself ends with."
        )
        return

    print(f"Found {len(matches)} MATERIALIZE-tagged block(s) in {contract_path}:")
    print("=" * 60)

    written, skipped_exists, errors = [], [], []

    for m in matches:
        dest = Path(m.group(1))
        content = m.group(2)

        if dest.exists() and not args.force:
            skipped_exists.append(str(dest))
            continue

        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            out = content if content.endswith("\n") else content + "\n"
            dest.write_text(out)
            written.append(str(dest))
        except OSError as e:
            errors.append(f"{dest}: {e}")

    for d in written:
        print(f"  [WRITTEN] {d}")
    for d in skipped_exists:
        print(f"  [SKIPPED] {d} already exists (use --force to overwrite deliberately)")
    for e in errors:
        print(f"  [ERROR  ] {e}")

    print("=" * 60)
    print(f"Written: {len(written)}  Skipped (exists): {len(skipped_exists)}  Errors: {len(errors)}")

    if skipped_exists and not args.force:
        print(
            f"\n{len(skipped_exists)} file(s) already existed and were left untouched. "
            f"If this contract is meant to update them, re-run with --force."
        )

    if errors:
        sys.exit(9)


def check_frozen_files(contract_id, frozen_paths):
    """Returns (ok: bool, details: list[str])."""
    snapshot_path = _resolve_snapshot_path(contract_id, for_write=False)
    details = []

    if not snapshot_path.exists():
        details.append(
            f"WARNING: no snapshot found for contract '{contract_id}' at {snapshot_path}. "
            f"Frozen File Validation did NOT run for this contract -- run `snapshot` first. "
            f"This is not a PASS by omission."
        )
        return True, details  # doesn't fail the run, but is loudly not a pass either

    with open(snapshot_path) as f:
        baseline = json.load(f)["files"]

    ok = True
    for rel_path in frozen_paths:
        p = Path(rel_path)
        if rel_path not in baseline:
            details.append(f"WARNING: {rel_path} has no recorded baseline hash -- not checked.")
            continue
        if not p.exists():
            details.append(f"FAIL: {rel_path} was frozen but no longer exists.")
            ok = False
            continue
        current = sha256_of(p)
        if current != baseline[rel_path]:
            details.append(
                f"FAIL: {rel_path} hash changed.\n"
                f"       baseline: {baseline[rel_path]}\n"
                f"       current:  {current}"
            )
            ok = False
        else:
            details.append(f"PASS: {rel_path} unchanged ({current[:12]}...)")

    return ok, details


# v1.3.4 (BUG-3): matches a markdown "## " (or deeper) heading line.
# Section presence is checked against extracted heading text, not against
# the raw file body, so a required section name appearing only in prose
# (e.g. "no verification was possible") no longer satisfies the check.
_HEADING_LINE_RE = re.compile(r'^#{2,6}\s+(.+?)\s*$', re.MULTILINE)


def _extract_headers(text):
    """Returns a list of heading text strings (## and deeper), whitespace-
    normalized and lowercased, extracted from a markdown document."""
    return [
        " ".join(m.group(1).split()).lower()
        for m in _HEADING_LINE_RE.finditer(text)
    ]


def check_reports(report_paths, required_sections):
    """Returns (ok: bool, details: list[str]).

    v1.3.4 (BUG-3): required_sections are matched against the report's
    actual "## "-level headers, not as a raw substring search across the
    whole file body. gatekeeper_spec.md's Report Validation section has
    always specified "required section headers present" -- this brings the
    implementation in line with that, rather than under-delivering against
    its own spec. A required section name is satisfied when it appears as a
    substring of some extracted header line (case-insensitive,
    whitespace-normalized) -- e.g. required "verification" matches a
    "## Verification Summary" header, per the real contract_report.md /
    chunk_report.md templates in gemini_spec.md section 8.
    """
    ok = True
    details = []
    for rel_path in report_paths:
        p = Path(rel_path)
        if not p.exists():
            details.append(f"FAIL: required report missing: {rel_path}")
            ok = False
            continue

        text = p.read_text(errors="replace")
        headers = _extract_headers(text)
        missing_sections = [
            s for s in required_sections
            if not any(s.lower() in h for h in headers)
        ]
        if missing_sections:
            details.append(
                f"FAIL: {rel_path} exists but is missing required section header(s): "
                f"{missing_sections} (checked against '## '-level headers only -- "
                f"a required word appearing in prose elsewhere in the file does not "
                f"satisfy this; this is not semantic validation, "
                f"per gatekeeper_spec.md's Forbidden list)"
            )
            ok = False
        else:
            details.append(f"PASS: {rel_path} present with required section headers")
    return ok, details


def _git_status_porcelain(repo_root=None):
    """Returns (ok, output_or_error). repo_root=None means the current
    directory's repo (the outer repo); a path runs against that path's own
    repo instead, via -C, without changing this process's cwd."""
    cmd = ["git"]
    if repo_root is not None:
        cmd += ["-C", str(repo_root)]
    cmd += ["status", "--porcelain"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return True, result.stdout
    except FileNotFoundError:
        return False, "git is not installed or not on PATH."
    except subprocess.CalledProcessError as e:
        return False, f"not a git repository, or git error: {e}"


def check_git_clean():
    """Returns (ok: bool, details: list[str]).

    Checks the outer repo's working tree, and -- v1.3.2 -- also the nested
    project/ repository if one exists (see Project Repository Isolation in
    factory_spec.md). project/ is gitignored from the outer repo by
    deliberate design (so the outer repo's structure and history show no
    trace of the Factory), but it is still expected to be its own real,
    clean git repository -- this check makes sure Repository Integrity
    actually covers both roots instead of silently only ever seeing the one
    that happens to be the process's cwd.
    """
    details = []
    overall_ok = True

    ok, output = _git_status_porcelain()
    if not ok:
        return False, [f"FAIL: outer repository -- {output}"]
    if output.strip():
        dirty = output.strip().splitlines()
        details.append(f"FAIL: outer repository working tree not clean ({len(dirty)} entries):")
        details += [f"       {line}" for line in dirty]
        overall_ok = False
    else:
        details.append("PASS: outer repository working tree clean")

    project_git = Path("project/.git")
    if project_git.exists():
        ok, output = _git_status_porcelain(repo_root="project")
        if not ok:
            details.append(f"FAIL: nested project/ repository -- {output}")
            overall_ok = False
        elif output.strip():
            dirty = output.strip().splitlines()
            details.append(f"FAIL: nested project/ repository working tree not clean ({len(dirty)} entries):")
            details += [f"       {line}" for line in dirty]
            overall_ok = False
        else:
            details.append("PASS: nested project/ repository working tree clean")
    else:
        details.append("SKIPPED: no nested project/ repository found (pre-v1.3.2 project, or not yet bootstrapped with one)")

    return overall_ok, details


# Order matters: check the more specific patterns before the ones they're a
# substring of ("COMPLETE — FLAGGED" contains "COMPLETE").
#
# v1.3.4 (BUG-1b): the bare "COMPLETE" pattern is matched with a regex word
# boundary so it can never match inside "INCOMPLETE". The em-dash/hyphen
# pairs above it are unaffected -- those were audited separately and found
# correct (real UTF-8 em dashes plus ASCII-hyphen fallbacks, deliberate
# dual coverage; see v1_3_4_candidate_spec.md section 1.1, "Not in scope").
STATUS_PATTERNS = [
    ("BLOCKED — HUMAN ACTION REQUIRED", "blocked_human_action"),
    ("BLOCKED - HUMAN ACTION REQUIRED", "blocked_human_action"),
    ("BLOCKED — CARRIED FORWARD", "blocked_carried_forward"),
    ("BLOCKED - CARRIED FORWARD", "blocked_carried_forward"),
    ("COMPLETE — FLAGGED", "complete_flagged"),
    ("COMPLETE - FLAGGED", "complete_flagged"),
    (re.compile(r'(?<![A-Z])COMPLETE(?![A-Z])'), "complete"),
]

# v1.3.4 (BUG-1a): a line matching this marks the end of the Final Status
# section for parsing purposes -- any other "## " heading. Bounding the
# search here stops words in Remaining Risks, the Plain-Language Summary,
# or any later section from being mistaken for the Final Status value.
_NEXT_HEADING_RE = re.compile(r'^##\s', re.MULTILINE)


def parse_contract_status(report_path: Path) -> str:
    """Reads the Final Status line of a contract_report.md. Never guesses --
    returns 'unknown' rather than assuming a status it can't actually find.

    v1.3.4 (BUG-1a/1b): the search is bound to the Final Status section
    itself -- from the "## Final Status" heading up to (but not including)
    the next "## " heading -- so a status word appearing later in Remaining
    Risks or the Plain-Language Summary can no longer be mistaken for the
    Final Status value. The bare "COMPLETE" pattern also now matches as a
    whole token, so it can never match inside "INCOMPLETE".
    """
    if not report_path.exists():
        return "not_started"

    text = report_path.read_text(errors="replace")
    lower = text.lower()
    idx = lower.find("## final status")
    if idx == -1:
        search_text = text
    else:
        after_heading = idx + len("## final status")
        next_heading_match = _NEXT_HEADING_RE.search(text, after_heading)
        end = next_heading_match.start() if next_heading_match else len(text)
        search_text = text[idx:end]

    for pattern, status in STATUS_PATTERNS:
        if isinstance(pattern, re.Pattern):
            if pattern.search(search_text):
                return status
        elif pattern in search_text:
            return status
    return "unknown"


def cmd_next(args):
    try:
        import yaml
    except ImportError:
        print("ERROR: next requires PyYAML (`pip install pyyaml --break-system-packages`).")
        sys.exit(9)

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print(f"ERROR: manifest not found: {manifest_path}")
        sys.exit(9)

    with open(manifest_path) as f:
        data = yaml.safe_load(f)

    contracts = {c["id"]: c for c in data.get("contracts", []) if "id" in c}
    execution_order = data.get("execution_order", [])
    if not execution_order:
        print(f"ERROR: no execution_order found in {manifest_path}")
        sys.exit(9)

    reports_dir = Path(args.reports_dir) if args.reports_dir else manifest_path.parent / "reports"

    SATISFIED = {"complete", "complete_flagged"}
    UNRESOLVED_BLOCKING = {"blocked_carried_forward", "blocked_human_action"}

    def _report_path_for(cid):
        # v1.3.4 (BUG-2): fall back between the as-given and zero-padded
        # contract ID, matching _find_contract_file's existing behavior --
        # a report filed at an unpadded path (e.g. reports/C1-3/) must
        # still be found, not silently read as not_started forever.
        _, _, candidates = _contract_id_candidates(cid)
        tried = candidates if candidates else [cid]
        for candidate_id in tried:
            candidate_path = reports_dir / candidate_id / "contract_report.md"
            if candidate_path.exists():
                return candidate_path
        return reports_dir / cid / "contract_report.md"

    statuses = {cid: parse_contract_status(_report_path_for(cid)) for cid in execution_order}

    print(f"Execution order per {manifest_path}:")
    print("=" * 60)
    for cid in execution_order:
        print(f"  {cid:12s} {statuses[cid]}")
    print("=" * 60)

    blocked_found = []
    for cid in execution_order:
        status = statuses[cid]

        if status in SATISFIED:
            continue

        if status in UNRESOLVED_BLOCKING:
            blocked_found.append((cid, status))
            continue  # don't stop here -- a later, independent contract may still be runnable

        deps = (contracts.get(cid, {}) or {}).get("depends_on", []) or []
        unmet_blocked = [d for d in deps if statuses.get(d) in UNRESOLVED_BLOCKING]
        unmet_pending = [d for d in deps if d not in [b[0] for b in blocked_found] and statuses.get(d) not in SATISFIED and statuses.get(d) not in UNRESOLVED_BLOCKING]

        if unmet_blocked:
            print(f"NEXT: none for {cid} -- depends on {unmet_blocked}, which {'is' if len(unmet_blocked)==1 else 'are'} blocked. Skipping, checking the rest of execution_order.")
            continue

        if unmet_pending:
            print(f"NEXT: none ready yet -- {cid} is next in order but depends on {unmet_pending}, not yet satisfied.")
            sys.exit(0)

        if status == "unknown":
            print(f"NEXT: none. {cid} has a report at {reports_dir / cid / 'contract_report.md'} "
                  f"but its Final Status could not be parsed. Fix the report rather than guessing at its status.")
            sys.exit(9)

        # status == "not_started" and all deps satisfied (or independent of anything blocked)
        c = contracts.get(cid, {})
        print(f"NEXT: {cid}")
        print(f"  Risk Tier: {c.get('risk_tier', '<not in manifest>')}")
        print(f"  Implementation Owner: {c.get('implementation_owner', '<not in manifest>')}")
        if blocked_found:
            print(f"  (Note: {[b[0] for b in blocked_found]} are blocked and were skipped over -- still needs Chunk Review attention.)")
        sys.exit(0)

    if blocked_found:
        print(f"NEXT: none. Every remaining contract is blocked on {[b[0] for b in blocked_found]} or already done.")
        print("This chunk cannot fully complete without Chunk Review addressing the blocked contract(s).")
        sys.exit(0)

    print("NEXT: none. Every contract in execution_order is COMPLETE or COMPLETE — FLAGGED.")
    print("Chunk is ready for chunk_report.md compilation and Chunk Review.")
    sys.exit(0)


def _run_mandatory_gate(contract_id, report_paths, required_verification_commands):
    """v1.4.2 amendment (D-032/D-033) -- for a T-COMP/T-CAUSAL contract,
    mechanically requires all four v1.4.2 guards to pass, not merely
    documents that they exist. Returns (ok, detail_lines). Reuses the
    exact underlying functions verify-contract/lint-contract/recompute/
    stamp-report already run standalone -- this is not a duplicate
    implementation, and it never re-invents what those subcommands do.

    Order matters: Required Verification Commands is checked first
    because it answers the specific gap independent review raised --
    that a report's declared command was never checked against what the
    contract actually required, only that whatever was declared exited
    0. The other three then run as before."""
    ok = True
    lines = []

    if not report_paths:
        return False, ["FAIL: no report given -- a T-COMP/T-CAUSAL contract cannot pass this gate "
                        "without a contract_report.md to check (Required Verification Commands, "
                        "verify-contract, lint-contract, recompute, and stamp presence all read one)."]

    for rp in report_paths:
        rp_path = Path(rp)
        text = _read_text_or_none(rp_path)
        if text is None:
            ok = False
            lines.append(f"FAIL [{rp}]: report not found.")
            continue

        # 1. Required Verification Commands (D-033) -- the declared
        # command(s) must be drawn from the frozen set the Architect declared at
        # contract-generation time, not freely invented in the report.
        declared = _extract_declared_commands(text)
        if required_verification_commands:
            missing_required = [c for c in required_verification_commands if c not in declared]
            if missing_required:
                ok = False
                lines.append(
                    f"FAIL [{rp}]: report's declared '## Verification' commands do not include "
                    f"every command this contract's Required Verification Commands field froze: "
                    f"missing {missing_required}. A report may declare additional commands, but "
                    f"cannot substitute a different one for a required one."
                )
            else:
                lines.append(f"OK [{rp}]: all {len(required_verification_commands)} Required "
                              f"Verification Command(s) present in the report's declared set.")
        else:
            lines.append(f"WARNING [{rp}]: scientific_claim_tier is T-COMP/T-CAUSAL but this "
                          f"contract declares no Required Verification Commands -- verify-contract "
                          f"below will still re-run whatever the report happens to declare, but "
                          f"nothing here confirms that's the command the contract actually required.")

        # 2. verify-contract -- re-execute every declared command for real.
        if not declared:
            ok = False
            lines.append(f"FAIL [{rp}]: no '## Verification' commands declared at all -- nothing "
                          f"to independently re-execute.")
        else:
            any_cmd_fail = False
            for cmd in declared:
                exit_code, stdout, stderr = _run_subprocess(cmd)
                if exit_code != 0:
                    any_cmd_fail = True
                    lines.append(f"FAIL [{rp}] verify-contract: `{cmd}` -> real exit code {exit_code}.")
            if any_cmd_fail:
                ok = False
            else:
                lines.append(f"OK [{rp}] verify-contract: {len(declared)} declared command(s) "
                              f"re-executed, all exited 0.")

        # 3. lint-contract -- swallowed exceptions, fabrication patterns,
        # frozen-machinery tampering, over the files this report's own
        # git diff touched (the same scope stamp-report uses).
        git_files, _ = _git_diff_files()
        py_targets = [f for f in (git_files or []) if f.endswith(".py")]
        lint_hard = []
        for sp in py_targets:
            h, _w = _scan_swallowed_exceptions(sp)
            lint_hard += h
        lint_hard += _scan_fabricated_statistical_input(py_targets)
        frozen_paths = _auto_frozen_verification_paths()
        if frozen_paths:
            fr_ok, _fr_details = check_frozen_files(contract_id, frozen_paths)
            if not fr_ok:
                lint_hard.append("FROZEN VERIFICATION MACHINERY TAMPERED (see lint-contract detail).")
        if lint_hard:
            ok = False
            for f in lint_hard:
                lines.append(f"FAIL [{rp}] lint-contract: {f}")
        else:
            lines.append(f"OK [{rp}] lint-contract: no hard failures across {len(py_targets)} "
                          f"changed Python file(s).")

        # 4. recompute -- a T-COMP/T-CAUSAL report must declare a
        # well-formed Recompute Declaration, and it must pass. Unlike the
        # standalone `recompute` subcommand (where no block is simply not
        # checked), a High-risk contract with no block at all is a
        # failure here -- that omission is exactly what D-031 warned was
        # silently allowed.
        checked, recompute_ok, recompute_lines = _check_recompute_block(rp_path)
        if not checked:
            ok = False
            if recompute_lines:
                lines.append(f"FAIL [{rp}] recompute: malformed Recompute Declaration -- "
                              f"{'; '.join(recompute_lines)}")
            else:
                lines.append(f"FAIL [{rp}] recompute: no Recompute Declaration block present. "
                              f"T-COMP/T-CAUSAL contracts require one (D-031, made mandatory by D-032).")
        elif not recompute_ok:
            ok = False
            lines.append(f"FAIL [{rp}] recompute: independent recomputation did not match "
                          f"or was not independent -- {'; '.join(recompute_lines)}")
        else:
            lines.append(f"OK [{rp}] recompute: independent recomputation matched.")

        # 5. stamp presence -- a High-risk contract cannot be COMPLETE
        # without a tamper-evident stamp (D-032). This checks presence
        # and integrity of an existing stamp; it does not append one --
        # `check` never modifies a report, stamping stays an explicit
        # separate step the Implementor runs via `stamp-report`.
        stamps = _find_stamps(text)
        if not stamps:
            ok = False
            lines.append(f"FAIL [{rp}] stamp: no Gatekeeper Verification Stamp present. "
                          f"T-COMP/T-CAUSAL contracts cannot be COMPLETE unstamped (D-032) -- "
                          f"run `gatekeeper.py stamp-report` before this check.")
        else:
            stamp_ok, stamp_findings = _verify_stamp_integrity(rp_path)
            if not stamp_ok:
                ok = False
                for f in stamp_findings:
                    lines.append(f"FAIL [{rp}] stamp: {f}")
            else:
                lines.append(f"OK [{rp}] stamp: {len(stamps)} stamp(s) present and intact.")

    return ok, lines


def cmd_check(args):
    checks_run = []
    overall_ok = True
    exit_code = 0
    # v1.3.4 (BUG-6): the exit-code contract stays exactly as documented
    # (0/4/6/8/9, joined by 17 in the v1.4.2 amendment below) --
    # exit_code = exit_code or N means only the first failing category
    # ever sets it, and that's left unchanged since something may already
    # depend on it. failed_categories tracks every failing category so a
    # printed summary line can show all of them, since the detail lines
    # above already do but the single integer exit code understates a
    # multi-category failure.
    failed_categories = []

    frozen_paths = sorted(set(list(args.frozen or []) + _auto_frozen_verification_paths()))
    report_paths = list(args.reports or [])

    scientific_claim_tier = None
    required_verification_commands = []

    if args.manifest:
        contract = load_manifest_contract(Path(args.manifest), args.contract)
        frozen_paths += contract.get("frozen_files", []) or []
        # v1.4.2 amendment -- mandatory mechanical gate (D-032/D-033): a
        # High-risk scientific/comparative claim no longer merely
        # documents that verify-contract/lint-contract/recompute/
        # stamp-report exist -- `check` now reads the same two manifest
        # fields the Architect declares frozen at contract-generation time and,
        # for T-COMP/T-CAUSAL, mechanically requires all four to pass
        # before the contract can read PASS. See dynamic_rules.md D-032,
        # D-033 and CHANGELOG.md's dated amendment to this entry.
        scientific_claim_tier = contract.get("scientific_claim_tier")
        required_verification_commands = contract.get("required_verification_commands", []) or []
        # v1.3.0 fix: required_reports in the manifest are bare filenames
        # (e.g. "contract_report.md"), matching the Contract Specification's
        # required_reports field -- they are NOT already full paths. Using
        # them as-is resolved relative to the current working directory,
        # not the actual filed location (project/chunks/chunkNN/reports/
        # {contract_id}/), causing a real reported false-missing-report
        # failure. A bare filename (no "/" in it) is now resolved against
        # that standard location; an entry that already contains a "/" is
        # assumed to already be a deliberate explicit path and is left
        # exactly as given, for backward compatibility with any manifest
        # that specified one that way on purpose.
        for rp in contract.get("required_reports", []) or []:
            if "/" in rp or "\\" in rp:
                report_paths.append(rp)
            else:
                # v1.3.4 (BUG-2): resolve against both the as-given and
                # zero-padded contract ID, the same fallback
                # _find_contract_file already applies -- whichever
                # candidate path actually exists on disk is used; if
                # neither exists yet, fall back to the fully-padded path
                # (the correct-going-forward spelling) so the failure
                # message points somewhere deterministic.
                chunk_num, _, candidates = _contract_id_candidates(args.contract or "")
                if chunk_num:
                    resolved = None
                    for candidate_id in candidates:
                        candidate_path = f"project/chunks/chunk{chunk_num}/reports/{candidate_id}/{rp}"
                        if Path(candidate_path).exists():
                            resolved = candidate_path
                            break
                    if resolved is None:
                        resolved = f"project/chunks/chunk{chunk_num}/reports/{candidates[-1]}/{rp}"
                    report_paths.append(resolved)
                else:
                    # No contract ID to derive a chunk number from -- can't
                    # resolve deterministically, so fall back to the literal
                    # value rather than guessing a path.
                    report_paths.append(rp)

    print(f"Gatekeeper check -- contract: {args.contract or '(none specified)'}")
    print("=" * 60)

    if frozen_paths:
        checks_run.append("Frozen File Validation")
        ok, details = check_frozen_files(args.contract or "unknown", frozen_paths)
        print("\n[Frozen File Validation]")
        for line in details:
            print(f"  {line}")
        if not ok:
            overall_ok = False
            exit_code = exit_code or 4
            failed_categories.append("frozen_file")
    else:
        print("\n[Frozen File Validation] SKIPPED -- no frozen files given (--frozen or manifest)")

    if report_paths:
        checks_run.append("Report Validation")
        required_sections = args.required_sections or DEFAULT_REQUIRED_SECTIONS
        ok, details = check_reports(report_paths, required_sections)
        print("\n[Report Validation]")
        for line in details:
            print(f"  {line}")
        if not ok:
            overall_ok = False
            exit_code = exit_code or 6
            failed_categories.append("report")
    else:
        print("\n[Report Validation] SKIPPED -- no reports given (--reports or manifest)")

    if args.allow_dirty:
        print("\n[Repository Integrity] SKIPPED -- --allow-dirty passed")
    else:
        checks_run.append("Repository Integrity")
        ok, details = check_git_clean()
        print("\n[Repository Integrity]")
        for line in details:
            print(f"  {line}")
        if not ok:
            overall_ok = False
            exit_code = exit_code or 8
            failed_categories.append("repository_integrity")

    if scientific_claim_tier in ("T-COMP", "T-CAUSAL"):
        checks_run.append("Mandatory Mechanical Gate (T-COMP/T-CAUSAL)")
        print(f"\n[Mandatory Mechanical Gate] scientific_claim_tier: {scientific_claim_tier}")
        gate_ok, gate_details = _run_mandatory_gate(
            args.contract or "unknown", report_paths, required_verification_commands,
        )
        for line in gate_details:
            print(f"  {line}")
        if not gate_ok:
            overall_ok = False
            exit_code = exit_code or 17
            failed_categories.append("mandatory_gate")
    elif scientific_claim_tier:
        print(f"\n[Mandatory Mechanical Gate] SKIPPED -- scientific_claim_tier is "
              f"'{scientific_claim_tier}' (T-DESC), not T-COMP/T-CAUSAL.")

    # v2.2.0 (D-034) -- Fail-Closed Tier Inference. Runs regardless of what
    # scientific_claim_tier currently reads, precisely because its job is to
    # catch the case where that field itself is wrong (too low). Only runs
    # when a contract file is actually locatable -- `check` is also called
    # in contexts (e.g. a bare --frozen/--reports invocation with no
    # --contract) where there is no contract prose to scan; that is
    # reported as SKIPPED, not silently passed.
    contract_text_for_tier = None
    if args.contract:
        contract_path, _err = _find_contract_file(args.contract)
        if contract_path is not None:
            contract_text_for_tier = _read_text_or_none(contract_path)
    if contract_text_for_tier is not None:
        checks_run.append("Fail-Closed Tier Inference")
        declared_tier_for_check = scientific_claim_tier or "NONE"
        m = re.search(r'Scientific Claim Tier.*?:\s*\**\s*(NONE|T-DESC|T-COMP|T-CAUSAL)\b',
                      contract_text_for_tier, re.IGNORECASE)
        if m:
            declared_tier_for_check = m.group(1).upper()
        minimum_tier, strong_matches, _weak = _infer_minimum_scientific_claim_tier(contract_text_for_tier)
        print(f"\n[Fail-Closed Tier Inference] declared: {declared_tier_for_check}  inferred minimum: {minimum_tier}")
        if strong_matches:
            print(f"  Strong signal(s) matched: {strong_matches}")
        if _TIER_RANK[declared_tier_for_check] < _TIER_RANK[minimum_tier]:
            overall_ok = False
            exit_code = exit_code or 18
            failed_categories.append("tier_inference")
            print(
                f"  FAIL: declared '{declared_tier_for_check}' is weaker than inferred minimum "
                f"'{minimum_tier}'. Run `gatekeeper.py tier-check --contract {args.contract}` "
                f"for the full explanation and remediation."
            )
        else:
            print("  OK.")
    else:
        print("\n[Fail-Closed Tier Inference] SKIPPED -- no --contract given, or its contract file "
              "was not found (run `gatekeeper.py tier-check` directly once it exists).")

    print("\n" + "=" * 60)
    if len(failed_categories) > 1:
        print(f"Failure categories: {failed_categories}")
    print(f"Checks executed: {checks_run if checks_run else '(none -- nothing was actually checked)'}")
    print(
        "NOT implemented in this script (still AI-attested only): "
        "Bootstrap Validation, Manifest Validation, Contract Validation, "
        "Allowed File Validation, Verification Script Validation, "
        "Dynamic Rule Validation, Bootstrap Compliance, full Git Validation. "
        "(v1.4.2 amendment: the Mandatory Mechanical Gate above IS mechanically enforced "
        "for T-COMP/T-CAUSAL contracts -- it is not on this AI-attested-only list.)"
    )
    print(f"RESULT: {'PASS' if overall_ok else 'FAIL'}")
    print(f"Exit code: {exit_code}")

    sys.exit(exit_code)


# v1.3.4 -- self-check reads these repo-root-relative files if present.
# All reads are best-effort: a missing file is reported as a finding, not a
# crash, since self-check's whole purpose is to surface exactly this kind
# of drift.
SELF_CHECK_FILES = {
    "gatekeeper_spec": Path("factory/gatekeeper_spec.md"),
    "factory_spec": Path("factory/factory_spec.md"),
    "version": Path("factory/VERSION"),
    "changelog": Path("factory/CHANGELOG.md"),
    # v2.2.0 -- architect_spec.md/implementor_spec.md are the primary role
    # documents as of this version (see CHANGELOG.md's v2.2.0 entry); the
    # gemini_spec/claude_init keys are kept, pointed at the same two role
    # documents were the old names retired outright, self-check would start
    # reporting every pre-v2.2 self_check_files reference to them as drift
    # rather than a deliberate rename. The legacy filenames themselves
    # (factory/ClaudeInitialization.md, factory/gemini_spec.md) still exist
    # on disk too, as short pointer files -- see bootstrap_manifest.yaml.
    "gemini_spec": Path("factory/implementor_spec.md"),
    "claude_init": Path("factory/architect_spec.md"),
    "implementor_spec": Path("factory/implementor_spec.md"),
    "architect_spec": Path("factory/architect_spec.md"),
    "domain_checklists": Path("factory/domain_checklists.md"),
    # v1.4.1 -- added after these two were found to have drifted (Factory
    # Version headers stuck at 1.3.4 through two full release cycles)
    # while _self_check_version_currency ran clean, because neither file
    # was in this dict at all. The check was correct; its target list was
    # incomplete. Found by direct inspection, not by self-check itself --
    # exactly the failure mode this dict's completeness exists to prevent.
    "constitution": Path("factory/constitution.md"),
    "dynamic_rules": Path("factory/dynamic_rules.md"),
    # v1.4.2 -- the same gap, found again, in the two files SELF_CHECK_FILES
    # itself lives in. gatekeeper.py's own module docstring ("STATUS
    # (Factory vX.Y.Z)") and bootstrap_manifest.yaml's factory.version
    # field are both live version references that nothing was checking --
    # this dict cannot monitor a file it doesn't list, including its own
    # host file. Found by direct inspection during a routine review, not
    # by self-check itself, exactly as before. bootstrap_manifest.yaml's
    # SEPARATE bootstrap_manifest_version field is deliberately excluded
    # from what the version-currency regex matches (see
    # _VERSION_HEADER_RE) -- that field versions the manifest schema
    # independently of the Factory version by the manifest's own stated
    # design and must not be flagged just because it differs from VERSION.
    "gatekeeper": Path("factory/gatekeeper.py"),
    "bootstrap_manifest": Path("factory/bootstrap_manifest.yaml"),
}

# Recognized argparse subcommand names, kept as a plain list rather than
# introspected from the parser object, so self-check has no import-order
# dependency on main() having run yet.
IMPLEMENTED_COMMANDS = [
    "snapshot", "snapshot-chunk", "next", "sort-dropbox", "stage-takethis",
    "clear-takethis", "materialize", "commit-project", "check", "self-check",
    "release-check", "acquisition-audit", "evidence-check",
    "verify-contract", "lint-contract", "recompute", "stamp-report", "verify-stamps",
    # v2.2.0
    "tier-check", "release-certify",
]

# Exit codes this script actually emits, per its own module docstring.
IMPLEMENTED_EXIT_CODES = {0, 4, 6, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19}

_CONTRACT_ID_SHAPED_RE = re.compile(r'\bC\d+-\d+\b')
_VALID_CONTRACT_ID_RE = re.compile(r'^C\d{2}-\d{2}$')
_VERSION_HEADER_RE = re.compile(
    # v1.4.2: added the `^[ \t]*version:` alternative (with MULTILINE) so
    # bootstrap_manifest.yaml's YAML `version: "X.Y.Z"` field is caught.
    # Anchored to line-start so it matches only a standalone `version:`
    # key, never `bootstrap_manifest_version:` -- the latter has no
    # whitespace-only prefix before "version:" on its own line (the
    # "bootstrap_manifest_" text sits between the line start and the
    # literal token "version:"), so it cannot satisfy `^[ \t]*version:`
    # regardless of its value. Verified by
    # test_gatekeeper_v1_4_2.py::test_independently_versioned_manifest_schema_field_is_never_flagged.
    r'(?:Factory Version\s*\n+\s*|as of v|Factory v|\*\*Version:\*\*\s*|^[ \t]*version:\s*["\']?)(\d+\.\d+\.\d+)',
    re.IGNORECASE | re.MULTILINE
)


def _read_text_or_none(path: Path):
    try:
        return path.read_text(errors="replace")
    except OSError:
        return None


def _self_check_implemented_vs_specified():
    """Diff target 1: implemented commands/exit codes vs. gatekeeper_spec.md's
    Implementation Status section. Returns list[str] findings."""
    findings = []
    spec_text = _read_text_or_none(SELF_CHECK_FILES["gatekeeper_spec"])
    if spec_text is None:
        findings.append(
            f"CANNOT CHECK: {SELF_CHECK_FILES['gatekeeper_spec']} not found -- "
            f"skipping Implemented vs. specified diff."
        )
        return findings

    spec_lower = spec_text.lower()

    # Every implemented command should be named somewhere in the spec's
    # Implementation Status section (a command implemented but never
    # disclosed is exactly the failure mode C01/gatekeeper_spec.md's own
    # Implementation Status section exists to prevent).
    for cmd in IMPLEMENTED_COMMANDS:
        cmd_variants = [cmd, cmd.replace("-", "_"), f"`{cmd}`"]
        if not any(v.lower() in spec_lower for v in cmd_variants):
            findings.append(
                f"UNDISCLOSED COMMAND: '{cmd}' is implemented in gatekeeper.py "
                f"but not mentioned anywhere in gatekeeper_spec.md's Implementation "
                f"Status section."
            )

    # Every exit code this script emits should appear in the spec's Exit
    # Codes table.
    exit_codes_section_idx = spec_lower.find("# exit codes")
    exit_codes_text = spec_text[exit_codes_section_idx:] if exit_codes_section_idx != -1 else spec_text
    for code in sorted(IMPLEMENTED_EXIT_CODES):
        if re.search(rf'(?<!\d){code}(?!\d)', exit_codes_text) is None:
            findings.append(
                f"UNDOCUMENTED EXIT CODE: gatekeeper.py can exit {code}, but "
                f"that code was not found in gatekeeper_spec.md's Exit Codes table."
            )

    return findings


def _self_check_artifact_lifecycle():
    """Diff target 2: for each row in factory_spec.md's Artifact Lifecycle
    table, check whether the declared producer has a corresponding
    instruction in gemini_spec.md or ClaudeInitialization.md. Returns
    list[str] findings.

    This is necessarily a heuristic, not a semantic check (self-check
    performs no AI reasoning, per Gatekeeper's own Verification Principles)
    -- it looks for the artifact's filename mentioned somewhere in the
    producer-facing instruction document, nothing more. A miss here is a
    prompt to look closer, not a proven gap.
    """
    findings = []
    factory_spec_text = _read_text_or_none(SELF_CHECK_FILES["factory_spec"])
    if factory_spec_text is None:
        findings.append(
            f"CANNOT CHECK: {SELF_CHECK_FILES['factory_spec']} not found -- "
            f"skipping Artifact Lifecycle diff."
        )
        return findings

    gemini_text = _read_text_or_none(SELF_CHECK_FILES["gemini_spec"]) or ""
    claude_init_text = _read_text_or_none(SELF_CHECK_FILES["claude_init"]) or ""
    combined_instructions = (gemini_text + "\n" + claude_init_text).lower()

    # Match Markdown table rows of the form "| artifact.ext | Producer | ... |"
    row_re = re.compile(r'^\|\s*([\w.]+\.\w+)\s*\|\s*([^|]+?)\s*\|', re.MULTILINE)
    for m in row_re.finditer(factory_spec_text):
        artifact, producer = m.group(1), m.group(2).strip()
        if producer.lower() in ("artifact", "---", ""):
            continue
        if "gemini" in producer.lower() or "claude" in producer.lower():
            if artifact.lower() not in combined_instructions:
                findings.append(
                    f"NO OPERATIVE INSTRUCTION: factory_spec.md's Artifact Lifecycle "
                    f"table lists '{artifact}' as produced by '{producer}', but "
                    f"'{artifact}' was not found in gemini_spec.md or "
                    f"ClaudeInitialization.md -- there may be no instruction telling "
                    f"that role to actually produce it."
                )

    return findings


def _self_check_version_currency():
    """Diff target 3: every document's embedded 'Factory Version' / 'as of
    vX.Y.Z' reference vs. VERSION and CHANGELOG.md's latest entry. Returns
    list[str] findings."""
    findings = []
    version_text = _read_text_or_none(SELF_CHECK_FILES["version"])
    if version_text is None:
        findings.append(
            f"CANNOT CHECK: {SELF_CHECK_FILES['version']} not found -- "
            f"skipping Version currency diff."
        )
        return findings

    current_version = version_text.strip()

    docs_to_scan = {
        name: path for name, path in SELF_CHECK_FILES.items()
        if name not in ("version", "changelog")
    }
    for name, path in docs_to_scan.items():
        text = _read_text_or_none(path)
        if text is None:
            continue
        stale = [
            v for v in set(_VERSION_HEADER_RE.findall(text))
            if v != current_version
        ]
        if stale:
            findings.append(
                f"STALE VERSION REFERENCE: {path} references version(s) "
                f"{sorted(stale)} but VERSION is {current_version!r}. This may be "
                f"an intentional historical reference (e.g. 'introduced in v1.3.0') "
                f"-- self-check cannot distinguish that from real staleness, so "
                f"confirm by reading context before editing."
            )

    return findings


def _self_check_naming_convention():
    """Diff target 4: extract C\\d+-\\d+-shaped IDs from worked examples
    inside spec documents; flag any that don't match ^C\\d{2}-\\d{2}$.
    Returns list[str] findings."""
    findings = []
    for name, path in SELF_CHECK_FILES.items():
        if name in ("version", "changelog"):
            continue
        text = _read_text_or_none(path)
        if text is None:
            continue
        bad_ids = sorted(set(
            m for m in _CONTRACT_ID_SHAPED_RE.findall(text)
            if not _VALID_CONTRACT_ID_RE.match(m)
        ))
        if bad_ids:
            findings.append(
                f"NAMING CONVENTION: {path} contains contract-ID-shaped string(s) "
                f"not matching ^C\\d{{2}}-\\d{{2}}$: {bad_ids}. Unpadded IDs like "
                f"'C3-01' are valid *input* to gatekeeper.py (it falls back to the "
                f"padded form) but should not appear in worked examples, which set "
                f"the pattern a future Architect copies."
            )
    return findings


def cmd_self_check(args):
    """v1.3.4 -- diagnostic only. Reports diffs between what gatekeeper.py
    actually does and what the Factory's own documents claim it does.
    Never modifies any file. Runs all four diff targets from
    v1_3_4_candidate_spec.md section 3 and prints every finding; an empty
    finding list for a target is reported as such, not silently skipped.
    """
    print("Gatekeeper self-check (diagnostic only -- reports diffs, never auto-fixes)")
    print("=" * 60)

    targets = [
        ("Implemented vs. specified", _self_check_implemented_vs_specified),
        ("Artifact Lifecycle vs. operative instructions", _self_check_artifact_lifecycle),
        ("Version currency", _self_check_version_currency),
        ("Naming-convention lint", _self_check_naming_convention),
    ]

    total_findings = 0
    for label, fn in targets:
        print(f"\n[{label}]")
        findings = fn()
        if not findings:
            print("  No drift found.")
        else:
            for f in findings:
                print(f"  - {f}")
            total_findings += len(findings)

    print("\n" + "=" * 60)
    print(f"Total findings: {total_findings}")
    print(
        "Evidence posture: unit-tested against synthetic drift scenarios, not yet "
        "run against a real project's full document set beyond the audit that "
        "produced v1.3.4 itself. Findings are prompts to look closer, not proven "
        "defects -- self-check performs no AI reasoning and can produce false "
        "positives (e.g. an intentional historical version reference)."
    )
    # Diagnostic tool: findings are reported, never treated as a failing
    # exit code. A non-zero exit here would make self-check itself a gate,
    # which is out of scope for a v1.3.x patch release (see v1.3.4 spec
    # section 0's C50 gate).
    sys.exit(0)


# ---------------------------------------------------------------------------
# release-check (v1.4.0) -- scans an outbound release artifact (a
# manuscript, REPRODUCIBILITY.md, supplementary material) before it leaves
# the repository. Two checks, kept in one command per C46 (both are "scan
# an outbound artifact before it ships"): a local-path/machine-identity
# scan (hard FAIL, unambiguous), and a key-fact consistency check against a
# project-declared key_facts.md (WARNING -- heuristic).
#
# Neither check performs semantic understanding of the manuscript's prose.
# Per Gatekeeper's own Verification Principles ("Gatekeeper never performs
# AI reasoning"), the fact-consistency check only catches drift against
# facts the Architect explicitly declared ahead of time in key_facts.md --
# it is not an open-ended fact-checker, and cannot be, without violating
# Gatekeeper's own Purpose. See v1_4_0_scientific_validity_layer.md Part 5,
# and D-017.
# ---------------------------------------------------------------------------

_LOCAL_PATH_RE = re.compile(
    r'(?:/Users/|/home/|[A-Za-z]:\\Users\\)[^\s"\')\]<>,;]+'
)

_KEY_FACT_HEADER_RE = re.compile(r'^##\s*Key Fact:.*$', re.MULTILINE)
_KEY_FACT_FIELD_RE = re.compile(
    r'anchor:\s*(?P<anchor>.+?)\s*$.*?'
    r'expected_value:\s*(?P<value>-?\d+(?:\.\d+)?)\s*$'
    r'(?:.*?tolerance:\s*(?P<tolerance>-?\d+(?:\.\d+)?)\s*$)?',
    re.MULTILINE | re.DOTALL
)

_NUMBER_NEAR_RE_TEMPLATE = r'.{{0,60}}\b{anchor}\b.{{0,60}}'
_BARE_NUMBER_RE = re.compile(r'-?\d+(?:\.\d+)?')


def _scan_local_paths(file_paths):
    """Returns list[str] findings: any /Users/, /home/, or C:\\Users\\
    absolute path found in any given file. Deterministic substring/regex
    match only -- no judgement about whether a given path is "legitimate"
    (e.g. deliberately documenting a specific deployment target); that
    call is left to whoever reads the finding.
    """
    findings = []
    for fp in file_paths:
        p = Path(fp)
        text = _read_text_or_none(p)
        if text is None:
            findings.append(f"CANNOT CHECK: {fp} not found -- skipping local-path scan for this file.")
            continue
        matches = sorted(set(_LOCAL_PATH_RE.findall(text)))
        for m in matches:
            findings.append(
                f"LOCAL PATH LEAK: {fp} contains an absolute local filesystem path "
                f"'{m}' -- this will not resolve on a reader's machine. Replace with "
                f"a repository-relative path."
            )
    return findings


def _parse_key_facts(key_facts_path):
    """Parses key_facts.md's '## Key Fact: ...' blocks into a list of
    dicts: {anchor, value, tolerance}. Each block runs from its '## Key
    Fact:' header to the next '## ' header or end of file. A block missing
    'anchor:' or 'expected_value:' is reported as malformed, not silently
    dropped -- a Key Fact the Architect intended to declare but mistyped
    should never fail open. Returns (facts_or_None, findings)."""
    text = _read_text_or_none(Path(key_facts_path))
    if text is None:
        return None, [f"CANNOT CHECK: {key_facts_path} not found -- skipping key-fact consistency check."]

    headers = list(_KEY_FACT_HEADER_RE.finditer(text))
    facts = []
    findings = []
    for i, h in enumerate(headers):
        block_end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
        block = text[h.end():block_end]
        m = _KEY_FACT_FIELD_RE.search(block)
        if m is None or m.group("anchor") is None or m.group("value") is None:
            findings.append(
                f"MALFORMED KEY FACT: '{h.group().strip()}' in {key_facts_path} is "
                f"missing an 'anchor:' or 'expected_value:' line -- skipped, not checked."
            )
            continue
        facts.append({
            "anchor": m.group("anchor").strip(),
            "value": float(m.group("value")),
            "tolerance": float(m.group("tolerance")) if m.group("tolerance") else 0.0,
        })
    return facts, findings


def _check_key_fact_consistency(manuscript_path, key_facts_path):
    """Returns list[str] findings. For each declared key fact, searches the
    manuscript for the anchor phrase; if a nearby number differs from the
    declared value by more than its tolerance, flags a mismatch. Bounded
    and heuristic by design (see module comment above) -- catches drift
    only against facts the Architect explicitly declared, and can
    false-positive when two genuinely distinct quantities share an anchor
    word (e.g. water volume released vs. moraine volume collapsed both
    containing the word "volume") -- findings are framed as requiring
    human confirmation, not proven defects.
    """
    findings = []
    facts, parse_findings = _parse_key_facts(key_facts_path)
    findings += parse_findings
    if facts is None:
        return findings
    if not facts:
        findings.append(
            f"CANNOT CHECK: {key_facts_path} exists but declares no '## Key Fact:' "
            f"blocks -- nothing to check consistency against."
        )
        return findings

    manuscript_text = _read_text_or_none(Path(manuscript_path))
    if manuscript_text is None:
        findings.append(f"CANNOT CHECK: {manuscript_path} not found -- skipping key-fact consistency check.")
        return findings

    for fact in facts:
        window_re = re.compile(
            _NUMBER_NEAR_RE_TEMPLATE.format(anchor=re.escape(fact["anchor"])),
            re.IGNORECASE | re.DOTALL,
        )
        mismatched_numbers = set()
        for window in window_re.findall(manuscript_text):
            for num_str in _BARE_NUMBER_RE.findall(window):
                if abs(float(num_str) - fact["value"]) > fact["tolerance"]:
                    mismatched_numbers.add(num_str)
        if mismatched_numbers:
            findings.append(
                f"KEY FACT MISMATCH: near '{fact['anchor']}', {manuscript_path} contains "
                f"number(s) {sorted(mismatched_numbers)} that differ from the declared "
                f"value {fact['value']} (tolerance {fact['tolerance']}) in {key_facts_path}. "
                f"This may be a real inconsistency, or two genuinely different quantities "
                f"that happen to share an anchor word -- confirm by reading context before "
                f"treating this as a defect."
            )
    return findings


# ---------------------------------------------------------------------------
# acquisition-audit (v1.4.0) -- scans data-acquisition scripts and their
# contract reports for red-flag patterns before their output is trusted.
# Two checks, kept in one command per C46 (both are "grep acquisition-
# related files for a pattern that demands investigation"): a structural
# audit for data-generation function definitions (hard FAIL -- D-022), and
# a textual scan for simulation-indicating language (WARNING -- D-023).
#
# Motivated by a real incident (Chunk 07, GLOF project rework): an
# acquisition script contained a function literally named
# `generate_fallback_timeseries`, called when the target API was
# unreachable, producing simulated data that passed every Reality Gate
# property check because the simulator was designed to produce realistic
# properties. The Architect caught it only by reading free-text output and
# noticing the word "synthesize" -- this command makes that catch
# deterministic. See dynamic_rules.md D-022, D-023.
#
# Like release-check's key-fact check, the textual scan is bounded and
# heuristic by design: some flagged words have legitimate uses ("generated
# thumbnail"), so matches are reported for human review, not treated as
# proven fabrication. The structural check is closer to unambiguous -- an
# acquisition script has no legitimate reason to define a function named
# generate_/simulate_/synthesize_/fallback_/mock_/fake_ -- but a determined
# fabricator could still choose a non-obvious name; this catches the common
# case, not every case (see v1_4_0_scientific_validity_layer.md's Part 12
# analogue, and dynamic_rules.md's "What Still Cannot Be Caught" note).
# ---------------------------------------------------------------------------

_ACQUISITION_FUNCTION_RE = re.compile(
    r'^\s*def\s+(generate_|simulate_|synthesize_|fallback_|mock_|fake_)\w*\s*\(',
    re.MULTILINE
)

_ACQUISITION_TEXT_RE = re.compile(
    r'\b(synthesize[sd]?|simulated|generated|fallback|mock(?:ed)?|synthetic'
    r'|offline[\s_-]*data|placeholder[\s_-]*data)\b',
    re.IGNORECASE
)

# v1.4.2 -- second structural sub-check, added to this command rather than
# as a new one (C46: improve an existing component before adding a new
# one). D-022's check catches a script that fabricates data because an
# *external* constraint blocked real acquisition (Chunk 07: API
# unreachable). This catches a related but distinct pattern with no
# external constraint at all: a script that is supposed to compute a
# metric/statistic over real per-observation data instead manufactures
# its own substitute observations from a random distribution and feeds
# those into the metric call directly. Real incident: GLOF project
# rework, Chunk 08, contract C08-06 (`run_bootstrap_ci.py`) -- read only
# the already-aggregated scalar auc_roc from
# evaluation_summary_real_data.json, then fabricated per-window scores
# via `rng.normal(...)` shaped to approximate that AUC, then bootstrapped
# and DeLong-tested the fabricated values. The resulting CIs and
# p-values were reported in statistical_significance.json, traced by
# claim_evidence_map.json (CL-16 through CL-21), and appear in
# sentinel_gl_manuscript.md's abstract and RQ3 result -- reproduced
# independently: running the real script against its real input with its
# own documented seed produced a byte-identical artifact to the one that
# shipped. Caught only by a later adversarial audit; `check_reports`,
# `evidence-check`, and `release-check` all operate on an artifact's own
# declared values and would not have caught this, because the artifact
# is internally self-consistent -- the fabrication happened one step
# upstream, in what produced the artifact. See dynamic_rules.md D-028.
#
# File-level co-occurrence, not proven data-flow: this does not trace
# whether the specific value passed to the metric function definitely
# originated from the distribution-sampling call (that would require an
# AST/data-flow analysis Gatekeeper's own Purpose -- deterministic,
# bounded, no AI reasoning -- does not rule out in principle, but which
# is a materially bigger undertaking than any existing check performs;
# not attempted here). A script that calls a distribution sampler
# (.normal/.uniform/.randn) anywhere in the same file as a call to a
# recognized metrics function (roc_auc_score, precision_recall_curve,
# roc_curve, f1_score, average_precision_score) is flagged. This can
# false-positive on a file that legitimately does both for unrelated
# reasons (e.g. a bundled power-analysis helper); that is why this is
# reported with exact file:line locations for human confirmation, the
# same posture as D-022's function-name check, not treated as
# infallible.
_DISTRIBUTION_SAMPLING_RE = re.compile(
    r'\b(\w+)\s*=\s*(?:np\.random\.|numpy\.random\.|rng\.)'
    r'(normal|uniform|randn|standard_normal)\s*\('
)

_METRIC_FUNCTION_CALL_RE = re.compile(
    r'\b(roc_auc_score|precision_recall_curve|roc_curve|f1_score|average_precision_score)\s*\('
)


def _scan_fabricated_statistical_input(script_paths):
    """v1.4.2, D-028. Returns list[str] findings: a script that calls a
    distribution-sampling method anywhere in the same file as a call to a
    recognized metrics function. Deterministic regex co-occurrence check
    only -- see the module comment above this function for exactly what
    it does and does not prove."""
    findings = []
    for sp in script_paths:
        text = _read_text_or_none(Path(sp))
        if text is None:
            findings.append(f"CANNOT CHECK: {sp} not found -- skipping fabrication audit for this file.")
            continue
        sampling_matches = list(_DISTRIBUTION_SAMPLING_RE.finditer(text))
        if not sampling_matches:
            continue
        if _METRIC_FUNCTION_CALL_RE.search(text) is None:
            continue
        for m in sampling_matches:
            line_no = text[:m.start()].count("\n") + 1
            findings.append(
                f"FABRICATED STATISTICAL INPUT: {sp}:{line_no} assigns '{m.group(1)}' from "
                f"a distribution sampler ({m.group(2)}(...)), and this file also calls a "
                f"metrics function ({', '.join(sorted(set(mm.group(1) for mm in _METRIC_FUNCTION_CALL_RE.finditer(text))))}). "
                f"A script computing a real metric/statistic has no legitimate reason to "
                f"manufacture its own per-observation values (C01) -- confirm '{m.group(1)}' "
                f"does not feed the metric computation before trusting this script's output."
            )
    return findings


def _scan_acquisition_functions(script_paths):
    """Returns list[str] findings: any function definition matching a
    data-generation naming pattern in an acquisition script. Deterministic
    regex match only -- catches the common case (an honestly- or
    carelessly-named fallback function), not a deliberately obfuscated one.
    """
    findings = []
    for sp in script_paths:
        text = _read_text_or_none(Path(sp))
        if text is None:
            findings.append(f"CANNOT CHECK: {sp} not found -- skipping structural audit for this file.")
            continue
        for m in _ACQUISITION_FUNCTION_RE.finditer(text):
            line_no = text[:m.start()].count("\n") + 1
            findings.append(
                f"DATA-GENERATION FUNCTION: {sp}:{line_no} defines a function matching "
                f"'{m.group(1)}*' -- an acquisition script has no legitimate reason to "
                f"generate, simulate, synthesize, mock, or fake data (C54). Investigate "
                f"before trusting this script's output."
            )
    return findings


def _scan_acquisition_text(text_paths):
    """Returns list[str] findings: simulation-indicating words found in
    acquisition scripts or contract reports. Heuristic -- some matches are
    legitimate ("generated thumbnail"); every finding names the exact word
    and location so a human can judge context quickly, per C39."""
    findings = []
    for tp in text_paths:
        text = _read_text_or_none(Path(tp))
        if text is None:
            findings.append(f"CANNOT CHECK: {tp} not found -- skipping textual scan for this file.")
            continue
        matches = sorted(set(m.group(0).lower() for m in _ACQUISITION_TEXT_RE.finditer(text)))
        if matches:
            findings.append(
                f"SIMULATION-INDICATING LANGUAGE: {tp} contains {matches} -- may be "
                f"legitimate ('generated thumbnail') or may indicate undisclosed data "
                f"substitution (D-023, the Chunk 07 pattern). Read context before judging."
            )
    return findings


# ---------------------------------------------------------------------------
# tier-check (v2.2.0, D-034) -- fail-closed minimum Scientific Claim Tier
# inference. Every mechanism this Factory has for scientific rigor (the
# T-COMP/T-CAUSAL baseline/significance/adversarial-test requirements, v1.4.0;
# the Mandatory Mechanical Gate, v1.4.2/D-032) is keyed off a contract's own
# self-declared scientific_claim_tier field. Nothing before v2.2 checked
# whether that self-declaration was actually low. A contract whose own text
# plainly describes a comparative or statistical claim can declare
# scientific_claim_tier: NONE (or omit it) and every one of those mechanisms
# silently does not apply -- not because they failed, but because they were
# never triggered.
#
# This is not hypothetical: project/chunks/chunk06/contracts/C06-03_contract.md
# in the uploaded factory_v1.5.0 TDLCR test project -- "Pre-Registered
# Hypothesis Evaluator & Result Registry Compiler," whose own Implementation
# Instructions name a Wilcoxon significance test, a Cliff's delta effect
# size, and SUPPORTED/FALSIFIED/INCONCLUSIVE verdicts feeding
# project/result_registry.json for IEEE publication -- declares
# `Scientific Claim Tier: NONE`, with a Verification Scripts entry that only
# confirms the module imports cleanly. Under v1.4.2/v2.1 alike, nothing
# mechanical would have caught that before Chunk Review. See CHANGELOG.md's
# v2.2.0 entry and dynamic_rules.md D-034 for the full account.
#
# Deliberately narrow, matching this file's existing posture for every other
# heuristic text scan (D-023's simulation-indicating language,
# D-028's fabrication co-occurrence check): this is keyword/pattern matching
# over a contract's own Objective/Context/Implementation Instructions/Outputs
# text, not semantic understanding. It can and will false-positive (a
# contract implementing a metrics *computation* utility, never itself making
# a comparative claim, may mention "F1" or "AUC" in passing) and it can
# false-negative (a claim phrased with no matched keyword at all). Every
# finding names the exact matched text so a human/Architect can judge context
# quickly, per C39 -- this is a floor under self-declaration, not a
# replacement for the Architect's own judgment at Chunk Planning.
#
# Ordering for comparison purposes: NONE < T-DESC < T-COMP < T-CAUSAL.
_TIER_RANK = {"NONE": 0, "T-DESC": 1, "T-COMP": 2, "T-CAUSAL": 3}

# Strong signals: specific enough that a contract matching one of these and
# still declaring NONE/T-DESC is very likely under-tiered, not a false
# positive. Named statistical tests/effect sizes, explicit p-value/CI
# notation, and pre-registered-verdict language (SUPPORTED/FALSIFIED/
# INCONCLUSIVE, the exact vocabulary factory_spec.md's Scientific Claim Tier
# table and venue_requirements.md's falsification criteria already use).
_TCOMP_STRONG_RE = re.compile(
    r'\b(wilcoxon|mann-?whitney|delong|paired\s+t-test|unpaired\s+t-test|'
    r'student.?s?\s+t-test|anova|chi-square|kruskal-?wallis|'
    r'cliff.?s?\s*delta|cohen.?s?\s*d\b|hedges.?\s*g|'
    r'p\s*[<>=]\s*0?\.\d+|p-value|confidence\s+interval|\bCI\s*[:=]|'
    r'outperforms?|out-performs?|statistically\s+significant|'
    r'SUPPORTED\s*/\s*FALSIFIED|FALSIFIED\s*/\s*INCONCLUSIVE|'
    r'pre-?registered\s+(?:hypothesis|criteri|falsification)|'
    r'effect\s+size)\b',
    re.IGNORECASE,
)

# Strong T-CAUSAL signals: robustness/causal/ablation claims specifically --
# distinct from T-COMP because factory_spec.md requires an adversarial test
# and a declared Stop Condition for these, not just baselines + significance.
_TCAUSAL_STRONG_RE = re.compile(
    r'\b(robust(?:ness)?\s+to|adversarial(?:ly)?\s+(?:test|robust|attack)|'
    r'is\s+robust|enables?\s+\w+\s+to|causally?|ablation\s+stud|'
    r'invariant\s+to|generalizes?\s+to\s+(?:unseen|out-of-distribution))\b',
    re.IGNORECASE,
)

# Weaker signals: bare metric/comparison vocabulary that is common in
# ordinary engineering work too (a contract implementing a scorer utility,
# for instance). Matching one of these alone is a WARNING nudge toward
# reviewing the tier, never a hard failure on its own.
_TCOMP_WEAK_RE = re.compile(
    r'\b(baselines?|benchmarks?|\bAUC\b|\bAUPRC\b|\bF1\b|precision|recall|'
    r'accuracy|hypothes(?:is|es)|result_registry|ablation\s+matrix)\b',
    re.IGNORECASE,
)

# Operation-class conflation (v2.2.0, D-035): a contract whose Objective
# opens with an implementation verb but whose Outputs/Definition of Done
# also promises a specific empirical/statistical result is exactly the
# "implement a benchmark runner and treat that as having run the benchmark"
# pattern DESIGN_RATIONALE-class review documents describe. Heuristic and
# WARNING-only -- plenty of contracts legitimately implement one stage of a
# pipeline whose *later* contract makes the claim; this only flags when both
# signals land in the same contract text.
_IMPLEMENTATION_VERB_RE = re.compile(
    r'^\s*(?:Implement|Build|Write|Create|Add)\b', re.IGNORECASE | re.MULTILINE,
)

# Statistical protocol language heuristics (v2.2.0, D-036): known-bad
# co-occurrence patterns from the Design Rationale failure table -- pairing/
# effect-size mismatch and the non-significance-as-equivalence fallacy.
# String/pattern co-occurrence only, exactly the same evidentiary posture as
# D-028's fabrication scan: it flags a combination worth a human/Architect
# looking at, it does not itself adjudicate whether the statistics are
# actually wrong.
_NONSIG_RE = re.compile(
    r'\b(not\s+(?:statistically\s+)?significant|non-significant|'
    r'no\s+significant\s+(?:difference|effect)|p\s*>\s*0?\.\d+)\b',
    re.IGNORECASE,
)
_EQUIVALENCE_CLAIM_RE = re.compile(
    r'\b(equivalent|equivalence)\b', re.IGNORECASE,
)
_EQUIVALENCE_MARGIN_RE = re.compile(
    r'\b(equivalence\s+margin|TOST|two[\s-]one[\s-]sided|non-?inferiority)\b',
    re.IGNORECASE,
)
_PAIRING_LANGUAGE_RE = re.compile(
    r'\b(paired|unpaired|independent\s+samples|within-subject|between-subject)\b',
    re.IGNORECASE,
)

# Named mathematical/statistical operators (v2.2.0, D-037): the specific,
# recurring family of "operator does not mean what its name claims"
# failures named in the uploaded factory_v2.1.0 Design Rationale document
# (itself grounded in a real project's adversarial audit, per that
# document's own account) -- distinct from this Factory's own first-hand
# GLOF/BPFeat evidence trail elsewhere in this file, and cited as such
# rather than blended into it. A contract whose text names one of these and
# is tiered T-COMP/T-CAUSAL should carry at least one Verification Script
# whose name/declared purpose reads as a semantic/operator test, not only an
# I/O-shape test -- see the Fail-Closed Tier Inference gate below and
# domain_checklists.md's "Required review questions" for what such a test
# should actually establish.
_NAMED_OPERATOR_RE = re.compile(
    r'\b(laplacian|adjacency\s+matrix|witness\s+complex|filtration|'
    r'boundary\s+operator|persistent\s+homology|simplicial\s+complex|'
    r'batch(?:ing)?\s+semantics?|permutation\s+invariance|k-core)\b',
    re.IGNORECASE,
)
_SEMANTIC_TEST_MARKER_RE = re.compile(
    r'(semantic_|operator_|known_answer|metamorphic|invariance_test|'
    r'monotonic|boundary_nilpotence|test_.*(?:laplacian|filtration|'
    r'witness|adjacency|batch))',
    re.IGNORECASE,
)


def _infer_minimum_scientific_claim_tier(text):
    """Returns (minimum_tier, strong_matches, weak_matches). minimum_tier is
    one of "NONE", "T-DESC", "T-COMP", "T-CAUSAL".

    Per factory_spec.md's Scientific Claim Tier section, a tier is only
    required at all for a contract whose Outputs include a quantitative or
    comparative claim -- ordinary plumbing (a data loader, a CRUD endpoint,
    test scaffolding) legitimately declares NONE, and that must not be
    flagged. So: no signal at all infers NONE (nothing here suggests this
    contract makes any claim); a WEAK signal alone (a bare metric name,
    e.g. "computes F1 and accuracy") infers T-DESC -- reporting a metric
    value is itself an observational claim ("we observe X"), which
    factory_spec.md's table says needs at least an evidence artifact and
    traceability; a STRONG signal infers T-COMP or T-CAUSAL as before.
    Matches are returned so every finding can quote the exact text that
    triggered it, per C39."""
    strong_causal = sorted(set(m.group(0) for m in _TCAUSAL_STRONG_RE.finditer(text)))
    strong_comp = sorted(set(m.group(0) for m in _TCOMP_STRONG_RE.finditer(text)))
    weak_comp = sorted(set(m.group(0) for m in _TCOMP_WEAK_RE.finditer(text)))

    if strong_causal:
        return "T-CAUSAL", strong_causal, weak_comp
    if strong_comp:
        return "T-COMP", strong_comp, weak_comp
    if weak_comp:
        return "T-DESC", [], weak_comp
    return "NONE", [], []


def _scan_operation_class_conflation(text):
    """Returns list[str] WARNING findings (v2.2.0, D-035). Heuristic only --
    an Objective opening with an implementation verb, in a contract whose
    text also matches a strong T-COMP/T-CAUSAL signal, is worth a second
    look at whether this contract actually executes/measures the claim it
    describes or only builds the machinery that could."""
    findings = []
    if _IMPLEMENTATION_VERB_RE.search(text):
        _, strong_comp, _ = _infer_minimum_scientific_claim_tier(text)
        strong_causal = _TCAUSAL_STRONG_RE.search(text)
        if strong_comp or strong_causal:
            signal = (strong_causal.group(0) if strong_causal else strong_comp[0])
            findings.append(
                f"POSSIBLE OPERATION-CLASS CONFLATION: Objective opens with an "
                f"implementation verb ('Implement'/'Build'/'Write'/'Create'/'Add'), but "
                f"this contract's text also matches empirical/statistical claim language "
                f"('{signal}'). Confirm this contract actually executes/measures the "
                f"claim rather than only building something a later contract will use to "
                f"do so -- 'implement a benchmark runner' is not evidence the benchmark "
                f"was run (Design Rationale, AR-01/AR-06-class pattern)."
            )
    return findings


def _scan_statistical_protocol_language(text_paths):
    """Returns list[str] WARNING findings (v2.2.0, D-036). Two known-bad
    co-occurrence patterns, string/pattern matching only -- same posture as
    _scan_acquisition_text: flags a combination worth a human/Architect
    reading in context, never adjudicates the statistics itself."""
    findings = []
    for tp in text_paths:
        text = _read_text_or_none(Path(tp))
        if text is None:
            findings.append(f"CANNOT CHECK: {tp} not found -- skipping statistical-protocol scan for this file.")
            continue
        if _NONSIG_RE.search(text) and _EQUIVALENCE_CLAIM_RE.search(text) and not _EQUIVALENCE_MARGIN_RE.search(text):
            findings.append(
                f"NON-SIGNIFICANCE TREATED AS EQUIVALENCE: {tp} contains both "
                f"non-significance language ('{_NONSIG_RE.search(text).group(0)}') and "
                f"equivalence language ('{_EQUIVALENCE_CLAIM_RE.search(text).group(0)}') "
                f"with no declared equivalence margin or TOST/non-inferiority test found. "
                f"Absence of a significant difference is not evidence of equivalence "
                f"without a pre-declared margin (Design Rationale failure table)."
            )
        strong_stats = _TCOMP_STRONG_RE.search(text)
        if strong_stats and not _PAIRING_LANGUAGE_RE.search(text):
            findings.append(
                f"PAIRING NOT DECLARED: {tp} names a statistical test/effect size "
                f"('{strong_stats.group(0)}') with no paired/unpaired/independent-samples "
                f"language found nearby. Confirm the test and effect size chosen are "
                f"actually compatible with how the samples were collected before trusting "
                f"the reported statistic."
            )
    return findings


def _scan_semantic_operator_test_presence(contract_text, declared_verification_text):
    """Returns list[str] WARNING findings (v2.2.0, D-037). Presence-only
    heuristic: for a contract whose text names a recognized mathematical/
    statistical operator, checks whether its Verification Scripts / declared
    verification commands contain a recognizable semantic-test marker.
    Cannot and does not check whether such a test, if present, actually
    establishes the operator's claimed property -- that remains Architect/
    Implementor judgment, per domain_checklists.md."""
    findings = []
    operator_matches = sorted(set(m.group(0) for m in _NAMED_OPERATOR_RE.finditer(contract_text)))
    if not operator_matches:
        return findings
    if not _SEMANTIC_TEST_MARKER_RE.search(declared_verification_text or ""):
        findings.append(
            f"NO SEMANTIC/OPERATOR TEST DECLARED: this contract's text names "
            f"{operator_matches}, but no Verification Script/declared command matches a "
            f"semantic-test naming pattern (semantic_*, operator_*, known_answer_*, "
            f"metamorphic_*, etc.). An I/O-shape test can pass while the named operator "
            f"is still mathematically wrong (e.g. a Laplacian that is actually an "
            f"adjacency matrix) -- see domain_checklists.md's review questions for what "
            f"this operator specifically needs validated."
        )
    return findings


def cmd_tier_check(args):
    """v2.2.0, D-034/D-035/D-036/D-037 -- fail-closed minimum Scientific
    Claim Tier inference, plus three related heuristic scans bundled into
    this command rather than three new ones (C46): operation-class
    conflation, statistical-protocol language, and semantic/operator test
    presence. Only the tier-inference check is a hard FAIL; the other three
    are WARNING-only, consistent with this script's existing Warning Policy
    for heuristic text scans. Exits 18 (Fail-Closed Tier Inference Failure)
    only if the declared tier is strictly weaker than the inferred minimum.
    """
    print("Gatekeeper tier-check (fail-closed minimum Scientific Claim Tier inference)")
    print("=" * 60)

    contract_text = None
    contract_source = None
    if args.contract_file:
        contract_text = _read_text_or_none(Path(args.contract_file))
        contract_source = args.contract_file
    elif args.contract:
        contract_path, err = _find_contract_file(args.contract)
        if contract_path is None:
            print(f"\nERROR: {err}")
            sys.exit(9)
        contract_text = _read_text_or_none(contract_path)
        contract_source = str(contract_path)
    else:
        print("\nERROR: one of --contract or --contract-file is required.")
        sys.exit(9)

    if contract_text is None:
        print(f"\nERROR: could not read {contract_source}.")
        sys.exit(9)

    declared_tier = args.declared_tier
    if declared_tier is None:
        m = re.search(r'Scientific Claim Tier.*?:\s*\**\s*(NONE|T-DESC|T-COMP|T-CAUSAL)\b',
                      contract_text, re.IGNORECASE)
        declared_tier = m.group(1).upper() if m else "NONE"
    declared_tier = declared_tier.upper()
    if declared_tier not in _TIER_RANK:
        print(f"\nERROR: --declared-tier '{declared_tier}' is not one of NONE/T-DESC/T-COMP/T-CAUSAL.")
        sys.exit(9)

    minimum_tier, strong_matches, weak_matches = _infer_minimum_scientific_claim_tier(contract_text)

    print(f"\n[Fail-Closed Tier Inference -- D-034]")
    print(f"  Contract: {contract_source}")
    print(f"  Declared Scientific Claim Tier: {declared_tier}")
    print(f"  Inferred minimum: {minimum_tier}")
    if strong_matches:
        print(f"  Strong signal(s) matched: {strong_matches}")
    if weak_matches:
        print(f"  Weak signal(s) matched (informational only): {weak_matches}")
    if not strong_matches and not weak_matches:
        print("  No empirical/statistical claim language matched.")

    hard_fail = _TIER_RANK[declared_tier] < _TIER_RANK[minimum_tier]
    if hard_fail:
        print(
            f"  FAIL: declared tier '{declared_tier}' is weaker than the inferred minimum "
            f"'{minimum_tier}'. Per Constitution C05-class fail-closed reasoning (see "
            f"dynamic_rules.md D-034): declared assurance may exceed but must never "
            f"undercut what the contract's own text implies. Re-declare "
            f"scientific_claim_tier at '{minimum_tier}' or higher in both the contract "
            f"file and execution_manifest.yaml, or revise the contract's own text if the "
            f"match is a false positive -- then re-run this check."
        )
    else:
        print(f"  OK: declared tier '{declared_tier}' meets or exceeds the inferred minimum.")

    warning_findings = _scan_operation_class_conflation(contract_text)
    print("\n[Operation-Class Conflation -- D-035]")
    if not warning_findings:
        print("  No conflation pattern matched.")
    else:
        for f in warning_findings:
            print(f"  - {f}")

    declared_verification_text = contract_text
    if args.reports:
        for rp in args.reports:
            rt = _read_text_or_none(Path(rp))
            if rt:
                declared_verification_text += "\n" + rt
    operator_findings = _scan_semantic_operator_test_presence(contract_text, declared_verification_text)
    print("\n[Semantic/Operator Test Presence -- D-037]")
    if not operator_findings:
        print("  No named operator matched, or a semantic-test marker was found.")
    else:
        for f in operator_findings:
            print(f"  - {f}")

    print("\n" + "=" * 60)
    print(
        "Evidence posture: D-034's tier inference is a keyword/pattern heuristic, unit-"
        "tested against the real project/chunks/chunk06/contracts/C06-03_contract.md "
        "text uploaded alongside this Factory version (Wilcoxon/Cliff's-delta/SUPPORTED-"
        "FALSIFIED-INCONCLUSIVE language, declared NONE) and against synthetic non-"
        "matching contracts. D-035/D-036/D-037 are WARNING-only and have zero project "
        "occurrences of their own -- filed as PROPOSED, not ACTIVE; see dynamic_rules.md. "
        "None of the four understands the contract's actual claim, only text patterns "
        "known to correlate with one."
    )
    print(f"RESULT: {'FAIL' if hard_fail else 'PASS'}")
    print(f"Exit code: {18 if hard_fail else 0}")
    sys.exit(18 if hard_fail else 0)


# ---------------------------------------------------------------------------
# evidence-check (v1.4.1) -- reads a contract report's structured "## Verdict
# Cross-Check" block and the JSON evidence artifact it names, and checks
# three things mechanically: does the report's stated verdict word match the
# artifact's own verdict field (D-024); does a declared pre-registered
# criterion, evaluated against the artifact's own numbers, actually support
# that verdict (D-025); and does the artifact's "metrics" list contain any
# degenerate value (exactly 0.0, 0.5, or 1.0, within tolerance) computed on
# too few samples (D-027, SVI-007).
#
# All three checks depend on a structured, declared format -- report prose
# is never parsed for meaning, and JSON is never interpreted beyond reading
# named keys. This is deliberate: per Gatekeeper's own Purpose ("Gatekeeper
# never performs AI reasoning"), a check that tried to understand arbitrary
# report prose or arbitrary natural-language criteria would not be
# deterministic. See factory_spec.md's Contract Specification (the Verdict
# Cross-Check block) and gemini_spec.md's contract report template for the
# format this command requires contracts to declare.
#
# Motivated by a real incident (Chunks 08-09, GLOF project rework): a
# contract report stated "Verdict: SUCCESS" while its own backing JSON
# artifact stated "f3_falsification_verdict": "FAILURE", and separately
# claimed SUCCESS while its own reported count (0 windows flagged) logically
# satisfied the pre-registered FAILURE criterion. Neither was caught by any
# verification script or by Gatekeeper -- only by a later adversarial audit.
# See dynamic_rules.md D-024, D-025, D-027.
# ---------------------------------------------------------------------------

_VERDICT_BLOCK_HEADER_RE = re.compile(r'^##\s*Verdict Cross-Check\s*$', re.MULTILINE)
_VERDICT_FIELD_RE = re.compile(r'^(\w+):\s*(.+?)\s*$', re.MULTILINE)

_DEGENERATE_VALUES = (0.0, 0.5, 1.0)
_DEGENERATE_TOLERANCE = 0.01
_DEGENERATE_MIN_SAMPLES = 30

_CRITERION_KINDS = {"count_gte", "count_lte", "value_gte", "value_lte", "bool_true", "bool_false", "none"}


def _load_json_or_none(path):
    text = _read_text_or_none(Path(path))
    if text is None:
        return None, f"CANNOT CHECK: {path} not found."
    try:
        return json.loads(text), None
    except json.JSONDecodeError as e:
        return None, f"CANNOT CHECK: {path} is not valid JSON ({e})."


def _get_json_path(data, key):
    """Looks up a possibly-dotted key ('a.b.c') in a nested dict. Returns
    (value, found_bool)."""
    node = data
    for part in key.split("."):
        if not isinstance(node, dict) or part not in node:
            return None, False
        node = node[part]
    return node, True


def _parse_verdict_block(report_path):
    """Finds the '## Verdict Cross-Check' block in a contract report and
    parses its declared fields. Returns (fields_dict_or_None, findings).
    A report with no such block is not an error -- not every contract has
    a pre-registered verdict to cross-check."""
    text = _read_text_or_none(Path(report_path))
    if text is None:
        return None, [f"CANNOT CHECK: {report_path} not found."]

    m = _VERDICT_BLOCK_HEADER_RE.search(text)
    if m is None:
        return None, []  # no block present -- nothing to check, not an error

    block_end = text.find("\n## ", m.end())
    block = text[m.end():block_end if block_end != -1 else len(text)]

    fields = {}
    for fm in _VERDICT_FIELD_RE.finditer(block):
        fields[fm.group(1)] = fm.group(2)

    findings = []
    if "verdict_word" not in fields or "artifact" not in fields or "artifact_key" not in fields:
        findings.append(
            f"MALFORMED VERDICT BLOCK: {report_path}'s '## Verdict Cross-Check' block is "
            f"missing 'verdict_word', 'artifact', or 'artifact_key' -- skipped, not checked."
        )
        return None, findings
    return fields, findings


def _check_verdict_consistency(report_path, fields):
    """D-024: does the report's declared verdict_word match the value at
    artifact_key inside the named JSON artifact?"""
    data, err = _load_json_or_none(fields["artifact"])
    if err:
        return [err]
    value, found = _get_json_path(data, fields["artifact_key"])
    if not found:
        return [
            f"CANNOT CHECK: {fields['artifact']} has no key '{fields['artifact_key']}' -- "
            f"cannot cross-check {report_path}'s declared verdict."
        ]
    reported = str(fields["verdict_word"]).strip().lower()
    actual = str(value).strip().lower()
    if reported != actual:
        return [
            f"VERDICT MISMATCH: {report_path} states verdict_word='{fields['verdict_word']}' "
            f"but {fields['artifact']}['{fields['artifact_key']}'] = '{value}'. The report's "
            f"stated outcome contradicts its own backing artifact."
        ]
    return []


def _evaluate_criterion(kind, threshold, actual_value):
    """Bounded, closed-set criterion evaluation -- never free-form. Returns
    True if the criterion is SATISFIED (i.e. supports a SUCCESS verdict)."""
    if kind == "count_gte" or kind == "value_gte":
        return actual_value >= threshold
    if kind == "count_lte" or kind == "value_lte":
        return actual_value <= threshold
    if kind == "bool_true":
        return bool(actual_value) is True
    if kind == "bool_false":
        return bool(actual_value) is False
    return None  # "none" or unrecognized -- not evaluated


def _check_criterion_consistency(report_path, fields):
    """D-025: if the report declares a pre-registered criterion
    (criterion/criterion_field/criterion_threshold), does the artifact's own
    number at criterion_field actually satisfy it -- and does that agree
    with the declared verdict_word?"""
    kind = fields.get("criterion", "none")
    if kind == "none" or kind not in _CRITERION_KINDS:
        return []  # no criterion declared, or not a recognized kind -- skip, not an error
    if "criterion_field" not in fields or "criterion_threshold" not in fields:
        return [
            f"MALFORMED VERDICT BLOCK: {report_path} declares criterion='{kind}' but is "
            f"missing 'criterion_field' or 'criterion_threshold' -- criterion not checked."
        ]
    data, err = _load_json_or_none(fields["artifact"])
    if err:
        return [err]
    actual_value, found = _get_json_path(data, fields["criterion_field"])
    if not found:
        return [
            f"CANNOT CHECK: {fields['artifact']} has no key '{fields['criterion_field']}' -- "
            f"criterion not checked."
        ]
    try:
        threshold = float(fields["criterion_threshold"])
        actual_num = float(actual_value) if not isinstance(actual_value, bool) else actual_value
    except (TypeError, ValueError):
        actual_num = actual_value  # bool_true/bool_false path

    satisfied = _evaluate_criterion(kind, threshold, actual_num)
    if satisfied is None:
        return []
    reported_success = str(fields["verdict_word"]).strip().upper() in ("SUCCESS", "PASS", "COMPLETE", "TRUE")
    if satisfied != reported_success:
        return [
            f"LOGICAL INCONSISTENCY: {report_path} declares verdict_word='{fields['verdict_word']}' "
            f"but its own criterion ({kind} {fields['criterion_field']}={actual_num} vs "
            f"threshold {threshold}) evaluates to {'SATISFIED' if satisfied else 'NOT SATISFIED'} "
            f"-- the stated verdict is not entailed by the report's own declared numbers."
        ]
    return []


def _check_degenerate_metrics(artifact_path):
    """D-027 / SVI-007: any metric in the artifact's 'metrics' list whose
    value sits within tolerance of 0.0, 0.5, or 1.0 and whose sample_count
    is below the minimum is flagged. Fully deterministic -- no artifact
    with a 'metrics' list means nothing to check, not an error."""
    data, err = _load_json_or_none(artifact_path)
    if err:
        return [err]
    metrics = data.get("metrics") if isinstance(data, dict) else None
    if not metrics:
        return []
    findings = []
    for m in metrics:
        name = m.get("name", "<unnamed metric>")
        value = m.get("value")
        n = m.get("sample_count")
        if value is None or n is None:
            continue
        if n < _DEGENERATE_MIN_SAMPLES and any(abs(value - b) <= _DEGENERATE_TOLERANCE for b in _DEGENERATE_VALUES):
            findings.append(
                f"DEGENERATE METRIC: {artifact_path} metric '{name}' = {value} on only {n} "
                f"samples (< {_DEGENERATE_MIN_SAMPLES}) -- a value this close to 0.0/0.5/1.0 on "
                f"this few samples is likely a sample-size artifact, not a genuine result. "
                f"Report it with this flag rather than as a clean finding."
            )
    return findings


def cmd_evidence_check(args):
    """v1.4.1 -- reads a contract report's '## Verdict Cross-Check' block
    and cross-checks it against the JSON artifact it names. Three checks:
    verdict-word consistency (D-024, hard FAIL), pre-registered-criterion
    logical consistency (D-025, hard FAIL), and degenerate-metric flagging
    (D-027, WARNING). A report with no Verdict Cross-Check block is not an
    error -- not every contract has a pre-registered verdict. Never
    modifies any file. Exits 12 (Evidence Inconsistency) only on a hard
    finding.
    """
    print("Gatekeeper evidence-check (cross-checks report verdicts against their own artifacts)")
    print("=" * 60)

    reports = list(args.reports or [])
    if not reports:
        print("\nERROR: --reports must name at least one contract_report.md. Nothing to check.")
        sys.exit(9)

    hard_findings = []
    warning_findings = []

    for rp in reports:
        fields, block_findings = _parse_verdict_block(rp)
        warning_findings += [f for f in block_findings if f.startswith("CANNOT CHECK")]
        hard_findings += [f for f in block_findings if f.startswith("MALFORMED")]
        if fields is None:
            continue
        verdict_findings = _check_verdict_consistency(rp, fields)
        warning_findings += [f for f in verdict_findings if f.startswith("CANNOT CHECK")]
        hard_findings += [f for f in verdict_findings if not f.startswith("CANNOT CHECK")]

        criterion_findings = _check_criterion_consistency(rp, fields)
        warning_findings += [f for f in criterion_findings if f.startswith("CANNOT CHECK")]
        hard_findings += [f for f in criterion_findings if not f.startswith("CANNOT CHECK")]

        degenerate_findings = _check_degenerate_metrics(fields["artifact"])
        warning_findings += degenerate_findings

    print("\n[Verdict / criterion consistency -- D-024, D-025]")
    consistency = [f for f in hard_findings if "VERDICT MISMATCH" in f or "LOGICAL INCONSISTENCY" in f or "MALFORMED" in f]
    if not consistency:
        print("  No mismatches found.")
    else:
        for f in consistency:
            print(f"  - {f}")

    print("\n[Degenerate metric flagging -- D-027, SVI-007]")
    degenerate = [f for f in warning_findings if "DEGENERATE METRIC" in f]
    if not degenerate:
        print("  No degenerate metrics found.")
    else:
        for f in degenerate:
            print(f"  - {f}")

    other_warnings = [f for f in warning_findings if f not in degenerate]
    if other_warnings:
        print("\n[Other]")
        for f in other_warnings:
            print(f"  - {f}")

    print("\n" + "=" * 60)
    print(f"Failures: {len(hard_findings)}   Warnings: {len(warning_findings)}")
    print(
        "Evidence posture: unit-tested against a synthetic reproduction of the Chunks 08-09 "
        "incident (D-024, D-025, D-027), not yet run against a real project beyond the one "
        "that motivated it. Requires the '## Verdict Cross-Check' structured block -- a "
        "report without one is silently not checked, not silently passed; confirm the block "
        "is present for any contract carrying a T-CAUSAL or pre-registered claim."
    )
    sys.exit(12 if hard_findings else 0)


def cmd_acquisition_audit(args):
    """v1.4.0 -- scans data-acquisition scripts and their contract reports
    for red-flag patterns before their output is trusted. Two checks:
    data-generation function definitions (hard FAIL -- D-022), and
    simulation-indicating text (WARNING -- D-023). Never modifies any
    file. Exits 11 (Acquisition Audit Failure) only on a structural
    finding; textual findings are reported but do not by themselves fail
    the run, consistent with Gatekeeper's Warning Policy.
    """
    print("Gatekeeper acquisition-audit (scans data-acquisition scripts and reports)")
    print("=" * 60)

    scripts = list(args.scripts or [])
    reports = list(args.reports or [])
    if not scripts and not reports:
        print("\nERROR: at least one of --scripts or --reports must be given. Nothing to check.")
        sys.exit(9)

    print("\n[Structural audit -- data-generation function definitions]")
    structural_findings = _scan_acquisition_functions(scripts)
    if not structural_findings:
        print("  No data-generation function definitions found.")
    else:
        for f in structural_findings:
            print(f"  - {f}")

    print("\n[Structural audit -- fabricated statistical input (v1.4.2, D-028)]")
    fabrication_findings = _scan_fabricated_statistical_input(scripts)
    structural_findings = structural_findings + fabrication_findings
    if not fabrication_findings:
        print("  No distribution-sampled values feeding a metrics function found.")
    else:
        for f in fabrication_findings:
            print(f"  - {f}")

    print("\n[Textual scan -- simulation-indicating language]")
    textual_findings = _scan_acquisition_text(scripts + reports)
    if not textual_findings:
        print("  No simulation-indicating language found.")
    else:
        for f in textual_findings:
            print(f"  - {f}")

    hard_failures = [
        f for f in structural_findings
        if f.startswith("DATA-GENERATION FUNCTION") or f.startswith("FABRICATED STATISTICAL INPUT")
    ]
    warnings = [f for f in structural_findings if f not in hard_failures] + textual_findings

    print("\n" + "=" * 60)
    print(f"Failures: {len(hard_failures)}   Warnings: {len(warnings)}")
    print(
        "Evidence posture: the two original checks (D-022, D-023) are unit-tested against "
        "a synthetic reproduction of the Chunk 07 incident; the fabricated-statistical-input "
        "check (v1.4.2, D-028) is unit-tested against the real C08-06 script and reproduces "
        "byte-identically against the real incident artifact. None has been run against a "
        "pipeline beyond the one that motivated it. Catches the common case, not a "
        "deliberately obfuscated one -- see C01, C54, and the Constitution's Chunk Review "
        "raw-artifact inspection for the layer this command does not replace. This command "
        "now covers two related but distinct triggers: data-*acquisition* scripts fabricating "
        "data under an external constraint (D-022/D-023), and data-*computation* scripts "
        "fabricating their own intermediate inputs with no external constraint at all "
        "(D-028) -- kept as one command per C46, since both are the same underlying concern "
        "(a script trusted to handle real observations must not silently substitute "
        "manufactured ones) at different pipeline stages."
    )
    sys.exit(11 if hard_failures else 0)


def cmd_release_check(args):
    """v1.4.0 -- scans release-bound artifacts before submission. Two
    checks: local-path/machine-identity leaks (hard FAIL, unambiguous --
    D-017), and key-fact consistency against project/key_facts.md
    (WARNING -- heuristic, requires human confirmation). Never modifies
    any file. Exits 10 (Release Artifact Failure) only on a hard local-path
    finding; key-fact mismatches are reported but do not by themselves
    fail the run, consistent with Gatekeeper's Warning Policy.
    """
    print("Gatekeeper release-check (scans outbound release artifacts)")
    print("=" * 60)

    if not Path(args.manuscript).exists():
        print(f"\nERROR: --manuscript path '{args.manuscript}' does not exist. Nothing to check.")
        sys.exit(9)

    files_to_scan = [args.manuscript] + list(args.files or [])

    print("\n[Local path / machine-identity scan]")
    path_findings = _scan_local_paths(files_to_scan)
    if not path_findings:
        print("  No local paths found.")
    else:
        for f in path_findings:
            print(f"  - {f}")

    print("\n[Key-fact consistency check]")
    fact_findings = []
    if args.key_facts:
        fact_findings = _check_key_fact_consistency(args.manuscript, args.key_facts)
        if not fact_findings:
            print("  No mismatches found against declared key facts.")
        else:
            for f in fact_findings:
                print(f"  - {f}")
    else:
        print("  SKIPPED: no --key-facts given.")

    hard_failures = [f for f in path_findings if f.startswith("LOCAL PATH LEAK")]
    warnings = [f for f in path_findings if not f.startswith("LOCAL PATH LEAK")] + fact_findings

    print("\n" + "=" * 60)
    print(f"Failures: {len(hard_failures)}   Warnings: {len(warnings)}")
    print(
        "Evidence posture: unit-tested against synthetic fixtures, not yet run against "
        "a real manuscript beyond the GLOF review that motivated this command. The "
        "key-fact check is intentionally bounded -- it only catches drift against facts "
        "the Architect declared in key_facts.md ahead of time, per Gatekeeper's "
        "Verification Principles (no AI reasoning, no open-ended fact-checking)."
    )
    sys.exit(10 if hard_failures else 0)


# ---------------------------------------------------------------------------
# Mechanical guards (v1.4.2) -- four related additions, all deterministic,
# none relying on AI judgement to decide pass/fail. Motivated by D-028 (the
# real C08-06 fabrication incident) and by the general observation it
# confirmed: `evidence-check` verifies a report against its own named
# artifact, never against independent re-execution or recomputation. These
# four close that specific gap:
#
#   verify-contract  -- Gatekeeper itself re-runs every command a report
#                        declares under "## Verification" and checks the
#                        REAL exit code. A report's claimed result is
#                        never trusted, only used as a human cross-check.
#   lint-contract     -- deterministic AST scan for swallowed exceptions
#                        (a caught-and-silently-continued exception is
#                        indistinguishable from a silently substituted
#                        fallback), reuses acquisition-audit's fabrication
#                        scan, and checks whether a project's verification
#                        machinery (source/tests/, verify_*.py,
#                        factory/verifiers/) was modified since it was
#                        auto-frozen (see below).
#   recompute         -- a contract can declare a second, independent
#                        script computing the same value from the same
#                        raw evidence; Gatekeeper runs it and compares.
#                        Independence is enforced mechanically (the
#                        independent script's hash must differ from the
#                        original's), not merely asserted by a label.
#   stamp-report      -- appends a tamper-evident stamp to a contract
#                        report containing the real results of the above
#                        three, plus git diff and frozen-file hashes.
#                        Everything above a stamp is hash-committed; any
#                        later modification is detected the next time the
#                        report is stamped or checked (exit 16). Anything
#                        needing correction goes in a new section below
#                        the stamp, not an edit above it.
#
# "Freeze all verification machinery automatically" (the fourth mechanical
# guard requested) is not new code -- it is v1.3.2's existing snapshot/hash
# infrastructure (check_frozen_files, sha256_of, SNAPSHOT_DIR) applied by
# default to a fixed path set, so no contract has to remember to declare
# source/tests/ etc. in --frozen (C46: improve an existing mechanism before
# adding a new one). See _auto_frozen_verification_paths, and its wiring
# into cmd_snapshot/cmd_snapshot_chunk/cmd_check below.
#
# Honesty about scope, stated once here rather than re-litigated per
# command: none of the four proves a script is CORRECT. verify-contract
# proves a declared command really exited 0 just now. lint-contract's
# swallowed-exception check is a standard, well-understood static-analysis
# pattern (the same class flake8-bugbear/bandit already catch) applied via
# Python's own `ast` module -- deterministic, but syntactic, not semantic;
# it cannot tell a genuinely necessary broad catch from a hidden one, which
# is exactly why an explicit "# GATEKEEPER-EXEMPT: <reason>" escape exists
# -- visible in the diff, not silent. recompute proves two DIFFERENT
# programs agree, which is real evidence, not proof either program is
# right (two independently wrong implementations can still agree). Stamp
# integrity proves content wasn't edited after stamping; it cannot stop
# someone from stamping over content that was already wrong before the
# first stamp. Every one of these is a genuine, mechanical improvement
# over trusting a report's own prose. None of them, individually or
# together, is a claim that fabrication has become impossible -- that
# claim would be the same kind of overclaim D-028 itself was filed to
# catch, and this codebase does not get to exempt itself from C01/C02/
# EP-005 while enforcing them on everything else.
# ---------------------------------------------------------------------------

AUTO_FROZEN_GLOBS = (
    "source/tests/**/*.py",
    "source/scripts/verify_*.py",
    "factory/verifiers/**/*.py",
)


def _auto_frozen_verification_paths():
    """Every contract's verification machinery is frozen automatically --
    no contract declares source/tests/, verify_*.py, or factory/verifiers/
    in --frozen by hand. Returns only paths that currently exist; silently
    empty on a project that has none yet, never an error."""
    found = []
    for pattern in AUTO_FROZEN_GLOBS:
        found.extend(str(p) for p in Path(".").glob(pattern) if p.is_file())
    return sorted(set(found))


def _now_utc_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _run_subprocess(command, timeout=300):
    """Actually executes a shell command. Never raises -- a command that
    can't even start is reported as a synthetic nonzero exit with the
    exception text as stderr, so every caller gets a real pass/fail
    signal instead of a crash. Same trust boundary the test suite already
    had: this executes code the pipeline was always going to execute via
    pytest/the declared command anyway; it does not newly expose the Implementor's
    code to execution that wasn't already happening."""
    try:
        proc = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=timeout)
        return proc.returncode, proc.stdout[-2000:], proc.stderr[-2000:]
    except subprocess.TimeoutExpired:
        return 124, "", f"TIMEOUT after {timeout}s"
    except Exception as e:
        return 127, "", f"COULD NOT EXECUTE: {e}"


def _git_diff_files():
    """Returns (files: list[str]-or-None, note: str). None means git is
    unavailable or this isn't a repository -- callers must treat that as
    'unknown', never as 'zero files changed'."""
    code, out, _ = _run_subprocess("git diff --name-only HEAD", timeout=30)
    if code != 0:
        code2, out2, _ = _run_subprocess("git diff --name-only --cached", timeout=30)
        if code2 != 0:
            return None, "git unavailable or not a repository -- files-modified list omitted."
        out = out2
    return [l.strip() for l in out.splitlines() if l.strip()], ""


# --- lint-contract ----------------------------------------------------------

_EXEMPTION_COMMENT_RE = re.compile(r'#\s*GATEKEEPER-EXEMPT:\s*(.+)')
_LOG_CALL_NAMES = {"warn", "warning", "error", "critical", "exception", "warn_explicit"}
_LOG_MODULE_NAMES = {"logging", "logger", "log", "warnings"}


def _scan_swallowed_exceptions(script_path):
    """Returns (hard_findings, warning_findings). Deterministic AST walk
    (Python's own `ast` module, stdlib -- no new dependency): an except
    handler whose body contains neither a `raise` nor a recognizable
    logging/warning call is flagged -- silently continuing after a real
    failure is indistinguishable from silently substituting a fallback
    (C01, C54, D-028). A handler that re-raises or logs is never flagged,
    regardless of anything else it does. A '# GATEKEEPER-EXEMPT: <reason>'
    comment anywhere in the handler's own source lines downgrades the
    finding to a warning (visible, human-confirmable) rather than
    silently passing it."""
    text = _read_text_or_none(Path(script_path))
    if text is None:
        return [], [f"CANNOT CHECK: {script_path} not found -- skipping exception-handling audit."]
    try:
        tree = ast.parse(text, filename=str(script_path))
    except SyntaxError as e:
        return [], [f"CANNOT CHECK: {script_path} is not valid Python ({e}) -- skipping exception-handling audit."]

    lines = text.splitlines()
    hard, warn = [], []

    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler):
            continue
        body_nodes = [n for child in node.body for n in ast.walk(child)]
        has_raise = any(isinstance(n, ast.Raise) for n in body_nodes)
        has_log = False
        for n in body_nodes:
            if not isinstance(n, ast.Call):
                continue
            func = n.func
            if isinstance(func, ast.Attribute) and func.attr in _LOG_CALL_NAMES:
                has_log = True
                break
            if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) and func.value.id in _LOG_MODULE_NAMES:
                has_log = True
                break
            if isinstance(func, ast.Name) and func.id in _LOG_CALL_NAMES:
                has_log = True
                break
        if has_raise or has_log:
            continue

        start_line = node.lineno
        end_line = max((getattr(n, "lineno", start_line) for n in body_nodes), default=start_line)
        block_text = "\n".join(lines[start_line - 1:end_line])
        exempt_m = _EXEMPTION_COMMENT_RE.search(block_text)

        try:
            exc_desc = ast.unparse(node.type) if node.type is not None else "bare except"
        except Exception:
            exc_desc = "except"
        location = f"{script_path}:{start_line}"

        if exempt_m:
            warn.append(
                f"EXEMPTED SWALLOWED EXCEPTION: {location} ({exc_desc}) neither re-raises nor logs, "
                f"but is exempted: \"{exempt_m.group(1).strip()}\". Confirm the exemption is genuine "
                f"before trusting it."
            )
        else:
            hard.append(
                f"SWALLOWED EXCEPTION: {location} ({exc_desc}) neither re-raises nor logs. Silently "
                f"continuing after a real failure is indistinguishable from silently substituting a "
                f"fallback (C01, C54, D-028). Add a 'raise', a logging call, or a "
                f"'# GATEKEEPER-EXEMPT: <reason>' comment inside the handler."
            )
    return hard, warn


def cmd_lint_contract(args):
    """v1.4.2, mechanical barrier #2. Scans declared scripts for swallowed
    exceptions and fabricated-statistical-input patterns (structural,
    both hard FAIL), and checks whether this project's auto-frozen
    verification machinery has been tampered with (hard FAIL). Never
    modifies any file."""
    print("Gatekeeper lint-contract (swallowed exceptions, fabrication patterns, frozen-machinery tampering)")
    print("=" * 60)
    scripts = list(args.scripts or [])
    if not scripts and not args.contract:
        print("\nERROR: give --scripts, --contract, or both. Nothing to lint.")
        sys.exit(9)

    hard, warn = [], []

    print("\n[Swallowed exceptions]")
    for sp in scripts:
        h, w = _scan_swallowed_exceptions(sp)
        hard += h
        warn += w
    section_findings = [f for f in hard + warn if any(sp in f for sp in scripts)]
    if not section_findings:
        print("  None found.")
    else:
        for f in section_findings:
            print(f"  - {f}")

    print("\n[Fabricated statistical input]")
    fab = _scan_fabricated_statistical_input(scripts)
    hard += fab
    if not fab:
        print("  None found.")
    else:
        for f in fab:
            print(f"  - {f}")

    print("\n[Frozen verification machinery]")
    frozen_paths = _auto_frozen_verification_paths()
    if not frozen_paths:
        print("  (none present in this project yet -- source/tests/, source/scripts/verify_*.py, "
              "factory/verifiers/ not found)")
    elif args.contract:
        fr_ok, fr_details = check_frozen_files(args.contract, frozen_paths)
        for l in fr_details:
            print(f"  {l}")
        if not fr_ok:
            hard.append("FROZEN MACHINERY TAMPERED: see Frozen verification machinery section above.")
    else:
        print(f"  {len(frozen_paths)} path(s) found: {frozen_paths}. Pass --contract to check against its snapshot.")

    print("\n" + "=" * 60)
    print(f"Hard failures: {len(hard)}   Warnings: {len(warn)}")
    sys.exit(14 if hard else 0)


# --- verify-contract ---------------------------------------------------------

_VERIFICATION_COMMAND_RE = re.compile(
    r'^\s*-\s*\*\*[^*]*(?:Command|Verification)[^*]*\*\*:\s*`([^`]+)`',
    re.MULTILINE | re.IGNORECASE,
)


def _extract_declared_commands(report_text):
    """Extracts backtick-wrapped shell commands from the report's existing
    '## Verification' bullets -- reuses the format contract reports
    already use (e.g. '**Command**: `pytest ...`', '**Claim
    Verification**: `python3 ...`'), rather than inventing a new block.
    Returns commands in file order, deduplicated."""
    seen = []
    for m in _VERIFICATION_COMMAND_RE.finditer(report_text):
        cmd = m.group(1).strip()
        if cmd not in seen:
            seen.append(cmd)
    return seen


def cmd_verify_contract(args):
    """v1.4.2, mechanical barrier #1. Gatekeeper actually executes every
    command a contract report declares under '## Verification' and checks
    the REAL exit code. A report's own claimed result is read only as a
    human cross-reference, never trusted as the verification itself."""
    print("Gatekeeper verify-contract (independently re-executes declared verification commands)")
    print("=" * 60)
    if not args.reports:
        print("\nERROR: --reports must be given. Nothing to check.")
        sys.exit(9)

    any_fail = False
    any_commands = False
    for rp in args.reports:
        text = _read_text_or_none(Path(rp))
        if text is None:
            print(f"\n[{rp}] CANNOT CHECK: not found.")
            any_fail = True
            continue
        commands = _extract_declared_commands(text)
        print(f"\n[{rp}] {len(commands)} declared command(s) found.")
        if not commands:
            print("  Nothing declared under '## Verification' to re-execute.")
            continue
        any_commands = True
        for cmd in commands:
            exit_code, stdout, stderr = _run_subprocess(cmd)
            status = "PASS" if exit_code == 0 else "FAIL"
            print(f"  [{status}] `{cmd}` -> real exit code {exit_code}")
            if exit_code != 0:
                any_fail = True
                print(f"         last output: {(stderr or stdout)[-500:]}")

    print("\n" + "=" * 60)
    if not any_commands:
        print("No declared verification commands found in any given report.")
    print(
        "Re-executes each declared command exactly once, independently of what the report claims "
        "about it. A command with side effects will have those side effects again -- declare "
        "read-only/idempotent verification commands only, the same expectation reports already carry."
    )
    sys.exit(13 if any_fail else 0)


# --- recompute ----------------------------------------------------------------

_RECOMPUTE_BLOCK_HEADER_RE = re.compile(r'^##\s*Recompute Declaration\s*$', re.MULTILINE)
_RECOMPUTE_REQUIRED_FIELDS = {
    "original_script", "independent_script", "artifact", "artifact_key",
    "independent_command", "independent_output_key",
}


def _parse_recompute_block(report_path):
    """Returns (fields_dict_or_None, findings). No block present is not an
    error -- not every contract declares one."""
    text = _read_text_or_none(Path(report_path))
    if text is None:
        return None, [f"CANNOT CHECK: {report_path} not found."]
    m = _RECOMPUTE_BLOCK_HEADER_RE.search(text)
    if m is None:
        return None, []
    block_end = text.find("\n## ", m.end())
    block = text[m.end():block_end if block_end != -1 else len(text)]
    fields = {}
    for fm in _VERDICT_FIELD_RE.finditer(block):
        fields[fm.group(1)] = fm.group(2)
    missing = _RECOMPUTE_REQUIRED_FIELDS - fields.keys()
    if missing:
        return None, [f"MALFORMED RECOMPUTE BLOCK: {report_path} is missing field(s): {sorted(missing)}."]
    return fields, []


def _check_recompute_block(report_path):
    """Returns (checked: bool, ok: bool, lines: list[str]). checked=False
    means no (well-formed) Recompute Declaration was present -- not a
    failure by itself; a MALFORMED block still returns checked=False but
    ok=False, since a declared-but-broken block should not fail open."""
    fields, findings = _parse_recompute_block(report_path)
    if fields is None:
        return (False, not findings, list(findings))

    lines = []
    orig = Path(fields["original_script"])
    indep = Path(fields["independent_script"])
    try:
        tolerance = float(fields.get("tolerance", "0") or 0)
    except ValueError:
        tolerance = 0.0

    if not indep.exists():
        lines.append(f"FAIL: independent_script {indep} does not exist.")
        return (True, False, lines)
    if orig.exists() and sha256_of(orig) == sha256_of(indep):
        lines.append(
            "FAIL: independent_script is byte-identical to original_script -- this is "
            "duplication, not independent verification (C11)."
        )
        return (True, False, lines)
    if not orig.exists():
        lines.append(f"WARNING: original_script {orig} not found -- cannot confirm independence, "
                      f"only that independent_script exists and runs.")

    artifact_data, err = _load_json_or_none(fields["artifact"])
    if err:
        lines.append(err)
        return (True, False, lines)
    claimed_value, found = _get_json_path(artifact_data, fields["artifact_key"])
    if not found:
        lines.append(f"FAIL: artifact_key '{fields['artifact_key']}' not found in {fields['artifact']}.")
        return (True, False, lines)

    exit_code, stdout, stderr = _run_subprocess(fields["independent_command"])
    if exit_code != 0:
        lines.append(f"FAIL: independent_command exited {exit_code}. stderr: {stderr[-300:]}")
        return (True, False, lines)
    try:
        recomputed = json.loads(stdout.strip().splitlines()[-1])
        recomputed_value = recomputed[fields["independent_output_key"]]
    except Exception as e:
        lines.append(
            f"FAIL: could not read '{fields.get('independent_output_key')}' from "
            f"independent_command's JSON stdout ({e})."
        )
        return (True, False, lines)

    try:
        diff = abs(float(claimed_value) - float(recomputed_value))
        match = diff <= tolerance
    except (TypeError, ValueError):
        diff = None
        match = claimed_value == recomputed_value

    if match:
        lines.append(f"PASS: claimed={claimed_value} recomputed={recomputed_value} tolerance={tolerance}")
        return (True, True, lines)
    lines.append(
        f"FAIL: RECOMPUTE MISMATCH claimed={claimed_value} recomputed={recomputed_value} "
        f"diff={diff} tolerance={tolerance}"
    )
    return (True, False, lines)


def cmd_recompute(args):
    """v1.4.2, mechanical barrier #3. For each report declaring a
    '## Recompute Declaration' block, actually runs the declared
    independent script and compares its output to the artifact's claimed
    value. Independence is enforced mechanically (hash comparison), not
    merely asserted."""
    print("Gatekeeper recompute (independent recomputation check)")
    print("=" * 60)
    if not args.reports:
        print("\nERROR: --reports must be given. Nothing to check.")
        sys.exit(9)

    any_fail = False
    any_checked = False
    for rp in args.reports:
        checked, ok, lines = _check_recompute_block(rp)
        print(f"\n[{rp}]")
        if not lines:
            print("  No Recompute Declaration block present.")
        for l in lines:
            print(f"  {l}")
        if checked:
            any_checked = True
            any_fail = any_fail or not ok
        elif lines:
            any_fail = True  # malformed block, disclosed but not silently skipped

    print("\n" + "=" * 60)
    if not any_checked:
        print("No well-formed Recompute Declaration blocks found. Nothing independently recomputed.")
    sys.exit(15 if any_fail else 0)


# --- stamp-report ---------------------------------------------------------

_STAMP_HEADER_RE = re.compile(r'^## Gatekeeper Verification Stamp #(\d+)\s*$', re.MULTILINE)
_STAMP_HASH_LINE_RE = re.compile(r'^content_hash_sha256:\s*([0-9a-f]{64})\s*$', re.MULTILINE)


def _find_stamps(text):
    """Returns list of dicts (number, header_start, claimed_hash), in file
    order, oldest first."""
    headers = list(_STAMP_HEADER_RE.finditer(text))
    stamps = []
    for i, hm in enumerate(headers):
        block_end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
        block_text = text[hm.start():block_end]
        hash_m = _STAMP_HASH_LINE_RE.search(block_text)
        stamps.append({
            "number": int(hm.group(1)),
            "header_start": hm.start(),
            "claimed_hash": hash_m.group(1) if hash_m else None,
        })
    return stamps


def _verify_stamp_integrity(report_path):
    """Returns (ok, findings). No stamps present -> (True, []) -- stamping
    is opt-in per report and never retroactively required of existing,
    unstamped reports (Backward Compatibility). Each stamp's claimed hash
    must equal sha256(content strictly before that stamp's own header),
    so tampering with content under an EARLIER stamp is still caught by
    every LATER stamp's hash, not just the nearest one."""
    text = _read_text_or_none(Path(report_path))
    if text is None:
        return False, [f"CANNOT CHECK: {report_path} not found."]
    stamps = _find_stamps(text)
    if not stamps:
        return True, []
    ok = True
    findings = []
    for s in stamps:
        if s["claimed_hash"] is None:
            findings.append(f"MALFORMED STAMP: {report_path} stamp #{s['number']} has no content_hash_sha256 line.")
            ok = False
            continue
        actual_hash = _sha256_text(text[:s["header_start"]])
        if actual_hash != s["claimed_hash"]:
            findings.append(
                f"STAMP TAMPERING DETECTED: {report_path} stamp #{s['number']} certified content hash "
                f"{s['claimed_hash'][:16]}..., but the actual content before this stamp now hashes to "
                f"{actual_hash[:16]}... -- something above this stamp was modified after it was issued."
            )
            ok = False
    return ok, findings


def _render_stamp_block(stamp_number, content_hash, verification_results, lint_hard, lint_warn,
                         recompute_lines, frozen_details, git_files):
    lines = [f"## Gatekeeper Verification Stamp #{stamp_number}", ""]
    lines.append(f"content_hash_sha256: {content_hash}")
    lines.append(f"stamped_at_utc: {_now_utc_iso()}")
    lines.append("")
    lines.append("### Files Modified (git diff)")
    if git_files is None:
        lines.append("- UNAVAILABLE (git not found or not a repository)")
    elif not git_files:
        lines.append("- (no uncommitted changes detected)")
    else:
        lines += [f"- {f}" for f in git_files]
    lines.append("")
    lines.append("### Verification Commands (independently re-executed)")
    if not verification_results:
        lines.append("- (none declared under '## Verification')")
    else:
        for r in verification_results:
            lines.append(f"- `{r['command']}` -> exit code {r['exit_code']} "
                          f"({'PASS' if r['exit_code'] == 0 else 'FAIL'})")
    lines.append("")
    lines.append("### Frozen Verification Machinery")
    if not frozen_details:
        lines.append("- (none present in this project yet)")
    else:
        lines += [f"- {d}" for d in frozen_details]
    lines.append("")
    lines.append("### Contract Lint")
    lines.append(f"- Hard failures: {len(lint_hard)}")
    lines += [f"  - {f}" for f in lint_hard]
    lines.append(f"- Warnings: {len(lint_warn)}")
    lines += [f"  - {f}" for f in lint_warn]
    lines.append("")
    lines.append("### Independent Recomputation")
    if not recompute_lines:
        lines.append("- (no Recompute Declaration in this report)")
    else:
        lines += [f"- {l}" for l in recompute_lines]
    lines.append("")
    lines.append(
        "Everything above this stamp (including any earlier stamps) is certified unchanged as of "
        "this hash. Modifying anything above this line is detected the next time this report is "
        "stamped or checked (exit code 16). Corrections belong in a new section below this line, "
        "not an edit above it."
    )
    return "\n".join(lines) + "\n"


def cmd_stamp_report(args):
    """v1.4.2, mechanical barrier #4 -- ties the other three together.
    Appends a tamper-evident stamp to a contract report containing the
    REAL results of verify-contract, lint-contract, and recompute (if
    declared), plus git diff and frozen-file status. Refuses to stamp if
    any EXISTING stamp has already been tampered with (exit 16, fail
    fast, before doing anything else). Never modifies content above the
    point it appends to."""
    print("Gatekeeper stamp-report (mechanical evidence stamp)")
    print("=" * 60)
    report_path = Path(args.report)
    text = _read_text_or_none(report_path)
    if text is None:
        print(f"ERROR: {args.report} not found.")
        sys.exit(9)

    ok, integrity_findings = _verify_stamp_integrity(report_path)
    existing_stamps = _find_stamps(text)
    if not ok:
        print("\n[Stamp Integrity] TAMPERING DETECTED -- refusing to add a new stamp.")
        for f in integrity_findings:
            print(f"  - {f}")
        sys.exit(16)
    print("\n[Stamp Integrity] " + ("no existing stamps -- this will be #1."
          if not existing_stamps else f"all {len(existing_stamps)} existing stamp(s) verified intact."))

    next_number = (max(s["number"] for s in existing_stamps) + 1) if existing_stamps else 1

    commands = _extract_declared_commands(text)
    verification_results = []
    for cmd in commands:
        exit_code, _, _ = _run_subprocess(cmd)
        verification_results.append({"command": cmd, "exit_code": exit_code})
    verification_failed = any(r["exit_code"] != 0 for r in verification_results)

    frozen_paths = _auto_frozen_verification_paths()
    frozen_details = []
    frozen_tampered = False
    if frozen_paths:
        if args.contract:
            fr_ok, frozen_details = check_frozen_files(args.contract, frozen_paths)
            frozen_tampered = not fr_ok
        else:
            frozen_details = [f"{p} = {sha256_of(Path(p))[:12]}... (no --contract given, informational only)"
                               for p in frozen_paths]

    git_files, _ = _git_diff_files()
    lint_hard, lint_warn = [], []
    py_targets = [f for f in (git_files or []) if f.endswith(".py")]
    for sp in py_targets:
        h, w = _scan_swallowed_exceptions(sp)
        lint_hard += h
        lint_warn += w
    lint_hard += _scan_fabricated_statistical_input(py_targets)

    _, recompute_ok, recompute_lines = _check_recompute_block(report_path)
    recompute_declared_and_failed = bool(recompute_lines) and not recompute_ok

    prefix = text if text.endswith("\n\n") else (text.rstrip("\n") + "\n\n")
    content_hash = _sha256_text(prefix)
    stamp_block = _render_stamp_block(
        next_number, content_hash, verification_results, lint_hard, lint_warn,
        recompute_lines, frozen_details, git_files,
    )
    new_text = prefix + stamp_block
    report_path.write_text(new_text)

    print(f"\nStamp #{next_number} appended to {args.report}.")
    print(f"  Verification commands: {len(verification_results)} run"
          + (", FAIL" if verification_failed else (", all passed" if verification_results else "")))
    print(f"  Lint: {len(lint_hard)} hard failure(s), {len(lint_warn)} warning(s)")
    print(f"  Frozen verification machinery: {'TAMPERED' if frozen_tampered else 'ok'} "
          f"({len(frozen_paths)} path(s))")
    print(f"  Recompute: {'declared and FAILED' if recompute_declared_and_failed else ('declared and passed' if recompute_lines else 'not declared')}")

    if verification_failed or lint_hard or frozen_tampered or recompute_declared_and_failed:
        sys.exit(14)
    sys.exit(0)


def cmd_verify_stamps(args):
    """Standalone integrity check, no side effects -- for CI or a Human to
    confirm a report hasn't been tampered with since it was last stamped,
    without also appending a new stamp."""
    print("Gatekeeper verify-stamps (tamper check only -- does not add a stamp)")
    print("=" * 60)
    any_fail = False
    for rp in args.reports or []:
        ok, findings = _verify_stamp_integrity(rp)
        stamps = _find_stamps(_read_text_or_none(Path(rp)) or "")
        print(f"\n[{rp}] {len(stamps)} stamp(s) found.")
        for f in findings:
            print(f"  - {f}")
        if ok and stamps:
            print("  All stamps verified intact.")
        if not ok:
            any_fail = True
    if not args.reports:
        print("\nERROR: --reports must be given.")
        sys.exit(9)
    sys.exit(16 if any_fail else 0)


def cmd_release_certify(args):
    """v2.2.0 (D-038) -- aggregate release certification, distinct from any
    single chunk's PASS. `release-check` (v1.4.0) scans one release-bound
    artifact for path leaks and key-fact drift; nothing before v2.2
    aggregated across an entire project and said, in one place, whether the
    whole thing is actually submission-ready. Chunk PASS and Gatekeeper
    `check` PASS are per-contract/per-chunk states -- this command is the
    only one that produces project/RELEASE_CERTIFICATION.md, and it is the
    only artifact this Factory's documents authorize anyone to call
    "CERTIFIED."

    Walks every contract_report.md under --chunks-dir and, per contract:
    confirms Final Status is COMPLETE (not FLAGGED or BLOCKED -- either one
    blocks certification, since a Fix Package or a carried-forward blocker
    means the project isn't actually in its claimed final state); runs the
    same evidence-check logic against any '## Verdict Cross-Check' block;
    runs the same recompute logic against any '## Recompute Declaration'
    block; and, when the contract's own contract.md is locatable, runs the
    same tier-inference logic tier-check does standalone. Then runs
    acquisition-audit against --scripts if given, and release-check against
    --manuscript if given.

    This is a thinner aggregation than it might look: it re-runs existing
    checks against existing artifacts, it does not invent a new evidence
    format, a new registry file, or a new role to perform the aggregation.
    Never modifies any contract report. Writes project/RELEASE_CERTIFICATION.md
    unconditionally (CERTIFIED or NOT CERTIFIED, both are useful states to
    have on record) and exits 19 on NOT CERTIFIED.
    """
    print("Gatekeeper release-certify (aggregate CERTIFIED / NOT CERTIFIED gate)")
    print("=" * 60)

    chunks_dir = Path(args.chunks_dir)
    if not chunks_dir.exists():
        print(f"\nERROR: --chunks-dir {chunks_dir} not found.")
        sys.exit(9)

    hard_findings = []
    warning_findings = []
    categories_checked = []

    report_paths = sorted(chunks_dir.glob("*/reports/*/contract_report.md"))
    print(f"\n[Contract Status] {len(report_paths)} contract_report.md file(s) found under {chunks_dir}")
    if not report_paths:
        hard_findings.append(f"NO CONTRACT REPORTS FOUND under {chunks_dir} -- nothing to certify.")

    non_complete = []
    for rp in report_paths:
        status = parse_contract_status(rp)
        if status != "complete":
            non_complete.append((str(rp), status))
    if non_complete:
        for rp, status in non_complete:
            hard_findings.append(f"NOT COMPLETE: {rp} Final Status is '{status}', not COMPLETE.")
    else:
        print(f"  All {len(report_paths)} report(s) read Final Status: COMPLETE.")
    categories_checked.append("contract_status")

    print("\n[Evidence / Recompute per contract]")
    verdict_checked = 0
    recompute_checked = 0
    for rp in report_paths:
        fields, block_findings = _parse_verdict_block(rp)
        hard_findings += [f"{rp}: {f}" for f in block_findings if f.startswith("MALFORMED")]
        warning_findings += [f"{rp}: {f}" for f in block_findings if f.startswith("CANNOT CHECK")]
        if fields is not None:
            verdict_checked += 1
            vf = _check_verdict_consistency(rp, fields)
            hard_findings += [f"{rp}: {f}" for f in vf if not f.startswith("CANNOT CHECK")]
            warning_findings += [f"{rp}: {f}" for f in vf if f.startswith("CANNOT CHECK")]
            cf = _check_criterion_consistency(rp, fields)
            hard_findings += [f"{rp}: {f}" for f in cf if not f.startswith("CANNOT CHECK")]
            warning_findings += [f"{rp}: {f}" for f in cf if f.startswith("CANNOT CHECK")]
            warning_findings += [f"{rp}: {f}" for f in _check_degenerate_metrics(fields["artifact"])]

        checked, ok, lines = _check_recompute_block(rp)
        if checked:
            recompute_checked += 1
            if not ok:
                hard_findings += [f"{rp} recompute: {l}" for l in lines]
    print(f"  {verdict_checked} report(s) had a Verdict Cross-Check block checked.")
    print(f"  {recompute_checked} report(s) had a Recompute Declaration checked.")
    categories_checked.append("evidence_and_recompute")

    print("\n[Fail-Closed Tier Inference per contract]")
    tier_checked = 0
    for rp in report_paths:
        contract_id = rp.parent.name
        contract_path, err = _find_contract_file(contract_id)
        if contract_path is None:
            warning_findings.append(f"{rp}: could not locate contract file for tier-check ({err})")
            continue
        ctext = _read_text_or_none(contract_path)
        if ctext is None:
            continue
        tier_checked += 1
        m = re.search(r'Scientific Claim Tier.*?:\s*\**\s*(NONE|T-DESC|T-COMP|T-CAUSAL)\b', ctext, re.IGNORECASE)
        declared = m.group(1).upper() if m else "NONE"
        minimum_tier, strong_matches, _weak = _infer_minimum_scientific_claim_tier(ctext)
        if _TIER_RANK[declared] < _TIER_RANK[minimum_tier]:
            hard_findings.append(
                f"{contract_path}: declared Scientific Claim Tier '{declared}' is weaker than "
                f"inferred minimum '{minimum_tier}' (matched {strong_matches})."
            )
    print(f"  {tier_checked} contract(s) checked for fail-closed tier inference.")
    categories_checked.append("tier_inference")

    if args.scripts:
        print("\n[Acquisition Audit]")
        structural = _scan_acquisition_functions(args.scripts) + _scan_fabricated_statistical_input(args.scripts)
        hard_findings += [f for f in structural if f.startswith("DATA-GENERATION FUNCTION") or f.startswith("FABRICATED STATISTICAL INPUT")]
        warning_findings += _scan_acquisition_text(args.scripts)
        warning_findings += _scan_statistical_protocol_language(args.scripts)
        print(f"  {len(args.scripts)} script(s) scanned.")
        categories_checked.append("acquisition_audit")
    else:
        print("\n[Acquisition Audit] SKIPPED -- no --scripts given.")

    if args.manuscript:
        print("\n[Release Artifact Scan]")
        path_findings = _scan_local_paths([args.manuscript] + list(args.files or []))
        hard_findings += path_findings
        if args.key_facts:
            kf_findings = _check_key_fact_consistency(args.manuscript, args.key_facts)
            warning_findings += kf_findings
        print(f"  Scanned {args.manuscript} (+{len(args.files or [])} additional file(s)).")
        categories_checked.append("release_artifact_scan")
    else:
        print("\n[Release Artifact Scan] SKIPPED -- no --manuscript given.")

    certified = not hard_findings
    verdict = "CERTIFIED" if certified else "NOT CERTIFIED"

    print("\n" + "=" * 60)
    print(f"Categories checked: {categories_checked}")
    print(f"Hard findings: {len(hard_findings)}   Warnings: {len(warning_findings)}")
    if hard_findings:
        print("\n[Hard findings]")
        for f in hard_findings:
            print(f"  - {f}")
    if warning_findings:
        print("\n[Warnings]")
        for f in warning_findings:
            print(f"  - {f}")
    print(f"\nRESULT: {verdict}")

    cert_path = Path("project/RELEASE_CERTIFICATION.md")
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        "# Release Certification",
        "",
        f"status: {verdict}",
        f"generated_at: {timestamp}",
        f"chunks_dir: {chunks_dir}",
        f"categories_checked: {categories_checked}",
        f"contract_reports_examined: {len(report_paths)}",
        "",
        "## Hard findings",
    ]
    lines += [f"- {f}" for f in hard_findings] if hard_findings else ["(none)"]
    lines += ["", "## Warnings"]
    lines += [f"- {f}" for f in warning_findings] if warning_findings else ["(none)"]
    lines += [
        "",
        "## Proof boundaries",
        "This certifies only what the categories above actually check: contract completion "
        "status, verdict/criterion/recompute consistency for contracts that declared those "
        "blocks, fail-closed tier inference, and (if invoked with --scripts/--manuscript) "
        "acquisition-audit and release-artifact scanning. It does not certify scientific "
        "truth, publication acceptance, or correctness of anything no check above actually "
        "examined -- an uninvoked category is absent from `categories_checked` above, not "
        "silently passed. A chunk-level Gatekeeper PASS is not this certificate, and this "
        "certificate does not retroactively upgrade one.",
    ]
    try:
        cert_path.parent.mkdir(parents=True, exist_ok=True)
        cert_path.write_text("\n".join(lines) + "\n")
        print(f"\nWrote {cert_path}")
    except OSError as e:
        print(f"\nWARNING: could not write {cert_path}: {e}")

    sys.exit(0 if certified else 19)


def main():
    # v1.3.4 (BUG-7): every path in this script is cwd-relative with no
    # validation. Run from the wrong directory and DROP_HERE/, project/,
    # etc. silently resolve to a nonexistent path, producing a generic,
    # misleading error instead of the real problem. This check runs before
    # any command dispatch, so every subcommand is covered by it.
    if not Path("factory/bootstrap_manifest.yaml").exists():
        print(
            "ERROR: gatekeeper.py must be run from the repository root "
            "(expected to find factory/bootstrap_manifest.yaml here)."
        )
        sys.exit(9)

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_snap = sub.add_parser("snapshot", help="Record baseline hashes for one contract's frozen files.")
    p_snap.add_argument("--contract", required=True)
    p_snap.add_argument("--frozen", nargs="+", required=True, help="Paths to freeze.")
    p_snap.add_argument("--force", action="store_true", help="Overwrite an existing snapshot. Use deliberately.")
    p_snap.set_defaults(func=cmd_snapshot)

    p_snap_chunk = sub.add_parser("snapshot-chunk", help="Snapshot every contract's frozen_files in a chunk's manifest, in one command.")
    p_snap_chunk.add_argument("--manifest", required=True, help="Path to the chunk's execution_manifest.yaml.")
    p_snap_chunk.add_argument("--force", action="store_true", help="Overwrite existing snapshots. Use deliberately.")
    p_snap_chunk.set_defaults(func=cmd_snapshot_chunk)

    p_next = sub.add_parser("next", help="Report the next contract ready to execute, per execution_order and contract_report.md statuses.")
    p_next.add_argument("--manifest", required=True, help="Path to the chunk's execution_manifest.yaml.")
    p_next.add_argument("--reports-dir", default=None, help="Override the default <manifest_dir>/reports/ location.")
    p_next.set_defaults(func=cmd_next)

    p_dropbox = sub.add_parser("sort-dropbox", help="File everything in DROP_HERE/ to the destination its dropbox_manifest.json declares.")
    p_dropbox.add_argument("--manifest", required=False, default=None, help="Accepted for symmetry with other commands; sort-dropbox reads DROP_HERE/dropbox_manifest.json directly and does not need the chunk manifest.")
    p_dropbox.add_argument("--force", action="store_true", help="Overwrite a destination file that already exists. Use deliberately.")
    p_dropbox.set_defaults(func=cmd_sort_dropbox)

    p_stage = sub.add_parser("stage-takethis", help="Copy one completed chunk's self-contained reports (every contract_report.md + chunk_report.md) into TAKE_THIS/. Copy only -- originals are untouched.")
    p_stage.add_argument("--chunk", required=True, help="Chunk directory name, e.g. chunk03.")
    p_stage.set_defaults(func=cmd_stage_takethis)

    p_clear = sub.add_parser("clear-takethis", help="Empty TAKE_THIS/ of whatever's currently staged there. Run when a new chunk starts. Never touches project/.")
    p_clear.set_defaults(func=cmd_clear_takethis)

    p_materialize = sub.add_parser("materialize", help="Extract MATERIALIZE-tagged code blocks from a contract file and write them to their declared destination paths, byte-for-byte.")
    p_materialize.add_argument("--contract", required=True, help="Contract ID, e.g. C01-02. The chunk directory is derived from the ID itself.")
    p_materialize.add_argument("--force", action="store_true", help="Overwrite a destination file that already exists. Use deliberately.")
    p_materialize.set_defaults(func=cmd_materialize)

    p_commit_project = sub.add_parser("commit-project", help="Commit everything staged in project/'s own nested git repository. Safe to call routinely -- a no-op if nothing changed.")
    p_commit_project.add_argument("--message", default=None, help="Commit message. Defaults to a generic 'Update project/ artifacts' if omitted.")
    p_commit_project.set_defaults(func=cmd_commit_project)

    p_self_check = sub.add_parser("self-check", help="Diagnose drift between gatekeeper.py's actual behavior and what the Factory's documents claim about it. Diagnostic only -- reports findings, never modifies anything.")
    p_self_check.set_defaults(func=cmd_self_check)

    p_release_check = sub.add_parser("release-check", help="Scan a release-bound artifact (manuscript, REPRODUCIBILITY.md) for local-path leaks and key-fact inconsistencies before submission.")
    p_release_check.add_argument("--manuscript", required=True, help="Path to the manuscript or primary release artifact to scan.")
    p_release_check.add_argument("--files", nargs="*", default=None, help="Additional release files to scan for local paths (e.g. REPRODUCIBILITY.md). The manuscript is always included.")
    p_release_check.add_argument("--key-facts", default=None, help="Path to project/key_facts.md. If omitted, the key-fact consistency check is skipped.")
    p_release_check.set_defaults(func=cmd_release_check)

    p_acq_audit = sub.add_parser("acquisition-audit", help="Scan data-acquisition scripts and their contract reports for data-generation function definitions and simulation-indicating language before trusting their output.")
    p_acq_audit.add_argument("--scripts", nargs="*", default=None, help="Paths to acquisition scripts to scan (structural + textual).")
    p_acq_audit.add_argument("--reports", nargs="*", default=None, help="Paths to contract reports to scan (textual only).")
    p_acq_audit.set_defaults(func=cmd_acquisition_audit)

    p_evidence_check = sub.add_parser("evidence-check", help="Cross-check a contract report's declared verdict and pre-registered criterion against its own backing JSON artifact, and flag degenerate metrics.")
    p_evidence_check.add_argument("--reports", nargs="*", default=None, help="Paths to contract_report.md files, each with a '## Verdict Cross-Check' block.")
    p_evidence_check.set_defaults(func=cmd_evidence_check)

    p_check = sub.add_parser("check", help="Run the implemented checks for one contract. v1.4.2 amendment: for a manifest contract whose scientific_claim_tier is T-COMP/T-CAUSAL, also mechanically enforces the Mandatory Mechanical Gate (Required Verification Commands, verify-contract, lint-contract, recompute, stamp presence -- exit 17). v2.2.0 addition: also runs Fail-Closed Tier Inference regardless of the declared tier, to catch the declaration itself being too low (exit 18).")
    p_check.add_argument("--contract", default=None)
    p_check.add_argument("--manifest", default=None, help="Path to execution_manifest.yaml to auto-derive frozen_files/required_reports.")
    p_check.add_argument("--frozen", nargs="*", default=None, help="Frozen file paths (supplements/overrides manifest).")
    p_check.add_argument("--reports", nargs="*", default=None, help="Report paths to validate (supplements/overrides manifest).")
    p_check.add_argument("--required-sections", nargs="*", default=None, help=f"Override default required section strings {DEFAULT_REQUIRED_SECTIONS}.")
    p_check.add_argument("--allow-dirty", action="store_true", help="Skip the clean-working-tree check. Only for active Phase 2 work.")
    p_check.set_defaults(func=cmd_check)

    p_verify_contract = sub.add_parser("verify-contract", help="v1.4.2 -- independently re-executes every command a contract report declares under '## Verification' and checks the real exit code.")
    p_verify_contract.add_argument("--reports", nargs="*", default=None, help="Paths to contract_report.md files.")
    p_verify_contract.set_defaults(func=cmd_verify_contract)

    p_lint_contract = sub.add_parser("lint-contract", help="v1.4.2 -- scans scripts for swallowed exceptions and fabricated-statistical-input patterns, and checks auto-frozen verification machinery for tampering.")
    p_lint_contract.add_argument("--scripts", nargs="*", default=None, help="Paths to scripts to lint.")
    p_lint_contract.add_argument("--contract", default=None, help="Contract ID, to check frozen verification machinery against its recorded snapshot.")
    p_lint_contract.set_defaults(func=cmd_lint_contract)

    p_recompute = sub.add_parser("recompute", help="v1.4.2 -- for a report declaring a '## Recompute Declaration' block, runs the declared independent script and compares its output to the artifact's claimed value.")
    p_recompute.add_argument("--reports", nargs="*", default=None, help="Paths to contract_report.md files.")
    p_recompute.set_defaults(func=cmd_recompute)

    p_stamp_report = sub.add_parser("stamp-report", help="v1.4.2 -- appends a tamper-evident Gatekeeper Verification Stamp to a contract report, containing real verify-contract/lint-contract/recompute results, git diff, and frozen-file status.")
    p_stamp_report.add_argument("--report", required=True, help="Path to the contract_report.md to stamp.")
    p_stamp_report.add_argument("--contract", default=None, help="Contract ID, to check frozen verification machinery against its recorded snapshot.")
    p_stamp_report.set_defaults(func=cmd_stamp_report)

    p_verify_stamps = sub.add_parser("verify-stamps", help="v1.4.2 -- checks stamp integrity only (no side effects); does not append a new stamp.")
    p_verify_stamps.add_argument("--reports", nargs="*", default=None, help="Paths to contract_report.md files.")
    p_verify_stamps.set_defaults(func=cmd_verify_stamps)

    p_tier_check = sub.add_parser("tier-check", help="v2.2.0 -- fail-closed minimum Scientific Claim Tier inference from a contract's own text, plus operation-class-conflation, statistical-protocol-language, and semantic/operator-test-presence heuristics.")
    p_tier_check.add_argument("--contract", default=None, help="Contract ID, e.g. C01-02 (locates the contract file automatically).")
    p_tier_check.add_argument("--contract-file", default=None, help="Explicit path to a contract .md file (overrides --contract's auto-location).")
    p_tier_check.add_argument("--declared-tier", default=None, help="Override the tier parsed from the contract file (NONE/T-DESC/T-COMP/T-CAUSAL).")
    p_tier_check.add_argument("--reports", nargs="*", default=None, help="Optional contract_report.md path(s), scanned alongside the contract for semantic-test-marker presence.")
    p_tier_check.set_defaults(func=cmd_tier_check)

    p_release_certify = sub.add_parser("release-certify", help="v2.2.0 -- aggregate CERTIFIED/NOT CERTIFIED gate across every contract report under --chunks-dir, distinct from any single chunk's PASS. Writes project/RELEASE_CERTIFICATION.md.")
    p_release_certify.add_argument("--chunks-dir", default="project/chunks", help="Root directory containing chunkNN/reports/{{contract_id}}/contract_report.md files. Default: project/chunks")
    p_release_certify.add_argument("--manuscript", default=None, help="Path to the manuscript or primary release artifact (enables the Release Artifact Scan category).")
    p_release_certify.add_argument("--files", nargs="*", default=None, help="Additional release files to scan for local paths alongside --manuscript.")
    p_release_certify.add_argument("--key-facts", default=None, help="Path to project/key_facts.md (enables key-fact consistency warnings).")
    p_release_certify.add_argument("--scripts", nargs="*", default=None, help="Data-acquisition/statistical-computation scripts to scan (enables the Acquisition Audit category).")
    p_release_certify.set_defaults(func=cmd_release_certify)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
