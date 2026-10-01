#pragma once
#include <klstream/core/worker.hpp>
#include <chrono>
#include <memory>
#include <mutex>
#include <stdexcept>
#include <unordered_set>

namespace klstream {
enum class RuntimeState { Created, Running, Draining, Stopped, Failed };
// Coordinator methods are serialized. Call them from a coordinator thread,
// never from an operator callback. Callbacks must return for cancellation to join.
class Runtime {
public:
    Runtime() = default;
    Runtime(const Runtime&) = delete;
    Runtime& operator=(const Runtime&) = delete;
    ~Runtime() { stop(); }
    int add_worker(CoreAffinity affinity = CoreAffinity::Any) {
        std::lock_guard<std::mutex> lock(mutex_);
        require_created();
        workers_.push_back(std::make_unique<WorkerThread>());
        workers_.back()->set_affinity(affinity);
        return static_cast<int>(workers_.size() - 1);
    }
    void register_op(IOperator* op, int id, CoreAffinity affinity = CoreAffinity::Any) {
        std::lock_guard<std::mutex> lock(mutex_);
        require_created();
        if (!op || id < 0 || static_cast<std::size_t>(id) >= workers_.size()) throw std::invalid_argument("Invalid operator registration");
        if (!registered_.insert(op).second) throw std::invalid_argument("Operator already has an owning worker");
        try { workers_[id]->assign(op); }
        catch (...) { registered_.erase(op); throw; }
        op->id = registered_.size() - 1;
        if (affinity != CoreAffinity::Any) workers_[id]->set_affinity(affinity);
    }
    void start() {
        std::lock_guard<std::mutex> lock(mutex_);
        require_created();
        if (registered_.empty()) throw std::logic_error("Cannot start an empty runtime");
        try { for (auto& w : workers_) w->start(); state_ = RuntimeState::Running; }
        catch (...) { cancel_and_join(); state_ = RuntimeState::Failed; throw; }
    }
    // A timeout leaves the runtime alive and returns false. It is not a success.
    bool wait_until_done(std::chrono::milliseconds timeout) {
        std::lock_guard<std::mutex> lock(mutex_);
        return await_done(timeout);
    }
    bool drain(std::chrono::milliseconds timeout = std::chrono::seconds(30)) {
        if (timeout.count() < 0) throw std::invalid_argument("Negative runtime timeout");
        std::lock_guard<std::mutex> lock(mutex_);
        if (state_ == RuntimeState::Stopped) return completed_;
        if (state_ != RuntimeState::Running && state_ != RuntimeState::Draining) throw std::logic_error("Drain requires a started runtime");
        state_ = RuntimeState::Draining;
        for (auto& w : workers_) w->request_finish();
        return await_done(timeout);
    }
    // Immediate cancellation: residual inputs may remain. Use drain for EOS.
    void stop() noexcept {
        std::lock_guard<std::mutex> lock(mutex_);
        if (state_ == RuntimeState::Stopped) return;
        cancel_and_join();
        bool failed = false;
        for (auto& w : workers_) failed = failed || w->failed();
        state_ = failed ? RuntimeState::Failed : RuntimeState::Stopped;
    }
    RuntimeState state() const { std::lock_guard<std::mutex> lock(mutex_); return state_; }
private:
    void require_created() const { if (state_ != RuntimeState::Created) throw std::logic_error("Runtime is one-shot; configure before start"); }
    void cancel_and_join() noexcept { for (auto& w : workers_) w->cancel(); for (auto& w : workers_) w->join(); }
    bool await_done(std::chrono::milliseconds timeout) {
        if (timeout.count() < 0) throw std::invalid_argument("Negative runtime timeout");
        if (state_ == RuntimeState::Stopped) return completed_;
        if (state_ != RuntimeState::Running && state_ != RuntimeState::Draining) throw std::logic_error("Wait requires a running runtime");
        const auto began = std::chrono::steady_clock::now();
        for (;;) {
            bool all = true, failed = false;
            for (auto& w : workers_) { all = all && w->finished(); failed = failed || w->failed(); }
            if (failed) {
                cancel_and_join(); state_ = RuntimeState::Failed;
                for (auto& w : workers_) if (w->error()) std::rethrow_exception(w->error());
            }
            if (all) { for (auto& w : workers_) w->join(); state_ = RuntimeState::Stopped; completed_ = true; return true; }
            if (std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - began) >= timeout) return false;
            std::this_thread::sleep_for(std::chrono::milliseconds(1));
        }
    }
    mutable std::mutex mutex_;
    RuntimeState state_{RuntimeState::Created};
    bool completed_{false};
    std::vector<std::unique_ptr<WorkerThread>> workers_;
    std::unordered_set<IOperator*> registered_;
};
}
