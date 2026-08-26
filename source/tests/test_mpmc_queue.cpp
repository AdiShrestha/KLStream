#include <gtest/gtest.h>
#include "klstream/core/mpmc_queue.hpp"
#include <thread>
#include <vector>
#include <atomic>

using namespace klstream;

// Test 1: SingleThreaded_PushPop
TEST(MPMCQueueTest, SingleThreaded_PushPop) {
    MPMCQueue<int> q(16);
    for (int i = 0; i < 5; ++i) {
        EXPECT_TRUE(q.try_push(i));
    }
    for (int i = 0; i < 5; ++i) {
        auto val = q.pop();
        ASSERT_TRUE(val.has_value());
        EXPECT_EQ(val.value(), i);
    }
}

// Test 2: CapacityRespected
TEST(MPMCQueueTest, CapacityRespected) {
    MPMCQueue<int> q(4);
    EXPECT_TRUE(q.try_push(1));
    EXPECT_TRUE(q.try_push(2));
    EXPECT_TRUE(q.try_push(3));
    EXPECT_TRUE(q.try_push(4));
    EXPECT_FALSE(q.try_push(5));
    
    EXPECT_TRUE(q.pop().has_value());
    EXPECT_TRUE(q.try_push(6));
}

// Test 3: ConcurrentProducerConsumer
TEST(MPMCQueueTest, ConcurrentProducerConsumer) {
    MPMCQueue<int> q(1024);
    const int num_items = 100'000;
    const int num_threads = 4;
    
    std::atomic<int> push_count{0};
    std::atomic<int> pop_count{0};
    
    std::vector<std::thread> producers;
    for (int t = 0; t < num_threads; ++t) {
        producers.emplace_back([&]() {
            for (int i = 0; i < num_items; ++i) {
                while (!q.try_push(i)) {}
                push_count++;
            }
        });
    }
    
    std::vector<std::thread> consumers;
    for (int t = 0; t < num_threads; ++t) {
        consumers.emplace_back([&]() {
            for (int i = 0; i < num_items; ++i) {
                int val;
                while (!q.try_pop(&val)) {}
                pop_count++;
            }
        });
    }
    
    for (auto& t : producers) t.join();
    for (auto& t : consumers) t.join();
    
    EXPECT_EQ(push_count.load(), num_items * num_threads);
    EXPECT_EQ(pop_count.load(), num_items * num_threads);
}
