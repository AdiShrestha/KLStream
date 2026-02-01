#!/usr/bin/env bash
# Development environment entry script

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[OK]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

usage() {
    cat <<EOF
KLStream Development Environment

Usage: $0 <command> [options]

Commands:
    build       Build the project (default: Debug)
    test        Run all tests
    bench       Run benchmarks
    clean       Clean build artifacts
    docker      Build and run in Docker (x86_64)
    shell       Enter Docker development shell
    format      Format code with clang-format
    lint        Run clang-tidy

Options:
    --release   Build with Release configuration
    --sanitize  Enable sanitizers (ASan + UBSan)

Examples:
    $0 build
    $0 build --release
    $0 test
    $0 docker shell

EOF
}

cmd_build() {
    local build_type="Debug"
    local sanitizers="OFF"
    
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --release) build_type="Release" ;;
            --sanitize) sanitizers="ON" ;;
            *) log_error "Unknown option: $1"; exit 1 ;;
        esac
        shift
    done
    
    log_info "Building with configuration: $build_type"
    
    cmake -B build -G Ninja \
        -DCMAKE_BUILD_TYPE="$build_type" \
        -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
        -DKLSTREAM_BUILD_TESTS=ON \
        -DKLSTREAM_BUILD_BENCHMARKS=ON \
        -DKLSTREAM_BUILD_EXAMPLES=ON \
        -DKLSTREAM_ENABLE_SANITIZERS="$sanitizers"
    
    cmake --build build --parallel
    
    # Link compile_commands.json for IDE support
    if [[ -f build/compile_commands.json ]]; then
        ln -sf build/compile_commands.json compile_commands.json
    fi
    
    log_success "Build complete"
}

cmd_test() {
    if [[ ! -d build ]]; then
        log_warn "Build directory not found, building first..."
        cmd_build
    fi
    
    log_info "Running tests..."
    cd build
    ctest --output-on-failure --parallel
    log_success "All tests passed"
}

cmd_bench() {
    if [[ ! -f build/benchmarks/throughput_benchmark ]]; then
        log_warn "Benchmarks not built, building with Release..."
        cmd_build --release
    fi
    
    log_info "Running throughput benchmark..."
    ./build/benchmarks/throughput_benchmark
    
    log_info "Running latency benchmark..."
    ./build/benchmarks/latency_benchmark
}

cmd_clean() {
    log_info "Cleaning build artifacts..."
    rm -rf build
    rm -f compile_commands.json
    log_success "Clean complete"
}

cmd_docker() {
    local subcmd="${1:-shell}"
    shift || true
    
    case "$subcmd" in
        build)
            log_info "Building Docker image (linux/amd64)..."
            docker compose build dev
            log_success "Docker build complete"
            ;;
        shell)
            log_info "Entering Docker development shell..."
            docker compose run --rm dev /bin/bash
            ;;
        run)
            log_info "Building and running in Docker..."
            docker compose build build
            docker compose up build
            ;;
        *)
            log_error "Unknown docker command: $subcmd"
            exit 1
            ;;
    esac
}

cmd_format() {
    log_info "Formatting code..."
    
    find include src examples tests benchmarks \
        -name '*.cpp' -o -name '*.hpp' -o -name '*.h' | \
        xargs clang-format -i
    
    log_success "Formatting complete"
}

cmd_lint() {
    if [[ ! -f build/compile_commands.json ]]; then
        log_warn "compile_commands.json not found, building first..."
        cmd_build
    fi
    
    log_info "Running clang-tidy..."
    
    find include src examples \
        -name '*.cpp' | \
        xargs clang-tidy -p build
    
    log_success "Linting complete"
}

# Main entry point
main() {
    local cmd="${1:-help}"
    shift || true
    
    case "$cmd" in
        build)  cmd_build "$@" ;;
        test)   cmd_test "$@" ;;
        bench)  cmd_bench "$@" ;;
        clean)  cmd_clean "$@" ;;
        docker) cmd_docker "$@" ;;
        format) cmd_format "$@" ;;
        lint)   cmd_lint "$@" ;;
        help|--help|-h) usage ;;
        *)
            log_error "Unknown command: $cmd"
            usage
            exit 1
            ;;
    esac
}

main "$@"
