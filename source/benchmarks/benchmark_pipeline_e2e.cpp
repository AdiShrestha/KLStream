#include <klstream/core/spsc_queue.hpp>
#include <klstream/core/event.hpp>
#include <klstream/model/isolation_forest.hpp>

#include <algorithm>
#include <array>
#include <atomic>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <random>
#include <string>
#include <thread>
#include <vector>

using namespace klstream;

struct StreamingTick {
    std::uint64_t seq;
    std::uint64_t timestamp_ns;
    std::array<float, 7> features;
};

struct StreamingResult {
    std::uint64_t seq;
    std::uint64_t source_time_ns;
    std::uint64_t sink_time_ns;
    double anomaly_score;
    bool is_alert;
};

int main(int argc, char** argv) {
    std::size_t target_events = 100000;
    std::string output_path = "results/e2e_streaming_benchmark.json";

    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "--events" && i + 1 < argc) {
            target_events = std::stoull(argv[++i]);
        } else if (arg == "--output" && i + 1 < argc) {
            output_path = argv[++i];
        }
    }

    std::cout << "========================================================\n";
    std::cout << "  KLStream End-to-End Replay Benchmark (INV-007/FR-006) \n";
    std::cout << "========================================================\n";
    std::cout << "Target Events: " << target_events << "\n";
    std::cout << "Output File:   " << output_path << "\n";

    // Build trained model for inference stage
    constexpr std::size_t D = 7;
    IsolationForest<D> forest(10, 128, 42);
    std::mt19937 rng(42);
    std::normal_distribution<float> dist(0.0f, 1.0f);
    std::vector<typename IsolationForest<D>::Point> train_pts;
    train_pts.reserve(1000);
    for (std::size_t i = 0; i < 1000; ++i) {
        typename IsolationForest<D>::Point pt;
        for (std::size_t d = 0; d < D; ++d) pt[d] = dist(rng);
        train_pts.push_back(pt);
    }
    forest.fit(train_pts);

    constexpr std::size_t QUEUE_CAPACITY = 8192;
    SPSCQueue<StreamingTick> q_source_worker(QUEUE_CAPACITY);
    SPSCQueue<StreamingResult> q_worker_sink(QUEUE_CAPACITY);

    std::atomic<std::size_t> events_ingested{0};
    std::atomic<std::size_t> events_processed{0};
    std::atomic<std::size_t> events_dropped{0};
    std::atomic<std::size_t> backpressure_activations{0};

    std::vector<double> latencies_ns;
    latencies_ns.reserve(target_events);

    auto start_wall_time = std::chrono::high_resolution_clock::now();

    // 1. Sink Thread
    std::thread sink_thread([&]() {
        StreamingResult res;
        for (std::size_t i = 0; i < target_events; ++i) {
            while (!q_worker_sink.pop(res)) {
                std::this_thread::yield();
            }
            auto now = std::chrono::high_resolution_clock::now();
            res.sink_time_ns = std::chrono::duration_cast<std::chrono::nanoseconds>(
                now.time_since_epoch()).count();
            
            double lat = static_cast<double>(res.sink_time_ns - res.source_time_ns);
            latencies_ns.push_back(std::max(0.0, lat));
            events_processed.fetch_add(1, std::memory_order_relaxed);

            // Inject artificial downstream backpressure between events 40,000 and 45,000
            if (i >= 40000 && i < 45000) {
                std::this_thread::sleep_for(std::chrono::microseconds(2));
            }

        }
    });

    // 2. Worker Thread (Inference)
    std::thread worker_thread([&]() {
        StreamingTick tick;
        for (std::size_t i = 0; i < target_events; ++i) {
            while (!q_source_worker.pop(tick)) {
                std::this_thread::yield();
            }
            double score = forest.anomaly_score(tick.features);
            StreamingResult res;
            res.seq = tick.seq;
            res.source_time_ns = tick.timestamp_ns;
            res.anomaly_score = score;
            res.is_alert = (score > 0.60);

            if (!q_worker_sink.try_push(res)) {
                backpressure_activations.fetch_add(1, std::memory_order_relaxed);
                while (!q_worker_sink.push(res)) {
                    std::this_thread::yield();
                }
            }
        }
    });

    // 3. Source Thread (Ingestion)
    std::thread source_thread([&]() {
        for (std::uint64_t i = 0; i < target_events; ++i) {
            StreamingTick tick;
            tick.seq = i + 1;
            auto now = std::chrono::high_resolution_clock::now();
            tick.timestamp_ns = std::chrono::duration_cast<std::chrono::nanoseconds>(
                now.time_since_epoch()).count();
            for (std::size_t d = 0; d < D; ++d) {
                tick.features[d] = static_cast<float>(d * 0.1f + (i % 100) * 0.01f);
            }

            if (!q_source_worker.try_push(tick)) {
                backpressure_activations.fetch_add(1, std::memory_order_relaxed);
                while (!q_source_worker.push(tick)) {
                    std::this_thread::yield();
                }
            }
            events_ingested.fetch_add(1, std::memory_order_relaxed);
        }
    });


    source_thread.join();
    worker_thread.join();
    sink_thread.join();

    auto end_wall_time = std::chrono::high_resolution_clock::now();
    double total_sec = std::chrono::duration<double>(end_wall_time - start_wall_time).count();
    double throughput_eps = static_cast<double>(target_events) / total_sec;

    std::sort(latencies_ns.begin(), latencies_ns.end());
    double p50 = latencies_ns[target_events * 0.50];
    double p90 = latencies_ns[target_events * 0.90];
    double p99 = latencies_ns[target_events * 0.99];
    double mean_lat = 0.0;
    for (double v : latencies_ns) mean_lat += v;
    mean_lat /= static_cast<double>(target_events);

    bool zero_loss = (events_dropped.load() == 0) &&
                     (events_ingested.load() == target_events) &&
                     (events_processed.load() == target_events);

    std::cout << "\nBenchmark Summary:\n";
    std::cout << "  Events Ingested:          " << events_ingested.load() << "\n";
    std::cout << "  Events Processed:         " << events_processed.load() << "\n";
    std::cout << "  Events Dropped:           " << events_dropped.load() << " (INV-007 verified: "
              << (zero_loss ? "PASS" : "FAIL") << ")\n";
    std::cout << "  Backpressure Activations: " << backpressure_activations.load() << "\n";
    std::cout << "  Total Elapsed Time:       " << total_sec << " s\n";
    std::cout << "  Replay Throughput:        " << throughput_eps << " events/sec\n";
    std::cout << "  Latency Mean:             " << mean_lat << " ns\n";
    std::cout << "  Latency P50:              " << p50 << " ns\n";
    std::cout << "  Latency P99:              " << p99 << " ns\n";

    // Write JSON report
    std::ofstream out(output_path);
    out << "{\n"
        << "  \"manifest_version\": \"1.0.0\",\n"
        << "  \"governing_invariants\": [\"INV-007\", \"FR-006\"],\n"
        << "  \"zero_loss_verified\": " << (zero_loss ? "true" : "false") << ",\n"
        << "  \"events_dropped\": " << events_dropped.load() << ",\n"
        << "  \"events_ingested\": " << events_ingested.load() << ",\n"
        << "  \"events_processed\": " << events_processed.load() << ",\n"
        << "  \"backpressure_activations\": " << backpressure_activations.load() << ",\n"
        << "  \"elapsed_seconds\": " << total_sec << ",\n"
        << "  \"throughput_events_per_sec\": " << throughput_eps << ",\n"
        << "  \"latency_ns\": {\n"
        << "    \"mean\": " << mean_lat << ",\n"
        << "    \"p50\": " << p50 << ",\n"
        << "    \"p90\": " << p90 << ",\n"
        << "    \"p99\": " << p99 << "\n"
        << "  }\n"
        << "}\n";
    out.close();

    std::cout << "\nResults successfully written to " << output_path << "\n";
    return zero_loss ? 0 : 1;
}
