cmake_minimum_required(VERSION 3.17)
project(KLStreamConsumerTest LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(KLStream CONFIG REQUIRED)

add_executable(consumer_test main.cpp)
target_link_libraries(consumer_test PRIVATE KLStream::klstream)
