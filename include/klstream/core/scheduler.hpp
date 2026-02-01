#pragma once

/**
 * @file scheduler.hpp
 * @brief Operator scheduling policies and implementation
 */

#include <vector>
#include <memory>
#include <atomic>
#include <random>

#include "klstream/core/operator.hpp"

namespace klstream {

// Forward declaration
class OperatorInstance;

/**
 * @brief Scheduling policy enumeration
 */
enum class SchedulingPolicy {
    RoundRobin,         // Cycle through operators
    WorkStealing,       // Idle workers steal from busy workers
    Priority,           // Priority-based scheduling
    LoadAware           // Dynamic load-based scheduling
};

/**
 * @brief Scheduler statistics
 */
struct SchedulerStats {
    std::uint64_t total_scheduled{0};
    std::uint64_t idle_cycles{0};
    std::uint64_t work_stolen{0};
    std::uint64_t backpressure_waits{0};
};

/**
 * @brief Abstract scheduler interface
 */
class Scheduler {
public:
    virtual ~Scheduler() = default;
    
    /**
     * @brief Select the next operator instance to execute
     * @param worker_id The ID of the requesting worker
     * @return Pointer to operator instance or nullptr if none available
     */
    virtual OperatorInstance* next(std::uint32_t worker_id) = 0;
    
    /**
     * @brief Notify scheduler that work is available
     */
    virtual void notify_work_available() = 0;
    
    /**
     * @brief Get scheduler statistics
     */
    [[nodiscard]] virtual SchedulerStats stats() const = 0;
    
    /**
     * @brief Get scheduling policy
     */
    [[nodiscard]] virtual SchedulingPolicy policy() const noexcept = 0;
};

/**
 * @brief Operator instance wrapper for scheduling
 */
class OperatorInstance {
public:
    OperatorInstance(
        std::unique_ptr<Operator> op,
        std::shared_ptr<Queue> input,
        std::uint32_t instance_id
    )
        : operator_(std::move(op))
        , input_queue_(std::move(input))
        , context_(operator_->name(), instance_id) {}
    
    [[nodiscard]] Operator* op() noexcept { return operator_.get(); }
    [[nodiscard]] const Operator* op() const noexcept { return operator_.get(); }
    [[nodiscard]] Queue* input() noexcept { return input_queue_.get(); }
    [[nodiscard]] OperatorContext& context() noexcept { return context_; }
    [[nodiscard]] const OperatorContext& context() const noexcept { return context_; }
    
    /**
     * @brief Check if this instance has work to do
     */
    [[nodiscard]] bool has_work() const {
        return input_queue_ && !input_queue_->empty();
    }
    
    /**
     * @brief Execute one processing iteration
     * @return true if work was done
     */
    bool execute_once() {
        if (!input_queue_) {
            return false;
        }
        
        auto event = input_queue_->try_pop();
        if (!event) {
            return false;
        }
        
        operator_->process(*event, context_);
        return true;
    }
    
    /**
     * @brief Execute multiple events (batch processing)
     * @param max_batch Maximum events to process
     * @return Number of events processed
     */
    std::size_t execute_batch(std::size_t max_batch = 64) {
        if (!input_queue_) {
            return 0;
        }
        
        std::size_t processed = 0;
        while (processed < max_batch) {
            auto event = input_queue_->try_pop();
            if (!event) {
                break;
            }
            operator_->process(*event, context_);
            processed++;
        }
        return processed;
    }

private:
    std::unique_ptr<Operator> operator_;
    std::shared_ptr<Queue> input_queue_;
    OperatorContext context_;
};

/**
 * @brief Round-robin scheduler implementation
 */
class RoundRobinScheduler : public Scheduler {
public:
    explicit RoundRobinScheduler(std::vector<OperatorInstance*> instances)
        : instances_(std::move(instances)) {}
    
    OperatorInstance* next(std::uint32_t worker_id) override {
        if (instances_.empty()) {
            return nullptr;
        }
        
        stats_.total_scheduled++;
        
        // Each worker maintains its own position
        auto& pos = positions_[worker_id];
        std::size_t checked = 0;
        
        while (checked < instances_.size()) {
            auto* instance = instances_[pos % instances_.size()];
            pos++;
            checked++;
            
            if (instance->has_work()) {
                return instance;
            }
        }
        
        stats_.idle_cycles++;
        return nullptr;
    }
    
    void notify_work_available() override {
        // Round-robin doesn't need notification
    }
    
    [[nodiscard]] SchedulerStats stats() const override {
        return stats_;
    }
    
    [[nodiscard]] SchedulingPolicy policy() const noexcept override {
        return SchedulingPolicy::RoundRobin;
    }

private:
    std::vector<OperatorInstance*> instances_;
    std::unordered_map<std::uint32_t, std::size_t> positions_;
    mutable SchedulerStats stats_;
};

/**
 * @brief Work-stealing scheduler implementation
 */
class WorkStealingScheduler : public Scheduler {
public:
    explicit WorkStealingScheduler(
        std::vector<std::vector<OperatorInstance*>> per_worker_instances,
        std::uint32_t num_workers
    )
        : per_worker_(std::move(per_worker_instances))
        , num_workers_(num_workers)
        , rng_(std::random_device{}()) {}
    
    OperatorInstance* next(std::uint32_t worker_id) override {
        stats_.total_scheduled++;
        
        // First, try local work
        for (auto* instance : per_worker_[worker_id]) {
            if (instance->has_work()) {
                return instance;
            }
        }
        
        // Try stealing from other workers
        std::uniform_int_distribution<std::uint32_t> dist(0, num_workers_ - 1);
        for (std::uint32_t attempts = 0; attempts < num_workers_; attempts++) {
            std::uint32_t victim = dist(rng_);
            if (victim == worker_id) continue;
            
            for (auto* instance : per_worker_[victim]) {
                if (instance->has_work()) {
                    stats_.work_stolen++;
                    return instance;
                }
            }
        }
        
        stats_.idle_cycles++;
        return nullptr;
    }
    
    void notify_work_available() override {
        // Could implement wake-up mechanism here
    }
    
    [[nodiscard]] SchedulerStats stats() const override {
        return stats_;
    }
    
    [[nodiscard]] SchedulingPolicy policy() const noexcept override {
        return SchedulingPolicy::WorkStealing;
    }

private:
    std::vector<std::vector<OperatorInstance*>> per_worker_;
    std::uint32_t num_workers_;
    mutable std::mt19937 rng_;
    mutable SchedulerStats stats_;
};

/**
 * @brief Factory for creating schedulers
 */
class SchedulerFactory {
public:
    static std::unique_ptr<Scheduler> create(
        SchedulingPolicy policy,
        std::vector<OperatorInstance*> instances,
        std::uint32_t num_workers
    ) {
        switch (policy) {
            case SchedulingPolicy::RoundRobin:
                return std::make_unique<RoundRobinScheduler>(std::move(instances));
            
            case SchedulingPolicy::WorkStealing: {
                // Distribute instances evenly
                std::vector<std::vector<OperatorInstance*>> per_worker(num_workers);
                for (std::size_t i = 0; i < instances.size(); i++) {
                    per_worker[i % num_workers].push_back(instances[i]);
                }
                return std::make_unique<WorkStealingScheduler>(
                    std::move(per_worker), num_workers
                );
            }
            
            default:
                return std::make_unique<RoundRobinScheduler>(std::move(instances));
        }
    }
};

} // namespace klstream
