#pragma once
#include <klstream/core/operator.hpp>
#include <klstream/core/event.hpp>
#include <klstream/core/spsc_queue.hpp>
#include <klstream/core/metrics.hpp>
#include <klstream/core/backpressure.hpp>
#include <klstream/window/types.hpp>
#include <algorithm>
#include <cstdint>
#include <cmath>

namespace klstream {

// ── AdaptiveWindowController ─────────────────────────────────────────────
//
// Pure control logic for dynamic window sizing based on downstream occupancy.
//
// Correctness guarantees (MAR-X4, FR-008):
//   * Hard bounds [w_min, w_max] enforced on every update.
//   * Deadband [occ_low, occ_high] prevents high-frequency limit-cycle oscillation.
//   * AIMD-style asymmetric adaptation: multiplicative shrink, additive/multiplicative growth.

class AdaptiveWindowController {
public:
    AdaptiveWindowController(std::uint32_t w_min, std::uint32_t w_max,
                             double occ_low, double occ_high,
                             double shrink_factor = 0.70,
                             double grow_factor   = 1.15)
        : w_min_(std::max(1u, w_min))
        , w_max_(std::max(w_min, w_max))
        , occ_low_(std::clamp(occ_low, 0.0, 1.0))
        , occ_high_(std::clamp(occ_high, occ_low, 1.0))
        , shrink_factor_(std::clamp(shrink_factor, 0.01, 0.99))
        , grow_factor_(std::max(1.01, grow_factor))
        , current_w_(w_max)
    {}

    std::uint32_t update(double ema_occupancy) {
        if (ema_occupancy > occ_high_) {
            auto next_w = static_cast<std::uint32_t>(std::floor(current_w_ * shrink_factor_));
            current_w_ = std::clamp(next_w, w_min_, w_max_);
            ++shrink_events_;
        } else if (ema_occupancy < occ_low_) {
            auto next_w = static_cast<std::uint32_t>(std::ceil(current_w_ * grow_factor_));
            if (next_w == current_w_) next_w += 1;
            current_w_ = std::clamp(next_w, w_min_, w_max_);
            ++grow_events_;
        }
        track_direction(ema_occupancy);
        return current_w_;
    }

    [[nodiscard]] std::uint32_t current() const noexcept { return current_w_; }
    [[nodiscard]] std::uint32_t w_min() const noexcept { return w_min_; }
    [[nodiscard]] std::uint32_t w_max() const noexcept { return w_max_; }
    [[nodiscard]] std::uint64_t direction_changes() const noexcept { return direction_changes_; }
    [[nodiscard]] std::uint64_t shrink_events() const noexcept { return shrink_events_; }
    [[nodiscard]] std::uint64_t grow_events() const noexcept { return grow_events_; }

private:
    void track_direction(double ema_occupancy) {
        int dir = 0;
        if (ema_occupancy > occ_high_) dir = -1;
        else if (ema_occupancy < occ_low_) dir = 1;
        else return;

        if (last_dir_ != 0 && dir != last_dir_) ++direction_changes_;
        last_dir_ = dir;
    }

    const std::uint32_t w_min_, w_max_;
    const double        occ_low_, occ_high_;
    const double        shrink_factor_, grow_factor_;
    std::uint32_t       current_w_;
    std::uint64_t       shrink_events_{0};
    std::uint64_t       grow_events_{0};
    std::uint64_t       direction_changes_{0};
    int                 last_dir_{0};
};

// ── AdaptiveWindowOp ───────────────────────────────────────────────────────
class AdaptiveWindowOp : public IOperator {
public:
    using InQueue  = SPSCQueue<Event<FeatureVector>>;
    using OutQueue = SPSCQueue<Event<WindowBatch>>;

    AdaptiveWindowOp(std::string name, InQueue* input, OutQueue* output,
                     std::uint32_t w_min = 16, std::uint32_t w_max = MAX_WINDOW_SIZE,
                     double occ_low = 0.30, double occ_high = 0.70,
                     double shrink_factor = 0.70, double grow_factor = 1.15)
        : IOperator(std::move(name))
        , input_(input), output_(output)
        , controller_(w_min, w_max, occ_low, occ_high, shrink_factor, grow_factor)
        , tracker_(*output)
    {}

    void attach_metrics(OperatorMetrics* m) override { metrics_ = m; }
    const AdaptiveWindowController& controller() const { return controller_; }

    OpStatus tick() override {
        if (has_pending_) {
            if (output_->try_push(pending_)) {
                has_pending_ = false;
                if (metrics_) metrics_->events_processed.increment();
                return OpStatus::Processed;
            }
            if (metrics_) metrics_->events_blocked.increment();
            return OpStatus::Blocked;
        }

        if (buffer_.count == 0) {
            auto start_t = std::chrono::steady_clock::now();
            tracker_.update();
            recorded_occupancy_ = static_cast<float>(tracker_.ema());
            target_w_ = controller_.update(recorded_occupancy_);
            auto end_t = std::chrono::steady_clock::now();
            overhead_ns_sum_ += std::chrono::duration_cast<std::chrono::nanoseconds>(end_t - start_t).count();
            overhead_samples_++;
        }

        Event<FeatureVector> in_ev;
        if (!input_->try_pop(&in_ev)) {
            if (metrics_) metrics_->events_idle.increment();
            return OpStatus::Idle;
        }

        buffer_.push_back(in_ev.data, in_ev.seq);

        if (!buffer_.full(target_w_)) {
            if (metrics_) metrics_->events_processed.increment();
            return OpStatus::Processed;
        }

        buffer_.occupancy_at_decision = recorded_occupancy_;

        Event<WindowBatch> out_ev;
        out_ev.timestamp_ns = in_ev.timestamp_ns;
        out_ev.key  = 0;
        out_ev.seq  = in_ev.seq;
        out_ev.data = buffer_;
        buffer_ = WindowBatch{};

        if (output_->try_push(out_ev)) {
            if (metrics_) metrics_->events_processed.increment();
            return OpStatus::Processed;
        }
        pending_     = out_ev;
        has_pending_ = true;
        if (metrics_) metrics_->events_blocked.increment();
        return OpStatus::Blocked;
    }

    [[nodiscard]] double mean_overhead_ns() const noexcept {
        return overhead_samples_ > 0 ? static_cast<double>(overhead_ns_sum_) / overhead_samples_ : 0.0;
    }

private:
    InQueue*                       input_;
    OutQueue*                      output_;
    AdaptiveWindowController       controller_;
    EMAOccupancyTracker<OutQueue>  tracker_;
    WindowBatch                    buffer_{};
    std::uint32_t                  target_w_{0};
    float                          recorded_occupancy_{0.0f};
    Event<WindowBatch>             pending_{};
    bool                           has_pending_{false};
    OperatorMetrics*               metrics_{nullptr};
    std::uint64_t                  overhead_ns_sum_{0};
    std::uint64_t                  overhead_samples_{0};
};


} // namespace klstream
