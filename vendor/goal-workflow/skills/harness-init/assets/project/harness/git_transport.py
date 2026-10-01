"""Controlled source publication, before any PR/CI verification or delivery.

The caller supplies an already locally validated, exact source SHA. Every native
operation runs beneath Controller.execute/git, with the same budget and process
journal. Remote URLs and native remote stdout/stderr stay inside a supervised
child; credentials in a URL must never enter checkpoint or command logs.
"""
import json
import re
import sys
import uuid

from .state import Blocked


# This program is deliberately self-contained: no project imports or untrusted
# exception strings can print a remote URL. Native Git children remain in the
# Controller-owned process session. Only the fixed JSON protocol is emitted.
_REMOTE_PROGRAM = r'''
import hashlib, json, os, re, subprocess, sys, tempfile
from pathlib import Path
from urllib.parse import unquote, urlsplit

def fail(reason):
    print(json.dumps({'ok': False, 'error': reason}))
    raise SystemExit(0)

def git(*args):
    return subprocess.run(['git', *args], stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, env=environment)

def fingerprint(url):
    if '://' in url:
        parsed = urlsplit(url)
        if parsed.scheme == 'file' and parsed.hostname in (None, '', 'localhost'):
            return {'kind': 'local', 'path_sha256': hashlib.sha256(
                str(Path(unquote(parsed.path)).resolve()).encode()).hexdigest()}
        if parsed.scheme not in ('https', 'ssh') or not parsed.hostname:
            fail('unsupported_remote_transport')
        host, path = parsed.hostname.lower(), unquote(parsed.path).strip('/')
        transport, port = parsed.scheme, parsed.port
    elif re.match(r'^(?:[^/@:]+@)?[^/:]+:', url):
        authority, path = url.split(':', 1)
        host = authority.rsplit('@', 1)[-1].lower()
        transport, port = 'ssh', None
    else:
        if '::' in url or '\n' in url or '\r' in url:
            fail('unsupported_remote_transport')
        return {'kind': 'local', 'path_sha256': hashlib.sha256(
            str(Path(url).resolve()).encode()).hexdigest()}
    if path.endswith('.git'):
        path = path[:-4]
    if not re.fullmatch(r'[a-z0-9.-]+', host) or not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', path):
        fail('invalid_remote_repository')
    return {'kind': 'network', 'hostname': host, 'repository': path.lower(),
            'transport': transport, 'port': port}

try:
    action, remote, request = sys.argv[1], sys.argv[2], json.loads(sys.argv[3])
    # Git tracing can otherwise write credentials to a configured trace file.
    environment = {k: v for k, v in os.environ.items()
                   if not k.startswith('GIT_TRACE') and k != 'GIT_CURL_VERBOSE'}
    environment['GIT_TERMINAL_PROMPT'] = '0'
    configured = git('remote', 'get-url', '--push', '--all', remote)
    if configured.returncode:
        fail('named_remote_unavailable')
    urls = configured.stdout.decode('utf-8').splitlines()
    if len(urls) != 1 or not urls[0]:
        fail('exactly_one_push_destination_required')
    url = urls[0]
    destination = fingerprint(url)
    # Git rewrites URL arguments too. An alias can expand to the approved
    # host and expand elsewhere when reused by ls-remote. Resolve that native
    # argument transport without contacting a server. A second pushInsteadOf
    # match is conservatively refused rather than guessing Git's push routing.
    fetch_url = git('ls-remote', '--get-url', url)
    rows = fetch_url.stdout.decode('utf-8').splitlines()
    if fetch_url.returncode or len(rows) != 1 or fingerprint(rows[0]) != destination:
        fail('remote_url_rewrite_changes_destination')
    rewrites = git('config', '--null', '--get-regexp', r'^url\..*\.pushinsteadof$')
    if rewrites.returncode not in (0, 1):
        fail('cannot_resolve_push_url_rules')
    for entry in rewrites.stdout.decode('utf-8').split('\0'):
        if entry:
            key, prefix = entry.split('\n', 1)
            if url.startswith(prefix):
                fail('second_push_url_rewrite_requires_explicit_destination')
    if request.get('destination') is not None and request['destination'] != destination:
        fail('remote_destination_changed')
    if action == 'fingerprint':
        print(json.dumps({'ok': True, 'destination': destination}))
        raise SystemExit(0)
    network_options = ['-c', 'http.followRedirects=false']
    if request.get('use_gh_credentials'):
        if destination['kind'] != 'network':
            fail('github_credentials_require_network_destination')
        network_options += ['-c', 'credential.helper=', '-c', 'credential.helper=!gh auth git-credential']
    ref = request['ref']
    if action == 'query':
        query = git(*network_options, 'ls-remote', '--refs', url, ref)
        if query.returncode:
            fail('remote_ref_query_failed')
        rows = query.stdout.decode('utf-8').splitlines()
        if len(rows) > 1:
            fail('ambiguous_remote_ref')
        head = None
        if rows:
            fields = rows[0].split('\t')
            if len(fields) != 2 or fields[1] != ref or not re.fullmatch(r'(?:[0-9a-f]{40}|[0-9a-f]{64})', fields[0]):
                fail('malformed_remote_ref')
            head = fields[0]
        print(json.dumps({'ok': True, 'destination': destination, 'head': head}))
    elif action == 'push':
        # The normal push protocol CAS uses the old SHA advertised to this push.
        # A temporary pre-push guard pins that SHA to our prior observation, so
        # even a concurrent *fast-forward* by somebody else is not overwritten.
        # No force/lease option is used. Existing pre-push hooks still execute.
        hook_result = git('rev-parse', '--path-format=absolute', '--git-path', 'hooks/pre-push')
        if hook_result.returncode:
            fail('cannot_resolve_existing_push_hook')
        original_hook = hook_result.stdout.decode('utf-8').strip()
        guard = """import os, subprocess, sys
EXPECTED = %r
raw = sys.stdin.buffer.read()
rows = raw.decode('utf-8').splitlines()
if len(rows) != 1:
    sys.exit(91)
parts = rows[0].split()
if len(parts) != 4 or parts[1] != EXPECTED['head'] or parts[2] != EXPECTED['ref']:
    sys.exit(92)
old = EXPECTED['before'] or ('0' * len(EXPECTED['head']))
if parts[3] != old:
    sys.exit(93)
if EXPECTED.get('source_ref'):
    source = subprocess.run(['git', 'rev-parse', '--verify', EXPECTED['source_ref'] + '^{commit}'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if source.returncode or source.stdout.decode().strip() != EXPECTED['head']:
        sys.exit(94)
hook = EXPECTED['original_hook']
if os.path.isfile(hook) and os.access(hook, os.X_OK):
    result = subprocess.run([hook, EXPECTED['remote_name'], *sys.argv[2:]], input=raw, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # All original output remains private, including credential-bearing URLs.
    sys.exit(result.returncode)
""" % dict(request, original_hook=original_hook, remote_name=remote)
        with tempfile.TemporaryDirectory(prefix='harness-source-push-') as directory:
            hook = Path(directory) / 'pre-push'
            hook.write_text('#!' + sys.executable + '\n' + guard)
            hook.chmod(0o700)
            pushed = git(*network_options, '-c', 'core.hooksPath=' + directory,
                         'push', '--porcelain', '--no-force', '--no-follow-tags',
                         '--recurse-submodules=no', url, request['head'] + ':' + ref)
        print(json.dumps({'ok': pushed.returncode == 0, 'destination': destination,
                          'error': None if pushed.returncode == 0 else 'push_rejected_or_unknown'}))
    else:
        fail('unsupported_remote_action')
except SystemExit:
    raise
except Exception:
    # Never include exception text: URL parsing and subprocess errors can carry
    # the original credential-bearing URL, and their tracebacks can do so too.
    fail('remote_transport_failed')
'''


