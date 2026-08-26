cmake_minimum_required(VERSION 3.17)

# Read canonical VERSION file
file(READ "${CMAKE_CURRENT_SOURCE_DIR}/VERSION" KLSTREAM_VERSION_RAW)
string(STRIP "${KLSTREAM_VERSION_RAW}" KLSTREAM_VERSION_STRING)
string(REGEX MATCH "^([0-9]+)\\.([0-9]+)\\.([0-9]+)" _ ${KLSTREAM_VERSION_STRING})
set(KLSTREAM_VERSION_MAJOR ${CMAKE_MATCH_1})
set(KLSTREAM_VERSION_MINOR ${CMAKE_MATCH_2})
set(KLSTREAM_VERSION_PATCH ${CMAKE_MATCH_3})
set(KLSTREAM_VERSION_NUMERIC "${KLSTREAM_VERSION_MAJOR}.${KLSTREAM_VERSION_MINOR}.${KLSTREAM_VERSION_PATCH}")

project(KLStream VERSION ${KLSTREAM_VERSION_NUMERIC} LANGUAGES CXX)


# ── CMake Modules & Configuration ─────────────────────────────────────────
list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/cmake")
include(KLStreamOptions)
include(KLStreamWarnings)

# ── Language standard ────────────────────────────────────────────────────
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)   # no GNU extensions; keeps us portable

# ── Platform-specific optimisation flags ────────────────────────────────
include(CheckCXXCompilerFlag)

if(CMAKE_SYSTEM_PROCESSOR MATCHES "arm64|aarch64")
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
    set(NATIVE_CPU_FLAG "-march=native")
endif()

# ── Build-type flags ─────────────────────────────────────────────────────
set(CMAKE_CXX_FLAGS_RELEASE "-O3 ${NATIVE_CPU_FLAG} -DNDEBUG")
set(CMAKE_CXX_FLAGS_DEBUG "-O0 -g3")
set(CMAKE_CXX_FLAGS_RELWITHDEBINFO "-O2 -g ${NATIVE_CPU_FLAG}")

if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
endif()

# ── KLStream header-only interface library ───────────────────────────────
find_package(Threads REQUIRED)

add_library(klstream INTERFACE)
target_include_directories(klstream INTERFACE
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/source/include>
    $<INSTALL_INTERFACE:include>
)
target_compile_features(klstream INTERFACE cxx_std_17)
target_link_libraries(klstream INTERFACE Threads::Threads)
add_library(klstream::klstream ALIAS klstream)
add_library(KLStream::klstream ALIAS klstream)

# ── FetchContent: Dependencies ───────────────────────────────────────────
include(FetchContent)

if(KLSTREAM_BUILD_TESTS)
    FetchContent_Declare(
        googletest
        GIT_REPOSITORY https://github.com/google/googletest.git
        GIT_TAG        v1.14.0
        GIT_SHALLOW    TRUE
    )
    set(INSTALL_GTEST OFF CACHE BOOL "" FORCE)
    set(BUILD_GMOCK   OFF CACHE BOOL "" FORCE)
    FetchContent_MakeAvailable(googletest)
endif()

if(KLSTREAM_BUILD_BENCHMARKS)
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
endif()

# ── Testing ───────────────────────────────────────────────────────────────
if(KLSTREAM_BUILD_TESTS)
    include(CTest)
    enable_testing()
endif()

# ── Subdirectories ────────────────────────────────────────────────────────
if(KLSTREAM_BUILD_EXAMPLES)
    add_subdirectory(source/examples)
endif()

if(KLSTREAM_BUILD_TESTS)
    add_subdirectory(source/tests)
endif()

if(KLSTREAM_BUILD_BENCHMARKS)
    add_subdirectory(source/benchmarks)
endif()

if(KLSTREAM_BUILD_EXPERIMENTS)
    add_subdirectory(source/experiments/research)
endif()

if(KLSTREAM_BUILD_APPS)
    add_subdirectory(source/apps/adaptive_window)
endif()

# ── Installation & Packaging ──────────────────────────────────────────────
include(GNUInstallDirs)
include(CMakePackageConfigHelpers)

install(TARGETS klstream
    EXPORT KLStreamTargets
    INCLUDES DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}
)

install(DIRECTORY source/include/
    DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}
)

install(EXPORT KLStreamTargets
    FILE KLStreamTargets.cmake
    NAMESPACE KLStream::
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/KLStream
)

write_basic_package_version_file(
    "${CMAKE_CURRENT_BINARY_DIR}/KLStreamConfigVersion.cmake"
    VERSION ${PROJECT_VERSION}
    COMPATIBILITY SameMajorVersion
)

configure_package_config_file(
    "${CMAKE_CURRENT_SOURCE_DIR}/cmake/KLStreamConfig.cmake.in"
    "${CMAKE_CURRENT_BINARY_DIR}/KLStreamConfig.cmake"
    INSTALL_DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/KLStream
)

install(FILES
    "${CMAKE_CURRENT_BINARY_DIR}/KLStreamConfig.cmake"
    "${CMAKE_CURRENT_BINARY_DIR}/KLStreamConfigVersion.cmake"
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/KLStream
)

