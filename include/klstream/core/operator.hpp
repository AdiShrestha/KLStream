#pragma once

/**
 * @file operator.hpp
 * @brief Base operator interface and common operator types
 */

#include <string>
#include <memory>
#include <vector>
#include <functional>
#include <atomic>

#include "klstream/core/event.hpp"
#include "klstream/core/queue.hpp"

namespace klstream {

// Forward declarations
class Runtime;
class OperatorContext;

/**
 * @brief Operator state enumeration
 */
enum class OperatorState {
    Created,
    Initialized,
    Running,
    Paused,
    ShuttingDown,
    Stopped
};

/**
 * @brief Operator statistics
 */
struct OperatorStats {
    std::uint64_t events_received{0};
    std::uint64_t events_emitted{0};
    std::uint64_t events_dropped{0};
    std::uint64_t processing_time_ns{0};
    std::uint64_t backpressure_events{0};
};

/**
 * @brief Context provided to operators during execution
 */
class OperatorContext {
public:
    explicit OperatorContext(std::string name, std::uint32_t instance_id = 0)
        : name_(std::move(name))
        , instance_id_(instance_id) {}
    
    [[nodiscard]] const std::string& name() const noexcept { return name_; }
    [[nodiscard]] std::uint32_t instance_id() const noexcept { return instance_id_; }
    
    /**
     * @brief Register an output queue for this operator
     */
    void add_output(std::shared_ptr<Queue> queue) {
        outputs_.push_back(std::move(queue));
    }
    
    /**
     * @brief Emit an event to all output queues
     * @return Number of outputs that accepted the event
     */
    std::size_t emit(Event event) {
        std::size_t count = 0;
        for (auto& output : outputs_) {
            if (output->push(event)) {
                count++;
            }
        }
        return count;
    }
    
    /**
     * @brief Try to emit without blocking
     */
    std::size_t try_emit(Event event) {
        std::size_t count = 0;
        for (auto& output : outputs_) {
            if (output->try_push(event)) {
                count++;
            }
        }
        return count;
    }
    
    [[nodiscard]] std::size_t output_count() const noexcept {
        return outputs_.size();
    }
    
    [[nodiscard]] const std::vector<std::shared_ptr<Queue>>& outputs() const noexcept {
        return outputs_;
    }

private:
    std::string name_;
    std::uint32_t instance_id_;
    std::vector<std::shared_ptr<Queue>> outputs_;
};

/**
 * @brief Base class for all stream operators
 * 
 * Operators are the processing units in the stream graph.
 * Each operator continuously processes events from input queues
 * and emits results to output queues.
 */
class Operator {
public:
    explicit Operator(std::string name)
        : name_(std::move(name)) {}
    
    virtual ~Operator() = default;
    
    // Non-copyable
    Operator(const Operator&) = delete;
    Operator& operator=(const Operator&) = delete;
    
    // Movable
    Operator(Operator&&) = default;
    Operator& operator=(Operator&&) = default;
    
    /**
     * @brief Initialize the operator
     * Called once before processing starts
     */
    virtual void init(OperatorContext& ctx) {
        (void)ctx;  // Default: no-op
    }
    
    /**
     * @brief Process a single event
     * @param event The event to process
     * @param ctx The operator context for emitting output
     */
    virtual void process(Event& event, OperatorContext& ctx) = 0;
    
    /**
     * @brief Shutdown the operator
     * Called once when processing stops
     */
    virtual void shutdown(OperatorContext& ctx) {
        (void)ctx;  // Default: no-op
    }
    
    /**
     * @brief Called periodically for time-based operations
     */
    virtual void on_timer(OperatorContext& ctx) {
        (void)ctx;  // Default: no-op
    }
    
    // Accessors
    [[nodiscard]] const std::string& name() const noexcept { return name_; }
    [[nodiscard]] OperatorState state() const noexcept { return state_.load(); }
    [[nodiscard]] const OperatorStats& stats() const noexcept { return stats_; }
    
protected:
    void set_state(OperatorState state) noexcept { state_.store(state); }
    
    // Statistics helpers
    void record_received() noexcept { stats_.events_received++; }
    void record_emitted() noexcept { stats_.events_emitted++; }
    void record_dropped() noexcept { stats_.events_dropped++; }
    void record_backpressure() noexcept { stats_.backpressure_events++; }
    void record_processing_time(std::uint64_t ns) noexcept { 
        stats_.processing_time_ns += ns; 
    }
    
private:
    std::string name_;
    std::atomic<OperatorState> state_{OperatorState::Created};
    OperatorStats stats_;
};

/**
 * @brief Source operator base class
 * 
 * Sources generate events and have no input queues.
 * They must respect backpressure from downstream operators.
 */
class SourceOperator : public Operator {
public:
    using Operator::Operator;
    
    /**
     * @brief Generate events
     * Called repeatedly to produce events
     * @return true to continue, false to stop
     */
    virtual bool generate(OperatorContext& ctx) = 0;
    
    // Sources don't process incoming events
    void process(Event& /*event*/, OperatorContext& /*ctx*/) final {
        // No-op: sources don't receive events
    }
    
    /**
     * @brief Check if source should stop generating
     */
    [[nodiscard]] bool should_stop() const noexcept {
        return stop_requested_.load(std::memory_order_acquire);
    }
    
    /**
     * @brief Request source to stop generating
     */
    void request_stop() noexcept {
        stop_requested_.store(true, std::memory_order_release);
    }

private:
    std::atomic<bool> stop_requested_{false};
};

/**
 * @brief Sink operator base class
 * 
 * Sinks consume events and have no output queues.
 * They are the terminal points of the stream graph.
 */
class SinkOperator : public Operator {
public:
    using Operator::Operator;
    
    /**
     * @brief Consume an event
     * @param event The event to consume
     */
    virtual void consume(const Event& event) = 0;
    
    void process(Event& event, OperatorContext& /*ctx*/) final {
        consume(event);
    }
};

/**
 * @brief Function-based operator for simple transformations
 */
template<typename Func>
class FunctionOperator : public Operator {
public:
    FunctionOperator(std::string name, Func func)
        : Operator(std::move(name))
        , func_(std::move(func)) {}
    
    void process(Event& event, OperatorContext& ctx) override {
        record_received();
        auto start = std::chrono::steady_clock::now();
        
        if constexpr (std::is_invocable_v<Func, Event&, OperatorContext&>) {
            func_(event, ctx);
        } else if constexpr (std::is_invocable_r_v<std::optional<Event>, Func, const Event&>) {
            if (auto result = func_(event)) {
                ctx.emit(std::move(*result));
                record_emitted();
            }
        } else {
            auto result = func_(event);
            ctx.emit(Event{result});
            record_emitted();
        }
        
        auto end = std::chrono::steady_clock::now();
        auto ns = std::chrono::duration_cast<std::chrono::nanoseconds>(end - start).count();
        record_processing_time(static_cast<std::uint64_t>(ns));
    }

private:
    Func func_;
};

/**
 * @brief Factory function for creating function-based operators
 */
template<typename Func>
auto make_operator(std::string name, Func&& func) {
    return std::make_unique<FunctionOperator<std::decay_t<Func>>>(
        std::move(name), std::forward<Func>(func)
    );
}

} // namespace klstream
