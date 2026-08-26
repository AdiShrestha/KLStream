#pragma once
#include <array>
#include <cstdint>
#include <type_traits>

namespace klstream {

// ── FeatureVector ─────────────────────────────────────────────────────────
// D = 5 feature dimensions for streaming anomaly detection.
struct FeatureVector {
    float log_return;
    float rolling_vol;
    float order_imbalance;
    float spread_bps;
    float volume;

    static constexpr std::size_t kDim = 5;

    std::array<float, kDim> to_point() const {
        return { log_return, rolling_vol, order_imbalance, spread_bps, volume };
    }
};
static_assert(sizeof(FeatureVector) == 5 * sizeof(float),
    "FeatureVector must stay a flat POD — no padding tricks, it crosses queues");

// ── WindowBatch ────────────────────────────────────────────────────────────
// Fixed-capacity, trivially-copyable container for windowed batches.
inline constexpr std::size_t MAX_WINDOW_SIZE = 256;

struct WindowBatch {
    std::array<FeatureVector, MAX_WINDOW_SIZE> points{};
    std::uint32_t count = 0;
    std::uint64_t first_seq = 0;
    std::uint64_t last_seq  = 0;
    float         occupancy_at_decision = 0.0f; // Recorded queue occupancy at decision

    void push_back(const FeatureVector& fv, std::uint64_t seq) {
        if (count == 0) first_seq = seq;
        points[count++] = fv;
        last_seq = seq;
    }
    bool full(std::size_t target_size) const { return count >= target_size; }
};
static_assert(std::is_trivially_copyable_v<WindowBatch>,
    "WindowBatch must remain trivially copyable to cross SPSCQueue boundaries");

// ── DetectionResult ──────────────────────────────────────────────────────
// Emitted by InferenceOp, consumed by Sink.
struct DetectionResult {
    double        max_score             = 0.0;
    std::uint32_t window_size_used      = 0;
    std::uint64_t first_seq             = 0;
    std::uint64_t last_seq              = 0;
    std::uint64_t flagged_seq           = 0;
    float         occupancy_at_decision = 0.0f; // Real-time occupancy at window decision
};
static_assert(std::is_trivially_copyable_v<DetectionResult>);

} // namespace klstream
