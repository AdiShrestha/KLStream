"""One canonical launch specification shared by execution and evidence audit.

Python/stdlib is the only implemented profile. Network isolation, per-job memory
and per-job process caps have no portable enforcement here and are rejected.
"""
import sys
import re
from pathlib import Path
from .io import inside, sha
from .metrics import EvidenceError
from .schema import expect_dict, expect_str, expect_int, expect_enum

KNOWN_RUNTIMES = {'python-cpu-v1': {'binary': sys.executable,
    'flags': ['-I', '-P', '-B', '-S'] if sys.version_info >= (3,11) else ['-I','-B','-S'], 'kind': 'python'}}


def _arguments(contract):
    args = contract.get('arguments', [])
    if isinstance(args, dict):
        # Compatibility for the old three-placeholder spelling. Dict sorting
        # previously put experiment_id first and silently swapped worker inputs.
        order = ('run_dir', 'seed', 'experiment_id')
        if set(args) - set(order):
            raise EvidenceError('use an ordered arguments list for literal or named arguments')
        args = [args[key] for key in order if key in args]
    if not isinstance(args, list):
        raise EvidenceError('execution_contract.arguments must be an ordered list')
    for value in args:
        expect_str(value, 'execution_contract.arguments item')
        if '\x00' in value:
            raise EvidenceError('NUL in execution argument')
    return args


def validate_contract(contract, root, frozen_code_paths):
    expect_dict(contract, 'execution_contract')
    allowed = {'runtime_id','entrypoint','arguments','network','cpu_seconds','wall_seconds','memory_bytes','process_limit'}
    if set(contract) - allowed:
        raise EvidenceError('unknown execution contract fields')
    if contract.get('runtime_id') not in KNOWN_RUNTIMES:
        raise EvidenceError('unknown runtime_id')
    entrypoint = contract.get('entrypoint')
    expect_str(entrypoint, 'execution_contract.entrypoint')
    path = inside(root, entrypoint)
    if not entrypoint.endswith('.py') or not path.is_file():
        raise EvidenceError('entrypoint must be an existing Python source file')
    if not any(entrypoint == cp or entrypoint.startswith(cp.rstrip('/') + '/') for cp in frozen_code_paths):
        raise EvidenceError('entrypoint must be inside a declared frozen code_path')
    _arguments(contract)
    for field in ('cpu_seconds','wall_seconds','memory_bytes','process_limit'):
        if field in contract:
            expect_int(contract[field], 'execution_contract.' + field, minimum=1)
    if 'memory_bytes' in contract or 'process_limit' in contract:
        raise EvidenceError('per-job memory/process limits are not implemented; do not declare them enforced')
    expect_enum(contract.get('network','allowed'), {'disabled','allowed'}, 'execution_contract.network')
    if contract.get('network') == 'disabled':
        raise EvidenceError('network isolation is not implemented for this runtime')
    return contract


def resolve_contract(contract, run_dir, seed, experiment_id):
    runtime = KNOWN_RUNTIMES[contract['runtime_id']]
    bound = {'supervisor_bound':str(Path(run_dir).resolve()), 'plan_seed':str(seed), 'plan_id':str(experiment_id)}
    argv = [runtime['binary'], *runtime['flags'], contract['entrypoint']]
    for value in _arguments(contract):
        value = bound.get(value, value)
        value = value.replace('{run_dir}',str(Path(run_dir).resolve())).replace('{seed}',str(seed)).replace('{experiment_id}',str(experiment_id))
        # Unknown braces must not silently become an unresolved policy parameter.
        if re.search(r'\{[^{}]+\}', value):
            raise EvidenceError('unresolved execution argument placeholder')
        argv.append(value)
    return argv, _build_preexec(contract), {'PYTHONDONTWRITEBYTECODE':'1'}


def _build_preexec(contract):
    cpu = contract.get('cpu_seconds')
    if not cpu:
        return None
    import resource
    def set_limits():
        # This limits CPU seconds per process, not the sum across descendants.
        resource.setrlimit(resource.RLIMIT_CPU, (cpu,cpu))
    return set_limits


def command_to_contract(command, code_paths):
    if not isinstance(command,list) or len(command)<2 or not all(isinstance(x,str) for x in command):
        raise EvidenceError('command must be an argv list for a frozen Python script')
    exe = Path(command[0]).name
    if not re.fullmatch(r'python(?:\d+(?:\.\d+)*)?', exe):
        raise EvidenceError('legacy command must directly invoke a Python runtime')
    index = 1
    while index<len(command) and command[index] in ('-I','-P','-B','-S'):
        index += 1
    if index == len(command):
        raise EvidenceError('command has no source entrypoint')
    ep = command[index]
    if not ep.endswith('.py') or not any(ep==cp or ep.startswith(cp.rstrip('/')+'/') for cp in code_paths):
        raise EvidenceError('command must directly execute a declared frozen code_path')
    if any('\x00' in value for value in command):
        raise EvidenceError('NUL in command')
    return {'runtime_id':'python-cpu-v1','entrypoint':ep,
            'arguments':command[index+1:],'network':'allowed'}, 'legacy command normalized to pinned Python; migrate to execution_contract'


def experiment_contract(experiment, root):
    contract = experiment.get('execution_contract')
    if contract is None:
        contract, _ = command_to_contract(experiment['command'], experiment['code_paths'])
    return validate_contract(contract, Path(root), experiment['code_paths'])


def runtime_binary_hash():
    return sha(sys.executable)
