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

void second_audit_regressions() {
    // Cancellation cannot be counted as a complete finite stream.
    SPSCQueue<Event<int>> cancelled(2); cancelled.stop(); cancelled.close();
    CHECK(cancelled.is_cancelled()); CHECK(!cancelled.is_drained());
    SinkOperator<int> sink("cancelled", &cancelled, [](const auto&) {});
    Runtime r; r.register_op(&sink, r.add_worker()); r.start();
    rejects([&] { r.wait_until_done(1s); }); CHECK(r.state() == RuntimeState::Failed);
    MPMCQueue<int> m(2); m.stop(); m.close(); CHECK(m.is_cancelled()); CHECK(!m.is_drained());
    SPSCQueue<Event<int>> in(2), out(2); out.close();
    MapOperator<int,int> map("closed", &in, &out, [](int x) { return x; });
    rejects([&] { map.tick(); });
    // Source assigns identity even when the callback uses the default Event::make.
    SPSCQueue<Event<int>> generated(4);
    SourceOperator<int> source("ids", &generated, [](auto& e, auto seq) { e = Event<int>::make(1); return seq < 3; });
    for (int i=0;i<3;++i) CHECK(source.tick()==OpStatus::Processed);
    CHECK(source.tick()==OpStatus::Finished);
    for (std::uint64_t i=0;i<3;++i) { Event<int> e{}; CHECK(generated.try_pop(e)); CHECK(e.seq==i); }
    SPSCQueue<Event<int>> delayed_in(2); SPSCQueue<EventBatch<int,4>> delayed_out(2);
    BatchOperator<int,4> delayed("controller_cost", &delayed_in, &delayed_out,
        [] { std::this_thread::sleep_for(10ms); return 4; }, 1ms);
    CHECK(delayed_in.try_push(Event<int>::make(1))); CHECK(delayed.tick()==OpStatus::Processed);
    CHECK(delayed.tick()==OpStatus::Processed); CHECK(delayed.tick()==OpStatus::Processed);
    EventBatch<int,4> partial{}; CHECK(delayed_out.try_pop(partial)); CHECK(partial.count==1);
    // Rate transition credits the preceding second at 10/s, then the next at 1/s.
    const auto t0 = TokenBucketRateLimiter::Clock::time_point{};
    TokenBucketRateLimiter bucket(10,100,1,t0);
    for (int i=0;i<100;++i) CHECK(bucket.try_consume_at(t0));
    CHECK(!bucket.try_consume_at(t0)); bucket.set_rate_at(1,t0+1s);
    for (int i=0;i<10;++i) CHECK(bucket.try_consume_at(t0+1s));
    CHECK(!bucket.try_consume_at(t0+1s)); CHECK(bucket.try_consume_at(t0+2s));
    CHECK(!bucket.try_consume_at(t0+2s)); rejects([&] { bucket.try_consume_at(t0); });
    rejects([&] { bucket.set_rate(-1); }); rejects([&] { bucket.throttle(1.1); });
    TokenBucketRateLimiter live(1000,100,1);
    std::thread adjust([&] { for (int i=0;i<2000;++i) { live.throttle(.5); live.recover(); } });
    for (int i=0;i<2000;++i) (void)live.try_consume(); adjust.join();
    struct FakeQueue { double value; double occupancy() const { return value; } } fake{.9};
    EMAOccupancyTracker<FakeQueue> ema(fake); ema.update(); CHECK(ema.ema()==.9); CHECK(ema.soft_pressure());
    fake.value=0; CHECK(ema.raw()==.9); ema.reset(); ema.update(); CHECK(ema.ema()==0);
    fake.value=std::numeric_limits<double>::quiet_NaN(); rejects([&] { ema.update(); });
    LatencyHistogram h; for (std::uint64_t i=0;i<100;++i) h.record(i*1000);
    CHECK(h.percentile(.07)==6); CHECK(h.percentile(7,100)==6);
    CHECK(h.p50()==49); CHECK(h.p95()==94); CHECK(h.p99()==98);
    Counter counter; counter.increment(std::numeric_limits<std::uint64_t>::max()); rejects([&] { counter.increment(); });
    IdleOp idle; Runtime timeout; timeout.register_op(&idle,timeout.add_worker()); timeout.start();
    rejects([&] { timeout.drain(-1ms); }); CHECK(timeout.state()==RuntimeState::Running); timeout.stop();
    // Adjacent float endpoints and huge finite ranges must fit/score without a
    // rounded empty split; repeated fitting with the same seed is deterministic.
    IsolationForest<1> forest(20,8,3);
    std::vector<IsolationForest<1>::Point> training{{0},{std::nextafter(0.0f,1.0f)}, {1}, {2}, {3}, {4}, {5}, {6}};
    forest.fit(training); const auto score=forest.anomaly_score({3});
    CHECK(std::isfinite(score) && score>0 && score<=1); forest.fit(training); CHECK(forest.anomaly_score({3})==score);
    forest.fit({{-std::numeric_limits<float>::max()},{std::numeric_limits<float>::max()}});
    CHECK(forest.anomaly_score({0})==.5);
}

