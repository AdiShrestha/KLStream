// adaptive_window/main.cpp
#include "klstream/core/runtime.hpp"
#include "klstream/core/metrics.hpp"
#include "klstream/operators/source.hpp"
#include "klstream/operators/window.hpp"
#include "klstream/window/types.hpp"
#include "klstream/window/adaptive_window_op.hpp"
#include "klstream/window/data_driven_window_op.hpp"
#include "klstream/window/inference_op.hpp"
#include "klstream/window/financial_tick_source.hpp"
#include "klstream/window/result_sink.hpp"
#include "klstream/model/isolation_forest.hpp"

#include <chrono>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>
#include <memory>
#include <stdexcept>

using namespace klstream;

// Loads a pretrained forest written by train_forest.cpp (Section 26) as a
// flat binary blob — see that section for the (de)serialisation format.
IsolationForest<FeatureVector::kDim> load_forest(const std::string& path) {
    IsolationForest<FeatureVector::kDim> forest(0, 0);
    std::ifstream in(path, std::ios::binary);
    if (!in) throw std::runtime_error("failed to open forest path: " + path);
    forest.load(in);
    return forest;
}

int main(int argc, char** argv) {
    std::string architecture = "adaptive";   // fixed | datadriven | adaptive
    std::string replay_csv   = "data/replay/replay_AAPL_20120621.csv";
    std::string forest_path  = "data/forest.bin";
    std::string out_csv      = "results/raw/run.csv";
    int         duration_sec = 60;
    ReplayMode  mode         = ReplayMode::MaxRate;
    double      speed_factor = 1.0;
    
    // Sensitivity parameters
    double occ_low = 0.30;
    double occ_high = 0.70;
    double shrink_factor = 0.70;
    double grow_factor = 1.15;

    for (int i = 1; i < argc; ++i) {
        std::string a = argv[i];
        auto val = [&](const char* flag){ return a.rfind(flag, 0) == 0; };
        if (val("--architecture=")) architecture = a.substr(15);
        else if (val("--replay=")) replay_csv = a.substr(9);
        else if (val("--forest=")) forest_path = a.substr(9);
        else if (val("--out=")) out_csv = a.substr(6);
        else if (val("--duration=")) duration_sec = std::stoi(a.substr(11));
        else if (val("--speed-factor=")) speed_factor = std::stod(a.substr(15));
        else if (val("--occ_low=")) occ_low = std::stod(a.substr(10));
        else if (val("--occ_high=")) occ_high = std::stod(a.substr(11));
        else if (val("--shrink=")) shrink_factor = std::stod(a.substr(9));
        else if (val("--grow=")) grow_factor = std::stod(a.substr(7));
        else if (val("--preserve-timing")) mode = ReplayMode::PreserveTiming;
    }

    auto forest = load_forest(forest_path);
    auto rows   = load_replay_csv(replay_csv);

    // ── Queues ────────────────────────────────────────────────────────────
    SPSCQueue<Event<FeatureVector>> q_src_feat(4096);   // source -> feature extract (identity here: TickSource already emits FeatureVector)
    SPSCQueue<Event<WindowBatch>>   q_win_inf(64);       // window stage -> InferenceOp
                                                            // SMALL capacity — see Section 7.3
    SPSCQueue<Event<DetectionResult>> q_inf_snk(4096);

    OperatorMetrics m_src("tick_source"), m_win("window_op"),
                    m_inf("inference"),   m_snk("result_sink");

    // ── Source ────────────────────────────────────────────────────────────
    FinancialTickSource tick_src(std::move(rows), mode, speed_factor);
    SourceOperator<FeatureVector> source("tick_source", &q_src_feat,
        [&tick_src](Event<FeatureVector>& out, std::uint64_t seq) {
            return tick_src(out, seq);
        });
    source.attach_metrics(&m_src);

    // ── Window stage (the variable under test) ──────────────────────────
    std::unique_ptr<IOperator> window_op;
    AdaptiveWindowOp*    adaptive_ptr = nullptr;   // kept for occupancy logging below

    if (architecture == "fixed") {
        auto* op = new TumblingCountWindow<FeatureVector, WindowBatch>(
            "fixed_window", &q_src_feat, &q_win_inf, 128,
            [](const std::vector<Event<FeatureVector>>& buf) {
                WindowBatch wb;
                for (const auto& ev : buf) wb.push_back(ev.data, ev.seq);
                return wb;
            });
        window_op.reset(op);
    } else if (architecture == "datadriven") {
        window_op = std::make_unique<DataDrivenWindowOp>(
            "data_driven_window", &q_src_feat, &q_win_inf);
    } else { // adaptive
        auto* op = new AdaptiveWindowOp("adaptive_window", &q_src_feat, &q_win_inf, 16, MAX_WINDOW_SIZE, occ_low, occ_high, shrink_factor, grow_factor);
        adaptive_ptr = op;
        window_op.reset(op);
    }
    window_op->attach_metrics(&m_win);

    // ── Inference + Sink ─────────────────────────────────────────────────
    InferenceOp inference("inference", &q_win_inf, &q_inf_snk, &forest);
    inference.attach_metrics(&m_inf);

    ResultSink sink("result_sink", &q_inf_snk, out_csv);
    sink.attach_metrics(&m_snk);

    // ── Runtime ───────────────────────────────────────────────────────────
    Runtime rt;
    rt.add_worker(CoreAffinity::Performance);   // 0: source
    rt.add_worker(CoreAffinity::Performance);   // 1: window stage
    rt.add_worker(CoreAffinity::Performance);   // 2: inference (heaviest compute)
    rt.add_worker(CoreAffinity::Efficiency);    // 3: sink

    rt.register_op(&source, 0);
    rt.register_op(window_op.get(), 1);
    rt.register_op(&inference, 2);
    rt.register_op(&sink, 3);

    for (auto* m : {&m_src, &m_win, &m_inf, &m_snk}) rt.metrics().add(m);

    std::cout << "Running architecture=" << architecture
              << " for " << duration_sec << "s, output=" << out_csv << "\n";
              
    // Occupancy logger for Exp 1
    std::atomic<bool> running{true};
    std::thread occ_logger([&]() {
        if (!adaptive_ptr) return;
        std::ofstream log("results/raw/occupancy_log.csv");
        log << "time_ms,window_size,occupancy,raw_depth\n";
        auto start = std::chrono::steady_clock::now();
        while (running) {
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
            auto now = std::chrono::steady_clock::now();
            auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(now - start).count();
            log << ms << "," 
                << adaptive_ptr->controller().current() << ","
                << q_win_inf.occupancy() << ","
                << q_win_inf.occupancy() * q_win_inf.capacity() << "\n";
        }
    });

    rt.start();
    rt.wait_for(std::chrono::seconds(duration_sec));
    rt.stop();
    
    running = false;
    occ_logger.join();

    if (adaptive_ptr) {
        std::cout << "Window-size direction changes: "
                  << adaptive_ptr->controller().direction_changes() << "\n";
        std::cout << "Mean Controller Overhead: " << adaptive_ptr->mean_overhead_ns() << " ns/call\n";
    } else if (architecture == "datadriven" && window_op) {
        auto* dd_ptr = static_cast<DataDrivenWindowOp*>(window_op.get());
        std::cout << "Mean Controller Overhead: " << dd_ptr->mean_overhead_ns() << " ns/call\n";
    }
    return 0;
}
