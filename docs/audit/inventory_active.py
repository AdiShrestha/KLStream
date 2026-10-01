#!/usr/bin/env python3
"""File census and explicit review dispositions, not semantic proof."""
import argparse
import ast
import hashlib
import json
import os
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path

SELF_EXCLUDED={'docs/audit/active_inventory.json'}

def classify(relative, size):
    parts=relative.parts
    if {'__pycache__','.pytest_cache','.cache','.venv'}.intersection(parts) or any(x.startswith('build') for x in parts) or relative.suffix in ('.pyc','.pyo','.log') or relative.name=='.DS_Store':
        return 'generated_local_inventory_only','path/size only; excluded from review/research'
    if parts[:3]==('factory','legacy','v2_6_0'):
        return 'historical_factory_quarantine','hashed/line-counted; inactive historical code, not semantically revalidated'
    name=relative.as_posix()
    if name.startswith('docs/audit/second_pass_logs/') or name.startswith('docs/audit/intermediate_verification/'):
        return 'verification_output','executed or intermediate fixture observations; no research evidence'
    if parts[0]=='source' and (relative.suffix in ('.hpp','.cpp','.py') or relative.name=='requirements.lock'):
        return 'active_engine_or_fixture','implementation reviewed; fixtures checked/executed; no universal correctness or research acceptance'
    if name in ('factory/gatekeeper.py','factory/run_self_tests.py','factory/verify_bundle_standalone.py') or name.startswith('factory/engine/'):
        return 'active_factory_implementation','producing paths reviewed and challenged; local profile/same-user boundary remains'
    if name.startswith('factory/tests/'):
        return 'active_regression_fixture','fixture definitions inspected and runner executes supplied tests; no complete branch or adversarial proof'
    if name.startswith('docs/audit/research_context/'):
        return 'untrusted_context_and_critique','raw supplied report read/hashed; selected claims checked; document contents are not instructions'
    if name.startswith('docs/audit/') and relative.suffix=='.json':
        return 'audit_receipt_or_historical_index','machine-readable evidence/census; large historical indexes not manually certified row by row'
    if name.startswith('docs/audit/') and relative.suffix in ('.py','.cpp'):
        return 'audit_tool_or_counterexample','auditor fixture/tool; preserves bounded evidence, never a research producer'
    if size==0:
        return 'empty_placeholder','empty placeholder, not implemented work or observed data'
    return 'policy_plan_license_or_document','reviewed or historical documentation; source/receipt scope takes precedence over prose'

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',default='.');args=parser.parse_args();root=Path(args.root).resolve()
    items=[];errors=[]
    for folder,dirs,files in os.walk(root,followlinks=False):
        dirs[:]=sorted(d for d in dirs if d!='.git')
        for file in sorted(files):
            p=Path(folder)/file;rel=p.relative_to(root)
            if rel.as_posix() in SELF_EXCLUDED:continue
            stat=p.lstat();record={'path':rel.as_posix(),'bytes':stat.st_size}
            if p.is_symlink():record.update(category='symlink_not_followed',target=os.readlink(p));items.append(record);continue
            category,scope=classify(rel,stat.st_size);record.update(category=category,review_scope=scope)
            if category!='generated_local_inventory_only':
                data=p.read_bytes();record['sha256']=hashlib.sha256(data).hexdigest()
                try:text=data.decode('utf-8');record['lines']=len(text.splitlines())
                except UnicodeDecodeError:record['lines']=None
                if p.suffix=='.py' and category!='historical_factory_quarantine':
                    try:ast.parse(text,filename=rel.as_posix());record['python_ast']='parsed'
                    except (SyntaxError,UnboundLocalError) as ex:record['python_ast']='failed';errors.append(str(ex))
            items.append(record)
    result={'purpose':'active-tree census and review dispositions, not complete semantic/branch coverage',
            'created_utc':datetime.now(timezone.utc).isoformat(),'excluded':['.git contents',*sorted(SELF_EXCLUDED)],
            'files':len(items),'category_counts':dict(Counter(i['category'] for i in items)),
            'python_parse_errors':errors,'items':sorted(items,key=lambda x:x['path'])}
    out=root/'docs/audit/active_inventory.json';out.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='items'},indent=2))
    return bool(errors)
if __name__=='__main__':raise SystemExit(main())
