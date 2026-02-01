#pragma once

/**
 * @file event.hpp
 * @brief Event type definitions for the stream processing runtime
 */

#include <cstdint>
#include <chrono>
#include <variant>
#include <vector>
#include <string>
#include <optional>
#include <memory>

namespace klstream {

/**
 * @brief Timestamp type using steady clock for monotonic timing
 */
using Timestamp = std::chrono::steady_clock::time_point;

/**
 * @brief Event key type for partitioning and routing
 */
using EventKey = std::uint64_t;

/**
 * @brief Sequence number for ordering within streams
 */
using SequenceNumber = std::uint64_t;

/**
 * @brief Supported payload types
 * 
 * Events can carry various payload types. Users can extend this
 * by using the Blob type for arbitrary binary data.
 */
using Blob = std::vector<std::byte>;

using Payload = std::variant<
    std::monostate,      // Empty payload
    std::int64_t,        // Integer
    double,              // Floating point
    std::string,         // String
    Blob                 // Binary data
>;

/**
 * @brief Event metadata
 * 
 * Contains optional metadata attached to events for routing,
 * ordering, and tracing purposes.
 */
struct EventMetadata {
    std::optional<EventKey> key;
    std::optional<SequenceNumber> sequence;
    Timestamp timestamp;
    std::optional<std::string> source_operator;
    
    EventMetadata() : timestamp(std::chrono::steady_clock::now()) {}
    
    explicit EventMetadata(EventKey k) 
        : key(k), timestamp(std::chrono::steady_clock::now()) {}
};

/**
 * @brief Core event type
 * 
 * Events are the fundamental unit of data in the stream processing system.
 * They are immutable once created and processed exactly once.
 */
class Event {
public:
    /**
     * @brief Construct an empty event
     */
    Event() = default;
    
    /**
     * @brief Construct an event with a payload
     */
    explicit Event(Payload data) 
        : payload_(std::move(data)) {}
    
    /**
     * @brief Construct an event with payload and key
     */
    Event(Payload data, EventKey key)
        : payload_(std::move(data))
        , metadata_(key) {}
    
    /**
     * @brief Construct an event with full metadata
     */
    Event(Payload data, EventMetadata meta)
        : payload_(std::move(data))
        , metadata_(std::move(meta)) {}

    // Accessors
    [[nodiscard]] const Payload& payload() const noexcept { return payload_; }
    [[nodiscard]] Payload& payload() noexcept { return payload_; }
    
    [[nodiscard]] const EventMetadata& metadata() const noexcept { return metadata_; }
    [[nodiscard]] EventMetadata& metadata() noexcept { return metadata_; }
    
    [[nodiscard]] std::optional<EventKey> key() const noexcept { return metadata_.key; }
    [[nodiscard]] Timestamp timestamp() const noexcept { return metadata_.timestamp; }
    
    /**
     * @brief Check if event has a specific payload type
     */
    template<typename T>
    [[nodiscard]] bool holds() const noexcept {
        return std::holds_alternative<T>(payload_);
    }
    
    /**
     * @brief Get payload as specific type (throws if wrong type)
     */
    template<typename T>
    [[nodiscard]] const T& get() const {
        return std::get<T>(payload_);
    }
    
    /**
     * @brief Get payload as specific type (returns nullptr if wrong type)
     */
    template<typename T>
    [[nodiscard]] const T* get_if() const noexcept {
        return std::get_if<T>(&payload_);
    }

private:
    Payload payload_;
    EventMetadata metadata_;
};

/**
 * @brief Poison pill event to signal stream termination
 */
struct PoisonPill {};

/**
 * @brief Event or termination signal
 */
using EventOrPoison = std::variant<Event, PoisonPill>;

} // namespace klstream
