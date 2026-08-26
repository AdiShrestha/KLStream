#pragma once
#include <klstream/core/operator.hpp>
#include <klstream/core/pinning.hpp>
#include <klstream/core/config.hpp>

#include <atomic>
#include <chrono>
#include <memory>
#include <thread>
#include <vector>
#include <mutex>

namespace klstream {

// ── WorkerThread ──────────────────────────────────────────────────────────
//
// One OS thread (std::thread) that owns a list of IOperator* and executes
// them cooperatively in a round-robin loop.
//
// Correctness guarantees (INV-009):
//   * Exactly one op->init() call per operator before loop entry.
//   * Drain pass to flush residual in-flight events before termination.
//   * Exactly one op->shutdown() call per operator before thread exit.
//   * Idempotent and thread-safe stop().

class WorkerThread {
public:
    WorkerThread() = default;

    WorkerThread(const WorkerThread&)            = delete;
    WorkerThread& operator=(const WorkerThread&) = delete;
    WorkerThread(WorkerThread&&)                 = delete;
    WorkerThread& operator=(WorkerThread&&)      = delete;

    void assign(IOperator* op) {
        operators_.push_back(op);
    }

    void set_affinity(CoreAffinity aff) { affinity_ = aff; }

    void start() {
        running_.store(true, std::memory_order_release);
        thread_ = std::thread([this]{ run(); });
    }

    void drain() {
        draining_.store(true, std::memory_order_release);
    }

    void stop() {
        std::lock_guard<std::mutex> lock(stop_mutex_);
        if (!stopped_) {
            running_.store(false, std::memory_order_release);
            if (thread_.joinable()) {
                thread_.join();
            }
            stopped_ = true;
        }
    }

    ~WorkerThread() {
        stop();
    }

private:
    void run() {
        apply_affinity(affinity_);

        // Exactly once init() on the worker thread
        for (auto* op : operators_) {
            op->init();
        }

        int idle_rounds = 0;
        const int YIELD_CAP = SPIN_BEFORE_YIELD + YIELD_BEFORE_SLEEP;

        while (running_.load(std::memory_order_relaxed)) {
            bool any_progress = false;
            for (auto* op : operators_) {
                OpStatus s = op->tick();
                if (s == OpStatus::Processed) any_progress = true;
            }
            if (!any_progress) {
                if (draining_.load(std::memory_order_relaxed)) {
                    break;
                }
                ++idle_rounds;
                if (idle_rounds < SPIN_BEFORE_YIELD) {
#if defined(__aarch64__)
                    __asm__ volatile("yield" ::: "memory");
#elif defined(__x86_64__)
                    __asm__ volatile("pause" ::: "memory");
#endif
                } else if (idle_rounds < YIELD_CAP) {
                    std::this_thread::yield();
                } else {
                    std::this_thread::sleep_for(
                        std::chrono::nanoseconds(SLEEP_NS));
                }
            } else {
                idle_rounds = 0;
            }
        }

        // Residual queue drain before shutdown
        constexpr int DRAIN_PASSES = 1000;
        for (int pass = 0; pass < DRAIN_PASSES; ++pass) {
            bool made_progress = false;
            for (auto* op : operators_) {
                if (op->tick() == OpStatus::Processed) {
                    made_progress = true;
                }
            }
            if (!made_progress) break;
        }

        // Exactly once shutdown() on the worker thread
        for (auto* op : operators_) {
            op->shutdown();
        }
    }

    std::vector<IOperator*>  operators_;
    CoreAffinity             affinity_{CoreAffinity::Any};
    std::atomic<bool>        running_{false};
    std::atomic<bool>        draining_{false};
    bool                     stopped_{false};
    std::mutex               stop_mutex_;
    std::thread              thread_;
};

} // namespace klstream
