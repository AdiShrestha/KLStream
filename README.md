# KLStream research rehabilitation

This is the active replacement for the legacy KLStream/Brolq tree. Read
[plan.md](plan.md) before conducting research or asking an agent to implement it.
The legacy paper, results, acquisition scripts, model files and certificates are
not accepted as research evidence. The audit reproduced synthetic data labelled
as a LOBSTER academic sample, simulated quantities presented as timings, fabricated
plots, invalid statistical verdicts, engine defects and factory assurance gaps.

The current deliverable is a small C++17 engine foundation, an evidence-backed
research plan, and Software Factory 3.3.0. It is **not submission ready**. No new
research benchmark or market-anomaly result has been produced. Generated inputs
in the tests and defect probes are explicitly test fixtures.

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel 2
ctest --test-dir build --output-on-failure
cmake -S . -B build-sanitizers -DCMAKE_BUILD_TYPE=Debug -DKLSTREAM_SANITIZERS=ON
cmake --build build-sanitizers --parallel 2
ctest --test-dir build-sanitizers --output-on-failure
```

The engine build requires CMake, a C++17 compiler and threads; it downloads no
dependencies. Factory tests use `python3 factory/run_self_tests.py`; the complete
suite includes local Unix sockets and requires an environment permitting them.
Passing those tests does not resolve the factory defects documented in the plan.
Do not freeze a confirmatory epoch or trust certification until KLS-02 is complete.
The placeholder `project/research_plan.json` is intentionally not a valid study.

Architect and Implementor sessions start at [project/agent_handoff.md](project/agent_handoff.md).
API boundaries and residual risks are in [docs/ENGINE_CONTRACT.md](docs/ENGINE_CONTRACT.md).
Audit scope, inventories and reproduced counterexamples are in [docs/audit](docs/audit).
Git preservation receipts are in [docs/audit/git_migration.json](docs/audit/git_migration.json).

The engine retains AGPL-3.0; the factory retains its proprietary license. See
[LICENSE](LICENSE) for the scopes. Do not assume public market data can be redistributed.
