#!/usr/bin/env python3
"""
verify_plan_original.py — Original verifier that counts planned sections in paper_plan.md.
"""
import json
from pathlib import Path

PLAN_PATH = Path("paper/paper_plan.md")

def main():
    content = PLAN_PATH.read_text()
    sections = [line for line in content.splitlines() if line.startswith("### Section")]
    print(json.dumps({"planned_sections_count": len(sections)}))

if __name__ == "__main__":
    main()
