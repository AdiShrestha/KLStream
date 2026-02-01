cmake_minimum_required(VERSION 3.20)

# Tests directory CMakeLists.txt

# Try to find GoogleTest, or use FetchContent
include(FetchContent)

FetchContent_Declare(
    googletest
    GIT_REPOSITORY https://github.com/google/googletest.git
    GIT_TAG v1.14.0
)

# For Windows: Prevent overriding the parent project's compiler/linker settings
set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)

FetchContent_MakeAvailable(googletest)

include(GoogleTest)

# Queue tests
add_executable(queue_test
    queue_test.cpp
)
target_link_libraries(queue_test
    PRIVATE
        klstream_core
        GTest::gtest_main
)
gtest_discover_tests(queue_test)

# Operator tests
add_executable(operator_test
    operator_test.cpp
)
target_link_libraries(operator_test
    PRIVATE
        klstream_core
        GTest::gtest_main
)
gtest_discover_tests(operator_test)

# Integration tests
add_executable(integration_test
    integration_test.cpp
)
target_link_libraries(integration_test
    PRIVATE
        klstream_core
        GTest::gtest_main
)
gtest_discover_tests(integration_test)