void test_tiny_queues_contention() {
    // SPSC tiny queue: capacity 2 has usable capacity 1.
    {
        SPSCQueue<int> s(2);
        CHECK(s.usable_capacity() == 1);
        constexpr int N = 10000;
        std::atomic<int> errors{0};
        std::thread prod([&] {
            for (int i = 0; i < N; ++i) {
                if (!s.push(i)) ++errors;
            }
            s.close();
        });
        std::thread cons([&] {
            for (int i = 0; i < N; ++i) {
                int val = -1;
                if (!s.pop(val) || val != i) ++errors;
            }
        });
        prod.join();
        cons.join();
        CHECK(errors == 0);
        CHECK(s.is_drained());
        CHECK(s.state() == QueueState::Drained);
    }

    // MPMC tiny queue: capacity 2 has 2 usable slots under multi-threaded contention.
    {
        MPMCQueue<int> m(2);
        CHECK(m.capacity() == 2);
        constexpr int num_producers = 4;
        constexpr int num_consumers = 4;
        constexpr int items_per_prod = 5000;
        constexpr int total_items = num_producers * items_per_prod;

        std::vector<std::atomic<int>> counts(total_items);
        for (auto& c : counts) c.store(0);
        std::atomic<int> errors{0};
        std::atomic<bool> monitor_stop{false};
        std::atomic<int> bounds_violations{0};

        // Concurrent monitor thread verifying slot boundedness: 0 <= occupancy <= C and 0.0 <= occ <= 1.0
        std::thread monitor([&] {
            while (!monitor_stop.load(std::memory_order_relaxed)) {
                std::size_t sz = m.size_approx();
                double occ = m.occupancy();
                if (sz > 2 || occ < 0.0 || occ > 1.0) {
                    ++bounds_violations;
                }
                std::this_thread::yield();
            }
        });

        std::vector<std::thread> producers;
        for (int p = 0; p < num_producers; ++p) {
            producers.emplace_back([&, p] {
                int start = p * items_per_prod;
                int end = start + items_per_prod;
                for (int i = start; i < end; ++i) {
                    if (!m.push(i)) ++errors;
                }
            });
        }

        std::vector<std::thread> consumers;
        for (int c = 0; c < num_consumers; ++c) {
            consumers.emplace_back([&] {
                for (int i = 0; i < items_per_prod; ++i) {
                    int val = -1;
                    if (!m.pop(val)) {
                        ++errors;
                    } else if (val < 0 || val >= total_items) {
                        ++errors;
                    } else {
                        ++counts[val];
                    }
                }
            });
        }

        for (auto& t : producers) t.join();
        for (auto& t : consumers) t.join();
        monitor_stop.store(true);
        monitor.join();

        m.close();
        CHECK(errors == 0);
        CHECK(bounds_violations == 0);
        CHECK(m.is_drained());
        CHECK(m.state() == QueueState::Drained);
        for (int i = 0; i < total_items; ++i) {
            CHECK(counts[i].load() == 1);
        }
    }
}

