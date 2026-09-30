#pragma once

#include <klstream/core/config.hpp>
#include <atomic>
#include <stdexcept>
#include <limits>
#include <cstddef>
#include <memory>
#include <new>
#include <optional>
#include <type_traits>
#include <thread>
#include <chrono>

namespace klstream {

// ── SPSCQueue<T> ─────────────────────────────────────────────────────────
//
// A bounded single-producer / single-consumer ring buffer using atomics.
// Check platform atomic progress properties before making lock-freedom claims.
//
// CORRECTNESS CONTRACT (INV-008):
//   * Exactly one thread calls push() or try_push() at a time (the producer).
//   * Exactly one thread calls pop() or try_pop() at a time (the consumer).
//   * T must be trivially copyable (POD-like).
//   * Usable slot capacity is strictly (capacity - 1) to distinguish full from empty.
//   * Synchronization uses std::memory_order_release / std::memory_order_acquire.

template <typename T>
class SPSCQueue {
    static_assert(std::is_trivially_copyable_v<T>,
        "SPSCQueue<T>: T must be trivially copyable. "
        "Use trivially copyable values; shared_ptr is not supported.");

public:
    // capacity must be a power of 2 and >= 2.
    explicit SPSCQueue(std::size_t capacity = DEFAULT_QUEUE_CAPACITY)
        : capacity_(checked_capacity(capacity))
        , mask_(capacity_ - 1)
        , buffer_(new T[capacity_] {})
    {}

    ~SPSCQueue() = default;

    // Non-copyable, non-movable (owns storage and atomics).
    SPSCQueue(const SPSCQueue&)            = delete;
    SPSCQueue& operator=(const SPSCQueue&) = delete;
    SPSCQueue(SPSCQueue&&)                 = delete;
    SPSCQueue& operator=(SPSCQueue&&)      = delete;

    // ── Producer side ─────────────────────────────────────────────────────

    // try_push: returns true on success, false if the queue is full.
    // Call from exactly ONE producer thread.
    [[nodiscard]] bool try_push(const T& val) noexcept {
        const std::size_t wi = write_idx_.load(std::memory_order_relaxed);
        const std::size_t next_wi = (wi + 1) & mask_;

        // Fast path: use cached read index.
        if (next_wi == write_idx_cached_) {
            write_idx_cached_ = read_idx_.load(std::memory_order_acquire);
            if (next_wi == write_idx_cached_) {
                return false; // Queue is full.
            }
        }
        if (!running_.load(std::memory_order_acquire)) return false;
        buffer_[wi] = val;
        write_idx_.store(next_wi, std::memory_order_release);
        return true;
    }

    // Blocking push: spins with backoff until space is available or stop() called.
    // Returns true on success, false if stopped before completing push.
    bool push(const T& val) noexcept {
        int spin = 0, yields = 0;
        while (!try_push(val)) {
            if (!running_.load(std::memory_order_relaxed)) {
                return false;
            }
            if (spin < SPIN_BEFORE_YIELD) {
                ++spin;
#if defined(__aarch64__)
                __asm__ volatile("yield" ::: "memory");
#elif defined(__x86_64__)
                __asm__ volatile("pause" ::: "memory");
#endif
            } else if (yields < YIELD_BEFORE_SLEEP) {
                ++yields;
                std::this_thread::yield();
            } else {
                std::this_thread::sleep_for(
                    std::chrono::nanoseconds(SLEEP_NS));
            }
        }
        return true;
    }

    // ── Consumer side ─────────────────────────────────────────────────────

    // try_pop: writes front element into *out and returns true, or false if empty.
    [[nodiscard]] bool try_pop(T* out) noexcept {
        if (out == nullptr) return false;
        const std::size_t ri = read_idx_.load(std::memory_order_relaxed);

        // Fast path: use cached write index.
        if (ri == read_idx_cached_) {
            read_idx_cached_ = write_idx_.load(std::memory_order_acquire);
            if (ri == read_idx_cached_) {
                return false; // Queue is empty.
            }
        }
        *out = buffer_[ri];
        read_idx_.store((ri + 1) & mask_, std::memory_order_release);
        return true;
    }

