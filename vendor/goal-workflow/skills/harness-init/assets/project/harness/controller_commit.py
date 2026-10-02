"""Opt-in restricted commit plumbing; deliberately not porcelain-commit equivalence.

The model may change only the named regular files. This controller rejects native
hooks, content filters, signing, executable Git policy, unusual index entries,
and concurrent repository changes rather than silently bypassing those policies.
Every Git subprocess is owned and budgeted by Controller.execute. Unknown object
or CAS outcomes are never retried. Reconciliation reads facts; recover_index is
an explicit, idempotent completion step only for an already proven ref update.
"""
import hashlib
import functools
import contextvars
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import time
import uuid
import unicodedata

from .state import Blocked, atomic_json

_VERSION = 1
_MAX_FILES = 50000
_MAX_BYTES = 256 * 1024 * 1024
_OWN = {"harness.run.lock", "harness.state.lock", "harness.execution.json",
        "harness-git", "harness-controller-commits", "harness-runs",
        "harness-worktrees", "harness-source", "harness-capability-versions",
        "harness-native", "harness-github"}
_OID = re.compile(r"(?:[a-f0-9]{40}|[a-f0-9]{64})\Z")

# Reading all effective config directly into controller logs could expose remote
# credentials. The supervised helper emits a digest, origins, and fixed errors;
# native config bytes and stderr never leave this child.
_INSPECT = r'''
import hashlib,json,os,pathlib,stat,subprocess,sys
root=sys.argv[1]
def fail(code):
    print(json.dumps({'error':code}));sys.exit(0)
def git(*args):
    p=subprocess.run(['git','-C',root,*args],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if p.returncode: fail('native_read_failed')
    return p.stdout
def autocrlf_disabled(rows):
    # Git's scalar value is the last occurrence in this same ordered read.
    value=next((value for key,value in reversed(rows) if key=='core.autocrlf'),'false')
    return value.lower() in ('false','no','off','0')
try:
    raw=git('config','--null','--show-origin','--list')
    parts=raw.split(b'\0'); rows=[]; origins=[]
    for i in range(0,len(parts)-1,2):
        origin=parts[i].decode('utf-8'); row=parts[i+1].decode('utf-8')
        key,_,value=row.partition('\n'); key=key.lower(); rows.append((key,value))
        if origin.startswith('file:'): origins.append(origin[5:])
        elif origin not in ('command line:',): fail('unsupported_config_origin')
    for key,value in rows:
        truth=value.lower() not in ('false','no','off','0')
        if key.startswith('filter.'): fail('content_filters_unsupported')
        if key=='core.hookspath': fail('custom_hooks_path_unsupported')
        if ((key in ('commit.gpgsign','tag.gpgsign') and truth)
            or key.startswith('gpg.') or key=='user.signingkey'): fail('signing_policy_unsupported')
        if ((key=='core.fsmonitor' and truth) or key in ('core.editor','sequence.editor','diff.external','core.pager')
            or key.startswith('pager.')
            or (key.startswith('diff.') and key.endswith(('.command','.textconv')))
            or (key.startswith('merge.') and key.endswith('.driver'))): fail('executable_git_policy_unsupported')
        if key in ('extensions.partialclone','extensions.worktreeconfig') and truth: fail('repository_extension_unsupported')
        if key in ('core.sparsecheckout','core.splitindex') and truth: fail('unusual_index_policy_unsupported')
        if key=='core.eol': fail('content_transform_policy_unsupported')
    if not autocrlf_disabled(rows): fail('content_transform_policy_unsupported')
    def text(*args): return git(*args).decode('utf-8').strip()
    # Validate real identity before a paid implementation attempt; never supply
    # a synthetic identity. Exclude Git's moving timestamp from the binding.
    author=text('var','GIT_AUTHOR_IDENT').rsplit(' ',2)[0]
    committer=text('var','GIT_COMMITTER_IDENT').rsplit(' ',2)[0]
    if not author or not committer: fail('actual_git_identity_missing')
    common=text('rev-parse','--path-format=absolute','--git-common-dir')
    gitdir=text('rev-parse','--absolute-git-dir')
    for name in ('shallow','info/grafts','objects/info/alternates'):
        special=pathlib.Path(common)/name
        if special.exists() or special.is_symlink(): fail('alternate_or_shallow_history_unsupported')
    if git('for-each-ref','--format=%(refname)','refs/replace').strip(): fail('replace_objects_unsupported')
    hooks=text('rev-parse','--path-format=absolute','--git-path','hooks')
    head=text('rev-parse','--verify','HEAD^{commit}')
    ref=text('symbolic-ref','HEAD')
    tree=text('rev-parse','--verify','HEAD^{tree}')
    parents=text('rev-list','--parents','-n','1',head).split()[1:]
    index=text('rev-parse','--path-format=absolute','--git-path','index')
    entries=[]
    for row in git('ls-tree','-rz','--full-tree',head).split(b'\0'):
        if row:
            meta,name=row.split(b'\t',1);mode,kind,oid=meta.decode().split()
            if mode not in ('100644','100755') or kind!='blob': fail('symlink_or_gitlink_unsupported')
            entries.append({'path':name.decode('utf-8'),'mode':mode,'oid':oid})
    staged=[]
    for row in git('-c','core.fsmonitor=false','ls-files','--stage','-z').split(b'\0'):
        if row:
            meta,name=row.split(b'\t',1);mode,oid,stage=meta.decode().split()
            if stage!='0' or mode not in ('100644','100755'): fail('unmerged_or_unusual_index')
            staged.append({'path':name.decode('utf-8'),'mode':mode,'oid':oid})
    for row in git('-c','core.fsmonitor=false','ls-files','-v','-z').split(b'\0'):
        if row and row[:1]!=b'H': fail('assume_unchanged_or_sparse_index')
    print(json.dumps({'common':common,'gitdir':gitdir,'hooks':hooks,'head':head,
        'ref':ref,'tree':tree,'parents':parents,'index':index,'entries':entries,'staged':staged,
        'config_sha256':hashlib.sha256(raw).hexdigest(),'config_origins':sorted(set(origins)),
        'attributes_files':[v for k,v in rows if k=='core.attributesfile'],
        'author_identity_sha256':hashlib.sha256(author.encode()).hexdigest(),
        'committer_identity_sha256':hashlib.sha256(committer.encode()).hexdigest()}))
except Exception: fail('native_inspection_failed')
'''


