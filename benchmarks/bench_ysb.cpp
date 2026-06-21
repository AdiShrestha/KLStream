#include <benchmark/benchmark.h>
#include "klstream/core/runtime.hpp"
#include "klstream/operators/source.hpp"
#include "klstream/operators/map.hpp"
#include "klstream/operators/filter.hpp"
#include "klstream/operators/window.hpp"
#include "klstream/operators/sink.hpp"
#include <atomic>
#include <random>

using namespace klstream;
using namespace std::chrono;

struct AdEvent {
    uint32_t ad_id;
    uint32_t campaign_id;
    uint8_t  event_type;
};

struct CampaignResult {
    uint32_t campaign_id;
    uint64_t view_count;
};

static constexpr int N_CAMPAIGNS = 100;
static constexpr int ADS_PER_CAMPAIGN = 10;
static constexpr int N_ADS = N_CAMPAIGNS * ADS_PER_CAMPAIGN;
static std::array<uint32_t, N_ADS> campaign_table;

static void build_campaign_table() {
    for (int i = 0; i < N_ADS; ++i) {
        campaign_table[i] = i / ADS_PER_CAMPAIGN;
    }
}

static void BM_YSBThroughput(benchmark::State& state) {
    build_campaign_table();
    std::mt19937 rng(42);
    std::uniform_int_distribution<uint32_t> ad_dist(0, N_ADS - 1);
    std::uniform_int_distribution<uint8_t>  type_dist(0, 2);
    
    for (auto _ : state) {
        SPSCQueue<Event<AdEvent>>         q1(16384);
        SPSCQueue<Event<AdEvent>>         q2(16384);
        SPSCQueue<Event<CampaignResult>>  q3(16384);
        SPSCQueue<Event<CampaignResult>>  q4(16384);
        
        SourceOperator<AdEvent> source("src", &q1, [&](Event<AdEvent>& out, uint64_t seq) {
            out = Event<AdEvent>::make(AdEvent{ ad_dist(rng), 0, type_dist(rng) }, 0, seq); return true;
        });
        FilterOperator<AdEvent> filter("flt", &q1, &q2, [](const AdEvent& e){ return e.event_type == 0; });
        MapOperator<AdEvent, CampaignResult> map("map", &q2, &q3, [](const AdEvent& e) -> CampaignResult {
            return { campaign_table[e.ad_id], 1 };
        });
        TumblingCountWindow<CampaignResult, CampaignResult> win("win", &q3, &q4, 1000, [](const std::vector<Event<CampaignResult>>& buf) -> CampaignResult {
            std::unordered_map<uint32_t, uint64_t> counts;
            for (const auto& r : buf) counts[r.data.campaign_id] += r.data.view_count;
            auto it = std::max_element(counts.begin(), counts.end(), [](const auto& a, const auto& b){ return a.second < b.second; });
            return { it->first, it->second };
        });
        std::atomic<uint64_t> count{0};
        SinkOperator<CampaignResult> sink("snk", &q4, [&count](const Event<CampaignResult>&){ count++; });
        
        Runtime rt;
        for(int i=0; i<4; ++i) rt.add_worker();
        rt.register_op(&source, 0);
        rt.register_op(&filter, 0);
        rt.register_op(&map, 1);
        rt.register_op(&win, 2);
        rt.register_op(&sink, 3);
        
        auto start = high_resolution_clock::now();
        rt.start();
        rt.wait_for(seconds(2));
        rt.stop();
        auto end = high_resolution_clock::now();
        
        state.SetItemsProcessed(count.load() * 1000); // Because window emits 1 result per 1000 items
        state.SetIterationTime(duration_cast<duration<double>>(end - start).count());
    }
}
BENCHMARK(BM_YSBThroughput)->UseManualTime();
