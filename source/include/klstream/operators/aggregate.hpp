// include/klstream/operators/aggregate.hpp
#pragma once
#include "../core/operator.hpp"
#include "../core/event.hpp"
#include "../core/spsc_queue.hpp"
#include "../core/metrics.hpp"
#include <functional>

namespace klstream {

// ── AggregateOperator<In, State, Out> ────────────────────────────────────
//
// Stateful incremental aggregation. Maintains an internal `State` and
// calls user-supplied functions for accumulation and extraction.
//
// This is NOT windowed — it maintains a running aggregate over all events
// seen so far (e.g., a running sum, count, or max). For windowed
// aggregation use TumblingCountWindow (Section 8.5) or TumblingTimeWindow
// (Section 8.6).
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
    {}

    void attach_metrics(OperatorMetrics* m) override { metrics_ = m; }

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

        Event<In> in_ev;
        if (!input_->try_pop(&in_ev)) {
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

private:
    InQueue*         input_;
    OutQueue*        output_;
    State            state_;
    AccumFn          accum_;
    ExtractFn        extract_;
    Event<Out>       pending_{};
    bool             has_pending_{false};
    OperatorMetrics* metrics_{nullptr};
};

} // namespace klstream