void test_blocking_and_waking() {
    // Full-queue producer blocking, then unblocked by consumer pop.
    {
        MPMCQueue<int> m(2);
        CHECK(m.push(11));
        CHECK(m.push(22));
        CHECK(!m.try_push(33)); // Full

        std::atomic<bool> producer_started{false};
        std::atomic<bool> producer_finished{false};
        std::thread p([&] {
            producer_started = true;
            bool ok = m.push(33);
            if (ok) producer_finished = true;
        });

        while (!producer_started.load()) std::this_thread::yield();
        std::this_thread::sleep_for(10ms);
        CHECK(!producer_finished.load()); // Producer must be blocked

        int val = 0;
        CHECK(m.pop(val));
        CHECK(val == 11);

        p.join();
        CHECK(producer_finished.load());

        CHECK(m.pop(val));
        CHECK(val == 22);
        CHECK(m.pop(val));
        CHECK(val == 33);
        CHECK(m.empty());
    }

    // Empty-queue consumer waiting, then unblocked by producer push.
    {
        MPMCQueue<int> m(2);
        std::atomic<bool> consumer_started{false};
        std::atomic<bool> consumer_finished{false};
        std::atomic<int> received{0};

        std::thread c([&] {
            consumer_started = true;
            int val = 0;
            if (m.pop(val)) {
                received = val;
                consumer_finished = true;
            }
        });

        while (!consumer_started.load()) std::this_thread::yield();
        std::this_thread::sleep_for(10ms);
        CHECK(!consumer_finished.load()); // Consumer must be waiting

        CHECK(m.push(777));
        c.join();
        CHECK(consumer_finished.load());
        CHECK(received.load() == 777);
    }
}

void test_injected_cancellation() {
    // 1. Cancellation wakes blocked producer on full queue.
    {
        MPMCQueue<int> m(2);
        CHECK(m.push(1));
        CHECK(m.push(2));
        std::atomic<bool> p_done{false};
        std::atomic<bool> p_ok{true};

        std::thread p([&] {
            p_ok = m.push(3);
            p_done = true;
        });

        std::this_thread::sleep_for(5ms);
        CHECK(!p_done.load());
        m.stop();
        p.join();
        CHECK(p_done.load());
        CHECK(!p_ok.load()); // push returned false on cancellation
    }

    // 2. Cancellation wakes waiting consumer on empty queue.
    {
        MPMCQueue<int> m(2);
        std::atomic<bool> c_done{false};
        std::atomic<bool> c_ok{true};
        int val = 0;

        std::thread c([&] {
            c_ok = m.pop(val);
            c_done = true;
        });

        std::this_thread::sleep_for(5ms);
        CHECK(!c_done.load());
        m.stop();
        c.join();
        CHECK(c_done.load());
        CHECK(!c_ok.load()); // pop returned false on cancellation
    }

    // 3. Injected cancellation under active multi-threaded contention.
    {
        MPMCQueue<int> m(2);
        std::atomic<bool> active{true};
        constexpr int P = 4, C = 4;
        std::vector<std::thread> threads;

        for (int i = 0; i < P; ++i) {
            threads.emplace_back([&, i] {
                int item = i * 1000000;
                while (active.load(std::memory_order_relaxed)) {
                    m.push(item++);
                }
            });
        }
        for (int i = 0; i < C; ++i) {
            threads.emplace_back([&] {
                int val = 0;
                while (active.load(std::memory_order_relaxed)) {
                    m.pop(val);
                }
            });
        }

        std::this_thread::sleep_for(15ms);
        m.stop(); // Inject cancellation while threads are actively pushing/pulling
        active.store(false);

        // Threads must join cleanly without deadlocks
        for (auto& t : threads) {
            t.join();
        }

        // Cancellation invariants
        CHECK(m.is_cancelled());
        CHECK(!m.is_drained());
        CHECK(m.state() == QueueState::Cancelled);
        CHECK(!m.is_running());

        // Close after cancellation must NOT overwrite Cancelled state
        m.close();
        CHECK(m.is_cancelled());
        CHECK(!m.is_drained());
        CHECK(m.state() == QueueState::Cancelled);

        // Consumers must fail closed: try_pop and pop must immediately fail
        int dummy = -1;
        CHECK(!m.try_pop(dummy));
        CHECK(!m.pop(dummy));
        CHECK(!m.try_push(42));
        CHECK(!m.push(42));
        CHECK(!m.is_drained());

        // Slot bounds remain strictly valid
        CHECK(m.occupancy() >= 0.0 && m.occupancy() <= 1.0);
        CHECK(m.size_approx() <= 2);
    }
}

