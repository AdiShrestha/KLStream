/**
 * @file integration_test.cpp
 * @brief Integration tests for the full runtime
 */

#include <gtest/gtest.h>
#include <chrono>
#include <thread>

#include "klstream/klstream.hpp"

using namespace klstream;

class IntegrationTest : public ::testing::Test {
protected:
    void SetUp() override {}
    void TearDown() override {}
};

TEST_F(IntegrationTest, SimplePipeline) {
    RuntimeConfig config;
    config.num_workers = 2;
    config.scheduling_policy = SchedulingPolicy::RoundRobin;
    
    Runtime runtime(config);
    
    StreamGraphBuilder builder;
    
    // Source: 1..100
    SequenceSource::Config source_config;
    source_config.start = 1;
    source_config.count = 100;
    
    auto source = std::make_unique<SequenceSource>("source", source_config);
    auto sink = std::make_unique<CountingSink>("sink");
    auto* sink_ptr = sink.get();
    
    builder
        .add_source(std::move(source))
        .add_sink(std::move(sink))
        .connect("source", "sink");
    
    runtime.init(std::move(builder));
    runtime.start();
    
    // Wait for processing
    std::this_thread::sleep_for(std::chrono::seconds(2));
    
    runtime.stop();
    
    EXPECT_EQ(sink_ptr->count(), 100);
}

TEST_F(IntegrationTest, MapFilterPipeline) {
    RuntimeConfig config;
    config.num_workers = 2;
    
    Runtime runtime(config);
    
    StreamGraphBuilder builder;
    
    // Source: 1..20
    SequenceSource::Config source_config;
    source_config.start = 1;
    source_config.count = 20;
    
    auto source = std::make_unique<SequenceSource>("source", source_config);
    auto square = make_int_map("square", [](std::int64_t x) { return x * x; });
    auto even = make_filter("even", filters::even());
    auto sink = std::make_unique<AggregatingSink>("sink");
    auto* sink_ptr = sink.get();
    
    builder
        .add_source(std::move(source))
        .add_operator(std::move(square))
        .add_operator(std::move(even))
        .add_sink(std::move(sink))
        .connect("source", "square")
        .connect("square", "even")
        .connect("even", "sink");
    
    runtime.init(std::move(builder));
    runtime.start();
    
    std::this_thread::sleep_for(std::chrono::seconds(2));
    
    runtime.stop();
    
    // 1..20 squared: 1, 4, 9, 16, 25, 36, 49, 64, 81, 100, 121, 144, 169, 196, 225, 256, 289, 324, 361, 400
    // Even: 4, 16, 36, 64, 100, 144, 196, 256, 324, 400 (10 items)
    // Sum: 4+16+36+64+100+144+196+256+324+400 = 1540
    
    EXPECT_EQ(sink_ptr->count(), 10);
    EXPECT_EQ(sink_ptr->sum(), 1540);
}

TEST_F(IntegrationTest, BackpressureHandling) {
    RuntimeConfig config;
    config.num_workers = 1;
    
    Runtime runtime(config);
    
    StreamGraphBuilder builder;
    
    // Fast source
    SequenceSource::Config source_config;
    source_config.start = 1;
    source_config.count = 10000;
    
    auto source = std::make_unique<SequenceSource>("source", source_config);
    
    // Slow processing
    auto slow_map = make_operator("slow", [](Event& e, OperatorContext& ctx) {
        std::this_thread::sleep_for(std::chrono::microseconds(100));
        ctx.emit(std::move(e));
    });
    
    auto sink = std::make_unique<CountingSink>("sink");
    
    builder
        .add_source(std::move(source))
        .add_operator(std::move(slow_map))
        .add_sink(std::move(sink))
        .connect("source", "slow")
        .connect("slow", "sink");
    
    runtime.init(std::move(builder));
    runtime.start();
    
    // Let it run briefly
    std::this_thread::sleep_for(std::chrono::milliseconds(500));
    
    runtime.stop();
    
    // With backpressure, the pipeline should have processed some events
    // without crashing or running out of memory
    auto metrics = runtime.metrics().snapshot();
    EXPECT_GT(metrics.total_events_processed, 0);
}

TEST_F(IntegrationTest, MetricsCollection) {
    RuntimeConfig config;
    config.num_workers = 2;
    config.enable_metrics = true;
    
    Runtime runtime(config);
    
    StreamGraphBuilder builder;
    
    SequenceSource::Config source_config;
    source_config.start = 1;
    source_config.count = 1000;
    
    auto source = std::make_unique<SequenceSource>("source", source_config);
    auto sink = std::make_unique<NullSink>("sink");
    
    builder
        .add_source(std::move(source))
        .add_sink(std::move(sink))
        .connect("source", "sink");
    
    runtime.init(std::move(builder));
    runtime.start();
    
    std::this_thread::sleep_for(std::chrono::seconds(1));
    
    auto snapshot = runtime.metrics().snapshot();
    
    runtime.stop();
    
    EXPECT_GT(snapshot.total_events_processed, 0);
    EXPECT_GT(runtime.metrics().uptime().count(), 0);
}
