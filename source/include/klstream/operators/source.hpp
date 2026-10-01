#pragma once
#include <klstream/core/operator.hpp>
#include <klstream/core/event.hpp>
#include <klstream/core/spsc_queue.hpp>
#include <klstream/core/metrics.hpp>
#include <klstream/core/backpressure.hpp>
#include <atomic>
#include <functional>
#include <memory>
#include <stdexcept>
#include <limits>

namespace klstream {
// A false generator return means permanent EOS. Callbacks must not block
// indefinitely. Queue, callbacks and attached metrics outlive the Runtime.
template <typename T> class SourceOperator : public IOperator {
public:
    using Queue = SPSCQueue<Event<T>>;
    using Generator = std::function<bool(Event<T>&, std::uint64_t)>;
    SourceOperator(std::string name, Queue* output, Generator generator)
        : IOperator(std::move(name)), output_(output), generator_(std::move(generator)) {
        if (!output_ || !generator_) throw std::invalid_argument("Source requires output and generator");
    }
    void enable_rate_limiting(double rate) {
        limiter_ = std::make_unique<TokenBucketRateLimiter>(rate);
    }
    void attach_metrics(OperatorMetrics* m) override { metrics_ = m; }
    void request_finish() noexcept override { finish_.store(true, std::memory_order_release); }
    OpStatus tick() override {
        if (!output_->is_running()) throw std::runtime_error("Output closed or cancelled before operator completion");
        // A token was consumed on generation; a retry never consumes another.
        if (has_pending_) {
            if (!output_->try_push(pending_)) { if (metrics_) metrics_->events_blocked.increment(); return OpStatus::Blocked; }
            has_pending_ = false;
            if (metrics_) metrics_->events_processed.increment();
            return OpStatus::Processed;
        }
        if (finish_.load(std::memory_order_acquire)) { output_->close(); return OpStatus::Finished; }
        if (limiter_ && !limiter_->try_consume()) { if (metrics_) metrics_->events_idle.increment(); return OpStatus::Idle; }
        Event<T> event{};
        if (!generator_(event, seq_)) { output_->close(); return OpStatus::Finished; }
        event.seq = seq_;
        if (seq_ == std::numeric_limits<std::uint64_t>::max()) throw std::overflow_error("Source sequence exhausted");
        ++seq_;
        if (!output_->try_push(event)) {
            pending_ = event; has_pending_ = true;
            if (metrics_) metrics_->events_blocked.increment();
            return OpStatus::Blocked;
        }
        if (metrics_) metrics_->events_processed.increment();
        return OpStatus::Processed;
    }
private:
    Queue* output_;
    Generator generator_;
    std::uint64_t seq_{0};
    Event<T> pending_{};
    bool has_pending_{false};
    std::atomic<bool> finish_{false};
    OperatorMetrics* metrics_{nullptr};
    std::unique_ptr<TokenBucketRateLimiter> limiter_;
};
}
