#!/usr/bin/env python3
"""Independent packaging/verification fixture; no research or release claim."""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import zipfile
from pathlib import Path

factory=Path(__file__).resolve().parents[2]/'factory'
sys.path.insert(0,str(factory))
import gatekeeper as gate
from tests.test_v3 import fixture,evaluate
from engine.io import read_json,write_json
spec=importlib.util.spec_from_file_location('independent_bundle_verifier',factory/'verify_bundle_standalone.py')
verifier=importlib.util.module_from_spec(spec);spec.loader.exec_module(verifier)

def package(project,target):
    files={str(p.relative_to(project)):p.read_bytes() for p in project.rglob('*') if p.is_file()}
    manifest={'schema_version':1,'factory_version':gate.VERSION,'release_status':'FIXTURE_ONLY',
              'files':{name:hashlib.sha256(data).hexdigest() for name,data in files.items()}}
    with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for name,data in files.items():archive.writestr(name,data)
        archive.writestr('BUNDLE_MANIFEST.json',json.dumps(manifest,allow_nan=False))

with tempfile.TemporaryDirectory(prefix='klstream-bundle-fixture-') as tmp:
    folder=Path(tmp);project=folder/'project';project.mkdir()
    key=folder/'private/signer.key';os.environ['FACTORY_SUPERVISOR_KEY']=str(key)
    with contextlib.redirect_stdout(io.StringIO()):
        fixture(project);gate.freeze(project);code=gate.run_exp(project,'known');audit=evaluate(project)
    if code!=0 or audit['errors']:raise RuntimeError('baseline fixture already invalid')
    archive=folder/'baseline.zip';package(project,archive)
    baseline=verifier.verify_bundle(archive,key.with_suffix('.pub'))
    # Alter execution and rebuild its outer ZIP hashes. Signature binding must fail.
    _,epoch,_=gate.active(project);execution=epoch/'runs/known/attempt0001/execution.json'
    value=read_json(execution);value['interpreter_sha256']='0'*64;write_json(execution,value)
    tampered=folder/'rehash.zip';package(project,tampered)
    after=verifier.verify_bundle(tampered,key.with_suffix('.pub'))
    result={'purpose':'independent packaging fixture, not scientific evidence',
            'baseline':baseline,'tampered_execution_with_rehashed_manifest':after,
            'passed':baseline['status']=='PASS' and baseline['signatures_verified']>=3 and after['status']=='FAIL'}
Path(sys.argv[1]).write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
print(json.dumps(result,indent=2,allow_nan=False))
raise SystemExit(0 if result['passed'] else 1)
