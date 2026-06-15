// include/klstream/core/metrics.hpp
#pragma once
#include "config.hpp"
#include <atomic>
#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>
#include <chrono>
#include <iostream>
#include <iomanip>

namespace klstream {

// ── Counter ───────────────────────────────────────────────────────────────
//
// A cache-line-aligned atomic counter for counting events.
// Each operator has one Counter for events_processed and one for
// events_blocked (backpressure occurrences).
//
// memory_order_relaxed is used everywhere because:
//   a) We only care about approximate throughput, not exact synchronisation.
//   b) Relaxed atomics do not generate memory fence instructions on ARM,
//      so they cost essentially nothing in the hot path.
//   c) We snapshot counters from a reporter thread using relaxed loads,
//      which is fine because we only need "recent" values, not "exact" values.
struct Counter {
    alignas(CACHE_LINE_SIZE) std::atomic<std::uint64_t> value{0};

    void increment() noexcept {
        value.fetch_add(1, std::memory_order_relaxed);
    }

    std::uint64_t load() const noexcept {
        return value.load(std::memory_order_relaxed);
    }

    // Atomically reset and return the old value (used by the reporter to
    // compute per-interval throughput without cumulative growth).
    std::uint64_t reset() noexcept {
        return value.exchange(0, std::memory_order_relaxed);
    }
};

// ── LatencyHistogram ──────────────────────────────────────────────────────
//
// A fixed-width histogram for end-to-end latency. Each bucket covers 1 us.
// Bucket index = latency_us = latency_ns / 1000.
// Values beyond MAX_LATENCY_US go into an overflow bucket.
//
// Not lock-free: uses a single compare_exchange_weak per record. Suitable
// for the sink operator (single consumer thread increments buckets).
// If multiple sinks need to share a histogram, protect with a mutex or
// use per-thread histograms merged periodically.
struct LatencyHistogram {
    std::array<std::atomic<std::uint64_t>, HISTOGRAM_BUCKETS + 1> buckets{};

    LatencyHistogram() {
        for (auto& b : buckets) b.store(0, std::memory_order_relaxed);
    }

    void record(std::uint64_t latency_ns) noexcept {
        std::size_t idx = latency_ns / 1000; // convert ns -> us
        if (idx >= HISTOGRAM_BUCKETS) idx = HISTOGRAM_BUCKETS; // overflow
        buckets[idx].fetch_add(1, std::memory_order_relaxed);
    }

    // Returns the latency_us value below which `pct` fraction of events fall.
    // E.g., percentile(0.99) returns p99 latency in microseconds.
    double percentile(double pct) const noexcept {
        std::uint64_t total = 0;
        for (const auto& b : buckets)
            total += b.load(std::memory_order_relaxed);
        if (total == 0) return 0.0;
        const std::uint64_t target = static_cast<std::uint64_t>(pct * total);
        std::uint64_t cumulative = 0;
        for (std::size_t i = 0; i < HISTOGRAM_BUCKETS; ++i) {
            cumulative += buckets[i].load(std::memory_order_relaxed);
            if (cumulative >= target) return static_cast<double>(i);
        }
        return static_cast<double>(MAX_LATENCY_US); // overflow bucket
    }
};

// ── OperatorMetrics ───────────────────────────────────────────────────────
//
// One per operator instance. Attached to the operator at construction and
// read by the MetricsReporter thread.
struct OperatorMetrics {
    Counter events_processed;   // successfully processed events
    Counter events_blocked;     // tick() returned Blocked (backpressure)
    Counter events_idle;        // tick() returned Idle (no input)
    std::string op_name;        // set at construction, never modified after

    OperatorMetrics() = default;
    explicit OperatorMetrics(std::string name) : op_name(std::move(name)) {}
};

// ── MetricsReporter ───────────────────────────────────────────────────────
//
// Runs on its own background std::thread. Every METRICS_INTERVAL_SEC seconds
// it samples all registered OperatorMetrics instances and prints a summary
// table to stdout.
//
// To use: create one MetricsReporter, call add(metrics_ptr) for each operator,
// then call start(). Call stop() on shutdown.
class MetricsReporter {
public:
    void add(OperatorMetrics* m) { entries_.push_back(m); }

    void start() {
        running_.store(true);
        thread_ = std::thread([this]{ run(); });
    }

    void stop() {
        running_.store(false);
        if (thread_.joinable()) thread_.join();
    }

    ~MetricsReporter() { stop(); }

private:
    void run() {
        while (running_.load(std::memory_order_relaxed)) {
            std::this_thread::sleep_for(
                std::chrono::seconds(METRICS_INTERVAL_SEC));
            print();
        }
    }

    void print() {
        using namespace std;
        cout << "\n── KLStream Metrics ─────────────────────────────────\n";
        cout << left
             << setw(22) << "Operator"
             << setw(16) << "Events/sec"
             << setw(14) << "Blocked/sec"
             << setw(12) << "Idle/sec" << "\n";
        cout << string(64, '-') << "\n";
        for (auto* m : entries_) {
            cout << setw(22) << m->op_name
                 << setw(16) << m->events_processed.reset()
                 << setw(14) << m->events_blocked.reset()
                 << setw(12) << m->events_idle.reset()
                 << "\n";
        }
        cout << flush;
    }

    std::vector<OperatorMetrics*> entries_;
    std::atomic<bool>             running_{false};
    std::thread                   thread_;
};

} // namespace klstream
