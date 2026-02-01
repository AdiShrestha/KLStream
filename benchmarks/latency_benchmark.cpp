/**
 * @file latency_benchmark.cpp
 * @brief Latency benchmarks for KLStream
 */

#include <benchmark/benchmark.h>
#include <chrono>
#include <vector>
#include <algorithm>
#include <numeric>

#include "klstream/klstream.hpp"

using namespace klstream;

static void BM_EndToEndLatency(benchmark::State& state) {
    const int num_workers = static_cast<int>(state.range(0));
    
    for (auto _ : state) {
        state.PauseTiming();
        
        RuntimeConfig config;
        config.num_workers = static_cast<std::uint32_t>(num_workers);
        
        Runtime runtime(config);
        StreamGraphBuilder builder;
        
        SequenceSource::Config source_config;
        source_config.start = 1;
        source_config.count = 1000;
        
        auto source = std::make_unique<SequenceSource>("source", source_config);
        auto sink = std::make_unique<CountingSink>("sink");
        auto* sink_ptr = sink.get();
        
        builder
            .add_source(std::move(source))
            .add_sink(std::move(sink))
            .connect("source", "sink");
        
        runtime.init(std::move(builder));
        
        state.ResumeTiming();
        
        auto start = std::chrono::high_resolution_clock::now();
        runtime.start();
        
        // Wait for completion
        while (sink_ptr->count() < 1000) {
            std::this_thread::yield();
        }
        
        auto end = std::chrono::high_resolution_clock::now();
        runtime.stop();
        
        auto duration = std::chrono::duration_cast<std::chrono::microseconds>(end - start);
        state.SetIterationTime(duration.count() / 1e6);
    }
    
    state.SetItemsProcessed(state.iterations() * 1000);
}
BENCHMARK(BM_EndToEndLatency)->Arg(1)->Arg(2)->Arg(4)->UseManualTime();

static void BM_PipelineLatency(benchmark::State& state) {
    const int pipeline_depth = static_cast<int>(state.range(0));
    
    for (auto _ : state) {
        state.PauseTiming();
        
        RuntimeConfig config;
        config.num_workers = 2;
        
        Runtime runtime(config);
        StreamGraphBuilder builder;
        
        SequenceSource::Config source_config;
        source_config.start = 1;
        source_config.count = 100;
        
        auto source = std::make_unique<SequenceSource>("source", source_config);
        builder.add_source(std::move(source));
        
        std::string prev_name = "source";
        for (int i = 0; i < pipeline_depth; i++) {
            std::string name = "pass_" + std::to_string(i);
            auto pass = make_operator(name, [](Event& e, OperatorContext& ctx) {
                ctx.emit(std::move(e));
            });
            builder.add_operator(std::move(pass));
            builder.connect(prev_name, name);
            prev_name = name;
        }
        
        auto sink = std::make_unique<CountingSink>("sink");
        auto* sink_ptr = sink.get();
        builder.add_sink(std::move(sink));
        builder.connect(prev_name, "sink");
        
        runtime.init(std::move(builder));
        
        state.ResumeTiming();
        
        auto start = std::chrono::high_resolution_clock::now();
        runtime.start();
        
        while (sink_ptr->count() < 100) {
            std::this_thread::yield();
        }
        
        auto end = std::chrono::high_resolution_clock::now();
        runtime.stop();
        
        auto duration = std::chrono::duration_cast<std::chrono::microseconds>(end - start);
        state.SetIterationTime(duration.count() / 1e6);
    }
}
BENCHMARK(BM_PipelineLatency)->Arg(1)->Arg(2)->Arg(4)->Arg(8)->UseManualTime();

BENCHMARK_MAIN();
