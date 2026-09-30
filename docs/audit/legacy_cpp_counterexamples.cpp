// Test fixtures reproducing legacy defects. Compile only against legacy headers.
#include <klstream/klstream.hpp>
#include <atomic>
#include <iostream>

using namespace klstream;
struct DelayedMap : IOperator {
    SPSCQueue<Event<int>>& in; SPSCQueue<Event<int>>& out; std::atomic<bool>& released;
    DelayedMap(SPSCQueue<Event<int>>& a,SPSCQueue<Event<int>>& b,std::atomic<bool>& c) : IOperator("delayed"),in(a),out(b),released(c) {}
    void init() override { while (!released.load()) std::this_thread::yield(); }
    OpStatus tick() override { Event<int> e{}; if (!in.try_pop(e)) return OpStatus::Idle; (void)out.try_push(e); return OpStatus::Processed; }
};
struct EarlySink : IOperator {
    SPSCQueue<Event<int>>& in; std::atomic<bool>& released; int count=0;
    EarlySink(SPSCQueue<Event<int>>& a,std::atomic<bool>& c) : IOperator("sink"),in(a),released(c) {}
    OpStatus tick() override { Event<int> e{}; if (!in.try_pop(e)) return OpStatus::Idle; ++count; return OpStatus::Processed; }
    void shutdown() override { released.store(true); }
};
int main() {
    SPSCQueue<int> invalid(3); // Legacy release mode accepts an invalid capacity.
    TokenBucketRateLimiter bucket(10,1); int tokens=0; while (tokens<20 && bucket.try_consume_at(std::chrono::steady_clock::time_point{})) ++tokens;
    IsolationForest<1> forest(1,256,42); forest.fit({{0},{1}});
    SPSCQueue<Event<int>> in(4),out(4); (void)in.try_push(Event<int>::make(1)); std::atomic<bool> release{false};
    DelayedMap map(in,out,release); EarlySink sink(out,release); Runtime runtime;
    runtime.register_op(&map,runtime.add_worker()); runtime.register_op(&sink,runtime.add_worker()); runtime.start(); runtime.stop();
    std::cout << "{\"invalid_capacity_accepted\":" << invalid.capacity() << ",\"tokens_at_nonadvancing_clock_with_burst_one\":" << tokens
              << ",\"two_row_forest_score\":" << forest.anomaly_score({0}) << ",\"sink_received\":" << sink.count
              << ",\"output_remaining_after_stop\":" << out.size_approx() << "}\n";
}
