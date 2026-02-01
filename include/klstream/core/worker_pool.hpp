#pragma once

/**
 * @file worker_pool.hpp
 * @brief Worker thread pool management
 */

#include <thread>
#include <vector>
#include <atomic>
#include <functional>
#include <condition_variable>
#include <mutex>

#include "klstream/core/scheduler.hpp"

namespace klstream {

/**
 * @brief Worker thread statistics
 */
struct WorkerStats {
    std::uint64_t events_processed{0};
    std::uint64_t idle_time_ns{0};
    std::uint64_t active_time_ns{0};
    std::uint64_t iterations{0};
};

/**
 * @brief Individual worker thread
 */
class Worker {
public:
    Worker(std::uint32_t id, Scheduler* scheduler)
        : id_(id)
        , scheduler_(scheduler) {}
    
    /**
     * @brief Start the worker thread
     */
    void start() {
        running_.store(true, std::memory_order_release);
        thread_ = std::thread(&Worker::run, this);
    }
    
    /**
     * @brief Stop the worker thread
     */
    void stop() {
        running_.store(false, std::memory_order_release);
        cv_.notify_all();
    }
    
    /**
     * @brief Wait for the worker thread to finish
     */
    void join() {
        if (thread_.joinable()) {
            thread_.join();
        }
    }
    
    /**
     * @brief Wake up the worker if it's sleeping
     */
    void wake() {
        cv_.notify_one();
    }
    
    [[nodiscard]] std::uint32_t id() const noexcept { return id_; }
    [[nodiscard]] const WorkerStats& stats() const noexcept { return stats_; }
    
    [[nodiscard]] bool is_running() const noexcept {
        return running_.load(std::memory_order_acquire);
    }

private:
    void run() {
        while (running_.load(std::memory_order_acquire)) {
            stats_.iterations++;
            
            auto start = std::chrono::steady_clock::now();
            
            // Get next operator to execute
            auto* instance = scheduler_->next(id_);
            
            if (instance) {
                // Execute batch of events
                auto processed = instance->execute_batch(64);
                stats_.events_processed += processed;
                
                auto end = std::chrono::steady_clock::now();
                auto ns = std::chrono::duration_cast<std::chrono::nanoseconds>(end - start).count();
                stats_.active_time_ns += static_cast<std::uint64_t>(ns);
            } else {
                // No work available, yield or sleep
                auto end = std::chrono::steady_clock::now();
                auto ns = std::chrono::duration_cast<std::chrono::nanoseconds>(end - start).count();
                stats_.idle_time_ns += static_cast<std::uint64_t>(ns);
                
                // Brief yield to avoid spinning
                std::this_thread::yield();
            }
        }
    }
    
    std::uint32_t id_;
    Scheduler* scheduler_;
    std::thread thread_;
    std::atomic<bool> running_{false};
    std::condition_variable cv_;
    std::mutex mutex_;
    WorkerStats stats_;
};

/**
 * @brief Configuration for worker pool
 */
struct WorkerPoolConfig {
    std::uint32_t num_workers{0};  // 0 = auto-detect
    bool pin_threads{false};       // Pin threads to CPU cores
    SchedulingPolicy policy{SchedulingPolicy::RoundRobin};
};

/**
 * @brief Pool of worker threads
 */
class WorkerPool {
public:
    explicit WorkerPool(WorkerPoolConfig config = {})
        : config_(config) {
        if (config_.num_workers == 0) {
            config_.num_workers = std::thread::hardware_concurrency();
            if (config_.num_workers == 0) {
                config_.num_workers = 4;  // Fallback
            }
        }
    }
    
    ~WorkerPool() {
        stop();
    }
    
    // Non-copyable, non-movable
    WorkerPool(const WorkerPool&) = delete;
    WorkerPool& operator=(const WorkerPool&) = delete;
    
    /**
     * @brief Initialize the worker pool with a scheduler
     */
    void init(Scheduler* scheduler) {
        scheduler_ = scheduler;
        workers_.reserve(config_.num_workers);
        
        for (std::uint32_t i = 0; i < config_.num_workers; i++) {
            workers_.push_back(std::make_unique<Worker>(i, scheduler_));
        }
    }
    
    /**
     * @brief Start all worker threads
     */
    void start() {
        for (auto& worker : workers_) {
            worker->start();
        }
        running_ = true;
    }
    
    /**
     * @brief Stop all worker threads
     */
    void stop() {
        if (!running_) return;
        
        running_ = false;
        for (auto& worker : workers_) {
            worker->stop();
        }
        for (auto& worker : workers_) {
            worker->join();
        }
    }
    
    /**
     * @brief Wake all workers
     */
    void wake_all() {
        for (auto& worker : workers_) {
            worker->wake();
        }
    }
    
    [[nodiscard]] std::uint32_t num_workers() const noexcept {
        return config_.num_workers;
    }
    
    [[nodiscard]] bool is_running() const noexcept {
        return running_;
    }
    
    /**
     * @brief Get aggregated worker statistics
     */
    [[nodiscard]] std::vector<WorkerStats> stats() const {
        std::vector<WorkerStats> result;
        result.reserve(workers_.size());
        for (const auto& worker : workers_) {
            result.push_back(worker->stats());
        }
        return result;
    }

private:
    WorkerPoolConfig config_;
    Scheduler* scheduler_{nullptr};
    std::vector<std::unique_ptr<Worker>> workers_;
    std::atomic<bool> running_{false};
};

} // namespace klstream
