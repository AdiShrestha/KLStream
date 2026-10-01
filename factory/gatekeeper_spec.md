# Gatekeeper implementation contract — v3.3.1

Implemented commands are `init`, `freeze`, `run`, `record`, `audit`, `certify`, `status`, and `handoff`. The implementation is in `gatekeeper.py`, using `engine/io.py`, `engine/plan.py`, `engine/metrics.py`, `engine/audit.py`, `engine/contract.py`, `engine/supervisor.py`, `engine/schema.py`, and `engine/attacks.py`. This list is the complete machine surface; no prose command in another document is implied to exist.

`freeze` validates and snapshots the plan, all declared source/data/methodology bytes, and active policy code. `run` executes preregistered argv safely, authenticates a local attempt ledger and captures each dispatch, and calls `record`. `record` verifies one run's raw predictions and training receipt. `audit` reloads all current receipts, recomputes metrics, validates split/source joins, compares every preregistered unit, and writes `project/audit_report.json`. `certify` repeats the audit and requires a digest-bound, nine-topic Architect review; it writes `project/RELEASE_CERTIFICATION.json`. `status` is informational. `handoff` packages evidence and reports to `TAKE_THIS/`.

The audit report always prints `checks_executed`, `diagnostics`, file bindings, and `not_automated`. A PASS is never synthesized from a contract report, a status string, or the existence of a JSON key. A non-implemented check must not be described as executed.

## v3.3.1 command surface

The original lifecycle commands remain available. Scientific verification commands are now registered and fail closed: `verify-constitution-coverage` (31), `verify-training-sufficiency` (32), `verify-split-integrity` (33), `verify-result-plausibility` (34), `verify-cross-artifact-traceability` (35), and `verify-reproducibility` (36). `acquisition-audit` and `tier-check` retain their historical exit codes (11 and 18). `verify-coverage-liveness` (40) checks callable reachability, duplicate attribution, and dynamic-rule drift. `release-certify` aggregates coverage and the lifecycle audit. These checks inspect artifact values and provenance; they do not claim to establish publication truth.

`run_manifest.json` may contain `convergence_evidence`, `test_label_distribution`, `evaluation_sample_size`, `sample_size_justification`, and `investigation_note`. Claim artifacts must carry an investigation note whenever plausibility checks flag them.

## Local 3.3.1 enforcement boundary

Only isolated Python/stdlib binary classification is implemented. Canonical typed
and converted legacy launches share validation and ordered arguments. Signature
version 2 authenticates freeze and complete execution bindings; audit verifies
current keys, ledger membership and outputs. Missing/altered receipts block audit.
Failed attempts require amendments. No sealed holdout or hostile-worker isolation
is implemented. Assurance and review status remain separate.

Hardware rows currently describe one-batch inference service observations and an
explicit trial horizon; they are not native offered-load streaming evidence.
Registry validation checks definitions only; run_self_tests.py supplies actual
selected regression execution. Statistical validity and truthful source generation
still require semantic review. Root plan KLS-02 remains open.
