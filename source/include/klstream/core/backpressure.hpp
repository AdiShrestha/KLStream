// include/klstream/core/backpressure.hpp
#pragma once
#include "config.hpp"
#include <atomic>
#include <chrono>
#include <thread>
#include <cstdint>

namespace klstream {

// ── EMAOccupancyTracker ───────────────────────────────────────────────────
//
// Wraps any Queue that exposes .occupancy() and tracks an exponential
// moving average of its fill fraction.
//
// The EMA alpha parameter controls smoothing:
//   Small alpha (e.g. 0.05): slow to react, very smooth — good for
//     predicting slow-building pressure from sustained overload.
//   Large alpha (e.g. 0.30): reacts quickly — better for bursty workloads.
//
// Default alpha = 0.10 is a sensible starting point. The research extension
// (Section 14.1) sweeps alpha values and measures the effect on p99 latency.
//
// USAGE:
//   EMAOccupancyTracker tracker(my_queue, 0.10);
//   // In the source's tick() loop:
//   tracker.update();
//   if (tracker.ema() > BP_SOFT_THRESHOLD) { /* slow down */ }

template <typename Queue>
class EMAOccupancyTracker {
public:
    explicit EMAOccupancyTracker(Queue& queue, double alpha = 0.10)
        : queue_(queue), alpha_(alpha), ema_(0.0) {}

    // Call once per tick() to update the EMA.
    void update() noexcept {
        double occ = queue_.occupancy();
        ema_ = alpha_ * occ + (1.0 - alpha_) * ema_;
    }

    [[nodiscard]] double ema() const noexcept { return ema_; }

    // Returns true if the EMA exceeds the soft backpressure threshold.
    // When this returns true the source should reduce its emission rate.
    [[nodiscard]] bool soft_pressure() const noexcept {
        return ema_ > BP_SOFT_THRESHOLD;
    }

    // Returns true if occupancy is critically high (hard threshold).
    // When this returns true the source should stop emitting entirely
    // and wait, identical to the baseline blocking behaviour.
    [[nodiscard]] bool hard_pressure() const noexcept {
        return queue_.occupancy() > BP_HARD_THRESHOLD;
    }

private:
    Queue&      queue_;
    double      alpha_;
    double      ema_;
};

// ── TokenBucketRateLimiter ────────────────────────────────────────────────
//
// A simple token-bucket used by SourceOperator to smoothly rate-limit event
// generation when adaptive backpressure is enabled.
//
// tokens are replenished at a configurable rate (tokens_per_sec).
// Each call to try_consume() uses one token. When the bucket is empty,
// try_consume() returns false and the source should pause.
//
// The rate can be reduced at runtime via set_rate(). This is how the adaptive
// backpressure controller gradually slows the source when soft pressure is
// detected (before the queue is actually full).
class TokenBucketRateLimiter {
public:
    explicit TokenBucketRateLimiter(double tokens_per_sec,
                                    double max_burst = 0.0)
        : rate_(tokens_per_sec)
        , tokens_(tokens_per_sec) // start full
        , max_tokens_(max_burst > 0 ? max_burst : tokens_per_sec)
        , last_(std::chrono::steady_clock::now())
    {}

    // Refill tokens based on elapsed time, then try to consume one.
    [[nodiscard]] bool try_consume() noexcept {
        refill();
        if (tokens_ >= 1.0) {
            tokens_ -= 1.0;
            return true;
        }
        return false;
    }

    void set_rate(double tokens_per_sec) noexcept {
        rate_ = tokens_per_sec;
    }

    double rate() const noexcept { return rate_; }

private:
    void refill() noexcept {
        auto now     = std::chrono::steady_clock::now();
        double elapsed = std::chrono::duration<double>(now - last_).count();
        last_    = now;
        tokens_ += elapsed * rate_;
        if (tokens_ > max_tokens_) tokens_ = max_tokens_;
    }

    double rate_;
    double tokens_;
    double max_tokens_;
    std::chrono::steady_clock::time_point last_;
};

} // namespace klstream
