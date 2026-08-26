#!/usr/bin/env python3
"""
verify_tex_original.py — Original verifier that extracts verified citation count from compilation manifest.
"""
import json
from pathlib import Path

MANIFEST_PATH = Path("results/latex_compilation_manifest.json")

def main():
    with open(MANIFEST_PATH, "r") as f:
        data = json.load(f)
    print(json.dumps({"citations_verified_count": int(data["citations_verified_count"])}))

if __name__ == "__main__":
    main()
