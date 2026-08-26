#!/usr/bin/env bash
set -euo pipefail

###############################################################################
# package_release.sh — Release Allowlist Assembly and Distribution Packaging
#
# Assembles:
#   dist/klstream-0.2.0.tar.gz        (source code, build, benchmarks, tests)
#   dist/klstream-paper-0.2.0.tar.gz  (manuscript, figures, tables, bibliography)
#   dist/SHA256SUMS                   (cryptographic digests)
#   results/release_packaging_manifest.json
###############################################################################

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
VERSION="0.2.0"
DIST_DIR="${REPO_ROOT}/dist"
STAGING_SRC="${REPO_ROOT}/.release-staging-src"
STAGING_PAPER="${REPO_ROOT}/.release-staging-paper"

echo "================================================================"
echo "  KLStream Release Packaging v${VERSION}"
echo "================================================================"

# Clean previous artifacts
rm -rf "${DIST_DIR}" "${STAGING_SRC}" "${STAGING_PAPER}"
mkdir -p "${DIST_DIR}"

###############################################################################
# SOURCE DISTRIBUTION — strict allowlist
###############################################################################
echo ""
echo "[1/4] Assembling source distribution..."

mkdir -p "${STAGING_SRC}/klstream-${VERSION}"
DST="${STAGING_SRC}/klstream-${VERSION}"

# Root build and metadata files
for f in CMakeLists.txt LICENSE README.md CITATION.cff; do
    if [ -f "${REPO_ROOT}/${f}" ]; then
        cp "${REPO_ROOT}/${f}" "${DST}/"
    fi
done

# Copy Dockerfile and compose if they exist
for f in Dockerfile compose.yaml docker-compose.yaml; do
    if [ -f "${REPO_ROOT}/${f}" ]; then
        cp "${REPO_ROOT}/${f}" "${DST}/"
    fi
done

# Source code tree
if [ -d "${REPO_ROOT}/source" ]; then
    cp -r "${REPO_ROOT}/source" "${DST}/source"
fi

# Scripts (only production scripts, not internal factory tools)
if [ -d "${REPO_ROOT}/scripts" ]; then
    mkdir -p "${DST}/scripts"
    for script in "${REPO_ROOT}/scripts/"*.sh "${REPO_ROOT}/scripts/"*.py; do
        [ -f "$script" ] && cp "$script" "${DST}/scripts/"
    done
fi

# Requirements file
if [ -f "${REPO_ROOT}/requirements.txt" ]; then
    cp "${REPO_ROOT}/requirements.txt" "${DST}/"
fi

# CI workflows
if [ -d "${REPO_ROOT}/.github" ]; then
    cp -r "${REPO_ROOT}/.github" "${DST}/.github"
fi

# Remove any .git directories, __pycache__, build caches
find "${STAGING_SRC}" -name ".git" -type d -exec rm -rf {} + 2>/dev/null || true
find "${STAGING_SRC}" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find "${STAGING_SRC}" -name "*.pyc" -delete 2>/dev/null || true
find "${STAGING_SRC}" -name ".DS_Store" -delete 2>/dev/null || true

SRC_FILE_COUNT=$(find "${STAGING_SRC}" -type f | wc -l | tr -d ' ')
echo "  Source files staged: ${SRC_FILE_COUNT}"

# Create tarball
(cd "${STAGING_SRC}" && tar czf "${DIST_DIR}/klstream-${VERSION}.tar.gz" "klstream-${VERSION}")
echo "  Created: dist/klstream-${VERSION}.tar.gz"

###############################################################################
# PAPER DISTRIBUTION — manuscript allowlist
###############################################################################
echo ""
echo "[2/4] Assembling paper distribution..."

mkdir -p "${STAGING_PAPER}/klstream-paper-${VERSION}"
PDST="${STAGING_PAPER}/klstream-paper-${VERSION}"

