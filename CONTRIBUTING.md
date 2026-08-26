# Contributing to KLStream

Thank you for your interest in contributing to KLStream! We welcome contributions to our low-latency parallel stream processing engine.

## Code Standards

- **Language Standard:** C++17 standard strictly enforced (`set(CMAKE_CXX_STANDARD 17)` without compiler extensions).
- **Concurrency & Memory Model:** Lock-free primitives (`SPSCQueue`, `MPMCQueue`) must strictly adhere to C++11 memory ordering semantics (`acquire`/`release`/`relaxed`). No undefined behavior or race conditions.
- **Header Structure:** All public headers under `source/include/klstream/` must be self-contained, include `#pragma once`, and use canonical angle-bracket paths `<klstream/...>`.
- **Code Style:** Formatted using `clang-format`. Run `./scripts/dev.sh format` before submitting PRs.

## Building and Testing

KLStream uses standard CMake Presets for all configurations:

```bash
# Configure and build Release preset
cmake --preset release
cmake --build --preset release

# Run full test suite
ctest --preset release --output-on-failure

# Or using the developer script
./scripts/dev.sh test release
```

### Sanitizers

All pull requests must pass AddressSanitizer, UndefinedBehaviorSanitizer, and ThreadSanitizer checks:

```bash
./scripts/dev.sh test asan
./scripts/dev.sh test tsan
```

## Pull Request Process

1. Fork the repository and create your branch from `main`.
2. Ensure all existing 24 unit and pipeline tests pass.
3. If introducing new functionality or operators, include unit tests under `source/tests/`.
4. Ensure `git status` is clean and all code is formatted (`./scripts/dev.sh format`).
5. Open a Pull Request with a clear description of changes and test evidence.

## Licensing

By contributing to KLStream, you agree that your contributions will be licensed under the project's [GNU Affero General Public License v3](LICENSE).