def _named_remote(remote):
    if not isinstance(remote, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', remote):
        raise Blocked('explicit safe named Git remote required')


def _branch_ref(value, *, full=False):
    if not isinstance(value, str) or not value or value.startswith('-'):
        raise Blocked('explicit branch ref required')
    if not value.startswith('refs/') and not full:
        value = 'refs/heads/' + value
    if not value.startswith('refs/heads/'):
        raise Blocked('refs/heads branch destination required')
    return value


def _git(controller, *args):
    try:
        return controller.git(*args)
    finally:
        # Native executions advance the revision even when Git fails.
        controller.state.read()


def _remote(controller, action, remote, request):
    if not controller.entered or controller.state.read().get('active'):
        raise Blocked('run lock and confirmed prior execution stop required')
    token = 'source-' + action + '-' + uuid.uuid4().hex
    output = controller.common / 'harness-source' / (token + '.stdout')
    try:
        record = controller.execute([sys.executable, '-c', _REMOTE_PROGRAM, action, remote,
                                     json.dumps(request, sort_keys=True)], controller.root,
                                    token, output, separate_stderr=True)
    finally:
        controller.state.read()
    if record['reason'] or record['exit_code'] != 0 or not record['stopped']:
        raise Blocked('controlled source ' + action + ' did not complete; outcome unknown')
    try:
        result = json.loads(output.read_text())
    except (ValueError, OSError) as exc:
        raise Blocked('source transport result missing or invalid; outcome unknown') from exc
    if not isinstance(result, dict) or result.get('ok') is not True:
        # Only fixed, allowlisted error codes are emitted, never native stderr.
        raise Blocked('controlled source ' + action + ' failed; reconcile actual remote ref')
    return result


def remote_fingerprint(controller, remote, *, expected_repository=None,
                       expected_hostname='github.com'):
    """Read the actual expanded push URL without exposing it, or making requests.

    A network repository expectation is mandatory at the production CLI boundary.
    Omitting it is intentionally low-level support for explicit local/bare tests.
    """
    _named_remote(remote)
    destination = _remote(controller, 'fingerprint', remote, {})['destination']
    if expected_repository is not None:
        if (not isinstance(expected_repository, str)
                or not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', expected_repository)
                or not isinstance(expected_hostname, str)
                or not re.fullmatch(r'[A-Za-z0-9.-]+', expected_hostname)):
            raise Blocked('explicit expected GitHub hostname and owner/repository required')
        if (destination.get('kind') != 'network'
                or destination.get('hostname') != expected_hostname.lower()
                or destination.get('repository') != expected_repository.lower()):
            raise Blocked('actual Git push destination differs from expected GitHub repository')
    return destination



def query_remote_ref(controller, remote, remote_ref, *, destination, use_gh_credentials=False):
    """Read the exact push-destination branch without logging remote credentials."""
    _named_remote(remote)
    remote_ref = _branch_ref(remote_ref, full=True)
    _git(controller, 'check-ref-format', remote_ref)
    return _remote(controller, 'query', remote, {
        'destination': destination, 'ref': remote_ref,
        'use_gh_credentials': use_gh_credentials})['head']


def push_remote_ref(controller, remote, remote_ref, head, *, destination, before,
                    source_ref=None, use_gh_credentials=False):
    """One safe native write; caller must durably journal intent and reconcile.

    The caller owns authorization and local proof. There is deliberately no
    retry here, no state-status promotion, and no promise of verified delivery.
    """
    _named_remote(remote)
    remote_ref = _branch_ref(remote_ref, full=True)
    if not isinstance(head, str) or not re.fullmatch(r'(?:[0-9a-f]{40}|[0-9a-f]{64})', head):
        raise Blocked('exact push commit SHA required')
    if before is not None and (not isinstance(before, str) or not re.fullmatch(r'(?:[0-9a-f]{40}|[0-9a-f]{64})', before)):
        raise Blocked('exact observed remote SHA required')
    _git(controller, 'check-ref-format', remote_ref)
    if source_ref is not None:
        source_ref = _branch_ref(source_ref)
        _git(controller, 'check-ref-format', source_ref)
    return _remote(controller, 'push', remote, {
        'destination': destination, 'ref': remote_ref, 'head': head,
        'before': before, 'source_ref': source_ref,
        'use_gh_credentials': use_gh_credentials})


def _save_operation(controller, operation_id, **changes):
    state = controller.state.read()
    matches = [op for op in state['remote_operations'] if op.get('operation_id') == operation_id]
    if len(matches) != 1:
        raise Blocked('source publication intent missing or ambiguous')
    matches[0].update(changes)
    return controller.state.write(state, state['revision'])


def push_source(controller, task_id, source_ref, expected_head, remote, remote_ref, *,
                expected_repository=None, expected_hostname='github.com', authorized=False,
                use_gh_credentials=False):
    """Publish exact locally passed source, never certify PR, CI or delivery.

    Existing remote commits may advance only from this task's last observed
    publication, with Git proving fast-forward ancestry. An uncertain write is
    queried once and must be reconciled before any new mutation. Restarting does
    not discard prior operations, consumed attempts or total execution budget.
    """
    if not controller.entered or authorized is not True:
        raise Blocked('explicit source push authorization and run lock required')
    if not isinstance(task_id, str) or not task_id:
        raise Blocked('explicit source publication task ID required')
    if not isinstance(expected_head, str) or not re.fullmatch(r'(?:[0-9a-f]{40}|[0-9a-f]{64})', expected_head):
        raise Blocked('exact validated source commit SHA required')
    if type(use_gh_credentials) is not bool:
        raise Blocked('use_gh_credentials must be boolean')
    _named_remote(remote)
    source_ref = _branch_ref(source_ref)
    remote_ref = _branch_ref(remote_ref, full=True)
    _git(controller, 'check-ref-format', source_ref)
    _git(controller, 'check-ref-format', remote_ref)

    def source_current():
        return _git(controller, 'rev-parse', '--verify', source_ref + '^{commit}') == expected_head

    if not source_current():
        raise Blocked('configured source ref differs from locally validated source SHA')
    destination = remote_fingerprint(controller, remote, expected_repository=expected_repository,
                                     expected_hostname=expected_hostname)
    request = {'destination': destination, 'ref': remote_ref,
               'use_gh_credentials': use_gh_credentials}
    before = _remote(controller, 'query', remote, request)['head']
    state = controller.state.read()

    def same_destination(op):
        return (op.get('action') == 'git-source-push' and op.get('task_id') == task_id
                and op.get('source_ref') == source_ref and op.get('remote') == remote
                and op.get('ref') == remote_ref and op.get('destination') == destination)

    # Actual ref observation repairs success-before-checkpoint for this identity.
    changed = False
    for op in state['remote_operations']:
        if (same_destination(op) and op.get('status') in ('intent', 'unknown')
                and before is not None and op.get('source_sha') == before):
            op.update(status='observed', observed_ref=before, reconciled=True)
            changed = True
    if changed:
        state = controller.state.write(state, state['revision'])

    if before == expected_head:
        if not source_current():
            raise Blocked('configured source ref changed during source reconciliation')
        state = controller.state.read()
        if not any(same_destination(op) and op.get('status') == 'observed'
                   and op.get('source_sha') == expected_head for op in state['remote_operations']):
            state['remote_operations'].append({
                'operation_id': uuid.uuid4().hex, 'action': 'git-source-push',
                'task_id': task_id, 'source_ref': source_ref, 'source_sha': expected_head,
                'remote': remote, 'ref': remote_ref, 'destination': destination,
                'status': 'observed', 'observed_ref': before, 'reused': True})
            controller.state.write(state, state['revision'])
        return {'status': 'source_published', 'task_id': task_id, 'source_sha': expected_head,
                'remote': remote, 'ref': remote_ref, 'reused': True}

    if any(op.get('status') in ('intent', 'unknown', 'pending') for op in state['remote_operations']):
        raise Blocked('previous remote outcome unresolved; source push will not be repeated')
    previous = [op for op in state['remote_operations'] if same_destination(op)
                and op.get('status') == 'observed']
    if before is not None:
        if not previous or previous[-1].get('source_sha') != before:
            raise Blocked('remote branch contains an unrecognized source publication')
        try:
            _git(controller, 'merge-base', '--is-ancestor', before, expected_head)
        except Blocked as exc:
            raise Blocked('source publication requires a proven fast-forward update') from exc
    elif previous:
        raise Blocked('previously published source branch was deleted; reconcile external change')
    if not source_current():
        raise Blocked('configured source ref changed before source publication')
    operation_id = uuid.uuid4().hex
    operation = {'operation_id': operation_id, 'action': 'git-source-push',
                 'task_id': task_id, 'source_ref': source_ref, 'source_sha': expected_head,
                 'remote': remote, 'ref': remote_ref, 'destination': destination,
                 'before': before, 'status': 'intent'}
    state = controller.state.read()
    state['remote_operations'].append(operation)
    controller.state.write(state, state['revision'])
    try:
        _remote(controller, 'push', remote, dict(request, head=expected_head,
                                                source_ref=source_ref, before=before))
    except Blocked:
        # Failure/timeout is not evidence the server rejected the write.
        _save_operation(controller, operation_id, status='unknown')
    try:
        after = _remote(controller, 'query', remote, request)['head']
    except Blocked:
        _save_operation(controller, operation_id, status='unknown')
        raise Blocked('source push outcome unknown; reconcile actual remote ref before retry') from None
    okay = after == expected_head
    _save_operation(controller, operation_id, status='observed' if okay else 'unknown',
                    observed_ref=after)
    if not okay:
        raise Blocked('source push outcome unknown or mismatched; no automatic retry')
    if not source_current():
        raise Blocked('source was published but configured source ref changed; revalidate before proceeding')
    return {'status': 'source_published', 'task_id': task_id, 'source_sha': expected_head,
            'remote': remote, 'ref': remote_ref, 'reused': False}
