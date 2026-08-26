# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-08-26

### Added
- Lock-free SPSC and MPMC ring buffers with cache-aligned acquire/release semantics.
- Closed-loop adaptive batch windowing with EMA queue occupancy feedback.
- Explicit `Runtime` lifecycle state machine (INIT → RUNNING → DRAINING → STOPPED).
- Cache-optimized Isolation Forest scoring engine with 64-byte KLIF binary serialization.
- Reality Gate automated data validation (6 domain invariants, 60/20/20 temporal split).
- Pre-registered falsification protocol with 3 claims (all SUPPORTED).
- 54-run experimental test matrix processing 99,000 events with 0 drops.
- SPSC throughput: 22.14 Mops/sec; scoring latency: 270.99 ns.
- E2E streaming: 1.69M events/sec with zero event loss.
- Complete IEEE-format LaTeX manuscript with 10 BibTeX references.
- 100% claims justification audit (10/10 verified).
- ACM/IEEE Artifact Evaluation guide with 5-minute reproduction.
- Release packaging with SHA-256 digests.
- Security, license, and secrets audit (0 hard violations).
- Software Factory v2.2.0 certification: 72 contracts, CERTIFIED.

### Changed
- Reorganized codebase into structured `source/` tree.
- Normalized all public headers to `<klstream/...>` paths.

### Removed
- Obsolete legacy `src/core/` files from quarantine.

## [Unreleased]

### Added
- Standardized `CMakePresets.json` supporting Debug, Release, ASan/UBSan, TSan, and Benchmark configurations.
- CMake installation and packaging rules exporting `KLStream::klstream` target and `KLStreamConfig.cmake`.
- Automated downstream consumer test verifying external `find_package(KLStream CONFIG REQUIRED)`.
- Self-contained header compilation test target (`test_header_compilation`).
- Single source of truth `VERSION` file driving CMake, C++ version macros, and package metadata.

### Changed
- Reorganized codebase into structured `source/` tree (`include/`, `apps/`, `examples/`, `tests/`, `benchmarks/`, `experiments/`).
- Refactored CMake options and target-scoped compiler warnings into `cmake/KLStreamOptions.cmake` and `cmake/KLStreamWarnings.cmake`.
- Normalized all public header `#include` statements to angle-bracket `<klstream/...>` paths.

### Removed
- Obsolete and uncompiled `src/core/` files from legacy quarantine.
- Broad global ignore rules in `.gitignore` and `.dockerignore`.

## [0.2.0-dev] - 2026-08-26

### Added
- Software Factory v2.2.0 rehabilitation and architectural foundation.
- Full forensic provenance audit of legacy datasets and scientific claims.
- Quarantined external archive of unverified legacy benchmark results (`klstream-legacy-unverified-*.tar.gz`).
- Complete set of 8 core founding artifacts and architectural invariants.

## [0.1.0] - 2026-08-01

### Added
- Initial C++17 implementation of lock-free SPSC ring buffer and MPMC queue.
- Core stream processing pipeline abstraction and worker scheduler.
- Basic map, filter, aggregate, and tumbling window operators.
- Yahoo Streaming Benchmark (YSB) pipeline example.
- Embedded Isolation Forest model and adaptive window operator research prototype.
