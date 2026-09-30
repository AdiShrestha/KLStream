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
        if (pending_) {
            if (!output_->try_push(batch_)) return OpStatus::Blocked;
            pending_ = false; batch_.count = 0;
            return OpStatus::Processed;
        }
        if (batch_.count && std::chrono::steady_clock::now() - opened_ >= deadline_) {
            pending_ = true; return OpStatus::Processed;
        }
        Event<T> input{};
        if (input_->try_pop(input)) {
            if (!batch_.count) {
                target_ = selector_();
                if (!target_ || target_ > Max) throw std::out_of_range("Batch selector outside storage bound");
                opened_ = std::chrono::steady_clock::now();
            }
            batch_.events[batch_.count++] = input;
            if (batch_.count == target_) pending_ = true;
            return OpStatus::Processed;
        }
        if (input_->is_drained()) {
            if (batch_.count) { pending_ = true; return OpStatus::Processed; }
            output_->close(); return OpStatus::Finished;
        }
        return OpStatus::Idle;
    }
private:
    InQueue* input_; OutQueue* output_; Selector selector_;
    std::chrono::nanoseconds deadline_;
    std::chrono::steady_clock::time_point opened_{};
    std::size_t target_{0}; Batch batch_{}; bool pending_{false};
};
}
