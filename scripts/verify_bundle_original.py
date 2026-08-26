#!/usr/bin/env python3
"""verify_bundle_original.py — Extract verified file count from reproduction bundle receipt."""
import json
def main():
    with open("results/reproduction_bundle_receipt.json") as f:
        data = json.load(f)
    print(json.dumps({"extracted_file_count": int(data["extracted_file_count"])}))
if __name__ == "__main__":
    main()
