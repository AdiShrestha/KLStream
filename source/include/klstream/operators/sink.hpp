#pragma once
#include <klstream/core/operator.hpp>
#include <klstream/core/event.hpp>
#include <klstream/core/spsc_queue.hpp>
#include <klstream/core/metrics.hpp>
#include <functional>
#include <stdexcept>
#include <utility>

#include <cstdint>

namespace klstream {

// ── SinkOperator<T> ───────────────────────────────────────────────────────
//
// Terminal operator. Pops events from its input queue and hands them to the
// user-supplied consumer function. Has no output queue.
//
// The consumer function receives the full Event<T> (not just the payload)
// so it has access to timestamp_ns for latency measurement.
//
// Example:
//   SinkOperator<uint64_t> printer(
//       "printer", &q_in,
//       [&hist](const Event<uint64_t>& ev) {
//           hist.record(ev.latency_ns()); });
template <typename T>
class SinkOperator : public IOperator {
public:
    using Queue      = SPSCQueue<Event<T>>;
    using ConsumerFn = std::function<void(const Event<T>&)>;

    SinkOperator(std::string name, Queue* input, ConsumerFn consumer)
        : IOperator(std::move(name))
        , input_(input)
        , consumer_(std::move(consumer))
    { if (!input_ || !consumer_) throw std::invalid_argument("SinkOperator requires input and consumer"); }

    void attach_metrics(OperatorMetrics* m) override { metrics_ = m; }

    OpStatus tick() override {
        if (input_->is_cancelled()) throw std::runtime_error("Input cancelled; EOS was not reached");
        Event<T> ev;
        if (!input_->try_pop(&ev)) {
            if (input_->is_drained()) return OpStatus::Finished;
            if (metrics_) metrics_->events_idle.increment();
            return OpStatus::Idle;
        }
        consumer_(ev);
        if (metrics_) metrics_->events_processed.increment();
        return OpStatus::Processed;
    }

private:
    Queue*           input_;
    ConsumerFn       consumer_;
    OperatorMetrics* metrics_{nullptr};
};

} // namespace klstream
