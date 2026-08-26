#pragma once
#include <array>
#include <cstdint>

namespace klstream {

// ── FeatureVector ─────────────────────────────────────────────────────────
// D = 5, matching Section 10's feature table exactly. Order matters: this
// order must match the column order written by preprocess_lobster.py
// (Section 11) and read by TickSource (Section 18).
struct FeatureVector {
    float log_return;
    float rolling_vol;
    float order_imbalance;
    float spread_bps;
    float volume;          // already log1p-scaled by the Python preprocessor

    static constexpr std::size_t kDim = 5;

    // Conversion to the array type IsolationTree/IsolationForest operate on.
    std::array<float, kDim> to_point() const {
        return { log_return, rolling_vol, order_imbalance, spread_bps, volume };
    }
};
static_assert(sizeof(FeatureVector) == 5 * sizeof(float),
    "FeatureVector must stay a flat POD — no padding tricks, it crosses queues");

// ── WindowBatch ────────────────────────────────────────────────────────────
// Fixed-capacity, trivially-copyable container — see Section 7.3 for why
// this cannot be a std::vector. MAX_WINDOW_SIZE caps every window
// strategy's upper bound (AdaptiveWindowController::w_max_,
// DataDrivenWindowOp's max, and FixedWindowOp's constant must all be
// <= MAX_WINDOW_SIZE).
inline constexpr std::size_t MAX_WINDOW_SIZE = 256;

struct WindowBatch {
    std::array<FeatureVector, MAX_WINDOW_SIZE> points{};
    std::uint32_t count = 0;
    std::uint64_t first_seq = 0;   // seq of points[0] — for ground-truth join
    std::uint64_t last_seq  = 0;   // seq of points[count-1]

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
// Emitted by InferenceOp (Section 17), consumed by Sink (Section 19).
struct DetectionResult {
    double        max_score        = 0.0;
    std::uint32_t window_size_used = 0;
    std::uint64_t first_seq        = 0;
    std::uint64_t last_seq         = 0;
    std::uint64_t flagged_seq      = 0;   // seq of the point that produced max_score
    float         occupancy_at_decision = 0.0f; // EMA reading at window-start time, 0 for non-adaptive variants
};
static_assert(std::is_trivially_copyable_v<DetectionResult>);

} // namespace klstream
