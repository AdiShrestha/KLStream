#pragma once
#include <cstdint>
#include <string_view>

#define KLSTREAM_VERSION_MAJOR 0
#define KLSTREAM_VERSION_MINOR 2
#define KLSTREAM_VERSION_PATCH 0
#define KLSTREAM_VERSION_STRING "0.2.0-dev"

namespace klstream {

constexpr const char* VERSION = "0.2.0-dev";
constexpr int VERSION_MAJOR = 0;
constexpr int VERSION_MINOR = 2;
constexpr int VERSION_PATCH = 0;

[[nodiscard]] inline constexpr const char* version() noexcept {
    return VERSION;
}

} // namespace klstream
