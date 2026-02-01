cmake_minimum_required(VERSION 3.20)

project(klstream
    VERSION 0.1.0
    DESCRIPTION "Kafka-less Parallel Stream Processing Runtime"
    LANGUAGES CXX
)

# ============================================================================
# Build Options
# ============================================================================
option(KLSTREAM_BUILD_TESTS "Build unit tests" ON)
option(KLSTREAM_BUILD_BENCHMARKS "Build benchmarks" ON)
option(KLSTREAM_BUILD_EXAMPLES "Build examples" ON)
option(KLSTREAM_ENABLE_SANITIZERS "Enable AddressSanitizer and UBSan" OFF)
option(KLSTREAM_ENABLE_LTO "Enable Link Time Optimization" OFF)

# ============================================================================
# C++ Standard and Compiler Settings
# ============================================================================
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# ============================================================================
# Compiler Warnings (Industry Standard)
# ============================================================================
add_library(klstream_warnings INTERFACE)
target_compile_options(klstream_warnings INTERFACE
    $<$<CXX_COMPILER_ID:GNU,Clang,AppleClang>:
        -Wall
        -Wextra
        -Wpedantic
        -Werror
        -Wconversion
        -Wsign-conversion
        -Wshadow
        -Wnon-virtual-dtor
        -Wold-style-cast
        -Wcast-align
        -Wunused
        -Woverloaded-virtual
        -Wformat=2
        -Wnull-dereference
        -Wdouble-promotion
    >
    $<$<CXX_COMPILER_ID:GNU>:
        -Wmisleading-indentation
        -Wduplicated-cond
        -Wduplicated-branches
        -Wlogical-op
    >
)

# ============================================================================
# Sanitizers (Debug builds)
# ============================================================================
add_library(klstream_sanitizers INTERFACE)
if(KLSTREAM_ENABLE_SANITIZERS)
    target_compile_options(klstream_sanitizers INTERFACE
        -fsanitize=address,undefined
        -fno-omit-frame-pointer
    )
    target_link_options(klstream_sanitizers INTERFACE
        -fsanitize=address,undefined
    )
endif()

# ============================================================================
# Link Time Optimization
# ============================================================================
if(KLSTREAM_ENABLE_LTO)
    include(CheckIPOSupported)
    check_ipo_supported(RESULT lto_supported OUTPUT lto_error)
    if(lto_supported)
        set(CMAKE_INTERPROCEDURAL_OPTIMIZATION ON)
    else()
        message(WARNING "LTO not supported: ${lto_error}")
    endif()
endif()

# ============================================================================
# Dependencies
# ============================================================================
find_package(Threads REQUIRED)

# ============================================================================
# Core Library
# ============================================================================
add_library(klstream_core STATIC
    src/core/runtime.cpp
    src/core/scheduler.cpp
    src/core/worker_pool.cpp
    src/core/metrics.cpp
)

target_include_directories(klstream_core
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/src
)

target_link_libraries(klstream_core
    PUBLIC
        Threads::Threads
    PRIVATE
        klstream_warnings
        klstream_sanitizers
)

# Set PIC for potential shared library usage
set_target_properties(klstream_core PROPERTIES
    POSITION_INDEPENDENT_CODE ON
)

# ============================================================================
# Examples
# ============================================================================
if(KLSTREAM_BUILD_EXAMPLES)
    add_executable(klstream_example_pipeline
        examples/simple_pipeline.cpp
    )
    target_link_libraries(klstream_example_pipeline
        PRIVATE
            klstream_core
            klstream_warnings
            klstream_sanitizers
    )
endif()

# ============================================================================
# Tests
# ============================================================================
if(KLSTREAM_BUILD_TESTS)
    enable_testing()
    add_subdirectory(tests)
endif()

# ============================================================================
# Benchmarks
# ============================================================================
if(KLSTREAM_BUILD_BENCHMARKS)
    add_subdirectory(benchmarks)
endif()

# ============================================================================
# Installation
# ============================================================================
include(GNUInstallDirs)

install(TARGETS klstream_core
    EXPORT klstream_targets
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
)

install(DIRECTORY include/
    DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}
)

install(EXPORT klstream_targets
    FILE klstream-targets.cmake
    NAMESPACE klstream::
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/klstream
)

# ============================================================================
# Package Configuration
# ============================================================================
include(CMakePackageConfigHelpers)

configure_package_config_file(
    ${CMAKE_CURRENT_SOURCE_DIR}/cmake/klstream-config.cmake.in
    ${CMAKE_CURRENT_BINARY_DIR}/klstream-config.cmake
    INSTALL_DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/klstream
)

write_basic_package_version_file(
    ${CMAKE_CURRENT_BINARY_DIR}/klstream-config-version.cmake
    VERSION ${PROJECT_VERSION}
    COMPATIBILITY SameMajorVersion
)

install(FILES
    ${CMAKE_CURRENT_BINARY_DIR}/klstream-config.cmake
    ${CMAKE_CURRENT_BINARY_DIR}/klstream-config-version.cmake
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/klstream
)
