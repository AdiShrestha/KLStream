#pragma once
#include <klstream/core/operator.hpp>
#include <klstream/core/event.hpp>
#include <klstream/core/spsc_queue.hpp>
#include <klstream/core/metrics.hpp>
#include <klstream/model/isolation_forest.hpp>
#include <klstream/window/types.hpp>

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

        const WindowBatch& wb = in_ev.data;
        double   max_score   = -1.0;
        uint32_t max_idx     = 0;
        for (std::uint32_t i = 0; i < wb.count; ++i) {
            double s = forest_->anomaly_score(wb.points[i].to_point());
            if (s > max_score) {
                max_score = s;
                max_idx = i;
            }
        }

        Event<DetectionResult> out_ev;
        out_ev.timestamp_ns = in_ev.timestamp_ns;
        out_ev.seq = in_ev.seq;
        out_ev.data = DetectionResult{
            max_score,
            wb.count,
            wb.first_seq,
            wb.last_seq,
            wb.first_seq + max_idx,
            wb.occupancy_at_decision
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
    InQueue*               input_;
    OutQueue*              output_;
    const Forest*          forest_;
    Event<DetectionResult> pending_{};
    bool                   has_pending_{false};
    OperatorMetrics*       metrics_{nullptr};
};

} // namespace klstream
