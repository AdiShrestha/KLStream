// Native C++ Execution Engine for KLStream.
// Streaming Isolation Forest Anomaly Detection with Bounded Microbatching.
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>
#include <thread>
#include <vector>
#include <stdexcept>

#include <klstream/core/event.hpp>
#include <klstream/core/spsc_queue.hpp>
#include <klstream/operators/batch.hpp>
#include <klstream/control/occupancy_controller.hpp>
#include <klstream/model/isolation_forest.hpp>

namespace {

struct Options {
    std::string train_path;
    std::string eval_path;
    std::string output_path;
    std::string trace_path;
    std::uint32_t seed{42};
    std::size_t trees{100};
    std::size_t subsample{256};
    std::size_t batch_min{1};
    std::size_t batch_max{32};
    std::size_t batch_init{4};
    std::size_t queue_capacity{512};
    std::uint64_t deadline_us{500};
};

struct DataRow {
    std::string sample_id;
    std::vector<float> features;
};

// Trivially copyable trace payload for SPSCQueue and EventBatch.
struct TraceRecord {
    std::uint64_t sample_index{0};
    std::uint64_t event_id{0};
    std::uint64_t ingest_time_ns{0};
};
static_assert(std::is_trivially_copyable_v<TraceRecord>, "TraceRecord must be trivially copyable");

struct ScoredItem {
    std::string sample_id;
    std::uint64_t event_id{0};
    std::size_t batch_id{0};
    std::size_t batch_size{0};
    std::uint64_t ingest_time_ns{0};
    std::uint64_t emit_time_ns{0};
    double latency_us{0.0};
    double queue_depth_frac{0.0};
    double score{0.0};
    std::string status{"OK"};
};

std::vector<std::string> split_csv_line(const std::string& line) {
    std::vector<std::string> tokens;
    std::string token;
    std::istringstream stream(line);
    while (std::getline(stream, token, ',')) {
        // Trim leading and trailing whitespace.
        auto start = token.find_first_not_of(" \t\r\n");
        auto end = token.find_last_not_of(" \t\r\n");
        if (start == std::string::npos) {
            tokens.push_back("");
        } else {
            tokens.push_back(token.substr(start, end - start + 1));
        }
    }
    return tokens;
}

std::vector<DataRow> load_csv_data(const std::string& path) {
    std::ifstream file(path);
    if (!file.is_open()) {
        throw std::runtime_error("Cannot open input file: " + path);
    }
    std::vector<DataRow> rows;
    std::string line;
    bool first_line = true;
    std::size_t expected_dims = 0;

    while (std::getline(file, line)) {
        if (line.empty()) continue;
        auto tokens = split_csv_line(line);
        if (tokens.empty()) continue;

        if (first_line) {
            first_line = false;
            // Check if first line is a header (tokens[1] not a float).
            if (tokens.size() > 1) {
                try {
                    std::size_t idx = 0;
                    std::stof(tokens[1], &idx);
                    if (idx == tokens[1].size()) {
                        // First line is numeric data, not header.
                    } else {
                        // Non-numeric suffix -> header, skip.
                        continue;
                    }
                } catch (...) {
                    // Header detected, skip line.
                    continue;
                }
            }
        }

        DataRow row;
        row.sample_id = tokens[0];
        for (std::size_t i = 1; i < tokens.size(); ++i) {
            float val = std::stof(tokens[i]);
            if (!std::isfinite(val)) {
                throw std::runtime_error("Non-finite feature encountered: " + tokens[i]);
            }
            row.features.push_back(val);
        }

        if (expected_dims == 0) {
            expected_dims = row.features.size();
        } else if (row.features.size() != expected_dims) {
            throw std::runtime_error("Inconsistent feature dimension in CSV: " + path);
        }

        rows.push_back(std::move(row));
    }

    return rows;
}

void print_usage(const char* prog) {
    std::cout << "Usage: " << prog << " [options]\n"
              << "Options:\n"
              << "  --train <path>           Path to training data CSV (sample_id, f0, f1, ...)\n"
              << "  --eval <path>            Path to evaluation data CSV (sample_id, f0, f1, ...)\n"
              << "  --output <path>          Path to output predictions CSV (sample_id, score)\n"
              << "  --trace-log <path>       Path to output event telemetry trace CSV\n"
              << "  --seed <int>             Random seed for isolation forest (default: 42)\n"
              << "  --trees <int>            Number of isolation trees (default: 100)\n"
              << "  --subsample <int>        Subsample size for tree construction (default: 256)\n"
              << "  --batch-min <int>        Minimum batch size (default: 1)\n"
              << "  --batch-max <int>        Maximum batch size (default: 32)\n"
              << "  --batch-init <int>       Initial batch size (default: 4)\n"
              << "  --queue-capacity <int>   SPSC Queue capacity (default: 512)\n"
              << "  --deadline-us <int>      Microbatch deadline in microseconds (default: 500)\n"
              << "  --help                   Display this usage message\n";
}

Options parse_arguments(int argc, char* argv[]) {
    Options opt;
    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "--help") {
            print_usage(argv[0]);
            std::exit(0);
        } else if (arg == "--train" && i + 1 < argc) {
            opt.train_path = argv[++i];
        } else if (arg == "--eval" && i + 1 < argc) {
            opt.eval_path = argv[++i];
        } else if (arg == "--output" && i + 1 < argc) {
            opt.output_path = argv[++i];
        } else if (arg == "--trace-log" && i + 1 < argc) {
            opt.trace_path = argv[++i];
        } else if (arg == "--seed" && i + 1 < argc) {
            opt.seed = static_cast<std::uint32_t>(std::stoul(argv[++i]));
        } else if (arg == "--trees" && i + 1 < argc) {
            opt.trees = std::stoul(argv[++i]);
        } else if (arg == "--subsample" && i + 1 < argc) {
            opt.subsample = std::stoul(argv[++i]);
        } else if (arg == "--batch-min" && i + 1 < argc) {
            opt.batch_min = std::stoul(argv[++i]);
        } else if (arg == "--batch-max" && i + 1 < argc) {
            opt.batch_max = std::stoul(argv[++i]);
        } else if (arg == "--batch-init" && i + 1 < argc) {
            opt.batch_init = std::stoul(argv[++i]);
        } else if (arg == "--queue-capacity" && i + 1 < argc) {
            opt.queue_capacity = std::stoul(argv[++i]);
        } else if (arg == "--deadline-us" && i + 1 < argc) {
            opt.deadline_us = std::stoull(argv[++i]);
        } else {
            throw std::invalid_argument("Unknown argument: " + arg);
        }
    }
    return opt;
}

} // namespace

