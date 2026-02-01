/**
 * @file operator_test.cpp
 * @brief Unit tests for operators
 */

#include <gtest/gtest.h>

#include "klstream/klstream.hpp"

using namespace klstream;

class OperatorTest : public ::testing::Test {
protected:
    void SetUp() override {}
    void TearDown() override {}
};

TEST_F(OperatorTest, MapOperator) {
    auto square = make_int_map("square", [](std::int64_t x) { return x * x; });
    
    auto output_queue = std::make_shared<Queue>();
    OperatorContext ctx("test", 0);
    ctx.add_output(output_queue);
    
    Event input{std::int64_t{5}};
    square->process(input, ctx);
    
    auto result = output_queue->try_pop();
    ASSERT_TRUE(result.has_value());
    EXPECT_EQ(result->get<std::int64_t>(), 25);
}

TEST_F(OperatorTest, FilterOperatorPass) {
    auto even_filter = make_filter("even", filters::even());
    
    auto output_queue = std::make_shared<Queue>();
    OperatorContext ctx("test", 0);
    ctx.add_output(output_queue);
    
    Event input{std::int64_t{4}};  // Even number
    even_filter->process(input, ctx);
    
    auto result = output_queue->try_pop();
    ASSERT_TRUE(result.has_value());
    EXPECT_EQ(result->get<std::int64_t>(), 4);
}

TEST_F(OperatorTest, FilterOperatorBlock) {
    auto even_filter = make_filter("even", filters::even());
    
    auto output_queue = std::make_shared<Queue>();
    OperatorContext ctx("test", 0);
    ctx.add_output(output_queue);
    
    Event input{std::int64_t{5}};  // Odd number
    even_filter->process(input, ctx);
    
    auto result = output_queue->try_pop();
    EXPECT_FALSE(result.has_value());  // Should be filtered out
}

TEST_F(OperatorTest, FilterInRange) {
    auto range_filter = make_filter("range", filters::in_range(10, 20));
    
    auto output_queue = std::make_shared<Queue>();
    OperatorContext ctx("test", 0);
    ctx.add_output(output_queue);
    
    // In range
    Event e1{std::int64_t{15}};
    range_filter->process(e1, ctx);
    EXPECT_TRUE(output_queue->try_pop().has_value());
    
    // Out of range (low)
    Event e2{std::int64_t{5}};
    range_filter->process(e2, ctx);
    EXPECT_FALSE(output_queue->try_pop().has_value());
    
    // Out of range (high)
    Event e3{std::int64_t{25}};
    range_filter->process(e3, ctx);
    EXPECT_FALSE(output_queue->try_pop().has_value());
}

TEST_F(OperatorTest, SourceOperator) {
    SequenceSource::Config config;
    config.start = 1;
    config.step = 2;
    config.count = 5;
    
    auto source = std::make_unique<SequenceSource>("seq", config);
    
    auto output_queue = std::make_shared<Queue>();
    OperatorContext ctx("seq", 0);
    ctx.add_output(output_queue);
    
    // Generate all events
    while (source->generate(ctx)) {}
    
    // Verify sequence: 1, 3, 5, 7, 9
    std::vector<std::int64_t> expected{1, 3, 5, 7, 9};
    for (auto exp : expected) {
        auto event = output_queue->try_pop();
        ASSERT_TRUE(event.has_value());
        EXPECT_EQ(event->get<std::int64_t>(), exp);
    }
    
    // Should be empty now
    EXPECT_FALSE(output_queue->try_pop().has_value());
}

TEST_F(OperatorTest, SinkOperator) {
    auto sink = std::make_unique<AggregatingSink>("agg");
    
    OperatorContext ctx("agg", 0);
    
    Event e1{std::int64_t{10}};
    Event e2{std::int64_t{20}};
    Event e3{std::int64_t{30}};
    
    sink->process(e1, ctx);
    sink->process(e2, ctx);
    sink->process(e3, ctx);
    
    EXPECT_EQ(sink->count(), 3);
    EXPECT_EQ(sink->sum(), 60);
    EXPECT_DOUBLE_EQ(sink->mean(), 20.0);
    EXPECT_EQ(sink->min(), 10);
    EXPECT_EQ(sink->max(), 30);
}

TEST_F(OperatorTest, CountingSink) {
    auto sink = std::make_unique<CountingSink>("counter");
    
    OperatorContext ctx("counter", 0);
    
    for (int i = 0; i < 100; i++) {
        Event e{std::int64_t{i}};
        sink->process(e, ctx);
    }
    
    EXPECT_EQ(sink->count(), 100);
    
    sink->reset();
    EXPECT_EQ(sink->count(), 0);
}

TEST_F(OperatorTest, FunctionOperator) {
    auto double_op = make_operator("double", [](Event& e, OperatorContext& ctx) {
        if (auto* val = e.get_if<std::int64_t>()) {
            ctx.emit(Event{*val * 2});
        }
    });
    
    auto output_queue = std::make_shared<Queue>();
    OperatorContext ctx("test", 0);
    ctx.add_output(output_queue);
    
    Event input{std::int64_t{7}};
    double_op->process(input, ctx);
    
    auto result = output_queue->try_pop();
    ASSERT_TRUE(result.has_value());
    EXPECT_EQ(result->get<std::int64_t>(), 14);
}

TEST_F(OperatorTest, ChainedOperators) {
    // Square -> Filter even
    auto square = make_int_map("square", [](std::int64_t x) { return x * x; });
    auto even = make_filter("even", filters::even());
    
    auto mid_queue = std::make_shared<Queue>();
    auto output_queue = std::make_shared<Queue>();
    
    OperatorContext ctx1("square", 0);
    ctx1.add_output(mid_queue);
    
    OperatorContext ctx2("even", 0);
    ctx2.add_output(output_queue);
    
    // Process 1..5
    for (int i = 1; i <= 5; i++) {
        Event e{std::int64_t{i}};
        square->process(e, ctx1);
    }
    
    // Now squares are: 1, 4, 9, 16, 25
    // Filter: 4, 16 (even)
    while (auto e = mid_queue->try_pop()) {
        even->process(*e, ctx2);
    }
    
    // Verify
    auto r1 = output_queue->try_pop();
    ASSERT_TRUE(r1.has_value());
    EXPECT_EQ(r1->get<std::int64_t>(), 4);
    
    auto r2 = output_queue->try_pop();
    ASSERT_TRUE(r2.has_value());
    EXPECT_EQ(r2->get<std::int64_t>(), 16);
    
    EXPECT_FALSE(output_queue->try_pop().has_value());
}
