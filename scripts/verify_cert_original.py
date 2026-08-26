#!/usr/bin/env python3
"""verify_cert_original.py — Extract contract count from certification summary."""
import json
def main():
    with open("results/release_certification_summary.json") as f:
        data = json.load(f)
    print(json.dumps({"total_contracts_examined": int(data["total_contracts_examined"])}))
if __name__ == "__main__":
    main()
