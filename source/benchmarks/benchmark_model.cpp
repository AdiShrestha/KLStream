#include <klstream/model/isolation_forest.hpp>

#include <algorithm>
#include <chrono>
#include <fstream>
#include <iostream>
#include <random>
#include <vector>

using namespace klstream;

int main() {
    std::cout << "========================================================\n";
    std::cout << "  KLStream Isolation Forest Scoring Benchmark (NFR-001) \n";
    std::cout << "========================================================\n";

    constexpr std::size_t D = 7;
    constexpr int N_TREES = 10;
    constexpr int SUBSAMPLE = 128;
    constexpr std::size_t N_EVALS = 200000;


    IsolationForest<D> forest(N_TREES, SUBSAMPLE, 42);

    // Generate training data to build realistic forest structure
    std::mt19937 rng(12345);
    std::normal_distribution<float> dist(0.0f, 1.0f);

    std::vector<typename IsolationForest<D>::Point> train_pts;
    train_pts.reserve(2000);
    for (std::size_t i = 0; i < 2000; ++i) {
        typename IsolationForest<D>::Point pt;
        for (std::size_t d = 0; d < D; ++d) pt[d] = dist(rng);
        train_pts.push_back(pt);
    }
    forest.fit(train_pts);

    // Generate evaluation points
    std::vector<typename IsolationForest<D>::Point> eval_pts;
    eval_pts.reserve(N_EVALS);
    for (std::size_t i = 0; i < N_EVALS; ++i) {
        typename IsolationForest<D>::Point pt;
        for (std::size_t d = 0; d < D; ++d) pt[d] = dist(rng);
        eval_pts.push_back(pt);
    }

    std::cout << "Scoring " << N_EVALS << " points across " << N_TREES << " isolation trees...\n";

    std::vector<double> latencies_ns;
    latencies_ns.reserve(N_EVALS);

    double score_accumulator = 0.0;

    auto total_start = std::chrono::high_resolution_clock::now();
    for (std::size_t i = 0; i < N_EVALS; ++i) {
        auto t0 = std::chrono::high_resolution_clock::now();
        double s = forest.anomaly_score(eval_pts[i]);
        auto t1 = std::chrono::high_resolution_clock::now();
        score_accumulator += s;
        latencies_ns.push_back(std::chrono::duration<double, std::nano>(t1 - t0).count());
    }
    auto total_end = std::chrono::high_resolution_clock::now();

    double total_sec = std::chrono::duration<double>(total_end - total_start).count();
    double amortized_mean_ns = (total_sec * 1e9) / static_cast<double>(N_EVALS);

    std::sort(latencies_ns.begin(), latencies_ns.end());
    double p50_ns = latencies_ns[N_EVALS * 0.50];
    double p90_ns = latencies_ns[N_EVALS * 0.90];
    double p99_ns = latencies_ns[N_EVALS * 0.99];

    std::cout << "  Mean Scoring Latency: " << amortized_mean_ns << " ns\n";
    std::cout << "  P50 Scoring Latency:  " << p50_ns << " ns\n";
    std::cout << "  P90 Scoring Latency:  " << p90_ns << " ns\n";
    std::cout << "  P99 Scoring Latency:  " << p99_ns << " ns\n";
    std::cout << "  (Checksum sum: " << score_accumulator << ")\n";

    // Write JSON results
    std::ofstream out("results/model_benchmarks.json");
    out << "{\n"
        << "  \"model\": \"IsolationForest\",\n"
        << "  \"num_trees\": " << N_TREES << ",\n"
        << "  \"subsample_size\": " << SUBSAMPLE << ",\n"
        << "  \"num_features\": " << D << ",\n"
        << "  \"evaluations\": " << N_EVALS << ",\n"
        << "  \"mean_latency_ns\": " << amortized_mean_ns << ",\n"
        << "  \"p50_latency_ns\": " << p50_ns << ",\n"
        << "  \"p90_latency_ns\": " << p90_ns << ",\n"
        << "  \"p99_latency_ns\": " << p99_ns << ",\n"
        << "  \"target_met\": " << (amortized_mean_ns < 500.0 ? "true" : "false") << "\n"
        << "}\n";
    out.close();

    std::cout << "Results written to results/model_benchmarks.json\n";
    return 0;
}
