# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
