/**
 * @file throughput_benchmark.cpp
 * @brief Throughput benchmarks for KLStream
 */

#include <benchmark/benchmark.h>

#include "klstream/klstream.hpp"

using namespace klstream;

static void BM_QueuePushPop(benchmark::State& state) {
    BoundedQueue<4096> queue;
    
    for (auto _ : state) {
        Event e{std::int64_t{42}};
        queue.push(std::move(e));
        auto result = queue.pop();
        benchmark::DoNotOptimize(result);
    }
    
    state.SetItemsProcessed(state.iterations());
}
BENCHMARK(BM_QueuePushPop);

static void BM_QueueTryPushPop(benchmark::State& state) {
    BoundedQueue<4096> queue;
    
    for (auto _ : state) {
        Event e{std::int64_t{42}};
        queue.try_push(std::move(e));
        auto result = queue.try_pop();
        benchmark::DoNotOptimize(result);
    }
    
    state.SetItemsProcessed(state.iterations());
}
BENCHMARK(BM_QueueTryPushPop);

static void BM_MapOperator(benchmark::State& state) {
    auto square = make_int_map("square", [](std::int64_t x) { return x * x; });
    
    auto output_queue = std::make_shared<Queue>();
    OperatorContext ctx("test", 0);
    ctx.add_output(output_queue);
    
    for (auto _ : state) {
        Event e{std::int64_t{42}};
        square->process(e, ctx);
        auto result = output_queue->try_pop();
        benchmark::DoNotOptimize(result);
    }
    
    state.SetItemsProcessed(state.iterations());
}
BENCHMARK(BM_MapOperator);

static void BM_FilterOperator(benchmark::State& state) {
    auto filter = make_filter("even", filters::even());
    
    auto output_queue = std::make_shared<Queue>();
    OperatorContext ctx("test", 0);
    ctx.add_output(output_queue);
    
    std::int64_t i = 0;
    for (auto _ : state) {
        Event e{i++};
        filter->process(e, ctx);
        output_queue->try_pop();  // Clear output
    }
    
    state.SetItemsProcessed(state.iterations());
}
BENCHMARK(BM_FilterOperator);

static void BM_EventCreation(benchmark::State& state) {
    for (auto _ : state) {
        Event e{std::int64_t{42}};
        benchmark::DoNotOptimize(e);
    }
    
    state.SetItemsProcessed(state.iterations());
}
BENCHMARK(BM_EventCreation);

static void BM_EventWithMetadata(benchmark::State& state) {
    for (auto _ : state) {
        EventMetadata meta(12345ULL);
        Event e{std::int64_t{42}, std::move(meta)};
        benchmark::DoNotOptimize(e);
    }
    
    state.SetItemsProcessed(state.iterations());
}
BENCHMARK(BM_EventWithMetadata);

static void BM_SequenceSource(benchmark::State& state) {
    SequenceSource::Config config;
    config.start = 0;
    config.count = static_cast<std::uint64_t>(state.max_iterations);
    
    auto source = std::make_unique<SequenceSource>("seq", config);
    auto output_queue = std::make_shared<Queue>();
    OperatorContext ctx("seq", 0);
    ctx.add_output(output_queue);
    
    for (auto _ : state) {
        source->generate(ctx);
        output_queue->try_pop();  // Clear
    }
    
    state.SetItemsProcessed(state.iterations());
}
BENCHMARK(BM_SequenceSource);

BENCHMARK_MAIN();
