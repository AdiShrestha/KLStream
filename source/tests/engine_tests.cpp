#include <klstream/klstream.hpp>
#include <atomic>
#include <iostream>
#include <limits>
#include <vector>

using namespace klstream;
using namespace std::chrono_literals;
// Checks remain active under NDEBUG. All generated inputs are test fixtures.
#define CHECK(x) do { if (!(x)) throw std::runtime_error("Failed: " #x); } while (false)
template<class F> void rejects(F fn) { bool threw = false; try { fn(); } catch (const std::exception&) { threw = true; } CHECK(threw); }

void queue_contracts() {
    for (auto n : {0u, 1u, 3u, 7u}) {
        rejects([=] { SPSCQueue<int> q(n); });
        rejects([=] { MPMCQueue<int> q(n); });
    }
    SPSCQueue<int> s(4);
    CHECK(s.usable_capacity() == 3);
    for (int i = 0; i < 3; ++i) CHECK(s.try_push(i));
    CHECK(!s.try_push(3)); CHECK(s.occupancy() == 1);
    s.close(); CHECK(!s.try_push(4));
    int x = 0;
    for (int i = 0; i < 3; ++i) { CHECK(s.try_pop(x)); CHECK(x == i); }
    CHECK(s.is_drained()); CHECK(!s.pop(x));
    MPMCQueue<int> m(4);
    for (int i = 0; i < 4; ++i) CHECK(m.try_push(i));
    CHECK(!m.try_push(5)); CHECK(m.size_approx() == 4); CHECK(m.occupancy() == 1);
    CHECK(!m.try_pop(static_cast<int*>(nullptr)));
    m.close(); CHECK(!m.try_push(6));
    for (int i = 0; i < 4; ++i) { CHECK(m.try_pop(x)); CHECK(x == i); }
    CHECK(m.is_drained());
    SPSCQueue<int> blocked(2); CHECK(blocked.try_push(1));
    std::atomic<bool> returned{false};
    std::thread t([&] { returned = !blocked.push(2); });
    std::this_thread::sleep_for(2ms); blocked.stop(); t.join(); CHECK(returned);
}

void concurrent_queues() {
    constexpr int n = 40000;
    SPSCQueue<int> s(8);
    std::atomic<int> bad{0};
    std::thread p([&] { for (int i = 0; i < n; ++i) if (!s.push(i)) ++bad; s.close(); });
    std::thread c([&] { int x = -1; for (int i = 0; i < n; ++i) { if (!s.pop(x) || x != i) ++bad; } });
    p.join(); c.join(); CHECK(bad == 0);
    MPMCQueue<int> m(16);
    std::vector<std::atomic<int>> seen(n);
    for (auto& a : seen) a.store(0);
    std::vector<std::thread> producers, consumers;
    for (int id = 0; id < 4; ++id) producers.emplace_back([&,id] { for (int i = id; i < n; i += 4) if (!m.push(i)) ++bad; });
    for (int id = 0; id < 4; ++id) consumers.emplace_back([&] { int x; for (int i = 0; i < n/4; ++i) { if (!m.pop(x) || x < 0 || x >= n) ++bad; else ++seen[x]; } });
    for (auto& t : producers) t.join();
    for (auto& t : consumers) t.join();
    m.close(); CHECK(m.is_drained()); CHECK(bad == 0);
    for (auto& a : seen) CHECK(a == 1);
}

