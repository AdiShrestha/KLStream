#include <gtest/gtest.h>
#include <klstream/core/backpressure.hpp>
#include <klstream/core/spsc_queue.hpp>
#include <thread>
#include <chrono>

using namespace klstream;

TEST(BackpressureTest, TokenBucketRateLimiter) {
    TokenBucketRateLimiter limiter(10.0, 10.0);
    int count = 0;
    while (limiter.try_consume()) {
        count++;
    }
    EXPECT_GE(count, 9);
    EXPECT_LE(count, 11);

    EXPECT_FALSE(limiter.try_consume());

    // Sleep for 110ms -> 1 token should replenish at 10 tokens/sec
    std::this_thread::sleep_for(std::chrono::milliseconds(110));
    EXPECT_TRUE(limiter.try_consume());
    EXPECT_FALSE(limiter.try_consume());
}

TEST(BackpressureTest, SimulatedClockExactRefill) {
    TokenBucketRateLimiter limiter(100.0, 100.0); // 100 tokens/sec
    auto t0 = std::chrono::steady_clock::now();

    // Drain initial tokens
    int consumed = 0;
    while (limiter.try_consume_at(t0)) {
        consumed++;
    }
    EXPECT_EQ(consumed, 100);

    // Advance simulated time by 500 ms -> should replenish 50 tokens
    auto t1 = t0 + std::chrono::milliseconds(500);
    int count_t1 = 0;
    while (limiter.try_consume_at(t1)) {
        count_t1++;
    }
    EXPECT_EQ(count_t1, 50);
}

TEST(BackpressureTest, NominalRatePreservedAcrossThrottling) {
    const double nominal = 50'000.0;
    TokenBucketRateLimiter limiter(nominal, nominal, 100.0);

    EXPECT_DOUBLE_EQ(limiter.nominal_rate(), nominal);
    EXPECT_DOUBLE_EQ(limiter.effective_rate(), nominal);

    // Throttle to 50%
    limiter.throttle(0.50);
    EXPECT_DOUBLE_EQ(limiter.effective_rate(), 25'000.0);
    EXPECT_DOUBLE_EQ(limiter.nominal_rate(), nominal); // Nominal untouched

    // Throttle to 10%
    limiter.throttle(0.10);
    EXPECT_DOUBLE_EQ(limiter.effective_rate(), 5'000.0);

    // Recover back to nominal
    limiter.recover();
    EXPECT_DOUBLE_EQ(limiter.effective_rate(), nominal);
}

TEST(BackpressureTest, MinRateFloorEnforced) {
    const double nominal = 1000.0;
    const double min_floor = 50.0;
    TokenBucketRateLimiter limiter(nominal, nominal, min_floor);

    // Throttle to 0% -> must clamp to min_rate
    limiter.throttle(0.0);
    EXPECT_DOUBLE_EQ(limiter.effective_rate(), min_floor);

    limiter.set_rate(1.0); // Below floor
    EXPECT_DOUBLE_EQ(limiter.effective_rate(), min_floor);
}

TEST(BackpressureTest, EMAOccupancyTracker) {
    SPSCQueue<int> q(1024);
    EMAOccupancyTracker<SPSCQueue<int>> tracker(q, 0.5);

    // Fill to ~50%
    for (int i = 0; i < 512; ++i) {
        EXPECT_TRUE(q.try_push(i));
    }

    tracker.update();
    double ema = tracker.ema();
    EXPECT_GT(ema, 0.0);
    EXPECT_LE(ema, 0.6);

    // Fill to full
    for (int i = 512; i < 1023; ++i) {
        EXPECT_TRUE(q.try_push(i));
    }

    for (int i = 0; i < 5; ++i) {
        tracker.update();
    }
    EXPECT_GT(tracker.ema(), ema);
    EXPECT_TRUE(tracker.hard_pressure());
}

TEST(BackpressureTest, BackpressureController_AdaptiveThrottleAndRecovery) {
    SPSCQueue<int> q(1024);
    TokenBucketRateLimiter limiter(10'000.0, 10'000.0, 100.0);
    BackpressureController<SPSCQueue<int>> controller(q, limiter, 0.8);

    // Initially empty -> nominal rate
    controller.update();
    EXPECT_DOUBLE_EQ(limiter.effective_rate(), 10'000.0);

    // Fill queue to 850 items (~83% occupancy)
    for (int i = 0; i < 850; ++i) {
        EXPECT_TRUE(q.try_push(i));
    }

    // Step EMA to steady-state occupancy
    for (int i = 0; i < 10; ++i) {
        controller.update();
    }
    EXPECT_LT(limiter.effective_rate(), 10'000.0);
    EXPECT_GT(limiter.effective_rate(), limiter.min_rate());

    // Drain queue completely
    int val = 0;
    while (q.try_pop(&val)) {}

    // Update controller -> rate recovers back to nominal
    for (int i = 0; i < 10; ++i) {
        controller.update();
    }
    EXPECT_DOUBLE_EQ(limiter.effective_rate(), 10'000.0);
}
