// examples/basic_pipeline/main.cpp
#include "klstream/core/config.hpp"
#include "klstream/core/event.hpp"
#include "klstream/core/spsc_queue.hpp"
#include "klstream/core/metrics.hpp"
#include "klstream/core/runtime.hpp"
#include "klstream/operators/source.hpp"
#include "klstream/operators/map.hpp"
#include "klstream/operators/filter.hpp"
#include "klstream/operators/aggregate.hpp"
#include "klstream/operators/sink.hpp"

#include <atomic>
#include <chrono>
#include <cstdint>
#include <iostream>

int main() {
    using namespace klstream;
    using namespace std::chrono;

    // ── Queues ────────────────────────────────────────────────────────────
    // Each queue is SPSC (one producer, one consumer).
    // Capacity: 4096 events (the DEFAULT_QUEUE_CAPACITY constant).
    // Changing this to 64 or 16384 is a one-argument change — experiment here.
    SPSCQueue<Event<uint64_t>> q_src_map(4096);   // source  → map
    SPSCQueue<Event<uint64_t>> q_map_flt(4096);   // map     → filter
    SPSCQueue<Event<uint64_t>> q_flt_agg(4096);   // filter  → aggregate
    SPSCQueue<Event<uint64_t>> q_agg_snk(4096);   // aggregate → sink

    // ── Metrics ───────────────────────────────────────────────────────────
    OperatorMetrics m_src("source");
    OperatorMetrics m_map("square_map");
    OperatorMetrics m_flt("even_filter");
    OperatorMetrics m_agg("running_sum");
    OperatorMetrics m_snk("sink");
    LatencyHistogram latency_hist;

    // ── Operators ─────────────────────────────────────────────────────────
    std::atomic<uint64_t> global_seq{0};

    // Source: generates integers 0, 1, 2, 3, ... (unlimited)
    SourceOperator<uint64_t> source(
        "source", &q_src_map,
        [&global_seq](Event<uint64_t>& out, uint64_t /*seq*/) -> bool {
            out = Event<uint64_t>::make(global_seq.fetch_add(1));
            return true;
        });
    source.attach_metrics(&m_src);
    // Optional rate cap: uncomment to limit to 1,000,000 events/sec
    // source.enable_rate_limiting(1'000'000.0);

    // Map: square each value
    MapOperator<uint64_t, uint64_t> squarer(
        "square_map", &q_src_map, &q_map_flt,
        [](uint64_t x) -> uint64_t { return x * x; });
    squarer.attach_metrics(&m_map);

    // Filter: keep only even-squared values (i.e., even x, since odd^2 is odd)
    FilterOperator<uint64_t> even_filter(
        "even_filter", &q_map_flt, &q_flt_agg,
        [](uint64_t x) -> bool { return (x % 2 == 0); });
    even_filter.attach_metrics(&m_flt);

    // Aggregate: running sum of all even-squared values
    AggregateOperator<uint64_t, uint64_t, uint64_t> summer(
        "running_sum", &q_flt_agg, &q_agg_snk,
        0ULL,
        [](uint64_t& st, const uint64_t& x) { st += x; },
        [](const uint64_t& st) { return st; });
    summer.attach_metrics(&m_agg);

    // Sink: record latency and count events
    SinkOperator<uint64_t> sink(
        "sink", &q_agg_snk,
        [&latency_hist](const Event<uint64_t>& ev) {
            latency_hist.record(ev.latency_ns());
        });
    sink.attach_metrics(&m_snk);

    // ── Runtime ───────────────────────────────────────────────────────────
    // Four workers:
    //   Worker 0 (P-core): runs source + squarer  (generation + transform)
    //   Worker 1 (P-core): runs even_filter       (selective pass-through)
    //   Worker 2 (P-core): runs running_sum        (stateful accumulation)
    //   Worker 3 (E-core): runs sink               (lightweight I/O)
    Runtime rt;
    rt.add_worker(CoreAffinity::Performance);  // Worker 0
    rt.add_worker(CoreAffinity::Performance);  // Worker 1
    rt.add_worker(CoreAffinity::Performance);  // Worker 2
    rt.add_worker(CoreAffinity::Efficiency);   // Worker 3

    rt.register_op(&source,      0, CoreAffinity::Performance);
    rt.register_op(&squarer,     0, CoreAffinity::Performance);
    rt.register_op(&even_filter, 1, CoreAffinity::Performance);
    rt.register_op(&summer,      2, CoreAffinity::Performance);
    rt.register_op(&sink,        3, CoreAffinity::Efficiency);

    rt.metrics().add(&m_src);
    rt.metrics().add(&m_map);
    rt.metrics().add(&m_flt);
    rt.metrics().add(&m_agg);
    rt.metrics().add(&m_snk);

    // ── Run for 10 seconds ────────────────────────────────────────────────
    std::cout << "KLStream basic_pipeline running for 10 seconds...\n";
    rt.start();
    rt.wait_for(seconds(10));
    rt.stop();

    // ── Print final latency percentiles ───────────────────────────────────
    std::cout << "\nLatency percentiles (end-to-end, microseconds):\n"
              << "  p50:  " << latency_hist.percentile(0.50) << " us\n"
              << "  p99:  " << latency_hist.percentile(0.99) << " us\n"
              << "  p999: " << latency_hist.percentile(0.999) << " us\n";

    return 0;
}
