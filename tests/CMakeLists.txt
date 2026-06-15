enable_testing()

set(TEST_SOURCES
    test_spsc_queue.cpp
    test_mpmc_queue.cpp
    test_operators.cpp
    test_backpressure.cpp
    test_pipeline_integration.cpp
)

foreach(src ${TEST_SOURCES})
    get_filename_component(name ${src} NAME_WE)
    add_executable(${name} ${src})
    target_link_libraries(${name}
        PRIVATE klstream::klstream GTest::gtest_main)
    gtest_discover_tests(${name})
endforeach()
