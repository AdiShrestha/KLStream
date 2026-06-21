#include <iostream>
#include <string>
#include <vector>
#include <cstdlib>

int main() {
    std::vector<std::string> architectures = {"fixed", "datadriven", "adaptive"};
    int warmup_runs = 5;
    int measurement_runs = 30;
    
    // Create output directories
    system("mkdir -p results/raw");

    // Experiment 1 is mechanism validation (1 run, adaptive)
    std::cout << "--- Running Experiment 1 (Mechanism Validation) ---\n";
    if (system("./build/adaptive_window/adaptive_window_main --architecture=adaptive --out=results/raw/exp1_adaptive.csv --duration=5") != 0) {
        std::cerr << "Aborted by user.\n";
        return 1;
    }

    // Experiments 2,3,5 are the main comparison
    std::cout << "--- Running Experiments 2, 3, 5 (Comparison) ---\n";
    for (const auto& arch : architectures) {
        std::cout << "Architecture: " << arch << "\n";
        
        // Warmup
        for (int i = 0; i < warmup_runs; ++i) {
            std::cout << "  Warmup " << (i+1) << "/" << warmup_runs << "\n";
            std::string cmd = "./build/adaptive_window/adaptive_window_main --architecture=" + arch + 
                              " --out=results/raw/warmup_" + arch + "_" + std::to_string(i) + ".csv --duration=5 > /dev/null";
            if (system(cmd.c_str()) != 0) {
                std::cerr << "Aborted by user.\n";
                return 1;
            }
        }
        
        // Measurement
        for (int i = 0; i < measurement_runs; ++i) {
            std::cout << "  Measurement " << (i+1) << "/" << measurement_runs << "\n";
            std::string cmd = "./build/adaptive_window/adaptive_window_main --architecture=" + arch + 
                              " --out=results/raw/run_" + arch + "_" + std::to_string(i) + ".csv --duration=5 > /dev/null";
            if (system(cmd.c_str()) != 0) {
                std::cerr << "Aborted by user.\n";
                return 1;
            }
        }
    }
    
    std::cout << "Harness complete.\n";
    return 0;
}
