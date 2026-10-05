"""Validation and regression test for data provenance and cohort manifests."""
from __future__ import annotations

import csv
import hashlib
import json
import pathlib
import unittest


class DataProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(__file__).resolve().parents[2]
        self.data_dir = self.root / "data"
        self.src_csv = self.data_dir / "source_records.csv"
        self.cohort_csv = self.data_dir / "cohort.csv"
        self.prov_json = self.data_dir / "provenance.json"
        self.req_lock = self.root / "source" / "requirements.lock"

    def _sha256(self, path: pathlib.Path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()

    def test_source_records_schema_and_integrity(self):
        self.assertTrue(self.src_csv.is_file(), "source_records.csv must exist")
        with open(self.src_csv, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        self.assertGreaterEqual(len(rows), 1, "source_records.csv must have at least one record")

        rec_ids = set()
        for r in rows:
            self.assertIn("record_id", r)
            self.assertIn("origin", r)
            self.assertIn("timestamp", r)
            self.assertIn("sha256", r)
            self.assertTrue(bool(r["record_id"].strip()))
            self.assertNotIn(r["record_id"], rec_ids, "duplicate record_id")
            rec_ids.add(r["record_id"])
            self.assertEqual(r["origin"], "observational")
            self.assertEqual(len(r["sha256"]), 64)

    def test_cohort_manifest_policy_compliance(self):
        self.assertTrue(self.cohort_csv.is_file(), "cohort.csv must exist")
        with open(self.cohort_csv, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        self.assertGreaterEqual(len(rows), 100, "cohort.csv must contain substantive records")

        sample_ids = set()
        group_splits = {}
        source_splits = {}

        train_ts, val_ts, test_ts = [], [], []

        for r in rows:
            sid = r["sample_id"]
            self.assertTrue(bool(sid.strip()))
            self.assertNotIn(sid, sample_ids, "duplicate sample_id in cohort")
            sample_ids.add(sid)

            self.assertIn(r["label"], ("0", "1"), "label must be 0 or 1")
            split = r["split"]
            self.assertIn(split, ("train", "validation", "test", "ood"))

            gid = r["group_id"]
            if gid in group_splits:
                self.assertEqual(group_splits[gid], split, f"group leakage for {gid}")
            else:
                group_splits[gid] = split

            for src in r["source_ids"].split("|"):
                if src in source_splits:
                    self.assertEqual(source_splits[src], split, f"source record leakage for {src}")
                else:
                    source_splits[src] = split

            t = int(r["timestamp"])
            if split == "train":
                train_ts.append(t)
            elif split == "validation":
                val_ts.append(t)
            elif split == "test":
                test_ts.append(t)

        # Statistical policy floors
        for split_name, sub in [("train", [r for r in rows if r["split"] == "train"]),
                                 ("validation", [r for r in rows if r["split"] == "validation"]),
                                 ("test", [r for r in rows if r["split"] == "test"])]:
            pos = sum(1 for r in sub if r["label"] == "1")
            neg = sum(1 for r in sub if r["label"] == "0")
            self.assertGreaterEqual(pos, 10, f"{split_name} positive class count < 10")
            self.assertGreaterEqual(neg, 10, f"{split_name} negative class count < 10")

        test_groups = {r["group_id"] for r in rows if r["split"] == "test"}
        self.assertGreaterEqual(len(test_groups), 30, "test split must have >= 30 independent groups")

        # Temporal ordering: max(train) < min(val) < min(test)
        self.assertLess(max(train_ts), min(val_ts), "train timestamp overlaps validation")
        self.assertLess(max(val_ts), min(test_ts), "validation timestamp overlaps test")

    def test_provenance_manifest_digests(self):
        self.assertTrue(self.prov_json.is_file(), "provenance.json must exist")
        with open(self.prov_json, "r", encoding="utf-8") as f:
            prov = json.load(f)

        self.assertIn("dataset_identifier", prov)
        self.assertTrue(prov["dataset_identifier"].startswith("http"))
        self.assertEqual(prov.get("provenance_basis"), "author_declared")
        self.assertIn("retrieval_date", prov)

        self.assertEqual(prov["source_records_sha256"], self._sha256(self.src_csv))
        self.assertEqual(prov["cohort_sha256"], self._sha256(self.cohort_csv))

    def test_requirements_lock(self):
        self.assertTrue(self.req_lock.is_file(), "requirements.lock must exist")
        text = self.req_lock.read_text(encoding="utf-8")
        self.assertIn("python==3.12", text)


if __name__ == "__main__":
    unittest.main()
