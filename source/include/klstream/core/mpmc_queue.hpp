// include/klstream/core/mpmc_queue.hpp
#pragma once
#include "config.hpp"
#include <atomic>
#include <cassert>
#include <cstddef>
#include <new>
#include <optional>
#include <type_traits>

namespace klstream {

template <typename T>
class MPMCQueue {
    static_assert(std::is_trivially_copyable_v<T>,
        "MPMCQueue<T>: T must be trivially copyable.");

    // Each slot holds the data and a sequence number.
    // The sequence number encodes whether the slot is:
    //   empty (seq == slot_index)        -> enqueuer can claim it
    //   filled (seq == slot_index + 1)   -> dequeuer can consume it
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
        ::operator delete(buffer_,
            std::align_val_t{CACHE_LINE_SIZE});
    }

    MPMCQueue(const MPMCQueue&)            = delete;
    MPMCQueue& operator=(const MPMCQueue&) = delete;

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
                // CAS failed — another producer claimed it; retry.
            } else if (diff < 0) {
                return false; // Queue is full.
            } else {
                pos = enqueue_pos_.load(std::memory_order_relaxed);
            }
        }
    }

    [[nodiscard]] bool try_pop(T* out) noexcept {
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

    std::optional<T> pop() noexcept {
        T val;
        if (try_pop(&val)) return val;
        return std::nullopt;
    }

    [[nodiscard]] double occupancy() const noexcept {
        const std::size_t ep = enqueue_pos_.load(std::memory_order_relaxed);
        const std::size_t dp = dequeue_pos_.load(std::memory_order_relaxed);
        const std::size_t used = (ep - dp + capacity_) & mask_;
        return static_cast<double>(used) / static_cast<double>(capacity_);
    }

    [[nodiscard]] std::size_t capacity() const noexcept { return capacity_; }

private:
    const std::size_t capacity_;
    const std::size_t mask_;
    Slot*             buffer_;

    alignas(CACHE_LINE_SIZE) std::atomic<std::size_t> enqueue_pos_{0};
    alignas(CACHE_LINE_SIZE) std::atomic<std::size_t> dequeue_pos_{0};
};

} // namespace klstream
