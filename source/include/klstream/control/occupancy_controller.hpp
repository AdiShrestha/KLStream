#pragma once
#include <algorithm>
#include <cmath>
#include <cstddef>
#include <stdexcept>

namespace klstream {
enum class FeedbackDirection { GrowUnderPressure, ShrinkUnderPressure };
// Explicit policy choice, no presumed optimal direction or stability claim.
// This object is owned by one operator thread. Telemetry must be published
// through a synchronized snapshot, not read concurrently from these fields.
class OccupancyBatchController {
public:
    OccupancyBatchController(std::size_t minimum, std::size_t maximum, std::size_t initial,
                             double alpha, double low, double high, double shrink,
                             double grow, FeedbackDirection direction)
        : min_(minimum), max_(maximum), current_(initial), alpha_(alpha), low_(low), high_(high),
          shrink_(shrink), grow_(grow), direction_(direction) {
        if (!min_ || min_ > max_ || initial < min_ || initial > max_ ||
            !std::isfinite(alpha) || alpha <= 0 || alpha > 1 ||
            !std::isfinite(low) || !std::isfinite(high) || low < 0 || high > 1 || low >= high ||
            !std::isfinite(shrink) || shrink <= 0 || shrink >= 1 || !std::isfinite(grow) || grow <= 1 ||
            (direction != FeedbackDirection::GrowUnderPressure && direction != FeedbackDirection::ShrinkUnderPressure))
            throw std::invalid_argument("Invalid occupancy controller configuration");
    }
    std::size_t update(double occupancy) {
        if (!std::isfinite(occupancy) || occupancy < 0 || occupancy > 1) throw std::invalid_argument("Invalid occupancy observation");
        ema_ = initialized_ ? alpha_ * occupancy + (1 - alpha_) * ema_ : occupancy;
        initialized_ = true;
        const bool high = ema_ > high_, low = ema_ < low_;
        if (!high && !low) return current_;
        const bool grow = direction_ == FeedbackDirection::GrowUnderPressure ? high : low;
        const long double candidate = grow ? std::ceil(static_cast<long double>(current_) * grow_) : std::floor(static_cast<long double>(current_) * shrink_);
        if (candidate >= static_cast<long double>(max_)) current_ = max_;
        else if (candidate <= static_cast<long double>(min_)) current_ = min_;
        else current_ = static_cast<std::size_t>(candidate);
        return current_;
    }
    std::size_t current() const noexcept { return current_; }
    double ema() const noexcept { return ema_; }
private:
    std::size_t min_, max_, current_;
    double alpha_, low_, high_, shrink_, grow_, ema_{0};
    FeedbackDirection direction_; bool initialized_{false};
};
}
