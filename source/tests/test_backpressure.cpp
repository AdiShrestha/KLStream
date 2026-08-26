#include <gtest/gtest.h>
#include "klstream/core/backpressure.hpp"
#include "klstream/core/spsc_queue.hpp"
#include <thread>
#include <chrono>

using namespace klstream;

TEST(BackpressureTest, TokenBucketRateLimiter) {
    TokenBucketRateLimiter limiter(10.0, 10.0);
    // consume all initial tokens
    int count = 0;
    while (limiter.try_consume()) {
        count++;
    }
    EXPECT_GE(count, 9);
    EXPECT_LE(count, 11);
    
    EXPECT_FALSE(limiter.try_consume());
    
    // wait for 1/10th of a second, should get 1 token
    std::this_thread::sleep_for(std::chrono::milliseconds(110));
    EXPECT_TRUE(limiter.try_consume());
    EXPECT_FALSE(limiter.try_consume());
}

TEST(BackpressureTest, EMAOccupancyTracker) {
    SPSCQueue<int> q(1024);
    EMAOccupancyTracker<SPSCQueue<int>> tracker(q, 0.5);
    
    for (int i = 0; i < 512; ++i) {
        q.try_push(i);
    }
    
    tracker.update();
    double ema = tracker.ema();
    EXPECT_GT(ema, 0.0);
    EXPECT_LE(ema, 0.6);
    
    for (int i = 0; i < 512; ++i) {
        q.try_push(i);
    } // queue is full now
    
    tracker.update();
    EXPECT_GT(tracker.ema(), ema);
    EXPECT_TRUE(tracker.hard_pressure());
}
