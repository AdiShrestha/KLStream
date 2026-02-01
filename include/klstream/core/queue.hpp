#pragma once

/**
 * @file queue.hpp
 * @brief Bounded, thread-safe queue with backpressure support
 */

#include <atomic>
#include <array>
#include <optional>
#include <chrono>
#include <condition_variable>
#include <mutex>

#include "klstream/core/event.hpp"

namespace klstream {

/**
 * @brief Queue statistics for monitoring
 */
struct QueueStats {
    std::uint64_t push_count{0};
    std::uint64_t pop_count{0};
    std::uint64_t push_blocked_count{0};
    std::uint64_t pop_blocked_count{0};
    std::size_t current_size{0};
    std::size_t capacity{0};
    std::size_t high_watermark{0};
};

/**
 * @brief Bounded MPMC (Multi-Producer Multi-Consumer) queue
 * 
 * Thread-safe bounded queue that enforces backpressure when full.
 * Uses a ring buffer implementation with condition variables for
 * blocking operations.
 * 
 * @tparam Capacity Static queue capacity (must be power of 2)
 */
template<std::size_t Capacity = 1024>
class BoundedQueue {
    static_assert((Capacity & (Capacity - 1)) == 0, "Capacity must be power of 2");
    static_assert(Capacity > 0, "Capacity must be positive");
    
public:
    BoundedQueue() = default;
    
    // Non-copyable, non-movable (due to synchronization primitives)
    BoundedQueue(const BoundedQueue&) = delete;
    BoundedQueue& operator=(const BoundedQueue&) = delete;
    BoundedQueue(BoundedQueue&&) = delete;
    BoundedQueue& operator=(BoundedQueue&&) = delete;
    
    /**
     * @brief Push an event to the queue, blocking if full
     * @param event Event to push
     * @return true if pushed successfully, false if queue is closed
     */
    bool push(Event event) {
        std::unique_lock<std::mutex> lock(mutex_);
        
        stats_.push_count++;
        
        // Wait for space or closure
        while (size_ == Capacity && !closed_) {
            stats_.push_blocked_count++;
            not_full_.wait(lock);
        }
        
        if (closed_) {
            return false;
        }
        
        buffer_[tail_] = std::move(event);
        tail_ = (tail_ + 1) & (Capacity - 1);
        size_++;
        
        if (size_ > stats_.high_watermark) {
            stats_.high_watermark = size_;
        }
        stats_.current_size = size_;
        
        lock.unlock();
        not_empty_.notify_one();
        
        return true;
    }
    
    /**
     * @brief Try to push without blocking
     * @param event Event to push
     * @return true if pushed, false if full or closed
     */
    bool try_push(Event event) {
        std::lock_guard<std::mutex> lock(mutex_);
        
        if (size_ == Capacity || closed_) {
            return false;
        }
        
        stats_.push_count++;
        buffer_[tail_] = std::move(event);
        tail_ = (tail_ + 1) & (Capacity - 1);
        size_++;
        
        if (size_ > stats_.high_watermark) {
            stats_.high_watermark = size_;
        }
        stats_.current_size = size_;
        
        not_empty_.notify_one();
        return true;
    }
    
    /**
     * @brief Push with timeout
     * @param event Event to push
     * @param timeout Maximum wait duration
     * @return true if pushed, false if timeout or closed
     */
    template<typename Rep, typename Period>
    bool push_for(Event event, std::chrono::duration<Rep, Period> timeout) {
        std::unique_lock<std::mutex> lock(mutex_);
        
        stats_.push_count++;
        
        if (!not_full_.wait_for(lock, timeout, [this] {
            return size_ < Capacity || closed_;
        })) {
            stats_.push_blocked_count++;
            return false;
        }
        
        if (closed_) {
            return false;
        }
        
        buffer_[tail_] = std::move(event);
        tail_ = (tail_ + 1) & (Capacity - 1);
        size_++;
        
        if (size_ > stats_.high_watermark) {
            stats_.high_watermark = size_;
        }
        stats_.current_size = size_;
        
        lock.unlock();
        not_empty_.notify_one();
        
        return true;
    }
    
