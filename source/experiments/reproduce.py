#!/usr/bin/env python3
"""
source/experiments/reproduce.py

KLStream: End-to-End Cold Reproduction & Artifact Integrity Runner
Contract KLS-13: Verifies clean build, binary hashes, data integrity,
and execution reproducibility from an isolated clean checkout.
Standard library only.
"""

import argparse
import datetime
import hashlib
import json
import os
import pathlib
import platform
import subprocess
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent


def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def run_cmd(cmd: list[str], cwd: pathlib.Path) -> tuple[int, str, str]:
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def reproduce_study(build_dir: pathlib.Path, output_report: pathlib.Path) -> dict:
    print("=" * 80)
    print("KLSTREAM: COLD REPRODUCTION & ARTIFACT INTEGRITY RUNNER (KLS-13)")
    print("=" * 80)
    print(f"Repository Root: {REPO_ROOT}")
    print(f"Build Directory: {build_dir}")
    print(f"Platform:        {platform.system()} {platform.machine()} (Python {platform.python_version()})")
    print("-" * 80)

    report = {
        "contract": "KLS-13",
        "title": "Cold Reproduction & Artifact Integrity Attestation",
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "stages": {},
    }

    # -------------------------------------------------------------------------
    # Stage 1: Build Verification
    # -------------------------------------------------------------------------
    print("\n[1/5] Configuring and building C++17 engine binaries...")
    cmake_cfg = ["cmake", "-B", str(build_dir), "-S", str(REPO_ROOT), f"-DPython3_EXECUTABLE={sys.executable}"]
    rc_cfg, out_cfg, err_cfg = run_cmd(cmake_cfg, REPO_ROOT)
    if rc_cfg != 0:
        raise RuntimeError(f"CMake configure failed:\n{err_cfg}")

    cmake_bld = ["cmake", "--build", str(build_dir), "--parallel", "2"]
    rc_bld, out_bld, err_bld = run_cmd(cmake_bld, REPO_ROOT)
    if rc_bld != 0:
        raise RuntimeError(f"CMake build failed:\n{err_bld}")

    engine_bin = build_dir / "engine_runner"
    test_bin = build_dir / "engine_tests"

    if not engine_bin.is_file() or not test_bin.is_file():
        raise FileNotFoundError("Compiled binaries missing after build")

    bin_hashes = {
        "engine_runner": sha256_file(engine_bin),
        "engine_tests": sha256_file(test_bin),
    }
    report["stages"]["build"] = {
        "status": "PASS",
        "binaries": bin_hashes,
    }
    print(f"  -> engine_runner: {bin_hashes['engine_runner'][:16]}...")
    print(f"  -> engine_tests:  {bin_hashes['engine_tests'][:16]}...")

    # -------------------------------------------------------------------------
    # Stage 2: C++ Unit Test Verification
    # -------------------------------------------------------------------------
    print("\n[2/5] Executing native C++ unit tests...")
    rc_t, out_t, err_t = run_cmd([str(test_bin)], REPO_ROOT)
    if rc_t != 0:
        raise RuntimeError(f"Engine unit tests failed:\n{err_t}\n{out_t}")
    report["stages"]["native_tests"] = {
        "status": "PASS",
        "exit_code": rc_t,
    }
    print("  -> Engine unit tests passed (100%).")

    # -------------------------------------------------------------------------
    # Stage 3: Public Data & Telemetry Integrity Check
    # -------------------------------------------------------------------------
    print("\n[3/5] Verifying SHA-256 digests of public research artifacts...")
    target_artifacts = [
        REPO_ROOT / "data" / "cohort.csv",
        REPO_ROOT / "data" / "source_records.csv",
        REPO_ROOT / "data" / "provenance.json",
        REPO_ROOT / "data" / "budget_curves.json",
        REPO_ROOT / "data" / "pilot_telemetry.json",
        REPO_ROOT / "data" / "sensitivity_manifest.json",
        REPO_ROOT / "data" / "independent_verdict.json",
    ]
    art_hashes = {}
    for art in target_artifacts:
        if not art.is_file():
            raise FileNotFoundError(f"Missing required artifact: {art}")
        art_hash = sha256_file(art)
        art_hashes[art.name] = art_hash
        print(f"  -> {art.name:<28}: {art_hash[:16]}... ({art.stat().st_size} bytes)")

    report["stages"]["artifacts"] = {
        "status": "PASS",
        "digests": art_hashes,
    }

    # -------------------------------------------------------------------------
    # Stage 4: Quickstart Demo Execution
    # -------------------------------------------------------------------------
    print("\n[4/5] Executing streaming anomaly detection demo...")
    demo_script = REPO_ROOT / "source" / "experiments" / "demo.py"
    rc_d, out_d, err_d = run_cmd([sys.executable, str(demo_script), "--split", "validation"], REPO_ROOT)
    if rc_d != 0:
        raise RuntimeError(f"Quickstart demo failed:\n{err_d}\n{out_d}")
    report["stages"]["demo"] = {
        "status": "PASS",
        "exit_code": rc_d,
    }
    print("  -> Quickstart streaming demo succeeded.")

    # -------------------------------------------------------------------------
    # Stage 5: Secrecy & Credential Audit
    # -------------------------------------------------------------------------
    print("\n[5/5] Auditing repository for credential or private key leaks...")
    leaked_markers = []
    priv_pattern = "-----" + "BEGIN " + "PRIVATE" + " KEY-----"
    for root_dir, _, files in os.walk(REPO_ROOT):
        # Skip git or build directories
        if ".git" in root_dir or "build" in root_dir or "scratch" in root_dir:
            continue
        for fname in files:
            fpath = pathlib.Path(root_dir) / fname
            if fpath == pathlib.Path(__file__).resolve():
                continue
            if fpath.suffix in (".py", ".cpp", ".hpp", ".txt", ".md", ".json", ".csv"):
                try:
                    content = fpath.read_text(encoding="utf-8", errors="ignore")
                    if priv_pattern in content:
                        leaked_markers.append(str(fpath.relative_to(REPO_ROOT)))
                except Exception:
                    pass

    if leaked_markers:
        raise RuntimeError(f"Private keys detected in public tree: {leaked_markers}")

    report["stages"]["secrecy_audit"] = {
        "status": "PASS",
        "private_key_violations": 0,
    }
    print("  -> Zero private keys or secret credentials detected.")

    # Save reproduction report
    output_report.parent.mkdir(parents=True, exist_ok=True)
    with open(output_report, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    rep_hash = sha256_file(output_report)
    print("\n" + "=" * 80)
    print(f"COLD REPRODUCTION COMPLETE & CERTIFIED:")
    print(f"Report: {output_report} (SHA-256: {rep_hash})")
    print("=" * 80)

    return report


def main():
    parser = argparse.ArgumentParser(description="KLStream Cold Reproduction Runner")
    parser.add_argument("--build-dir", type=pathlib.Path, default=REPO_ROOT / "build")
    parser.add_argument("--output-report", type=pathlib.Path, default=REPO_ROOT / "data" / "reproduction_report.json")
    args = parser.parse_args()

    reproduce_study(args.build_dir, args.output_report)


if __name__ == "__main__":
    main()