_DEADLINE = contextvars.ContextVar('controller_commit_deadline', default=None)


def _budgeted(function):
    @functools.wraps(function)
    def invoke(controller, *args, **kwargs):
        if not controller.entered:
            raise Blocked('run lock required for restricted commit audit')
        before = controller.state.read()['spent_seconds']
        started = time.monotonic()
        remaining = controller.limits['total_seconds'] - before
        if remaining <= 0:
            raise Blocked('budget_exhausted')
        deadline = min(_DEADLINE.get() or float('inf'), started + remaining)
        token = _DEADLINE.set(deadline)
        try:
            return function(controller, *args, **kwargs)
        finally:
            _DEADLINE.reset(token)
            state = controller.state.read()
            uncharged = max(0, time.monotonic() - started - (state['spent_seconds'] - before))
            if uncharged:
                state['spent_seconds'] += uncharged
                state['controller_audit_seconds'] = state.get('controller_audit_seconds', 0) + uncharged
                controller.state.write(state, state['revision'])
    return invoke


def _check_deadline():
    if _DEADLINE.get() is not None and time.monotonic() >= _DEADLINE.get():
        raise Blocked('budget_exhausted during bounded filesystem audit')


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=True).encode()).hexdigest()


def _enabled(config):
    if config.get('host', {}).get('commit_mode', 'model_commit') != 'controller_commit':
        raise Blocked('explicit host.commit_mode=controller_commit required')


def _branch_ref(value, *, target=False):
    if not isinstance(value, str) or not value:
        raise Blocked('explicit Git branch ref required')
    if value.startswith('refs/'):
        if value.startswith('refs/heads/') or (target and value.startswith('refs/remotes/')):
            return value
        raise Blocked('source must be local; target must be local or remote-tracking branch')
    return 'refs/heads/' + value


def _id(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,100}', value) or '..' in value:
        raise Blocked('invalid controller commit operation identity')
    return value


def _environment():
    # Ambient overrides could redirect the repository, config, index, attributes,
    # object store, signing, or helpers. Do not reinterpret them as authorization.
    forbidden = [key for key in os.environ if key.startswith('GIT_')
                 and key not in ('GIT_TERMINAL_PROMPT', 'GIT_OPTIONAL_LOCKS', 'GIT_PAGER',
                     'GIT_ALLOW_PROTOCOL', 'GIT_CONFIG_NOSYSTEM', 'GIT_CONFIG_GLOBAL',
                     'GIT_AUTHOR_NAME', 'GIT_AUTHOR_EMAIL', 'GIT_COMMITTER_NAME', 'GIT_COMMITTER_EMAIL')]
    if os.environ.get('GIT_CONFIG_GLOBAL', '/dev/null') != '/dev/null':
        forbidden.append('GIT_CONFIG_GLOBAL')
    if forbidden:
        raise Blocked('ambient Git environment overrides unsupported')
    result = dict(os.environ)
    result.update(GIT_TERMINAL_PROMPT='0', GIT_OPTIONAL_LOCKS='0')
    return result


def _run(controller, path, argv, *, index=None, input_text=None):
    if not controller.entered or controller.state.read().get('active'):
        raise Blocked('run lock and confirmed prior execution stop required')
    token = 'controller-commit-' + uuid.uuid4().hex
    output = controller.common / 'harness-controller-commits' / 'logs' / (token + '.stdout')
    env = _environment()
    if index is not None:
        env['GIT_INDEX_FILE'] = str(index)
    _check_deadline()
    remaining = ((_DEADLINE.get() - time.monotonic()) if _DEADLINE.get() is not None
                 else controller.limits['command_seconds'])
    if remaining <= 0:
        raise Blocked('budget_exhausted before native commit command')
    record = controller.execute(argv, path, token, output, env=env,
                                timeout=min(controller.limits['command_seconds'], remaining),
                                input_text=input_text, separate_stderr=True)
    if record.get('reason') or record.get('exit_code') != 0 or not record.get('stopped'):
        raise Blocked('controlled commit operation failed or outcome unknown; reconcile, never retry')
    with output.open('rb') as stream:
        raw = stream.read(_MAX_BYTES + _MAX_FILES * 200 + 1)
    if len(raw) > _MAX_BYTES + _MAX_FILES * 200:
        raise Blocked('bounded native output exceeded')
    return raw


def _hook_guard(controller, path, expected=None):
    guard = controller.common / 'harness-controller-commits' / 'empty-hooks'
    if guard.is_relative_to(Path(path).resolve()):
        raise Blocked('hook guard must be outside the model worktree')
    if not os.path.lexists(guard):
        if expected is not None:
            raise Blocked('controller hook guard disappeared')
        guard.mkdir(mode=0o700)
    info = guard.lstat()
    identity = {'device': info.st_dev, 'inode': info.st_ino, 'uid': info.st_uid,
                'mode': stat.S_IMODE(info.st_mode)}
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != 0o700 or any(guard.iterdir())
            or (expected is not None and identity != expected)):
        raise Blocked('cannot attest isolated empty controller hook directory')
    return guard, identity


