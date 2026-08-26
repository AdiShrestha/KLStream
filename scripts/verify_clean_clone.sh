#!/usr/bin/env bash
set -euo pipefail

###############################################################################
# verify_clean_clone.sh — Clean-clone isolated platform verification
#
# Unpacks dist/klstream-0.2.0.tar.gz into an isolated temporary directory
# (with spaces in the path name), verifies structural integrity, and records
# results in results/clean_clone_verification_report.json.
###############################################################################

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
VERSION="0.2.0"
TARBALL="${REPO_ROOT}/dist/klstream-${VERSION}.tar.gz"

echo "================================================================"
echo "  KLStream Clean-Clone Isolated Verification v${VERSION}"
echo "================================================================"

# Verify tarball exists
if [ ! -f "${TARBALL}" ]; then
    echo "ERROR: Distribution tarball not found at ${TARBALL}"
    exit 1
fi

# Create isolated temp directory with spaces in path
CLONE_DIR=$(mktemp -d "${TMPDIR:-/tmp}/klstream clean test.XXXXXX")
echo ""
echo "[1/5] Extracting to isolated path with spaces: ${CLONE_DIR}"

tar xzf "${TARBALL}" -C "${CLONE_DIR}"
EXTRACT_DIR="${CLONE_DIR}/klstream-${VERSION}"

if [ ! -d "${EXTRACT_DIR}" ]; then
    echo "ERROR: Expected directory ${EXTRACT_DIR} not found after extraction"
    rm -rf "${CLONE_DIR}"
    exit 1
fi

echo "  Extraction successful."

# Count extracted files
TOTAL_FILES=$(find "${EXTRACT_DIR}" -type f | wc -l | tr -d ' ')
echo "  Total extracted files: ${TOTAL_FILES}"

echo ""
echo "[2/5] Verifying essential files exist..."

ESSENTIAL_FILES=(
    "CMakeLists.txt"
    "LICENSE"
    "README.md"
    "CITATION.cff"
)

MISSING_COUNT=0
for f in "${ESSENTIAL_FILES[@]}"; do
    if [ -f "${EXTRACT_DIR}/${f}" ]; then
        echo "  [OK] ${f}"
    else
        echo "  [MISSING] ${f}"
        MISSING_COUNT=$((MISSING_COUNT + 1))
    fi
done

echo ""
echo "[3/5] Verifying source tree structure..."

SOURCE_DIRS=(
    "source/include"
    "source/tests"
    "source/benchmarks"
    "source/apps"
    "source/experiments"
)

for d in "${SOURCE_DIRS[@]}"; do
    if [ -d "${EXTRACT_DIR}/${d}" ]; then
        COUNT=$(find "${EXTRACT_DIR}/${d}" -type f | wc -l | tr -d ' ')
        echo "  [OK] ${d}/ (${COUNT} files)"
    else
        echo "  [MISSING] ${d}/"
        MISSING_COUNT=$((MISSING_COUNT + 1))
    fi
done

echo ""
echo "[4/5] Verifying no extraneous files leaked..."

EXTRANEOUS=0
# Check for .git directories
GIT_DIRS=$(find "${EXTRACT_DIR}" -name ".git" -type d 2>/dev/null | wc -l | tr -d ' ')
if [ "$GIT_DIRS" -gt 0 ]; then
    echo "  [FAIL] Found .git directories in extraction"
    EXTRANEOUS=$((EXTRANEOUS + GIT_DIRS))
else
    echo "  [OK] No .git directories"
fi

# Check for __pycache__
PYCACHE=$(find "${EXTRACT_DIR}" -name "__pycache__" -type d 2>/dev/null | wc -l | tr -d ' ')
if [ "$PYCACHE" -gt 0 ]; then
    echo "  [FAIL] Found __pycache__ directories"
    EXTRANEOUS=$((EXTRANEOUS + PYCACHE))
else
    echo "  [OK] No __pycache__ directories"
fi

# Check for .DS_Store
DSSTORE=$(find "${EXTRACT_DIR}" -name ".DS_Store" 2>/dev/null | wc -l | tr -d ' ')
if [ "$DSSTORE" -gt 0 ]; then
    echo "  [FAIL] Found .DS_Store files"
    EXTRANEOUS=$((EXTRANEOUS + DSSTORE))
else
    echo "  [OK] No .DS_Store files"
fi

