cmake_minimum_required(VERSION 3.17)
project(KLStream VERSION 0.1.0 LANGUAGES CXX)

# ── Language standard ────────────────────────────────────────────────────
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)   # no GNU extensions; keeps us portable

# ── Platform-specific optimisation flags ────────────────────────────────
include(CheckCXXCompilerFlag)

if(CMAKE_SYSTEM_PROCESSOR MATCHES "arm64|aarch64")
    # On Apple Silicon: prefer -mcpu=apple-m3; fall back through m2, m1,
    # and finally -march=native if none are recognised (older Xcode).
    check_cxx_compiler_flag("-mcpu=apple-m3" HAS_M3)
    check_cxx_compiler_flag("-mcpu=apple-m2" HAS_M2)
    check_cxx_compiler_flag("-mcpu=apple-m1" HAS_M1)
    if(HAS_M3)
        set(NATIVE_CPU_FLAG "-mcpu=apple-m3")
    elseif(HAS_M2)
        set(NATIVE_CPU_FLAG "-mcpu=apple-m2")
    elseif(HAS_M1)
        set(NATIVE_CPU_FLAG "-mcpu=apple-m1")
    else()
        set(NATIVE_CPU_FLAG "-march=native")
    endif()
else()
    # x86-64 (CI, porting, Intel Mac)
    set(NATIVE_CPU_FLAG "-march=native")
endif()

# ── Build-type flags ─────────────────────────────────────────────────────
# Release: maximum optimisation + native CPU tuning
set(CMAKE_CXX_FLAGS_RELEASE "-O3 ${NATIVE_CPU_FLAG} -DNDEBUG")

# Debug: no optimisation, full debug info
set(CMAKE_CXX_FLAGS_DEBUG "-O0 -g3")

# RelWithDebInfo: moderate optimisation + debug info (useful for profiling
# with Instruments — symbols present without full -O0 penalty)
set(CMAKE_CXX_FLAGS_RELWITHDEBINFO "-O2 -g ${NATIVE_CPU_FLAG}")

# Default to Release if the user does not specify
if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
endif()

# ── Compiler warnings ────────────────────────────────────────────────────
add_compile_options(
    -Wall -Wextra -Wpedantic
    -Wno-unused-parameter      # common in operator stubs during development
    -Wno-gnu-anonymous-struct  # GCC extension; irrelevant on clang
)

# ── Sanitizer support ────────────────────────────────────────────────────
# Build with -DKLSTREAM_TSAN=ON to enable ThreadSanitizer.
# Build with -DKLSTREAM_ASAN=ON to enable AddressSanitizer.
# Do NOT combine TSan and ASan — they are incompatible.
option(KLSTREAM_TSAN "Enable ThreadSanitizer" OFF)
option(KLSTREAM_ASAN "Enable AddressSanitizer" OFF)

if(KLSTREAM_TSAN)
    add_compile_options(-fsanitize=thread -fno-omit-frame-pointer)
    add_link_options(-fsanitize=thread)
    message(STATUS "ThreadSanitizer ENABLED")
endif()

if(KLSTREAM_ASAN)
    add_compile_options(-fsanitize=address -fno-omit-frame-pointer)
    add_link_options(-fsanitize=address)
    message(STATUS "AddressSanitizer ENABLED")
endif()

# ── KLStream header-only interface library ───────────────────────────────
# All source code lives in headers. This CMake target just exposes the
# include directory so that every subdirectory (examples, tests, benchmarks)
# can link against klstream::klstream and get the headers.
add_library(klstream INTERFACE)
target_include_directories(klstream INTERFACE
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>
)
target_link_libraries(klstream INTERFACE pthread)
add_library(klstream::klstream ALIAS klstream)

# ── FetchContent: GoogleTest ─────────────────────────────────────────────
include(FetchContent)

FetchContent_Declare(
    googletest
    GIT_REPOSITORY https://github.com/google/googletest.git
    GIT_TAG        v1.14.0
    GIT_SHALLOW    TRUE
)
set(INSTALL_GTEST OFF CACHE BOOL "" FORCE)
set(BUILD_GMOCK   OFF CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(googletest)

# ── FetchContent: Google Benchmark ───────────────────────────────────────
FetchContent_Declare(
    googlebenchmark
    GIT_REPOSITORY https://github.com/google/benchmark.git
    GIT_TAG        v1.8.4
    GIT_SHALLOW    TRUE
)
set(BENCHMARK_ENABLE_TESTING       OFF CACHE BOOL "" FORCE)
set(BENCHMARK_ENABLE_INSTALL       OFF CACHE BOOL "" FORCE)
set(BENCHMARK_DOWNLOAD_DEPENDENCIES ON  CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(googlebenchmark)

# ── Subdirectories ────────────────────────────────────────────────────────
add_subdirectory(examples)
add_subdirectory(tests)
add_subdirectory(benchmarks)
add_subdirectory(research)
