#include <gtest/gtest.h>
#include <klstream/core/metrics.hpp>
#include <thread>
#include <vector>
#include <numeric>

using namespace klstream;

TEST(MetricsAccuracyTest, EmptyHistogramReturnsZero) {
    LatencyHistogram hist;
    EXPECT_EQ(hist.count(), 0);
    EXPECT_DOUBLE_EQ(hist.percentile(0.50), 0.0);
    EXPECT_DOUBLE_EQ(hist.percentile(0.90), 0.0);
    EXPECT_DOUBLE_EQ(hist.percentile(0.95), 0.0);
    EXPECT_DOUBLE_EQ(hist.percentile(0.99), 0.0);
    EXPECT_DOUBLE_EQ(hist.mean(), 0.0);
}

TEST(MetricsAccuracyTest, SingleSampleReturnsExactLatency) {
    LatencyHistogram hist;
    hist.record_us(42);
    EXPECT_EQ(hist.count(), 1);
    EXPECT_DOUBLE_EQ(hist.p50(), 42.0);
    EXPECT_DOUBLE_EQ(hist.p90(), 42.0);
    EXPECT_DOUBLE_EQ(hist.p95(), 42.0);
    EXPECT_DOUBLE_EQ(hist.p99(), 42.0);
    EXPECT_DOUBLE_EQ(hist.mean(), 42.0);
}

TEST(MetricsAccuracyTest, UniformKnownAnswer_1To100) {
    LatencyHistogram hist;
    for (std::uint64_t lat = 1; lat <= 100; ++lat) {
        hist.record_us(lat);
    }
    EXPECT_EQ(hist.count(), 100);
    EXPECT_DOUBLE_EQ(hist.p50(), 50.0);
    EXPECT_DOUBLE_EQ(hist.p90(), 90.0);
    EXPECT_DOUBLE_EQ(hist.p95(), 95.0);
    EXPECT_DOUBLE_EQ(hist.p99(), 99.0);
    EXPECT_DOUBLE_EQ(hist.percentile(1.00), 100.0);
    EXPECT_DOUBLE_EQ(hist.mean(), 50.5);
}

TEST(MetricsAccuracyTest, BimodalDistribution) {
    LatencyHistogram hist;
    // 500 samples at 10us, 500 samples at 100us
    for (int i = 0; i < 500; ++i) hist.record_us(10);
    for (int i = 0; i < 500; ++i) hist.record_us(100);

    EXPECT_EQ(hist.count(), 1000);
    EXPECT_DOUBLE_EQ(hist.percentile(0.40), 10.0);
    EXPECT_DOUBLE_EQ(hist.percentile(0.50), 10.0);
    EXPECT_DOUBLE_EQ(hist.percentile(0.51), 100.0);
    EXPECT_DOUBLE_EQ(hist.percentile(0.95), 100.0);
    EXPECT_DOUBLE_EQ(hist.mean(), 55.0);
}

TEST(MetricsAccuracyTest, CounterNonDestructiveRead) {
    Counter counter;
    EXPECT_EQ(counter.load(), 0);

    counter.increment(10);
    EXPECT_EQ(counter.load(), 10);
    EXPECT_EQ(counter.load(), 10); // Repeated reads do not mutate
    EXPECT_EQ(counter.get(), 10);

    counter.increment(5);
    EXPECT_EQ(counter.load(), 15);

    counter.reset();
    EXPECT_EQ(counter.load(), 0);
}

TEST(MetricsAccuracyTest, ConcurrentHistogramUpdates) {
    LatencyHistogram hist;
    const int num_threads = 8;
    const int samples_per_thread = 25'000;
    const int total_samples = num_threads * samples_per_thread;

    std::vector<std::thread> threads;
    for (int t = 0; t < num_threads; ++t) {
        threads.emplace_back([&hist]() {
            for (int i = 1; i <= samples_per_thread; ++i) {
                hist.record(static_cast<std::uint64_t>(i % 500) * 1000); // 0..499 us
            }
        });
    }

    for (auto& t : threads) t.join();

    EXPECT_EQ(hist.count(), static_cast<std::uint64_t>(total_samples));
    EXPECT_GE(hist.p50(), 0.0);
    EXPECT_LE(hist.p50(), 500.0);
}
