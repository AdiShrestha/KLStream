cmake_minimum_required(VERSION 3.20)

# Benchmarks directory CMakeLists.txt

include(FetchContent)

FetchContent_Declare(
    benchmark
    GIT_REPOSITORY https://github.com/google/benchmark.git
    GIT_TAG v1.8.3
)

set(BENCHMARK_ENABLE_TESTING OFF CACHE BOOL "" FORCE)
set(BENCHMARK_ENABLE_INSTALL OFF CACHE BOOL "" FORCE)

FetchContent_MakeAvailable(benchmark)

# Throughput benchmark
add_executable(throughput_benchmark
    throughput_benchmark.cpp
)
target_link_libraries(throughput_benchmark
    PRIVATE
        klstream_core
        benchmark::benchmark
)

# Latency benchmark
add_executable(latency_benchmark
    latency_benchmark.cpp
)
target_link_libraries(latency_benchmark
    PRIVATE
        klstream_core
        benchmark::benchmark
)
