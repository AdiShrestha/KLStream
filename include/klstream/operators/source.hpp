// include/klstream/operators/source.hpp
#pragma once
#include "../core/operator.hpp"
#include "../core/event.hpp"
#include "../core/spsc_queue.hpp"
#include "../core/metrics.hpp"
#include "../core/backpressure.hpp"
#include <functional>
#include <atomic>
#include <cstdint>

namespace klstream {

// ── SourceOperator<T> ─────────────────────────────────────────────────────
//
// Generates events from a user-supplied generator function and pushes them
// into a single output queue. Has no input queue.
//
// The generator function is called once per tick() to produce one event.
// When the generator returns false, the source is exhausted (finite source).
// When it returns true and populates `out`, the source pushes `out` downstream.
//
// Rate limiting:
//   If a TokenBucketRateLimiter is attached (via enable_rate_limiting()),
//   the source checks the bucket before calling the generator. This is the
//   mechanism for both:
//     (a) basic rate control (cap at N events/sec for testing)
//     (b) adaptive backpressure (reduce rate when EMA occupancy rises)
//
// Backpressure:
//   If the output queue is full (try_push returns false), the source caches
//   the generated event in pending_ and returns Blocked. On the next tick()
//   it attempts to push pending_ again without generating a new event.
template <typename T>
class SourceOperator : public IOperator {
public:
    using Queue     = SPSCQueue<Event<T>>;
    using Generator = std::function<bool(Event<T>& out, std::uint64_t seq)>;

    SourceOperator(std::string name, Queue* output, Generator gen)
        : IOperator(std::move(name))
        , output_(output)
        , gen_(std::move(gen))
    {}

    void enable_rate_limiting(double events_per_sec) {
        limiter_ = std::make_unique<TokenBucketRateLimiter>(events_per_sec);
        ema_tracker_ = std::make_unique<EMAOccupancyTracker<Queue>>(*output_);
    }

    void attach_metrics(OperatorMetrics* m) { metrics_ = m; }

    OpStatus tick() override {
        // ── Adaptive backpressure (if enabled) ───────────────────────────
        if (ema_tracker_) {
            ema_tracker_->update();
            if (ema_tracker_->hard_pressure()) {
                if (metrics_) metrics_->events_blocked.increment();
                return OpStatus::Blocked;
            }
            if (ema_tracker_->soft_pressure() && limiter_) {
                // Reduce rate to 50% of configured rate.
                limiter_->set_rate(limiter_->rate() * 0.5);
            } else if (limiter_) {
                // Recover rate gradually (5% per tick toward original).
                limiter_->set_rate(
                    std::min(limiter_->rate() * 1.05, original_rate_));
            }
        }

        // ── Rate limiter check ────────────────────────────────────────────
        if (limiter_ && !limiter_->try_consume()) {
            if (metrics_) metrics_->events_idle.increment();
            return OpStatus::Idle;
        }

        // ── Push pending event from previous Blocked tick ─────────────────
        if (has_pending_) {
            if (output_->try_push(pending_)) {
                has_pending_ = false;
                if (metrics_) metrics_->events_processed.increment();
                return OpStatus::Processed;
            }
            if (metrics_) metrics_->events_blocked.increment();
            return OpStatus::Blocked;
        }

        // ── Generate a new event ──────────────────────────────────────────
        Event<T> ev;
        if (!gen_(ev, seq_++)) {
            return OpStatus::Idle; // Generator exhausted or throttling.
        }

        if (output_->try_push(ev)) {
            if (metrics_) metrics_->events_processed.increment();
            return OpStatus::Processed;
        }

        // Could not push — cache and report Blocked.
        pending_     = ev;
        has_pending_ = true;
        if (metrics_) metrics_->events_blocked.increment();
        return OpStatus::Blocked;
    }

private:
    Queue*             output_;
    Generator          gen_;
    std::uint64_t      seq_{0};
    Event<T>           pending_{};
    bool               has_pending_{false};
    double             original_rate_{0.0};
    OperatorMetrics*   metrics_{nullptr};
    std::unique_ptr<TokenBucketRateLimiter>          limiter_;
    std::unique_ptr<EMAOccupancyTracker<Queue>>      ema_tracker_;
};

} // namespace klstream
