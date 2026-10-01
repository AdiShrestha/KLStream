#pragma once
#include <klstream/core/config.hpp>
#include <algorithm>
#include <atomic>
#include <chrono>
#include <cmath>
#include <mutex>
#include <stdexcept>

namespace klstream {
// Single-owner feedback tracker. Initial EMA is the first observed occupancy;
// observations must be finite fractions. Thresholds are declared policy parameters.
template <typename Queue> class EMAOccupancyTracker {
public:
    explicit EMAOccupancyTracker(Queue& queue, double alpha = .10,
                                 double soft = BP_SOFT_THRESHOLD, double hard = BP_HARD_THRESHOLD)
        : queue_(queue), alpha_(alpha), soft_(soft), hard_(hard) {
        if (!std::isfinite(alpha) || alpha <= 0 || alpha > 1 ||
            !std::isfinite(soft) || !std::isfinite(hard) || soft < 0 || soft >= hard || hard > 1)
            throw std::invalid_argument("Invalid EMA/pressure policy");
    }
    void update() {
        const double occ = queue_.occupancy();
        if (!std::isfinite(occ) || occ < 0 || occ > 1) throw std::domain_error("Invalid queue occupancy");
        raw_ = occ;
        ema_ = initialized_ ? alpha_ * occ + (1 - alpha_) * ema_ : occ;
        initialized_ = true;
    }
    double ema() const noexcept { return ema_; }
    double raw() const noexcept { return raw_; }
    double soft_threshold() const noexcept { return soft_; }
    double hard_threshold() const noexcept { return hard_; }
    bool soft_pressure() const noexcept { return initialized_ && ema_ > soft_; }
    bool hard_pressure() const noexcept { return initialized_ && raw_ > hard_; }
    void reset() noexcept { initialized_ = false; ema_ = raw_ = 0; }
private:
    Queue& queue_; double alpha_, soft_, hard_, ema_{0}, raw_{0}; bool initialized_{false};
};

// Thread-safe accounting. A rate change first credits elapsed time at the OLD
// rate. The initial burst is an explicit policy choice, not a throughput result.
// The positive floor prevents a zero-rate configuration; it is no liveness proof.
class TokenBucketRateLimiter {
public:
    using Clock = std::chrono::steady_clock;
    explicit TokenBucketRateLimiter(double rate, double burst = 0, double floor = 0,
                                    Clock::time_point initial = Clock::now())
        : nominal_rate_(rate), effective_rate_(rate),
          min_rate_(floor == 0 ? std::min(1.0, rate) : floor),
          tokens_(burst > 0 ? burst : std::max(1.0, rate)), max_tokens_(tokens_), last_(initial) {
        if (!std::isfinite(rate) || rate <= 0 || !std::isfinite(burst) || burst < 0 ||
            max_tokens_ < 1 || !std::isfinite(floor) || floor < 0 || min_rate_ > rate)
            throw std::invalid_argument("Invalid token bucket rate, burst or floor");
    }
    bool try_consume() {
        std::lock_guard<std::mutex> lock(mutex_);
        return consume(Clock::now());
    }
    // Simulated calls must share one monotone clock domain with construction.
    bool try_consume_at(Clock::time_point now) {
        std::lock_guard<std::mutex> lock(mutex_); return consume(now);
    }
    void set_rate(double rate) {
        validate_rate(rate);
        std::lock_guard<std::mutex> lock(mutex_); change_rate(rate, Clock::now());
    }
    void set_rate_at(double rate, Clock::time_point now) {
        validate_rate(rate);
        std::lock_guard<std::mutex> lock(mutex_); change_rate(rate, now);
    }
    void throttle(double factor) {
        if (!std::isfinite(factor) || factor < 0 || factor > 1) throw std::invalid_argument("Throttle factor outside [0,1]");
        set_rate(nominal_rate_ * factor);
    }
    void recover() { set_rate(nominal_rate_); }
    double rate() const noexcept { return effective_rate_.load(std::memory_order_relaxed); }
    double effective_rate() const noexcept { return rate(); }
    double nominal_rate() const noexcept { return nominal_rate_; }
    double min_rate() const noexcept { return min_rate_; }
private:
    static void validate_rate(double rate) {
        if (!std::isfinite(rate) || rate < 0) throw std::invalid_argument("Invalid token rate");
    }
    void refill(Clock::time_point now) {
        if (now < last_) throw std::domain_error("Token accounting clock moved backwards");
        // Convert before subtraction: extreme valid time points must not overflow
        // the clock's signed integer duration representation.
        using Period = Clock::duration::period;
        const long double elapsed = (static_cast<long double>(now.time_since_epoch().count()) -
            static_cast<long double>(last_.time_since_epoch().count())) * Period::num / Period::den;
        const long double credit = elapsed * rate();
        tokens_ = static_cast<double>(std::min(static_cast<long double>(max_tokens_),
                                            static_cast<long double>(tokens_) + credit));
        last_ = now;
    }
    bool consume(Clock::time_point now) {
        refill(now); if (tokens_ < 1) return false; tokens_ -= 1; return true;
    }
    void change_rate(double rate, Clock::time_point now) {
        refill(now); effective_rate_.store(std::clamp(rate, min_rate_, nominal_rate_), std::memory_order_relaxed);
    }
    const double nominal_rate_; std::atomic<double> effective_rate_; const double min_rate_;
    double tokens_; const double max_tokens_; Clock::time_point last_; std::mutex mutex_;
};

template <typename Queue> class BackpressureController {
public:
    BackpressureController(Queue& queue, TokenBucketRateLimiter& limiter, double alpha = .10,
                           double soft = BP_SOFT_THRESHOLD, double hard = BP_HARD_THRESHOLD)
        : tracker_(queue, alpha, soft, hard), limiter_(limiter) {}
    void update() {
        tracker_.update();
        if (tracker_.hard_pressure()) limiter_.set_rate(limiter_.min_rate());
        else if (tracker_.soft_pressure()) {
            const double factor = std::clamp(1 - (tracker_.ema() - tracker_.soft_threshold()) /
                (tracker_.hard_threshold() - tracker_.soft_threshold()), 0.0, 1.0);
            limiter_.throttle(factor);
        } else limiter_.recover();
    }
    const EMAOccupancyTracker<Queue>& tracker() const noexcept { return tracker_; }
private:
    EMAOccupancyTracker<Queue> tracker_; TokenBucketRateLimiter& limiter_;
};
}
