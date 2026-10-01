#pragma once

#include <klstream/core/config.hpp>
#include <klstream/core/queue_state.hpp>
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

// ── MPMCQueue<T> ─────────────────────────────────────────────────────────
//
// A bounded, multi-producer multi-consumer queue using atomic operations based on Dmitry
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
        : capacity_(checked_capacity(capacity))
        , mask_(capacity_ - 1)
        , buffer_(new Slot[capacity_] {})
    {
        for (std::size_t i = 0; i < capacity_; ++i)
            buffer_[i].seq.store(i, std::memory_order_relaxed);
    }
    ~MPMCQueue() = default;

    MPMCQueue(const MPMCQueue&)            = delete;
    MPMCQueue& operator=(const MPMCQueue&) = delete;
    MPMCQueue(MPMCQueue&&)                 = delete;
    MPMCQueue& operator=(MPMCQueue&&)      = delete;

    // ── Enqueue ───────────────────────────────────────────────────────────

    [[nodiscard]] bool try_push(const T& val) noexcept {
        if (!is_running()) return false;
        std::size_t pos = enqueue_pos_.load(std::memory_order_relaxed);
        for (;;) {
            Slot& slot = buffer_[pos & mask_];
            std::size_t seq = slot.seq.load(std::memory_order_acquire);
            std::size_t diff = seq - pos;
            if (diff == 0) {
                // Slot is free — try to claim it.
                if (enqueue_pos_.compare_exchange_weak(
                        pos, pos + 1, std::memory_order_relaxed)) {
                    slot.data = val;
                    slot.seq.store(pos + 1, std::memory_order_release);
                    return true;
                }
            } else if (diff > std::numeric_limits<std::size_t>::max() / 2) {
                return false; // Queue is full.
            } else {
                pos = enqueue_pos_.load(std::memory_order_relaxed);
            }
        }
    }

    bool push(const T& val) noexcept {
        int spin = 0, yields = 0;
        while (!try_push(val)) {
            if (!is_running()) {
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
            std::size_t diff = seq - (pos + 1);
            if (diff == 0) {
                if (dequeue_pos_.compare_exchange_weak(
                        pos, pos + 1, std::memory_order_relaxed)) {
                    *out = slot.data;
                    slot.seq.store(pos + mask_ + 1,
                                   std::memory_order_release);
                    return true;
                }
            } else if (diff > std::numeric_limits<std::size_t>::max() / 2) {
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
            if (!is_running()) {
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

    // Publish EOS after all producers are quiescent; cancellation uses stop().
    void close() noexcept {
        auto expected = QueueState::Open;
        state_.compare_exchange_strong(expected, QueueState::Closed, std::memory_order_acq_rel);
    }

    [[nodiscard]] bool is_drained() const noexcept {
        return state_.load(std::memory_order_acquire) == QueueState::Closed && empty();
    }
    [[nodiscard]] bool is_cancelled() const noexcept {
        return state_.load(std::memory_order_acquire) == QueueState::Cancelled;
    }
    void stop() noexcept { state_.store(QueueState::Cancelled, std::memory_order_release); }
    [[nodiscard]] bool is_running() const noexcept {
        return state_.load(std::memory_order_acquire) == QueueState::Open;
    }

    // Approximate occupancy in [0.0, 1.0].
    [[nodiscard]] double occupancy() const noexcept {
        const std::size_t ep = enqueue_pos_.load(std::memory_order_relaxed);
        const std::size_t dp = dequeue_pos_.load(std::memory_order_relaxed);
        const std::size_t used = ep - dp;
        const std::size_t clamped = (used > capacity_) ? capacity_ : used;
        return static_cast<double>(clamped) / static_cast<double>(capacity_);
    }

    [[nodiscard]] std::size_t size_approx() const noexcept {
        const std::size_t ep = enqueue_pos_.load(std::memory_order_relaxed);
        const std::size_t dp = dequeue_pos_.load(std::memory_order_relaxed);
        const std::size_t used = ep - dp;
        return (used > capacity_) ? capacity_ : used;
    }

    [[nodiscard]] std::size_t capacity() const noexcept { return capacity_; }

    [[nodiscard]] bool empty() const noexcept {
        const std::size_t ep = enqueue_pos_.load(std::memory_order_acquire);
        const std::size_t dp = dequeue_pos_.load(std::memory_order_acquire);
        return ep == dp;
    }

private:
    static std::size_t checked_capacity(std::size_t n) {
        if (n < 2 || (n & (n - 1)) != 0 || n > std::numeric_limits<std::size_t>::max() / sizeof(Slot) || n > std::numeric_limits<std::size_t>::max() / 2)
            throw std::invalid_argument("MPMCQueue capacity must be a representable power of two >= 2");
        return n;
    }
    const std::size_t capacity_;
    const std::size_t mask_;
    std::unique_ptr<Slot[]> buffer_;

    alignas(CACHE_LINE_SIZE) std::atomic<std::size_t> enqueue_pos_{0};
    alignas(CACHE_LINE_SIZE) std::atomic<std::size_t> dequeue_pos_{0};
    alignas(CACHE_LINE_SIZE) std::atomic<QueueState>  state_{QueueState::Open};
};

} // namespace klstream
