// include/klstream/core/operator.hpp
#pragma once
#include <cstdint>
#include <string>

namespace klstream {

// ── OpStatus ─────────────────────────────────────────────────────────────
//
// Return value of IOperator::tick(). The worker thread uses this to decide
// what to do next:
//
//   Processed -> reset backoff counter, immediately call tick() again.
//   Idle      -> increment backoff counter, apply spin/yield/sleep policy.
//   Blocked   -> output queue was full; do NOT pop input on the next tick()
//               (the operator must remember the un-pushed event internally).
//               Increment backoff counter to give the downstream time to drain.
enum class OpStatus : std::uint8_t {
    Processed = 0,  // One event was successfully processed and pushed.
    Idle      = 1,  // Input queue was empty; nothing to do.
    Blocked   = 2,  // Output queue was full; event is held inside operator.
};

// ── IOperator ─────────────────────────────────────────────────────────────
//
// The abstract base class for every operator in the pipeline.
//
// Lifecycle:
//   1. Construct the operator (pass queue pointers, lambda, etc. in ctor).
//   2. Runtime calls init() once on the owning thread before the first tick().
//   3. Runtime calls tick() in a tight loop for the operator's lifetime.
//   4. Runtime calls shutdown() once when stopping (after setting stop flag).
//
// Threading: init(), tick(), and shutdown() are always called from the same
// worker thread. The operator does not need to protect its own state with
// locks — the queues are the synchronisation boundary.
//
// The operator OWNS a "pending" slot: when tick() returns Blocked, it means
// the operator has popped an event from its input queue and stored it in an
// internal field (e.g., `pending_`). On the next tick() call, it attempts
// to push the pending event again without popping a new one. This guarantees
// at-most-once-pop: we never lose data by popping something we could not push.
class IOperator {
public:
    explicit IOperator(std::string name) : name_(std::move(name)) {}
    virtual ~IOperator() = default;

    // Called once by the worker thread before the first tick().
    virtual void init() {}

    // Core scheduling unit. Called repeatedly. See OpStatus for semantics.
    [[nodiscard]] virtual OpStatus tick() = 0;

    // Called once after the stop flag is set. Flush, close files, etc.
    virtual void shutdown() {}

    const std::string& name() const { return name_; }

    // Unique integer ID assigned by the Runtime at registration time.
    std::uint64_t id = 0;

private:
    std::string name_;
};

} // namespace klstream
