#pragma once
#include "../core/operator.hpp"
#include "../core/event.hpp"
#include "../core/spsc_queue.hpp"
#include "../core/metrics.hpp"
#include "../core/backpressure.hpp"   // EMAOccupancyTracker — reused as-is
#include "types.hpp"
#include <algorithm>
#include <cstdint>

namespace klstream {

// ── AdaptiveWindowController ─────────────────────────────────────────────
//
// Pure control logic, separated from the operator so it can be unit-tested
// without any queue/threading machinery (Section 27 covers testing this
// in isolation with synthetic occupancy traces).
//
// Asymmetric shrink-fast / grow-slow update, directly modeled on TCP's
// AIMD congestion control (cited explicitly in your methodology section —
// this is a principled choice, not an arbitrary tuning knob). The deadband
// between occ_low_ and occ_high_ is what prevents oscillation (Section 6,
// point 1) — do not remove it even if it looks redundant in early testing.
class AdaptiveWindowController {
public:
    AdaptiveWindowController(std::uint32_t w_min, std::uint32_t w_max,
                             double occ_low, double occ_high,
                             double shrink_factor = 0.70,
                             double grow_factor   = 1.15)
        : w_min_(w_min), w_max_(w_max)
        , occ_low_(occ_low), occ_high_(occ_high)
        , shrink_factor_(shrink_factor), grow_factor_(grow_factor)
        , current_w_(w_max)   // start wide: assume calm until proven otherwise
    {}

    // Call exactly once per window START (Section 14's tick() logic below
    // captures this once and holds it for the whole window's fill duration
    // — never mid-window, to avoid a window "shrinking out from under
    // itself").
    std::uint32_t update(double ema_occupancy) {
        if (ema_occupancy > occ_high_) {
            current_w_ = std::max(w_min_,
                static_cast<std::uint32_t>(current_w_ * shrink_factor_));
            ++shrink_events_;
        } else if (ema_occupancy < occ_low_) {
            current_w_ = std::min(w_max_,
                static_cast<std::uint32_t>(current_w_ * grow_factor_));
            ++grow_events_;
        }
        // else: deadband — hold steady. This branch existing (doing
        // nothing) is the whole anti-oscillation mechanism.
        track_direction(ema_occupancy);
        return current_w_;
    }

    std::uint32_t current() const { return current_w_; }

    // Window Oscillation Rate support (Section 23.2) — counts direction
    // *changes*, not raw shrink/grow events, which is the metric that
    // actually captures thrashing.
    std::uint64_t direction_changes() const { return direction_changes_; }

private:
    void track_direction(double ema_occupancy) {
        int dir = 0;
        if (ema_occupancy > occ_high_) dir = -1;       // shrinking
        else if (ema_occupancy < occ_low_) dir = 1;    // growing
        else return;                                     // deadband: no direction sample
        if (last_dir_ != 0 && dir != last_dir_) ++direction_changes_;
        last_dir_ = dir;
    }

    std::uint32_t w_min_, w_max_;
    double        occ_low_, occ_high_;
    double        shrink_factor_, grow_factor_;
    std::uint32_t current_w_;
    std::uint64_t shrink_events_{0};
    std::uint64_t grow_events_{0};
    std::uint64_t direction_changes_{0};
    int           last_dir_{0};
};

// ── AdaptiveWindowOp ───────────────────────────────────────────────────────
//
// Implements the IOperator interface (Section 7.5 of the Implementation
// Guide) — same tick()/OpStatus contract as every other KLStream operator,
// so it slots into Runtime::register_op() with no special handling.
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
        , tracker_(*output)   // reads occupancy of ITS OWN output queue —
                                // this is the load-bearing line, see Section 7.2
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

        // At the START of a new window, capture this window's target size
        // ONCE from the current EMA reading. Held fixed until this window
        // fires (Section 7.2's "shrink for FUTURE windows" rule).
        if (buffer_.count == 0) {
            auto start_t = std::chrono::steady_clock::now();
            tracker_.update();
            target_w_ = controller_.update(tracker_.ema());
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
            return OpStatus::Processed;   // buffered, window not yet ready
        }

        Event<WindowBatch> out_ev;
        out_ev.timestamp_ns = in_ev.timestamp_ns;  // last tick's timestamp;
                                                     // InferenceOp overwrites
                                                     // this with the flagged
                                                     // tick's own timestamp
                                                     // before re-emitting
                                                     // (Section 7.4, 17.2)
        out_ev.key  = 0;
        out_ev.seq  = in_ev.seq;
        out_ev.data = buffer_;
        buffer_ = WindowBatch{};   // reset for next window

        if (output_->try_push(out_ev)) {
            if (metrics_) metrics_->events_processed.increment();
            return OpStatus::Processed;
        }
        pending_     = out_ev;
        has_pending_ = true;
        if (metrics_) metrics_->events_blocked.increment();
        return OpStatus::Blocked;
    }

private:
    InQueue*                       input_;
    OutQueue*                      output_;
    AdaptiveWindowController       controller_;
    EMAOccupancyTracker<OutQueue>  tracker_;
    WindowBatch                    buffer_{};
    std::uint32_t                  target_w_{0};
    Event<WindowBatch>             pending_{};
    bool                            has_pending_{false};
    OperatorMetrics*               metrics_{nullptr};
    std::uint64_t                  overhead_ns_sum_{0};
    std::uint64_t                  overhead_samples_{0};

public:
    double mean_overhead_ns() const {
        return overhead_samples_ > 0 ? static_cast<double>(overhead_ns_sum_) / overhead_samples_ : 0.0;
    }
};

} // namespace klstream