void test_queue_state_invariants() {
    // Test SPSC state transitions
    {
        SPSCQueue<int> s(4);
        CHECK(s.state() == QueueState::Open);
        CHECK(!s.is_drained());
        CHECK(!s.is_cancelled());
        CHECK(s.is_running());

        CHECK(s.push(10));
        CHECK(s.state() == QueueState::Open);

        s.close();
        CHECK(s.state() == QueueState::Closed);
        CHECK(!s.is_drained());
        CHECK(!s.is_cancelled());
        CHECK(!s.is_running());

        // Repeated close is idempotent
        s.close();
        CHECK(s.state() == QueueState::Closed);

        int out = 0;
        CHECK(s.pop(out));
        CHECK(out == 10);

        // Queue is now empty and was closed -> Drained!
        CHECK(s.empty());
        CHECK(s.state() == QueueState::Drained);
        CHECK(s.is_drained());
        CHECK(!s.is_cancelled());

        // Stop after drained -> Cancelled!
        s.stop();
        CHECK(s.state() == QueueState::Cancelled);
        CHECK(!s.is_drained());
        CHECK(s.is_cancelled());

        // Close after stop must not overwrite Cancelled
        s.close();
        CHECK(s.state() == QueueState::Cancelled);
        CHECK(!s.is_drained());
    }

    // Test SPSC cancellation with remaining items: fail closed
    {
        SPSCQueue<int> s(4);
        CHECK(s.push(1));
        CHECK(s.push(2));
        s.stop();

        CHECK(s.state() == QueueState::Cancelled);
        CHECK(!s.is_drained());
        CHECK(s.is_cancelled());

        // Consumers must fail closed immediately
        int out = 0;
        CHECK(!s.try_pop(out));
        CHECK(!s.pop(out));
        CHECK(!s.try_push(3));
        CHECK(!s.push(3));

        // Close must not overwrite Cancelled
        s.close();
        CHECK(s.state() == QueueState::Cancelled);
        CHECK(!s.is_drained());
    }

    // Test MPMC state transitions
    {
        MPMCQueue<int> m(4);
        CHECK(m.state() == QueueState::Open);
        CHECK(m.push(100));
        m.close();
        CHECK(m.state() == QueueState::Closed);
        CHECK(!m.is_drained());

        int out = 0;
        CHECK(m.pop(out));
        CHECK(out == 100);

        CHECK(m.empty());
        CHECK(m.state() == QueueState::Drained);
        CHECK(m.is_drained());

        m.stop();
        CHECK(m.state() == QueueState::Cancelled);
        CHECK(!m.is_drained());

        m.close();
        CHECK(m.state() == QueueState::Cancelled);
        CHECK(!m.is_drained());
    }

    // Test MPMC cancellation with remaining items: fail closed
    {
        MPMCQueue<int> m(4);
        CHECK(m.push(1));
        CHECK(m.push(2));
        m.stop();

        CHECK(m.state() == QueueState::Cancelled);
        CHECK(!m.is_drained());

        int out = 0;
        CHECK(!m.try_pop(out));
        CHECK(!m.pop(out));
        CHECK(!m.try_push(3));
        CHECK(!m.push(3));

        m.close();
        CHECK(m.state() == QueueState::Cancelled);
        CHECK(!m.is_drained());
    }
}