def _git(controller, path, *args, index=None, input_text=None, guard_identity=None, model_worktree=None):
    # Existing policy is rejected, never waived. This attested empty directory
    # prevents concurrent activation in the original hook directory from running
    # during the final audit/CAS race. Post-audit still rejects that policy drift.
    guarded_path = model_worktree or path
    guard, observed_identity = _hook_guard(controller, guarded_path, guard_identity)
    try:
        raw = _run(controller, path, ['git', '-C', str(path), '-c',
                    'core.hooksPath=' + str(guard), '-c', 'core.fsmonitor=false',
                    '-c', 'commit.gpgsign=false', *args],
                    index=index, input_text=input_text)
    except BaseException as exc:
        try:
            _hook_guard(controller, guarded_path, observed_identity)
        except Blocked as guard_error:
            raise Blocked('native outcome unknown and controller hook guard changed') from exc
        raise
    _hook_guard(controller, guarded_path, observed_identity)
    return raw.decode('utf-8').strip()


def _regular(path):
    _check_deadline()
    try:
        before = path.lstat()
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise Blocked('only unlinked regular files are supported: ' + str(path))
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            opened = os.fstat(fd)
            if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
                raise Blocked('file changed during audit')
            with os.fdopen(fd, 'rb', closefd=False) as stream:
                data = stream.read(_MAX_BYTES + 1)
            after = os.fstat(fd)
        finally:
            os.close(fd)
        stamp = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns, s.st_mode)
        if len(data) > _MAX_BYTES or stamp(before) != stamp(after) or stamp(after) != stamp(path.lstat()):
            raise Blocked('file changed or exceeded audit bound')
        return data, before.st_mode
    except OSError as exc:
        raise Blocked('cannot audit regular file safely') from exc


def _file(path):
    data, mode = _regular(path)
    return {'sha256': hashlib.sha256(data).hexdigest(), 'mode': stat.S_IMODE(mode), 'size': len(data)}


def _scan(root, *, skip=()):
    result, size = {}, 0
    if root.is_symlink() or not root.is_dir():
        raise Blocked('unsafe audit directory')
    for base, directories, files in os.walk(root, followlinks=False):
        _check_deadline()
        relative = Path(base).relative_to(root)
        if relative == Path('.'):
            directories[:] = [name for name in directories if name not in skip]
            files = [name for name in files if name not in skip]
        for name in directories:
            if (Path(base) / name).is_symlink():
                raise Blocked('symlink directories unsupported')
        for name in files:
            path = Path(base) / name
            result[path.relative_to(root).as_posix()] = _file(path)
            size += result[path.relative_to(root).as_posix()]['size']
            if len(result) > _MAX_FILES or size > _MAX_BYTES:
                raise Blocked('restricted commit audit bound exceeded')
    return result


def _metadata(common):
    return _scan(common, skip=_OWN)


def _allowed(task, config=None, roots=()):
    values = task.get('allowed_paths')
    if not isinstance(values, list) or not values or len(values) > 500 or not all(isinstance(v, str) for v in values) or len(values) != len(set(values)):
        raise Blocked('controller commit requires explicit unique allowed_paths')
    normalized = [unicodedata.normalize('NFC', value).casefold() for value in values]
    if len(normalized) != len(set(normalized)):
        raise Blocked('portable-colliding allowed_paths')
    for value in values:
        if (not isinstance(value, str) or not value or '\\' in value or '\x00' in value
                or any(c in value for c in '*?[]:!\r\n\t') or value.startswith('-')
                or PurePosixPath(value).is_absolute()
                or any(part in ('', '.', '..') or part.casefold() == '.git' for part in value.split('/'))
                or value.casefold() == '.loop-state.json' or value != value.strip() or len(value) > 4096
                or any(ord(c) < 32 or ord(c) == 127 for c in value)
                or any(part.endswith(('.', ' ')) or re.fullmatch(r'(?i)(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?', part) for part in value.split('/'))):
            raise Blocked('allowed_paths must be literal repository-relative file paths')
    protected = set()
    for item in [task.get('spec')] + [arg for check in (config or {}).get('checks', []) for arg in check.get('argv', [])]:
        if not isinstance(item, str) or not item:
            continue
        token = item.split('=', 1)[1] if item.startswith('-') and '=' in item else item
        if token.startswith('-'):
            continue
        for root in roots:
            root = Path(root).resolve()
            candidate = Path(token) if Path(token).is_absolute() else root / token
            try:
                canonical = candidate.resolve()
                if canonical.is_relative_to(root):
                    protected.add(canonical.relative_to(root).as_posix())
            except (OSError, RuntimeError) as exc:
                raise Blocked('cannot resolve approved checker/spec path safely') from exc
    for value in values:
        if value in protected:
            raise Blocked('allowed_paths may not include the approved checker/spec file')
        parts = value.split('/')
        if (any(part.casefold() in ('.harness', '.agents', '.codex') for part in parts)
                or parts[-1].casefold() in ('agents.md', '.gitattributes', '.gitmodules')
                or value == '.serena/project.yml' or value == task.get('spec')):
            raise Blocked('allowed_paths may not include protected policy/contract files')
        for check in (config or {}).get('checks', []):
            if value in check.get('argv', []):
                raise Blocked('allowed_paths may not include the approved check executable')
    return sorted(values)


