cmake_minimum_required(VERSION 3.17)
project(KLStreamBenchmarks LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# If built standalone
if(NOT TARGET klstream)
    add_library(klstream INTERFACE)
    target_include_directories(klstream INTERFACE ${CMAKE_CURRENT_SOURCE_DIR}/../include)
endif()

find_package(Threads REQUIRED)

add_executable(benchmark_queues benchmark_queues.cpp)
target_link_libraries(benchmark_queues PRIVATE klstream Threads::Threads)

add_executable(benchmark_model benchmark_model.cpp)
target_link_libraries(benchmark_model PRIVATE klstream Threads::Threads)

if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/benchmark_pipeline_e2e.cpp")
    add_executable(benchmark_pipeline_e2e benchmark_pipeline_e2e.cpp)
    target_link_libraries(benchmark_pipeline_e2e PRIVATE klstream Threads::Threads)
endif()
