#!/usr/bin/env bash
set -euo pipefail

PRESET="${1:-release}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo "[INFO] Building with preset: ${PRESET}"
cmake --preset "${PRESET}"
cmake --build --preset "${PRESET}" --parallel
echo "[OK] Build completed successfully."
