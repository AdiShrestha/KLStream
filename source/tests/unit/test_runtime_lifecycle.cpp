#include <gtest/gtest.h>
#include <klstream/core/runtime.hpp>
#include <klstream/core/spsc_queue.hpp>
#include <klstream/operators/source.hpp>
#include <klstream/operators/sink.hpp>
#include <klstream/operators/map.hpp>

#include <atomic>
#include <vector>
#include <chrono>

using namespace klstream;

namespace {

class LifecycleTrackingOperator : public IOperator {
public:
    LifecycleTrackingOperator(std::atomic<int>& inits, std::atomic<int>& shutdowns)
        : IOperator("LifecycleTracker")
        , inits_(inits)
        , shutdowns_(shutdowns) {}

    void init() override {
        inits_.fetch_add(1, std::memory_order_relaxed);
    }

    OpStatus tick() override {
        return OpStatus::Idle;
    }

    void shutdown() override {
        shutdowns_.fetch_add(1, std::memory_order_relaxed);
    }

private:
    std::atomic<int>& inits_;
    std::atomic<int>& shutdowns_;
};

} // namespace

TEST(RuntimeLifecycleTest, InitialStateIsCreated) {
    Runtime rt;
    EXPECT_EQ(rt.state(), RuntimeState::Created);
}

TEST(RuntimeLifecycleTest, StartTransitionsToRunning) {
    Runtime rt;
    rt.add_worker();
    rt.start();
    EXPECT_EQ(rt.state(), RuntimeState::Running);
    rt.stop();
    EXPECT_EQ(rt.state(), RuntimeState::Stopped);
}

TEST(RuntimeLifecycleTest, DoubleStartThrowsException) {
    Runtime rt;
    rt.add_worker();
    rt.start();
    EXPECT_THROW(rt.start(), std::logic_error);
    rt.stop();
}

TEST(RuntimeLifecycleTest, AddWorkerAfterStartThrows) {
    Runtime rt;
    rt.add_worker();
    rt.start();
    EXPECT_THROW(rt.add_worker(), std::logic_error);
    rt.stop();
}

TEST(RuntimeLifecycleTest, StopIsIdempotent) {
    Runtime rt;
    rt.add_worker();
    rt.start();
    EXPECT_EQ(rt.state(), RuntimeState::Running);

    rt.stop();
    EXPECT_EQ(rt.state(), RuntimeState::Stopped);

    // Repeated stop() calls must be safe and idempotent
    EXPECT_NO_THROW(rt.stop());
    EXPECT_NO_THROW(rt.stop());
    EXPECT_NO_THROW(rt.stop());
    EXPECT_EQ(rt.state(), RuntimeState::Stopped);
}

TEST(RuntimeLifecycleTest, ExactlyOnceCallbacks) {
    std::atomic<int> inits{0};
    std::atomic<int> shutdowns{0};

    LifecycleTrackingOperator op(inits, shutdowns);

    {
        Runtime rt;
        int w0 = rt.add_worker();
        rt.register_op(&op, w0);

        EXPECT_EQ(inits.load(), 0);
        EXPECT_EQ(shutdowns.load(), 0);

        rt.start();
        rt.wait_for(std::chrono::milliseconds(50));

        EXPECT_EQ(inits.load(), 1);
        EXPECT_EQ(shutdowns.load(), 0);

        rt.stop();
        rt.stop(); // extra idempotent stop
    }

    EXPECT_EQ(inits.load(), 1);
    EXPECT_EQ(shutdowns.load(), 1);
}

TEST(RuntimeLifecycleTest, LosslessPipelineDrain) {
    const int N = 1000;
    SPSCQueue<Event<int>> q_in(2048);
    SPSCQueue<Event<int>> q_out(2048);

    // Pre-populate input queue with items
    for (int i = 0; i < N; ++i) {
        EXPECT_TRUE(q_in.try_push(Event<int>::make(i)));
    }

    std::vector<int> collected;
    collected.reserve(N);

    MapOperator<int, int> map_op("MultiplyBy2", &q_in, &q_out, [](int x) {
        return x * 2;
    });

    SinkOperator<int> sink_op("Collector", &q_out, [&](const Event<int>& ev) {
        collected.push_back(ev.data);
    });


    {
        Runtime rt;
        int w0 = rt.add_worker();
        int w1 = rt.add_worker();

        rt.register_op(&map_op, w0);
        rt.register_op(&sink_op, w1);

        rt.start();

        // Wait until all items are processed or runtime drains
        auto start_time = std::chrono::steady_clock::now();
        while (collected.size() < N &&
               std::chrono::steady_clock::now() - start_time < std::chrono::seconds(2)) {
            std::this_thread::sleep_for(std::chrono::milliseconds(10));
        }

        rt.drain();
        rt.stop();
    }

    ASSERT_EQ(collected.size(), static_cast<std::size_t>(N));
    for (int i = 0; i < N; ++i) {
        EXPECT_EQ(collected[i], i * 2);
    }
}
