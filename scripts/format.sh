#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

if command -v clang-format &> /dev/null; then
    echo "[INFO] Formatting source files with clang-format..."
    find source -type f \( -name "*.hpp" -o -name "*.cpp" \) -exec clang-format -i {} +
    echo "[OK] Formatting complete."
else
    echo "[WARN] clang-format not found in PATH; skipping formatting."
fi
