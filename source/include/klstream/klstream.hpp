#pragma once

/**
 * @file klstream.hpp
 * @brief Main header for KLStream - Kafka-less Parallel Stream Processing Runtime
 * 
 * Include this single header to access the full KLStream API.
 */

#include "klstream/core/config.hpp"
#include "klstream/core/event.hpp"
#include "klstream/core/spsc_queue.hpp"
#include "klstream/core/mpmc_queue.hpp"
#include "klstream/core/backpressure.hpp"
#include "klstream/core/operator.hpp"
#include "klstream/core/worker.hpp"
#include "klstream/core/runtime.hpp"
#include "klstream/core/metrics.hpp"
#include "klstream/core/pinning.hpp"

#include "klstream/operators/source.hpp"
#include "klstream/operators/sink.hpp"
#include "klstream/operators/map.hpp"
#include "klstream/operators/filter.hpp"
#include "klstream/operators/aggregate.hpp"
#include "klstream/operators/window.hpp"

namespace klstream {

/**
 * @brief Library version information
 */
constexpr const char* VERSION = "0.1.0";
constexpr int VERSION_MAJOR = 0;
constexpr int VERSION_MINOR = 1;
constexpr int VERSION_PATCH = 0;

} // namespace klstream
