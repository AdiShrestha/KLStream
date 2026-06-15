// research/core_pinning/main.cpp
#include "klstream/core/runtime.hpp"
#include "klstream/operators/source.hpp"
#include "klstream/operators/map.hpp"
#include "klstream/operators/sink.hpp"
#include <iostream>
#include <string>
#include <cmath>

using namespace klstream;
using namespace std::chrono;

struct ExperimentAffinityConfig {
    CoreAffinity source;
    CoreAffinity compute;  // Map, Filter, Aggregate
    CoreAffinity sink;
};

int main(int argc, char* argv[]) {
    std::string mode = "optimised";
    if (argc > 1) mode = argv[1];

    ExperimentAffinityConfig cfg;
    if (mode == "all_any") {
        cfg = { CoreAffinity::Any, CoreAffinity::Any, CoreAffinity::Any };
    } else if (mode == "all_perf") {
        cfg = { CoreAffinity::Performance, CoreAffinity::Performance, CoreAffinity::Performance };
    } else if (mode == "optimised") {
        cfg = { CoreAffinity::Efficiency, CoreAffinity::Performance, CoreAffinity::Efficiency };
    } else if (mode == "reversed") {
        cfg = { CoreAffinity::Performance, CoreAffinity::Efficiency, CoreAffinity::Performance };
    } else {
        std::cerr << "Unknown mode: " << mode << "\n";
        return 1;
    }

    SPSCQueue<Event<double>> q1(4096);
    SPSCQueue<Event<double>> q2(4096);

    SourceOperator<double> source("src", &q1, [](Event<double>& out, uint64_t seq) {
        out = Event<double>::make(static_cast<double>(seq));
        return true;
    });

    MapOperator<double, double> map("compute", &q1, &q2, [](double x) {
        for(int i=0; i<100; ++i) x = std::sin(x);
        return x;
    });

    OperatorMetrics m_snk("snk");
    LatencyHistogram latency;
    SinkOperator<double> sink("snk", &q2, [&latency](const Event<double>& ev) {
        latency.record(ev.latency_ns());
    });
    sink.attach_metrics(&m_snk);

    Runtime rt;
    rt.add_worker(cfg.source);
    rt.add_worker(cfg.compute);
    rt.add_worker(cfg.sink);

    rt.register_op(&source, 0);
    rt.register_op(&map, 1);
    rt.register_op(&sink, 2);
    
    rt.metrics().add(&m_snk);

    std::cout << "Running core_pinning experiment in mode: " << mode << "\n";
    rt.start();
    rt.wait_for(seconds(10));
    rt.stop();

    std::cout << "Throughput: " << m_snk.events_processed.load() / 10 << " ev/s\n";
    std::cout << "p50 latency: " << latency.percentile(0.5) << " us\n";
    std::cout << "p99 latency: " << latency.percentile(0.99) << " us\n";

    return 0;
}
