// include/klstream/operators/filter.hpp
#pragma once
#include "../core/operator.hpp"
#include "../core/event.hpp"
#include "../core/spsc_queue.hpp"
#include "../core/metrics.hpp"
#include <functional>

namespace klstream {

// ── FilterOperator<T> ─────────────────────────────────────────────────────
//
// Stateless selective pass-through. Pops one Event<T> from input. If the
// predicate returns true, pushes it to output unchanged. If false, the event
// is dropped (this is one of the few operators that intentionally discards
// events — it is correct by design, not a data-loss bug).
//
// Example:
//   FilterOperator<uint64_t> even_only(
//       "even_filter", &q_in, &q_out,
//       [](uint64_t x) { return x % 2 == 0; });
template <typename T>
class FilterOperator : public IOperator {
public:
    using Queue     = SPSCQueue<Event<T>>;
    using Predicate = std::function<bool(const T&)>;

    FilterOperator(std::string name, Queue* input, Queue* output, Predicate pred)
        : IOperator(std::move(name))
        , input_(input), output_(output), pred_(std::move(pred))
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

        Event<T> ev;
        if (!input_->try_pop(&ev)) {
            if (metrics_) metrics_->events_idle.increment();
            return OpStatus::Idle;
        }

        if (!pred_(ev.data)) {
            // Filtered out — count as processed (we consumed it) but don't push.
            if (metrics_) metrics_->events_processed.increment();
            return OpStatus::Processed;
        }

        if (output_->try_push(ev)) {
            if (metrics_) metrics_->events_processed.increment();
            return OpStatus::Processed;
        }

        pending_     = ev;
        has_pending_ = true;
        if (metrics_) metrics_->events_blocked.increment();
        return OpStatus::Blocked;
    }

private:
    Queue*           input_;
    Queue*           output_;
    Predicate        pred_;
    Event<T>         pending_{};
    bool             has_pending_{false};
    OperatorMetrics* metrics_{nullptr};
};

} // namespace klstream