    // Reference overload
    [[nodiscard]] bool try_pop(T& out) noexcept {
        return try_pop(&out);
    }

    // Blocking pop: spins with backoff until an item is available or stop() called.
    // Returns true on success, false if stopped while empty.
    bool pop(T& out) noexcept {
        int spin = 0, yields = 0;
        while (!try_pop(out)) {
            if (!running_.load(std::memory_order_relaxed)) {
                return try_pop(out);
            }
            if (spin < SPIN_BEFORE_YIELD) {
                ++spin;
#if defined(__aarch64__)
                __asm__ volatile("yield" ::: "memory");
#elif defined(__x86_64__)
                __asm__ volatile("pause" ::: "memory");
#endif
            } else if (yields < YIELD_BEFORE_SLEEP) {
                ++yields;
                std::this_thread::yield();
            } else {
                std::this_thread::sleep_for(
                    std::chrono::nanoseconds(SLEEP_NS));
            }
        }
        return true;
    }

    // Convenience: returns std::nullopt when empty.
    std::optional<T> pop() noexcept {
        T val;
        if (try_pop(&val)) return val;
        return std::nullopt;
    }

    // ── Control & Inspection ──────────────────────────────────────────────

    // Close only after producers are quiescent. Consumers may drain existing values.
    void close() noexcept {
        stop();
    }

    [[nodiscard]] bool is_drained() const noexcept {
        return !is_running() && empty();
    }

    void stop() noexcept {
        running_.store(false, std::memory_order_release);
    }

    [[nodiscard]] bool is_running() const noexcept {
        return running_.load(std::memory_order_acquire);
    }

    // Approximate occupancy in [0.0, 1.0].
    [[nodiscard]] double occupancy() const noexcept {
        const std::size_t wi = write_idx_.load(std::memory_order_relaxed);
        const std::size_t ri = read_idx_.load(std::memory_order_relaxed);
        const std::size_t used = (wi - ri + capacity_) & mask_;
        const std::size_t max_usable = capacity_ - 1;
        if (max_usable == 0) return 0.0;
        return static_cast<double>(used) / static_cast<double>(max_usable);
    }

    [[nodiscard]] std::size_t size_approx() const noexcept {
        const std::size_t wi = write_idx_.load(std::memory_order_relaxed);
        const std::size_t ri = read_idx_.load(std::memory_order_relaxed);
        return (wi - ri + capacity_) & mask_;
    }

    [[nodiscard]] std::size_t capacity() const noexcept { return capacity_; }
    [[nodiscard]] std::size_t usable_capacity() const noexcept { return capacity_ - 1; }

    [[nodiscard]] bool empty() const noexcept {
        return write_idx_.load(std::memory_order_acquire)
            == read_idx_.load(std::memory_order_acquire);
    }

private:
    static std::size_t checked_capacity(std::size_t n) {
        if (n < 2 || (n & (n - 1)) != 0 || n > std::numeric_limits<std::size_t>::max() / sizeof(T))
            throw std::invalid_argument("SPSCQueue capacity must be a representable power of two >= 2");
        return n;
    }
    alignas(CACHE_LINE_SIZE) std::atomic<std::size_t> write_idx_{0};
    alignas(CACHE_LINE_SIZE) std::size_t              write_idx_cached_{0};
    alignas(CACHE_LINE_SIZE) std::atomic<std::size_t> read_idx_{0};
    alignas(CACHE_LINE_SIZE) std::size_t              read_idx_cached_{0};
    alignas(CACHE_LINE_SIZE) std::atomic<bool>        running_{true};

    const std::size_t capacity_;
    const std::size_t mask_;
    std::unique_ptr<T[]> buffer_; // typed allocation starts object lifetimes in C++17
};

} // namespace klstream
