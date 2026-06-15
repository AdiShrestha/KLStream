// research/adaptive_backpressure/main.cpp
#include "klstream/core/runtime.hpp"
#include "klstream/operators/source.hpp"
#include "klstream/operators/sink.hpp"
#include <iostream>
#include <string>
#include <atomic>
#include <thread>
#include <chrono>

using namespace klstream;
using namespace std::chrono;

int main(int argc, char* argv[]) {
    std::string mode = "baseline";
    int qsize = 1024;
    std::string burst = "medium";
    int duration_sec = 5;

    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg.find("--mode=") == 0) mode = arg.substr(7);
        else if (arg.find("--queue_size=") == 0) qsize = std::stoi(arg.substr(13));
        else if (arg.find("--burst_level=") == 0) burst = arg.substr(14);
        else if (arg.find("--duration=") == 0) duration_sec = std::stoi(arg.substr(11));
    }

    SPSCQueue<Event<uint64_t>> q_src_snk(qsize);
    OperatorMetrics m_src("src");
    OperatorMetrics m_snk("snk");
    LatencyHistogram latency;

    std::atomic<bool> in_burst{false};
    
    SourceOperator<uint64_t> source("src", &q_src_snk, [&in_burst](Event<uint64_t>& out, uint64_t seq) {
        if (!in_burst.load(std::memory_order_relaxed)) {
            std::this_thread::sleep_for(std::chrono::microseconds(100)); // ~10k/sec
        }
        out = Event<uint64_t>::make(seq, 0, seq);
        return true;
    });
    source.attach_metrics(&m_src);
    
    if (mode == "adaptive") {
        source.enable_rate_limiting(1'000'000.0); // 1M/sec max rate
    }

    SinkOperator<uint64_t> sink("snk", &q_src_snk, [&latency](const Event<uint64_t>& ev) {
        latency.record(ev.latency_ns());
        // simulate slow consumer (bottleneck)
        std::this_thread::sleep_for(std::chrono::nanoseconds(500));
    });
    sink.attach_metrics(&m_snk);

    Runtime rt;
    rt.add_worker(CoreAffinity::Performance);
    rt.add_worker(CoreAffinity::Efficiency);
    rt.register_op(&source, 0);
    rt.register_op(&sink, 1);
    
    rt.metrics().add(&m_src);
    rt.metrics().add(&m_snk);

    // Burst toggler thread
    std::atomic<bool> running{true};
    std::thread burst_thread([&]() {
        int burst_ms = burst == "high" ? 400 : (burst == "medium" ? 200 : 50);
        int quiet_ms = 1000 - burst_ms;
        while (running) {
            in_burst = true;
            std::this_thread::sleep_for(milliseconds(burst_ms));
            in_burst = false;
            std::this_thread::sleep_for(milliseconds(quiet_ms));
        }
    });

    rt.start();
    rt.wait_for(seconds(duration_sec));
    rt.stop();
    
    running = false;
    burst_thread.join();

    std::cout << "Mode: " << mode << ", QSize: " << qsize << ", Burst: " << burst << "\n";
    std::cout << "Throughput: " << m_snk.events_processed.load() / duration_sec << " ev/s\n";
    std::cout << "Blocked/sec: " << m_src.events_blocked.load() / duration_sec << "\n";
    std::cout << "p50 latency: " << latency.percentile(0.5) << " us\n";
    std::cout << "p99 latency: " << latency.percentile(0.99) << " us\n";
    std::cout << "p999 latency: " << latency.percentile(0.999) << " us\n";

    return 0;
}
