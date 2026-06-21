# adaptive_window/CMakeLists.txt
# Appended as a new add_subdirectory() call in the project root CMakeLists.txt,
# alongside the existing add_subdirectory(examples) / tests / benchmarks calls.

add_executable(adaptive_window_main main.cpp)
target_link_libraries(adaptive_window_main PRIVATE klstream)

add_executable(train_forest train_forest.cpp)
target_link_libraries(train_forest PRIVATE klstream)

add_executable(adaptive_window_harness harness.cpp)
target_link_libraries(adaptive_window_harness PRIVATE klstream)
