#pragma once
#include <klstream/core/config.hpp>
#include <atomic>
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>
#include <chrono>
#include <thread>
#include <iostream>
#include <iomanip>
#include <algorithm>


namespace klstream {

// ── Counter ───────────────────────────────────────────────────────────────
//
// A cache-line-aligned atomic counter for counting events.
// Thread-safe and non-destructive: reads do not mutate cumulative totals.

struct Counter {
    alignas(CACHE_LINE_SIZE) std::atomic<std::uint64_t> value{0};

    Counter() = default;
    explicit Counter(std::uint64_t init_val) : value(init_val) {}

    void increment(std::uint64_t n = 1) noexcept {
        value.fetch_add(n, std::memory_order_relaxed);
    }

    [[nodiscard]] std::uint64_t load() const noexcept {
        return value.load(std::memory_order_relaxed);
    }

    [[nodiscard]] std::uint64_t get() const noexcept {
        return load();
    }

    void reset() noexcept {
        value.store(0, std::memory_order_relaxed);
    }
};

// ── LatencyHistogram ──────────────────────────────────────────────────────
//
// A fixed-width histogram for end-to-end latency in microseconds.
// Bucket index = latency_us = latency_ns / 1000.
// Values exceeding MAX_LATENCY_US fall into the overflow bucket (index HISTOGRAM_BUCKETS).

struct LatencyHistogram {
    static constexpr std::size_t NUM_BUCKETS = HISTOGRAM_BUCKETS + 1;
    std::array<std::atomic<std::uint64_t>, NUM_BUCKETS> buckets{};

    LatencyHistogram() {
        for (auto& b : buckets) b.store(0, std::memory_order_relaxed);
    }

    void record(std::uint64_t latency_ns) noexcept {
        std::size_t idx = latency_ns / 1000; // convert ns -> us
        if (idx >= HISTOGRAM_BUCKETS) idx = HISTOGRAM_BUCKETS; // overflow
        buckets[idx].fetch_add(1, std::memory_order_relaxed);
    }

    void record_us(std::uint64_t latency_us) noexcept {
        std::size_t idx = (latency_us >= HISTOGRAM_BUCKETS) ? HISTOGRAM_BUCKETS : latency_us;
        buckets[idx].fetch_add(1, std::memory_order_relaxed);
    }

    [[nodiscard]] std::uint64_t count() const noexcept {
        std::uint64_t total = 0;
        for (const auto& b : buckets) {
            total += b.load(std::memory_order_relaxed);
        }
        return total;
    }

    // Returns the exact percentile latency in microseconds using rank-based nearest-rank method.
    // pct is in [0.0, 1.0] (e.g. 0.95 for P95).
    [[nodiscard]] double percentile(double pct) const noexcept {
        std::uint64_t total = count();
        if (total == 0) return 0.0;

        double clamped_pct = std::clamp(pct, 0.0, 1.0);
        std::uint64_t target = static_cast<std::uint64_t>(std::ceil(clamped_pct * static_cast<double>(total)));
        if (target == 0) target = 1;

        std::uint64_t cumulative = 0;
        for (std::size_t i = 0; i < NUM_BUCKETS; ++i) {
            cumulative += buckets[i].load(std::memory_order_relaxed);
            if (cumulative >= target) {
                return static_cast<double>(i);
            }
        }
        return static_cast<double>(MAX_LATENCY_US);
    }

    [[nodiscard]] double p50() const noexcept { return percentile(0.50); }
    [[nodiscard]] double p90() const noexcept { return percentile(0.90); }
    [[nodiscard]] double p95() const noexcept { return percentile(0.95); }
    [[nodiscard]] double p99() const noexcept { return percentile(0.99); }

    [[nodiscard]] double mean() const noexcept {
        std::uint64_t total_samples = 0;
        double sum_us = 0.0;
        for (std::size_t i = 0; i < NUM_BUCKETS; ++i) {
            std::uint64_t c = buckets[i].load(std::memory_order_relaxed);
            total_samples += c;
            sum_us += static_cast<double>(i * c);
        }
        if (total_samples == 0) return 0.0;
        return sum_us / static_cast<double>(total_samples);
    }

    void reset() noexcept {
        for (auto& b : buckets) b.store(0, std::memory_order_relaxed);
    }
};

// ── OperatorMetrics ───────────────────────────────────────────────────────
struct OperatorMetrics {
    Counter events_processed;
    Counter events_blocked;
    Counter events_idle;
    std::string op_name;

    OperatorMetrics() = default;
    explicit OperatorMetrics(std::string name) : op_name(std::move(name)) {}
};

// ── MetricsReporter ───────────────────────────────────────────────────────
class MetricsReporter {
public:
    struct Entry {
        OperatorMetrics* metrics;
        std::uint64_t    last_processed{0};
        std::uint64_t    last_blocked{0};
        std::uint64_t    last_idle{0};
    };

    void add(OperatorMetrics* m) {
        if (m) entries_.push_back(Entry{m, m->events_processed.load(), m->events_blocked.load(), m->events_idle.load()});
    }

    void start() {
        running_.store(true, std::memory_order_release);
        thread_ = std::thread([this]{ run(); });
    }

    void stop() {
        running_.store(false, std::memory_order_release);
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
             << setw(12) << "Idle/sec"
             << setw(16) << "Total Processed" << "\n";
        cout << string(80, '-') << "\n";
        for (auto& entry : entries_) {
            if (!entry.metrics) continue;
            uint64_t cur_p = entry.metrics->events_processed.load();
            uint64_t cur_b = entry.metrics->events_blocked.load();
            uint64_t cur_i = entry.metrics->events_idle.load();

            uint64_t rate_p = (cur_p >= entry.last_processed) ? (cur_p - entry.last_processed) : 0;
            uint64_t rate_b = (cur_b >= entry.last_blocked) ? (cur_b - entry.last_blocked) : 0;
            uint64_t rate_i = (cur_i >= entry.last_idle) ? (cur_i - entry.last_idle) : 0;

            entry.last_processed = cur_p;
            entry.last_blocked = cur_b;
            entry.last_idle = cur_i;

            cout << setw(22) << entry.metrics->op_name
                 << setw(16) << rate_p
                 << setw(14) << rate_b
                 << setw(12) << rate_i
                 << setw(16) << cur_p
                 << "\n";
        }
        cout << flush;
    }

    std::vector<Entry> entries_;
    std::atomic<bool>  running_{false};
    std::thread        thread_;
};

} // namespace klstream
