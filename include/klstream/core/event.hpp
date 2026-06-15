// include/klstream/core/event.hpp
#pragma once
#include "config.hpp"
#include <cstdint>
#include <chrono>

namespace klstream {

// ── Event<Payload> ────────────────────────────────────────────────────────
//
// The atom of data in KLStream. Templated on Payload so the type system
// prevents accidentally routing an Event<AdEvent> into an operator that
// expects Event<uint64_t>.
//
// Design notes:
//   * timestamp_ns: set by the source at creation time using a monotonic clock.
//     Used to compute end-to-end latency at the sink. Never modified by
//     intermediate operators.
//   * key: for keyed streams (e.g., consistent-hashing placement, Section 14.3).
//     Ignored by stateless operators (Map, Filter). Stateful operators
//     (Aggregate, Window) use it to group events.
//   * seq: monotonically increasing sequence number set by the source. Used in
//     tests to verify ordering is preserved within a single queue.
//   * data: the user-defined payload. Must be trivially copyable for lock-free
//     queue correctness (no internal pointers, no vtable, no reference counting).
//
// Alignment: alignas(CACHE_LINE_SIZE) would waste space for small payloads.
// We leave the struct naturally aligned and rely on the queue's own ring
// buffer being cache-line aligned. The struct should be kept small (<=64 bytes
// including the three metadata fields) so it fits in one or two cache lines.
template <typename Payload>
struct Event {
    std::uint64_t timestamp_ns;  // nanoseconds since epoch (monotonic)
    std::uint64_t key;           // routing / grouping key
    std::uint64_t seq;           // sequence number (set by source, monotonic)
    Payload       data;          // user payload — must be trivially copyable

    // ── Factory helpers ───────────────────────────────────────────────────
    static Event make(Payload d, std::uint64_t k = 0, std::uint64_t s = 0) {
        using namespace std::chrono;
        auto now_ns = static_cast<std::uint64_t>(
            duration_cast<nanoseconds>(
                steady_clock::now().time_since_epoch()
            ).count()
        );
        return Event{ now_ns, k, s, std::move(d) };
    }

    // Elapsed nanoseconds since this event was created (call at the sink).
    std::uint64_t latency_ns() const {
        using namespace std::chrono;
        auto now_ns = static_cast<std::uint64_t>(
            duration_cast<nanoseconds>(
                steady_clock::now().time_since_epoch()
            ).count()
        );
        return (now_ns >= timestamp_ns) ? (now_ns - timestamp_ns) : 0;
    }
};

// Convenience alias for the common case of a plain 64-bit integer payload.
using IntEvent = Event<std::uint64_t>;

} // namespace klstream
