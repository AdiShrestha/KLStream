#!/usr/bin/env bash
set -euo pipefail

PRESET="${1:-release}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo "[INFO] Running test suite with preset: ${PRESET}"
if [[ ! -d "build/${PRESET}" ]]; then
    "${SCRIPT_DIR}/build.sh" "${PRESET}"
fi

ctest --preset "${PRESET}" --output-on-failure
echo "[OK] All tests passed successfully."
