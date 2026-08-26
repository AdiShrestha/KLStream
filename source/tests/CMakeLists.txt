enable_testing()
include(GoogleTest)

set(TEST_SOURCES
    test_spsc_queue.cpp
    test_mpmc_queue.cpp
    test_operators.cpp
    test_backpressure.cpp
    test_pipeline_integration.cpp
    unit/test_header_compilation.cpp
    unit/test_runtime_lifecycle.cpp
    unit/test_metrics_accuracy.cpp
    unit/test_adaptive_controller.cpp
    unit/test_isolation_forest_math.cpp
    unit/test_model_serialization.cpp
)






foreach(src ${TEST_SOURCES})
    get_filename_component(name ${src} NAME_WE)
    add_executable(${name} ${src})
    target_link_libraries(${name}
        PRIVATE klstream::klstream GTest::gtest_main)
    klstream_apply_warnings(${name})
    gtest_discover_tests(${name})
endforeach()
