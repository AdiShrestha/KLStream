#include <gtest/gtest.h>
#include "klstream/operators/map.hpp"
#include "klstream/operators/filter.hpp"
#include "klstream/operators/aggregate.hpp"
#include "klstream/operators/window.hpp"
#include "klstream/operators/source.hpp"
#include "klstream/core/spsc_queue.hpp"
#include <vector>

using namespace klstream;

// Test 1: MapOperator_Squares
TEST(OperatorsTest, MapOperator_Squares) {
    SPSCQueue<Event<uint64_t>> q_in(16);
    SPSCQueue<Event<uint64_t>> q_out(16);
    
    MapOperator<uint64_t, uint64_t> map_op(
        "map", &q_in, &q_out, [](uint64_t x) { return x * x; });
        
    for (uint64_t i = 1; i <= 5; ++i) {
        q_in.try_push(Event<uint64_t>::make(i));
    }
    
    for (int i = 0; i < 5; ++i) {
        EXPECT_EQ(map_op.tick(), OpStatus::Processed);
    }
    EXPECT_EQ(map_op.tick(), OpStatus::Idle);
    
    std::vector<uint64_t> expected = {1, 4, 9, 16, 25};
    for (uint64_t exp : expected) {
        auto val = q_out.pop();
        ASSERT_TRUE(val.has_value());
        EXPECT_EQ(val.value().data, exp);
    }
}

// Test 2: FilterOperator_Evens
TEST(OperatorsTest, FilterOperator_Evens) {
    SPSCQueue<Event<uint64_t>> q_in(16);
    SPSCQueue<Event<uint64_t>> q_out(16);
    
    FilterOperator<uint64_t> filter_op(
        "filter", &q_in, &q_out, [](uint64_t x) { return x % 2 == 0; });
        
    for (uint64_t i = 1; i <= 5; ++i) {
        q_in.try_push(Event<uint64_t>::make(i));
    }
    
    for (int i = 0; i < 5; ++i) {
        EXPECT_EQ(filter_op.tick(), OpStatus::Processed);
    }
    
    std::vector<uint64_t> expected = {2, 4};
    for (uint64_t exp : expected) {
        auto val = q_out.pop();
        ASSERT_TRUE(val.has_value());
        EXPECT_EQ(val.value().data, exp);
    }
    EXPECT_FALSE(q_out.pop().has_value());
}

// Test 3: AggregateOperator_RunningSum
TEST(OperatorsTest, AggregateOperator_RunningSum) {
    SPSCQueue<Event<uint64_t>> q_in(16);
    SPSCQueue<Event<uint64_t>> q_out(16);
    
    AggregateOperator<uint64_t, uint64_t, uint64_t> agg_op(
        "agg", &q_in, &q_out, 0ULL,
        [](uint64_t& st, uint64_t x){ st += x; },
        [](const uint64_t& st){ return st; });
        
    for (uint64_t i = 1; i <= 5; ++i) {
        q_in.try_push(Event<uint64_t>::make(i));
    }
    
    for (int i = 0; i < 5; ++i) {
        EXPECT_EQ(agg_op.tick(), OpStatus::Processed);
    }
    
    std::vector<uint64_t> expected = {1, 3, 6, 10, 15};
    for (uint64_t exp : expected) {
        auto val = q_out.pop();
        ASSERT_TRUE(val.has_value());
        EXPECT_EQ(val.value().data, exp);
    }
}

// Test 4: TumblingCountWindow_Fires
TEST(OperatorsTest, TumblingCountWindow_Fires) {
    SPSCQueue<Event<uint64_t>> q_in(16);
    SPSCQueue<Event<uint64_t>> q_out(16);
    
    TumblingCountWindow<uint64_t, uint64_t> win_op(
        "win", &q_in, &q_out, 3,
        [](const std::vector<Event<uint64_t>>& buf) {
            uint64_t sum = 0;
            for (auto v : buf) sum += v.data;
            return sum;
        });
        
    std::vector<uint64_t> input = {10, 20, 30, 40, 50, 60};
    for (uint64_t x : input) {
        q_in.try_push(Event<uint64_t>::make(x));
    }
    
    for (int i = 0; i < 6; ++i) {
        EXPECT_EQ(win_op.tick(), OpStatus::Processed);
    }
    
    auto val1 = q_out.pop();
    ASSERT_TRUE(val1.has_value());
    EXPECT_EQ(val1.value().data, 60ULL);
    
    auto val2 = q_out.pop();
    ASSERT_TRUE(val2.has_value());
    EXPECT_EQ(val2.value().data, 150ULL);
    
    EXPECT_FALSE(q_out.pop().has_value());
}

