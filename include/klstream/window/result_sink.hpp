#pragma once
#include "../core/operator.hpp"
#include "../core/event.hpp"
#include "../core/spsc_queue.hpp"
#include "../core/metrics.hpp"
#include "types.hpp"
#include <fstream>
#include <iomanip>

namespace klstream {

// Writes one CSV row per DetectionResult. Joined against
// injection_log.csv (Section 9.3) offline in Python (Section 23/25's
// analysis notebook) — this operator does NOT compute F1/PATR/WOR/LBA
// itself; it only records ground truth needed to compute them later,
// keeping the hot C++ path free of any evaluation-metric logic.
class ResultSink : public IOperator {
public:
    using InQueue = SPSCQueue<Event<DetectionResult>>;

    ResultSink(std::string name, InQueue* input, std::string out_csv_path)
        : IOperator(std::move(name))
        , input_(input)
        , out_(out_csv_path)
    {
        out_ << "seq,detect_timestamp_ns,latency_ns,max_score,window_size_used,"
                "first_seq,last_seq,flagged_seq,occupancy_at_decision\n";
    }

    void attach_metrics(OperatorMetrics* m) override { metrics_ = m; }

    OpStatus tick() override {
        Event<DetectionResult> ev;
        if (!input_->try_pop(&ev)) {
            if (metrics_) metrics_->events_idle.increment();
            return OpStatus::Idle;
        }
        const auto& r = ev.data;
        out_ << ev.seq << ','
             << ev.timestamp_ns << ','
             << ev.latency_ns() << ','
             << std::setprecision(8) << r.max_score << ','
             << r.window_size_used << ','
             << r.first_seq << ','
             << r.last_seq << ','
             << r.flagged_seq << ','
             << r.occupancy_at_decision << '\n';
        if (metrics_) metrics_->events_processed.increment();
        return OpStatus::Processed;
    }

    void shutdown() override { out_.flush(); }

private:
    InQueue*      input_;
    std::ofstream out_;
    OperatorMetrics* metrics_{nullptr};
};

} // namespace klstream
