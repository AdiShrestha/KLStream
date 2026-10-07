# Troubleshooting & Platform Diagnostics

This guide provides diagnosis and remediation steps for common issues encountered during build, testing, and reproduction.

---

## 1. Compiler Support for C++20

### Issue: `error: unknown standard 'c++20'` or missing C++20 features
**Symptom:** CMake configuration or compilation fails with compiler flag errors.  
**Cause:** The default host compiler is older than GCC 11 or Clang 13.  
**Remediation:**
- On macOS: Ensure Xcode Command Line Tools are updated:
  ```bash
  xcode-select --install
  ```
- On Ubuntu/Debian Linux: Install modern GCC or Clang:
  ```bash
  sudo apt-get update && sudo apt-get install -y g++-12 clang-15 cmake
  export CXX=g++-12
  ```

---

## 2. CMake Build Directory Conflict

### Issue: CMake configuration fails with `CMakeCache.txt does not match`
**Symptom:**
```text
CMake Error: The source directory ... does not match the source directory used to generate cache
```
**Cause:** The repository was moved, or an existing build directory was created with different generator flags.  
**Remediation:** Remove the build directory and reconfigure cleanly:
```bash
rm -rf build build-sanitizers
cmake -B build -S . -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel 2
```

---

## 3. Test Failure Due to Missing Untracked Checkpoint

### Issue: Test skips or fails looking for `data/model_checkpoint.iforest`
**Symptom:** In a cold checkout without prebuilt models, tests report that the `.iforest` binary is not found.  
**Cause:** Binary `.iforest` checkpoints may be untracked or excluded by `.gitignore`.  
**Remediation:** All unit tests in `source/tests/` are designed with graceful fallbacks. If you wish to generate a fresh checkpoint from the raw cohort:
```bash
python3 source/experiments/runner.py \
    --cohort data/cohort.csv \
    --eval-splits train \
    --model-save data/model_checkpoint.iforest
```

---

## 4. High Latency Variance on macOS

### Issue: Observed tail latency $p99$ shows intermittent spikes
**Symptom:** Occasional runs show $p99$ latency spikes attributable to OS thread migration.  
**Cause:** macOS Grand Central Dispatch (GCD) dynamically moves threads between Efficiency and Performance cores when energy-saver or thermal throttling triggers.  
**Remediation:**
- Ensure the laptop is connected to external AC power.
- Close CPU-intensive background tasks during benchmark execution.
- Repeat runs across 5 independent PRNG seeds as demonstrated in `independent_verdict.py` to average out OS scheduling jitter.

---

## 5. Corrupted Artifact Hashes

### Issue: `reproduce.py` reports hash mismatch on public data artifacts
**Symptom:** Stage 3 of `reproduce.py` reports `FAILED` on `data/cohort.csv` or similar files.  
**Cause:** The data file was edited locally or line endings were converted (e.g. CRLF vs LF on Windows checkouts).  
**Remediation:** Ensure Git checks out files with standard LF line endings:
```bash
git config core.autocrlf false
git checkout -- data/
```
Verify the SHA-256 hashes against `data/source_records.csv` or `data/provenance.json`.
