"""Local receipt authentication, not worker isolation or a sealed evaluator.

Same-user workers can access the signing credentials. Ed25519 is optional via
cryptography; the stdlib fallback is a symmetric HMAC, never a public signature.
Verification is read-only and refuses missing, inconsistent or substituted keys.
"""
import base64
import binascii
import hashlib
import hmac
import locale
import os
import sys
import platform
import time
from pathlib import Path
from .io import canonical, EvidenceError, sha

SCHEME_ED25519 = 'ed25519'
SCHEME_HMAC_SHA256 = 'hmac-sha256'
_DEFAULT_KEY_DIR = Path.home() / '.factory'
_KEY_ENV = 'FACTORY_SUPERVISOR_KEY'


def _key_path():
    return Path(os.environ[_KEY_ENV]) if os.environ.get(_KEY_ENV) else _DEFAULT_KEY_DIR / 'supervisor.key'


def _pub_key_path():
    return _key_path().with_suffix('.pub')


def _try_ed25519():
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        return True
    except ImportError:
        return False


def _read_public():
    try:
        lines = _pub_key_path().read_text().splitlines()
        if len(lines) != 2 or lines[0] not in ('# ed25519', '# hmac-sha256'):
            raise EvidenceError('invalid supervisor key metadata')
        scheme = lines[0][2:]
        data = base64.b64decode(lines[1], validate=True)
        if len(data) != 32:
            raise EvidenceError('invalid supervisor key length')
        return data, scheme
    except (OSError, ValueError, binascii.Error) as ex:
        raise EvidenceError('supervisor verification key unavailable or malformed') from ex


def _load_keys():
    public, scheme = _read_public()
    try:
        private = _key_path().read_bytes()
    except OSError as ex:
        raise EvidenceError('supervisor signing key unavailable') from ex
    if len(private) != 32:
        raise EvidenceError('invalid supervisor private key length')
    if scheme == SCHEME_HMAC_SHA256:
        if not hmac.compare_digest(private, public):
            raise EvidenceError('supervisor key pair differs')
    else:
        if not _try_ed25519():
            raise EvidenceError('Ed25519 dependency unavailable; scheme downgrade forbidden')
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives import serialization
        actual = Ed25519PrivateKey.from_private_bytes(private).public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        if actual != public:
            raise EvidenceError('supervisor key pair differs')
    return private, public, scheme


def init_supervisor_keys(force=False):
    priv, pub = _key_path(), _pub_key_path()
    if not force and (priv.exists() or pub.exists()):
        if not (priv.exists() and pub.exists()):
            raise EvidenceError('incomplete supervisor key pair; refusing implicit rotation')
        _, _, scheme = _load_keys()
        return priv, pub, scheme
    priv.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if _try_ed25519():
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives import serialization
        key = Ed25519PrivateKey.generate()
        private = key.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())
        public = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        scheme = SCHEME_ED25519
    else:
        private = public = os.urandom(32)
        scheme = SCHEME_HMAC_SHA256
    # The HMAC verification file contains a secret too. Both files are private.
    for path, data in ((priv, private), (pub, f'# {scheme}\n{base64.b64encode(public).decode()}\n'.encode())):
        if path.is_symlink():
            raise EvidenceError('supervisor key path is a symlink')
        flags = os.O_WRONLY | os.O_CREAT | (os.O_TRUNC if force else os.O_EXCL)
        fd = os.open(path, flags, 0o600)
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, 'wb') as file:
                file.write(data)
        except Exception:
            raise
    return priv, pub, scheme


def sign_receipt(receipt_dict):
    init_supervisor_keys()
    private, public, scheme = _load_keys()
    signed = {k: v for k, v in receipt_dict.items() if k != 'supervisor_signature'}
    signed.update(signature_version=2, signature_scheme=scheme,
                  public_key_id=hashlib.sha256(public).hexdigest())
    payload = canonical(signed)
    if scheme == SCHEME_ED25519:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        signature = Ed25519PrivateKey.from_private_bytes(private).sign(payload)
    else:
        signature = hmac.new(private, payload, hashlib.sha256).digest()
    signed['supervisor_signature'] = base64.b64encode(signature).decode()
    return signed


