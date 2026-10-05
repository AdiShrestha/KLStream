#!/usr/bin/env python3
"""Authentic Market Data Acquisition and Preprocessing for KLStream.

Ingests public, verifiable tick trade streams from the Binance Public Data Archive
(https://data.binance.vision/data/spot/daily/trades/BTCUSDT/).
Verifies cryptographic SHA-256 checksums published by the provider.
Generates:
  - data/source_records.csv: Raw captured input digests.
  - data/cohort.csv: Canonical dataset split temporally without leakage.
  - data/provenance.json: Cryptographic provenance manifest.

Standard library only. No synthetic fallbacks or mock data generation (F01).
"""
from __future__ import annotations

import csv
import datetime
import hashlib
import io
import json
import os
import pathlib
import sys
import urllib.request
import zipfile


DAYS = [
    ("2017-08-17", "train", "rec_20170817"),
    ("2017-08-18", "validation", "rec_20170818"),
    ("2017-08-19", "test", "rec_20170819"),
]

BASE_URL = "https://data.binance.vision/data/spot/daily/trades/BTCUSDT"
WINDOW_MS = 30 * 60 * 1000  # 30-minute independent evaluation windows
ANOMALY_QUOTE_CUTOFF = 4500.0  # Large block order value threshold established from training set


def compute_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def compute_file_sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def acquire_raw_file(day: str, raw_dir: pathlib.Path) -> tuple[pathlib.Path, str]:
    """Download raw daily trade zip and verify provider checksum."""
    zip_name = f"BTCUSDT-trades-{day}.zip"
    chk_name = f"BTCUSDT-trades-{day}.zip.CHECKSUM"
    zip_path = raw_dir / zip_name
    chk_path = raw_dir / chk_name

    zip_url = f"{BASE_URL}/{zip_name}"
    chk_url = f"{BASE_URL}/{chk_name}"

    # Fetch provider checksum
    req_chk = urllib.request.Request(chk_url, headers={"User-Agent": "KLStream-Research/1.0"})
    with urllib.request.urlopen(req_chk, timeout=30) as resp:
        chk_text = resp.read().decode("utf-8").strip()
    expected_sha = chk_text.split()[0]
    chk_path.write_text(chk_text + "\n", encoding="utf-8")

    # Fetch or verify zip bytes
    if zip_path.is_file():
        existing_sha = compute_file_sha256(zip_path)
        if existing_sha == expected_sha:
            return zip_path, expected_sha

    req_zip = urllib.request.Request(zip_url, headers={"User-Agent": "KLStream-Research/1.0"})
    with urllib.request.urlopen(req_zip, timeout=60) as resp:
        zip_bytes = resp.read()

    actual_sha = compute_sha256(zip_bytes)
    if actual_sha != expected_sha:
        raise ValueError(f"Provider checksum mismatch for {zip_name}: expected {expected_sha}, got {actual_sha}")

    zip_path.write_bytes(zip_bytes)
    return zip_path, expected_sha