def _origin_files(result, path):
    files = {}
    for name in result['config_origins']:
        origin = Path(name)
        if not origin.is_absolute():
            origin = path / origin
        files[str(origin.absolute())] = _file(origin)
    hooks = Path(result['hooks'])
    if not hooks.is_absolute():
        hooks = path / hooks
    if hooks.is_symlink():
        raise Blocked('symlink hook directory unsupported')
    hook_files = _scan(hooks) if hooks.exists() else {}
    for name, item in hook_files.items():
        # Git sample hooks are not actual hooks, even if executable.
        if not name.endswith('.sample') and item['mode'] & 0o111:
            raise Blocked('executable Git hook unsupported: ' + name)
    attrs = [Path(result['common']) / 'info/attributes']
    attrs += [Path(name).expanduser() for name in result.pop('attributes_files')]
    attrs.append(Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config'))) / 'git/attributes')
    for base, directories, names in os.walk(path, followlinks=False):
        _check_deadline()
        directories[:] = [name for name in directories if name != '.git']
        if '.gitattributes' in names:
            attrs.append(Path(base) / '.gitattributes')
    for attr in attrs:
        if not attr.is_absolute():
            attr = path / attr
        if attr.is_symlink():
            raise Blocked('symlink attributes file unsupported')
        if attr.exists():
            data, _ = _regular(attr)
            if data.strip():
                raise Blocked('active attributes policy unsupported by raw-blob controller commit')
            files[str(attr.absolute())] = _file(attr)
    result['policy_files'] = files
    result['hook_files'] = hook_files
    return result


@_budgeted
def policy_check(controller, path=None):
    """Read-only native preflight, suitable for an opt-in capability probe."""
    path = Path(path or controller.root).resolve()
    raw = _run(controller, path, [sys.executable, '-c', _INSPECT, str(path)])
    try:
        result = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise Blocked('invalid native commit inspection') from exc
    if result.get('error'):
        raise Blocked('restricted controller commit: ' + result['error'])
    if Path(result['common']).resolve() != controller.common.resolve():
        raise Blocked('commit worktree belongs to another repository')
    return _origin_files(result, path)


def _worktree(controller, path, oid_length):
    skip = {'.git'}
    if path == controller.state.path.parent:
        skip.add(controller.state.path.name)
    manifest = _scan(path, skip=skip)
    for name, row in manifest.items():
        raw, mode = _regular(path / name)
        algorithm = hashlib.sha1 if oid_length == 40 else hashlib.sha256
        row['oid'] = algorithm(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        row['mode'] = '100755' if mode & 0o111 else '100644'
    return manifest


def _tree(manifest):
    return {row['path']: {'mode': row['mode'], 'oid': row['oid']} for row in manifest}


def _content(manifest):
    return {name: {'mode': row['mode'], 'oid': row['oid']} for name, row in manifest.items()}


def operation_worktree(controller, operation_id):
    """Resolve only the durable operation's worktree, never a caller-supplied path."""
    return Path(_load(_directory(controller, operation_id))['snapshot']['worktree'])


def _directory(controller, operation_id):
    parent = controller.common / 'harness-controller-commits'
    if parent.is_symlink():
        raise Blocked('unsafe commit journal directory')
    parent.mkdir(exist_ok=True)
    directory = parent / _id(operation_id)
    if directory.is_symlink():
        raise Blocked('unsafe commit operation directory')
    return directory


def _load(directory):
    try:
        value = json.loads(_regular(directory / 'operation.json')[0])
    except (ValueError, OSError) as exc:
        raise Blocked('controller commit journal missing or damaged') from exc
    if not isinstance(value, dict) or value.get('schema_version') != _VERSION or value.get('snapshot', {}).get('operation_id') != directory.name:
        raise Blocked('unsupported controller commit journal')
    return value


def _save(directory, value):
    atomic_json(directory / 'operation.json', value)


def _binding(controller, config, task, path, snapshot):
    _enabled(config)
    if Path(path).is_symlink():
        raise Blocked('worktree symlink alias unsupported')
    path = Path(path).resolve()
    if (snapshot['worktree'] != str(path) or snapshot['common'] != str(controller.common.resolve())
            or snapshot['task_sha256'] != _digest(task) or snapshot['config_sha256'] != _digest(config)
            or snapshot['allowed_paths'] != _allowed(task, config, (controller.root, path))
            or snapshot['git_environment_sha256'] != _digest({k: v for k, v in _environment().items() if k.startswith('GIT_')})):
        raise Blocked('controller commit task/config/provenance changed')
    return path


def _read_regular_tree(controller, path, oid):
    """Read a bounded, literal regular-file tree and one framed native blob batch."""
    raw = _run(controller, path, ['git', '-C', str(path), 'ls-tree', '-rz', '-l', '--full-tree', oid])
    manifest, normalized, total = {}, set(), 0
    for entry in raw.split(b'\0'):
        _check_deadline()
        if not entry:
            continue
        try:
            metadata, encoded_name = entry.split(b'\t', 1)
            mode, kind, object_id, size = metadata.decode('ascii').split()
            name, size = encoded_name.decode('utf-8'), int(size)
        except (ValueError, UnicodeError) as exc:
            raise Blocked('malformed native target tree') from exc
        parts = name.split('/')
        key = unicodedata.normalize('NFC', name).casefold()
        if (mode not in ('100644', '100755') or kind != 'blob' or not _OID.fullmatch(object_id)
                or size < 0 or name != name.strip() or len(name) > 4096
                or any(part in ('', '.', '..') or part.casefold() == '.git'
                       or part.endswith(('.', ' ')) for part in parts)
                or any(char in name for char in '\\:')
                or any(ord(char) < 32 or ord(char) == 127 for char in name)
                or any(re.fullmatch(r'(?i)(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?', part) for part in parts)
                or key in normalized):
            raise Blocked('target tree requires unsupported paths or nonregular entries')
        normalized.add(key)
        manifest[name] = {'mode': mode, 'oid': object_id, 'size': size}
        total += size
        if len(manifest) > _MAX_FILES or total > _MAX_BYTES:
            raise Blocked('restricted target tree bound exceeded')
    if any('/'.join(key.split('/')[:n]) in normalized
           for key in normalized for n in range(1, len(key.split('/')))):
        raise Blocked('target tree has portable file/directory prefix collision')
    names = sorted(manifest)
    batch = _run(controller, path, ['git', '-C', str(path), 'cat-file', '--batch'],
                 input_text=''.join(manifest[name]['oid'] + '\n' for name in names))
    contents, position = {}, 0
    for name in names:
        _check_deadline()
        row = manifest[name]
        end = batch.find(b'\n', position)
        expected = (row['oid'] + ' blob ' + str(row['size'])).encode()
        if end < 0 or batch[position:end] != expected:
            raise Blocked('malformed native target blob framing')
        start = end + 1
        content = batch[start:start + row['size']]
        position = start + row['size']
        algorithm = hashlib.sha1 if len(row['oid']) == 40 else hashlib.sha256
        if (len(content) != row['size'] or batch[position:position + 1] != b'\n'
                or algorithm(b'blob ' + str(len(content)).encode() + b'\0' + content).hexdigest() != row['oid']):
            raise Blocked('native target blob does not match its exact object identity')
        position += 1
        if name.split('/')[-1].casefold() == '.gitattributes' and content.strip():
            raise Blocked('target attributes policy unsupported by raw materialization')
        row['sha256'] = hashlib.sha256(content).hexdigest()
        contents[name] = content
    if position != len(batch):
        raise Blocked('unexpected trailing native target blob data')
    return manifest, contents


@_budgeted
def add_task_worktree(controller, config, task, path):
    """Create an ordinary-file task checkout without native checkout/filter hooks.

    This intentionally supports fewer semantics than porcelain checkout. Unknown
    or interrupted creation keeps its native branch/worktree and durable intent;
    it is never retried, rolled back, or presented as model-ready automatically.
    """
    _enabled(config)
    if Path(path).is_symlink():
        raise Blocked('task worktree symlink unsupported')
    path = Path(path).resolve()
    _allowed(task, config, (controller.root, path))
    owner = controller.common / 'harness-worktrees'
    if owner.is_symlink() or path.parent != owner.resolve() or os.path.lexists(path):
        raise Blocked('new task worktree must be an absent direct controller-owned path')
    source = _branch_ref(task['source'])
    target = _branch_ref(task['target'], target=True)
    if source == target:
        raise Blocked('task source and target branches must differ')
    before = policy_check(controller, controller.root)
    guard, guard_identity = _hook_guard(controller, path)
    def native(*args, cwd=None):
        return _git(controller, cwd or controller.root, *args,
                    guard_identity=guard_identity, model_worktree=path)
    native('check-ref-format', source)
    native('check-ref-format', target)
    if native('for-each-ref', '--format=%(refname)', source):
        raise Blocked('source branch already exists; inspect retained worktree before resuming')
    parent = native('rev-parse', '--verify', target + '^{commit}')
    tree = native('rev-parse', '--verify', parent + '^{tree}')
    manifest, contents = _read_regular_tree(controller, controller.root, parent)
    metadata = _metadata(controller.common)
    if any(name.endswith('.lock') for name in metadata):
        raise Blocked('preexisting native Git lock requires reconciliation before worktree creation')
    if policy_check(controller, controller.root) != before:
        raise Blocked('repository policy changed before worktree creation')
    if native('rev-parse', '--verify', target + '^{commit}') != parent:
        raise Blocked('target moved before worktree creation')
    owner.mkdir(exist_ok=True)
    journal_root = controller.common / 'harness-controller-commits/worktree-intents'
    if journal_root.is_symlink():
        raise Blocked('unsafe worktree intent directory')
    journal_root.mkdir(mode=0o700, exist_ok=True)
    journal = journal_root / (uuid.uuid4().hex + '.json')
    record = {'schema_version': _VERSION, 'actor': 'controller', 'phase': 'intent',
              'source_ref': source, 'target_ref': target, 'parent': parent, 'tree': tree,
              'worktree': str(path), 'task_sha256': _digest(task), 'config_sha256': _digest(config),
              'manifest_sha256': _digest(manifest), 'hook_guard': guard_identity}
    atomic_json(journal, record)
    try:
        # --no-checkout avoids native file conversion and post-checkout execution.
        native('worktree', 'add', '--no-checkout', '-b', source.removeprefix('refs/heads/'), str(path), parent)
        record['phase'] = 'branch_created'
        atomic_json(journal, record)
        fresh = policy_check(controller, path)
        if fresh['head'] != parent or fresh['ref'] != source or fresh['staged']:
            raise Blocked('new task worktree index/ref changed before materialization')
        for name, content in contents.items():
            _check_deadline()
            destination = path.joinpath(*name.split('/'))
            cursor = path
            for part in name.split('/')[:-1]:
                cursor = cursor / part
                if cursor.is_symlink():
                    raise Blocked('task directory changed during raw materialization')
                cursor.mkdir(exist_ok=True)
                if not cursor.is_dir():
                    raise Blocked('task file/directory collision; preserve existing files')
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
            fd = os.open(destination, flags, 0o755 if manifest[name]['mode'] == '100755' else 0o644)
            with os.fdopen(fd, 'wb') as stream:
                stream.write(content); stream.flush(); os.fsync(stream.fileno())
        native('read-tree', parent, cwd=path)
        actual = policy_check(controller, path)
        if (actual['head'] != parent or actual['ref'] != source or actual['tree'] != tree
                or _tree(actual['staged']) != _content(manifest)
                or native('write-tree', cwd=path) != tree
                or _worktree(controller, path, len(parent)) != manifest
                or native('rev-parse', '--verify', target + '^{commit}') != parent
                or policy_check(controller, controller.root) != before):
            raise Blocked('raw task worktree does not match pinned target and policy')
        after = _metadata(controller.common)
        gitdir = str(Path(actual['gitdir']).resolve().relative_to(controller.common.resolve())) + '/'
        if any(name.startswith(gitdir) for name in metadata):
            raise Blocked('native worktree metadata directory was not fresh')
        mutable = {source, 'logs/' + source} | {name for name in after if name.startswith(gitdir)}
        _unchanged_metadata(metadata, after, mutable=mutable)
        _hook_guard(controller, path, guard_identity)
        record['phase'] = 'completed'
        atomic_json(journal, record)
        return {'actor': 'controller', 'source': task['source'], 'source_ref': source,
                'worktree': str(path), 'path': str(path), 'parent': parent, 'tree': tree}
    except BaseException:
        record['phase'] = 'unknown_or_incomplete'
        atomic_json(journal, record)
        raise


@_budgeted
def prepare(controller, config, task, path, operation_id):
    """Snapshot pristine task branch before starting the implementation model."""
    _enabled(config)
    allowed = _allowed(task, config, (controller.root, path))
    directory = _directory(controller, operation_id)
    if directory.exists():
        raise Blocked('controller commit operation already exists; reconcile exact operation identity')
    for prior_directory in directory.parent.iterdir():
        if prior_directory.name in ('logs', 'empty-hooks', 'worktree-intents') or not prior_directory.is_dir():
            continue
        prior = _load(prior_directory)
        if prior.get('phase') not in ('completed', 'no_change'):
            raise Blocked('prior controller commit operation unresolved; reconcile before model launch')
    path = Path(path).resolve()
    facts = policy_check(controller, path)
    source = _branch_ref(task['source'])
    target = _branch_ref(task['target'], target=True)
    if facts['ref'] != source or source == target:
        raise Blocked('controller commit only accepts the explicit isolated task source branch')
    if facts['entries'] != facts['staged']:
        raise Blocked('preexisting staged changes forbidden')
    for name in allowed:
        cursor = path
        for part in name.split('/'):
            cursor = cursor / part
            if cursor.is_symlink():
                raise Blocked('allowed_paths may not have symlink components')
        if (path / name).is_dir():
            raise Blocked('allowed_paths may not name directories')
    manifest = _worktree(controller, path, len(facts['head']))
    if _content(manifest) != _tree(facts['entries']):
        raise Blocked('preexisting dirty/untracked files forbidden')
    _, guard_identity = _hook_guard(controller, path)
    metadata = _metadata(controller.common)
    if any(name.endswith('.lock') for name in metadata):
        raise Blocked('preexisting native Git lock requires reconciliation before model launch')
    dotgit = _file(path / '.git') if (path / '.git').is_file() else None
    snapshot = {'schema_version': _VERSION, 'operation_id': operation_id, 'actor': 'controller',
        'worktree': str(path), 'common': str(controller.common.resolve()), 'source_ref': source,
        'parent': facts['head'], 'parent_tree': facts['tree'], 'facts': facts, 'hook_guard': guard_identity,
        'allowed_paths': allowed, 'git_environment_sha256': _digest({k: v for k, v in _environment().items() if k.startswith('GIT_')}), 'task_sha256': _digest(task), 'config_sha256': _digest(config),
        'worktree_manifest': manifest, 'metadata': metadata, 'git_entry': dotgit}
    directory.mkdir(mode=0o700)
    _save(directory, {'schema_version': _VERSION, 'snapshot': snapshot, 'phase': 'prepared'})
    return snapshot


def _unchanged_metadata(before, after, *, new_objects=(), mutable=()):
    allowed = {'objects/' + oid[:2] + '/' + oid[2:] for oid in new_objects}
    for name in set(before) | set(after):
        if name in mutable:
            continue
        if before.get(name) != after.get(name) and not (name not in before and name in allowed):
            raise Blocked('repository metadata changed during controller commit: ' + name)


class _NoChange(Blocked):
    pass


def _audit(controller, config, task, path, snapshot, *, objects=(), expected_manifest=None):
    path = _binding(controller, config, task, path, snapshot)
    _hook_guard(controller, path, snapshot['hook_guard'])
    facts = policy_check(controller, path)
    if facts != snapshot['facts']:
        raise Blocked('model/external HEAD, index, config, hooks or repository identity changed')
    if snapshot['git_entry'] is not None and _file(path / '.git') != snapshot['git_entry']:
        raise Blocked('worktree Git link changed')
    _unchanged_metadata(snapshot['metadata'], _metadata(controller.common), new_objects=objects)
    manifest = _worktree(controller, path, len(snapshot['parent']))
    changed = sorted(name for name in set(manifest) | set(snapshot['worktree_manifest'])
                     if manifest.get(name) != snapshot['worktree_manifest'].get(name))
    if not changed:
        raise _NoChange('no changed files; source branch remains unchanged')
    if not set(changed).issubset(snapshot['allowed_paths']):
        raise Blocked('changes outside explicit allowed_paths')
    if expected_manifest is not None and manifest != expected_manifest:
        raise Blocked('worktree bytes changed after controller audit')
    return manifest, changed


def _object_manifest(controller, path, tree):
    raw = _run(controller, path, ['git', '-C', str(path), 'ls-tree', '-rz', '-t', '--full-tree', tree])
    entries, objects = {}, {tree}
    for row in raw.split(b'\0'):
        if not row:
            continue
        meta, name = row.split(b'\t', 1)
        mode, kind, oid = meta.decode().split()
        objects.add(oid)
        if kind != 'tree':
            entries[name.decode('utf-8')] = {'mode': mode, 'oid': oid}
    return entries, objects


def _verify_blobs(controller, path, manifest):
    rows = sorted(manifest.items())
    raw = _run(controller, path, ['git', '-C', str(path), 'cat-file', '--batch'],
               input_text=''.join(row['oid'] + '\n' for _, row in rows))
    position = 0
    for name, row in rows:
        end = raw.find(b'\n', position)
        if end < 0 or raw[position:end] != (row['oid'] + ' blob ' + str(row['size'])).encode():
            raise Blocked('native blob header differs from audited manifest')
        position = end + 1
        content = raw[position:position + row['size']]
        position += row['size']
        if (len(content) != row['size'] or raw[position:position+1] != b'\n'
                or hashlib.sha256(content).hexdigest() != row['sha256']):
            raise Blocked('native blob bytes differ from audited manifest: ' + name)
        position += 1
    if position != len(raw):
        raise Blocked('unexpected native blob output')


def _record_unknown(directory, operation, phase):
    operation['phase'] = phase
    _save(directory, operation)


@_budgeted
def commit(controller, config, task, path, snapshot):
    """Create exact audited objects, then CAS task source; never retry this ID."""
    path = _binding(controller, config, task, path, snapshot)
    directory = _directory(controller, snapshot['operation_id'])
    operation = _load(directory)
    if operation['snapshot'] != snapshot or operation.get('phase') != 'prepared':
        raise Blocked('commit operation already attempted or snapshot changed; reconcile only')
    try:
        manifest, changed = _audit(controller, config, task, path, snapshot)
    except _NoChange:
        operation['phase'] = 'no_change'
        _save(directory, operation)
        raise
    operation.update(phase='object_intent', manifest=manifest, changed_paths=changed,
                     actor='controller', parent=snapshot['parent'], source_ref=snapshot['source_ref'])
    _save(directory, operation)  # Durable before any object or ref mutation.
    index = directory / 'audited.index'
    objects = set()
    try:
        _git(controller, path, 'read-tree', snapshot['parent'], index=index, guard_identity=snapshot['hook_guard'])
        for number, name in enumerate(changed):
            if name not in manifest:
                _git(controller, path, 'update-index', '--force-remove', '--', name, index=index, guard_identity=snapshot['hook_guard'])
                continue
            raw, mode = _regular(path / name)
            if hashlib.sha256(raw).hexdigest() != manifest[name]['sha256']:
                raise Blocked('worktree changed before blob capture')
            blob = directory / ('blob-' + str(number))
            with blob.open('xb') as stream:
                stream.write(raw); stream.flush(); os.fsync(stream.fileno())
            oid = _git(controller, path, 'hash-object', '-w', '--no-filters', '--', str(blob), guard_identity=snapshot['hook_guard'])
            if oid != manifest[name]['oid']:
                raise Blocked('native blob differs from audited bytes')
            objects.add(oid)
            _git(controller, path, 'update-index', '--add', '--cacheinfo',
                 manifest[name]['mode'], oid, name, index=index, guard_identity=snapshot['hook_guard'])
        tree = _git(controller, path, 'write-tree', index=index, guard_identity=snapshot['hook_guard'])
        entries, tree_objects = _object_manifest(controller, path, tree)
        objects.update(tree_objects)
        if entries != _content(manifest):
            raise Blocked('native tree differs from exact audited manifest')
        _audit(controller, config, task, path, snapshot, objects=objects, expected_manifest=manifest)
        operation.update(phase='commit_tree_intent', tree=tree, object_ids=sorted(objects),
                         audited_index=_file(index))
        _save(directory, operation)
        message = 'Controller task ' + str(task['id']) + '\n\nOperation: ' + snapshot['operation_id'] + '\n'
        oid = _git(controller, path, 'commit-tree', tree, '-p', snapshot['parent'], input_text=message, guard_identity=snapshot['hook_guard'])
        if not _OID.fullmatch(oid):
            raise Blocked('commit-tree result unknown')
        objects.add(oid)
        operation.update(phase='object_created', commit=oid, object_ids=sorted(objects))
        _save(directory, operation)
        _verify_blobs(controller, path, manifest)
        _audit(controller, config, task, path, snapshot, objects=objects, expected_manifest=manifest)
        operation['phase'] = 'cas_intent'
        _save(directory, operation)  # expectedOld is part of this immutable identity.
        _git(controller, path, 'update-ref', '--no-deref', '-m',
             'harness controller commit ' + snapshot['operation_id'], snapshot['source_ref'], oid, snapshot['parent'], guard_identity=snapshot['hook_guard'])
    except BaseException:
        phase = operation.get('phase', 'object_intent')
        _record_unknown(directory, operation, 'cas_unknown' if phase == 'cas_intent' else 'object_unknown')
        raise
    operation['phase'] = 'ref_updated'
    _save(directory, operation)
    return recover_index(controller, config, task, path, snapshot['operation_id'])


def _post_ref_audit(controller, config, task, path, operation, *, permit_synced_index=False, owned_index_lock=None):
    snapshot = operation['snapshot']
    path = _binding(controller, config, task, path, snapshot)
    _hook_guard(controller, path, snapshot['hook_guard'])
    facts = policy_check(controller, path)
    old = snapshot['facts']
    if (facts['head'] != operation.get('commit') or facts['ref'] != snapshot['source_ref']
            or facts['tree'] != operation.get('tree') or facts['parents'] != [snapshot['parent']]):
        raise Blocked('actual source ref is not the exact controller commit')
    for name in ('common','gitdir','hooks','index','config_sha256','config_origins','policy_files','hook_files','author_identity_sha256','committer_identity_sha256'):
        if facts[name] != old[name]:
            raise Blocked('repository policy/provenance changed after CAS')
    _verify_blobs(controller, path, operation['manifest'])
    if _tree(facts['entries']) != _content(operation['manifest']):
        raise Blocked('committed tree differs from audited manifest')
    if _worktree(controller, path, len(snapshot['parent'])) != operation['manifest']:
        raise Blocked('worktree changed after CAS; preserve files and reconcile')
    staged = _tree(facts['staged'])
    if staged != _tree(old['staged']) and not (permit_synced_index and staged == _content(operation['manifest'])):
        raise Blocked('actual index changed after CAS')
    if snapshot['git_entry'] is not None and _file(path / '.git') != snapshot['git_entry']:
        raise Blocked('worktree Git link changed after CAS')
    common = controller.common.resolve()
    ref = snapshot['source_ref']
    gitdir = Path(old['gitdir']).resolve()
    mutable = {ref, 'logs/' + ref, str((gitdir / 'logs/HEAD').relative_to(common))}
    if permit_synced_index:
        actual_index = _file(Path(old['index']))
        original_index = snapshot['metadata'][str(Path(old['index']).resolve().relative_to(common))]
        if operation['phase'] != 'completed' and actual_index not in (original_index, operation['audited_index']):
            raise Blocked('actual index bytes changed after CAS')
        mutable.add(str(Path(old['index']).resolve().relative_to(common)))
    if owned_index_lock is not None:
        mutable.add(str(Path(owned_index_lock).relative_to(common)))
    _unchanged_metadata(snapshot['metadata'], _metadata(common),
                        new_objects=operation['object_ids'], mutable=mutable)
    return facts


@_budgeted
def reconcile(controller, config, task, path, operation_id):
    """Read actual outcome only. Never creates objects, retries CAS, or syncs index."""
    directory = _directory(controller, operation_id)
    operation = _load(directory)
    snapshot = operation['snapshot']
    path = _binding(controller, config, task, path, snapshot)
    try:
        facts = policy_check(controller, path)
    except Blocked as exc:
        raw_head = _run(controller, path, ['git', '-C', str(path), 'rev-parse', '--verify', snapshot['source_ref']]).decode().strip()
        return {'actor': 'controller', 'operation_id': operation_id, 'phase': operation['phase'],
                'status': 'blocked', 'reason': str(exc), 'observed_head': raw_head,
                'source_ref': snapshot['source_ref'], 'parent': snapshot['parent'],
                'commit': operation.get('commit'), 'tree': operation.get('tree')}
    result = {'actor': 'controller', 'operation_id': operation_id, 'phase': operation['phase'],
              'parent': snapshot['parent'], 'source_ref': snapshot['source_ref'],
              'worktree': snapshot['worktree'], 'common': snapshot['common'], 'observed_head': facts['head']}
    if not operation.get('commit'):
        return dict(result, status=({'prepared': 'edit_pending', 'no_change': 'no_change'}.get(operation['phase'], 'blocked')),
                    reason='edits not committed' if operation['phase'] == 'prepared' else 'object outcome unknown; no ref retry permitted')
    if facts['head'] != operation['commit']:
        return dict(result, status='blocked', reason='CAS not proven; current ref differs from recorded commit')
    try:
        _post_ref_audit(controller, config, task, path, operation, permit_synced_index=True)
    except Blocked as exc:
        return dict(result, status='blocked', reason=str(exc))
    synced = _tree(facts['staged']) == _content(operation['manifest'])
    return dict(result, status='committed' if synced else 'index_sync_required',
                commit=operation['commit'], H=operation['commit'], tree=operation['tree'],
                changed_paths=operation['changed_paths'], blobs=operation['manifest'], index_synced=synced)


def _recover_owned_index_lock(controller, directory, operation):
    record = operation.get('index_lock')
    if not record:
        return
    expected = Path(operation['snapshot']['facts']['index']).with_name('index.lock')
    if record.get('path') != str(expected):
        raise Blocked('recorded index lock identity damaged')
    try:
        info = expected.lstat()
    except FileNotFoundError:
        return
    if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
            or (info.st_dev, info.st_ino) != (record.get('device'), record.get('inode'))):
        raise Blocked('index lock has another owner; do not remove')
    from .runtime import owned
    if owned(record.get('owner', {})) is not None:
        raise Blocked('index sync owner still alive; do not remove lock')
    # Controller.run_lock is held and the exact recorded creator is proven dead.
    # Removing only this inode cannot discard another native Git writer's lock.
    expected.unlink()
    operation.pop('index_lock', None)
    _save(directory, operation)


@_budgeted
def recover_index(controller, config, task, path, operation_id):
    """Sync only the already-proven exact tree, without touching worktree files."""
    directory = _directory(controller, operation_id)
    operation = _load(directory)
    _binding(controller, config, task, path, operation['snapshot'])
    _recover_owned_index_lock(controller, directory, operation)
    result = reconcile(controller, config, task, path, operation_id)
    if result['status'] not in ('committed', 'index_sync_required'):
        raise Blocked(result['reason'])
    facts = _post_ref_audit(controller, config, task, path, operation, permit_synced_index=True)
    if result['status'] == 'index_sync_required':
        # Preserve the original actual index until CAS has definitely succeeded.
        # A dedicated lock plus atomic replace prevents overwriting another Git
        # index writer. read-tree affects a separate index, never worktree bytes.
        actual = Path(facts['index'])
        lock = actual.with_name(actual.name + '.lock')
        if _file(directory / 'audited.index') != operation['audited_index']:
            raise Blocked('audited alternate index changed before recovery')
        raw, _ = _regular(directory / 'audited.index')
        operation['phase'] = 'index_sync_intent'
        _save(directory, operation)
        owned_lock = None
        try:
            _check_deadline()
            with lock.open('xb') as stream:
                info = os.fstat(stream.fileno())
                owned_lock = (info.st_dev, info.st_ino)
                from .runtime import identity
                import psutil
                operation['index_lock'] = {'path': str(lock), 'device': info.st_dev, 'inode': info.st_ino,
                                           'owner': identity(psutil.Process())}
                _save(directory, operation)
                _post_ref_audit(controller, config, task, path, operation, permit_synced_index=True, owned_index_lock=lock)
                stream.write(raw); stream.flush(); os.fsync(stream.fileno())
            _check_deadline()
            os.replace(lock, actual)
            dfd = os.open(actual.parent, os.O_RDONLY)
            try: os.fsync(dfd)
            finally: os.close(dfd)
        except FileExistsError as exc:
            raise Blocked('actual index lock busy; preserve successful ref and recover later') from exc
        finally:
            # On caught failure remove only the exact inode we exclusively made.
            # A crash retains the lock for explicit, fact-based reconciliation.
            if owned_lock is not None:
                try:
                    info = lock.lstat()
                    if (info.st_dev, info.st_ino) == owned_lock:
                        lock.unlink()
                except FileNotFoundError:
                    pass
    _post_ref_audit(controller, config, task, path, operation, permit_synced_index=True)
    operation.pop('index_lock', None)
    operation['phase'] = 'completed'
    _save(directory, operation)
    return dict(result, status='committed', phase='completed', index_synced=True)
