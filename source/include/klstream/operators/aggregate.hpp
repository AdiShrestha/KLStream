#pragma once
#include <klstream/core/operator.hpp>
#include <klstream/core/event.hpp>
#include <klstream/core/spsc_queue.hpp>
#include <klstream/core/metrics.hpp>
#include <functional>
#include <stdexcept>
#include <utility>


namespace klstream {

// ── AggregateOperator<In, State, Out> ────────────────────────────────────
//
// Stateful incremental aggregation. Maintains an internal `State` and
// calls user-supplied functions for accumulation and extraction.
//
// This is NOT windowed — it maintains a running aggregate over all events
// seen so far (e.g., a running sum, count, or max). For windowed
// aggregation use TumblingCountWindow. State is shared across keys; keyed
// aggregation requires a separate implementation.
//
// Example — running sum:
//   AggregateOperator<uint64_t, uint64_t, uint64_t> summer(
//       "summer", &q_in, &q_out,
//       0ULL,                                   // initial state
//       [](uint64_t& st, uint64_t x){ st += x; },  // accumulate
//       [](const uint64_t& st){ return st; });      // extract
template <typename In, typename State, typename Out>
class AggregateOperator : public IOperator {
public:
    using InQueue    = SPSCQueue<Event<In>>;
    using OutQueue   = SPSCQueue<Event<Out>>;
    using AccumFn    = std::function<void(State&, const In&)>;
    using ExtractFn  = std::function<Out(const State&)>;

    AggregateOperator(std::string name,
                      InQueue*   input,
                      OutQueue*  output,
                      State      init_state,
                      AccumFn    accum,
                      ExtractFn  extract)
        : IOperator(std::move(name))
        , input_(input), output_(output)
        , state_(std::move(init_state))
        , accum_(std::move(accum))
        , extract_(std::move(extract))
    { if (!input_ || !output_ || !accum_ || !extract_) throw std::invalid_argument("AggregateOperator requires queues and callbacks"); }

    void attach_metrics(OperatorMetrics* m) override { metrics_ = m; }

    OpStatus tick() override {
        if (input_->is_cancelled()) {
            if (has_pending_) { ++dropped_count_; has_pending_ = false; }
            throw std::runtime_error("Input cancelled; EOS was not reached");
        }
        if (!output_->is_running()) {
            if (has_pending_) { ++dropped_count_; has_pending_ = false; }
            throw std::runtime_error("Output closed or cancelled before operator completion");
        }
        if (has_pending_) {
            if (output_->try_push(pending_)) {
                has_pending_ = false;
                if (metrics_) metrics_->events_processed.increment();
                return OpStatus::Processed;
            }
            if (metrics_) metrics_->events_blocked.increment();
            return OpStatus::Blocked;
        }

        Event<In> in_ev;
        if (!input_->try_pop(&in_ev)) {
            if (input_->is_drained()) { output_->close(); return OpStatus::Finished; }
            if (metrics_) metrics_->events_idle.increment();
            return OpStatus::Idle;
        }

        accum_(state_, in_ev.data);

        Event<Out> out_ev;
        out_ev.timestamp_ns = in_ev.timestamp_ns;
        out_ev.key          = in_ev.key;
        out_ev.seq          = in_ev.seq;
        out_ev.data         = extract_(state_);

        if (output_->try_push(out_ev)) {
            if (metrics_) metrics_->events_processed.increment();
            return OpStatus::Processed;
        }

        pending_     = out_ev;
        has_pending_ = true;
        if (metrics_) metrics_->events_blocked.increment();
        return OpStatus::Blocked;
    }

    void shutdown() override {
        if (has_pending_) { ++dropped_count_; has_pending_ = false; }
    }
    [[nodiscard]] std::size_t dropped_count() const noexcept { return dropped_count_; }
    [[nodiscard]] std::size_t aborted_count() const noexcept { return dropped_count_; }

private:
    InQueue*         input_;
    OutQueue*        output_;
    State            state_;
    AccumFn          accum_;
    ExtractFn        extract_;
    Event<Out>       pending_{};
    bool             has_pending_{false};
    std::size_t       dropped_count_{0};
    OperatorMetrics* metrics_{nullptr};
};

} // namespace klstream
