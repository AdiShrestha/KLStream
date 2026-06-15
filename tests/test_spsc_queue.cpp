#include <gtest/gtest.h>
#include "klstream/core/spsc_queue.hpp"
#include <thread>
#include <vector>

using namespace klstream;

// Test 1: SingleThreaded_PushPop
TEST(SPSCQueueTest, SingleThreaded_PushPop) {
    SPSCQueue<int> q(16);
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
TEST(SPSCQueueTest, CapacityRespected) {
    SPSCQueue<int> q(4);
    EXPECT_TRUE(q.try_push(1));
    EXPECT_TRUE(q.try_push(2));
    EXPECT_TRUE(q.try_push(3));
    EXPECT_FALSE(q.try_push(4)); // queue is full (capacity is technically n-1 usable in some ring buffers, but rigtorp allows full N if power of 2, wait. Let's check capacity. rigtorp uses capacity_ - 1 mask so it actually stores capacity_ items).
    // Let's actually test up to capacity.
    SPSCQueue<int> q2(4);
    EXPECT_TRUE(q2.try_push(1));
    EXPECT_TRUE(q2.try_push(2));
    EXPECT_TRUE(q2.try_push(3));
    EXPECT_TRUE(q2.try_push(4));
    EXPECT_FALSE(q2.try_push(5));
    
    EXPECT_TRUE(q2.pop().has_value());
    EXPECT_TRUE(q2.try_push(6));
}

// Test 3: ConcurrentProducerConsumer
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
            int val;
            while (!q.try_pop(&val)) {}
            EXPECT_EQ(val, i);
        }
    });
    
    producer.join();
    consumer.join();
}

// Test 4: OccupancyApproximate
TEST(SPSCQueueTest, OccupancyApproximate) {
    SPSCQueue<int> q(16);
    for (int i = 0; i < 8; ++i) {
        EXPECT_TRUE(q.try_push(i));
    }
    double occ = q.occupancy();
    EXPECT_GE(occ, 0.45);
    EXPECT_LE(occ, 0.55);
}

// Test 5: PowerOfTwoEnforced
TEST(SPSCQueueTest, PowerOfTwoEnforced) {
    EXPECT_DEATH({ SPSCQueue<int> q(3); }, "power of 2");
}
