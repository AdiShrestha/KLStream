#!/usr/bin/env bash
# scripts/run_all_benchmarks.sh
set -e

BUILD=./build
RESULTS=./research/results
mkdir -p $RESULTS

echo "Running SPSC queue benchmarks..."
$BUILD/benchmarks/bench_spsc_queue \
    --benchmark_format=csv \
    --benchmark_out=$RESULTS/spsc_queue.csv

echo "Running pipeline throughput benchmarks..."
$BUILD/benchmarks/bench_pipeline_throughput \
    --benchmark_format=csv \
    --benchmark_out=$RESULTS/pipeline_throughput.csv

echo "Running YSB benchmark..."
$BUILD/benchmarks/bench_ysb \
    --benchmark_format=csv \
    --benchmark_out=$RESULTS/ysb.csv

echo "All benchmarks complete. Results in $RESULTS/"