    /**
     * @brief Pop an event from the queue, blocking if empty
     * @return Event if available, nullopt if queue is closed and empty
     */
    std::optional<Event> pop() {
        std::unique_lock<std::mutex> lock(mutex_);
        
        stats_.pop_count++;
        
        // Wait for data or closure
        while (size_ == 0 && !closed_) {
            stats_.pop_blocked_count++;
            not_empty_.wait(lock);
        }
        
        if (size_ == 0) {
            return std::nullopt;
        }
        
        Event event = std::move(buffer_[head_]);
        head_ = (head_ + 1) & (Capacity - 1);
        size_--;
        stats_.current_size = size_;
        
        lock.unlock();
        not_full_.notify_one();
        
        return event;
    }
    
    /**
     * @brief Try to pop without blocking
     * @return Event if available, nullopt if empty
     */
    std::optional<Event> try_pop() {
        std::lock_guard<std::mutex> lock(mutex_);
        
        if (size_ == 0) {
            return std::nullopt;
        }
        
        stats_.pop_count++;
        Event event = std::move(buffer_[head_]);
        head_ = (head_ + 1) & (Capacity - 1);
        size_--;
        stats_.current_size = size_;
        
        not_full_.notify_one();
        return event;
    }
    
    /**
     * @brief Pop with timeout
     * @param timeout Maximum wait duration
     * @return Event if available, nullopt if timeout or closed+empty
     */
    template<typename Rep, typename Period>
    std::optional<Event> pop_for(std::chrono::duration<Rep, Period> timeout) {
        std::unique_lock<std::mutex> lock(mutex_);
        
        stats_.pop_count++;
        
        if (!not_empty_.wait_for(lock, timeout, [this] {
            return size_ > 0 || closed_;
        })) {
            stats_.pop_blocked_count++;
            return std::nullopt;
        }
        
        if (size_ == 0) {
            return std::nullopt;
        }
        
        Event event = std::move(buffer_[head_]);
        head_ = (head_ + 1) & (Capacity - 1);
        size_--;
        stats_.current_size = size_;
        
        lock.unlock();
        not_full_.notify_one();
        
        return event;
    }
    
    /**
     * @brief Close the queue (no more pushes accepted)
     */
    void close() {
        {
            std::lock_guard<std::mutex> lock(mutex_);
            closed_ = true;
        }
        not_full_.notify_all();
        not_empty_.notify_all();
    }
    
    /**
     * @brief Check if queue is closed
     */
    [[nodiscard]] bool is_closed() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return closed_;
    }
    
    /**
     * @brief Get current queue size
     */
    [[nodiscard]] std::size_t size() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return size_;
    }
    
    /**
     * @brief Check if queue is empty
     */
    [[nodiscard]] bool empty() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return size_ == 0;
    }
    
    /**
     * @brief Check if queue is full
     */
    [[nodiscard]] bool full() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return size_ == Capacity;
    }
    
    /**
     * @brief Get queue capacity
     */
    [[nodiscard]] static constexpr std::size_t capacity() noexcept {
        return Capacity;
    }
    
    /**
     * @brief Get queue statistics
     */
    [[nodiscard]] QueueStats stats() const {
        std::lock_guard<std::mutex> lock(mutex_);
        auto s = stats_;
        s.capacity = Capacity;
        return s;
    }

private:
    mutable std::mutex mutex_;
    std::condition_variable not_full_;
    std::condition_variable not_empty_;
    
    std::array<Event, Capacity> buffer_;
    std::size_t head_{0};
    std::size_t tail_{0};
    std::size_t size_{0};
    bool closed_{false};
    
    QueueStats stats_;
};

/**
 * @brief Default queue type with reasonable capacity
 */
using Queue = BoundedQueue<4096>;

/**
 * @brief Small queue for low-latency scenarios
 */
using SmallQueue = BoundedQueue<256>;

/**
 * @brief Large queue for high-throughput scenarios
 */
using LargeQueue = BoundedQueue<65536>;

} // namespace klstream
