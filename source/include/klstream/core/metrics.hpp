#pragma once
#include <klstream/core/config.hpp>
#include <array>
#include <atomic>
#include <cmath>
#include <cstdint>
#include <limits>
#include <mutex>
#include <stdexcept>
#include <string>
#include <utility>

namespace klstream {
struct Counter {
    std::atomic<std::uint64_t> value{0};
    void increment(std::uint64_t n = 1) noexcept { value.fetch_add(n, std::memory_order_relaxed); }
    std::uint64_t load() const noexcept { return value.load(std::memory_order_relaxed); }
    std::uint64_t get() const noexcept { return load(); }
};
struct OperatorMetrics {
    Counter events_processed, events_blocked, events_idle;
    std::string op_name;
    explicit OperatorMetrics(std::string name = {}) : op_name(std::move(name)) {}
};
// Optional diagnostic recorder, not a nanosecond-accurate tail estimator.
// Quantiles are lower bucket bounds in microseconds; overflow returns infinity.
// Record raw timestamps for publication evidence. Lock overhead is observable.
class LatencyHistogram {
public:
    void record(std::uint64_t ns) {
        std::lock_guard<std::mutex> lock(mutex_);
        const auto us = ns / 1000;
        ++buckets_[us < HISTOGRAM_BUCKETS ? us : HISTOGRAM_BUCKETS];
        ++count_; sum_ns_ += static_cast<long double>(ns);
    }
    std::uint64_t count() const { std::lock_guard<std::mutex> lock(mutex_); return count_; }
    double percentile(double p) const {
        if (!std::isfinite(p) || p <= 0 || p > 1) throw std::invalid_argument("Percentile fraction must be in (0,1]");
        std::lock_guard<std::mutex> lock(mutex_);
        if (!count_) throw std::logic_error("No latency observations");
        const auto rank = static_cast<std::uint64_t>(std::ceil(static_cast<long double>(p) * count_));
        std::uint64_t cumulative = 0;
        for (std::size_t i = 0; i < buckets_.size(); ++i) {
            cumulative += buckets_[i];
            if (cumulative >= rank) return i == HISTOGRAM_BUCKETS ? std::numeric_limits<double>::infinity() : static_cast<double>(i);
        }
        throw std::logic_error("Histogram rank inconsistency");
    }
    double mean() const {
        std::lock_guard<std::mutex> lock(mutex_);
        if (!count_) throw std::logic_error("No latency observations");
        return static_cast<double>(sum_ns_ / count_ / 1000); // actual observed mean, us
    }
    double p50() const { return percentile(.5); }
    double p95() const { return percentile(.95); }
    double p99() const { return percentile(.99); }
private:
    mutable std::mutex mutex_;
    std::array<std::uint64_t, HISTOGRAM_BUCKETS + 1> buckets_{};
    std::uint64_t count_{0};
    long double sum_ns_{0};
};
}
