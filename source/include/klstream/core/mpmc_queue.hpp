#pragma once

#include <klstream/core/config.hpp>
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

// ── MPMCQueue<T> ─────────────────────────────────────────────────────────
//
// A bounded, multi-producer multi-consumer lock-free queue based on Dmitry
// Vyukov's turn-based per-slot sequence counters.
//
// CORRECTNESS CONTRACT (INV-008, FR-002):
//   * Multiple producer threads may concurrently call push() or try_push().
//   * Multiple consumer threads may concurrently call pop() or try_pop().
//   * T must be trivially copyable.
//   * All `capacity` slots are usable.
//   * Memory ordering: acquire on sequence check, release on sequence advance.

template <typename T>
class MPMCQueue {
    static_assert(std::is_trivially_copyable_v<T>,
        "MPMCQueue<T>: T must be trivially copyable.");

    struct Slot {
        alignas(CACHE_LINE_SIZE) std::atomic<std::size_t> seq;
        T data;
    };

public:
    explicit MPMCQueue(std::size_t capacity = DEFAULT_QUEUE_CAPACITY)
        : capacity_(capacity)
        , mask_(capacity - 1)
        , buffer_(static_cast<Slot*>(
            ::operator new(capacity * sizeof(Slot),
                           std::align_val_t{CACHE_LINE_SIZE})))
    {
        assert(capacity >= 2);
        assert((capacity & (capacity - 1)) == 0 &&
               "MPMCQueue capacity must be a power of 2");
        for (std::size_t i = 0; i < capacity; ++i) {
            buffer_[i].seq.store(i, std::memory_order_relaxed);
        }
    }

    ~MPMCQueue() {
        stop();
        ::operator delete(buffer_,
            std::align_val_t{CACHE_LINE_SIZE});
    }

    MPMCQueue(const MPMCQueue&)            = delete;
    MPMCQueue& operator=(const MPMCQueue&) = delete;
    MPMCQueue(MPMCQueue&&)                 = delete;
    MPMCQueue& operator=(MPMCQueue&&)      = delete;

    // ── Enqueue ───────────────────────────────────────────────────────────

    [[nodiscard]] bool try_push(const T& val) noexcept {
        std::size_t pos = enqueue_pos_.load(std::memory_order_relaxed);
        for (;;) {
            Slot& slot = buffer_[pos & mask_];
            std::size_t seq = slot.seq.load(std::memory_order_acquire);
            std::ptrdiff_t diff = static_cast<std::ptrdiff_t>(seq)
                                - static_cast<std::ptrdiff_t>(pos);
            if (diff == 0) {
                // Slot is free — try to claim it.
                if (enqueue_pos_.compare_exchange_weak(
                        pos, pos + 1, std::memory_order_relaxed)) {
                    slot.data = val;
                    slot.seq.store(pos + 1, std::memory_order_release);
                    return true;
                }
            } else if (diff < 0) {
                return false; // Queue is full.
            } else {
                pos = enqueue_pos_.load(std::memory_order_relaxed);
            }
        }
    }

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

    // ── Dequeue ───────────────────────────────────────────────────────────

    [[nodiscard]] bool try_pop(T* out) noexcept {
        if (out == nullptr) return false;
        std::size_t pos = dequeue_pos_.load(std::memory_order_relaxed);
        for (;;) {
            Slot& slot = buffer_[pos & mask_];
            std::size_t seq = slot.seq.load(std::memory_order_acquire);
            std::ptrdiff_t diff = static_cast<std::ptrdiff_t>(seq)
                                - static_cast<std::ptrdiff_t>(pos + 1);
            if (diff == 0) {
                if (dequeue_pos_.compare_exchange_weak(
                        pos, pos + 1, std::memory_order_relaxed)) {
                    *out = slot.data;
                    slot.seq.store(pos + mask_ + 1,
                                   std::memory_order_release);
                    return true;
                }
            } else if (diff < 0) {
                return false; // Queue is empty.
            } else {
                pos = dequeue_pos_.load(std::memory_order_relaxed);
            }
        }
    }

    [[nodiscard]] bool try_pop(T& out) noexcept {
        return try_pop(&out);
    }

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

    std::optional<T> pop() noexcept {
        T val;
        if (try_pop(&val)) return val;
        return std::nullopt;
    }

    // ── Inspection & Control ──────────────────────────────────────────────

    void stop() noexcept {
        running_.store(false, std::memory_order_release);
    }

    [[nodiscard]] bool is_running() const noexcept {
        return running_.load(std::memory_order_acquire);
    }

    // Approximate occupancy in [0.0, 1.0].
    [[nodiscard]] double occupancy() const noexcept {
        const std::size_t ep = enqueue_pos_.load(std::memory_order_relaxed);
        const std::size_t dp = dequeue_pos_.load(std::memory_order_relaxed);
        const std::size_t used = (ep >= dp) ? (ep - dp) : 0;
        const std::size_t clamped = (used > capacity_) ? capacity_ : used;
        return static_cast<double>(clamped) / static_cast<double>(capacity_);
    }

    [[nodiscard]] std::size_t size_approx() const noexcept {
        const std::size_t ep = enqueue_pos_.load(std::memory_order_relaxed);
        const std::size_t dp = dequeue_pos_.load(std::memory_order_relaxed);
        const std::size_t used = (ep >= dp) ? (ep - dp) : 0;
        return (used > capacity_) ? capacity_ : used;
    }

    [[nodiscard]] std::size_t capacity() const noexcept { return capacity_; }

    [[nodiscard]] bool empty() const noexcept {
        const std::size_t ep = enqueue_pos_.load(std::memory_order_acquire);
        const std::size_t dp = dequeue_pos_.load(std::memory_order_acquire);
        return ep <= dp;
    }

private:
    const std::size_t capacity_;
    const std::size_t mask_;
    Slot*             buffer_;

    alignas(CACHE_LINE_SIZE) std::atomic<std::size_t> enqueue_pos_{0};
    alignas(CACHE_LINE_SIZE) std::atomic<std::size_t> dequeue_pos_{0};
    alignas(CACHE_LINE_SIZE) std::atomic<bool>        running_{true};
};

} // namespace klstream