int main(int argc, char* argv[]) {
    try {
        auto opt = parse_arguments(argc, argv);
        if (opt.eval_path.empty() || opt.output_path.empty()) {
            print_usage(argv[0]);
            return 1;
        }

        // 1. Load training data if provided, or fit on eval data if train not specified.
        std::vector<DataRow> train_data;
        if (!opt.train_path.empty()) {
            train_data = load_csv_data(opt.train_path);
        }
        auto eval_data = load_csv_data(opt.eval_path);

        if (train_data.empty()) {
            // Unsupervised fitting on evaluation data features if train partition omitted.
            train_data = eval_data;
        }

        if (train_data.size() < 2) {
            throw std::runtime_error("Training dataset must contain at least 2 rows for Isolation Forest");
        }

        std::size_t feature_dim = train_data.front().features.size();
        if (feature_dim == 0) {
            throw std::runtime_error("Features must have positive dimension");
        }

        // 2. Train Isolation Forest model.
        std::vector<std::vector<float>> train_points;
        train_points.reserve(train_data.size());
        for (const auto& r : train_data) {
            train_points.push_back(r.features);
        }

        klstream::DynamicIsolationForest forest(opt.trees, opt.subsample, opt.seed);
        forest.fit(train_points);

        // 3. Setup Streaming Pipeline with Microbatching.
        constexpr std::size_t MaxBatch = 256;
        std::size_t batch_min = std::max<std::size_t>(1, opt.batch_min);
        std::size_t batch_max = std::min<std::size_t>(MaxBatch, std::max(batch_min, opt.batch_max));
        std::size_t batch_init = std::max(batch_min, std::min(batch_max, opt.batch_init));

        klstream::SPSCQueue<klstream::Event<TraceRecord>> in_queue(opt.queue_capacity);
        klstream::SPSCQueue<klstream::EventBatch<TraceRecord, MaxBatch>> batch_queue(opt.queue_capacity);

        klstream::OccupancyBatchController controller(
            batch_min, batch_max, batch_init,
            0.2, 0.2, 0.8, 0.8, 1.25,
            klstream::FeedbackDirection::GrowUnderPressure);

        klstream::BatchOperator<TraceRecord, MaxBatch> batch_op(
            "microbatcher", &in_queue, &batch_queue,
            [&controller, &in_queue]() {
                return controller.update(in_queue.occupancy());
            },
            std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::microseconds(opt.deadline_us)));

        std::size_t offered_count = eval_data.size();
        std::size_t admitted_count = 0;
        std::size_t emitted_count = 0;
        std::vector<ScoredItem> scored_results;
        scored_results.reserve(offered_count);

        // Thread 1: Ingestion / Source thread
        std::thread producer([&]() {
            for (std::size_t i = 0; i < offered_count; ++i) {
                auto now = std::chrono::steady_clock::now();
                uint64_t ingest_ns = static_cast<uint64_t>(
                    std::chrono::duration_cast<std::chrono::nanoseconds>(
                        now.time_since_epoch()).count());

                TraceRecord rec;
                rec.sample_index = i;
                rec.event_id = i + 1;
                rec.ingest_time_ns = ingest_ns;

                klstream::Event<TraceRecord> ev{ingest_ns, 0, i + 1, rec};

                while (!in_queue.try_push(ev)) {
                    std::this_thread::yield();
                }
                ++admitted_count;
            }
            in_queue.close();
        });

        // Thread 2: Batching Operator thread
        std::thread batcher([&]() {
            while (true) {
                auto status = batch_op.tick();
                if (status == klstream::OpStatus::Finished) {
                    break;
                }
                if (status == klstream::OpStatus::Blocked || status == klstream::OpStatus::Idle) {
                    std::this_thread::yield();
                }
            }
        });

        // Thread 3: Scoring & Consumer thread
        std::thread consumer([&]() {
            std::size_t batch_counter = 0;
            while (true) {
                klstream::EventBatch<TraceRecord, MaxBatch> batch;
                if (batch_queue.try_pop(batch)) {
                    ++batch_counter;
                    auto emit_time = std::chrono::steady_clock::now();
                    uint64_t emit_ns = static_cast<uint64_t>(
                        std::chrono::duration_cast<std::chrono::nanoseconds>(
                            emit_time.time_since_epoch()).count());
                    double q_occupancy = in_queue.occupancy();

                    for (std::size_t b = 0; b < batch.count; ++b) {
                        const auto& item = batch.events[b].data;
                        const auto& eval_row = eval_data[item.sample_index];
                        double score = forest.anomaly_score(eval_row.features);

                        uint64_t ingest_ns = item.ingest_time_ns;
                        double latency_us = (emit_ns >= ingest_ns)
                            ? static_cast<double>(emit_ns - ingest_ns) / 1000.0
                            : 0.0;

                        ScoredItem scored;
                        scored.sample_id = eval_row.sample_id;
                        scored.event_id = item.event_id;
                        scored.batch_id = batch_counter;
                        scored.batch_size = batch.count;
                        scored.ingest_time_ns = ingest_ns;
                        scored.emit_time_ns = emit_ns;
                        scored.latency_us = latency_us;
                        scored.queue_depth_frac = q_occupancy;
                        scored.score = score;
                        scored.status = "OK";

                        scored_results.push_back(scored);
                        ++emitted_count;
                    }
                } else {
                    if (batch_queue.is_drained()) {
                        break;
                    }
                    std::this_thread::yield();
                }
            }
        });

        producer.join();
        batcher.join();
        consumer.join();

        // 4. Verify Event Conservation Invariant.
        std::size_t dropped_count = batch_op.dropped_count();
        if (emitted_count + dropped_count != admitted_count || admitted_count != offered_count) {
            std::cerr << "Event conservation failure: offered=" << offered_count
                      << ", admitted=" << admitted_count
                      << ", emitted=" << emitted_count
                      << ", dropped=" << dropped_count << "\n";
            return 2;
        }

        // 5. Write predictions CSV (sample_id, score).
        std::ofstream pred_file(opt.output_path);
        if (!pred_file.is_open()) {
            throw std::runtime_error("Cannot write predictions to: " + opt.output_path);
        }
        pred_file << "sample_id,score\n";
        pred_file << std::fixed << std::setprecision(10);
        for (const auto& res : scored_results) {
            pred_file << res.sample_id << "," << res.score << "\n";
        }
        pred_file.close();

        // 6. Write trace log CSV if requested.
        if (!opt.trace_path.empty()) {
            std::ofstream trace_file(opt.trace_path);
            if (!trace_file.is_open()) {
                throw std::runtime_error("Cannot write trace log to: " + opt.trace_path);
            }
            trace_file << "event_id,sample_id,batch_id,batch_size,ingest_time_ns,emit_time_ns,latency_us,queue_depth,score,status\n";
            trace_file << std::fixed << std::setprecision(6);
            for (const auto& res : scored_results) {
                trace_file << res.event_id << ","
                           << res.sample_id << ","
                           << res.batch_id << ","
                           << res.batch_size << ","
                           << res.ingest_time_ns << ","
                           << res.emit_time_ns << ","
                           << res.latency_us << ","
                           << res.queue_depth_frac << ","
                           << res.score << ","
                           << res.status << "\n";
            }
            trace_file.close();
        }

        // 7. Compute latency percentiles for execution report.
        std::vector<double> latencies;
        latencies.reserve(scored_results.size());
        for (const auto& s : scored_results) latencies.push_back(s.latency_us);
        std::sort(latencies.begin(), latencies.end());

        double p50 = latencies.empty() ? 0.0 : latencies[latencies.size() / 2];
        double p99 = latencies.empty() ? 0.0 : latencies[static_cast<std::size_t>(latencies.size() * 0.99)];

        // Output summary JSON to stdout.
        std::cout << "{\n"
                  << "  \"status\": \"SUCCESS\",\n"
                  << "  \"events_offered\": " << offered_count << ",\n"
                  << "  \"events_admitted\": " << admitted_count << ",\n"
                  << "  \"events_emitted\": " << emitted_count << ",\n"
                  << "  \"events_dropped\": " << dropped_count << ",\n"
                  << "  \"conservation_verified\": true,\n"
                  << "  \"p50_latency_us\": " << p50 << ",\n"
                  << "  \"p99_latency_us\": " << p99 << ",\n"
                  << "  \"trees\": " << opt.trees << ",\n"
                  << "  \"subsample\": " << opt.subsample << ",\n"
                  << "  \"dimension\": " << feature_dim << "\n"
                  << "}\n";

        return 0;
    } catch (const std::exception& ex) {
        std::cerr << "Engine runner error: " << ex.what() << "\n";
        return 1;
    }
}