void test_batch_and_window_cancellation() {
    // BatchOperator: flush on EOS vs abort on Cancellation
    {
        // 1. Flush on EOS
        SPSCQueue<Event<int>> in(8);
        SPSCQueue<EventBatch<int, 4>> out(4);
        BatchOperator<int, 4> batch_op("batch_eos", &in, &out, [] { return 4; }, 1s);

        CHECK(in.try_push(Event<int>::make(10)));
        CHECK(in.try_push(Event<int>::make(20)));
        CHECK(batch_op.tick() == OpStatus::Processed);
        CHECK(batch_op.tick() == OpStatus::Processed);

        // Normal EOS: close input
        in.close();
        CHECK(batch_op.tick() == OpStatus::Processed); // Marks partial batch as pending
        CHECK(batch_op.tick() == OpStatus::Processed); // Pushes pending batch to output
        EventBatch<int, 4> b{};
        CHECK(out.try_pop(b));
        CHECK(b.count == 2);
        CHECK(b.events[0].data == 10);
        CHECK(b.events[1].data == 20);
        CHECK(batch_op.tick() == OpStatus::Finished);
        CHECK(batch_op.dropped_count() == 0);
        CHECK(batch_op.aborted_count() == 0);
        CHECK(out.is_drained());
    }
    {
        // 2. Abort on Cancellation
        SPSCQueue<Event<int>> in(8);
        SPSCQueue<EventBatch<int, 4>> out(4);
        BatchOperator<int, 4> batch_op("batch_cancel", &in, &out, [] { return 4; }, 1s);

        CHECK(in.try_push(Event<int>::make(10)));
        CHECK(in.try_push(Event<int>::make(20)));
        CHECK(batch_op.tick() == OpStatus::Processed);
        CHECK(batch_op.tick() == OpStatus::Processed);

        // Cancellation injected on input
        in.stop();
        rejects([&] { batch_op.tick(); });
        CHECK(batch_op.dropped_count() == 2);
        CHECK(batch_op.aborted_count() == 2);

        // Output must not have received the aborted batch
        EventBatch<int, 4> b{};
        CHECK(!out.try_pop(b));
        CHECK(!out.is_drained());
    }

    // TumblingCountWindow: flush on EOS vs abort on Cancellation
    {
        // 1. Flush on EOS
        SPSCQueue<Event<int>> in(8);
        SPSCQueue<Event<int>> out(4);
        TumblingCountWindow<int, int> win("win_eos", &in, &out, 3, [](const auto& vec) {
            int sum = 0;
            for (const auto& e : vec) sum += e.data;
            return sum;
        });

        CHECK(in.try_push(Event<int>::make(1)));
        CHECK(in.try_push(Event<int>::make(2)));
        CHECK(win.tick() == OpStatus::Processed);
        CHECK(win.tick() == OpStatus::Processed);

        in.close();
        CHECK(win.tick() == OpStatus::Processed); // Emits partial window
        CHECK(win.tick() == OpStatus::Processed); // Pushes pending event
        Event<int> res{};
        CHECK(out.try_pop(res));
        CHECK(res.data == 3);
        CHECK(win.tick() == OpStatus::Finished);
        CHECK(win.dropped_count() == 0);
        CHECK(win.aborted_count() == 0);
        CHECK(out.is_drained());
    }
    {
        // 2. Abort on Cancellation
        SPSCQueue<Event<int>> in(8);
        SPSCQueue<Event<int>> out(4);
        TumblingCountWindow<int, int> win("win_cancel", &in, &out, 3, [](const auto& vec) {
            int sum = 0;
            for (const auto& e : vec) sum += e.data;
            return sum;
        });

        CHECK(in.try_push(Event<int>::make(1)));
        CHECK(in.try_push(Event<int>::make(2)));
        CHECK(win.tick() == OpStatus::Processed);
        CHECK(win.tick() == OpStatus::Processed);

        in.stop();
        rejects([&] { win.tick(); });
        CHECK(win.dropped_count() == 2);
        CHECK(win.aborted_count() == 2);

        Event<int> res{};
        CHECK(!out.try_pop(res));
        CHECK(!out.is_drained());
    }
}

