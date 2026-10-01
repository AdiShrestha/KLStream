# v3 plan and evidence schema

The only active project control file is `project/research_plan.json`. It contains the project population and license, explicit observational/simulation/fixture origin, cohort/source-record paths, methodology and dependency lock, paths to freeze, experiments, comparisons, claims, derived analysis plans, release files, and policy. Every experiment has one preregistered seed, model/config, command argv, evaluation splits, threshold, role, and training policy. A comparison gives explicit aligned pairs, the estimand metric, sampling unit (`seed_fixed_test`), alpha, minimum effect, precision target, and decision rule. A claim names its exact estimand, population, scope, and evidence experiments.

The cohort CSV must contain `sample_id,label,group_id,split,source_ids` and may include `entity_ids,timestamp` where required. Source records contain `record_id,origin`; every sample source ID must exist and have the declared origin. A run writes `execution.json`, `result.json`, `predictions.csv`, and training artifacts below its authenticated local attempt directory. Predictions contain `sample_id,label,score`. Probability results include six independently recomputed metrics; ranking results
include AUROC, average precision, accuracy and F1, without Brier/log loss.
The fixed probability log_loss definition clips p and 1-p independently to
[1e-15,1-1e-15] for natural-log evaluation only; other metrics retain original
probabilities. This finite clipped metric is not the unbounded mathematical loss
of an incorrect exact-zero prediction. Report the convention in any claim. Iterative minimized objectives may be signed and finite. Early stopping may end
at its preregistered budget cap with a diagnostic; this is not convergence.
Learned iterative methods additionally include a raw epoch history, checkpoint and initial checkpoint, observed epoch count, best checkpoint, and stopping rationale.

For domain-specific tasks, create an adapter that converts losslessly into a reviewed schema and ships its independent recomputation and mutation tests. A binary-classification receipt must never be relabelled as regression, causal, topology, or native efficiency evidence. Ranking mode is
limited to binary discrimination/threshold metrics, not learning-to-rank evaluation.
