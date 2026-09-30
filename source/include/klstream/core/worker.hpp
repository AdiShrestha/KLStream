#pragma once
#include <klstream/core/operator.hpp>
#include <klstream/core/pinning.hpp>
#include <atomic>
#include <exception>
#include <thread>
#include <vector>
#include <stdexcept>
#include <algorithm>

namespace klstream {
// One owning worker per operator. Idle is never interpreted as global EOS.
class WorkerThread {
public:
    WorkerThread() = default;
    WorkerThread(const WorkerThread&) = delete;
    WorkerThread& operator=(const WorkerThread&) = delete;
    ~WorkerThread() { cancel(); join(); }
    void assign(IOperator* op) {
        if (started_ || !op || std::find(operators_.begin(), operators_.end(), op) != operators_.end())
            throw std::logic_error("Invalid or repeated worker assignment");
        operators_.push_back(op);
    }
    void set_affinity(CoreAffinity a) {
        if (started_) throw std::logic_error("Configure worker before start");
        affinity_ = a;
    }
    void start() {
        if (started_) throw std::logic_error("Worker is one-shot");
        thread_ = std::thread([this] { run(); });
        started_ = true;
    }
    void cancel() noexcept { cancel_.store(true, std::memory_order_release); }
    void request_finish() noexcept { for (auto* op : operators_) op->request_finish(); }
    void join() noexcept { if (thread_.joinable()) thread_.join(); }
    bool finished() const noexcept { return finished_.load(std::memory_order_acquire); }
    bool failed() const noexcept { return failed_.load(std::memory_order_acquire); }
    // Read only after join. Runtime propagates the original callback exception.
    std::exception_ptr error() const noexcept { return error_; }
private:
    void run() noexcept {
        apply_affinity(affinity_);
        std::size_t initialized = 0;
        try {
            for (auto* op : operators_) { op->init(); ++initialized; }
            std::vector<bool> done(operators_.size(), false);
            std::size_t left = done.size();
            while (left && !cancel_.load(std::memory_order_acquire)) {
                bool progress = false;
                for (std::size_t i = 0; i < operators_.size(); ++i) {
                    if (done[i]) continue;
                    const auto s = operators_[i]->tick();
                    if (s == OpStatus::Finished) { done[i] = true; --left; progress = true; }
                    else if (s == OpStatus::Processed) progress = true;
                }
                if (!progress) std::this_thread::yield();
            }
        } catch (...) { error_ = std::current_exception(); failed_.store(true, std::memory_order_release); }
        for (std::size_t i = 0; i < initialized; ++i) {
            try { operators_[i]->shutdown(); }
            catch (...) { if (!error_) error_ = std::current_exception(); failed_.store(true, std::memory_order_release); }
        }
        finished_.store(true, std::memory_order_release);
    }
    std::vector<IOperator*> operators_;
    CoreAffinity affinity_{CoreAffinity::Any};
    std::atomic<bool> cancel_{false}, finished_{false}, failed_{false};
    std::exception_ptr error_;
    std::thread thread_;
    bool started_{false}; // coordinator-owned; never read by the worker
};
}
