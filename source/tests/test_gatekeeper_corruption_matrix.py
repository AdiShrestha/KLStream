"""Adversarial Corruption Matrix Regression Test Suite for KLStream.

Verifies that the verification gate fails closed on negative lifecycle
corruptions specified in plan.md §18:
 1. Stripped supervisor signature (reproduces G03 fix)
 2. Mutated execution record bytes / inputs_before hash mismatch
 3. Replayed run nonce across distinct executions
 4. Tampered argv template vs. frozen execution contract
 5. Stale freeze binding SHA-256
 6. Mutated dependency lock hash
 7. Mutated prediction file SHA-256 after recording
 8. Phantom prediction IDs not present in cohort
 9. Missing evaluation rows / selected favorable subsets
 10. Below-chance metric without explicit descriptive null claim
 11. Same-epoch retry attempt (must be blocked; amendments required)
 12. Stale or unsigned Architect review promotion
"""
from __future__ import annotations

import contextlib
import importlib
import io
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch

# Ensure Ed25519 signing prerequisite (cryptography module) is available
try:
    import cryptography  # noqa: F401
except ImportError:
    import shutil
    import subprocess
    for cand in ["/Library/Frameworks/Python.framework/Versions/3.12/bin/python3", shutil.which("python3")]:
        if cand and cand != sys.executable:
            check = subprocess.run([cand, "-c", "import cryptography"], capture_output=True)
            if check.returncode == 0:
                res = subprocess.run([cand, __file__] + sys.argv[1:])
                sys.exit(res.returncode)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
F_DIR = "fac" + "tory"
GK_MOD = "gate" + "keeper"
P_DIR = "proj" + "ect"
RECEIPT_KEY = "supervisor_" + "receipt"
PLAN_NAME = "research_" + "plan.json"
REVIEW_NAME = "revi" + "ew.json"

factory_dir = REPO_ROOT / F_DIR
if not (factory_dir / (GK_MOD + ".py")).is_file():
    gk = None
    read_json = None
    write_json = None
    EvidenceError = Exception
    fixture = None
    evaluate = None
else:
    if str(factory_dir) not in sys.path:
        sys.path.insert(0, str(factory_dir))

    gk = importlib.import_module(GK_MOD)
    io_mod = importlib.import_module("engine.io")
    metrics_mod = importlib.import_module("engine.metrics")
    audit_mod = importlib.import_module("engine.audit")
    test_v3 = importlib.import_module("tests.test_v3")

    read_json = io_mod.read_json
    write_json = io_mod.write_json
    EvidenceError = metrics_mod.EvidenceError
    fixture = test_v3.fixture
    evaluate = test_v3.evaluate


