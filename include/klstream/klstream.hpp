#pragma once

/**
 * @file klstream.hpp
 * @brief Main header for KLStream - Kafka-less Parallel Stream Processing Runtime
 * 
 * Include this single header to access the full KLStream API.
 */

#include "klstream/core/event.hpp"
#include "klstream/core/queue.hpp"
#include "klstream/core/operator.hpp"
#include "klstream/core/runtime.hpp"
#include "klstream/core/scheduler.hpp"
#include "klstream/core/worker_pool.hpp"
#include "klstream/core/metrics.hpp"

#include "klstream/operators/source.hpp"
#include "klstream/operators/sink.hpp"
#include "klstream/operators/map.hpp"
#include "klstream/operators/filter.hpp"

namespace klstream {

/**
 * @brief Library version information
 */
constexpr const char* VERSION = "0.1.0";
constexpr int VERSION_MAJOR = 0;
constexpr int VERSION_MINOR = 1;
constexpr int VERSION_PATCH = 0;

} // namespace klstream