void runtime_completion(bool early) {
    SPSCQueue<Event<int>> input(4), output(4);
    std::atomic<int> generated{0}; std::vector<Event<int>> observed;
    SourceOperator<int> source("finite", &input, [&](Event<int>& e, std::uint64_t seq) {
        if (seq == 15000) return false;
        e = Event<int>::make(static_cast<int>(seq), 9, seq); ++generated; return true;
    });
    MapOperator<int,int> map("double", &input, &output, [](int x) { return x * 2; });
    SinkOperator<int> sink("collect", &output, [&](const Event<int>& e) { observed.push_back(e); if (e.seq % 200 == 0) std::this_thread::sleep_for(10us); });
    Runtime r;
    auto sink_worker = r.add_worker(), source_worker = r.add_worker(), map_worker = r.add_worker();
    r.register_op(&sink, sink_worker); r.register_op(&source, source_worker); r.register_op(&map, map_worker);
    rejects([&] { r.register_op(&map, sink_worker); });
    r.start(); rejects([&] { r.start(); });
    if (early) { std::this_thread::sleep_for(2ms); CHECK(r.drain(10s)); }
    else CHECK(r.wait_until_done(10s));
    CHECK(observed.size() == static_cast<std::size_t>(generated.load()));
    if (!early) CHECK(observed.size() == 15000);
    for (std::size_t i = 0; i < observed.size(); ++i) { CHECK(observed[i].seq == i); CHECK(observed[i].key == 9); CHECK(observed[i].data == static_cast<int>(i)*2); CHECK(observed[i].timestamp_ns > 0); }
    CHECK(input.is_drained()); CHECK(output.is_drained());
    r.stop(); r.stop(); CHECK(r.state() == RuntimeState::Stopped);
}

struct IdleOp : IOperator { IdleOp() : IOperator("idle") {} OpStatus tick() override { return OpStatus::Idle; } };
struct ThrowOp : IOperator {
    int& shutdowns;
    explicit ThrowOp(int& n) : IOperator("throw"), shutdowns(n) {}
    OpStatus tick() override { throw std::runtime_error("callback sentinel"); }
    void shutdown() override { ++shutdowns; }
};
void runtime_failure() {
    IdleOp direct_idle; WorkerThread direct;
    rejects([&] { direct.assign(nullptr); }); direct.assign(&direct_idle);
    rejects([&] { direct.assign(&direct_idle); }); direct.start();
    rejects([&] { direct.start(); }); rejects([&] { direct.assign(&direct_idle); });
    direct.cancel(); direct.join(); rejects([&] { direct.start(); });
    IdleOp idle; Runtime r; r.register_op(&idle, r.add_worker()); r.start();
    CHECK(!r.wait_until_done(2ms)); CHECK(!r.drain(2ms)); r.stop(); CHECK(!r.drain());
    int shutdowns = 0; ThrowOp op(shutdowns); Runtime failed; failed.register_op(&op, failed.add_worker()); failed.start();
    rejects([&] { failed.wait_until_done(1s); }); CHECK(shutdowns == 1); CHECK(failed.state() == RuntimeState::Failed);
    failed.stop(); CHECK(shutdowns == 1);
}

void operators_and_partial_batches() {
    SPSCQueue<Event<int>> input(8), output(2);
    for (int i = 0; i < 5; ++i) CHECK(input.try_push(Event<int>{static_cast<std::uint64_t>(100+i), 1, static_cast<std::uint64_t>(i), i}));
    input.close();
    TumblingCountWindow<int,int> window("sum", &input, &output, 3, [](const auto& b) { int sum = 0; for (const auto& e : b) sum += e.data; return sum; });
    std::vector<Event<int>> sums;
    for (int i = 0; i < 30; ++i) { const auto status = window.tick(); Event<int> e{}; if (output.try_pop(e)) sums.push_back(e); if (status == OpStatus::Finished) break; }
    CHECK(sums.size() == 2); CHECK(sums[0].data == 3); CHECK(sums[1].data == 7); CHECK(sums[0].timestamp_ns == 100); CHECK(sums[1].timestamp_ns == 103);
    SPSCQueue<Event<int>> in(8); using B = EventBatch<int,4>; SPSCQueue<B> out(2);
    for (int i = 0; i < 5; ++i) CHECK(in.try_push(Event<int>{static_cast<std::uint64_t>(10+i), 2, static_cast<std::uint64_t>(i), i}));
    in.close(); BatchOperator<int,4> batch("batch", &in, &out, [] { return 3; }, 1s);
    std::vector<Event<int>> points;
    for (int i = 0; i < 30; ++i) { auto status = batch.tick(); B b{}; if (out.try_pop(b)) for (std::size_t j=0; j<b.count; ++j) points.push_back(b.events[j]); if (status == OpStatus::Finished) break; }
    CHECK(points.size() == 5); for (std::size_t i=0; i<5; ++i) { CHECK(points[i].seq == i); CHECK(points[i].timestamp_ns == 10+i); }
    CHECK(out.is_drained());
    SPSCQueue<Event<int>> timed_in(4); SPSCQueue<B> timed_out(2);
    BatchOperator<int,4> timed("deadline", &timed_in, &timed_out, [] { return 4; }, 1ms);
    CHECK(timed_in.try_push(Event<int>::make(7))); CHECK(timed.tick() == OpStatus::Processed);
    std::this_thread::sleep_for(2ms); timed.tick(); timed.tick(); B b{}; CHECK(timed_out.try_pop(b)); CHECK(b.count == 1); CHECK(b.events[0].data == 7);
    rejects([&] { TumblingCountWindow<int,int> w("bad", &input, &output, 0, [](const auto&) { return 0; }); });
    // A blocked map applies the transform exactly once and retains metadata.
    SPSCQueue<Event<int>> mi(4), mo(2); int transforms = 0;
    CHECK(mo.try_push(Event<int>::make(99))); CHECK(mi.try_push(Event<int>{42,3,8,2}));
    MapOperator<int,int> map("map", &mi, &mo, [&](int x) { ++transforms; return x+1; });
    CHECK(map.tick() == OpStatus::Blocked); CHECK(map.tick() == OpStatus::Blocked); CHECK(transforms == 1);
    Event<int> e{}; CHECK(mo.try_pop(e)); CHECK(map.tick() == OpStatus::Processed); CHECK(mo.try_pop(e)); CHECK(e.timestamp_ns == 42); CHECK(e.seq == 8); CHECK(e.data == 3);
}

