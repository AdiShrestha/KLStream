#pragma once
#include <klstream/core/operator.hpp>
#include <klstream/core/event.hpp>
#include <klstream/core/spsc_queue.hpp>
#include <functional>
#include <stdexcept>
#include <vector>

namespace klstream {
// Non-keyed, count-based aggregation. EOS flushes one partial window. The
// aggregate timestamp refers to its oldest input, not every member's latency.
template <typename T, typename Out> class TumblingCountWindow : public IOperator {
public:
    using InQueue = SPSCQueue<Event<T>>;
    using OutQueue = SPSCQueue<Event<Out>>;
    using AggrFn = std::function<Out(const std::vector<Event<T>>&)>;
    TumblingCountWindow(std::string name, InQueue* input, OutQueue* output, std::size_t size, AggrFn fn)
        : IOperator(std::move(name)), input_(input), output_(output), size_(size), fn_(std::move(fn)) {
        if (!input_ || !output_ || !size_ || !fn_) throw std::invalid_argument("Invalid count window");
        buffer_.reserve(size_);
    }
    OpStatus tick() override {
        if (input_->is_cancelled()) throw std::runtime_error("Input cancelled; EOS was not reached");
        if (!output_->is_running()) throw std::runtime_error("Output closed or cancelled before operator completion");
        if (pending_) {
            if (!output_->try_push(event_)) return OpStatus::Blocked;
            pending_ = false;
            return OpStatus::Processed;
        }
        Event<T> in{};
        if (input_->try_pop(in)) {
            buffer_.push_back(in);
            if (buffer_.size() == size_) emit();
            return OpStatus::Processed;
        }
        if (input_->is_drained()) {
            if (!buffer_.empty()) { emit(); return OpStatus::Processed; }
            output_->close(); return OpStatus::Finished;
        }
        return OpStatus::Idle;
    }
private:
    void emit() {
        event_ = Event<Out>{buffer_.front().timestamp_ns, 0, buffer_.back().seq, fn_(buffer_)};
        buffer_.clear(); pending_ = true;
    }
    InQueue* input_; OutQueue* output_;
    std::size_t size_; AggrFn fn_;
    std::vector<Event<T>> buffer_;
    Event<Out> event_{}; bool pending_{false};
};
}
