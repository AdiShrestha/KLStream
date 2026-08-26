#include <gtest/gtest.h>
#include <klstream/window/adaptive_window_op.hpp>
#include <klstream/window/inference_op.hpp>
#include <klstream/window/types.hpp>
#include <klstream/model/isolation_forest.hpp>
#include <klstream/core/spsc_queue.hpp>

using namespace klstream;

TEST(AdaptiveControllerTest, HardBoundsClamping) {
    const std::uint32_t w_min = 16;
    const std::uint32_t w_max = 256;
    AdaptiveWindowController controller(w_min, w_max, 0.30, 0.70, 0.50, 1.50);

    // Apply severe high occupancy (1.0) repeatedly
    for (int i = 0; i < 50; ++i) {
        std::uint32_t w = controller.update(1.0);
        EXPECT_GE(w, w_min);
        EXPECT_LE(w, w_max);
    }
    EXPECT_EQ(controller.current(), w_min);

    // Apply zero occupancy (0.0) repeatedly
    for (int i = 0; i < 50; ++i) {
        std::uint32_t w = controller.update(0.0);
        EXPECT_GE(w, w_min);
        EXPECT_LE(w, w_max);
    }
    EXPECT_EQ(controller.current(), w_max);
}

TEST(AdaptiveControllerTest, StepLoadDampingAndStability) {
    // MAR-X4 validation: step increase in queue occupancy converges monotonically to w_min
    const std::uint32_t w_min = 16;
    const std::uint32_t w_max = 256;
    AdaptiveWindowController controller(w_min, w_max, 0.30, 0.70, 0.70, 1.15);

    EXPECT_EQ(controller.current(), w_max);

    std::uint32_t prev_w = w_max;
    for (int i = 0; i < 15; ++i) {
        std::uint32_t w = controller.update(0.90);
        EXPECT_LE(w, prev_w); // Monotonically non-increasing
        EXPECT_GE(w, w_min);
        prev_w = w;
    }
    EXPECT_EQ(controller.current(), w_min);
    EXPECT_EQ(controller.direction_changes(), 0); // Zero oscillation
}

TEST(AdaptiveControllerTest, DeadbandStability) {
    const std::uint32_t w_min = 16;
    const std::uint32_t w_max = 128;
    AdaptiveWindowController controller(w_min, w_max, 0.30, 0.70);

    controller.update(0.80); // Step down once
    std::uint32_t steady_w = controller.current();

    // In deadband [0.30, 0.70], window size must remain constant
    for (int i = 0; i < 20; ++i) {
        std::uint32_t w = controller.update(0.50);
        EXPECT_EQ(w, steady_w);
    }
    EXPECT_EQ(controller.direction_changes(), 0);
}

TEST(AdaptiveControllerTest, TelemetryOccupancyForwarded) {
    SPSCQueue<Event<FeatureVector>> in_q(512);
    SPSCQueue<Event<WindowBatch>> batch_q(512);
    SPSCQueue<Event<DetectionResult>> out_q(512);

    AdaptiveWindowOp window_op("AdaptiveWindow", &in_q, &batch_q, 16, 64, 0.30, 0.70);
    IsolationForest<5> forest(10, 16, 42); // 10 trees, sub-sample 16, seed 42
    InferenceOp inference_op("Inference", &batch_q, &out_q, &forest);

    // Fill input queue with 64 events
    for (uint64_t i = 1; i <= 64; ++i) {
        FeatureVector fv{0.01f, 0.02f, 0.1f, 1.5f, 500.0f};
        EXPECT_TRUE(in_q.try_push(Event<FeatureVector>::make(fv, 0, i)));
    }

    // Process all events through window operator
    while (in_q.occupancy() > 0.0) {
        window_op.tick();
    }

    // Process batch through inference operator
    while (batch_q.occupancy() > 0.0) {
        inference_op.tick();
    }

    Event<DetectionResult> res_ev;
    ASSERT_TRUE(out_q.try_pop(&res_ev));
    EXPECT_GT(res_ev.data.window_size_used, 0);
    EXPECT_GE(res_ev.data.occupancy_at_decision, 0.0f);
}