# Manuscript files
if [ -d "${REPO_ROOT}/paper" ]; then
    mkdir -p "${PDST}/paper"
    for f in "${REPO_ROOT}/paper/"*.md "${REPO_ROOT}/paper/"*.tex "${REPO_ROOT}/paper/"*.bib "${REPO_ROOT}/paper/"*.sh "${REPO_ROOT}/paper/"*.py; do
        [ -f "$f" ] && cp "$f" "${PDST}/paper/"
    done
fi

# Figures and tables
if [ -d "${REPO_ROOT}/results/figures" ]; then
    mkdir -p "${PDST}/results/figures"
    cp -r "${REPO_ROOT}/results/figures/"* "${PDST}/results/figures/" 2>/dev/null || true
fi
if [ -d "${REPO_ROOT}/results/tables" ]; then
    mkdir -p "${PDST}/results/tables"
    cp -r "${REPO_ROOT}/results/tables/"* "${PDST}/results/tables/" 2>/dev/null || true
fi

# Remove caches
find "${STAGING_PAPER}" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find "${STAGING_PAPER}" -name "*.pyc" -delete 2>/dev/null || true
find "${STAGING_PAPER}" -name ".DS_Store" -delete 2>/dev/null || true

PAPER_FILE_COUNT=$(find "${STAGING_PAPER}" -type f | wc -l | tr -d ' ')
echo "  Paper files staged: ${PAPER_FILE_COUNT}"

# Create tarball
(cd "${STAGING_PAPER}" && tar czf "${DIST_DIR}/klstream-paper-${VERSION}.tar.gz" "klstream-paper-${VERSION}")
echo "  Created: dist/klstream-paper-${VERSION}.tar.gz"

###############################################################################
# SHA-256 DIGESTS
###############################################################################
echo ""
echo "[3/4] Computing SHA-256 digests..."

cd "${DIST_DIR}"
if command -v sha256sum >/dev/null 2>&1; then
    sha256sum klstream-*.tar.gz > SHA256SUMS
elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 klstream-*.tar.gz > SHA256SUMS
else
    echo "WARNING: No sha256sum or shasum found"
    echo "UNAVAILABLE" > SHA256SUMS
fi
cd "${REPO_ROOT}"

echo "  SHA256SUMS written to dist/SHA256SUMS"
cat "${DIST_DIR}/SHA256SUMS"

###############################################################################
# PACKAGING MANIFEST
###############################################################################
echo ""
echo "[4/4] Generating packaging manifest..."

SRC_SIZE=$(stat -f%z "${DIST_DIR}/klstream-${VERSION}.tar.gz" 2>/dev/null || stat -c%s "${DIST_DIR}/klstream-${VERSION}.tar.gz" 2>/dev/null || echo "0")
PAPER_SIZE=$(stat -f%z "${DIST_DIR}/klstream-paper-${VERSION}.tar.gz" 2>/dev/null || stat -c%s "${DIST_DIR}/klstream-paper-${VERSION}.tar.gz" 2>/dev/null || echo "0")

python3 -c "
import json
manifest = {
    'manifest_version': '1.0.0',
    'release_version': '${VERSION}',
    'packages': {
        'klstream-${VERSION}.tar.gz': {
            'type': 'source_distribution',
            'file_count': ${SRC_FILE_COUNT},
            'size_bytes': ${SRC_SIZE}
        },
        'klstream-paper-${VERSION}.tar.gz': {
            'type': 'paper_distribution',
            'file_count': ${PAPER_FILE_COUNT},
            'size_bytes': ${PAPER_SIZE}
        }
    },
    'sha256sums_file': 'dist/SHA256SUMS',
    'status': 'PACKAGED'
}
with open('results/release_packaging_manifest.json', 'w') as f:
    json.dump(manifest, f, indent=2)
print(json.dumps(manifest, indent=2))
"

# Clean up staging directories
rm -rf "${STAGING_SRC}" "${STAGING_PAPER}"

echo ""
echo "================================================================"
echo "  Release packaging completed successfully (PASS)"
echo "================================================================"
