// source/tests/unit/test_header_compilation.cpp
// Header compilation test verifying that all KLStream headers are self-contained and compile cleanly.

#include <gtest/gtest.h>

// Core headers
#include <klstream/core/config.hpp>
#include <klstream/core/event.hpp>
#include <klstream/core/spsc_queue.hpp>
#include <klstream/core/mpmc_queue.hpp>
#include <klstream/core/backpressure.hpp>
#include <klstream/core/operator.hpp>
#include <klstream/core/worker.hpp>
#include <klstream/core/runtime.hpp>
#include <klstream/core/metrics.hpp>
#include <klstream/core/pinning.hpp>

// Operators headers
#include <klstream/operators/source.hpp>
#include <klstream/operators/sink.hpp>
#include <klstream/operators/map.hpp>
#include <klstream/operators/filter.hpp>
#include <klstream/operators/aggregate.hpp>
#include <klstream/operators/window.hpp>

// Model headers
#include <klstream/model/isolation_forest.hpp>

// Window headers
#include <klstream/window/types.hpp>
#include <klstream/window/financial_tick_source.hpp>
#include <klstream/window/adaptive_window_op.hpp>
#include <klstream/window/data_driven_window_op.hpp>
#include <klstream/window/inference_op.hpp>
#include <klstream/window/result_sink.hpp>

// Umbrella header
#include <klstream/klstream.hpp>

TEST(HeaderCompilationTest, VersionConstantsAvailable) {
    EXPECT_STREQ(klstream::VERSION, "0.2.0-dev");
    EXPECT_STREQ(klstream::version(), "0.2.0-dev");
    EXPECT_EQ(klstream::VERSION_MAJOR, 0);
    EXPECT_EQ(klstream::VERSION_MINOR, 2);
    EXPECT_EQ(klstream::VERSION_PATCH, 0);
}


TEST(HeaderCompilationTest, CoreConfigConstantsAvailable) {
    EXPECT_GE(klstream::CACHE_LINE_SIZE, 64);
    EXPECT_EQ(klstream::DEFAULT_QUEUE_CAPACITY, 4096);
    EXPECT_DOUBLE_EQ(klstream::BP_SOFT_THRESHOLD, 0.70);
    EXPECT_DOUBLE_EQ(klstream::BP_HARD_THRESHOLD, 0.95);
}

TEST(HeaderCompilationTest, StructAndClassInstantiations) {
    klstream::Event<uint64_t> evt = klstream::Event<uint64_t>::make(12345);
    EXPECT_EQ(evt.data, 12345);

    klstream::SPSCQueue<uint64_t> spsc(16);
    EXPECT_EQ(spsc.capacity(), 16);
    EXPECT_TRUE(spsc.empty());

    klstream::MPMCQueue<uint64_t> mpmc(16);
    EXPECT_EQ(mpmc.capacity(), 16);
    EXPECT_DOUBLE_EQ(mpmc.occupancy(), 0.0);

    klstream::TokenBucketRateLimiter limiter(1000.0, 100);
    EXPECT_TRUE(limiter.try_consume());

    klstream::EMAOccupancyTracker<klstream::SPSCQueue<uint64_t>> tracker(spsc, 0.1);
    tracker.update();
    EXPECT_GE(tracker.ema(), 0.0);
}
