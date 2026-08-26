// include/klstream/core/spsc_queue.hpp
#pragma once
#include "config.hpp"
#include <atomic>
#include <cassert>
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
// A bounded, lock-free, single-producer / single-consumer ring buffer.
//
// CORRECTNESS CONTRACT (do not violate):
//   * Exactly one thread calls push() or try_push() at a time (the producer).
//   * Exactly one thread calls pop() or try_pop() at a time (the consumer).
//   * These two threads may be different OS threads — that is the whole point.
//   * T must be trivially copyable (POD-like). For complex types, wrap them
//     in a std::shared_ptr before putting them in an Event.
//
// MEMORY LAYOUT (cache-line padded to prevent false sharing):
//
//   [padding 0]          <- start on cache line boundary
//   write_idx_           <- producer writes, consumer reads (release/acquire)
//   [padding 1]          <- isolate write_idx_ from read_idx_
//   write_idx_cached_    <- producer's local shadow of read_idx_ (relaxed)
//   [padding 2]
//   read_idx_            <- consumer writes, producer reads (release/acquire)
//   [padding 3]          <- isolate read_idx_ from write_idx_
//   read_idx_cached_     <- consumer's local shadow of write_idx_ (relaxed)
//   [padding 4]
//   capacity_            <- const after construction
//   buffer_              <- the actual ring, heap-allocated, cache-line aligned
//
// WHY CACHED INDICES:
//   In the fast path (queue neither full nor empty), the producer only ever
//   reads its own write_idx_ and its cached copy of read_idx_. It never
//   touches the cache line that the consumer is modifying. This eliminates
//   MESI "RFO" (Request For Ownership) cache-line ping-pong, which is the
//   dominant cost in naive implementations.

template <typename T>
class SPSCQueue {
    static_assert(std::is_trivially_copyable_v<T>,
        "SPSCQueue<T>: T must be trivially copyable. "
        "Wrap complex types in std::shared_ptr.");

public:
    // capacity must be a power of 2 and >= 2.
    explicit SPSCQueue(std::size_t capacity = DEFAULT_QUEUE_CAPACITY)
        : capacity_(capacity)
        , buffer_(static_cast<T*>(
            ::operator new(capacity * sizeof(T),
                           std::align_val_t{CACHE_LINE_SIZE})))
    {
        assert(capacity >= 2 && "SPSCQueue capacity must be >= 2");
        assert((capacity & (capacity - 1)) == 0 &&
               "SPSCQueue capacity must be a power of 2");
    }

    ~SPSCQueue() {
        ::operator delete(buffer_,
            std::align_val_t{CACHE_LINE_SIZE});
    }

    // Non-copyable, non-movable (contains raw pointer + atomics).
    SPSCQueue(const SPSCQueue&)            = delete;
    SPSCQueue& operator=(const SPSCQueue&) = delete;
    SPSCQueue(SPSCQueue&&)                 = delete;
    SPSCQueue& operator=(SPSCQueue&&)      = delete;

    // ── Producer side ─────────────────────────────────────────────────────

    // try_push: returns true on success, false if the queue is full.
    // Call from exactly ONE producer thread.
    [[nodiscard]] bool try_push(const T& val) noexcept {
        const std::size_t wi = write_idx_.load(std::memory_order_relaxed);
        const std::size_t next_wi = (wi + 1) & (capacity_ - 1);

        // Fast path: use cached read index.
        if (next_wi == write_idx_cached_) {
            // Cached value says queue might be full. Re-read the real index.
            write_idx_cached_ = read_idx_.load(std::memory_order_acquire);
            if (next_wi == write_idx_cached_) {
                return false; // Queue is actually full.
            }
        }
        buffer_[wi] = val;
        // Release: make the write visible to the consumer before we advance
        // write_idx_. The consumer will see the updated index and then read
        // the element we just wrote.
        write_idx_.store(next_wi, std::memory_order_release);
        return true;
    }

    // Blocking push: spins with three-tier backoff until space is available.
    // Not recommended in the hot path — prefer try_push() + OpStatus::Blocked.
    void push(const T& val) noexcept {
        int spin = 0, yields = 0;
        while (!try_push(val)) {
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
    }

    // ── Consumer side ─────────────────────────────────────────────────────

    // try_pop: writes the front element into *out and returns true, or
    // returns false if the queue is empty. out must not be null.
    [[nodiscard]] bool try_pop(T* out) noexcept {
        const std::size_t ri = read_idx_.load(std::memory_order_relaxed);

        // Fast path: use cached write index.
        if (ri == read_idx_cached_) {
            read_idx_cached_ = write_idx_.load(std::memory_order_acquire);
            if (ri == read_idx_cached_) {
                return false; // Queue is actually empty.
            }
        }
        *out = buffer_[ri];
        read_idx_.store((ri + 1) & (capacity_ - 1),
                        std::memory_order_release);
        return true;
    }

    // Convenience: returns std::nullopt when empty.
    std::optional<T> pop() noexcept {
        T val;
        if (try_pop(&val)) return val;
        return std::nullopt;
    }

    // ── Inspection ────────────────────────────────────────────────────────

    // Approximate occupancy [0.0, 1.0]. Approximate because read and write
    // indices are read with relaxed ordering — the result may be stale.
    // Good enough for the EMA tracker in backpressure.hpp.
    [[nodiscard]] double occupancy() const noexcept {
        const std::size_t wi = write_idx_.load(std::memory_order_relaxed);
        const std::size_t ri = read_idx_.load(std::memory_order_relaxed);
        const std::size_t used = (wi - ri + capacity_) & (capacity_ - 1);
        return static_cast<double>(used) / static_cast<double>(capacity_);
    }

    [[nodiscard]] std::size_t capacity() const noexcept { return capacity_; }

    [[nodiscard]] bool empty() const noexcept {
        return write_idx_.load(std::memory_order_acquire)
            == read_idx_.load(std::memory_order_acquire);
    }

private:
    // Each hot atomic lives on its own 128-byte cache line.
    // The layout is: pad | atomic | cache-shadow | pad | atomic | cache-shadow | pad
    // so that no two of these four values share a cache line.

    alignas(CACHE_LINE_SIZE) std::atomic<std::size_t> write_idx_{0};
    alignas(CACHE_LINE_SIZE) std::size_t              write_idx_cached_{0};
    alignas(CACHE_LINE_SIZE) std::atomic<std::size_t> read_idx_{0};
    alignas(CACHE_LINE_SIZE) std::size_t              read_idx_cached_{0};

    const std::size_t capacity_;
    T*                buffer_;   // heap-allocated, CACHE_LINE_SIZE-aligned
};

} // namespace klstream
