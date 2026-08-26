#include <klstream/core/spsc_queue.hpp>
#include <klstream/core/mpmc_queue.hpp>

#include <chrono>
#include <fstream>
#include <iostream>
#include <thread>
#include <vector>

using namespace klstream;

struct QueueBenchmarkResult {
    std::string queue_type;
    std::size_t capacity;
    std::size_t num_operations;
    int num_producers;
    int num_consumers;
    double elapsed_seconds;
    double million_ops_per_sec;
};

QueueBenchmarkResult benchmark_spsc(std::size_t num_ops = 20000000) {
    constexpr std::size_t CAPACITY = 65536;
    SPSCQueue<std::uint64_t> queue(CAPACITY);

    auto start = std::chrono::high_resolution_clock::now();

    std::thread producer([&]() {
        for (std::uint64_t i = 1; i <= num_ops; ++i) {
            while (!queue.push(i)) {}
        }
    });

    std::thread consumer([&]() {
        std::uint64_t val = 0;
        for (std::size_t i = 0; i < num_ops; ++i) {
            while (!queue.pop(val)) {}
        }
    });

    producer.join();
    consumer.join();

    auto end = std::chrono::high_resolution_clock::now();
    double secs = std::chrono::duration<double>(end - start).count();
    double mops = (static_cast<double>(num_ops) / 1e6) / secs;

    return {"SPSCQueue", CAPACITY, num_ops, 1, 1, secs, mops};
}

QueueBenchmarkResult benchmark_mpmc(std::size_t num_ops_per_pair = 2500000, int num_pairs = 4) {
    constexpr std::size_t CAPACITY = 65536;
    MPMCQueue<std::uint64_t> queue(CAPACITY);

    std::size_t total_ops = num_ops_per_pair * num_pairs;
    auto start = std::chrono::high_resolution_clock::now();

    std::vector<std::thread> producers;
    std::vector<std::thread> consumers;

    for (int p = 0; p < num_pairs; ++p) {
        producers.emplace_back([&, p]() {
            for (std::size_t i = 0; i < num_ops_per_pair; ++i) {
                while (!queue.push(static_cast<std::uint64_t>(i + 1))) {}
            }
        });
    }

    for (int c = 0; c < num_pairs; ++c) {
        consumers.emplace_back([&, c]() {
            std::uint64_t val = 0;
            for (std::size_t i = 0; i < num_ops_per_pair; ++i) {
                while (!queue.pop(val)) {}
            }
        });
    }

    for (auto& t : producers) t.join();
    for (auto& t : consumers) t.join();

    auto end = std::chrono::high_resolution_clock::now();
    double secs = std::chrono::duration<double>(end - start).count();
    double mops = (static_cast<double>(total_ops) / 1e6) / secs;

    return {"MPMCQueue", CAPACITY, total_ops, num_pairs, num_pairs, secs, mops};
}

int main() {
    std::cout << "========================================================\n";
    std::cout << "  KLStream Lock-Free Queue Micro-Benchmarks (NFR-001)   \n";
    std::cout << "========================================================\n";

    std::cout << "Running SPSCQueue benchmark (1 Producer, 1 Consumer, 20M ops)...\n";
    auto spsc_res = benchmark_spsc(20000000);
    std::cout << "  SPSC Throughput: " << spsc_res.million_ops_per_sec << " Million ops/sec ("
              << spsc_res.elapsed_seconds << "s)\n";

    std::cout << "Running MPMCQueue benchmark (4 Producers, 4 Consumers, 10M ops)...\n";
    auto mpmc_res = benchmark_mpmc(2500000, 4);
    std::cout << "  MPMC Throughput: " << mpmc_res.million_ops_per_sec << " Million ops/sec ("
              << mpmc_res.elapsed_seconds << "s)\n";

    // Write JSON results
    std::ofstream out("results/queue_benchmarks.json");
    out << "{\n"
        << "  \"spsc\": {\n"
        << "    \"queue_type\": \"" << spsc_res.queue_type << "\",\n"
        << "    \"operations\": " << spsc_res.num_operations << ",\n"
        << "    \"elapsed_seconds\": " << spsc_res.elapsed_seconds << ",\n"
        << "    \"million_ops_per_sec\": " << spsc_res.million_ops_per_sec << ",\n"
        << "    \"target_exceeded\": " << (spsc_res.million_ops_per_sec > 10.0 ? "true" : "false") << "\n"
        << "  },\n"
        << "  \"mpmc\": {\n"
        << "    \"queue_type\": \"" << mpmc_res.queue_type << "\",\n"
        << "    \"producers\": " << mpmc_res.num_producers << ",\n"
        << "    \"consumers\": " << mpmc_res.num_consumers << ",\n"
        << "    \"operations\": " << mpmc_res.num_operations << ",\n"
        << "    \"elapsed_seconds\": " << mpmc_res.elapsed_seconds << ",\n"
        << "    \"million_ops_per_sec\": " << mpmc_res.million_ops_per_sec << "\n"
        << "  }\n"
        << "}\n";
    out.close();

    std::cout << "Results written to results/queue_benchmarks.json\n";
    return 0;
}
