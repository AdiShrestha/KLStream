# KLStream

KLStream is a high-throughput, bounded-queue C++17 stream processing engine foundation designed for deterministic microbatching, windowed aggregations, and concurrent pipeline routing.

## Building and Testing

The engine requires CMake 3.16+, a C++17 compliant compiler, and POSIX threads. It has no external third-party library dependencies.

### Release Build & Test Suite
```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel 2
ctest --test-dir build --output-on-failure
```

### Sanitizer Build (ASan / UBSan)
```sh
cmake -S . -B build-sanitizers -DCMAKE_BUILD_TYPE=Debug -DKLSTREAM_SANITIZERS=ON
cmake --build build-sanitizers --parallel 2
ctest --test-dir build-sanitizers --output-on-failure
```

### ThreadSanitizer Build (TSan)
```sh
cmake -S . -B build-tsan -DCMAKE_BUILD_TYPE=Debug -DCMAKE_CXX_FLAGS="-fsanitize=thread" -DCMAKE_EXE_LINKER_FLAGS="-fsanitize=thread"
cmake --build build-tsan --parallel 2
ctest --test-dir build-tsan --output-on-failure
```

## Architecture & Guarantees

- **Core Queues:** Lock-free Single-Producer Single-Consumer (`SPSCQueue`) and bounded Multi-Producer Multi-Consumer (`MPMCQueue`) with monotonic slot reservation and acquire/release visibility.
- **Queue State Transitions:** Explicit lifecycle (`Open` -> `Closed` -> `Drained` vs `Cancelled`). Cancelled streams fail closed immediately to prevent processing on aborted inputs.
- **Operators:** Bounded batching, tumbling count windows, mapping, filtering, aggregation, source ingestion, and sink dispatch.
- **Engine Invariants:** Memory safety, rate-limiting clock monotonicity, and concurrency invariants are documented in [docs/ENGINE_CONTRACT.md](docs/ENGINE_CONTRACT.md).

## License

The engine under `source/` is licensed under GNU Affero General Public License v3 (AGPL-3.0). See [LICENSE](LICENSE) and `source/LICENSE`.
