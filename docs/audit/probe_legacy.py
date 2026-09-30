#!/usr/bin/env python3
"""Reproduce specific legacy defects using isolated fixtures; never research results."""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import sys
import tempfile
from pathlib import Path

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

def main():
    legacy = Path(sys.argv[1]).resolve()
    factory = Path(__file__).resolve().parents[2] / 'factory'
    sys.path.insert(0, str(legacy / 'source/experiments'))
    download = module('legacy_download', legacy / 'source/experiments/preprocessing/download_sample.py')
    metrics = module('legacy_metrics', legacy / 'source/experiments/metrics/evaluation_metrics.py')
    stats = module('legacy_stats', legacy / 'source/experiments/protocol/statistical_methods.py')
    runner = module('legacy_runner', legacy / 'source/experiments/runners/experiment_runner.py')
    findings = {'purpose': 'Defect counterexamples on test fixtures; not admissible research evidence', 'legacy_head': '83545b7c845454af309794d08a1ec2d41220a7db'}
    with tempfile.TemporaryDirectory(prefix='klstream-audit-probes-') as tmp:
        root = Path(tmp)
        download.generate_academic_sample_fixture(root / 'generated')
        findings['academic_fixture_byte_identity'] = []
        for p in (root / 'generated').glob('*.csv'):
            q = legacy / 'data/raw/academic_sample' / p.name
            a, b = hashlib.sha256(p.read_bytes()).hexdigest(), hashlib.sha256(q.read_bytes()).hexdigest()
            findings['academic_fixture_byte_identity'].append({'file': p.name, 'generated_sha256': a, 'existing_sha256': b, 'identical': a == b})
        dataset = legacy / 'data/processed/replay_synthetic_seed101.csv'
        records, _, _ = runner.load_dataset_split(str(dataset), str(root / 'missing-manifest.json'), 'test')
        findings['missing_split_manifest_silently_reads_rows'] = len(records)
    findings['single_class_auc_substitution'] = metrics.compute_auc_roc([0, 0], [0.1, 0.9])
    findings['tied_pr_auc_order_a'] = metrics.compute_pr_auc([0, 1], [0.5, 0.5])
    findings['tied_pr_auc_order_b'] = metrics.compute_pr_auc([1, 0], [0.5, 0.5])
    findings['two_sided_min_p_five_pairs'] = stats.wilcoxon_paired_test([1,2,3,4,5], [0,0,0,0,0])['p_value']
    findings['two_sided_min_p_six_pairs'] = stats.wilcoxon_paired_test([1,2,3,4,5,6], [0,0,0,0,0,0])['p_value']
    historical = json.loads((legacy / 'results/statistical_summary.json').read_text())
    findings['historical_fixed500_p_values'] = next(x for x in historical['comparisons']['t_e2e_p99_ns']['tests'] if x['comparator_name'] == 'fixed_w500')
    sys.path.insert(0, str(factory))
    os.environ['FACTORY_SUPERVISOR_KEY'] = '/private/tmp/klstream-audit-20260930/probe-supervisor.key'
    import gatekeeper as g
    from tests.test_v3 import fixture, evaluate
    from engine.io import read_json, write_json
    with tempfile.TemporaryDirectory(prefix='klstream-factory-probe-') as tmp, contextlib.redirect_stdout(io.StringIO()):
        root = Path(tmp)
        fixture(root)
        g.freeze(root)
        g.run_exp(root, 'known')
        before = evaluate(root)
        _, epoch, _ = g.active(root)
        execution = epoch / 'runs/known/attempt0001/execution.json'
        receipt = read_json(execution)
        receipt.pop('supervisor_receipt', None)
        write_json(execution, receipt)
        after = evaluate(root)
        findings['factory_removed_signature_audit_errors'] = {'before': before['errors'], 'after': after['errors']}
        findings['factory_assurance_without_signature'] = g._compute_assurance_level(after)
    target = Path(sys.argv[2])
    target.write_text(json.dumps(findings, indent=2, allow_nan=False) + '\n')
    print(json.dumps(findings, indent=2))

if __name__ == '__main__':
    main()
