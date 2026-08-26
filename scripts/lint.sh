#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

if command -v clang-tidy &> /dev/null; then
    echo "[INFO] Running clang-tidy on source tree..."
    if [[ ! -f "build/debug/compile_commands.json" ]]; then
        cmake -B build/debug -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
    fi
    find source -type f -name "*.cpp" -exec clang-tidy -p build/debug {} +
    echo "[OK] Linting complete."
else
    echo "[WARN] clang-tidy not found in PATH; skipping linting."
fi
