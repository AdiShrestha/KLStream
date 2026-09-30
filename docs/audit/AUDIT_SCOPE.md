# Audit scope and limits — 2026-09-30

Legacy root: `/Users/adi/adi/brolq`, branch rehabilitation/phase-1 at
`83545b7c845454af309794d08a1ec2d41220a7db`, with existing uncommitted results and
untracked author documents. Public main before migration was
`bc095f0be747216b59de08ec0bbf06163cf67553`.

All 12,844 non-.git files were inventoried. 11,735 generated/build/cache/snapshot
files were inventoried by path and size, not semantically certified. The other
1,109 files were SHA-256 hashed; 537 text files were scanned, Python code was AST
parsed, 94 JSON files parsed and 537 CSV bodies streamed. Headerless CSV summaries
count the first row separately; consult the index before interpreting its row count.
The machine census categorizes 163 legacy source, 632 historical evidence, 266
historical claim/control, 37 other, and 11 superseded factory-v2 files. Category is
triage, not a conclusion that every line is safe or defective.

Manual analysis traced high-risk paths from acquisition to transformation, splits,
model training/loading, engine queues/operators/lifecycle, experiment dispatch,
metrics/statistics, figures/verdicts, paper checks and factory certification. Selected
counterexamples were executed on isolated fixtures. No legacy research experiment
was rerun. No unknown pickle/model blob was deserialized for this audit. No audit
can establish that all bugs, races, provenance problems or methodology errors are gone.

The inventories, excerpts, counterexample scripts and outputs make findings
reviewable without the old folder. Generated binaries, archived bundles and full
raw traces were not copied into the new project. Git tags preserve the public old
main and the later local legacy snapshot; the migration receipt states exact scopes.
Large `.snapshot_baseline` bundles and caches remain local; they are not new Git blobs.

Factory 3.3.0's complete 276-test suite passed in an environment permitting local
Unix sockets. In the restrictive sandbox the same suite had one socket permission
error. Independently, removing a supervisor signature still passed audit and yielded
SEALED_EVALUATION_ATTESTED. Passing tests and this failing assurance property coexist.
New engine release, ASan/UBSan and ThreadSanitizer fixture checks passed; 20 public headers were
compiled independently. All such outputs are software checks on declared fixtures,
not published empirical evidence. See `verification_summary.json` and `plan.md`.