// Test 5: Operator_BlockedWhenOutputFull
TEST(OperatorsTest, Operator_BlockedWhenOutputFull) {
    SPSCQueue<Event<uint64_t>> q_in(16);
    SPSCQueue<Event<uint64_t>> q_out(4); // capacity 4 -> holds 3
    
    MapOperator<uint64_t, uint64_t> map_op(
        "map", &q_in, &q_out, [](uint64_t x) { return x; });
        
    EXPECT_TRUE(q_in.try_push(Event<uint64_t>::make(1)));
    EXPECT_TRUE(q_in.try_push(Event<uint64_t>::make(2)));
    EXPECT_TRUE(q_in.try_push(Event<uint64_t>::make(3)));
    EXPECT_TRUE(q_in.try_push(Event<uint64_t>::make(4))); // push 4
    
    EXPECT_EQ(map_op.tick(), OpStatus::Processed); // out holds 1
    EXPECT_EQ(map_op.tick(), OpStatus::Processed); // out holds 2
    EXPECT_EQ(map_op.tick(), OpStatus::Processed); // out holds 3 (full)
    EXPECT_EQ(map_op.tick(), OpStatus::Blocked);   // blocked
    
    auto val = q_out.pop();
    ASSERT_TRUE(val.has_value());
    
    EXPECT_EQ(map_op.tick(), OpStatus::Processed);
}

// Test 6: SourceOperator_PendingRetry
TEST(OperatorsTest, SourceOperator_PendingRetry) {
    SPSCQueue<Event<uint64_t>> q_out(4); // capacity 4 -> holds 3
    
    uint64_t seq_val = 0;
    SourceOperator<uint64_t> src_op(
        "src", &q_out,
        [&seq_val](Event<uint64_t>& out, uint64_t) {
            out = Event<uint64_t>::make(++seq_val);
            return true;
        });
        
    EXPECT_EQ(src_op.tick(), OpStatus::Processed); // q_out holds 1
    EXPECT_EQ(src_op.tick(), OpStatus::Processed); // q_out holds 2
    EXPECT_EQ(src_op.tick(), OpStatus::Processed); // q_out holds 3 (full)
    EXPECT_EQ(src_op.tick(), OpStatus::Blocked);
    
    // Ensure seq_val hasn't been incremented unnecessarily
    EXPECT_EQ(seq_val, 4ULL); 
    
    q_out.pop();
    
    EXPECT_EQ(src_op.tick(), OpStatus::Processed);
    EXPECT_EQ(seq_val, 4ULL); // Should push the same cached event
}

// Test 7: TumblingTimeWindow_Fires
TEST(OperatorsTest, TumblingTimeWindow_Fires) {
    SPSCQueue<Event<uint64_t>> q_in(16);
    SPSCQueue<Event<uint64_t>> q_out(16);
    
    // 100ms time window
    TumblingTimeWindow<uint64_t, uint64_t> win_op(
        "win", &q_in, &q_out, std::chrono::milliseconds(100),
        [](const std::vector<uint64_t>& buf) {
            uint64_t sum = 0;
            for (auto v : buf) sum += v;
            return sum;
        });
        
    // First event at T=0
    q_in.try_push(Event<uint64_t>::make(10));
    EXPECT_EQ(win_op.tick(), OpStatus::Processed);
    
    // Queue should be empty, window not fired
    EXPECT_FALSE(q_out.pop().has_value());
    
    // Sleep to simulate time passing (150ms > 100ms)
    std::this_thread::sleep_for(std::chrono::milliseconds(150));
    
    // Second event triggers the window for the first batch
    q_in.try_push(Event<uint64_t>::make(20));
    EXPECT_EQ(win_op.tick(), OpStatus::Processed);
    
    // Now the window should have fired with the first event
    auto val = q_out.pop();
    ASSERT_TRUE(val.has_value());
    EXPECT_EQ(val.value().data, 10ULL);
}