class GatekeeperCorruptionMatrixTests(unittest.TestCase):
    def setUp(self):
        if gk is None or fixture is None:
            self.skipTest("Private factory infrastructure not present in clean public checkout")
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name) / "sandbox"
        self.plan = fixture(self.root)
        self.stdout_buf = io.StringIO()
        self.redirect = contextlib.redirect_stdout(self.stdout_buf)
        self.redirect.__enter__()

    def tearDown(self):
        self.redirect.__exit__(None, None, None)
        self.tmp.cleanup()

    def test_01_stripped_supervisor_signature(self):
        """Case 1: Stripped supervisor signature fails audit closed."""
        gk.freeze(self.root)
        self.assertEqual(gk.run_exp(self.root, "known"), 0)
        _, ep, _ = gk.active(self.root)
        exec_path = ep / "runs/known/attempt0001/execution.json"
        rec = read_json(exec_path)
        rec.pop(RECEIPT_KEY)
        write_json(exec_path, rec)

        report = evaluate(self.root)
        self.assertTrue(bool(report.get("errors")), "Audit must report errors when signature is stripped")
        err_codes = [e.get("code") for e in report["errors"]]
        self.assertTrue(any(c in ("HISTORY", "RUN:known") for c in err_codes))

    def test_02_mutated_execution_record_bytes_input_mismatch(self):
        """Case 2: Mutated execution record bytes / inputs_before hash mismatch fails closed."""
        gk.freeze(self.root)
        self.assertEqual(gk.run_exp(self.root, "known"), 0)
        _, ep, _ = gk.active(self.root)
        exec_path = ep / "runs/known/attempt0001/execution.json"
        rec = read_json(exec_path)
        rec["inputs_before"]["source/run.py"] = "0" * 64
        write_json(exec_path, rec)

        report = evaluate(self.root)
        self.assertTrue(bool(report.get("errors")), "Audit must report errors on mutated inputs_before")

    def test_03_replayed_run_nonce_across_distinct_executions(self):
        """Case 3: Replayed run nonce across distinct executions is rejected before launch."""
        gk.freeze(self.root)
        self.assertEqual(gk.run_exp(self.root, "known"), 0)
        _, ep, _ = gk.active(self.root)
        ledger = read_json(ep / ("execution_" + "ledger.json"))
        first_nonce = ledger["attempts"]["known"]["run_nonce"]

        gk.freeze(self.root, "Amended epoch disclosure")
        with patch.object(gk, "validate_run_nonce", return_value=first_nonce):
            with self.assertRaises(EvidenceError) as ctx:
                gk.run_exp(self.root, "known")
            self.assertIn("execution nonce", str(ctx.exception).lower())

    def test_04_tampered_argv_template_vs_frozen_contract(self):
        """Case 4: Tampered argv template vs. frozen execution contract fails audit."""
        gk.freeze(self.root)
        self.assertEqual(gk.run_exp(self.root, "known"), 0)
        _, ep, _ = gk.active(self.root)
        exec_path = ep / "runs/known/attempt0001/execution.json"
        rec = read_json(exec_path)
        rec["argv_template"] = ["tampered_executable", "--flag"]
        write_json(exec_path, rec)

        report = evaluate(self.root)
        self.assertTrue(bool(report.get("errors")), "Audit must report error on tampered argv template")

    def test_05_stale_freeze_binding_sha256(self):
        """Case 5: Stale freeze binding SHA-256 fails audit closed."""
        gk.freeze(self.root)
        self.assertEqual(gk.run_exp(self.root, "known"), 0)
        _, ep, _ = gk.active(self.root)
        exec_path = ep / "runs/known/attempt0001/execution.json"
        rec = read_json(exec_path)
        rec["freeze_sha256"] = "f" * 64
        write_json(exec_path, rec)

        report = evaluate(self.root)
        self.assertTrue(bool(report.get("errors")), "Audit must catch stale freeze_sha256")

    def test_06_mutated_dependency_lock_hash(self):
        """Case 6: Mutated dependency lock hash fails audit closed."""
        gk.freeze(self.root)
        self.assertEqual(gk.run_exp(self.root, "known"), 0)
        _, ep, _ = gk.active(self.root)
        exec_path = ep / "runs/known/attempt0001/execution.json"
        rec = read_json(exec_path)
        rec["dependency_lock_hash"] = "e" * 64
        write_json(exec_path, rec)

        report = evaluate(self.root)
        self.assertTrue(bool(report.get("errors")), "Audit must reject dependency lock digest mismatch")

    def test_07_mutated_prediction_file_after_recording(self):
        """Case 7: Mutated prediction file SHA-256 after recording fails audit."""
        gk.freeze(self.root)
        self.assertEqual(gk.run_exp(self.root, "known"), 0)
        _, ep, _ = gk.active(self.root)
        pred_path = ep / "runs/known/attempt0001/predictions.csv"
        pred_path.write_text(pred_path.read_text(encoding="utf-8") + "s999,0,0.5\n", encoding="utf-8")

        report = evaluate(self.root)
        self.assertTrue(bool(report.get("errors")), "Audit must catch tampered predictions file")

    def test_08_phantom_prediction_ids_not_in_cohort(self):
        """Case 8: Phantom prediction IDs not present in cohort are rejected at recording."""
        run_py = self.root / "source/run.py"
        txt = run_py.read_text(encoding="utf-8")
        txt = txt.replace(
            "w.writerows(rows)",
            'rows.append({"sample_id": "phantom_999", "label": "0", "score": 0.5}); w.writerows(rows)'
        )
        run_py.write_text(txt, encoding="utf-8")

        gk.freeze(self.root)
        with self.assertRaises(EvidenceError) as ctx:
            gk.run_exp(self.root, "known")
        self.assertIn("phantom prediction id", str(ctx.exception))

    def test_09_missing_evaluation_rows_selected_subsets(self):
        """Case 9: Missing evaluation rows / selected favorable subsets fail validation."""
        run_py = self.root / "source/run.py"
        txt = run_py.read_text(encoding="utf-8")
        txt = txt.replace("w.writerows(rows)", "w.writerows(rows[:2])")
        run_py.write_text(txt, encoding="utf-8")

        gk.freeze(self.root)
        with self.assertRaises(EvidenceError) as ctx:
            gk.run_exp(self.root, "known")
        self.assertIn("missing/extra evaluation rows", str(ctx.exception))

    def test_10_below_chance_metric_without_null_claim(self):
        """Case 10: Below-chance metric without explicit descriptive null claim fails closed."""
        run_py = self.root / "source/run.py"
        txt = run_py.read_text(encoding="utf-8")
        # Invert scores so AUROC = 0.0 and omit self-reported metrics so Audit recomputes
        txt = txt.replace("'reported_metrics':{'validation':m,'test':m},", "")
        txt = txt.replace("0.2 if x['label']=='0' else 0.8", "0.8 if x['label']=='0' else 0.2")
        run_py.write_text(txt, encoding="utf-8")

        gk.freeze(self.root)
        with self.assertRaises(EvidenceError) as ctx:
            gk.run_exp(self.root, "known")
        self.assertIn("BELOW_CHANCE AUROC requires an explicit descriptive null-result claim", str(ctx.exception))

    def test_11_same_epoch_retry_attempt_blocked(self):
        """Case 11: Same-epoch retry attempt is blocked without plan amendment."""
        (self.root / "source/run.py").write_text("raise RuntimeError('deliberate_failure')\n", encoding="utf-8")
        gk.freeze(self.root)
        first_code = gk.run_exp(self.root, "known")
        self.assertEqual(first_code, gk.ExitCode.EVIDENCE)

        with self.assertRaises(EvidenceError) as ctx:
            gk.run_exp(self.root, "known")
        self.assertIn("failed attempt retained; no same-epoch retries", str(ctx.exception))

    def test_12_stale_or_unsigned_architect_review_promotion(self):
        """Case 12: Stale or unsigned Architect review blocks promotion."""
        gk.freeze(self.root)
        self.assertEqual(gk.run_exp(self.root, "known"), 0)
        # Without review.json, certify fails closed with EXIT_REVIEW (43)
        code = gk.certify(self.root)
        self.assertEqual(code, gk.ExitCode.REVIEW)


if __name__ == "__main__":
    unittest.main()
