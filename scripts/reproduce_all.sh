#!/usr/bin/env bash
# =============================================================================
# reproduce_all.sh — Full KLStream-AdaptiveWindow Reproduction Pipeline
#
# Runs every step needed to reproduce the results in the paper/report,
# in the exact order they were originally produced.
#
# Prerequisites:
#   - CMake build already compiled (cmake -B build && cmake --build build --parallel)
#   - Python 3 with: pandas, numpy, scipy, matplotlib, scikit-learn
#   - Raw LOBSTER data files placed in data/raw/ (see Step 0 below)
#
# Usage:
#   bash scripts/reproduce_all.sh 2>&1 | tee results/reproduction_log.txt
#
# Expected final numbers (from results/final_aggregate_output.txt):
#   Fixed:       PA%20 F1 = 0.2096,  P95 latency = 44.87 ms
#   DataDriven:  PA%20 F1 = 0.1805,  P95 latency = 78.30 ms
#   Adaptive:    PA%20 F1 = 0.1135,  P95 latency = 19.00 ms
# =============================================================================
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo "=== KLStream-AdaptiveWindow Full Reproduction ==="
echo "Working directory: $(pwd)"
echo "Start time: $(date)"
echo ""

# ---------------------------------------------------------------------------
# Step 0: Preprocessing (skip if replay file already exists)
# ---------------------------------------------------------------------------
echo "--- Step 0: Preprocessing (skip if data/replay/ exists) ---"
if [ -f "data/replay/replay_AAPL_20120621.csv" ]; then
    echo "  [SKIP] data/replay/replay_AAPL_20120621.csv already exists."
else
    echo "  Running preprocess_lobster.py ..."
    echo "  (Requires raw LOBSTER files in data/raw/)"
    python3 preprocessing/preprocess_lobster.py \
        --message  data/raw/AAPL_2012-06-21_34200000_57600000_message_1.csv \
        --orderbook data/raw/AAPL_2012-06-21_34200000_57600000_orderbook_1.csv \
        --out      data/replay/replay_AAPL_20120621.csv \
        --seed 42
    echo "  Done: data/replay/replay_AAPL_20120621.csv"
fi
echo ""

# ---------------------------------------------------------------------------
# Step 1: Build (ensures binary is up to date)
# ---------------------------------------------------------------------------
echo "--- Step 1: Building C++ binaries ---"
cmake -B build -G Ninja \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
    -DKLSTREAM_BUILD_TESTS=OFF \
    -DKLSTREAM_BUILD_BENCHMARKS=OFF \
    -DKLSTREAM_BUILD_EXAMPLES=ON \
    -DKLSTREAM_ENABLE_SANITIZERS=OFF
cmake --build build --parallel
echo "  Done: build/adaptive_window/adaptive_window_main"
echo ""

# ---------------------------------------------------------------------------
# Step 2: Train Isolation Forest
# ---------------------------------------------------------------------------
echo "--- Step 2: Training Isolation Forest ---"
./build/adaptive_window/train_forest
echo "  Done: forest model artifacts written"
echo ""

# ---------------------------------------------------------------------------
# Step 3: Main 30-run comparison (speed_factor=1460, all 3 architectures)
# ---------------------------------------------------------------------------
echo "--- Step 3: Main 90-run sweep (30 runs × 3 architectures, speed_factor=1460) ---"
# Clear previous results to guarantee a fresh run
mkdir -p results/raw/exp2_3
python3 analysis/run_experiments.py
# run_experiments.py verifies: exactly 30 files per architecture, all fresh
echo ""

# ---------------------------------------------------------------------------
# Step 4: Aggregate results (produces the numbers in the paper)
# ---------------------------------------------------------------------------
echo "--- Step 4: Aggregating results ---"
python3 analysis/aggregate_results.py | tee results/final_aggregate_output.txt
echo ""

# ---------------------------------------------------------------------------
# Step 5: Sensitivity grid — Experiment 4 (270 runs, speed_factor=1460)
# ---------------------------------------------------------------------------
echo "--- Step 5: Sensitivity grid — 9 cells × 30 reps at speed_factor=1460 ---"
# Always call with explicit speed_factor=1460 and n_reps=30 to be unambiguous.
# Output: results/experiment4_grid_replicated.csv (has speed_factor and n_reps columns)
python3 analysis/run_experiment4.py 1460 30
echo ""

# ---------------------------------------------------------------------------
# Step 6: Generate figures
# ---------------------------------------------------------------------------
echo "--- Step 6: Generating figures ---"
mkdir -p results/figures
python3 analysis/plot_pareto.py
python3 analysis/plot_hysteresis.py
python3 analysis/bench_inference_scaling.py
echo ""

# ---------------------------------------------------------------------------
# Step 7: Overhead measurement (Experiment 5)
# ---------------------------------------------------------------------------
echo "--- Step 7: Controller overhead measurement ---"
python3 analysis/run_experiment5.py
echo ""

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
echo "=== Reproduction complete ==="
echo "End time: $(date)"
echo ""
echo "Output locations:"
echo "  Aggregate numbers   : results/final_aggregate_output.txt"
echo "  Aggregated CSV      : results/aggregated_results.csv"
echo "  Exp4 grid (replicated): results/experiment4_grid_replicated.csv"
echo "  Figures             : results/figures/"
echo "  Raw per-run CSVs    : results/raw/exp2_3/ (90 files)"
echo ""
echo "Expected values:"
echo "  Fixed:      PA%20 F1 = 0.2096  P95 lat = 44.87 ms"
echo "  DataDriven: PA%20 F1 = 0.1805  P95 lat = 78.30 ms"
echo "  Adaptive:   PA%20 F1 = 0.1135  P95 lat = 19.00 ms"
