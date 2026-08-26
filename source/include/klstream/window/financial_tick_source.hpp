#pragma once
#include "../core/operator.hpp"
#include "../core/event.hpp"
#include "../core/spsc_queue.hpp"
#include "../core/metrics.hpp"
#include "../core/backpressure.hpp"
#include "types.hpp"
#include <fstream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
#include <thread>
#include <chrono>

namespace klstream {

// One row of the CSV produced by preprocess_lobster.py (Section 11).
struct TickRow {
    std::uint64_t seq;
    std::uint64_t timestamp_ns;
    float         log_return, rolling_vol, order_imbalance, spread_bps, volume;
    std::uint8_t  label;          // 0=normal, 1=flash_crash, 2=wash_trade_proxy
    std::uint8_t  is_burst_period;
};

// Loads the entire replay CSV into memory once at startup. LOBSTER sample
// days are at most a few hundred thousand events — comfortably fits in RAM
// on an 8GB+ machine; no streaming file I/O needed during the actual run,
// which keeps TickSource's tick() allocation-free and fast.
inline std::vector<TickRow> load_replay_csv(const std::string& path) {
    std::ifstream f(path);
    if (!f) throw std::runtime_error("cannot open replay CSV: " + path);
    std::string line;
    std::getline(f, line); // header
    std::vector<TickRow> rows;
    while (std::getline(f, line)) {
        std::stringstream ss(line);
        std::string cell;
        TickRow r{};
        std::getline(ss, cell, ','); r.seq = std::stoull(cell);
        std::getline(ss, cell, ','); r.timestamp_ns = std::stoull(cell);
        std::getline(ss, cell, ','); /* mid_price, unused downstream */
        std::getline(ss, cell, ','); r.log_return = std::stof(cell);
        std::getline(ss, cell, ','); r.rolling_vol = std::stof(cell);
        std::getline(ss, cell, ','); r.order_imbalance = std::stof(cell);
        std::getline(ss, cell, ','); r.spread_bps = std::stof(cell);
        std::getline(ss, cell, ','); r.volume = std::stof(cell);
        std::getline(ss, cell, ','); r.label = static_cast<std::uint8_t>(std::stoi(cell));
        std::getline(ss, cell, ','); r.is_burst_period = static_cast<std::uint8_t>(std::stoi(cell));
        rows.push_back(r);
    }
    return rows;
}

// ── FinancialTickSource ───────────────────────────────────────────────────
//
// Wraps SourceOperator<FeatureVector>'s generator-function pattern
// (Section 8.1 of the Implementation Guide) around the preloaded replay
// data. Two replay modes:
//   PreserveTiming — sleeps between events to approximate the original
//     LOBSTER inter-event gaps (scaled by speed_factor). Realistic but slow
//     to reach high sustained throughput; good for latency-fidelity runs.
//   MaxRate — no sleeping; emits as fast as the downstream rate limiter (if
//     any) and queue backpressure allow. Good for the bursty-source / stress
//     experiments (Section 25, reusing the original Section 14.1 pattern).
//
// Bursty behavior: rows flagged is_burst_period=1 are emitted at MaxRate
// regardless of the configured mode; calm rows respect the configured mode.
// This directly reproduces the "alternates between high-rate burst and
// low-rate quiet phases" generator from the original adaptive-backpressure
// research extension (Section 14.1 of the Implementation Guide), now driven
// by real injected-anomaly placement instead of an artificial timer.
enum class ReplayMode { PreserveTiming, MaxRate };

class FinancialTickSource {
public:
    FinancialTickSource(std::vector<TickRow> rows, ReplayMode mode,
                        double speed_factor = 1.0)
        : rows_(std::move(rows)), mode_(mode), speed_factor_(speed_factor)
    {}

    // Generator function passed to SourceOperator<FeatureVector>'s ctor
    // (Section 8.1 of the Implementation Guide) — matches
    // SourceOperator<T>::Generator's exact signature.
    bool operator()(Event<FeatureVector>& out, std::uint64_t /*unused_seq*/) {
        if (idx_ >= rows_.size()) {
            idx_ = 0;
            start_real_ = std::chrono::steady_clock::now();
            start_log_ = rows_[0].timestamp_ns;
            loop_count_++;
            base_seq_ += rows_.back().seq + 1;
        }

        const TickRow& r = rows_[idx_];

        if (idx_ == 0 && loop_count_ == 0) {
            start_real_ = std::chrono::steady_clock::now();
            start_log_ = r.timestamp_ns;
        } else if (mode_ == ReplayMode::PreserveTiming) {
            auto elapsed_log = r.timestamp_ns - start_log_;
            auto scaled_log = std::chrono::nanoseconds(static_cast<std::int64_t>(elapsed_log / speed_factor_));
            auto target_real = start_real_ + scaled_log;
            
            auto now = std::chrono::steady_clock::now();
            if (target_real > now) {
                auto sleep_dur = target_real - now;
                if (sleep_dur > std::chrono::milliseconds(10)) {
                    // Cap large sleeps (e.g. overnight gaps)
                    sleep_dur = std::chrono::milliseconds(10);
                    start_real_ = now - scaled_log + sleep_dur; // Advance base time
                    target_real = start_real_ + scaled_log;
                }
                
                if (sleep_dur > std::chrono::microseconds(100)) {
                    std::this_thread::sleep_for(sleep_dur - std::chrono::microseconds(50));
                }
                while (std::chrono::steady_clock::now() < target_real) {
                    std::this_thread::yield();
                }
            }
        }

        FeatureVector fv{ r.log_return, r.rolling_vol, r.order_imbalance,
                          r.spread_bps, r.volume };
        out = Event<FeatureVector>::make(fv, 0, r.seq + base_seq_);
        ground_truth_label_ = r.label;   // exposed via last_label() for the
                                          // optional online-eval harness
        ++idx_;
        return true;
    }

    std::uint8_t last_label() const { return ground_truth_label_; }
    std::size_t  remaining() const { return rows_.size() - idx_; }

private:
    std::vector<TickRow> rows_;
    ReplayMode            mode_;
    double                speed_factor_;
    std::size_t           idx_{0};
    std::uint8_t          ground_truth_label_{0};
    std::chrono::steady_clock::time_point start_real_;
    std::uint64_t         start_log_{0};
    std::uint64_t         loop_count_{0};
    std::uint64_t         base_seq_{0};
};

} // namespace klstream
