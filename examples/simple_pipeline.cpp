/**
 * @file simple_pipeline.cpp
 * @brief Example: Source → Map → Filter → Aggregate → Sink
 * 
 * This demonstrates a complete stream processing pipeline
 * as described in the specification.
 */

#include <iostream>
#include <chrono>
#include <thread>
#include <csignal>
#include <atomic>

#include "klstream/klstream.hpp"

std::atomic<bool> g_shutdown{false};

void signal_handler(int /*signal*/) {
    g_shutdown.store(true);
    std::cout << "\nShutdown requested..." << std::endl;
}

int main() {
    std::signal(SIGINT, signal_handler);
    std::signal(SIGTERM, signal_handler);
    
    std::cout << "=== KLStream Example Pipeline ===" << std::endl;
    std::cout << "Version: " << klstream::VERSION << std::endl;
    std::cout << std::endl;
    
    // Configure runtime
    klstream::RuntimeConfig config;
    config.num_workers = 4;
    config.scheduling_policy = klstream::SchedulingPolicy::RoundRobin;
    config.enable_metrics = true;
    
    // Create runtime
    klstream::Runtime runtime(config);
    
    // Build the stream graph
    // Pipeline: Source → Map(square) → Filter(even) → Aggregate → Sink
    klstream::StreamGraphBuilder builder;
    
    // Source: generates integers 1..100000
    klstream::SequenceSource::Config source_config;
    source_config.start = 1;
    source_config.step = 1;
    source_config.count = 100000;
    source_config.delay = std::chrono::microseconds(10);  // Rate limiting
    
    auto source = std::make_unique<klstream::SequenceSource>("source", source_config);
    
    // Map: square each number
    auto square_map = klstream::make_int_map("square", [](std::int64_t x) {
        return x * x;
    });
    
    // Filter: keep only even numbers
    auto even_filter = klstream::make_filter("even_filter", klstream::filters::even());
    
    // Sink: aggregating sink to compute statistics
    auto agg_sink = std::make_unique<klstream::AggregatingSink>("aggregate");
    auto* agg_ptr = agg_sink.get();  // Keep pointer for stats access
    
    // Build graph
    builder
        .add_source(std::move(source))
        .add_operator(std::move(square_map))
        .add_operator(std::move(even_filter))
        .add_sink(std::move(agg_sink))
        .connect("source", "square")
        .connect("square", "even_filter")
        .connect("even_filter", "aggregate");
    
    // Initialize and start
    std::cout << "Initializing runtime..." << std::endl;
    runtime.init(std::move(builder));
    
    std::cout << "Starting pipeline..." << std::endl;
    runtime.start();
    
    // Monitor progress
    auto start_time = std::chrono::steady_clock::now();
    while (!g_shutdown.load() && runtime.state() == klstream::RuntimeState::Running) {
        std::this_thread::sleep_for(std::chrono::seconds(1));
        
        // Print metrics
        std::cout << "\r" << runtime.metrics().format() << std::flush;
        
        // Check if processing is complete (simple heuristic)
        auto elapsed = std::chrono::steady_clock::now() - start_time;
        if (elapsed > std::chrono::seconds(30)) {
            std::cout << "\n\nTimeout reached, stopping..." << std::endl;
            break;
        }
    }
    
    std::cout << std::endl;
    
    // Stop runtime
    std::cout << "Stopping runtime..." << std::endl;
    runtime.stop();
    
    // Print final statistics
    std::cout << "\n=== Final Statistics ===" << std::endl;
    std::cout << "Events aggregated: " << agg_ptr->count() << std::endl;
    std::cout << "Sum: " << agg_ptr->sum() << std::endl;
    std::cout << "Mean: " << agg_ptr->mean() << std::endl;
    std::cout << "Min: " << agg_ptr->min() << std::endl;
    std::cout << "Max: " << agg_ptr->max() << std::endl;
    std::cout << "Uptime: " << runtime.metrics().uptime().count() << " ms" << std::endl;
    
    return 0;
}
