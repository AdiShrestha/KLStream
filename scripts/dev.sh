#!/usr/bin/env bash
# scripts/dev.sh — Unified developer entry point for KLStream

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# Output formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[OK]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

usage() {
    cat <<EOF
KLStream Developer CLI

Usage: $0 <command> [arguments]

Commands:
    build [preset]      Build project using CMakePresets (default: release)
    test [preset]       Run tests using CTestPresets (default: release)
    bench               Build and run microbenchmarks
    clean               Remove build directories and artifacts
    format              Format C++ source files with clang-format
    lint                Run clang-tidy static analysis
    docker [subcommand] Build and run in Docker container (default: shell)
    help                Show this help message

Presets:
    release             Optimized native build
    debug               Debug symbols without optimization
    asan                AddressSanitizer and UndefinedBehaviorSanitizer
    tsan                ThreadSanitizer
    ubsan               UndefinedBehaviorSanitizer
    benchmarks          Release build with Google Benchmark targets

Examples:
    $0 build
    $0 build debug
    $0 test
    $0 test asan
    $0 bench
    $0 clean
EOF
}

cmd_build() {
    local preset="${1:-release}"
    "${SCRIPT_DIR}/build.sh" "${preset}"
}

cmd_test() {
    local preset="${1:-release}"
    "${SCRIPT_DIR}/test.sh" "${preset}"
}

cmd_bench() {
    log_info "Building benchmarks preset..."
    "${SCRIPT_DIR}/build.sh" benchmarks

    log_info "Running SPSC Queue microbenchmark..."
    if [[ -x "build/benchmarks/source/benchmarks/bench_spsc_queue" ]]; then
        ./build/benchmarks/source/benchmarks/bench_spsc_queue --benchmark_min_time=0.1s
    fi

    log_info "Running Pipeline Throughput microbenchmark..."
    if [[ -x "build/benchmarks/source/benchmarks/bench_pipeline_throughput" ]]; then
        ./build/benchmarks/source/benchmarks/bench_pipeline_throughput --benchmark_min_time=0.1s
    fi

    log_info "Running YSB microbenchmark..."
    if [[ -x "build/benchmarks/source/benchmarks/bench_ysb" ]]; then
        ./build/benchmarks/source/benchmarks/bench_ysb --benchmark_min_time=0.1s
    fi

    log_success "Benchmarks completed."
}

cmd_clean() {
    log_info "Cleaning build artifacts and scratch files..."
    rm -rf build build-* build_* cmake-build-*
    rm -f compile_commands.json
    log_success "Clean completed."
}

cmd_format() {
    "${SCRIPT_DIR}/format.sh"
}

cmd_lint() {
    "${SCRIPT_DIR}/lint.sh"
}

cmd_docker() {
    local subcmd="${1:-shell}"
    shift || true

    case "$subcmd" in
        build)
            log_info "Building Docker release image..."
            docker compose build app
            log_success "Docker build complete."
            ;;
        shell)
            log_info "Entering development shell in Docker..."
            docker compose run --rm dev /bin/bash
            ;;
        test)
            log_info "Running test suite inside Docker..."
            docker compose run --rm dev ./scripts/dev.sh test release
            ;;
        *)
            log_error "Unknown docker subcommand: $subcmd"
            exit 1
            ;;
    esac
}

main() {
    local cmd="${1:-help}"
    shift || true

    case "$cmd" in
        build)  cmd_build "$@" ;;
        test)   cmd_test "$@" ;;
        bench)  cmd_bench "$@" ;;
        clean)  cmd_clean "$@" ;;
        format) cmd_format "$@" ;;
        lint)   cmd_lint "$@" ;;
        docker) cmd_docker "$@" ;;
        help|--help|-h) usage ;;
        *)
            log_error "Unknown command: $cmd"
            usage
            exit 1
            ;;
    esac
}

main "$@"
