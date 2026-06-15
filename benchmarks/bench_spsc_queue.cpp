// benchmarks/bench_spsc_queue.cpp
#include <benchmark/benchmark.h>
#include "klstream/core/spsc_queue.hpp"
#include "klstream/core/event.hpp"
#include <thread>

using namespace klstream;

// ── Raw throughput: how fast can one SPSC queue push+pop? ────────────────
// Expected on M3: 200–500 million events/sec (this is the upper bound for
// the entire runtime — no pipeline can be faster than its queues).
static void BM_SPSC_Throughput(benchmark::State& state) {
    SPSCQueue<Event<int>> q(static_cast<size_t>(state.range(0)));
    Event<int> ev = Event<int>::make(42);
    Event<int> out;
    auto producer = std::thread([&]{
        for (auto _ : state) {
            while (!q.try_push(ev)) {}  // blocks if full — this is the paired throughput test
        }
    });
    for (auto _ : state) {
        while (!q.try_pop(&out)) {}
    }
    producer.join();
    state.SetItemsProcessed(state.iterations());
}
BENCHMARK(BM_SPSC_Throughput)
    ->Arg(64)->Arg(256)->Arg(1024)->Arg(4096)->Arg(16384)
    ->UseRealTime()->ThreadRange(1, 1);

// ── Latency: round-trip time for one event through a SPSC queue ──────────
// (ping-pong between two threads)
static void BM_SPSC_RTT_Latency(benchmark::State& state) {
    SPSCQueue<Event<int>> q_fwd(256);
    SPSCQueue<Event<int>> q_bck(256);
    Event<int> ping = Event<int>::make(0);
    Event<int> pong;
    bool running = true;
    auto echo = std::thread([&]{
        Event<int> e;
        while (running) {
            if (q_fwd.try_pop(&e)) q_bck.try_push(e);
        }
    });
    for (auto _ : state) {
        while(!q_fwd.try_push(ping)) {}
        while (!q_bck.try_pop(&pong)) {}
    }
    running = false;
    echo.join();
    state.SetLabel("RTT ns per event");
}
BENCHMARK(BM_SPSC_RTT_Latency)->UseRealTime();

BENCHMARK_MAIN();
