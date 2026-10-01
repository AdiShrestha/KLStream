# Domain review prompts

## Any empirical ML study
What is the observation and independent unit? Do labels precede modeling? Are group/entity/time splits disjoint? Was threshold selection validation-only? Are all seeds, failed runs, precision targets, intervals, effect sizes, multiplicity, calibration, and failures reported?

## Graph/topology
Are source edge directions, timestamps, labels, and candidate IDs traceable? Does the complex preserve boundary conventions and `B_k B_{k+1}=0`? Are 1-skeleton and filled complexes intentionally distinct? Do batching, pooling, normalization, and isolated nodes preserve the intended operator? Are topology-specific controls meaningful, and are baselines capacity/compute matched rather than merely named?

## Systems/efficiency
What exact device, software versions, driver, synchronization, input shape, warmup, batch, percentile, sustained interval, memory profiler, power sensor, and thermal state produced each number? Are claims bounded to this stack and workload? Are transients and sustained fanless-device behavior reported under a prospectively selected observation interval?

## Statistics and claims
Which test follows from pairing, clusters, distribution and sample size? Is the estimand compatible with the reported unit? Is a null result distinguished from equivalence? Does every claim have a figure/table and every result have a claim or limitation? Does an OOD shift represent deployment, and are subgroups and failure ceilings visible?

This checklist is a review aid; the gate does not pretend to infer mathematical semantics from words.

### Scientific sufficiency reasoning

Choose sample counts, replication and training budgets prospectively for the actual estimand and method. Historical 30-row, 10-per-class and 10-epoch defaults are not universal requirements or proofs of sufficiency. Recorded exceptions and fixed-budget limitations must be explicit; no choice may be changed after seeing test outcomes to rescue a claim. Noniterative methods have no gradient epochs.