# Check for factory/ (should not be in release)
if [ -d "${EXTRACT_DIR}/factory" ]; then
    echo "  [FAIL] factory/ directory leaked into release"
    EXTRANEOUS=$((EXTRANEOUS + 1))
else
    echo "  [OK] No factory/ directory"
fi

# Check for project/ (should not be in release)
if [ -d "${EXTRACT_DIR}/project" ]; then
    echo "  [FAIL] project/ directory leaked into release"
    EXTRANEOUS=$((EXTRANEOUS + 1))
else
    echo "  [OK] No project/ directory"
fi

echo ""
echo "[5/5] Attempting CMake configuration in isolated path..."

BUILD_STATUS="SKIPPED"
CMAKE_EXIT="-1"
TEST_PASSED=0
TEST_TOTAL=0

if command -v cmake >/dev/null 2>&1; then
    BUILD_DIR="${EXTRACT_DIR}/build"
    mkdir -p "${BUILD_DIR}"
    
    # Try cmake configure
    if cmake -B "${BUILD_DIR}" -S "${EXTRACT_DIR}" -DCMAKE_BUILD_TYPE=Release >/dev/null 2>&1; then
        CMAKE_EXIT="0"
        echo "  [OK] CMake configure succeeded in path with spaces"
        
        # Try build
        if cmake --build "${BUILD_DIR}" --parallel 2>/dev/null; then
            echo "  [OK] CMake build succeeded"
            BUILD_STATUS="BUILD_PASS"
            
            # Try running tests
            if command -v ctest >/dev/null 2>&1; then
                CTEST_OUTPUT=$(cd "${BUILD_DIR}" && ctest --output-on-failure 2>&1) || true
                TEST_TOTAL=$(echo "$CTEST_OUTPUT" | grep -oE '[0-9]+ tests' | head -1 | grep -oE '[0-9]+' || echo "0")
                TEST_PASSED=$(echo "$CTEST_OUTPUT" | grep -oE '[0-9]+ tests passed' | head -1 | grep -oE '[0-9]+' || echo "0")
                
                if [ "$TEST_PASSED" = "$TEST_TOTAL" ] && [ "$TEST_TOTAL" -gt 0 ]; then
                    BUILD_STATUS="ALL_TESTS_PASS"
                    echo "  [OK] CTest: ${TEST_PASSED}/${TEST_TOTAL} tests passed"
                else
                    BUILD_STATUS="TESTS_PARTIAL"
                    echo "  [WARN] CTest: ${TEST_PASSED}/${TEST_TOTAL} tests passed"
                fi
            else
                echo "  [SKIP] ctest not found"
            fi
        else
            BUILD_STATUS="BUILD_FAIL"
            echo "  [FAIL] CMake build failed"
        fi
    else
        CMAKE_EXIT="1"
        BUILD_STATUS="CONFIGURE_FAIL"
        echo "  [FAIL] CMake configure failed in path with spaces"
    fi
else
    echo "  [SKIP] cmake not available — structural verification only"
fi

# Clean up
rm -rf "${CLONE_DIR}"

# Generate report
OVERALL_STATUS="PASS"
if [ "$MISSING_COUNT" -gt 0 ] || [ "$EXTRANEOUS" -gt 0 ]; then
    OVERALL_STATUS="FAIL"
fi

python3 -c "
import json
report = {
    'manifest_version': '1.0.0',
    'release_version': '${VERSION}',
    'extraction_path': '${CLONE_DIR}',
    'path_contains_spaces': True,
    'total_extracted_files': ${TOTAL_FILES},
    'essential_files_missing': ${MISSING_COUNT},
    'extraneous_files_found': ${EXTRANEOUS},
    'cmake_exit_code': ${CMAKE_EXIT},
    'build_status': '${BUILD_STATUS}',
    'tests_passed': ${TEST_PASSED},
    'tests_total': ${TEST_TOTAL},
    'overall_status': '${OVERALL_STATUS}'
}
with open('${REPO_ROOT}/results/clean_clone_verification_report.json', 'w') as f:
    json.dump(report, f, indent=2)
print(json.dumps(report, indent=2))
"

echo ""
echo "================================================================"
if [ "$OVERALL_STATUS" = "PASS" ]; then
    echo "  Clean-clone verification completed successfully (PASS)"
else
    echo "  Clean-clone verification FAILED"
fi
echo "================================================================"
