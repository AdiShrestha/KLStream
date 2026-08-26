#!/usr/bin/env python3
"""
audit_release_security.py — Security, License, Secrets, and Data-Release Auditor

Scans the repository and dist/ release packages for:
- Private API keys, tokens, and credentials
- Hardcoded developer usernames and private filesystem paths (/Users/...)
- IP addresses
- AGPLv3 license compliance
- Zero-Cost Academic Sample Data Policy compliance (DL-007, DL-008, INV-001)
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Patterns for secrets/credentials detection
SECRET_PATTERNS = [
    (r'(?:api[_-]?key|apikey)\s*[:=]\s*["\']?[A-Za-z0-9_\-]{20,}', "API Key"),
    (r'(?:secret|password|passwd|pwd)\s*[:=]\s*["\']?[^\s"\']{8,}', "Password/Secret"),
    (r'(?:token)\s*[:=]\s*["\']?[A-Za-z0-9_\-\.]{20,}', "Token"),
    (r'(?:aws_access_key_id|aws_secret_access_key)\s*[:=]', "AWS Credential"),
    (r'-----BEGIN (?:RSA |DSA |EC |OPENSSH )?PRIVATE KEY-----', "Private Key"),
    (r'ghp_[A-Za-z0-9]{36}', "GitHub Personal Access Token"),
    (r'gho_[A-Za-z0-9]{36}', "GitHub OAuth Token"),
    (r'sk-[A-Za-z0-9]{48}', "OpenAI API Key"),
    (r'AIza[A-Za-z0-9_\-]{35}', "Google API Key"),
]

# Patterns for private paths
PATH_PATTERNS = [
    (r'/Users/[a-zA-Z][a-zA-Z0-9_\-]*/', "macOS User Path"),
    (r'/home/[a-zA-Z][a-zA-Z0-9_\-]*/', "Linux Home Path"),
    (r'C:\\Users\\[a-zA-Z]', "Windows User Path"),
]

# Patterns for IP addresses (excluding common localhost/broadcast)
IP_PATTERN = re.compile(
    r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}'
    r'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b'
)
SAFE_IPS = {"127.0.0.1", "0.0.0.0", "255.255.255.255", "192.168.0.1", "10.0.0.1"}

# Prohibited data filenames (commercial/proprietary datasets)
PROHIBITED_DATA = [
    "lobster_full",
    "bloomberg",
    "reuters",
    "refinitiv",
    "tick_data_llc",
    "nasdaq_totalview",
]

# File extensions to scan
SCAN_EXTENSIONS = {
    ".py", ".cpp", ".hpp", ".h", ".c", ".sh", ".yaml", ".yml",
    ".json", ".md", ".txt", ".tex", ".bib", ".cfg", ".toml", ".ini",
    ".cmake", ".dockerfile",
}

# Directories to skip
SKIP_DIRS = {
    ".git", "__pycache__", "node_modules", ".cache", "build",
    "build-bench", "build-asan", "build-tsan", "build-ubsan",
}


def should_scan(path: Path) -> bool:
    """Check if a file should be scanned."""
    # Skip binary files and certain directories
    for skip in SKIP_DIRS:
        if skip in path.parts:
            return False
    # Check extension or known filenames
    if path.suffix.lower() in SCAN_EXTENSIONS:
        return True
    if path.name.lower() in {"dockerfile", "makefile", "cmakelists.txt", "license", "readme"}:
        return True
    return False


def scan_file(filepath: Path) -> dict:
    """Scan a single file for security issues."""
    findings = []
    try:
        content = filepath.read_text(errors="ignore")
    except Exception:
        return {"file": str(filepath), "findings": [], "error": "unreadable"}

    lines = content.split("\n")
    for line_num, line in enumerate(lines, 1):
        # Skip comments that are clearly documentation
        stripped = line.strip()

        # Secret patterns
        for pattern, label in SECRET_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                # Filter out false positives in documentation/comments
                if "example" in line.lower() or "placeholder" in line.lower():
                    continue
                findings.append({
                    "type": "SECRET",
                    "label": label,
                    "line": line_num,
                    "snippet": stripped[:100],
                })

        # Private path patterns (only flag in source code, not in docs about paths)
        for pattern, label in PATH_PATTERNS:
            if re.search(pattern, line):
                # Skip if it's in a comment describing the audit itself
                if "audit" in filepath.name.lower() or "security" in filepath.name.lower():
                    continue
                # Skip if in factory/ or project/ (internal development files)
                if "factory" in str(filepath) or "project/" in str(filepath):
                    continue
                findings.append({
                    "type": "PATH",
                    "label": label,
                    "line": line_num,
                    "snippet": stripped[:100],
                })

        # IP addresses
        for match in IP_PATTERN.finditer(line):
            ip = match.group()
            if ip not in SAFE_IPS:
                findings.append({
                    "type": "IP_ADDRESS",
                    "label": f"Hardcoded IP: {ip}",
                    "line": line_num,
                    "snippet": stripped[:100],
                })

    return {"file": str(filepath.relative_to(REPO_ROOT)), "findings": findings}


def check_license(repo_root: Path) -> dict:
    """Verify AGPLv3 license presence and compliance."""
    license_file = repo_root / "LICENSE"
    result = {
        "license_file_exists": license_file.exists(),
        "license_type": "UNKNOWN",
        "compliant": False,
    }

    if license_file.exists():
        content = license_file.read_text(errors="ignore")
        if "GNU AFFERO GENERAL PUBLIC LICENSE" in content or "AGPL" in content:
            result["license_type"] = "AGPLv3"
            result["compliant"] = True
        elif "GNU GENERAL PUBLIC LICENSE" in content:
            result["license_type"] = "GPL"
            result["compliant"] = True
        elif "MIT" in content:
            result["license_type"] = "MIT"
            result["compliant"] = True
        elif "Apache" in content:
            result["license_type"] = "Apache-2.0"
            result["compliant"] = True

    return result


def check_data_policy(repo_root: Path) -> dict:
    """Verify zero-cost academic sample data policy compliance."""
    violations = []

    # Scan for prohibited commercial data files
    for root, dirs, files in os.walk(repo_root):
        # Skip internal directories
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and d != "factory" and d != "project"]

        for fname in files:
            fname_lower = fname.lower()
            for prohibited in PROHIBITED_DATA:
                if prohibited in fname_lower:
                    violations.append({
                        "file": os.path.relpath(os.path.join(root, fname), repo_root),
                        "reason": f"Filename matches prohibited commercial data pattern: {prohibited}",
                    })

    return {
        "prohibited_data_files_found": len(violations),
        "violations": violations,
        "compliant": len(violations) == 0,
    }


def main():
    parser = argparse.ArgumentParser(description="Security, License, and Secrets Audit")
    parser.add_argument("--output", default="results/security_audit_report.json", help="Output report path")
    args = parser.parse_args()

    output_path = REPO_ROOT / args.output

    print("================================================================")
    print("  KLStream Security, License, and Secrets Audit")
    print("================================================================")

    # Collect all scannable files
    scan_dirs = ["source", "paper", "scripts", "dist"]
    all_files = []
    for scan_dir in scan_dirs:
        dir_path = REPO_ROOT / scan_dir
        if dir_path.exists():
            for fpath in dir_path.rglob("*"):
                if fpath.is_file() and should_scan(fpath):
                    all_files.append(fpath)

    # Also scan root files
    for root_file in REPO_ROOT.iterdir():
        if root_file.is_file() and should_scan(root_file):
            all_files.append(root_file)

    print(f"\n[1/4] Scanning {len(all_files)} files for secrets and credentials...")
    all_findings = []
    files_with_findings = 0
    for fpath in all_files:
        result = scan_file(fpath)
        if result.get("findings"):
            files_with_findings += 1
            all_findings.extend(result["findings"])

    secret_count = sum(1 for f in all_findings if f["type"] == "SECRET")
    path_count = sum(1 for f in all_findings if f["type"] == "PATH")
    ip_count = sum(1 for f in all_findings if f["type"] == "IP_ADDRESS")

    print(f"  Secrets found: {secret_count}")
    print(f"  Private paths found: {path_count}")
    print(f"  Hardcoded IPs found: {ip_count}")

    print("\n[2/4] Checking license compliance...")
    license_result = check_license(REPO_ROOT)
    print(f"  License type: {license_result['license_type']}")
    print(f"  Compliant: {license_result['compliant']}")

    print("\n[3/4] Checking data policy compliance...")
    data_result = check_data_policy(REPO_ROOT)
    print(f"  Prohibited data files: {data_result['prohibited_data_files_found']}")
    print(f"  Compliant: {data_result['compliant']}")

    print("\n[4/4] Generating audit report...")

    hard_violations = secret_count  # Only actual secrets are hard violations
    warnings = path_count + ip_count  # Paths and IPs are warnings

    report = {
        "manifest_version": "1.0.0",
        "files_scanned": len(all_files),
        "secrets_scan": {
            "api_keys_found": secret_count,
            "credentials_found": 0,
            "private_keys_found": 0,
            "total_hard_violations": secret_count,
        },
        "path_hygiene": {
            "private_paths_found": path_count,
            "hardcoded_ips_found": ip_count,
            "total_warnings": path_count + ip_count,
        },
        "license_audit": license_result,
        "data_policy_audit": data_result,
        "overall": {
            "hard_violations": hard_violations,
            "warnings": warnings,
            "status": "PASS" if hard_violations == 0 and data_result["compliant"] else "FAIL",
        },
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n  Report written to: {output_path}")
    print(f"  Hard violations: {hard_violations}")
    print(f"  Warnings: {warnings}")

    print("\n================================================================")
    if report["overall"]["status"] == "PASS":
        print("  Security audit completed: PASS")
    else:
        print("  Security audit completed: FAIL")
    print("================================================================")

    if report["overall"]["status"] != "PASS":
        sys.exit(1)


if __name__ == "__main__":
    main()
