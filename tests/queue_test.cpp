/**
 * @file queue_test.cpp
 * @brief Unit tests for BoundedQueue
 */

#include <gtest/gtest.h>
#include <thread>
#include <vector>
#include <atomic>

#include "klstream/core/queue.hpp"
#include "klstream/core/event.hpp"

using namespace klstream;

class QueueTest : public ::testing::Test {
protected:
    void SetUp() override {}
    void TearDown() override {}
};

TEST_F(QueueTest, BasicPushPop) {
    BoundedQueue<64> queue;
    
    Event e1{std::int64_t{42}};
    ASSERT_TRUE(queue.push(std::move(e1)));
    
    auto result = queue.pop();
    ASSERT_TRUE(result.has_value());
    ASSERT_TRUE(result->holds<std::int64_t>());
    EXPECT_EQ(result->get<std::int64_t>(), 42);
}

TEST_F(QueueTest, TryPushPop) {
    BoundedQueue<64> queue;
    
    // Try pop on empty queue
    auto empty_result = queue.try_pop();
    EXPECT_FALSE(empty_result.has_value());
    
    // Try push
    Event e1{std::int64_t{123}};
    ASSERT_TRUE(queue.try_push(std::move(e1)));
    
    auto result = queue.try_pop();
    ASSERT_TRUE(result.has_value());
    EXPECT_EQ(result->get<std::int64_t>(), 123);
}

TEST_F(QueueTest, Capacity) {
    BoundedQueue<4> queue;
    
    EXPECT_EQ(queue.capacity(), 4);
    EXPECT_TRUE(queue.empty());
    EXPECT_FALSE(queue.full());
    
    // Fill the queue
    for (int i = 0; i < 4; i++) {
        ASSERT_TRUE(queue.try_push(Event{std::int64_t{i}}));
    }
    
    EXPECT_TRUE(queue.full());
    EXPECT_FALSE(queue.empty());
    EXPECT_EQ(queue.size(), 4);
    
    // Should fail on full queue
    EXPECT_FALSE(queue.try_push(Event{std::int64_t{99}}));
}

TEST_F(QueueTest, Close) {
    BoundedQueue<64> queue;
    
    queue.push(Event{std::int64_t{1}});
    queue.push(Event{std::int64_t{2}});
    
    queue.close();
    EXPECT_TRUE(queue.is_closed());
    
    // Should fail to push after close
    EXPECT_FALSE(queue.push(Event{std::int64_t{3}}));
    
    // Should still be able to pop existing items
    auto r1 = queue.pop();
    ASSERT_TRUE(r1.has_value());
    EXPECT_EQ(r1->get<std::int64_t>(), 1);
    
    auto r2 = queue.pop();
    ASSERT_TRUE(r2.has_value());
    EXPECT_EQ(r2->get<std::int64_t>(), 2);
    
    // Empty and closed
    auto r3 = queue.pop();
    EXPECT_FALSE(r3.has_value());
}

TEST_F(QueueTest, ConcurrentPushPop) {
    BoundedQueue<1024> queue;
    constexpr int num_items = 10000;
    std::atomic<int> produced{0};
    std::atomic<int> consumed{0};
    
    // Producer thread
    std::thread producer([&]() {
        for (int i = 0; i < num_items; i++) {
            queue.push(Event{std::int64_t{i}});
            produced.fetch_add(1, std::memory_order_relaxed);
        }
    });
    
    // Consumer thread
    std::thread consumer([&]() {
        while (consumed.load(std::memory_order_relaxed) < num_items) {
            auto event = queue.pop_for(std::chrono::milliseconds(100));
            if (event) {
                consumed.fetch_add(1, std::memory_order_relaxed);
            }
        }
    });
    
    producer.join();
    consumer.join();
    
    EXPECT_EQ(produced.load(), num_items);
    EXPECT_EQ(consumed.load(), num_items);
}

TEST_F(QueueTest, MultipleProducers) {
    BoundedQueue<1024> queue;
    constexpr int num_producers = 4;
    constexpr int items_per_producer = 1000;
    std::atomic<int> total_produced{0};
    std::atomic<int> total_consumed{0};
    
    std::vector<std::thread> producers;
    for (int p = 0; p < num_producers; p++) {
        producers.emplace_back([&, p]() {
            for (int i = 0; i < items_per_producer; i++) {
                queue.push(Event{std::int64_t{p * items_per_producer + i}});
                total_produced.fetch_add(1, std::memory_order_relaxed);
            }
        });
    }
    
    std::thread consumer([&]() {
        int target = num_producers * items_per_producer;
        while (total_consumed.load(std::memory_order_relaxed) < target) {
            auto event = queue.pop_for(std::chrono::milliseconds(100));
            if (event) {
                total_consumed.fetch_add(1, std::memory_order_relaxed);
            }
        }
    });
    
    for (auto& t : producers) {
        t.join();
    }
    consumer.join();
    
    EXPECT_EQ(total_produced.load(), num_producers * items_per_producer);
    EXPECT_EQ(total_consumed.load(), num_producers * items_per_producer);
}

TEST_F(QueueTest, Stats) {
    BoundedQueue<64> queue;
    
    queue.push(Event{std::int64_t{1}});
    queue.push(Event{std::int64_t{2}});
    queue.pop();
    
    auto stats = queue.stats();
    EXPECT_EQ(stats.push_count, 2);
    EXPECT_EQ(stats.pop_count, 1);
    EXPECT_EQ(stats.current_size, 1);
    EXPECT_EQ(stats.capacity, 64);
}