void test_token_bucket_and_bounds() {
    const auto t0 = TokenBucketRateLimiter::Clock::time_point{};

    // Clock monotonicity rejection: negative delta t
    {
        TokenBucketRateLimiter b(10, 10, 1, t0);
        CHECK(b.try_consume_at(t0));
        // Moving backward in time throws domain_error
        rejects([&] { b.try_consume_at(t0 - 1s); });
        rejects([&] { b.set_rate_at(5, t0 - 1s); });
    }

    // Rate refill monotonic credit calculation before adjustment
    {
        TokenBucketRateLimiter b(10, 20, 1, t0);
        for (int i = 0; i < 20; ++i) CHECK(b.try_consume_at(t0));
        CHECK(!b.try_consume_at(t0)); // 0 tokens

        // At t0 + 1s, refill adds 10 tokens (rate=10), then rate changes to 2
        b.set_rate_at(2, t0 + 1s);
        // We should now have 10 tokens from the first second
        for (int i = 0; i < 10; ++i) CHECK(b.try_consume_at(t0 + 1s));
        CHECK(!b.try_consume_at(t0 + 1s)); // exhausted

        // Next second (t0 + 2s), rate is 2, so 2 tokens refilled
        CHECK(b.try_consume_at(t0 + 2s));
        CHECK(b.try_consume_at(t0 + 2s));
        CHECK(!b.try_consume_at(t0 + 2s));
    }

    // Parameter rejection
    rejects([] { TokenBucketRateLimiter b(-1); });
    rejects([] { TokenBucketRateLimiter b(10, -5); });
    rejects([] { TokenBucketRateLimiter b(10, 5, -1); });
    rejects([] { TokenBucketRateLimiter b(10, 5, 15); }); // floor > rate
    rejects([] { TokenBucketRateLimiter b(std::numeric_limits<double>::infinity()); });
    rejects([] { TokenBucketRateLimiter b(std::numeric_limits<double>::quiet_NaN()); });
}

