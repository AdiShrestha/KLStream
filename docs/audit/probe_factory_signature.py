#!/usr/bin/env python3
"""Audit fixture only: demonstrate unsigned acceptance in supplied factory 3.3.0.
Run: PYTHONDONTWRITEBYTECODE=1 python3 docs/audit/probe_factory_signature.py OUTPUT.json
Never use this fixture as research evidence or a release certificate.
"""
import contextlib
import io
import json
import os
import sys
import tempfile
from pathlib import Path

factory = Path(__file__).resolve().parents[2] / 'factory'
sys.path.insert(0, str(factory))
with tempfile.TemporaryDirectory(prefix='klstream-signature-counterexample-') as tmp:
    root = Path(tmp)
    os.environ['FACTORY_SUPERVISOR_KEY'] = str(root / 'private' / 'supervisor.key')
    import gatekeeper as gate
    from tests.test_v3 import fixture, evaluate
    from engine.io import read_json, write_json
    project = root / 'fixture'; project.mkdir()
    with contextlib.redirect_stdout(io.StringIO()):
        fixture(project); gate.freeze(project); gate.run_exp(project, 'known')
        before = evaluate(project)
        _, epoch, _ = gate.active(project)
        execution = epoch / 'runs/known/attempt0001/execution.json'
        record = read_json(execution)
        had_signature = 'supervisor_receipt' in record
        record.pop('supervisor_receipt', None); write_json(execution, record)
        after = evaluate(project)
    result = {'purpose': 'Audit fixture, not research evidence', 'signature_present_before': had_signature,
              'before_errors': before['errors'], 'after_errors': after['errors'],
              'assurance_after_removal': gate._compute_assurance_level(after)}
Path(sys.argv[1]).write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
