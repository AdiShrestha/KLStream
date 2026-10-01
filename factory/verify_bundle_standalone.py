#!/usr/bin/env python3
"""Independent byte/signature verifier: no project or engine imports.
Embedded release labels are untrusted metadata. HMAC verification requires a
shared secret; never publish its .pub file as though it were an Ed25519 key.
"""
import argparse
import base64
import hashlib
import hmac
import json
import math
import zipfile
from pathlib import Path, PurePosixPath

MANIFEST='BUNDLE_MANIFEST.json'


def canonical(obj):
    return json.dumps(obj,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


def strict_json(data):
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result: raise ValueError('duplicate JSON key')
            result[key]=value
        return result
    def bad(value): raise ValueError('non-finite JSON constant')
    def finite(value):
        result=float(value)
        if not math.isfinite(result): raise ValueError('non-finite JSON number')
        return result
    return json.loads(data,object_pairs_hook=unique,parse_constant=bad,parse_float=finite)


def _verify_receipt_sig(receipt, key, scheme):
    try:
        if not isinstance(receipt,dict) or receipt.get('signature_version')!=2:
            raise ValueError('unsupported or missing signature version')
        if receipt.get('signature_scheme')!=scheme or receipt.get('public_key_id')!=hashlib.sha256(key).hexdigest():
            raise ValueError('signature scheme/key identity mismatch')
        signature=base64.b64decode(receipt['supervisor_signature'],validate=True)
        payload=canonical({k:v for k,v in receipt.items() if k!='supervisor_signature'})
        if scheme=='ed25519':
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
            Ed25519PublicKey.from_public_bytes(key).verify(signature,payload)
        elif scheme=='hmac-sha256':
            if not hmac.compare_digest(signature,hmac.new(key,payload,hashlib.sha256).digest()):
                raise ValueError('HMAC mismatch')
        else: raise ValueError('unknown signature scheme')
        return True,None
    except Exception as ex:
        return False,'signature verification failed: '+str(ex)


def verify_bundle(path,public_key_path=None):
    errors=[];manifest={};files={};verified=0
    try:
        with zipfile.ZipFile(path) as archive:
            infos=archive.infolist();names=[i.filename for i in infos]
            for info in infos:
                name=info.filename;p=PurePosixPath(name)
                if (not name or str(p)!=name or p.is_absolute() or '..' in p.parts or ':' in name or
                    '\\' in name or name=='.' or info.is_dir() or (info.external_attr>>16)&0o170000==0o120000):
                    raise ValueError('unsafe/non-regular bundle member')
            if len(names)!=len(set(names)) or MANIFEST not in names: raise ValueError('duplicate members or missing manifest')
            if archive.getinfo(MANIFEST).file_size>16*1024*1024: raise ValueError('manifest exceeds limit')
            manifest=strict_json(archive.read(MANIFEST))
            if not isinstance(manifest,dict) or type(manifest.get('schema_version')) is not int or manifest['schema_version']!=1:
                raise ValueError('invalid manifest schema')
            files=manifest.get('files')
            if not isinstance(files,dict) or set(files)!=set(names)-{MANIFEST}: raise ValueError('manifest membership mismatch')
            for name,expected in files.items():
                h=hashlib.sha256()
                with archive.open(name) as file:
                    for chunk in iter(lambda:file.read(1024*1024),b''):h.update(chunk)
                if h.hexdigest()!=expected: raise ValueError('hash mismatch: '+name)
            if public_key_path:
                lines=Path(public_key_path).read_text().splitlines()
                if len(lines)!=2 or lines[0] not in ('# ed25519','# hmac-sha256'):raise ValueError('invalid key metadata')
                scheme=lines[0][2:];key=base64.b64decode(lines[1],validate=True)
                if len(key)!=32:raise ValueError('invalid key length')
                for name in files:
                    if not name.endswith(('execution.json','freeze.json','attempt_ledger.json')):continue
                    if archive.getinfo(name).file_size>16*1024*1024:raise ValueError('receipt exceeds limit')
                    outer=strict_json(archive.read(name))
                    receipt=outer.get('supervisor_receipt',outer.get('freeze_attestation',outer))
                    ok,message=_verify_receipt_sig(receipt,key,scheme)
                    if not ok:raise ValueError(f'{name}: {message}')
                    if 'supervisor_receipt' in outer:
                        unsigned={k:v for k,v in outer.items() if k not in ('supervisor_receipt','record_error','receipt_error')}
                        if hashlib.sha256(canonical(unsigned)).hexdigest()!=receipt.get('execution_binding'):
                            raise ValueError('execution binding mismatch: '+name)
                    if 'freeze_attestation' in outer:
                        payload={k:v for k,v in receipt.items() if k not in ('supervisor_signature','signature_scheme','public_key_id','signature_version')}
                        if payload!={k:v for k,v in outer.items() if k!='freeze_attestation'}:raise ValueError('freeze binding mismatch')
                    verified+=1
    except Exception as ex:errors.append(str(ex))
    return {'status':'FAIL' if errors else 'PASS','errors':errors,
            'files_checked':len(files) if isinstance(files,dict) and not errors else 0,
            'signatures_verified':verified if not errors else 0,
            'release_status':manifest.get('release_status','unknown') if isinstance(manifest,dict) else 'unknown',
            'factory_version':manifest.get('factory_version','unknown') if isinstance(manifest,dict) else 'unknown',
            'assurance_level':'LOCAL_SIGNATURES_VERIFIED' if verified and not errors else 'BYTE_INTEGRITY_ONLY',
            'scope':'membership, bytes and optional local authentication; release labels are untrusted; no scientific certification'}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('archive');parser.add_argument('--public-key')
    args=parser.parse_args();result=verify_bundle(args.archive,args.public_key)
    print(json.dumps(result,indent=2));raise SystemExit(result['status']!='PASS')

if __name__=='__main__':main()
