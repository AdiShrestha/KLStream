#pragma once
#include "../core/operator.hpp"
#include "../core/event.hpp"
#include "../core/spsc_queue.hpp"
#include "../core/metrics.hpp"
#include "types.hpp"
#include <algorithm>
#include <cstdint>

namespace klstream {

class DataDrivenWindowOp : public IOperator {
public:
    using InQueue  = SPSCQueue<Event<FeatureVector>>;
    using OutQueue = SPSCQueue<Event<WindowBatch>>;

    DataDrivenWindowOp(std::string name, InQueue* input, OutQueue* output,
                       std::uint32_t w_min = 16, std::uint32_t w_max = MAX_WINDOW_SIZE,
                       float vol_low = 8.98e-09f, float vol_high = 1.52e-08f)
        : IOperator(std::move(name))
        , input_(input), output_(output)
        , w_min_(w_min), w_max_(w_max)
        , vol_low_(vol_low), vol_high_(vol_high)
        , target_w_(w_max)
    {}

    void attach_metrics(OperatorMetrics* m) override { metrics_ = m; }

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
            // Linear interpolation between w_max (calm) and w_min (volatile),
            // clamped — the literature-baseline analogue of Section 14's
            // EMA-occupancy read, but driven by the FeatureVector's own
            // rolling_vol field rather than any queue state.
            float vol = last_vol_;
            float frac = std::clamp((vol - vol_low_) / (vol_high_ - vol_low_), 0.0f, 1.0f);
            target_w_ = static_cast<std::uint32_t>(
                w_max_ - frac * static_cast<float>(w_max_ - w_min_));
            auto end_t = std::chrono::steady_clock::now();
            overhead_ns_sum_ += std::chrono::duration_cast<std::chrono::nanoseconds>(end_t - start_t).count();
            overhead_samples_++;
        }

        Event<FeatureVector> in_ev;
        if (!input_->try_pop(&in_ev)) {
            if (metrics_) metrics_->events_idle.increment();
            return OpStatus::Idle;
        }
        last_vol_ = in_ev.data.rolling_vol;
        buffer_.push_back(in_ev.data, in_ev.seq);

        if (!buffer_.full(target_w_)) {
            if (metrics_) metrics_->events_processed.increment();
            return OpStatus::Processed;
        }

        Event<WindowBatch> out_ev;
        out_ev.timestamp_ns = in_ev.timestamp_ns;
        out_ev.seq  = in_ev.seq;
        out_ev.data = buffer_;
        buffer_ = WindowBatch{};

        if (output_->try_push(out_ev)) {
            if (metrics_) metrics_->events_processed.increment();
            return OpStatus::Processed;
        }
        pending_ = out_ev;
        has_pending_ = true;
        if (metrics_) metrics_->events_blocked.increment();
        return OpStatus::Blocked;
    }

private:
    InQueue*       input_;
    OutQueue*      output_;
    std::uint32_t  w_min_, w_max_;
    float          vol_low_, vol_high_;
    std::uint32_t  target_w_;
    float          last_vol_{0.0f};
    WindowBatch    buffer_{};
    Event<WindowBatch> pending_{};
    bool           has_pending_{false};
    OperatorMetrics* metrics_{nullptr};
    std::uint64_t  overhead_ns_sum_{0};
    std::uint64_t  overhead_samples_{0};

public:
    double mean_overhead_ns() const {
        return overhead_samples_ > 0 ? static_cast<double>(overhead_ns_sum_) / overhead_samples_ : 0.0;
    }
};

} // namespace klstream
