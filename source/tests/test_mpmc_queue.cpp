#include <gtest/gtest.h>
#include <klstream/core/mpmc_queue.hpp>
#include <thread>
#include <vector>
#include <atomic>
#include <algorithm>
#include <chrono>

using namespace klstream;

// Test 1: SingleThreaded_PushPop
TEST(MPMCQueueTest, SingleThreaded_PushPop) {
    MPMCQueue<int> q(16);
    EXPECT_TRUE(q.empty());
    for (int i = 0; i < 5; ++i) {
        EXPECT_TRUE(q.try_push(i));
    }
    EXPECT_FALSE(q.empty());
    for (int i = 0; i < 5; ++i) {
        auto val = q.pop();
        ASSERT_TRUE(val.has_value());
        EXPECT_EQ(val.value(), i);
    }
    EXPECT_TRUE(q.empty());
}

// Test 2: CapacityRespected
TEST(MPMCQueueTest, CapacityRespected) {
    MPMCQueue<int> q(4);
    EXPECT_TRUE(q.try_push(1));
    EXPECT_TRUE(q.try_push(2));
    EXPECT_TRUE(q.try_push(3));
    EXPECT_TRUE(q.try_push(4));
    EXPECT_FALSE(q.try_push(5)); // Full
    
    int out = 0;
    EXPECT_TRUE(q.try_pop(out));
    EXPECT_EQ(out, 1);
    EXPECT_TRUE(q.try_push(6));
}

// Test 3: FullQueueOccupancyReportsN
TEST(MPMCQueueTest, FullQueueOccupancyReportsN) {
    const std::size_t cap = 16;
    MPMCQueue<int> q(cap);
    EXPECT_DOUBLE_EQ(q.occupancy(), 0.0);
    EXPECT_EQ(q.size_approx(), 0);

    for (std::size_t i = 0; i < cap; ++i) {
        EXPECT_TRUE(q.try_push(static_cast<int>(i)));
    }

    // Full queue must report occupancy 1.0 (not 0.0)
    EXPECT_DOUBLE_EQ(q.occupancy(), 1.0);
    EXPECT_EQ(q.size_approx(), cap);

    int val = 0;
    EXPECT_TRUE(q.try_pop(&val));
    EXPECT_DOUBLE_EQ(q.occupancy(), 15.0 / 16.0);
    EXPECT_EQ(q.size_approx(), 15);
}

// Test 4: DisjointRangesMultiProducerMultiConsumer (4 producers, 4 consumers)
TEST(MPMCQueueTest, DisjointRangesMultiProducerMultiConsumer) {
    MPMCQueue<int> q(1024);
    const int items_per_producer = 25'000;
    const int num_producers = 4;
    const int total_items = items_per_producer * num_producers;
    const int num_consumers = 4;

    std::vector<std::thread> producers;
    for (int p = 0; p < num_producers; ++p) {
        producers.emplace_back([&, p]() {
            int start = p * items_per_producer;
            int end = start + items_per_producer;
            for (int i = start; i < end; ++i) {
                while (!q.try_push(i)) {}
            }
        });
    }

    std::vector<std::vector<int>> consumer_results(num_consumers);
    std::vector<std::thread> consumers;
    std::atomic<int> total_popped{0};

    for (int c = 0; c < num_consumers; ++c) {
        consumers.emplace_back([&, c]() {
            consumer_results[c].reserve(total_items / num_consumers + 1000);
            while (total_popped.load(std::memory_order_relaxed) < total_items) {
                int val = -1;
                if (q.try_pop(&val)) {
                    consumer_results[c].push_back(val);
                    total_popped.fetch_add(1, std::memory_order_relaxed);
                }
            }
        });
    }

    for (auto& t : producers) t.join();
    for (auto& t : consumers) t.join();

    // Verify all items are collected with zero duplicates and zero loss
    std::vector<int> all_popped;
    all_popped.reserve(total_items);
    for (const auto& vec : consumer_results) {
        all_popped.insert(all_popped.end(), vec.begin(), vec.end());
    }

    ASSERT_EQ(all_popped.size(), static_cast<std::size_t>(total_items));
    std::sort(all_popped.begin(), all_popped.end());

    for (int i = 0; i < total_items; ++i) {
        EXPECT_EQ(all_popped[i], i);
    }
}

// Test 5: StopUnblocksBlockingPush
TEST(MPMCQueueTest, StopUnblocksBlockingPush) {
    MPMCQueue<int> q(2);
    EXPECT_TRUE(q.try_push(1));
    EXPECT_TRUE(q.try_push(2));

    std::atomic<bool> push_started{false};
    std::atomic<bool> push_returned{false};
    bool push_result = true;

    std::thread blocked_producer([&]() {
        push_started.store(true);
        push_result = q.push(999);
        push_returned.store(true);
    });

    while (!push_started.load()) {
        std::this_thread::yield();
    }
    std::this_thread::sleep_for(std::chrono::milliseconds(20));

    EXPECT_FALSE(push_returned.load());
    q.stop();

    blocked_producer.join();
    EXPECT_TRUE(push_returned.load());
    EXPECT_FALSE(push_result);
}

// Test 6: StopUnblocksBlockingPop
TEST(MPMCQueueTest, StopUnblocksBlockingPop) {
    MPMCQueue<int> q(4);
    EXPECT_TRUE(q.empty());

    std::atomic<bool> pop_started{false};
    std::atomic<bool> pop_returned{false};
    int pop_val = -1;
    bool pop_result = true;

    std::thread blocked_consumer([&]() {
        pop_started.store(true);
        pop_result = q.pop(pop_val);
        pop_returned.store(true);
    });

    while (!pop_started.load()) {
        std::this_thread::yield();
    }
    std::this_thread::sleep_for(std::chrono::milliseconds(20));

    EXPECT_FALSE(pop_returned.load());
    q.stop();

    blocked_consumer.join();
    EXPECT_TRUE(pop_returned.load());
    EXPECT_FALSE(pop_result);
}
