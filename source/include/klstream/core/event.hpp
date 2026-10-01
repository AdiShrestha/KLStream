#pragma once
#include <klstream/core/config.hpp>
#include <cstdint>
#include <chrono>
#include <utility>
#include <type_traits>
#include <stdexcept>


namespace klstream {

// ── Event<Payload> ────────────────────────────────────────────────────────
//
// The atom of data in KLStream. Templated on Payload so the type system
// prevents accidentally routing an Event<AdEvent> into an operator that
// expects Event<uint64_t>.
//
// timestamp_ns is the process steady-clock source creation time, preserved by
// pointwise transforms. seq identifies source order; key is carried as metadata.
// Keyed state/sharding is not implemented by the current aggregate/window classes.
// Payloads are trivially copyable; queue progress guarantees also depend on the
// platform atomic implementation. No cache geometry is measured by this type.
template <typename Payload>
struct Event {
    static_assert(std::is_trivially_copyable_v<Payload>, "Event payload must be trivially copyable");
    std::uint64_t timestamp_ns{0};  // source creation nanoseconds in the process steady-clock domain
    std::uint64_t key{0};           // routing / grouping key
    std::uint64_t seq{0};           // sequence number (set by source, monotonic)
    Payload       data{};          // user payload — must be trivially copyable

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
        if (timestamp_ns > now_ns) throw std::domain_error("Event timestamp is outside the current steady-clock past");
        return now_ns - timestamp_ns;
    }
};

// Convenience alias for the common case of a plain 64-bit integer payload.
using IntEvent = Event<std::uint64_t>;

} // namespace klstream
