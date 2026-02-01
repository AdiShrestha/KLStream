#pragma once

/**
 * @file metrics.hpp
 * @brief Metrics collection and reporting
 */

#include <atomic>
#include <chrono>
#include <vector>
#include <string>
#include <unordered_map>
#include <mutex>
#include <iostream>
#include <iomanip>
#include <sstream>

namespace klstream {

/**
 * @brief Counter metric (monotonically increasing)
 */
class Counter {
public:
    void increment(std::uint64_t value = 1) noexcept {
        value_.fetch_add(value, std::memory_order_relaxed);
    }
    
    [[nodiscard]] std::uint64_t value() const noexcept {
        return value_.load(std::memory_order_relaxed);
    }
    
    void reset() noexcept {
        value_.store(0, std::memory_order_relaxed);
    }

private:
    std::atomic<std::uint64_t> value_{0};
};

/**
 * @brief Gauge metric (can go up and down)
 */
class Gauge {
public:
    void set(std::int64_t value) noexcept {
        value_.store(value, std::memory_order_relaxed);
    }
    
    void increment(std::int64_t delta = 1) noexcept {
        value_.fetch_add(delta, std::memory_order_relaxed);
    }
    
    void decrement(std::int64_t delta = 1) noexcept {
        value_.fetch_sub(delta, std::memory_order_relaxed);
    }
    
    [[nodiscard]] std::int64_t value() const noexcept {
        return value_.load(std::memory_order_relaxed);
    }

private:
    std::atomic<std::int64_t> value_{0};
};

/**
 * @brief Histogram for latency measurements
 */
class Histogram {
public:
    explicit Histogram(std::vector<double> buckets = default_buckets())
        : buckets_(std::move(buckets))
        , counts_(buckets_.size() + 1, 0) {}
    
    void observe(double value) {
        std::lock_guard<std::mutex> lock(mutex_);
        sum_ += value;
        count_++;
        
        for (std::size_t i = 0; i < buckets_.size(); i++) {
            if (value <= buckets_[i]) {
                counts_[i]++;
                return;
            }
        }
        counts_.back()++;  // +Inf bucket
    }
    
    [[nodiscard]] double sum() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return sum_;
    }
    
    [[nodiscard]] std::uint64_t count() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return count_;
    }
    
    [[nodiscard]] double mean() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return count_ > 0 ? sum_ / static_cast<double>(count_) : 0.0;
    }
    
    static std::vector<double> default_buckets() {
        return {0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0};
    }

private:
    mutable std::mutex mutex_;
    std::vector<double> buckets_;
    std::vector<std::uint64_t> counts_;
    double sum_{0.0};
    std::uint64_t count_{0};
};

/**
 * @brief Runtime metrics snapshot
 */
struct RuntimeMetrics {
    std::uint64_t total_events_processed{0};
    std::uint64_t events_per_second{0};
    double avg_latency_ms{0.0};
    std::size_t total_queue_size{0};
    std::uint64_t backpressure_events{0};
    double cpu_utilization{0.0};
    std::chrono::steady_clock::time_point timestamp;
};

/**
 * @brief Operator-level metrics
 */
struct OperatorMetrics {
    std::string name;
    std::uint64_t events_received{0};
    std::uint64_t events_emitted{0};
    double avg_processing_time_us{0.0};
    std::size_t input_queue_size{0};
};

/**
 * @brief Metrics collector and reporter
 */
class MetricsCollector {
public:
    MetricsCollector() : start_time_(std::chrono::steady_clock::now()) {}
    
    // Global counters
    Counter& events_processed() { return events_processed_; }
    Counter& events_dropped() { return events_dropped_; }
    Counter& backpressure_events() { return backpressure_; }
    
    // Latency histogram
    Histogram& processing_latency() { return latency_; }
    
    // Queue gauges
    Gauge& total_queue_size() { return queue_size_; }
    
    /**
     * @brief Collect current runtime metrics snapshot
     */
    [[nodiscard]] RuntimeMetrics snapshot() const {
        auto now = std::chrono::steady_clock::now();
        auto elapsed = std::chrono::duration_cast<std::chrono::seconds>(
            now - last_snapshot_time_
        ).count();
        
        RuntimeMetrics metrics;
        metrics.timestamp = now;
        metrics.total_events_processed = events_processed_.value();
        metrics.events_per_second = elapsed > 0 
            ? (metrics.total_events_processed - last_events_) / static_cast<uint64_t>(elapsed)
            : 0;
        metrics.avg_latency_ms = latency_.mean() * 1000.0;
        metrics.total_queue_size = static_cast<std::size_t>(queue_size_.value());
        metrics.backpressure_events = backpressure_.value();
        
        last_snapshot_time_ = now;
        last_events_ = metrics.total_events_processed;
        
        return metrics;
    }
    
    /**
     * @brief Format metrics as string
     */
    [[nodiscard]] std::string format() const {
        auto m = snapshot();
        std::ostringstream oss;
        oss << std::fixed << std::setprecision(2);
        oss << "Events: " << m.total_events_processed
            << " | Rate: " << m.events_per_second << " evt/s"
            << " | Latency: " << m.avg_latency_ms << " ms"
            << " | Queue: " << m.total_queue_size
            << " | Backpressure: " << m.backpressure_events;
        return oss.str();
    }
    
    /**
     * @brief Print metrics to stdout
     */
    void print() const {
        std::cout << format() << std::endl;
    }
    
    /**
     * @brief Get uptime
     */
    [[nodiscard]] std::chrono::milliseconds uptime() const {
        return std::chrono::duration_cast<std::chrono::milliseconds>(
            std::chrono::steady_clock::now() - start_time_
        );
    }

private:
    std::chrono::steady_clock::time_point start_time_;
    mutable std::chrono::steady_clock::time_point last_snapshot_time_{std::chrono::steady_clock::now()};
    mutable std::uint64_t last_events_{0};
    
    Counter events_processed_;
    Counter events_dropped_;
    Counter backpressure_;
    Histogram latency_;
    Gauge queue_size_;
};

} // namespace klstream