def verify_receipt_signature(receipt_dict):
    if not isinstance(receipt_dict, dict) or receipt_dict.get('signature_version') != 2:
        raise EvidenceError('missing or unsupported supervisor signature version')
    public, stored_scheme = _read_public()  # Never create or rotate keys on verify.
    if receipt_dict.get('signature_scheme') != stored_scheme:
        raise EvidenceError('signature scheme differs from pinned supervisor key')
    if receipt_dict.get('public_key_id') != hashlib.sha256(public).hexdigest():
        raise EvidenceError('receipt signed by unknown supervisor key')
    try:
        signature = base64.b64decode(receipt_dict['supervisor_signature'], validate=True)
        payload = canonical({k: v for k, v in receipt_dict.items() if k != 'supervisor_signature'})
        if stored_scheme == SCHEME_ED25519:
            if not _try_ed25519():
                raise EvidenceError('Ed25519 dependency unavailable; scheme downgrade forbidden')
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
            Ed25519PublicKey.from_public_bytes(public).verify(signature, payload)
        elif not hmac.compare_digest(signature, hmac.new(public, payload, hashlib.sha256).digest()):
            raise EvidenceError('receipt signature verification failed')
    except EvidenceError:
        raise
    except Exception as ex:
        raise EvidenceError('receipt signature verification failed or malformed') from ex
    return True


def build_receipt(*, run_nonce, project_id, epoch, experiment_id,
                  snapshot_merkle_root, input_root, runtime_id,
                  interpreter_hash, dependency_lock_hash, launch_spec,
                  seed, output_root, exit_status, cpu_time, memory_peak,
                  started_at, finished_at, supervisor_version, policy_version,
                  execution_binding=None, wall_time=None):
    # None is unavailable. Never substitute elapsed wall time for CPU time or
    # fabricate zero peak memory. Resource collection needs a reviewed adapter.
    return sign_receipt({
        'receipt_version': 2, 'run_nonce': run_nonce, 'project_id': project_id,
        'epoch': epoch, 'experiment_id': experiment_id,
        'snapshot_merkle_root': snapshot_merkle_root, 'input_root': input_root,
        'runtime_id': runtime_id, 'interpreter_hash': interpreter_hash,
        'dependency_lock_hash': dependency_lock_hash, 'launch_spec': launch_spec,
        'seed': seed, 'output_root': output_root, 'exit_status': exit_status,
        'execution_binding': execution_binding,
        'resource_observations': {'cpu_time_seconds': cpu_time,
                                  'memory_peak_bytes': memory_peak,
                                  'wall_time_seconds': wall_time},
        'started_at': started_at, 'finished_at': finished_at,
        'supervisor_version': supervisor_version, 'policy_version': policy_version,
        'trust_scope': 'local_same_user_execution; no sealed evaluation or malicious-worker isolation',
    })


def execution_binding(record):
    from .io import digest
    return digest({k: v for k, v in record.items()
                   if k not in ('supervisor_receipt', 'record_error', 'receipt_error')})


def runtime_attestation():
    try:
        loc = locale.getlocale()
    except Exception:
        loc = (None, None)
    return {'interpreter_binary': sys.executable, 'interpreter_hash': sha(sys.executable),
            'python_version': sys.version, 'platform_system': platform.system(),
            'platform_release': platform.release(), 'platform_machine': platform.machine(),
            'platform_node': platform.node(), 'locale': str(loc), 'timezone': str(time.timezone),
            'encoding': sys.getdefaultencoding(), 'byte_order': sys.byteorder}


def _interpreter_hash():
    return sha(sys.executable)


def verify_freeze(freeze):
    signed=freeze.get('freeze_attestation')
    verify_receipt_signature(signed)
    metadata={'supervisor_signature','signature_scheme','public_key_id','signature_version'}
    payload={key:value for key,value in signed.items() if key not in metadata}
    if payload!={key:value for key,value in freeze.items() if key!='freeze_attestation'}:
        raise EvidenceError('freeze differs from authenticated snapshot')
    from .io import merkle_root
    if freeze.get('snapshot_algorithm')!='sha256_binary_tree_v2' or merkle_root(freeze['files'])!=freeze.get('snapshot_merkle_root'):
        raise EvidenceError('snapshot tree root mismatch')
