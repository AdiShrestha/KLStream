// include/klstream/operators/map.hpp
#pragma once
#include "../core/operator.hpp"
#include "../core/event.hpp"
#include "../core/spsc_queue.hpp"
#include "../core/metrics.hpp"
#include <functional>

namespace klstream {

// ── MapOperator<In, Out> ─────────────────────────────────────────────────
//
// Stateless 1-to-1 transform. Pops one Event<In> from the input queue,
// applies the user function to the payload, and pushes one Event<Out>
// to the output queue. Metadata (timestamp_ns, key, seq) is forwarded
// unchanged so latency measurement is accurate end-to-end.
//
// Example:
//   MapOperator<uint64_t, uint64_t> squarer(
//       "squarer",
//       &q_in, &q_out,
//       [](uint64_t x) -> uint64_t { return x * x; });
template <typename In, typename Out>
class MapOperator : public IOperator {
public:
    using InQueue  = SPSCQueue<Event<In>>;
    using OutQueue = SPSCQueue<Event<Out>>;
    using Fn       = std::function<Out(const In&)>;

    MapOperator(std::string name, InQueue* input, OutQueue* output, Fn fn)
        : IOperator(std::move(name))
        , input_(input), output_(output), fn_(std::move(fn))
    {}

    void attach_metrics(OperatorMetrics* m) override { metrics_ = m; }

    OpStatus tick() override {
        // If we have a pending output from a previous Blocked tick, try again.
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

        Event<Out> out_ev;
        out_ev.timestamp_ns = in_ev.timestamp_ns; // forward original timestamp
        out_ev.key          = in_ev.key;
        out_ev.seq          = in_ev.seq;
        out_ev.data         = fn_(in_ev.data);

        if (output_->try_push(out_ev)) {
            if (metrics_) metrics_->events_processed.increment();
            return OpStatus::Processed;
        }

        pending_     = out_ev;
        has_pending_ = true;
        // Put in_ev back? No — we have already consumed it. The pending_
        // slot holds the computed output. We never re-run fn_ on the same input.
        if (metrics_) metrics_->events_blocked.increment();
        return OpStatus::Blocked;
    }

private:
    InQueue*          input_;
    OutQueue*         output_;
    Fn                fn_;
    Event<Out>        pending_{};
    bool              has_pending_{false};
    OperatorMetrics*  metrics_{nullptr};
};

} // namespace klstream
