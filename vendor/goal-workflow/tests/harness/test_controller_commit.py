"""Restricted commit boundary tests using native Git, with no real model or API."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'skills/harness-init/assets/project'))
from harness.controller_commit import prepare, commit, reconcile, recover_index, policy_check
from harness.runtime import Controller
from harness.state import Blocked


def git(path, *args):
    return subprocess.check_output(['git', '-C', str(path), *args], text=True, stderr=subprocess.PIPE).strip()


class RestrictedCommit(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / 'repo'
        self.root.mkdir()
        git(self.root, 'init', '-b', 'main')
        git(self.root, 'config', 'user.name', 'Fixture')
        git(self.root, 'config', 'user.email', 'fixture@example.invalid')
        (self.root / '.gitignore').write_text('.loop-state.json\n')
        (self.root / 'allowed.txt').write_text('old\n')
        (self.root / 'other.txt').write_text('untouched\n')
        git(self.root, 'add', '.')
        git(self.root, 'commit', '-m', 'base')
        self.path = Path(self.tmp.name) / 'source'
        git(self.root, 'worktree', 'add', '-b', 'task', str(self.path))
        self.config = {'host': {'commit_mode': 'controller_commit'}}
        self.task = {'id': 'T1', 'source': 'task', 'target': 'main', 'allowed_paths': ['allowed.txt', 'new.bin']}
        self.controller = Controller(self.root, 'local', 'commit-test', {'command_seconds': 5,
            'total_seconds': 200, 'max_attempts': 500, 'stop_grace_seconds': .2})
        self.controller.__enter__()
        self.head = git(self.path, 'rev-parse', 'HEAD')
        self.index = Path(git(self.path, 'rev-parse', '--path-format=absolute', '--git-path', 'index'))
        self.original_index = self.index.read_bytes()

    def tearDown(self):
        self.controller.__exit__(None, None, None)
        self.tmp.cleanup()

    def prepare(self):
        return prepare(self.controller, self.config, self.task, self.path, 'op-one')

    def commit(self, snapshot):
        return commit(self.controller, self.config, self.task, self.path, snapshot)

    def test_exact_binary_manifest_and_index_sync(self):
        snap = self.prepare()
        (self.path / 'allowed.txt').write_bytes(b'new\x00\xff\r\n')
        (self.path / 'new.bin').write_bytes(bytes(range(256)))
        receipt = self.commit(snap)
        self.assertEqual(receipt['actor'], 'controller')
        self.assertEqual(receipt['parent'], self.head)
        self.assertEqual(receipt['status'], 'committed')
        self.assertEqual(git(self.path, 'rev-parse', 'HEAD^'), self.head)
        self.assertEqual(git(self.root, 'rev-parse', 'main'), self.head)
        self.assertEqual(git(self.path, 'status', '--porcelain'), '')
        self.assertEqual(subprocess.check_output(['git','-C',str(self.path),'show','HEAD:allowed.txt']), b'new\x00\xff\r\n')
        self.assertEqual(receipt['blobs']['new.bin']['oid'], git(self.path, 'rev-parse', 'HEAD:new.bin'))
        attempts = self.controller.state.read()['attempts']
        native = []
        for item in attempts:
            if item['argv'][0] != 'git':
                continue
            args = item['argv'][3:]
            while args[:1] == ['-c']:
                args = args[2:]
            native.append(args)
        self.assertTrue(any(args[:1]==['commit-tree'] for args in native))
        cas = next(args for args in native if args[:1]==['update-ref'])
        self.assertEqual(cas[-3:], ['refs/heads/task', receipt['commit'], self.head])
        self.assertFalse(any(args[:1] in (['commit'], ['add']) for args in native))

    def test_deletion_and_executable_mode(self):
        snap = self.prepare()
        (self.path / 'allowed.txt').unlink()
        (self.path / 'new.bin').write_text('#!/bin/sh\nexit 0\n')
        (self.path / 'new.bin').chmod(0o755)
        self.commit(snap)
        self.assertEqual(git(self.path, 'ls-tree', 'HEAD', 'new.bin').split()[0], '100755')
        self.assertEqual(git(self.path, 'ls-tree', 'HEAD', 'allowed.txt'), '')
        self.assertEqual(git(self.path, 'status', '--porcelain'), '')

    def test_preexisting_dirty_or_staged_rejected(self):
        (self.path / 'allowed.txt').write_text('prior')
        with self.assertRaisesRegex(Blocked, 'preexisting dirty'):
            self.prepare()
        git(self.path, 'add', 'allowed.txt')
        with self.assertRaisesRegex(Blocked, 'staged'):
            self.prepare()

    def test_unauthorized_path_rejected_without_ref_or_index_change(self):
        snap = self.prepare()
        (self.path / 'other.txt').write_text('not allowed')
        with self.assertRaisesRegex(Blocked, 'outside'):
            self.commit(snap)
        self.assertEqual(git(self.path, 'rev-parse', 'HEAD'), self.head)
        self.assertEqual(self.index.read_bytes(), self.original_index)

    def test_executable_hook_filter_signing_and_fsmonitor_rejected_before_execution(self):
        hook = self.root / '.git/hooks/reference-transaction'
        marker = self.root / 'HOOK-RAN'
        hook.write_text('#!/bin/sh\ntouch ' + str(marker) + '\n')
        hook.chmod(0o755)
        with self.assertRaisesRegex(Blocked, 'hook'):
            self.prepare()
        self.assertFalse(marker.exists())
        hook.unlink()
        for key, value, message in [('filter.test.clean','touch '+str(marker),'filter'),
                ('commit.gpgsign','true','signing'),('core.fsmonitor','touch '+str(marker),'executable')]:
            git(self.root, 'config', key, value)
            with self.assertRaisesRegex(Blocked, message):
                self.prepare()
            git(self.root, 'config', '--unset', key)
            self.assertFalse(marker.exists())

    def test_model_head_index_and_config_changes_rejected(self):
        snap = self.prepare()
        (self.path / 'allowed.txt').write_text('new')
        git(self.path, 'add', 'allowed.txt')
        with self.assertRaisesRegex(Blocked, 'index'):
            self.commit(snap)
        self.assertEqual(git(self.path, 'rev-parse', 'HEAD'), self.head)

    def test_symlink_rejected(self):
        snap = self.prepare()
        (self.path / 'allowed.txt').unlink()
        (self.path / 'allowed.txt').symlink_to(self.path / 'other.txt')
        with self.assertRaisesRegex(Blocked, 'regular'):
            self.commit(snap)
        self.assertEqual(git(self.path, 'rev-parse', 'HEAD'), self.head)

    def test_unknown_commit_tree_never_moves_ref_or_retries(self):
        snap = self.prepare()
        (self.path / 'allowed.txt').write_text('new')
        original = self.controller.execute
        calls = []
        def execute(argv, *args, **kwargs):
            result = original(argv, *args, **kwargs)
            if argv[0]=='git' and 'commit-tree' in argv[3:]:
                calls.append(argv)
                raise Blocked('lost commit-tree receipt')
            return result
        with patch.object(self.controller, 'execute', side_effect=execute):
            with self.assertRaises(Blocked): self.commit(snap)
            with self.assertRaises(Blocked): self.commit(snap)
        self.assertEqual(len(calls), 1)
        self.assertEqual(git(self.path, 'rev-parse', 'HEAD'), self.head)
        self.assertEqual(self.index.read_bytes(), self.original_index)
        result = reconcile(self.controller,self.config,self.task,self.path,'op-one')
        self.assertEqual(result['status'], 'blocked')
        with self.assertRaisesRegex(Blocked, 'unresolved'):
            prepare(self.controller,self.config,self.task,self.path,'op-two')

    def test_unknown_cas_reconciles_read_only_then_exact_index_recovery(self):
        snap = self.prepare()
        (self.path / 'allowed.txt').write_text('new')
        original = self.controller.execute
        calls = []
        def execute(argv, *args, **kwargs):
            result = original(argv, *args, **kwargs)
            if argv[0]=='git' and 'update-ref' in argv[3:]:
                calls.append(argv)
                raise Blocked('lost CAS receipt')
            return result
        with patch.object(self.controller, 'execute', side_effect=execute):
            with self.assertRaises(Blocked): self.commit(snap)
        self.assertNotEqual(git(self.path, 'rev-parse', 'HEAD'), self.head)
        self.assertEqual(self.index.read_bytes(), self.original_index)
        result = reconcile(self.controller,self.config,self.task,self.path,'op-one')
        self.assertEqual(result['status'], 'index_sync_required')
        self.assertEqual(self.index.read_bytes(), self.original_index)
        repaired = recover_index(self.controller,self.config,self.task,self.path,'op-one')
        self.assertEqual(repaired['status'],'committed')
        self.assertEqual(git(self.path,'status','--porcelain'),'')
        again = recover_index(self.controller,self.config,self.task,self.path,'op-one')
        self.assertEqual(again['commit'], repaired['commit'])
        self.assertEqual(len(calls),1)

    def test_post_audit_change_blocks_cas_and_preserves_index(self):
        snap = self.prepare()
        (self.path / 'allowed.txt').write_text('new')
        original = self.controller.execute
        def execute(argv, *args, **kwargs):
            result = original(argv, *args, **kwargs)
            if argv[0]=='git' and 'commit-tree' in argv[3:]:
                (self.path/'allowed.txt').write_text('changed after audit')
            return result
        with patch.object(self.controller,'execute',side_effect=execute):
            with self.assertRaisesRegex(Blocked,'after controller audit'):
                self.commit(snap)
        self.assertEqual(git(self.path,'rev-parse','HEAD'), self.head)
        self.assertEqual(self.index.read_bytes(),self.original_index)


    def test_attribute_and_protected_contract_policy(self):
        for name in ['.gitattributes', '.harness/config.json', 'AGENTS.md', '.agents/rule.md', '.codex/config.toml', '.gitmodules', '.serena/project.yml']:
            task = dict(self.task, allowed_paths=[name])
            with self.assertRaisesRegex(Blocked, 'protected'):
                prepare(self.controller, self.config, task, self.path, 'op-one')
        attr = self.path / '.gitattributes'
        attr.write_text('*.txt text eol=crlf\n')
        with self.assertRaisesRegex(Blocked, 'attributes'):
            self.prepare()
        attr.unlink()
        git(self.root, 'config', 'core.autocrlf', 'true')
        with self.assertRaisesRegex(Blocked, 'transform'):
            self.prepare()

    def test_custom_hookspath_and_symlink_attributes_rejected(self):
        hooks = Path(self.tmp.name) / 'empty'
        hooks.mkdir()
        git(self.root, 'config', 'core.hooksPath', str(hooks))
        with self.assertRaisesRegex(Blocked, 'hooks_path'):
            self.prepare()
        git(self.root, 'config', '--unset', 'core.hooksPath')
        (self.root / '.git/info/attributes').symlink_to(self.path / 'allowed.txt')
        with self.assertRaisesRegex(Blocked, 'symlink'):
            self.prepare()

    def test_final_window_hook_never_executes_and_receipt_blocks(self):
        snap = self.prepare()
        (self.path / 'allowed.txt').write_text('new')
        original = self.controller.execute
        marker = Path(self.tmp.name) / 'HOOK-RAN'
        def execute(argv, *args, **kwargs):
            if argv[0]=='git' and 'update-ref' in argv[3:]:
                hook = self.root / '.git/hooks/reference-transaction'
                hook.write_text('#!/bin/sh\ntouch ' + str(marker) + '\n')
                hook.chmod(0o755)
            return original(argv, *args, **kwargs)
        with patch.object(self.controller,'execute',side_effect=execute):
            with self.assertRaisesRegex(Blocked, 'hook'):
                self.commit(snap)
        self.assertFalse(marker.exists())
        self.assertNotEqual(git(self.path, 'rev-parse', 'HEAD'), self.head)
        self.assertEqual(self.index.read_bytes(), self.original_index)
        result = reconcile(self.controller,self.config,self.task,self.path,'op-one')
        self.assertEqual(result['status'], 'blocked')
        self.assertEqual(result['observed_head'], git(self.path, 'rev-parse', 'HEAD'))

    def test_final_window_worktree_edit_preserved_without_success(self):
        snap = self.prepare()
        (self.path / 'allowed.txt').write_text('new')
        original = self.controller.execute
        def execute(argv, *args, **kwargs):
            if argv[0]=='git' and 'update-ref' in argv[3:]:
                (self.path / 'allowed.txt').write_text('external concurrent write')
            return original(argv, *args, **kwargs)
        with patch.object(self.controller,'execute',side_effect=execute):
            with self.assertRaisesRegex(Blocked, 'worktree changed'):
                self.commit(snap)
        self.assertEqual((self.path/'allowed.txt').read_text(),'external concurrent write')
        self.assertEqual(self.index.read_bytes(),self.original_index)

    def test_actual_index_lock_is_preserved_and_retry_only_syncs(self):
        snap = self.prepare()
        (self.path / 'allowed.txt').write_text('new')
        original = self.controller.execute
        lock = self.index.with_name('index.lock')
        def execute(argv,*args,**kwargs):
            result = original(argv,*args,**kwargs)
            if argv[0]=='git' and 'update-ref' in argv[3:]:
                lock.write_text('external lock owner')
            return result
        with patch.object(self.controller,'execute',side_effect=execute):
            with self.assertRaises(Blocked): self.commit(snap)
        self.assertEqual(lock.read_text(), 'external lock owner')
        lock.unlink()
        result = recover_index(self.controller,self.config,self.task,self.path,'op-one')
        self.assertEqual(result['status'],'committed')

    def test_prepared_reconciliation_does_not_create_commit(self):
        self.prepare()
        result = reconcile(self.controller,self.config,self.task,self.path,'op-one')
        self.assertEqual(result['status'],'edit_pending')
        self.assertEqual(git(self.path,'rev-parse','HEAD'),self.head)

    def test_guard_cannot_be_replaced_with_symlink(self):
        snap = self.prepare()
        (self.path / 'allowed.txt').write_text('new')
        guard = self.root / '.git/harness-controller-commits/empty-hooks'
        target = Path(self.tmp.name) / 'guard-target'
        target.mkdir()
        target.chmod(0o700)
        guard.rmdir()
        guard.symlink_to(target, target_is_directory=True)
        with self.assertRaisesRegex(Blocked,'attest'):
            self.commit(snap)
        self.assertEqual(git(self.path,'rev-parse','HEAD'), self.head)


    def test_model_made_commit_is_not_misattributed_or_reset(self):
        snap = self.prepare()
        (self.path / 'allowed.txt').write_text('model commit')
        git(self.path, 'add', 'allowed.txt')
        git(self.path, 'commit', '-m', 'model bypassed boundary')
        external = git(self.path, 'rev-parse', 'HEAD')
        with self.assertRaisesRegex(Blocked, 'HEAD'):
            self.commit(snap)
        self.assertEqual(git(self.path, 'rev-parse', 'HEAD'), external)

    def test_effectively_identical_config_file_change_still_blocks(self):
        snap = self.prepare()
        (self.path / 'allowed.txt').write_text('new')
        with (self.root / '.git/config').open('a') as stream:
            stream.write('\n# external metadata edit\n')
        with self.assertRaisesRegex(Blocked, 'config'):
            self.commit(snap)
        self.assertEqual(git(self.path, 'rev-parse', 'HEAD'), self.head)

    def test_no_change_is_terminal_without_native_commit(self):
        snap = self.prepare()
        with self.assertRaisesRegex(Blocked, 'no changed'):
            self.commit(snap)
        result = reconcile(self.controller,self.config,self.task,self.path,'op-one')
        self.assertEqual(result['status'], 'no_change')
        prepare(self.controller,self.config,self.task,self.path,'op-two')
        self.assertEqual(git(self.path,'rev-parse','HEAD'),self.head)

    def test_expected_old_cas_rejects_concurrent_branch_writer(self):
        snap = self.prepare()
        (self.path / 'allowed.txt').write_text('new')
        other = git(self.path,'commit-tree',snap['parent_tree'],'-p',self.head,'-m','external concurrent commit')
        # The object is deliberately made after prepare, which is itself drift.
        # Add its exact prior bytes to baseline to isolate just the CAS window.
        from harness.controller_commit import _metadata, _save
        snap['metadata'] = _metadata(self.controller.common)
        directory = self.controller.common / 'harness-controller-commits/op-one'
        _save(directory, {'schema_version':1,'snapshot':snap,'phase':'prepared'})
        original = self.controller.execute
        count = []
        def execute(argv,*args,**kwargs):
            if argv[0]=='git' and 'update-ref' in argv[3:]:
                count.append(argv)
                git(self.path,'update-ref','refs/heads/task',other,self.head)
            return original(argv,*args,**kwargs)
        with patch.object(self.controller,'execute',side_effect=execute):
            with self.assertRaises(Blocked): self.commit(snap)
        self.assertEqual(git(self.path,'rev-parse','HEAD'),other)
        self.assertEqual(self.index.read_bytes(),self.original_index)
        self.assertEqual(len(count),1)
        result = reconcile(self.controller,self.config,self.task,self.path,'op-one')
        self.assertEqual(result['status'],'blocked')
        with self.assertRaises(Blocked): self.commit(snap)

    def test_journal_symlink_is_not_followed(self):
        snap = self.prepare()
        journal = self.controller.common / 'harness-controller-commits/op-one/operation.json'
        saved = journal.with_name('saved.json')
        journal.rename(saved)
        journal.symlink_to(saved)
        with self.assertRaisesRegex(Blocked, 'regular'):
            self.commit(snap)
        self.assertEqual(git(self.path,'rev-parse','HEAD'),self.head)

    def test_guard_content_changed_after_cas_blocks_success(self):
        snap = self.prepare()
        (self.path / 'allowed.txt').write_text('new')
        original = self.controller.execute
        def execute(argv,*args,**kwargs):
            result = original(argv,*args,**kwargs)
            if argv[0]=='git' and 'update-ref' in argv[3:]:
                guard = self.controller.common / 'harness-controller-commits/empty-hooks'
                (guard / 'unexpected').write_text('external')
            return result
        with patch.object(self.controller,'execute',side_effect=execute):
            with self.assertRaisesRegex(Blocked,'attest'):
                self.commit(snap)
        self.assertNotEqual(git(self.path,'rev-parse','HEAD'),self.head)
        self.assertEqual(self.index.read_bytes(),self.original_index)
        result = reconcile(self.controller,self.config,self.task,self.path,'op-one')
        self.assertEqual(result['status'],'blocked')

    def test_case_colliding_and_nonportable_paths_rejected(self):
        for paths in [['Allowed.txt','allowed.txt'], ['file*'], ['a/../b'], ['NUL.txt'], ['bad.'], ['a/'], ['file\x7f']]:
            with self.subTest(paths=paths):
                task = dict(self.task, allowed_paths=paths)
                with self.assertRaises(Blocked):
                    prepare(self.controller,self.config,task,self.path,'op-one')

    def test_ambient_environment_drift_and_redirects_rejected(self):
        snap = self.prepare()
        (self.path / 'allowed.txt').write_text('new')
        with patch.dict(os.environ, {'GIT_AUTHOR_EMAIL':'external@example.invalid'}):
            with self.assertRaisesRegex(Blocked, 'provenance'):
                self.commit(snap)
        with patch.dict(os.environ, {'GIT_INDEX_FILE':str(self.index)}):
            with self.assertRaisesRegex(Blocked, 'environment'):
                self.commit(snap)
        self.assertEqual(self.index.read_bytes(),self.original_index)

    def test_native_audits_consume_same_cumulative_budget(self):
        self.prepare()
        state = self.controller.state.read()
        self.assertGreater(state['controller_audit_seconds'], 0)
        self.assertGreater(state['spent_seconds'], state['controller_audit_seconds'])
        self.assertTrue(all(attempt['stopped'] for attempt in state['attempts']))

    def test_changed_alternate_index_never_overwrites_actual_index(self):
        snap = self.prepare()
        (self.path / 'allowed.txt').write_text('new')
        original = self.controller.execute
        def execute(argv,*args,**kwargs):
            result = original(argv,*args,**kwargs)
            if argv[0]=='git' and 'update-ref' in argv[3:]:
                raise Blocked('lost CAS receipt')
            return result
        with patch.object(self.controller,'execute',side_effect=execute):
            with self.assertRaises(Blocked): self.commit(snap)
        alternate = self.controller.common / 'harness-controller-commits/op-one/audited.index'
        alternate.write_bytes(b'corrupted')
        with self.assertRaisesRegex(Blocked, 'alternate index changed'):
            recover_index(self.controller,self.config,self.task,self.path,'op-one')
        self.assertEqual(self.index.read_bytes(),self.original_index)


    def test_crashed_index_sync_recovers_only_recorded_dead_owner_lock(self):
        snap = self.prepare()
        (self.path / 'allowed.txt').write_text('new')
        original = self.controller.execute
        def execute(argv,*args,**kwargs):
            result = original(argv,*args,**kwargs)
            if argv[0]=='git' and 'update-ref' in argv[3:]:
                raise Blocked('lost CAS receipt')
            return result
        with patch.object(self.controller,'execute',side_effect=execute):
            with self.assertRaises(Blocked): self.commit(snap)
        from harness.runtime import identity
        import psutil
        process = subprocess.Popen([sys.executable,'-c','import time;time.sleep(.2)'])
        owner = identity(psutil.Process(process.pid))
        process.wait(timeout=3)
        lock = self.index.with_name('index.lock')
        lock.write_bytes(b'partial interrupted index')
        info = lock.stat()
        journal = self.controller.common / 'harness-controller-commits/op-one/operation.json'
        operation = json.loads(journal.read_text())
        operation['phase'] = 'index_sync_intent'
        operation['index_lock'] = {'path':str(lock),'device':info.st_dev,'inode':info.st_ino,'owner':owner}
        journal.write_text(json.dumps(operation))
        observed = reconcile(self.controller,self.config,self.task,self.path,'op-one')
        self.assertEqual(observed['status'],'blocked')
        self.assertTrue(lock.exists())
        result = recover_index(self.controller,self.config,self.task,self.path,'op-one')
        self.assertEqual(result['status'],'committed')
        self.assertFalse(lock.exists())
        self.assertEqual(git(self.path,'status','--porcelain'),'')


    def test_checker_and_spec_path_aliases_are_protected_before_host(self):
        aliases = ['./allowed.txt', 'nested/../allowed.txt', str(self.root/'allowed.txt'),
                   str(self.path/'allowed.txt'), '--script=./allowed.txt']
        for alias in aliases:
            with self.subTest(alias=alias):
                config = dict(self.config, checks=[{'id':'checker','argv':[sys.executable,alias]}])
                with self.assertRaisesRegex(Blocked,'checker/spec'):
                    prepare(self.controller,config,self.task,self.path,'op-one')
        task = dict(self.task,spec='./allowed.txt')
        with self.assertRaisesRegex(Blocked,'checker/spec'):
            prepare(self.controller,self.config,task,self.path,'op-one')

    def test_native_call_is_not_started_after_outer_deadline(self):
        import time
        from harness.controller_commit import _run, _DEADLINE
        token = _DEADLINE.set(time.monotonic()-1)
        try:
            with patch.object(self.controller,'execute') as execute:
                with self.assertRaisesRegex(Blocked,'budget_exhausted'):
                    _run(self.controller,self.path,['git','-C',str(self.path),'rev-parse','HEAD'])
                execute.assert_not_called()
        finally:
            _DEADLINE.reset(token)
        self.assertEqual(git(self.path,'rev-parse','HEAD'),self.head)

    def test_preexisting_native_lock_blocks_prepare(self):
        lock = self.index.with_name('index.lock')
        lock.write_text('existing native writer')
        with self.assertRaisesRegex(Blocked,'preexisting native Git lock'):
            self.prepare()
        self.assertEqual(lock.read_text(),'existing native writer')
        self.assertEqual(git(self.path,'rev-parse','HEAD'),self.head)

    def test_identity_is_real_bound_and_mutation_guards_are_local(self):
        snap = self.prepare()
        self.assertEqual(len(snap['facts']['author_identity_sha256']),64)
        self.assertEqual(len(snap['facts']['committer_identity_sha256']),64)
        (self.path/'allowed.txt').write_text('ordinary update')
        self.commit(snap)
        attempts = self.controller.state.read()['attempts']
        for item in attempts:
            argv = item['argv']
            if argv[0]=='git' and argv[3:4]==['-c']:
                self.assertIn('core.fsmonitor=false',argv)
                self.assertIn('commit.gpgsign=false',argv)
        self.assertEqual(git(self.root,'config','--get-regexp',r'^user\.'),'user.name Fixture\nuser.email fixture@example.invalid')


    def test_no_checkout_worktree_materializes_nested_binary_executable_target(self):
        from harness.controller_commit import add_task_worktree
        directory = self.root / 'nested'
        directory.mkdir()
        (directory/'data.bin').write_bytes(bytes(range(256)))
        (directory/'run.sh').write_text('#!/bin/sh\nexit 0\n')
        (directory/'run.sh').chmod(0o755)
        git(self.root,'add','nested/data.bin','nested/run.sh')
        git(self.root,'commit','-m','ordinary nested target fixture')
        parent = git(self.root,'rev-parse','HEAD')
        path = self.controller.common / 'harness-worktrees/new-controller-task'
        task = dict(self.task,source='new-controller-task')
        result = add_task_worktree(self.controller,self.config,task,path)
        self.assertEqual(result['parent'],parent)
        self.assertEqual(git(path,'rev-parse','HEAD'),parent)
        self.assertEqual(git(path,'status','--porcelain'),'')
        self.assertEqual((path/'nested/data.bin').read_bytes(),bytes(range(256)))
        self.assertTrue((path/'nested/run.sh').stat().st_mode & 0o111)
        self.assertEqual(git(self.root,'rev-parse','main'),parent)
        args = [item['argv'] for item in self.controller.state.read()['attempts']
                if item['argv'][0]=='git' and 'worktree' in item['argv'][3:]]
        self.assertEqual(len(args),1)
        self.assertIn('--no-checkout',args[0])
        snap = prepare(self.controller,self.config,task,path,'created-op')
        (path/'allowed.txt').write_text('ordinary task edit')
        receipt = commit(self.controller,self.config,task,path,snap)
        self.assertEqual(receipt['status'],'committed')
        self.assertEqual(git(path,'status','--porcelain'),'')

    def test_no_checkout_worktree_preserves_existing_destination(self):
        from harness.controller_commit import add_task_worktree
        path = self.controller.common / 'harness-worktrees/existing-task'
        path.mkdir(parents=True)
        (path/'user.txt').write_text('preserve this file')
        task = dict(self.task,source='new-controller-task')
        with self.assertRaisesRegex(Blocked,'absent direct'):
            add_task_worktree(self.controller,self.config,task,path)
        self.assertEqual((path/'user.txt').read_text(),'preserve this file')
        self.assertEqual(git(self.root,'for-each-ref','--format=%(refname)','refs/heads/new-controller-task'),'')


    def test_no_checkout_worktree_preserves_explicit_remote_tracking_target(self):
        from harness.controller_commit import add_task_worktree
        target = 'refs/remotes/origin/main'
        git(self.root,'update-ref',target,self.head)
        task = dict(self.task,source='remote-backed-task',target=target)
        path = self.controller.common / 'harness-worktrees/remote-backed-task'
        result = add_task_worktree(self.controller,self.config,task,path)
        self.assertEqual(result['parent'],self.head)
        self.assertEqual(git(path,'symbolic-ref','HEAD'),'refs/heads/remote-backed-task')
        self.assertEqual(git(path,'rev-parse','HEAD'),self.head)
        self.assertEqual(git(path,'status','--porcelain'),'')
        snap = prepare(self.controller,self.config,task,path,'remote-target-op')
        (path/'allowed.txt').write_text('ordinary remote-backed task edit')
        receipt = commit(self.controller,self.config,task,path,snap)
        self.assertEqual(receipt['status'],'committed')
        self.assertEqual(receipt['parent'],self.head)
        self.assertEqual(git(self.root,'rev-parse',target),self.head)
        self.assertEqual(git(self.root,'rev-parse','main'),self.head)
        self.assertFalse(any(row['argv'][0]=='git' and any(verb in row['argv'][3:] for verb in ('fetch','push'))
                             for row in self.controller.state.read()['attempts']))


if __name__ == '__main__': unittest.main(verbosity=2)
