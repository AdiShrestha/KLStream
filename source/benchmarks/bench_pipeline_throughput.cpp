#include <benchmark/benchmark.h>
#include "klstream/core/runtime.hpp"
#include "klstream/operators/source.hpp"
#include "klstream/operators/map.hpp"
#include "klstream/operators/filter.hpp"
#include "klstream/operators/sink.hpp"
#include <atomic>
#include <cmath>

using namespace klstream;
using namespace std::chrono;

static void BM_PipelineWorkerScaling(benchmark::State& state) {
    int workers = state.range(0);
    
    for (auto _ : state) {
        SPSCQueue<Event<uint64_t>> q1(4096);
        SPSCQueue<Event<uint64_t>> q2(4096);
        SPSCQueue<Event<uint64_t>> q3(4096);
        
        uint64_t seq = 0;
        SourceOperator<uint64_t> src("src", &q1, [&seq](Event<uint64_t>& out, uint64_t) {
            out = Event<uint64_t>::make(++seq); return true;
        });
        MapOperator<uint64_t, uint64_t> map("map", &q1, &q2, [](uint64_t x){ return x*x; });
        FilterOperator<uint64_t> filter("flt", &q2, &q3, [](uint64_t x){ return x%2==0; });
        std::atomic<uint64_t> count{0};
        SinkOperator<uint64_t> sink("snk", &q3, [&count](const Event<uint64_t>&){ count++; });
        
        Runtime rt;
        for(int i=0; i<workers; ++i) rt.add_worker();
        
        rt.register_op(&src, 0);
        rt.register_op(&map, workers > 1 ? 1 : 0);
        rt.register_op(&filter, workers > 2 ? 2 : (workers > 1 ? 1 : 0));
        rt.register_op(&sink, workers > 3 ? 3 : (workers > 2 ? 2 : (workers > 1 ? 1 : 0)));
        
        auto start = high_resolution_clock::now();
        rt.start();
        rt.wait_for(seconds(1));
        rt.stop();
        auto end = high_resolution_clock::now();
        
        state.SetItemsProcessed(count.load());
        state.SetIterationTime(duration_cast<duration<double>>(end - start).count());
    }
}
BENCHMARK(BM_PipelineWorkerScaling)->Arg(1)->Arg(2)->Arg(3)->Arg(4)->UseManualTime();

static void BM_ExpensiveCompute(benchmark::State& state) {
    int iterations = state.range(0);
    int workers = state.range(1);
    
    for (auto _ : state) {
        SPSCQueue<Event<double>> q1(4096);
        SPSCQueue<Event<double>> q2(4096);
        
        double val = 1.0;
        SourceOperator<double> src("src", &q1, [&val](Event<double>& out, uint64_t) {
            out = Event<double>::make(val += 0.1); return true;
        });
        MapOperator<double, double> map("map", &q1, &q2, [iterations](double x){ 
            for(int i=0; i<iterations; ++i) x = std::sin(x);
            return x;
        });
        std::atomic<uint64_t> count{0};
        SinkOperator<double> sink("snk", &q2, [&count](const Event<double>&){ count++; });
        
        Runtime rt;
        for(int i=0; i<workers; ++i) rt.add_worker();
        
        rt.register_op(&src, 0);
        rt.register_op(&map, workers > 1 ? 1 : 0);
        rt.register_op(&sink, workers > 2 ? 2 : (workers > 1 ? 1 : 0));
        
        auto start = high_resolution_clock::now();
        rt.start();
        rt.wait_for(seconds(1));
        rt.stop();
        auto end = high_resolution_clock::now();
        
        state.SetItemsProcessed(count.load());
        state.SetIterationTime(duration_cast<duration<double>>(end - start).count());
    }
}
BENCHMARK(BM_ExpensiveCompute)
    ->Args({100, 1})->Args({100, 3})
    ->Args({1000, 1})->Args({1000, 3})
    ->Args({10000, 1})->Args({10000, 3})
    ->UseManualTime();
