# KLStream Implementation Report

## Commits & Progress
- **Commit 1**: `chore: remove obsolete files from old architecture`
  - Deleted deprecated files including `queue.hpp`, `scheduler.hpp`, `worker_pool.hpp` and their respective tests.
- **Commit 2**: `feat(core): add config, pinning, and metrics modules`
  - Implemented core constants (`config.hpp`), Apple Silicon core affinity mapping (`pinning.hpp`), and metrics trackers (`metrics.hpp`).
- **Commit 3**: `feat(core): add event type and lock-free queues`
  - Implemented `event.hpp`, rigtorp-style `spsc_queue.hpp`, and Dmitry Vyukov-style `mpmc_queue.hpp`.
- **Commit 4**: `feat(core): add execution engine and backpressure trackers`
  - Implemented `operator.hpp`, thread manager `worker.hpp`, global coordinator `runtime.hpp`, and research extensions in `backpressure.hpp`.
- **Commit 5**: `feat(operators): add standard and window operators`
  - Implemented stateless operators (`source.hpp`, `map.hpp`, `filter.hpp`, `sink.hpp`) and stateful windowing operators (`aggregate.hpp`, `window.hpp`).
- **Commit 6**: `feat(examples): add CMake build system and example pipelines`
  - Added root `CMakeLists.txt` configuring fetchcontent for testing/benchmarking.
  - Implemented the `basic_pipeline` and `yahoo_streaming_benchmark` examples.
- **Commit 7**: `test: add unit and integration tests`
  - Implemented GoogleTest suites for queues, operators, backpressure, and pipeline integration.
- **Commit 8**: `bench: add google benchmark suites`
  - Implemented microbenchmarks for SPSC queue and end-to-end pipelines (basic and YSB).
- **Commit 9**: `feat(research): add research extensions and benchmark scripts`
  - Added scripts for automated benchmark execution and implemented the adaptive backpressure and core pinning research extensions.
- **Commit 10**: `fix(build): resolve ambiguous struct and gtest discovery`
  - Fixed ambiguous `AffinityConfig` struct definition in `core_pinning` research extension.
  - Ensured correct CMake target inclusion for `GoogleTest`.
- **Commit 11**: `test: fix capacities in queue and operator tests`
  - Fixed `Operator_BlockedWhenOutputFull` and `SourceOperator_PendingRetry` capacity logic.
  - Aligned GoogleTests with the strict bounds of `SPSCQueue` lock-free operations.
