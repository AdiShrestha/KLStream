# KLStream

**Kafka-less Parallel Stream Processing Runtime for Multi-Core Systems**

A high-performance, single-node stream processing runtime that executes continuous dataflow graphs using bounded queues, explicit backpressure, and cooperative scheduling—without external infrastructure like Kafka.

## Features

- **No External Dependencies**: Pure C++20 implementation with no message broker required
- **Bounded Memory**: Fixed-capacity queues prevent unbounded memory growth
- **Backpressure**: Automatic flow control when downstream operators slow down
- **Parallel Execution**: Worker thread pool with configurable scheduling policies
- **Modular Operators**: Composable source, map, filter, and sink operators
- **Metrics Collection**: Built-in performance monitoring and statistics

## Quick Start

### Prerequisites

- C++20 compatible compiler (GCC 11+, Clang 14+)
- CMake 3.20+
- Ninja (recommended) or Make
- Docker (for x86_64 Linux development on macOS ARM)

### Building Locally (Native)

```bash
# Clone and enter directory
cd brolq

# Make dev script executable
chmod +x scripts/dev.sh

# Build (Debug by default)
./scripts/dev.sh build

# Build Release
./scripts/dev.sh build --release

# Run tests
./scripts/dev.sh test

# Run benchmarks
./scripts/dev.sh bench
```

### Building with Docker (x86_64 Linux on macOS ARM)

For M1/M2/M3 Mac users who need to target x86_64 Linux:

```bash
# Enter Docker development shell
./scripts/dev.sh docker shell

# Inside container, build and test
cmake -B build -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel
cd build && ctest --output-on-failure
```

Or build everything in one command:

```bash
docker compose build build
```

### Running the Example

```bash
# After building
./build/klstream_example_pipeline
```

## Project Structure

```
brolq/
├── include/klstream/        # Public headers
│   ├── core/
│   │   ├── event.hpp       # Event types
│   │   ├── queue.hpp       # Bounded thread-safe queues
│   │   ├── operator.hpp    # Base operator interfaces
│   │   ├── scheduler.hpp   # Scheduling policies
│   │   ├── worker_pool.hpp # Worker thread management
│   │   ├── runtime.hpp     # Main runtime coordination
│   │   └── metrics.hpp     # Metrics collection
│   └── operators/
│       ├── source.hpp      # Source operators
│       ├── sink.hpp        # Sink operators
│       ├── map.hpp         # Map transformations
│       └── filter.hpp      # Filter predicates
├── src/core/               # Implementation files
├── examples/               # Example applications
├── tests/                  # Unit and integration tests
├── benchmarks/             # Performance benchmarks
├── scripts/                # Development scripts
├── CMakeLists.txt          # Build configuration
├── Dockerfile              # Multi-stage Docker build
└── docker-compose.yml      # Docker Compose configuration
```

## Architecture

### Stream Graph Model

```
Source → Operator → Operator → ... → Sink
           ↑           ↑
        Queue       Queue
      (bounded)   (bounded)
```

### Key Components

1. **Events**: Immutable data units with optional metadata (key, timestamp)
2. **Queues**: Bounded MPMC queues with blocking/non-blocking operations
3. **Operators**: Processing units (Source, Map, Filter, Sink)
4. **Scheduler**: Distributes work to worker threads (Round-Robin, Work-Stealing)
5. **Runtime**: Coordinates graph execution and lifecycle

### Example Pipeline

```cpp
#include "klstream/klstream.hpp"

int main() {
    klstream::Runtime runtime;
    klstream::StreamGraphBuilder builder;
    
    // Source: generate integers 1..1000
    klstream::SequenceSource::Config src_cfg;
    src_cfg.count = 1000;
    builder.add_source(std::make_unique<klstream::SequenceSource>("src", src_cfg));
    
    // Map: square each number
    builder.add_operator(klstream::make_int_map("square", 
        [](int64_t x) { return x * x; }));
    
    // Filter: keep even numbers
    builder.add_operator(klstream::make_filter("even", 
        klstream::filters::even()));
    
    // Sink: aggregate results
    auto sink = std::make_unique<klstream::AggregatingSink>("agg");
    auto* sink_ptr = sink.get();
    builder.add_sink(std::move(sink));
    
    // Connect operators
    builder.connect("src", "square")
           .connect("square", "even")
           .connect("even", "agg");
    
    // Run pipeline
    runtime.init(std::move(builder));
    runtime.start();
    // ... wait for completion
    runtime.stop();
    
    std::cout << "Sum: " << sink_ptr->sum() << std::endl;
    return 0;
}
```

## Configuration

### Runtime Configuration

```cpp
klstream::RuntimeConfig config;
config.num_workers = 4;  // Worker threads (0 = auto-detect)
config.scheduling_policy = klstream::SchedulingPolicy::RoundRobin;
config.enable_metrics = true;
```

### Build Options

| Option | Default | Description |
|--------|---------|-------------|
| `KLSTREAM_BUILD_TESTS` | ON | Build unit tests |
| `KLSTREAM_BUILD_BENCHMARKS` | ON | Build benchmarks |
| `KLSTREAM_BUILD_EXAMPLES` | ON | Build examples |
| `KLSTREAM_ENABLE_SANITIZERS` | OFF | Enable ASan/UBSan |
| `KLSTREAM_ENABLE_LTO` | OFF | Enable Link Time Optimization |

## Performance

Run benchmarks to measure:

- **Throughput**: Events processed per second
- **Latency**: End-to-end processing time
- **Queue efficiency**: Push/pop operations

```bash
./scripts/dev.sh bench
```

## Development

### Code Formatting

```bash
./scripts/dev.sh format
```

### Static Analysis

```bash
./scripts/dev.sh lint
```

### Clean Build

```bash
./scripts/dev.sh clean
./scripts/dev.sh build
```

## License

MIT License - See LICENSE file for details.

## References

- Based on concepts from Apache Flink, StreamIt, and SEDA
- Implements bounded MPMC queues with backpressure
- Uses cooperative scheduling similar to OpenMP runtime