def process_dataset(project_root: pathlib.Path) -> dict:
    data_dir = project_root / "data"
    raw_dir = data_dir / "raw"
    data_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)

    source_records = []
    cohort_records = []
    raw_records_info = {}

    for day, split, rec_id in DAYS:
        print(f"Acquiring and verifying raw market trace for {day} ({split})...")
        zip_path, sha_digest = acquire_raw_file(day, raw_dir)

        # Day epoch start timestamp
        day_date = datetime.date.fromisoformat(day)
        day_epoch_ms = int(datetime.datetime(day_date.year, day_date.month, day_date.day, tzinfo=datetime.timezone.utc).timestamp() * 1000)

        source_records.append({
            "record_id": rec_id,
            "origin": "observational",
            "timestamp": str(day_epoch_ms),
            "sha256": sha_digest,
        })

        raw_records_info[rec_id] = {
            "filename": zip_path.name,
            "url": f"{BASE_URL}/{zip_path.name}",
            "sha256": sha_digest,
            "provider_checksum_verified": True,
            "date": day,
            "split": split,
        }

        # Parse CSV inside ZIP
        with zipfile.ZipFile(zip_path) as z:
            csv_name = z.namelist()[0]
            with z.open(csv_name) as f:
                reader = csv.reader(io.TextIOWrapper(f, encoding="utf-8"))
                prev_time = None
                for row in reader:
                    if not row or len(row) < 6:
                        continue
                    # Format: id, price, qty, quote_qty, time, is_buyer_maker, is_best_match
                    trade_id = row[0].strip()
                    price = float(row[1])
                    qty = float(row[2])
                    quote_qty = float(row[3])
                    t_ms = int(row[4])
                    is_buyer_maker = 1.0 if row[5].strip().lower() == "true" else 0.0

                    interarrival_ms = float(t_ms - prev_time) if prev_time is not None else 0.0
                    prev_time = t_ms

                    # Window index (30 min blocks)
                    w_idx = (t_ms % 86400000) // WINDOW_MS
                    group_id = f"g_{day.replace('-', '')}_w{w_idx:02d}"

                    # Anomaly ground truth: large block trade in volume/value
                    label = "1" if quote_qty >= ANOMALY_QUOTE_CUTOFF else "0"
                    sample_id = f"t_{day.replace('-', '')}_{int(trade_id):07d}"

                    cohort_records.append({
                        "sample_id": sample_id,
                        "label": label,
                        "group_id": group_id,
                        "split": split,
                        "source_ids": rec_id,
                        "timestamp": str(t_ms),
                        "price": f"{price:.2f}",
                        "qty": f"{qty:.8f}",
                        "quote_qty": f"{quote_qty:.8f}",
                        "is_buyer_maker": f"{is_buyer_maker:.1f}",
                        "interarrival_ms": f"{interarrival_ms:.1f}",
                    })

    # Sort cohort strictly by timestamp
    cohort_records.sort(key=lambda r: int(r["timestamp"]))

    # 1. Write data/source_records.csv
    src_csv_path = data_dir / "source_records.csv"
    with open(src_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["record_id", "origin", "timestamp", "sha256"])
        writer.writeheader()
        writer.writerows(source_records)
    src_sha = compute_file_sha256(src_csv_path)

    # 2. Write data/cohort.csv
    cohort_csv_path = data_dir / "cohort.csv"
    fieldnames = [
        "sample_id", "label", "group_id", "split", "source_ids",
        "timestamp", "price", "qty", "quote_qty", "is_buyer_maker", "interarrival_ms"
    ]
    with open(cohort_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(cohort_records)
    cohort_sha = compute_file_sha256(cohort_csv_path)

    # 3. Write data/provenance.json
    provenance = {
        "dataset_identifier": f"{BASE_URL}/",
        "retrieval_date": datetime.date.today().isoformat(),
        "license": "CC-BY-4.0",
        "source_records_sha256": src_sha,
        "cohort_sha256": cohort_sha,
        "provenance_basis": "author_declared",
        "raw_records": raw_records_info,
    }
    prov_path = data_dir / "provenance.json"
    with open(prov_path, "w", encoding="utf-8") as f:
        json.dump(provenance, f, indent=2)

    # Self-validation
    train_rows = [r for r in cohort_records if r["split"] == "train"]
    val_rows = [r for r in cohort_records if r["split"] == "validation"]
    test_rows = [r for r in cohort_records if r["split"] == "test"]

    test_groups = {r["group_id"] for r in test_rows}
    if len(test_groups) < 30:
        raise ValueError(f"Insufficient test groups: {len(test_groups)} < 30")

    for split_name, subset in [("train", train_rows), ("validation", val_rows), ("test", test_rows)]:
        pos = sum(1 for r in subset if r["label"] == "1")
        neg = sum(1 for r in subset if r["label"] == "0")
        if pos < 10 or neg < 10:
            raise ValueError(f"Class count floor violation in {split_name}: pos={pos}, neg={neg}")

    max_train_t = max(int(r["timestamp"]) for r in train_rows)
    min_val_t = min(int(r["timestamp"]) for r in val_rows)
    max_val_t = max(int(r["timestamp"]) for r in val_rows)
    min_test_t = min(int(r["timestamp"]) for r in test_rows)

    if not (max_train_t < min_val_t < max_val_t < min_test_t):
        raise ValueError("Temporal order invariant violated across train/validation/test partitions")

    summary = {
        "total_events": len(cohort_records),
        "train_events": len(train_rows),
        "val_events": len(val_rows),
        "test_events": len(test_rows),
        "test_groups": len(test_groups),
        "source_records_sha256": src_sha,
        "cohort_sha256": cohort_sha,
        "provenance_path": str(prov_path.relative_to(project_root)),
    }
    print("Dataset ingestion and verification successful:")
    print(json.dumps(summary, indent=2))
    return summary


def main():
    root = pathlib.Path.cwd().resolve()
    for parent in [root] + list(root.parents):
        if (parent / "CMakeLists.txt").is_file() and (parent / "source").is_dir():
            root = parent
            break
    process_dataset(root)


if __name__ == "__main__":
    main()
