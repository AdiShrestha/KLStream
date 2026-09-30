#!/usr/bin/env python3
"""Read-only legacy census. Classification is triage, never scientific validation."""
import argparse
import ast
import collections
import csv
import hashlib
import json
import os
import re
from pathlib import Path

TEXT = {'.py', '.hpp', '.h', '.cpp', '.c', '.md', '.txt', '.sh', '.yaml', '.yml', '.toml', '.tex', '.bib', '.cff', '.json', '.jsonl', '.cmake'}
PATTERN = re.compile(r'(?i)hardcod|fallback|mock|fabricat|representative.*curve|limit_cycle_detected|98\.02|97\.72|print\(json|t_q\s*=|t_exec\s*=|t_freshness\s*=|SUPPORTED|pickle\.loads')

def category(rel):
    first = rel.parts[0]
    if first.startswith('build') or first in {'.cache', '.snapshot_baseline', '.vscode', 'dist'} or '__pycache__' in rel.parts:
        return 'generated_or_cache_inventory_only'
    if first in {'data', 'models', 'results'}:
        return 'historical_evidence_quarantined'
    if first in {'project', 'TAKE_THIS', 'paper'} or rel.suffix == '.md':
        return 'historical_claims_and_control_records'
    if first == 'factory':
        return 'superseded_factory_v2'
    if first == 'source':
        return 'legacy_source_requires_semantic_review'
    return 'configuration_or_other'

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def main():
    p = argparse.ArgumentParser()
    p.add_argument('legacy', type=Path)
    p.add_argument('output', type=Path)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=True)
    counts = collections.Counter()
    files, text_index, json_index, csv_index = [], [], [], []
    for directory, dirs, names in os.walk(a.legacy, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d != '.git')
        for name in sorted(names):
            path = Path(directory) / name
            rel = path.relative_to(a.legacy)
            cat = category(rel)
            counts[cat] += 1
            item = {'path': str(rel), 'category': cat, 'bytes': path.lstat().st_size}
            if path.is_symlink():
                item['symlink_target'] = os.readlink(path)
            elif cat != 'generated_or_cache_inventory_only':
                item['sha256'] = sha(path)
                if path.suffix in TEXT or name in {'LICENSE', 'VERSION', '.gitignore', 'CMakeLists.txt'}:
                    s = path.read_text(errors='replace')
                    entry = {'path': str(rel), 'lines': len(s.splitlines()), 'sha256': item['sha256'], 'review_level': 'whole_file_automated_content_scan'}
                    if path.suffix == '.py':
                        try:
                            t = ast.parse(s)
                            entry['functions'] = [{'name': n.name, 'line': n.lineno, 'end': n.end_lineno} for n in ast.walk(t) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
                        except SyntaxError as e:
                            entry['syntax_error'] = str(e)
                    entry['headings'] = [line[:220] for line in s.splitlines() if line.startswith('# ') or line.startswith('## ')][:60]
                    entry['triage_matches'] = [{'line': i, 'text': line[:400]} for i, line in enumerate(s.splitlines(), 1) if PATTERN.search(line)][:80]
                    text_index.append(entry)
                    if path.suffix == '.json':
                        try:
                            obj = json.loads(s)
                            json_index.append({'path': str(rel), 'type': type(obj).__name__, 'keys': list(obj) if isinstance(obj, dict) else [], 'sha256': item['sha256']})
                        except (ValueError, TypeError) as e:
                            json_index.append({'path': str(rel), 'parse_error': str(e)})
                if path.suffix == '.csv':
                    with path.open(newline='') as f:
                        reader = csv.reader(f)
                        header = next(reader, [])
                        row_count = 0
                        widths = collections.Counter()
                        labels = collections.Counter()
                        label_i = next((header.index(k) for k in ('is_anomaly', 'label') if k in header), None)
                        for row in reader:
                            row_count += 1
                            widths[len(row)] += 1
                            if label_i is not None and len(row) > label_i:
                                labels[row[label_i]] += 1
                    csv_index.append({'path': str(rel), 'first_row': header, 'subsequent_rows': row_count, 'row_widths': dict(widths), 'label_counts': dict(labels), 'sha256': item['sha256'], 'header_status': 'first row preserved; headerless files need +1 row'})
            files.append(item)
    output = {'scope': 'all non-.git filesystem files inventoried; generated/cache bytes not semantically audited; all other bytes hashed; text scanned and Python AST parsed; CSV bodies streamed', 'legacy_root': str(a.legacy), 'counts': dict(counts), 'total_files': len(files), 'text_scanned': len(text_index), 'json_parsed': len(json_index), 'csv_streamed': len(csv_index)}
    for name, obj in [('legacy_inventory.json', files), ('legacy_text_index.json', text_index), ('legacy_json_index.json', json_index), ('legacy_csv_index.json', csv_index), ('inventory_summary.json', output)]:
        (a.output / name).write_text(json.dumps(obj, indent=2, sort_keys=True) + '\n')
    print(json.dumps(output, indent=2))

if __name__ == '__main__':
    main()
