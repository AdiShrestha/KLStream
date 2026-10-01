#!/usr/bin/env python3
"""Reproduce bounded foundation checks; never creates a research epoch.

Run with an environment permitting local Unix sockets and compiler sanitizer
runtimes. Builds/keys are temporary. This receipt is software verification only.
"""
import argparse
import ast
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as file:
        for chunk in iter(lambda:file.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def source_hashes():
    paths=[ROOT/'CMakeLists.txt']
    paths += [p for base in ('source','factory') for p in (ROOT/base).rglob('*') if p.is_file()
              and '__pycache__' not in p.parts and 'legacy' not in p.parts]
    paths += list((ROOT/'docs/audit').glob('*.py'))
    return {str(p.relative_to(ROOT)):sha(p) for p in sorted(paths)}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',default=str(ROOT/'docs/audit/second_pass_verification.json'))
    args=parser.parse_args();output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True)
    logs=output.parent/'second_pass_logs';logs.mkdir(exist_ok=True)
    initial=source_hashes()
    receipt={'purpose':'executed software fixtures only; no research, performance or certification claim',
             'started_utc':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),
             'machine':platform.machine(),'python':sys.version,'checks':[],
             'source_sha256':initial,'not_automated':['universal race/progress proof','authentic research acquisition',
             'native streaming lifecycle','offered-event scientific measurement','holdout isolation','novelty/publication readiness']}
    def run(name,argv,expected=0,timeout=180):
        print('Checking '+name,flush=True);start=time.monotonic()
        try:
            result=subprocess.run([str(x) for x in argv],cwd=ROOT,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},
                                  stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
            code=result.returncode;data=result.stdout
        except subprocess.TimeoutExpired as ex:code=None;data=(ex.stdout or b'')+b'\nCHECK TIMED OUT\n'
        log=logs/(name+'.txt');log.write_bytes(data)
        item={'name':name,'argv':[str(x) for x in argv],'exit_code':code,'expected_exit_code':expected,
              'passed':code==expected,'wall_seconds':time.monotonic()-start,
              'log':str(log.relative_to(ROOT)) if log.is_relative_to(ROOT) else str(log),'log_sha256':sha(log)}
        receipt['checks'].append(item)
        print(name+': '+('PASS' if item['passed'] else 'FAIL'),flush=True)
        return data.decode(errors='replace')
    for name,argv in [('compiler',['c++','--version']),('cmake',['cmake','--version']),
                      ('hardware',['sysctl','-n','machdep.cpu.brand_string','hw.ncpu','hw.memsize'])]:
        try:
            proc=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=15)
            receipt[name]={'argv':argv,'exit_code':proc.returncode,'stdout':proc.stdout.decode(errors='replace'),
                           'stderr':proc.stderr.decode(errors='replace')}
        except (OSError,subprocess.TimeoutExpired) as ex:receipt[name]={'available':False,'reason':str(ex)}
    disk=shutil.disk_usage(ROOT);receipt['storage_observation_bytes']=dict(zip(('total','used','free'),disk))
    with tempfile.TemporaryDirectory(prefix='klstream-final-verification-') as directory:
        temp=Path(directory)
        for name,flags in [('release',['-DCMAKE_BUILD_TYPE=Release']),
                           ('asan_ubsan',['-DCMAKE_BUILD_TYPE=Debug','-DKLSTREAM_SANITIZERS=ON'])]:
            build=temp/name
            run(name+'_configure',['cmake','-S',ROOT,'-B',build,*flags])
            run(name+'_build',['cmake','--build',build,'--parallel','2'])
            run(name+'_ctest',['ctest','--test-dir',build,'--output-on-failure'])
            receipt[name+'_binary_sha256']={p.name:sha(p) for p in (build/'engine_tests',build/'forest_reference_dump') if p.is_file()}
        tsan=temp/'engine_tests_tsan'
        run('tsan_compile',['c++','-std=c++17','-O1','-g','-Wall','-Wextra','-Wpedantic','-Werror',
                           '-fsanitize=thread','-fno-omit-frame-pointer','-pthread','-I',ROOT/'source/include',
                           ROOT/'source/tests/engine_tests.cpp','-o',tsan])
        if tsan.exists():
            run('tsan_run',[tsan]);receipt['tsan_binary_sha256']=sha(tsan)
        headers=sorted((ROOT/'source/include').rglob('*.hpp'));header_log=[];failures=[]
        for header in headers:
            name=header.relative_to(ROOT/'source/include').as_posix();unit=temp/'header.cpp'
            unit.write_text('#include <'+name+'>\nint main(){}\n')
            command=['c++','-std=c++17','-Wall','-Wextra','-Wpedantic','-Werror','-pthread',
                     '-I',str(ROOT/'source/include'),'-fsyntax-only',str(unit)]
            proc=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=30)
            header_log.append(name+' exit='+str(proc.returncode)+'\n'+proc.stdout.decode(errors='replace'))
            if proc.returncode:failures.append(name)
        log=logs/'public_headers.txt';log.write_text('\n'.join(header_log))
        receipt['public_headers']={'count':len(headers),'failed':failures,'passed':not failures,
                                  'log_sha256':sha(log),'log':str(log.relative_to(ROOT))}
        factory_text=run('factory_suite',[sys.executable,ROOT/'factory/run_self_tests.py'])
        match=re.search(r'Ran (\d+) tests',factory_text);receipt['factory_test_count']=int(match[1]) if match else None
        signature=temp/'signature.json'
        run('signature_removal_probe',[sys.executable,ROOT/'docs/audit/probe_factory_signature.py',signature])
        if signature.exists():
            value=json.loads(signature.read_text());receipt['signature_removal_probe']=value
            receipt['signature_removal_rejected']=not value['before_errors'] and bool(value['after_errors']) and value['assurance_after_removal']=='BLOCKED'
            (output.parent/'factory_signature_repaired.json').write_bytes(signature.read_bytes())
        bundle=temp/'bundle.json'
        run('standalone_bundle_probe',[sys.executable,ROOT/'docs/audit/probe_current_bundle.py',bundle])
        if bundle.exists():receipt['standalone_bundle_probe']=json.loads(bundle.read_text())
        # Root template is intentionally invalid. certify must refuse without a study.
        run('invalid_template_certify',[sys.executable,ROOT/'factory/gatekeeper.py','certify',ROOT],expected=31)
        probe=temp/'engine_counterexamples'
        run('engine_probe_compile',['c++','-std=c++17','-O2','-pthread','-I',ROOT/'source/include',
                                   ROOT/'docs/audit/active_engine_counterexamples.cpp','-o',probe])
        if probe.exists():
            text=run('engine_probe_run',[probe])
            try:
                data=json.loads(text);receipt['engine_probe']=data
                receipt['engine_counterexamples_rejected']=(data['cancelled_is_drained']==0 and data['cancelled_sink_finished']==0
                       and data['seven_percentile_us']==data['expected_seven_percentile_us'] and data['preceding_rate_credit_available']==1)
            except ValueError:receipt['engine_counterexamples_rejected']=False
    # Parse all active Python files without creating importable bytecode in source.
    problems=[];parsed=0
    for base in ('source','factory','docs/audit','docs/audit_tools'):
        for p in (ROOT/base).rglob('*.py'):
            if 'legacy' in p.parts:continue
            try:ast.parse(p.read_text(),filename=str(p));parsed+=1
            except (SyntaxError,UnicodeError) as ex:problems.append(str(ex))
    receipt['python_ast']={'count':parsed,'errors':problems,'passed':not problems}
    receipt['source_unchanged_during_verification']=initial==source_hashes()
    receipt['finished_utc']=datetime.now(timezone.utc).isoformat()
    receipt['passed']=(all(x['passed'] for x in receipt['checks']) and receipt['public_headers']['passed']
                       and receipt['python_ast']['passed'] and receipt.get('signature_removal_rejected',False)
                       and receipt.get('engine_counterexamples_rejected',False) and receipt['source_unchanged_during_verification'])
    output.write_text(json.dumps(receipt,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'passed':receipt['passed'],'factory_tests':receipt.get('factory_test_count'),
                      'public_headers':receipt['public_headers']['count'],'receipt':str(output)},indent=2),flush=True)
    return 0 if receipt['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
