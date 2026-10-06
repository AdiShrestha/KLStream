#pragma once
#include <klstream/core/event.hpp>
#include <klstream/core/operator.hpp>
#include <klstream/core/spsc_queue.hpp>
#include <array>
#include <functional>
#include <stdexcept>

namespace klstream {
template <typename T, std::size_t Max> struct EventBatch {
    static_assert(Max > 0, "Batch maximum must be positive");
    std::array<Event<T>, Max> events{};
    std::size_t count{0};
    std::uint64_t ready_time_ns{0};
};
// The selector is evaluated once after the first input of each batch arrives.
// A processing-time deadline requests partial-batch readiness; scheduler and
// output backpressure can delay publication. EOS flushes leftovers.
// Every input's ID and timestamp survives batching. No detection labels exist here.
template <typename T, std::size_t Max> class BatchOperator : public IOperator {
public:
    using Batch = EventBatch<T, Max>;
    using InQueue = SPSCQueue<Event<T>>;
    using OutQueue = SPSCQueue<Batch>;
    using Selector = std::function<std::size_t()>;
    BatchOperator(std::string name, InQueue* input, OutQueue* output, Selector selector, std::chrono::nanoseconds deadline)
        : IOperator(std::move(name)), input_(input), output_(output), selector_(std::move(selector)), deadline_(deadline) {
        if (!input_ || !output_ || !selector_ || deadline_.count() <= 0) throw std::invalid_argument("Invalid batch operator");
    }
    OpStatus tick() override {
        if (input_->is_cancelled()) {
            abort_partial();
            throw std::runtime_error("Input cancelled; EOS was not reached");
        }
        if (!output_->is_running()) {
            abort_partial();
            throw std::runtime_error("Output closed or cancelled before operator completion");
        }
        if (pending_) {
            if (!output_->try_push(batch_)) return OpStatus::Blocked;
            pending_ = false; batch_.count = 0; batch_.ready_time_ns = 0;
            return OpStatus::Processed;
        }
        if (batch_.count && std::chrono::steady_clock::now() - opened_ >= deadline_) {
            batch_.ready_time_ns = static_cast<std::uint64_t>(
                std::chrono::duration_cast<std::chrono::nanoseconds>(
                    std::chrono::steady_clock::now().time_since_epoch()).count());
            pending_ = true; return OpStatus::Processed;
        }
        Event<T> input{};
        if (input_->try_pop(input)) {
            if (!batch_.count) {
                opened_ = std::chrono::steady_clock::now();
                target_ = selector_();
                if (!target_ || target_ > Max) throw std::out_of_range("Batch selector outside storage bound");
            }
            batch_.events[batch_.count++] = input;
            if (batch_.count == target_) {
                batch_.ready_time_ns = static_cast<std::uint64_t>(
                    std::chrono::duration_cast<std::chrono::nanoseconds>(
                        std::chrono::steady_clock::now().time_since_epoch()).count());
                pending_ = true;
            }
            return OpStatus::Processed;
        }
        if (input_->is_drained()) {
            if (batch_.count) {
                batch_.ready_time_ns = static_cast<std::uint64_t>(
                    std::chrono::duration_cast<std::chrono::nanoseconds>(
                        std::chrono::steady_clock::now().time_since_epoch()).count());
                pending_ = true; return OpStatus::Processed;
            }
            output_->close(); return OpStatus::Finished;
        }
        return OpStatus::Idle;
    }
    void shutdown() override {
        abort_partial();
    }
    [[nodiscard]] std::size_t dropped_count() const noexcept { return dropped_count_; }
    [[nodiscard]] std::size_t aborted_count() const noexcept { return dropped_count_; }
private:
    void abort_partial() noexcept {
        if (batch_.count > 0 || pending_) {
            dropped_count_ += batch_.count;
            batch_.count = 0;
            batch_.ready_time_ns = 0;
            pending_ = false;
        }
    }
    InQueue* input_; OutQueue* output_; Selector selector_;
    std::chrono::nanoseconds deadline_;
    std::chrono::steady_clock::time_point opened_{};
    std::size_t target_{0}; Batch batch_{}; bool pending_{false};
    std::size_t dropped_count_{0};
};
}
