// include/klstream/core/pinning.hpp
#pragma once
#include <cstdint>

// macOS-specific QoS thread affinity. Compiles to no-ops on other platforms.
#if defined(__APPLE__)
#  include <pthread.h>
#endif

namespace klstream {

// ── CoreAffinity ─────────────────────────────────────────────────────────
//
// Which type of core the worker thread should prefer.
// On Apple M3: Performance cores are ~4 GHz, Efficiency cores ~2.75 GHz.
//
// Use Performance for compute-heavy operators (Map with expensive transforms,
// Aggregate with complex state, Window with large buffers).
// Use Efficiency for lightweight operators (Source with rate limiting,
// simple Filter, Sink that just counts or writes a counter).
// Use Any to let the OS decide (default — identical to not calling anything).
enum class CoreAffinity : std::uint8_t {
    Any         = 0,  // OS-managed (default).
    Performance = 1,  // Prefer P-cores (QOS_CLASS_USER_INTERACTIVE on macOS).
    Efficiency  = 2,  // Prefer E-cores (QOS_CLASS_BACKGROUND on macOS).
};

// ── apply_affinity ────────────────────────────────────────────────────────
//
// Call this at the START of a worker thread's execution (before any work).
// It sets the calling thread's QoS class so the macOS scheduler routes it
// to the requested core type.
//
// On non-Apple platforms this is a compile-time no-op. The rest of the
// codebase never calls any platform-specific API directly — only this function.
inline void apply_affinity(CoreAffinity affinity) noexcept {
#if defined(__APPLE__)
    switch (affinity) {
        case CoreAffinity::Performance:
            pthread_set_qos_class_self_np(QOS_CLASS_USER_INTERACTIVE, 0);
            break;
        case CoreAffinity::Efficiency:
            pthread_set_qos_class_self_np(QOS_CLASS_BACKGROUND, 0);
            break;
        case CoreAffinity::Any:
        default:
            break; // Leave the OS to decide.
    }
#else
    (void)affinity; // Suppress unused-parameter warning.
#endif
}

// ── AffinityMap ──────────────────────────────────────────────────────────
//
// Convenience struct used by Runtime (Section 7.10) to pair an operator ID
// with the affinity hint for the worker thread that will run it.
struct AffinityConfig {
    std::uint64_t operator_id;
    CoreAffinity  affinity;
};

} // namespace klstream
