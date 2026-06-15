// include/klstream/core/config.hpp
#pragma once
#include <cstddef>
#include <cstdint>

namespace klstream {

// ── Cache line size ────────────────────────────────────────────────────────
// Apple Silicon (M1/M2/M3): hw.cachelinesize = 128.
// x86-64 (Intel/AMD):        64.
// Verify on your machine:  sysctl -n hw.cachelinesize
//
// IMPORTANT: Every alignas() in the hot path uses this constant.
// If you port to x86 change this to 64 — everything else adapts automatically.
#if defined(__aarch64__)
  inline constexpr std::size_t CACHE_LINE_SIZE = 128;
#else
  inline constexpr std::size_t CACHE_LINE_SIZE = 64;
#endif

// ── Queue defaults ─────────────────────────────────────────────────────────
// Default capacity for all queues created without an explicit size argument.
// Must be a power of 2 (required by the MPMC queue's bitmask trick).
// 4096 events × sizeof(Event<uint64_t>) = ~64 KB per queue — fits in L2 cache.
inline constexpr std::size_t DEFAULT_QUEUE_CAPACITY = 4096;

// ── Backpressure thresholds ────────────────────────────────────────────────
// Soft threshold: when EMA occupancy fraction exceeds this, start throttling.
inline constexpr double BP_SOFT_THRESHOLD = 0.70;
// Hard threshold: when instantaneous occupancy exceeds this, block immediately.
inline constexpr double BP_HARD_THRESHOLD = 0.95;

// ── Worker backoff parameters ──────────────────────────────────────────────
// How many ARM `yield` spins before escalating to std::this_thread::yield().
inline constexpr int SPIN_BEFORE_YIELD = 64;
// How many std::this_thread::yield() calls before escalating to sleep.
inline constexpr int YIELD_BEFORE_SLEEP = 32;
// Sleep duration in nanoseconds when all operators are Idle.
inline constexpr int SLEEP_NS = 100;

// ── Metrics ───────────────────────────────────────────────────────────────
// Reporting interval in seconds for the metrics printer.
inline constexpr int METRICS_INTERVAL_SEC = 1;

// ── Latency histogram ─────────────────────────────────────────────────────
// Number of buckets. Each bucket covers 1 microsecond up to MAX_LATENCY_US,
// then a final overflow bucket.
inline constexpr std::size_t HISTOGRAM_BUCKETS = 10000;
inline constexpr std::size_t MAX_LATENCY_US    = 10000; // 10 ms

} // namespace klstream
