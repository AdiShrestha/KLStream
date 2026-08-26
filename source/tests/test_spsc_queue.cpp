#include <gtest/gtest.h>
#include <klstream/core/spsc_queue.hpp>
#include <thread>
#include <vector>
#include <atomic>
#include <chrono>

using namespace klstream;

// Test 1: SingleThreaded_PushPop
TEST(SPSCQueueTest, SingleThreaded_PushPop) {
    SPSCQueue<int> q(16);
    EXPECT_TRUE(q.empty());
    EXPECT_EQ(q.usable_capacity(), 15);
    EXPECT_EQ(q.capacity(), 16);

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
TEST(SPSCQueueTest, CapacityRespected) {
    SPSCQueue<int> q(4);
    EXPECT_EQ(q.usable_capacity(), 3);

    EXPECT_TRUE(q.try_push(1));
    EXPECT_TRUE(q.try_push(2));
    EXPECT_TRUE(q.try_push(3));
    EXPECT_FALSE(q.try_push(4)); // Usable capacity is 3 (capacity - 1)

    int out = 0;
    EXPECT_TRUE(q.try_pop(out));
    EXPECT_EQ(out, 1);
    EXPECT_TRUE(q.try_push(6));
}

// Test 3: CapacityBoundary_Capacity2Usable1
TEST(SPSCQueueTest, CapacityBoundary_Capacity2Usable1) {
    SPSCQueue<int> q(2);
    EXPECT_EQ(q.capacity(), 2);
    EXPECT_EQ(q.usable_capacity(), 1);

    EXPECT_TRUE(q.try_push(42));
    EXPECT_FALSE(q.try_push(43)); // Full after 1 item

    int out = 0;
    EXPECT_TRUE(q.try_pop(&out));
    EXPECT_EQ(out, 42);
    EXPECT_TRUE(q.empty());

    EXPECT_TRUE(q.try_push(99));
    EXPECT_FALSE(q.empty());
}

// Test 4: OccupancyPrecision
TEST(SPSCQueueTest, OccupancyPrecision) {
    SPSCQueue<int> q(16);
    EXPECT_DOUBLE_EQ(q.occupancy(), 0.0);

    for (int i = 0; i < 15; ++i) {
        EXPECT_TRUE(q.try_push(i));
    }
    // Full (15/15) = 1.0
    EXPECT_DOUBLE_EQ(q.occupancy(), 1.0);

    int out = 0;
    EXPECT_TRUE(q.try_pop(&out));
    // 14 / 15
    EXPECT_NEAR(q.occupancy(), 14.0 / 15.0, 1e-6);
}

// Test 5: ConcurrentProducerConsumer (1,000,000 items)
TEST(SPSCQueueTest, ConcurrentProducerConsumer) {
    SPSCQueue<int> q(1024);
    const int num_items = 1'000'000;

    std::thread producer([&]() {
        for (int i = 0; i < num_items; ++i) {
            while (!q.try_push(i)) {}
        }
    });

    std::thread consumer([&]() {
        for (int i = 0; i < num_items; ++i) {
            int val = -1;
            while (!q.try_pop(&val)) {}
            EXPECT_EQ(val, i);
        }
    });

    producer.join();
    consumer.join();
}

// Test 6: StopUnblocksBlockingPush
TEST(SPSCQueueTest, StopUnblocksBlockingPush) {
    SPSCQueue<int> q(4);
    // Fill to usable capacity (3 items)
    EXPECT_TRUE(q.try_push(1));
    EXPECT_TRUE(q.try_push(2));
    EXPECT_TRUE(q.try_push(3));

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

// Test 7: StopUnblocksBlockingPop
TEST(SPSCQueueTest, StopUnblocksBlockingPop) {
    SPSCQueue<int> q(4);
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
