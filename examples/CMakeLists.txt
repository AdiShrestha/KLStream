add_executable(basic_pipeline basic_pipeline/main.cpp)
target_link_libraries(basic_pipeline PRIVATE klstream::klstream)

add_executable(ysb_pipeline yahoo_streaming_benchmark/main.cpp)
target_link_libraries(ysb_pipeline PRIVATE klstream::klstream)
