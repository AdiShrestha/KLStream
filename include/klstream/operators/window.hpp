// include/klstream/operators/window.hpp
#pragma once
#include "../core/operator.hpp"
#include "../core/event.hpp"
#include "../core/spsc_queue.hpp"
#include "../core/metrics.hpp"
#include <functional>
#include <vector>
#include <chrono>
#include <cstddef>
#include <cstdint>

namespace klstream {

// ── TumblingCountWindow<T, Out> ───────────────────────────────────────────
//
// Collects events into a non-overlapping window of fixed size (window_size).
// When the window is full, calls the user's aggregation function to produce
// one Out event and clears the buffer.
//
// Memory: stores up to window_size events in a std::vector (pre-reserved).
// The window fires and emits exactly one Out event per window_size inputs.
//
// Example — window average over every 100 integers:
//   TumblingCountWindow<uint64_t, double> avg_window(
//       "avg_100", &q_in, &q_out, 100,
//       [](const std::vector<uint64_t>& buf) -> double {
//           uint64_t sum = 0;
//           for (auto v : buf) sum += v;
//           return static_cast<double>(sum) / buf.size();
//       });
template <typename T, typename Out>
class TumblingCountWindow : public IOperator {
public:
    using InQueue   = SPSCQueue<Event<T>>;
    using OutQueue  = SPSCQueue<Event<Out>>;
    using AggrFn    = std::function<Out(const std::vector<T>&)>;

    TumblingCountWindow(std::string name,
                        InQueue*    input,
                        OutQueue*   output,
                        std::size_t window_size,
                        AggrFn      aggr)
        : IOperator(std::move(name))
        , input_(input), output_(output)
        , window_size_(window_size), aggr_(std::move(aggr))
    {
        buffer_.reserve(window_size_);
    }

    void attach_metrics(OperatorMetrics* m) { metrics_ = m; }

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

        Event<T> in_ev;
        if (!input_->try_pop(&in_ev)) {
            if (metrics_) metrics_->events_idle.increment();
            return OpStatus::Idle;
        }

        if (buffer_.empty()) {
            window_start_ts_ = in_ev.timestamp_ns; // track for latency
        }
        buffer_.push_back(in_ev.data);

        if (buffer_.size() >= window_size_) {
            Event<Out> out_ev;
            out_ev.timestamp_ns = window_start_ts_;
            out_ev.key          = in_ev.key;
            out_ev.seq          = in_ev.seq;
            out_ev.data         = aggr_(buffer_);
            buffer_.clear();

            if (output_->try_push(out_ev)) {
                if (metrics_) metrics_->events_processed.increment();
                return OpStatus::Processed;
            }
            pending_     = out_ev;
            has_pending_ = true;
            if (metrics_) metrics_->events_blocked.increment();
            return OpStatus::Blocked;
        }

        if (metrics_) metrics_->events_processed.increment();
        return OpStatus::Processed; // buffered, not yet emitted
    }

private:
    InQueue*          input_;
    OutQueue*         output_;
    std::size_t       window_size_;
    AggrFn            aggr_;
    std::vector<T>    buffer_;
    std::uint64_t     window_start_ts_{0};
    Event<Out>        pending_{};
    bool              has_pending_{false};
    OperatorMetrics*  metrics_{nullptr};
};

// ── TumblingTimeWindow<T, Out> ────────────────────────────────────────────
//
// Like TumblingCountWindow but fires every `window_ns` nanoseconds regardless
// of how many events arrived. On each tick() it:
//   1. Checks if the window has expired (now - window_open_time >= window_ns).
//   2. If yes: fires the aggregation, clears the buffer, opens a new window.
//   3. If no: pops and buffers one event (if available), returns Processed.
//
// An empty window (no events arrived in the interval) is not emitted.
//
// Example — 1-second tumbling window summing integers:
//   TumblingTimeWindow<uint64_t, uint64_t> one_sec(
//       "1sec_sum", &q_in, &q_out,
//       std::chrono::seconds(1),
//       [](const std::vector<uint64_t>& v) {
//           uint64_t s = 0; for (auto x : v) s += x; return s; });
template <typename T, typename Out>
class TumblingTimeWindow : public IOperator {
public:
    using InQueue   = SPSCQueue<Event<T>>;
    using OutQueue  = SPSCQueue<Event<Out>>;
    using AggrFn    = std::function<Out(const std::vector<T>&)>;

    TumblingTimeWindow(std::string name,
                       InQueue*    input,
                       OutQueue*   output,
                       std::chrono::nanoseconds window_duration,
                       AggrFn      aggr)
        : IOperator(std::move(name))
        , input_(input), output_(output)
        , window_ns_(window_duration.count())
        , aggr_(std::move(aggr))
    {
        reset_window();
    }

    void attach_metrics(OperatorMetrics* m) { metrics_ = m; }

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

        // Check if the window has expired.
        std::uint64_t now = now_ns();
        if ((now - window_open_ns_) >= static_cast<std::uint64_t>(window_ns_)) {
            if (!buffer_.empty()) {
                Event<Out> out_ev;
                out_ev.timestamp_ns = window_open_ns_;
                out_ev.key          = 0;
                out_ev.seq          = window_count_++;
                out_ev.data         = aggr_(buffer_);
                buffer_.clear();
                reset_window();
                if (output_->try_push(out_ev)) {
                    if (metrics_) metrics_->events_processed.increment();
                    return OpStatus::Processed;
                }
                pending_     = out_ev;
                has_pending_ = true;
                if (metrics_) metrics_->events_blocked.increment();
                return OpStatus::Blocked;
            }
            reset_window();
        }

        // Buffer one event if available.
        Event<T> in_ev;
        if (!input_->try_pop(&in_ev)) {
            if (metrics_) metrics_->events_idle.increment();
            return OpStatus::Idle;
        }
        buffer_.push_back(in_ev.data);
        if (metrics_) metrics_->events_processed.increment();
        return OpStatus::Processed;
    }

private:
    void reset_window() {
        window_open_ns_ = now_ns();
    }

    static std::uint64_t now_ns() {
        using namespace std::chrono;
        return static_cast<std::uint64_t>(
            duration_cast<nanoseconds>(
                steady_clock::now().time_since_epoch()).count());
    }

    InQueue*          input_;
    OutQueue*         output_;
    std::int64_t      window_ns_;
    AggrFn            aggr_;
    std::vector<T>    buffer_;
    std::uint64_t     window_open_ns_{0};
    std::uint64_t     window_count_{0};
    Event<Out>        pending_{};
    bool              has_pending_{false};
    OperatorMetrics*  metrics_{nullptr};
};

} // namespace klstream
