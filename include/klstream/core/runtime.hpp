// include/klstream/core/runtime.hpp
#pragma once
#include "operator.hpp"
#include "pinning.hpp"
#include "worker.hpp"
#include "metrics.hpp"
#include <cstdint>
#include <memory>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

namespace klstream {

// ── OperatorRegistration ──────────────────────────────────────────────────
struct OperatorRegistration {
    IOperator*   op;
    CoreAffinity affinity;
    int          worker_id; // which worker thread to assign this op to
};

// ── Runtime ───────────────────────────────────────────────────────────────
//
// The top-level coordinator. Responsibilities:
//   1. Accept (operator, affinity, worker_id) registrations.
//   2. Assign operators to WorkerThreads.
//   3. Start all workers (and the MetricsReporter).
//   4. Provide a blocking wait() method for main() to call.
//   5. Stop cleanly on request.
//
// USAGE PATTERN:
//
//   klstream::Runtime rt;
//   rt.add_worker();                         // Worker 0
//   rt.add_worker();                         // Worker 1
//   rt.register_op(&my_source, 0, CoreAffinity::Efficiency);
//   rt.register_op(&my_map,    0, CoreAffinity::Performance);
//   rt.register_op(&my_sink,   1, CoreAffinity::Efficiency);
//   rt.metrics().add(&source_metrics);
//   rt.metrics().add(&sink_metrics);
//   rt.start();
//   rt.wait_for(std::chrono::seconds(10));
//   rt.stop();
//
// Thread safety: add_worker(), register_op(), start(), stop(), and wait_for()
// must all be called from the same thread (typically main()).
class Runtime {
public:
    // Add a worker thread slot. Returns its 0-based index.
    int add_worker(CoreAffinity default_affinity = CoreAffinity::Any) {
        int idx = static_cast<int>(workers_.size());
        workers_.emplace_back(std::make_unique<WorkerThread>());
        workers_.back()->set_affinity(default_affinity);
        return idx;
    }

    // Register an operator with a specific worker thread.
    void register_op(IOperator* op, int worker_id,
                     CoreAffinity affinity = CoreAffinity::Any)
    {
        if (worker_id < 0 ||
            worker_id >= static_cast<int>(workers_.size())) {
            throw std::out_of_range(
                "Runtime::register_op: invalid worker_id " +
                std::to_string(worker_id));
        }
        op->id = next_op_id_++;
        // Override the worker's default affinity if a per-op affinity is given.
        if (affinity != CoreAffinity::Any) {
            workers_[worker_id]->set_affinity(affinity);
        }
        workers_[worker_id]->assign(op);
    }

    MetricsReporter& metrics() { return reporter_; }

    // Start all workers and the metrics reporter.
    void start() {
        if (started_) throw std::logic_error("Runtime::start() called twice");
        started_ = true;
        reporter_.start();
        for (auto& w : workers_) w->start();
    }

    // Block the calling thread until duration elapses, then return.
    template <typename Rep, typename Period>
    void wait_for(std::chrono::duration<Rep, Period> duration) {
        std::this_thread::sleep_for(duration);
    }

    // Stop all workers and the metrics reporter.
    void stop() {
        for (auto& w : workers_) w->stop();
        reporter_.stop();
    }

    ~Runtime() { if (started_) stop(); }

private:
    std::vector<std::unique_ptr<WorkerThread>> workers_;
    MetricsReporter                            reporter_;
    std::uint64_t                              next_op_id_{0};
    bool                                       started_{false};
};

} // namespace klstream
