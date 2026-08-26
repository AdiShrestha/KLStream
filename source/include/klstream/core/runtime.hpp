#pragma once
#include <klstream/core/operator.hpp>
#include <klstream/core/pinning.hpp>
#include <klstream/core/worker.hpp>
#include <klstream/core/metrics.hpp>

#include <cstdint>
#include <memory>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>
#include <atomic>
#include <mutex>
#include <chrono>

namespace klstream {

// ── RuntimeState ──────────────────────────────────────────────────────────
enum class RuntimeState : std::uint8_t {
    Created = 0,
    Starting = 1,
    Running = 2,
    Stopping = 3,
    Draining = 4,
    Stopped = 5
};

inline const char* to_string(RuntimeState state) noexcept {
    switch (state) {
        case RuntimeState::Created:  return "Created";
        case RuntimeState::Starting: return "Starting";
        case RuntimeState::Running:  return "Running";
        case RuntimeState::Stopping: return "Stopping";
        case RuntimeState::Draining: return "Draining";
        case RuntimeState::Stopped:  return "Stopped";
    }
    return "Unknown";
}

// ── OperatorRegistration ──────────────────────────────────────────────────
struct OperatorRegistration {
    IOperator*   op;
    CoreAffinity affinity;
    int          worker_id;
};

// ── Runtime ───────────────────────────────────────────────────────────────
//
// The top-level coordinator. Responsibilities:
//   1. Explicit lifecycle state machine (Created -> Starting -> Running -> Stopping/Draining -> Stopped).
//   2. Accept (operator, affinity, worker_id) registrations.
//   3. Assign operators to WorkerThreads.
//   4. Start all workers (and the MetricsReporter).
//   5. Provide a blocking wait_for() method.
//   6. Idempotent stop() and graceful pipeline drain.

class Runtime {
public:
    Runtime() : state_(RuntimeState::Created) {}

    ~Runtime() {
        if (state_.load(std::memory_order_acquire) != RuntimeState::Stopped &&
            state_.load(std::memory_order_acquire) != RuntimeState::Created) {
            stop();
        }
    }

    Runtime(const Runtime&)            = delete;
    Runtime& operator=(const Runtime&) = delete;
    Runtime(Runtime&&)                 = delete;
    Runtime& operator=(Runtime&&)      = delete;

    int add_worker(CoreAffinity default_affinity = CoreAffinity::Any) {
        if (state_.load(std::memory_order_acquire) != RuntimeState::Created) {
            throw std::logic_error("Runtime::add_worker called after start()");
        }
        int idx = static_cast<int>(workers_.size());
        workers_.emplace_back(std::make_unique<WorkerThread>());
        workers_.back()->set_affinity(default_affinity);
        return idx;
    }

    void register_op(IOperator* op, int worker_id,
                     CoreAffinity affinity = CoreAffinity::Any)
    {
        if (state_.load(std::memory_order_acquire) != RuntimeState::Created) {
            throw std::logic_error("Runtime::register_op called after start()");
        }
        if (worker_id < 0 || worker_id >= static_cast<int>(workers_.size())) {
            throw std::out_of_range(
                "Runtime::register_op: invalid worker_id " +
                std::to_string(worker_id));
        }
        op->id = next_op_id_++;
        if (affinity != CoreAffinity::Any) {
            workers_[worker_id]->set_affinity(affinity);
        }
        workers_[worker_id]->assign(op);
    }

    MetricsReporter& metrics() { return reporter_; }

    [[nodiscard]] RuntimeState state() const noexcept {
        return state_.load(std::memory_order_acquire);
    }

    void start() {
        RuntimeState expected = RuntimeState::Created;
        if (!state_.compare_exchange_strong(expected, RuntimeState::Starting,
                                            std::memory_order_acq_rel)) {
            throw std::logic_error("Runtime::start() called in invalid state: " +
                                   std::string(to_string(expected)));
        }

        reporter_.start();
        for (auto& w : workers_) {
            w->start();
        }

        state_.store(RuntimeState::Running, std::memory_order_release);
    }

    template <typename Rep, typename Period>
    void wait_for(std::chrono::duration<Rep, Period> duration) {
        std::this_thread::sleep_for(duration);
    }

    void drain() {
        std::lock_guard<std::mutex> lock(stop_mutex_);
        RuntimeState current = state_.load(std::memory_order_acquire);
        if (current == RuntimeState::Stopped || current == RuntimeState::Stopping || current == RuntimeState::Draining) {
            return;
        }
        state_.store(RuntimeState::Draining, std::memory_order_release);
        for (auto& w : workers_) {
            w->drain();
        }
    }

    void stop() {
        std::lock_guard<std::mutex> lock(stop_mutex_);
        RuntimeState current = state_.load(std::memory_order_acquire);
        if (current == RuntimeState::Stopped) {
            return; // Idempotent
        }
        if (current == RuntimeState::Created) {
            state_.store(RuntimeState::Stopped, std::memory_order_release);
            return;
        }

        state_.store(RuntimeState::Stopping, std::memory_order_release);
        reporter_.stop();

        // Stop workers in reverse order to ensure downstream drains upstream
        for (auto it = workers_.rbegin(); it != workers_.rend(); ++it) {
            (*it)->stop();
        }

        state_.store(RuntimeState::Stopped, std::memory_order_release);
    }

private:
    std::vector<std::unique_ptr<WorkerThread>> workers_;
    MetricsReporter                            reporter_;
    std::uint64_t                              next_op_id_{0};
    std::atomic<RuntimeState>                  state_{RuntimeState::Created};
    std::mutex                                 stop_mutex_;
};

} // namespace klstream