void test_operator_parameter_validation() {
    SPSCQueue<Event<int>> in(4), out(4);
    SPSCQueue<EventBatch<int, 4>> batch_out(4);

    // Negative timeouts in Runtime
    {
        Runtime r;
        rejects([&] { r.wait_until_done(-1ms); });
        rejects([&] { r.drain(-5ms); });
    }

    // BatchOperator null and invalid parameters
    rejects([&] { BatchOperator<int, 4>("b", nullptr, &batch_out, [] { return 2; }, 1ms); });
    rejects([&] { BatchOperator<int, 4>("b", &in, nullptr, [] { return 2; }, 1ms); });
    rejects([&] { BatchOperator<int, 4>("b", &in, &batch_out, nullptr, 1ms); });
    rejects([&] { BatchOperator<int, 4>("b", &in, &batch_out, [] { return 2; }, 0ms); });
    rejects([&] { BatchOperator<int, 4>("b", &in, &batch_out, [] { return 2; }, -10ms); });

    // TumblingCountWindow null and invalid parameters
    rejects([&] { TumblingCountWindow<int, int>("w", nullptr, &out, 2, [](const auto&) { return 0; }); });
    rejects([&] { TumblingCountWindow<int, int>("w", &in, nullptr, 2, [](const auto&) { return 0; }); });
    rejects([&] { TumblingCountWindow<int, int>("w", &in, &out, 0, [](const auto&) { return 0; }); });
    rejects([&] { TumblingCountWindow<int, int>("w", &in, &out, 2, nullptr); });

    // MapOperator null parameters
    rejects([&] { MapOperator<int, int>("m", nullptr, &out, [](int x) { return x; }); });
    rejects([&] { MapOperator<int, int>("m", &in, nullptr, [](int x) { return x; }); });
    rejects([&] { MapOperator<int, int>("m", &in, &out, nullptr); });

    // FilterOperator null parameters
    rejects([&] { FilterOperator<int>("f", nullptr, &out, [](int) { return true; }); });
    rejects([&] { FilterOperator<int>("f", &in, nullptr, [](int) { return true; }); });
    rejects([&] { FilterOperator<int>("f", &in, &out, nullptr); });

    // SinkOperator null parameters
    rejects([&] { SinkOperator<int>("s", nullptr, [](const auto&) {}); });
    rejects([&] { SinkOperator<int>("s", &in, nullptr); });

    // SourceOperator null parameters
    rejects([&] { SourceOperator<int>("src", nullptr, [](auto&, auto) { return true; }); });
    rejects([&] { SourceOperator<int>("src", &out, nullptr); });

    // AggregateOperator null parameters
    rejects([&] { AggregateOperator<int, int, int>("a", nullptr, &out, 0, [](int&, int) {}, [](const int&) { return 0; }); });
    rejects([&] { AggregateOperator<int, int, int>("a", &in, nullptr, 0, [](int&, int) {}, [](const int&) { return 0; }); });
    rejects([&] { AggregateOperator<int, int, int>("a", &in, &out, 0, nullptr, [](const int&) { return 0; }); });
    rejects([&] { AggregateOperator<int, int, int>("a", &in, &out, 0, [](int&, int) {}, nullptr); });
}

void test_clean_shutdown_and_deadlock_free_join() {
    SPSCQueue<Event<int>> q1(4), q2(4);

    SourceOperator<int> source("src", &q1, [](Event<int>& e, std::uint64_t seq) {
        e = Event<int>::make(static_cast<int>(seq));
        std::this_thread::sleep_for(50us);
        return true; // continuous
    });
    MapOperator<int, int> map("map", &q1, &q2, [](int x) { return x * 2; });
    SinkOperator<int> sink("sink", &q2, [](const Event<int>&) {});

    Runtime r;
    auto w1 = r.add_worker();
    auto w2 = r.add_worker();
    auto w3 = r.add_worker();
    r.register_op(&source, w1);
    r.register_op(&map, w2);
    r.register_op(&sink, w3);

    r.start();
    std::this_thread::sleep_for(15ms);
    // Immediate stop while workers are executing tick loops
    r.stop();
    // Must join without deadlock and state should be Stopped or Failed
    auto st = r.state();
    CHECK(st == RuntimeState::Stopped || st == RuntimeState::Failed);

    // Calling stop again is idempotent
    r.stop();
    CHECK(r.state() == st);
}

int main() {
    try {
        queue_contracts(); concurrent_queues(); runtime_completion(false); runtime_completion(true);
        runtime_failure(); operators_and_partial_batches(); math_and_configuration(); second_audit_regressions();
        test_tiny_queues_contention();
        test_blocking_and_waking();
        test_injected_cancellation();
        test_queue_state_invariants();
        test_batch_and_window_cancellation();
        test_token_bucket_and_bounds();
        test_operator_parameter_validation();
        test_clean_shutdown_and_deadlock_free_join();
        std::cout << "Foundation correctness checks passed; test fixtures only.\n";
    } catch (const std::exception& e) { std::cerr << e.what() << '\n'; return 1; }
}
