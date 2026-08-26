set(BENCH_SOURCES
    bench_spsc_queue.cpp
    bench_pipeline_throughput.cpp
    bench_ysb.cpp
)

foreach(src ${BENCH_SOURCES})
    get_filename_component(name ${src} NAME_WE)
    add_executable(${name} ${src})
    target_link_libraries(${name}
        PRIVATE klstream::klstream benchmark::benchmark_main)
endforeach()
