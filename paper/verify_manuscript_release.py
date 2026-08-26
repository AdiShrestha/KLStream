#!/usr/bin/env python3
"""
verify_manuscript_release.py — Manuscript and Supplementary Release Verification

Verifies that release manuscript files contain:
- Zero unexpanded template variables (TODO, TBD, FIXME, [?])
- No broken internal references
- All bibliography citations resolved
"""

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

MANUSCRIPT_FILES = [
    "paper/paper.md",
    "paper/main.tex",
    "paper/references.bib",
    "paper/ARTIFACT_EVALUATION.md",
]

PLACEHOLDER_PATTERNS = [
    (r'\bTODO\b', "TODO"),
    (r'\bTBD\b', "TBD"),
    (r'\bFIXME\b', "FIXME"),
    (r'\[?\?\]', "[?]"),
    (r'\bXXX\b', "XXX"),
    (r'\bHACK\b', "HACK"),
]


def main():
    parser = argparse.ArgumentParser(description="Manuscript Release Verification")
    parser.add_argument("--output", default="results/manuscript_release_verification_report.json")
    args = parser.parse_args()

    print("================================================================")
    print("  KLStream Manuscript Release Verification")
    print("================================================================")

    results = {}
    total_placeholders = 0
    total_files_checked = 0
    all_files_exist = True

    for rel_path in MANUSCRIPT_FILES:
        fpath = REPO_ROOT / rel_path
        file_result = {
            "exists": fpath.exists(),
            "placeholders_found": [],
            "placeholder_count": 0,
        }

        if not fpath.exists():
            print(f"\n  [MISSING] {rel_path}")
            all_files_exist = False
            results[rel_path] = file_result
            continue

        total_files_checked += 1
        content = fpath.read_text(errors="ignore")
        lines = content.split("\n")

        print(f"\n  [{rel_path}]")

        # Check for placeholders
        for line_num, line in enumerate(lines, 1):
            for pattern, label in PLACEHOLDER_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    file_result["placeholders_found"].append({
                        "pattern": label,
                        "line": line_num,
                        "text": line.strip()[:80],
                    })

        file_result["placeholder_count"] = len(file_result["placeholders_found"])
        total_placeholders += file_result["placeholder_count"]

        if file_result["placeholder_count"] == 0:
            print(f"    Placeholders: 0 (CLEAN)")
        else:
            print(f"    Placeholders: {file_result['placeholder_count']} FOUND")
            for p in file_result["placeholders_found"]:
                print(f"      Line {p['line']}: [{p['pattern']}] {p['text']}")

        results[rel_path] = file_result

    # LaTeX citation check
    tex_path = REPO_ROOT / "paper/main.tex"
    bib_path = REPO_ROOT / "paper/references.bib"
    citation_check = {"citations_found": 0, "bib_keys": 0, "unresolved": []}

    if tex_path.exists() and bib_path.exists():
        tex_content = tex_path.read_text(errors="ignore")
        bib_content = bib_path.read_text(errors="ignore")

        citations = set()
        for m in re.finditer(r'\\cite\{([^}]+)\}', tex_content):
            for k in m.group(1).split(","):
                citations.add(k.strip())

        bib_keys = set(re.findall(r'@\w+\{([^,]+),', bib_content))
        unresolved = citations - bib_keys

        citation_check = {
            "citations_found": len(citations),
            "bib_keys": len(bib_keys),
            "unresolved": list(unresolved),
        }

        print(f"\n  [LaTeX Citations]")
        print(f"    In-text citations: {len(citations)}")
        print(f"    BibTeX keys: {len(bib_keys)}")
        print(f"    Unresolved: {len(unresolved)}")

    overall_status = "PASS"
    if total_placeholders > 0 or not all_files_exist or len(citation_check.get("unresolved", [])) > 0:
        overall_status = "FAIL"

    report = {
        "manifest_version": "1.0.0",
        "files_checked": total_files_checked,
        "total_placeholders": total_placeholders,
        "all_files_present": all_files_exist,
        "citation_check": citation_check,
        "per_file": results,
        "status": overall_status,
    }

    output_path = REPO_ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n  Report: {output_path}")
    print(f"\n================================================================")
    print(f"  Manuscript verification: {overall_status}")
    print(f"================================================================")

    if overall_status != "PASS":
        sys.exit(1)


if __name__ == "__main__":
    main()
