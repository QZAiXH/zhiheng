"""Free native object/ref-CAS proof; never a model/controller integration claim."""
import hashlib
import json
import os
import shutil
import sys
import tempfile
import uuid
from pathlib import Path

from .state import Blocked, atomic_json
from .runtime import Controller


# All native children share the outer Controller's process group, command timeout,
# reservation and cumulative budget. The repo is empty, template-free and has no
# inherited Git configuration: this does not bypass any policy of the real repo.
_PROGRAM = r'''
import hashlib, json, re, subprocess, sys
from pathlib import Path

root, executable = Path(sys.argv[1]), sys.argv[2]
records = []

def run(*args, data=None, allowed=(0,)):
    process = subprocess.run([executable, '-C', str(root), *args], input=data,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if len(process.stdout) > 16384 or len(process.stderr) > 16384:
        raise RuntimeError('unexpected oversized native output')
    output = process.stdout.decode('utf-8')
    records.append({'argv': list(args), 'exit_code': process.returncode,
                    'stdout': output, 'stderr': process.stderr.decode('utf-8'),
                    'stdin_sha256': hashlib.sha256(data).hexdigest() if data is not None else None})
    if process.returncode not in allowed:
        raise RuntimeError('native command failed: ' + args[0])
    return output.strip(), process.returncode

def oid(value):
    if not re.fullmatch(r'(?:[0-9a-f]{40}|[0-9a-f]{64})', value):
        raise RuntimeError('native object identity was malformed')
    return value

try:
    run('init', '--bare', '--template=', '.')
    blob = oid(run('hash-object', '-w', '--stdin', data=b'harness-controller-commit-probe\n')[0])
    tree = oid(run('mktree', data=('100644 blob ' + blob + '\tprobe.txt\n').encode())[0])
    first = oid(run('commit-tree', tree, data=b'harness controller commit probe one\n')[0])
    second = oid(run('commit-tree', tree, '-p', first, data=b'harness controller commit probe two\n')[0])
    ref = 'refs/harness-probes/controller-commit'
    zero = '0' * len(first)
    run('update-ref', ref, first, zero)
    if run('rev-parse', '--verify', ref)[0] != first:
        raise RuntimeError('initial reference write not observed')
    _, rejected = run('update-ref', ref, second, zero, allowed=(0, 1, 128))
    if rejected == 0 or run('rev-parse', '--verify', ref)[0] != first:
        raise RuntimeError('mismatching old object did not preserve the reference')
    run('update-ref', ref, second, first)
    if run('rev-parse', '--verify', ref)[0] != second:
        raise RuntimeError('matching old object update not observed')
    commit = run('cat-file', '-p', second)[0]
    if not commit.startswith('tree ' + tree + '\nparent ' + first + '\n'):
        raise RuntimeError('commit tree/parent object proof mismatch')
    if run('cat-file', '-p', blob)[0] != 'harness-controller-commit-probe':
        raise RuntimeError('blob bytes not observed')
    run('update-ref', '-d', ref, second)
    if run('for-each-ref', '--format=%(refname)', 'refs/harness-probes/')[0]:
        raise RuntimeError('probe reference cleanup not observed')
    print(json.dumps({'ok': True, 'blob': blob, 'tree': tree, 'initial_commit': first,
                      'commit': second, 'ref': ref, 'cas_rejection_observed': True,
                      'cas_update_observed': True, 'ref_cleanup_observed': True, 'commands': records}))
except Exception as exc:
    print(json.dumps({'ok': False, 'error': str(exc), 'commands': records}))
    raise SystemExit(1)
'''


