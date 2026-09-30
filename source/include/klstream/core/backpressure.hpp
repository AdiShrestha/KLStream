#pragma once

#include <klstream/core/config.hpp>
#include <atomic>
#include <chrono>
#include <thread>
#include <cstdint>
#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace klstream {

// ── EMAOccupancyTracker ───────────────────────────────────────────────────
//
// Wraps any Queue exposing .occupancy() and tracks an exponential
// moving average of its fill fraction.
//
// Formula: EMA_t = alpha * occ_t + (1 - alpha) * EMA_{t-1}

template <typename Queue>
class EMAOccupancyTracker {
public:
    explicit EMAOccupancyTracker(Queue& queue, double alpha = 0.10)
        : queue_(queue), alpha_(alpha), ema_(0.0) {
        if (!std::isfinite(alpha) || alpha <= 0 || alpha > 1) throw std::invalid_argument("EMA alpha must be in (0,1]");
    }

    void update() {
        double occ = queue_.occupancy();
        ema_ = alpha_ * occ + (1.0 - alpha_) * ema_;
    }

    [[nodiscard]] double ema() const noexcept { return ema_; }

    [[nodiscard]] bool soft_pressure() const noexcept {
        return ema_ > BP_SOFT_THRESHOLD;
    }

    [[nodiscard]] bool hard_pressure() const noexcept {
        return queue_.occupancy() > BP_HARD_THRESHOLD;
    }

    void reset() noexcept {
        ema_ = 0.0;
    }

private:
    Queue& queue_;
    double alpha_;
    double ema_;
};

// ── TokenBucketRateLimiter ────────────────────────────────────────────────
//
// Token-bucket rate limiter with nominal rate preservation and anti-lockup guarantees.
//
// Correctness Contract (INV-007, FR-006):
//   * nominal_rate_ is immutable and defines the baseline emission target.
//   * effective_rate_ dynamically fluctuates under backpressure but never drops below min_rate_.
//   * When backpressure clears, effective_rate_ deterministically recovers to nominal_rate_.

class TokenBucketRateLimiter {
public:
    explicit TokenBucketRateLimiter(double tokens_per_sec,
                                    double max_burst = 0.0,
                                    double min_rate_floor = 0.0)
        : nominal_rate_(tokens_per_sec)
        , effective_rate_(tokens_per_sec)
        , min_rate_(min_rate_floor == 0 ? std::min(1.0, tokens_per_sec) : min_rate_floor)
        , tokens_(max_burst > 0 ? max_burst : std::max(1.0, tokens_per_sec))
        , max_tokens_(max_burst > 0.0 ? max_burst : std::max(1.0, tokens_per_sec))
        , last_(std::chrono::steady_clock::now())
    {
        if (!std::isfinite(tokens_per_sec) || tokens_per_sec <= 0 || !std::isfinite(max_burst) || max_burst < 0 || max_tokens_ < 1 || !std::isfinite(min_rate_floor) || min_rate_floor < 0 || min_rate_ > nominal_rate_)
            throw std::invalid_argument("Invalid token bucket rate, burst or floor");
    }

    // Try consuming a token at the current real time.
    [[nodiscard]] bool try_consume() noexcept {
        return try_consume_at(std::chrono::steady_clock::now());
    }

    // Try consuming a token at a specified time point (for deterministic/simulated testing).
    [[nodiscard]] bool try_consume_at(std::chrono::steady_clock::time_point now) noexcept {
        refill(now);
        if (tokens_ >= 1.0) {
            tokens_ -= 1.0;
            return true;
        }
        return false;
    }

    // Set dynamic rate directly; clamped to [min_rate_, nominal_rate_].
    void set_rate(double tokens_per_sec) {
        if (!std::isfinite(tokens_per_sec)) throw std::invalid_argument("Nonfinite token rate");
        double clamped = std::clamp(tokens_per_sec, min_rate_, nominal_rate_);
        effective_rate_.store(clamped, std::memory_order_relaxed);
    }

    // Throttle rate by a factor in [0.0, 1.0].
    void throttle(double factor) {
        if (!std::isfinite(factor)) throw std::invalid_argument("Nonfinite throttle factor");
        double clamped_factor = std::clamp(factor, 0.0, 1.0);
        double new_rate = nominal_rate_ * clamped_factor;
        set_rate(new_rate);
    }

    // Reset rate to 100% nominal rate.
    void recover() noexcept {
        effective_rate_.store(nominal_rate_, std::memory_order_relaxed);
    }

    [[nodiscard]] double rate() const noexcept {
        return effective_rate_.load(std::memory_order_relaxed);
    }

    [[nodiscard]] double nominal_rate() const noexcept {
        return nominal_rate_;
    }

    [[nodiscard]] double effective_rate() const noexcept {
        return rate();
    }

    [[nodiscard]] double min_rate() const noexcept {
        return min_rate_;
    }

private:
    void refill(std::chrono::steady_clock::time_point now) noexcept {
        double elapsed = std::chrono::duration<double>(now - last_).count();
        if (elapsed <= 0.0) return;
        last_ = now;
        double current_rate = effective_rate_.load(std::memory_order_relaxed);
        tokens_ += elapsed * current_rate;
        if (tokens_ > max_tokens_) tokens_ = max_tokens_;
    }

    const double                                 nominal_rate_;
    std::atomic<double>                          effective_rate_;
    const double                                 min_rate_;
    double                                       tokens_;
    double                                       max_tokens_;
    std::chrono::steady_clock::time_point        last_;
};

// ── BackpressureController ────────────────────────────────────────────────
//
// Automatically adjusts emission rate of a TokenBucketRateLimiter based on
// EMA occupancy of downstream queues.

template <typename Queue>
class BackpressureController {
public:
    BackpressureController(Queue& downstream_queue,
                           TokenBucketRateLimiter& rate_limiter,
                           double alpha = 0.10)
        : tracker_(downstream_queue, alpha)
        , limiter_(rate_limiter)
    {}

    void update() {
        tracker_.update();
        double ema = tracker_.ema();

        if (tracker_.hard_pressure()) {
            limiter_.set_rate(limiter_.min_rate());
        } else if (tracker_.soft_pressure()) {
            // Linear throttle between soft threshold (0.70) and hard threshold (0.90)
            double range = BP_HARD_THRESHOLD - BP_SOFT_THRESHOLD;
            double over = ema - BP_SOFT_THRESHOLD;
            double factor = std::clamp(1.0 - (over / range), 0.0, 1.0);
            limiter_.throttle(factor);
        } else {
            // Below soft threshold: recover to nominal
            limiter_.recover();
        }
    }

    [[nodiscard]] const EMAOccupancyTracker<Queue>& tracker() const noexcept {
        return tracker_;
    }

private:
    EMAOccupancyTracker<Queue> tracker_;
    TokenBucketRateLimiter&    limiter_;
};

} // namespace klstream