void math_and_configuration() {
    rejects([] { Event<int>{std::numeric_limits<std::uint64_t>::max(),0,0,1}.latency_ns(); });
    TokenBucketRateLimiter bucket(2, 1);
    CHECK(bucket.try_consume()); CHECK(!bucket.try_consume());
    bucket.throttle(.5); CHECK(bucket.rate() == 1); bucket.recover(); CHECK(bucket.rate() == 2);
    rejects([] { TokenBucketRateLimiter b(0); }); rejects([] { TokenBucketRateLimiter b(1, .5); });
    rejects([] { TokenBucketRateLimiter b(1, 1, 2); });
    TokenBucketRateLimiter slow(.1); CHECK(slow.try_consume()); CHECK(!slow.try_consume());
    OccupancyBatchController grow(1,16,4,1,.3,.7,.5,2,FeedbackDirection::GrowUnderPressure);
    CHECK(grow.update(.9) == 8); CHECK(grow.update(.5) == 8); CHECK(grow.update(.1) == 4);
    rejects([&] { grow.update(std::numeric_limits<double>::quiet_NaN()); });
    LatencyHistogram histogram; rejects([&] { histogram.p99(); });
    histogram.record(30000000); CHECK(std::isinf(histogram.p99())); CHECK(histogram.mean() == 30000);
    CHECK(IsolationForest<1>::c_factor(2) == 1);
    CHECK(std::abs(IsolationForest<1>::c_factor(3) - 5.0/3) < 1e-12);
    IsolationForest<1> forest(3,256,7); rejects([&] { forest.anomaly_score({0}); });
    forest.fit({{0},{1}}); CHECK(forest.subsample_size() == 2); CHECK(forest.c_psi() == 1); CHECK(forest.anomaly_score({0}) == .5);
    forest.fit({{2},{2},{2}}); CHECK(std::abs(forest.anomaly_score({2}) - .5) < 1e-12);
    rejects([&] { forest.fit({}); }); rejects([&] { forest.anomaly_score({std::numeric_limits<float>::infinity()}); });
    IsolationForest<32> one_feature(1,3,3); std::vector<IsolationForest<32>::Point> sparse(3); sparse[1][0] = 1; sparse[2][0] = 2;
    one_feature.fit(sparse); CHECK(one_feature.anomaly_score(sparse[0]) != one_feature.anomaly_score(sparse[2]) || one_feature.anomaly_score(sparse[1]) != one_feature.anomaly_score(sparse[2]));
}

int main() {
    try {
        queue_contracts(); concurrent_queues(); runtime_completion(false); runtime_completion(true);
        runtime_failure(); operators_and_partial_batches(); math_and_configuration();
        std::cout << "Foundation correctness checks passed; test fixtures only.\n";
    } catch (const std::exception& e) { std::cerr << e.what() << '\n'; return 1; }
}
