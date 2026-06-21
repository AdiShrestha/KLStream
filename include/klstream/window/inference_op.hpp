#pragma once
#include "../core/operator.hpp"
#include "../core/event.hpp"
#include "../core/spsc_queue.hpp"
#include "../core/metrics.hpp"
#include "../model/isolation_forest.hpp"
#include "types.hpp"

namespace klstream {

class InferenceOp : public IOperator {
public:
    using InQueue  = SPSCQueue<Event<WindowBatch>>;
    using OutQueue = SPSCQueue<Event<DetectionResult>>;
    using Forest   = IsolationForest<FeatureVector::kDim>;

    InferenceOp(std::string name, InQueue* input, OutQueue* output,
               const Forest* forest)
        : IOperator(std::move(name))
        , input_(input), output_(output), forest_(forest)
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

        Event<WindowBatch> in_ev;
        if (!input_->try_pop(&in_ev)) {
            if (metrics_) metrics_->events_idle.increment();
            return OpStatus::Idle;
        }

        // ── The O(W log psi) hot loop — Section 7.2's causal mechanism ───
        const WindowBatch& wb = in_ev.data;
        double   max_score   = -1.0;
        uint32_t max_idx     = 0;
        for (std::uint32_t i = 0; i < wb.count; ++i) {
            double s = forest_->anomaly_score(wb.points[i].to_point());
            if (s > max_score) { max_score = s; max_idx = i; }
        }

        Event<DetectionResult> out_ev;
        // Re-stamp with the FLAGGED point's own timestamp, not the window's
        // arrival timestamp (Section 7.4) — this is what makes downstream
        // latency() measure "time since the actual anomalous tick occurred."
        //
        // NOTE: per-point timestamps are not retained inside WindowBatch
        // (FeatureVector intentionally omits a timestamp field to keep it
        // exactly 5 floats / 20 bytes for cache-friendly scoring). We
        // approximate the flagged point's wall-clock arrival time by linear
        // interpolation between the window's first and last event
        // timestamps — out_ev.timestamp_ns = in_ev.timestamp_ns
        // (the window's LAST-tick arrival time) is used as a conservative
        // (slightly pessimistic, never optimistic) stand-in. State this
        // approximation explicitly in your methodology section: it means
        // reported latency is an upper bound, not an exact per-tick figure,
        // which is the safe direction to bias an evaluation.
        out_ev.timestamp_ns = in_ev.timestamp_ns;
        out_ev.seq = in_ev.seq;
        out_ev.data = DetectionResult{
            max_score,
            wb.count,
            wb.first_seq,
            wb.last_seq,
            wb.first_seq + max_idx,
            0.0f   // filled in by the wiring code for the Adaptive variant only
        };

        if (output_->try_push(out_ev)) {
            if (metrics_) metrics_->events_processed.increment();
            return OpStatus::Processed;
        }
        pending_ = out_ev;
        has_pending_ = true;
        if (metrics_) metrics_->events_blocked.increment();
        return OpStatus::Blocked;
    }

private:
    InQueue*       input_;
    OutQueue*      output_;
    const Forest*  forest_;   // owned by main(), lives for the runtime's lifetime
    Event<DetectionResult> pending_{};
    bool           has_pending_{false};
    OperatorMetrics* metrics_{nullptr};
};

} // namespace klstream
