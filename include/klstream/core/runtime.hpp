#pragma once

/**
 * @file runtime.hpp
 * @brief Main runtime coordination and stream graph execution
 */

#include <memory>
#include <vector>
#include <unordered_map>
#include <string>
#include <stdexcept>

#include "klstream/core/operator.hpp"
#include "klstream/core/queue.hpp"
#include "klstream/core/scheduler.hpp"
#include "klstream/core/worker_pool.hpp"
#include "klstream/core/metrics.hpp"

namespace klstream {

/**
 * @brief Runtime configuration
 */
struct RuntimeConfig {
    std::uint32_t num_workers{0};          // 0 = auto
    std::size_t default_queue_capacity{4096};
    SchedulingPolicy scheduling_policy{SchedulingPolicy::RoundRobin};
    bool enable_metrics{true};
    std::chrono::milliseconds metrics_interval{1000};
};

/**
 * @brief Runtime state enumeration
 */
enum class RuntimeState {
    Created,
    Initialized,
    Running,
    ShuttingDown,
    Stopped
};

/**
 * @brief Edge definition in the stream graph
 */
struct Edge {
    std::string from_operator;
    std::string to_operator;
    std::size_t queue_capacity{4096};
};

/**
 * @brief Stream graph builder
 */
class StreamGraphBuilder {
public:
    /**
     * @brief Add an operator to the graph
     */
    StreamGraphBuilder& add_operator(std::unique_ptr<Operator> op) {
        auto name = op->name();
        operators_[name] = std::move(op);
        return *this;
    }
    
    /**
     * @brief Add a source operator
     */
    StreamGraphBuilder& add_source(std::unique_ptr<SourceOperator> source) {
        auto name = source->name();
        sources_.push_back(name);
        operators_[name] = std::move(source);
        return *this;
    }
    
    /**
     * @brief Add a sink operator
     */
    StreamGraphBuilder& add_sink(std::unique_ptr<SinkOperator> sink) {
        auto name = sink->name();
        sinks_.push_back(name);
        operators_[name] = std::move(sink);
        return *this;
    }
    
    /**
     * @brief Connect two operators
     */
    StreamGraphBuilder& connect(
        const std::string& from,
        const std::string& to,
        std::size_t queue_capacity = 4096
    ) {
        edges_.push_back({from, to, queue_capacity});
        return *this;
    }
    
    [[nodiscard]] std::unordered_map<std::string, std::unique_ptr<Operator>>& operators() {
        return operators_;
    }
    
    [[nodiscard]] const std::vector<Edge>& edges() const { return edges_; }
    [[nodiscard]] const std::vector<std::string>& sources() const { return sources_; }
    [[nodiscard]] const std::vector<std::string>& sinks() const { return sinks_; }

private:
    std::unordered_map<std::string, std::unique_ptr<Operator>> operators_;
    std::vector<Edge> edges_;
    std::vector<std::string> sources_;
    std::vector<std::string> sinks_;
};

/**
 * @brief Main stream processing runtime
 * 
 * The runtime is responsible for:
 * - Managing the stream graph
 * - Coordinating worker threads
 * - Enforcing backpressure
 * - Collecting metrics
 */
class Runtime {
public:
    explicit Runtime(RuntimeConfig config = {});
    ~Runtime();
    
    // Non-copyable, non-movable
    Runtime(const Runtime&) = delete;
    Runtime& operator=(const Runtime&) = delete;
    
    /**
     * @brief Initialize the runtime with a stream graph
     */
    void init(StreamGraphBuilder builder);
    
    /**
     * @brief Start the runtime
     */
    void start();
    
    /**
     * @brief Stop the runtime gracefully
     */
    void stop();
    
    /**
     * @brief Wait for the runtime to complete
     */
    void await_completion();
    
    /**
     * @brief Get runtime state
     */
    [[nodiscard]] RuntimeState state() const noexcept { return state_; }
    
    /**
     * @brief Get metrics collector
     */
    [[nodiscard]] MetricsCollector& metrics() { return *metrics_; }
    [[nodiscard]] const MetricsCollector& metrics() const { return *metrics_; }
    
    /**
     * @brief Get runtime configuration
     */
    [[nodiscard]] const RuntimeConfig& config() const noexcept { return config_; }

private:
    void run_sources();
    void drain_queues();
    
    RuntimeConfig config_;
    RuntimeState state_{RuntimeState::Created};
    
    std::vector<std::unique_ptr<OperatorInstance>> instances_;
    std::vector<std::shared_ptr<Queue>> queues_;
    std::vector<SourceOperator*> source_operators_;
    std::vector<std::thread> source_threads_;
    
    std::unique_ptr<Scheduler> scheduler_;
    std::unique_ptr<WorkerPool> worker_pool_;
    std::unique_ptr<MetricsCollector> metrics_;
    
    std::atomic<bool> running_{false};
};

} // namespace klstream
