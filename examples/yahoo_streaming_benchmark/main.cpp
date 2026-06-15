// examples/yahoo_streaming_benchmark/main.cpp
#include "klstream/core/config.hpp"
#include "klstream/core/event.hpp"
#include "klstream/core/spsc_queue.hpp"
#include "klstream/core/metrics.hpp"
#include "klstream/core/runtime.hpp"
#include "klstream/operators/source.hpp"
#include "klstream/operators/filter.hpp"
#include "klstream/operators/map.hpp"
#include "klstream/operators/window.hpp"
#include "klstream/operators/sink.hpp"

#include <array>
#include <chrono>
#include <cstdint>
#include <iostream>
#include <random>
#include <string>
#include <unordered_map>

namespace ysb {

// ── YSB event types ───────────────────────────────────────────────────────
// The benchmark specifies these fields for each ad event.
struct AdEvent {
    uint32_t ad_id;
    uint32_t campaign_id;
    uint8_t  event_type;  // 0=view, 1=click, 2=purchase
};

// The aggregated result pushed to the sink.
struct CampaignResult {
    uint32_t campaign_id;
    uint64_t view_count;
};

// Simulate a campaign lookup table (replaces Kafka join in the original YSB).
// In the original benchmark this is a Redis lookup; we model it as a flat array.
static constexpr int N_CAMPAIGNS = 100;
static constexpr int ADS_PER_CAMPAIGN = 10;
static constexpr int N_ADS = N_CAMPAIGNS * ADS_PER_CAMPAIGN;

// campaign_table[ad_id] = campaign_id
static std::array<uint32_t, N_ADS> campaign_table;

void build_campaign_table() {
    for (int i = 0; i < N_ADS; ++i) {
        campaign_table[i] = i / ADS_PER_CAMPAIGN;
    }
}

} // namespace ysb

int main() {
    using namespace klstream;
    using namespace std::chrono;
    using namespace ysb;

    build_campaign_table();

    std::mt19937 rng(42);
    std::uniform_int_distribution<uint32_t> ad_dist(0, N_ADS - 1);
    std::uniform_int_distribution<uint8_t>  type_dist(0, 2);

    // ── Queues ────────────────────────────────────────────────────────────
    // YSB pipeline:
    //   Source<AdEvent> -> Filter<AdEvent> -> Map<AdEvent,CampaignResult>
    //     -> TumblingCountWindow<CampaignResult,CampaignResult>
    //     -> Sink<CampaignResult>
    SPSCQueue<Event<AdEvent>>         q_src_flt(4096);
    SPSCQueue<Event<AdEvent>>         q_flt_map(4096);
    SPSCQueue<Event<CampaignResult>>  q_map_win(4096);
    SPSCQueue<Event<CampaignResult>>  q_win_snk(4096);

    OperatorMetrics m_src("ysb_source");
    OperatorMetrics m_flt("view_filter");
    OperatorMetrics m_map("campaign_join");
    OperatorMetrics m_win("10sec_window");
    OperatorMetrics m_snk("ysb_sink");
    LatencyHistogram latency;
    std::atomic<uint64_t> total_out{0};

    // Source: generates random AdEvents
    SourceOperator<AdEvent> source(
        "ysb_source", &q_src_flt,
        [&rng, &ad_dist, &type_dist]
        (Event<AdEvent>& out, uint64_t seq) -> bool {
            out = Event<AdEvent>::make(
                AdEvent{ ad_dist(rng), 0, type_dist(rng) }, 0, seq);
            return true;
        });
    source.attach_metrics(&m_src);

    // Filter: keep only event_type == 0 (view events)
    FilterOperator<AdEvent> view_filter(
        "view_filter", &q_src_flt, &q_flt_map,
        [](const AdEvent& e) { return e.event_type == 0; });
    view_filter.attach_metrics(&m_flt);

    // Map (replaces the distributed join): look up campaign_id
    MapOperator<AdEvent, CampaignResult> join(
        "campaign_join", &q_flt_map, &q_map_win,
        [](const AdEvent& e) -> CampaignResult {
            return { campaign_table[e.ad_id], 1 };
        });
    join.attach_metrics(&m_map);

    // Window: count views per campaign over every 1000 events
    // (replaces the original 10-second tumbling window for benchmark clarity)
    TumblingCountWindow<CampaignResult, CampaignResult> win(
        "1k_window", &q_map_win, &q_win_snk, 1000,
        [](const std::vector<CampaignResult>& buf) -> CampaignResult {
            std::unordered_map<uint32_t, uint64_t> counts;
            for (const auto& r : buf) counts[r.campaign_id] += r.view_count;
            // Return the campaign with most views in this window.
            auto it = std::max_element(counts.begin(), counts.end(),
                [](const auto& a, const auto& b){ return a.second < b.second; });
            return { it->first, it->second };
        });
    win.attach_metrics(&m_win);

    // Sink
    SinkOperator<CampaignResult> sink(
        "ysb_sink", &q_win_snk,
        [&latency, &total_out](const Event<CampaignResult>& ev) {
            latency.record(ev.latency_ns());
            total_out.fetch_add(1, std::memory_order_relaxed);
        });
    sink.attach_metrics(&m_snk);

    // ── Runtime ───────────────────────────────────────────────────────────
    Runtime rt;
    rt.add_worker(CoreAffinity::Performance);  // 0: source + filter
    rt.add_worker(CoreAffinity::Performance);  // 1: join + window
    rt.add_worker(CoreAffinity::Efficiency);   // 2: sink

    rt.register_op(&source,      0);
    rt.register_op(&view_filter, 0);
    rt.register_op(&join,        1);
    rt.register_op(&win,         1);
    rt.register_op(&sink,        2);

    for (auto* m : {&m_src, &m_flt, &m_map, &m_win, &m_snk})
        rt.metrics().add(m);

    std::cout << "KLStream Yahoo Streaming Benchmark — 30 seconds\n";
    rt.start();
    rt.wait_for(seconds(30));
    rt.stop();

    std::cout
        << "Total window results: " << total_out.load() << "\n"
        << "p50 latency: " << latency.percentile(0.50) << " us\n"
        << "p99 latency: " << latency.percentile(0.99) << " us\n";

    return 0;
}
