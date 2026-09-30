# Venue Requirements

Status: Frozen File (same policy as architecture.md — see C43, C50's Backward Compatibility
section). Created at Project Initialization. Reviewed at MAR (`methodology_adversarial_review.md`).
Checked for drift at every Chunk Review's Methodology Drift Check and Baseline Completeness Check.

This document exists to give the Architect an external reference point. A specification with no
external reference point is incomplete (C52).

---

## Target Venue

{{VENUE_NAME}} — e.g. IEEE Transactions on Geoscience and Remote Sensing (TGRS)

## Recent Venue Publications (minimum 3, required — MAR-5 fails without these)

Fill with real papers, read closely enough to extract these fields honestly. Do not fabricate
entries or approximate from memory alone (C01, C08) — locate and read the actual paper.

| Paper | Year | Methodology | Baselines used | Sample size | Key convention worth matching |
|---|---|---|---|---|---|
| {{citation 1}} | | | | | |
| {{citation 2}} | | | | | |
| {{citation 3}} | | | | | |

## Minimum Expected Baselines For This Venue

State the actual categories, drawn from the table above, not a generic list:

1. Current operational/industry standard
2. At least one non-learned statistical method
3. At least one competitive learned method from the last 2 years of venue publications

If fewer than 3 distinct baseline categories are achievable, state why explicitly here — this
becomes an MAR-2 CONDITIONAL PASS finding, not a silent gap discovered at Chunk Review.

## Minimum Expected Sample Sizes

Set real numbers for this project, derived from the venue table above and the actual data
available — not copied from a generic template:

- Evaluation units (lakes / subjects / sessions / whatever the unit is): {{N}}
- Synthetic/injected instances per condition, if applicable: {{N}}
- Real events available for retrospective validation: {{N}} — if this is fewer than 3, state the
  implication for what claims are and aren't supportable up front, here, not after the paper is
  written.

## Statistical Method Requirement

For every comparative (T-COMP) or causal (T-CAUSAL) claim this project will make, name the specific
statistical method that will support it (bootstrap CI, permutation test, paired significance test,
cross-validation with reported variance). A raw point estimate with no method named here is not
sufficient evidence for a T-COMP or T-CAUSAL claim (SVI-003) — a sample count above the minimum
threshold is necessary but not sufficient; the method itself must exist and be named.

## Minimum Meaningful Effect Size

For every T-CAUSAL claim's core metric, state not just the null/below-chance threshold (AUC-ROC ≤
0.5, no significant correlation) but the minimum value that would count as *meaningful*, not just
*technically above chance*. A result that clears 0.5 but sits far below this line is still a
Constitution C53 Stop Condition, not a positive finding to report and move past.

| Core metric | Below-chance threshold | Minimum meaningful value | Basis for the meaningful threshold |
|---|---|---|---|
| {{e.g. AUC-ROC, primary detection task}} | 0.5 | {{e.g. 0.65}} | {{cite the venue table above, or a domain-standard threshold — not an arbitrary round number}} |

## Pre-Registered Falsification Criteria

For each core hypothesis, state what result would falsify it and what action follows — declared now,
before anyone has an incentive to rationalize a disappointing number after the fact. This is
distinct from MAR-7 (what's publishable if the hypothesis fails): this answers what result changes
the methodology *mid-project*, not what's salvageable at the end.

| Hypothesis | Falsifying result | Action if falsified |
|---|---|---|
| {{e.g. "TS-MAE detects precursors"}} | {{e.g. "Score-C AUC-ROC < 0.65 on real-event retrospective"}} | {{e.g. "Reframe as feasibility study, do not claim detection"}} |

If a falsifying result occurs and is not caught here, Constitution C53 is the fallback — but a
declared criterion is the stronger, earlier form of the same protection, and costs nothing to write
down before the experiment runs.

## Required Ablation Types

State which apply to this project's architecture:

- Sensor/channel ablation
- Architecture ablation (if a novel architecture)
- Threshold/hyperparameter sensitivity analysis — name every hyperparameter that will need one
  (D-018): {{list}}

## Expected Data Properties (feeds Reality Gate — do not skip this)

State real, domain-grounded expectations now, before any data is acquired. Reality Gate checks
actual data against these numbers; a threshold invented after seeing the data is not a real gate.

**Domain grounding requirement:** every number below must cite one of: **(a)** a peer-reviewed
publication reporting the same statistic for the same sensor/region/season, **(b)** the sensor's
documented revisit cycle plus known regional climatology, or **(c)** a prior dataset from the same
region with documented completeness. "Architect's estimate" is not a valid basis. If none of (a)–(c)
is available, write "UNKNOWN — Reality Gate will use conservative defaults" explicitly, and flag it
as an MAR-6 finding — an unfounded number silently treated as ground truth defeats the entire
purpose of this section.

- Expected missing-data / gap rate for this domain, region, and season: {{N}}% — basis: {{(a)/(b)/(c), cited}}
- Expected temporal coverage: {{date range}}
- Expected sensors/channels present: {{list}}
- Expected revisit frequency (feeds `acquisition_provenance.json`'s scene-count consistency check): {{e.g. "6-day nominal for Sentinel-1 dual-satellite operation"}} — basis: {{cited}}
- Any property whose real-data value being *suspiciously better than expected* (e.g. suspiciously
  complete, suspiciously uniform) should itself be treated as a red flag, not a convenience: state
  which properties, and why, here.

## Title/Claim Conventions

- Every adjective in the eventual title must correspond to a specific, named experimental test —
  list the adjectives you expect to use and the test each one requires, now, before writing begins:

| Anticipated title adjective | Required validating test |
|---|---|
| {{e.g. "cloud-robust"}} | {{e.g. must be tested against cloud-contaminated inputs, not simulated features}} |
| {{e.g. "real-time"}} | {{e.g. latency measurement under realistic load}} |
| {{e.g. "precursor detection"}} | {{e.g. successful detection on ≥1 real event, with the threshold declared before the test runs, not chosen afterward}} |

## Release Artifact Notes

Any known personal-machine paths, credentials, or internal-only identifiers that must not appear in
anything targeted for external release: {{list, or "none identified at initialization — re-check at
release via gatekeeper.py release-check"}}
