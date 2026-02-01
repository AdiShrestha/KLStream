/**
 * @file runtime.cpp
 * @brief Runtime implementation
 */

#include "klstream/core/runtime.hpp"

#include <algorithm>
#include <iostream>

namespace klstream {

Runtime::Runtime(RuntimeConfig config)
    : config_(std::move(config))
    , metrics_(std::make_unique<MetricsCollector>()) {}

Runtime::~Runtime() {
    stop();
}

void Runtime::init(StreamGraphBuilder builder) {
    if (state_ != RuntimeState::Created) {
        throw std::runtime_error("Runtime already initialized");
    }
    
    // Create queues for each edge
    std::unordered_map<std::string, std::vector<std::shared_ptr<Queue>>> output_queues;
    std::unordered_map<std::string, std::shared_ptr<Queue>> input_queues;
    
    for (const auto& edge : builder.edges()) {
        auto queue = std::make_shared<Queue>();
        queues_.push_back(queue);
        output_queues[edge.from_operator].push_back(queue);
        input_queues[edge.to_operator] = queue;
    }
    
    // Create operator instances
    std::vector<OperatorInstance*> all_instances;
    
    for (auto& [name, op] : builder.operators()) {
        auto input_it = input_queues.find(name);
        std::shared_ptr<Queue> input = input_it != input_queues.end() 
            ? input_it->second 
            : nullptr;
        
        // Check if this is a source operator
        if (auto* source = dynamic_cast<SourceOperator*>(op.get())) {
            source_operators_.push_back(source);
        }
        
        auto instance = std::make_unique<OperatorInstance>(
            std::move(op), input, 0
        );
        
        // Connect output queues
        auto output_it = output_queues.find(name);
        if (output_it != output_queues.end()) {
            for (auto& out_queue : output_it->second) {
                instance->context().add_output(out_queue);
            }
        }
        
        all_instances.push_back(instance.get());
        instances_.push_back(std::move(instance));
    }
    
    // Initialize scheduler
    std::uint32_t num_workers = config_.num_workers;
    if (num_workers == 0) {
        num_workers = std::thread::hardware_concurrency();
        if (num_workers == 0) num_workers = 4;
    }
    
    scheduler_ = SchedulerFactory::create(
        config_.scheduling_policy,
        all_instances,
        num_workers
    );
    
    // Initialize worker pool
    WorkerPoolConfig pool_config;
    pool_config.num_workers = num_workers;
    pool_config.policy = config_.scheduling_policy;
    
    worker_pool_ = std::make_unique<WorkerPool>(pool_config);
    worker_pool_->init(scheduler_.get());
    
    // Initialize operators
    for (auto& instance : instances_) {
        instance->op()->init(instance->context());
    }
    
    state_ = RuntimeState::Initialized;
}

void Runtime::start() {
    if (state_ != RuntimeState::Initialized) {
        throw std::runtime_error("Runtime not initialized");
    }
    
    running_.store(true, std::memory_order_release);
    state_ = RuntimeState::Running;
    
    // Start worker threads
    worker_pool_->start();
    
    // Start source threads
    run_sources();
}

void Runtime::run_sources() {
    for (auto* source : source_operators_) {
        source_threads_.emplace_back([this, source]() {
            // Find the instance for this source
            OperatorInstance* instance = nullptr;
            for (auto& inst : instances_) {
                if (inst->op() == source) {
                    instance = inst.get();
                    break;
                }
            }
            
            if (!instance) return;
            
            while (running_.load(std::memory_order_acquire) && !source->should_stop()) {
                if (!source->generate(instance->context())) {
                    break;
                }
                metrics_->events_processed().increment();
            }
        });
    }
}

void Runtime::stop() {
    if (state_ != RuntimeState::Running) {
        return;
    }
    
    state_ = RuntimeState::ShuttingDown;
    
    // Stop sources first
    for (auto* source : source_operators_) {
        source->request_stop();
    }
    
    // Wait for source threads
    for (auto& t : source_threads_) {
        if (t.joinable()) {
            t.join();
        }
    }
    source_threads_.clear();
    
    // Drain queues
    drain_queues();
    
    // Stop running
    running_.store(false, std::memory_order_release);
    
    // Close all queues
    for (auto& queue : queues_) {
        queue->close();
    }
    
    // Stop workers
    worker_pool_->stop();
    
    // Shutdown operators
    for (auto& instance : instances_) {
        instance->op()->shutdown(instance->context());
    }
    
    state_ = RuntimeState::Stopped;
}

void Runtime::drain_queues() {
    bool has_work = true;
    while (has_work) {
        has_work = false;
        for (auto& queue : queues_) {
            if (!queue->empty()) {
                has_work = true;
                break;
            }
        }
        if (has_work) {
            std::this_thread::sleep_for(std::chrono::milliseconds(10));
        }
    }
}

void Runtime::await_completion() {
    for (auto& t : source_threads_) {
        if (t.joinable()) {
            t.join();
        }
    }
}

} // namespace klstream
