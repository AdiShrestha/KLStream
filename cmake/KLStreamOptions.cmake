# cmake/KLStreamOptions.cmake
# Build configuration options for the KLStream project

include(CMakeDependentOption)

option(KLSTREAM_BUILD_TESTS "Build the unit and integration test suite" ON)
option(KLSTREAM_BUILD_BENCHMARKS "Build the microbenchmarks suite" OFF)
option(KLSTREAM_BUILD_EXAMPLES "Build the executable pipeline examples" ON)
option(KLSTREAM_BUILD_APPS "Build the adaptive window and research applications" ON)
option(KLSTREAM_BUILD_EXPERIMENTS "Build the research experiment binaries" ON)
option(KLSTREAM_ENABLE_WARNINGS_AS_ERRORS "Treat compiler warnings as errors" OFF)

option(KLSTREAM_ENABLE_ASAN "Enable AddressSanitizer (ASan)" OFF)
option(KLSTREAM_ENABLE_TSAN "Enable ThreadSanitizer (TSan)" OFF)
option(KLSTREAM_ENABLE_UBSAN "Enable UndefinedBehaviorSanitizer (UBSan)" OFF)

# Sanity check: TSan and ASan are mutually exclusive
if(KLSTREAM_ENABLE_ASAN AND KLSTREAM_ENABLE_TSAN)
    message(FATAL_ERROR "AddressSanitizer and ThreadSanitizer cannot be enabled simultaneously.")
endif()

message(STATUS "── KLStream Build Options ─────────────────────────────")
message(STATUS "  Build type:                 ${CMAKE_BUILD_TYPE}")
message(STATUS "  Build tests:                ${KLSTREAM_BUILD_TESTS}")
message(STATUS "  Build benchmarks:           ${KLSTREAM_BUILD_BENCHMARKS}")
message(STATUS "  Build examples:             ${KLSTREAM_BUILD_EXAMPLES}")
message(STATUS "  Build applications:         ${KLSTREAM_BUILD_APPS}")
message(STATUS "  Build experiments:          ${KLSTREAM_BUILD_EXPERIMENTS}")
message(STATUS "  Warnings as errors:         ${KLSTREAM_ENABLE_WARNINGS_AS_ERRORS}")
message(STATUS "  AddressSanitizer:           ${KLSTREAM_ENABLE_ASAN}")
message(STATUS "  ThreadSanitizer:            ${KLSTREAM_ENABLE_TSAN}")
message(STATUS "  UndefinedBehaviorSanitizer: ${KLSTREAM_ENABLE_UBSAN}")
message(STATUS "───────────────────────────────────────────────────────")