def _descriptor(path):
    raw = path.read_bytes()
    return {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


def probe_controller_commit(controller, timeout):
    """Use the actual entered project Controller; retain every failure artifact."""
    from .controller_commit import policy_check

    if not isinstance(controller, Controller) or not controller.entered or not controller.run_lock.is_locked:
        raise Blocked("Controller commit capability probe requires the actual entered locked Controller")
    prior_attempts = len(controller.state.read()["attempts"])
    token = "controller-commit-probe-" + uuid.uuid4().hex
    parent = controller.common / "harness-p0-controller-commit"
    if parent.is_symlink():
        raise Blocked("Controller commit probe evidence directory cannot be a symlink")
    parent.mkdir(exist_ok=True)
    directory = parent / token
    directory.mkdir()
    result = {"version": 1, "status": "blocked", "kind": "native_controller_commit_probe",
              "scope": "isolated_temporary_repository", "model_calls": 0,
              "proves_model_controller_split": False, "logs": {},
              "host_boundary": {"status": "not_observed",
                  "detail": "Native CAS is a Controller capability, not an OS sandbox boundary. Actual host sandbox isolation requires independent host evidence; trusted simulation hosts cannot establish malicious-host isolation."}}
    temporary = None
    log = directory / "native.stdout"
    try:
        # Refuse hooks/filter/signing/custom policies before performing a native
        # object or ref write. This is an observation, not a policy override.
        result["repository_policy"] = policy_check(controller)
        executable = shutil.which("git")
        if not executable:
            raise Blocked("Git executable unavailable for native commit capability probe")
        temporary = Path(tempfile.mkdtemp(prefix="harness-controller-commit-p0-")).resolve()
        result["probe_directory"] = str(temporary)
        result["git_executable"] = executable
        env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        if os.environ.get("GIT_ALLOW_PROTOCOL") == "file":
            env["GIT_ALLOW_PROTOCOL"] = "file"  # Retain the fixture's restrictive transport boundary.
        env.update({"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
                    "GIT_ATTR_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0",
                    "GIT_AUTHOR_NAME": "Harness P0", "GIT_AUTHOR_EMAIL": "harness-p0@example.invalid",
                    "GIT_COMMITTER_NAME": "Harness P0", "GIT_COMMITTER_EMAIL": "harness-p0@example.invalid",
                    "GIT_AUTHOR_DATE": "2000-01-01T00:00:00Z", "GIT_COMMITTER_DATE": "2000-01-01T00:00:00Z"})
        record = controller.execute([sys.executable, "-c", _PROGRAM, str(temporary), executable],
                                    temporary, token, log, timeout=timeout, env=env, separate_stderr=True)
        result["execution"] = record
        for name, path in (("stdout", log), ("stderr", Path(str(log) + ".stderr"))):
            if path.is_file():
                result["logs"][name] = _descriptor(path)
        raw = log.read_bytes()
        if len(raw) > 65536:
            raise Blocked("Native controller commit probe output exceeded its bound")
        observation = json.loads(raw)
        result["observation"] = observation
        if record["exit_code"] != 0 or record["reason"] or not record["stopped"] or observation.get("ok") is not True:
            raise Blocked("Native controller commit probe failed or execution stop is unconfirmed")
        if any(observation.get(name) is not True for name in (
                "cas_rejection_observed", "cas_update_observed", "ref_cleanup_observed")):
            raise Blocked("Native controller commit probe lacks object/ref CAS proof")
        shutil.rmtree(temporary)
        result.update(status="verified", directory_cleanup_observed=True,
                      detail="Native Git objects and successful/rejected reference CAS verified in an isolated repository under the project Controller. This does not prove an actual model/controller task split.")
    except (Blocked, OSError, ValueError, KeyError) as exc:
        result["detail"] = str(exc)
        if temporary is not None and temporary.exists():
            result["preserved_probe_directory"] = str(temporary)
    for name, path in (("stdout", log), ("stderr", Path(str(log) + ".stderr"))):
        if path.is_file():
            result["logs"][name] = _descriptor(path)
    # Include policy-check stdout/stderr even when it refused before native
    # object/ref writes. These same files remain in the Controller journal.
    known = {item["path"] for item in result["logs"].values()}
    for number, attempt in enumerate(controller.state.read()["attempts"][prior_attempts:]):
        for field in ("log", "stderr_log"):
            path = Path(attempt[field]) if attempt.get(field) else None
            if path is not None and path.is_file() and str(path) not in known:
                result["logs"]["policy-" + str(number) + "-" + field] = _descriptor(path)
                known.add(str(path))
    report = directory / "report.json"
    atomic_json(report, result)
    result["report_path"] = str(report)
    result["report_sha256"] = _descriptor(report)["sha256"]
    return result
