"""Source publication integration tests: real temporary/bare Git, no network."""
import copy
import json
import os
from pathlib import Path
import subprocess
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'skills/harness-init/assets/project'))
from harness import git_transport
from harness.git_transport import push_source, remote_fingerprint, query_remote_ref
from harness.runtime import Controller
from harness.state import Blocked

LIMITS = {'command_seconds': 5, 'total_seconds': 90,
          'max_attempts': 150, 'stop_grace_seconds': 0.3}


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True,
                                   stderr=subprocess.DEVNULL).strip()


class SourcePushTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='harness-source-tests-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'source'
        self.root.mkdir()
        git(self.root, 'init', '-b', 'main')
        git(self.root, 'config', 'user.name', 'Fixture')
        git(self.root, 'config', 'user.email', 'fixture@example.invalid')
        (self.root / '.gitignore').write_text('.loop-state.json\n')
        (self.root / 'base.txt').write_text('base\n')
        self.base = self.commit('base')
        git(self.root, 'checkout', '-b', 'feature')
        (self.root / 'feature.txt').write_text('feature\n')
        self.head = self.commit('feature')
        self.remote = Path(self.tmp.name) / 'remote.git'
        self.remote.mkdir()
        git(self.remote, 'init', '--bare')
        git(self.root, 'remote', 'add', 'origin', str(self.remote))
        self.ref = 'refs/heads/feature'
        self.task_id = 'TASK-source'

    def commit(self, message):
        git(self.root, 'add', '.')
        git(self.root, 'commit', '-m', message)
        return git(self.root, 'rev-parse', 'HEAD')

    def controller(self, **limits):
        return Controller(self.root, 'github', 'source-test', dict(LIMITS, **limits))

    def push(self, controller, head=None, **kwargs):
        return push_source(controller, self.task_id, 'feature', head or self.head,
                           'origin', self.ref, authorized=True, **kwargs)

    def actual(self):
        rows = git(self.root, 'ls-remote', str(self.remote), self.ref).split()
        return rows[0] if rows else None

    def assert_no_delivery_claim(self, result):
        self.assertEqual(result['status'], 'source_published')
        for key in ('verified', 'verified_delivery', 'delivered_sha', 'D', 'pr', 'platform_evidence'):
            self.assertNotIn(key, result)

    def test_first_push_reuse_budget_and_task_status_unchanged(self):
        with self.controller() as controller:
            state = controller.state.read()
            task = {'status': 'local_passed', 'H': self.head, 'local_evidence': 'unchanged'}
            state['tasks'][self.task_id] = copy.deepcopy(task)
            old_op = {'action': 'fixture-history', 'status': 'observed'}
            state['remote_operations'].append(old_op)
            controller.state.write(state, state['revision'])
            original = git_transport._remote
            def inspect(action_controller, action, remote, request):
                if action == 'push':
                    saved = controller.state.read()
                    self.assertEqual(saved['remote_operations'][-1]['status'], 'intent')
                    self.assertIsNone(self.actual())
                return original(action_controller, action, remote, request)
            with patch.object(git_transport, '_remote', side_effect=inspect):
                first = self.push(controller)
            self.assert_no_delivery_claim(first)
            self.assertFalse(first['reused'])
            after = controller.state.read()
            attempts, spent = len(after['attempts']), after['spent_seconds']
            self.assertGreater(attempts, 4)
            self.assertGreater(spent, 0)
            self.assertEqual(after['tasks'][self.task_id], task)
            self.assertEqual(after['remote_operations'][0], old_op)
            again = self.push(controller)
            self.assertTrue(again['reused'])
            self.assert_no_delivery_claim(again)
            final = controller.state.read()
            self.assertGreater(len(final['attempts']), attempts)
            self.assertGreater(final['spent_seconds'], spent)
            self.assertEqual(len(final['remote_operations']), 2)
            self.assertEqual(final['attempts'][:attempts], after['attempts'])
        self.assertEqual(self.actual(), self.head)

    def test_update_requires_recorded_prior_head_and_fast_forward(self):
        with self.controller() as controller:
            self.push(controller)
            prior = copy.deepcopy(controller.state.read()['remote_operations'][0])
            (self.root / 'feature.txt').write_text('feature version two\n')
            updated = self.commit('next feature')
            result = self.push(controller, updated)
            self.assertEqual(self.actual(), updated)
            self.assert_no_delivery_claim(result)
            operations = controller.state.read()['remote_operations']
            self.assertEqual(operations[0], prior)
            self.assertEqual(operations[1]['before'], self.head)
            self.assertEqual(operations[1]['status'], 'observed')

    def test_success_before_checkpoint_is_reconciled_without_second_push(self):
        original = git_transport._save_operation
        def crash(controller, operation_id, **changes):
            if changes.get('status') == 'observed':
                raise SystemExit('simulated crash after external success')
            return original(controller, operation_id, **changes)
        with self.controller() as controller:
            with patch.object(git_transport, '_save_operation', side_effect=crash):
                with self.assertRaises(SystemExit):
                    self.push(controller)
            self.assertEqual(controller.state.read()['remote_operations'][0]['status'], 'intent')
        self.assertEqual(self.actual(), self.head)
        with self.controller() as controller:
            with patch.object(git_transport, '_remote', wraps=git_transport._remote) as called:
                recovered = self.push(controller)
            self.assertTrue(recovered['reused'])
            self.assertNotIn('push', [call.args[1] for call in called.call_args_list])
            self.assertEqual(controller.state.read()['remote_operations'][0]['status'], 'observed')

    def test_push_unknown_without_success_queries_and_never_retries(self):
        original = git_transport._remote
        seen = []
        def fail_push(controller, action, remote, request):
            seen.append(action)
            if action == 'push':
                raise Blocked('simulated uncertain write')
            return original(controller, action, remote, request)
        with self.controller() as controller:
            with patch.object(git_transport, '_remote', side_effect=fail_push):
                with self.assertRaisesRegex(Blocked, 'unknown'):
                    self.push(controller)
                self.assertEqual(seen[-1], 'query')
                with self.assertRaisesRegex(Blocked, 'unresolved'):
                    self.push(controller)
            self.assertEqual(seen.count('push'), 1)
            self.assertEqual(controller.state.read()['remote_operations'][0]['status'], 'unknown')
        self.assertIsNone(self.actual())

    def test_lost_post_push_query_recovers_observed_ref(self):
        original = git_transport._remote
        queries = 0
        def lose_query(controller, action, remote, request):
            nonlocal queries
            if action == 'query':
                queries += 1
                if queries == 2:
                    raise Blocked('simulated lost read')
            return original(controller, action, remote, request)
        with self.controller() as controller:
            with patch.object(git_transport, '_remote', side_effect=lose_query):
                with self.assertRaisesRegex(Blocked, 'unknown'):
                    self.push(controller)
            self.assertEqual(controller.state.read()['remote_operations'][0]['status'], 'unknown')
            result = self.push(controller)
            self.assertTrue(result['reused'])
            self.assertEqual(controller.state.read()['remote_operations'][0]['status'], 'observed')

    def test_unknown_old_head_success_reconciles_before_authorized_update(self):
        with self.controller() as controller:
            self.push(controller)
            state = controller.state.read()
            state['remote_operations'][0]['status'] = 'unknown'
            controller.state.write(state, state['revision'])
            (self.root / 'feature.txt').write_text('next\n')
            updated = self.commit('next')
            self.push(controller, updated)
            operations = controller.state.read()['remote_operations']
            self.assertTrue(operations[0]['reconciled'])
            self.assertEqual(operations[1]['source_sha'], updated)

    def test_unowned_existing_remote_branch_blocks_even_if_ff_possible(self):
        git(self.root, 'push', 'origin', self.base + ':' + self.ref)
        with self.controller() as controller:
            with self.assertRaisesRegex(Blocked, 'unrecognized'):
                self.push(controller)
            self.assertEqual(controller.state.read()['remote_operations'], [])
        self.assertEqual(self.actual(), self.base)

    def test_unknown_external_remote_change_blocks(self):
        with self.controller() as controller:
            self.push(controller)
            (self.root / 'feature.txt').write_text('external\n')
            external = self.commit('external source update')
            git(self.root, 'push', 'origin', external + ':' + self.ref)
            (self.root / 'feature.txt').write_text('requested next\n')
            updated = self.commit('next')
            with self.assertRaisesRegex(Blocked, 'unrecognized'):
                self.push(controller, updated)
        self.assertEqual(self.actual(), external)

    def test_recorded_remote_head_does_not_allow_non_fast_forward(self):
        with self.controller() as controller:
            self.push(controller)
            git(self.root, 'checkout', '-b', 'alternative', self.base)
            (self.root / 'alternative.txt').write_text('alternate\n')
            alternate = self.commit('divergent source')
            git(self.root, 'update-ref', self.ref, alternate)
            with self.assertRaisesRegex(Blocked, 'fast-forward'):
                self.push(controller, alternate)
            self.assertEqual(len(controller.state.read()['remote_operations']), 1)
        self.assertEqual(self.actual(), self.head)

    def test_raced_ancestor_remote_write_is_not_overwritten(self):
        original = git_transport._remote
        def race(controller, action, remote, request):
            if action == 'push':
                git(self.root, 'push', 'origin', self.base + ':' + self.ref)
            return original(controller, action, remote, request)
        with self.controller() as controller:
            with patch.object(git_transport, '_remote', side_effect=race):
                with self.assertRaisesRegex(Blocked, 'unknown|mismatched'):
                    self.push(controller)
            self.assertEqual(controller.state.read()['remote_operations'][0]['status'], 'unknown')
        self.assertEqual(self.actual(), self.base)

    def test_existing_pre_push_hook_still_runs_and_can_reject(self):
        hook = self.root / '.git/hooks/pre-push'
        hook.write_text('#!/bin/sh\nprintf hook-ran > hook-marker\nexit 1\n')
        hook.chmod(0o700)
        with self.controller() as controller:
            with self.assertRaises(Blocked):
                self.push(controller)
        self.assertEqual((self.root / 'hook-marker').read_text(), 'hook-ran')
        self.assertIsNone(self.actual())

    def test_original_pre_push_hook_receives_named_remote(self):
        hook = self.root / '.git/hooks/pre-push'
        hook.write_text('#!/bin/sh\nif [ "$1" = origin ]; then exit 1; fi\nexit 0\n')
        hook.chmod(0o700)
        with self.controller() as controller:
            with self.assertRaises(Blocked):
                self.push(controller)
        self.assertIsNone(self.actual())

    def test_receiver_pre_receive_hook_is_not_bypassed(self):
        hook = self.remote / 'hooks/pre-receive'
        hook.write_text('#!/bin/sh\nexit 1\n')
        hook.chmod(0o700)
        with self.controller() as controller:
            with self.assertRaises(Blocked):
                self.push(controller)
        self.assertIsNone(self.actual())

    def test_second_url_rewrite_cannot_bypass_expected_destination(self):
        # First expansion appears to be the approved GitHub destination, but
        # reusing that expanded URL would redirect both operations elsewhere.
        git(self.root, 'remote', 'set-url', 'origin', 'alias:fixture/repository.git')
        git(self.root, 'config', 'url.https://github.com/.insteadOf', 'alias:')
        git(self.root, 'config', 'url.' + str(self.remote) + '.insteadOf',
            'https://github.com/fixture/repository.git')
        with self.controller() as controller:
            with self.assertRaises(Blocked):
                remote_fingerprint(controller, 'origin', expected_repository='fixture/repository')
        self.assertIsNone(self.actual())

    def test_source_changed_after_push_is_not_promoted(self):
        original = git_transport._remote
        def move_source(controller, action, remote, request):
            result = original(controller, action, remote, request)
            if action == 'push':
                git(self.root, 'update-ref', self.ref, self.base)
            return result
        with self.controller() as controller:
            with patch.object(git_transport, '_remote', side_effect=move_source):
                with self.assertRaisesRegex(Blocked, 'configured source ref changed'):
                    self.push(controller)
            self.assertEqual(controller.state.read()['remote_operations'][0]['status'], 'observed')
            self.assertEqual(controller.state.read()['tasks'], {})
        self.assertEqual(self.actual(), self.head)

    def test_explicit_auth_required_even_for_reuse(self):
        with self.controller() as controller:
            for authorization in (False, None, 'yes', 1):
                with self.assertRaisesRegex(Blocked, 'authorization'):
                    push_source(controller, self.task_id, 'feature', self.head, 'origin', self.ref,
                                authorized=authorization)
            self.assertEqual(controller.state.read()['commands_started'], 0)
        self.assertIsNone(self.actual())

    def test_exact_head_mismatch_is_rejected_before_remote_read(self):
        with self.controller() as controller:
            with patch.object(git_transport, '_remote', wraps=git_transport._remote) as called:
                with self.assertRaisesRegex(Blocked, 'validated source SHA'):
                    self.push(controller, self.base)
                called.assert_not_called()
        self.assertIsNone(self.actual())

    def test_bad_refs_remote_and_sha_block_without_effects(self):
        cases = [('feature', self.head, '--all', self.ref),
                 ('feature', self.head, str(self.remote), self.ref),
                 ('feature', self.head, 'origin', 'refs/tags/feature'),
                 ('feature', self.head, 'origin', 'refs/heads/bad..ref'),
                 ('feature~1', self.head, 'origin', self.ref),
                 ('feature', self.head[:7], 'origin', self.ref)]
        with self.controller() as controller:
            for source, head, remote, ref in cases:
                with self.subTest(source=source, remote=remote, ref=ref):
                    with self.assertRaises(Blocked):
                        push_source(controller, self.task_id, source, head, remote, ref, authorized=True)
        self.assertIsNone(self.actual())

    def test_expected_github_repository_rejects_bare_local_without_network(self):
        with self.controller() as controller:
            with patch.object(git_transport, '_remote', wraps=git_transport._remote) as called:
                with self.assertRaisesRegex(Blocked, 'expected GitHub'):
                    self.push(controller, expected_repository='fixture/repository')
            self.assertEqual([call.args[1] for call in called.call_args_list], ['fingerprint'])
        self.assertIsNone(self.actual())

    def test_credential_url_fingerprint_is_redacted_and_uses_pushurl(self):
        secret = 'DUMMY_SECRET_must_never_appear_782736'
        git(self.root, 'remote', 'set-url', 'origin', 'https://github.com/wrong/fetch.git')
        git(self.root, 'remote', 'set-url', '--push', 'origin',
            'https://username:' + secret + '@github.com/Fixture/Repository.git?token=' + secret)
        with self.controller() as controller:
            destination = remote_fingerprint(controller, 'origin', expected_repository='fixture/repository')
            self.assertEqual(destination['repository'], 'fixture/repository')
            self.assertEqual(destination['hostname'], 'github.com')
            self.assertNotIn(secret, json.dumps(destination))
            self.assertNotIn(secret, controller.state.path.read_text())
            self.assertNotIn(secret, controller.journal.read_text())
            for path in (controller.common / 'harness-source').rglob('*'):
                if path.is_file():
                    self.assertNotIn(secret, path.read_text())
            self.assertEqual(controller.state.read()['commands_started'], 1)

    def test_wrong_repo_and_host_fail_without_remote_connection(self):
        git(self.root, 'remote', 'set-url', 'origin', 'ssh://git@github.com/fixture/repository.git')
        with self.controller() as controller:
            with self.assertRaisesRegex(Blocked, 'expected GitHub'):
                remote_fingerprint(controller, 'origin', expected_repository='other/repository')
            with self.assertRaisesRegex(Blocked, 'expected GitHub'):
                remote_fingerprint(controller, 'origin', expected_repository='fixture/repository', expected_hostname='other.example')

    def test_multiple_push_destinations_are_refused(self):
        git(self.root, 'remote', 'set-url', '--add', '--push', 'origin', str(self.remote))
        git(self.root, 'remote', 'set-url', '--add', '--push', 'origin', str(self.remote) + '-other')
        with self.controller() as controller:
            with self.assertRaises(Blocked):
                remote_fingerprint(controller, 'origin')

    def test_query_uses_actual_push_destination_not_fetch_remote(self):
        other = Path(self.tmp.name) / 'fetch-only.git'
        other.mkdir()
        git(other, 'init', '--bare')
        git(self.root, 'remote', 'set-url', 'origin', str(other))
        git(self.root, 'remote', 'set-url', '--push', 'origin', str(self.remote))
        with self.controller() as controller:
            self.push(controller)
            destination = remote_fingerprint(controller, 'origin')
            self.assertEqual(query_remote_ref(controller, 'origin', self.ref, destination=destination), self.head)
        self.assertEqual(git(other, 'show-ref') if git(other, 'for-each-ref') else '', '')
        self.assertEqual(self.actual(), self.head)

    def test_gh_credentials_are_command_scoped_and_inherit_config_dir(self):
        # A tiny test-only Git shim intercepts just the network query. All local
        # Git and remote-URL resolution remain real; no external request occurs.
        git(self.root, 'remote', 'set-url', 'origin', 'https://github.com/fixture/repository.git')
        config_before = (self.root / '.git/config').read_bytes()
        shim_directory = Path(self.tmp.name) / 'shim'
        shim_directory.mkdir()
        trace = Path(self.tmp.name) / 'helper-observation.json'
        real_git = shutil.which('git')
        shim = shim_directory / 'git'
        program = """import json, os, sys
from pathlib import Path
args = sys.argv[1:]
if 'ls-remote' in args and '--get-url' not in args:
    Path(os.environ['SOURCE_HELPER_TRACE']).write_text(json.dumps({
        'empty': 'credential.helper=' in args,
        'gh': 'credential.helper=!gh auth git-credential' in args,
        'config_inherited': os.environ.get('GH_CONFIG_DIR') == os.environ.get('SOURCE_EXPECTED_GH_CONFIG')}))
    sys.exit(0)
os.execv(%r, [%r, *args])
""" % (real_git, real_git)
        shim.write_text('#!' + sys.executable + '\n' + program)
        shim.chmod(0o700)
        fake_config = str(Path(self.tmp.name) / 'dummy-gh-config')
        with patch.dict(os.environ, {'PATH': str(shim_directory) + os.pathsep + os.environ['PATH'],
                                    'SOURCE_HELPER_TRACE': str(trace),
                                    'GH_CONFIG_DIR': fake_config,
                                    'SOURCE_EXPECTED_GH_CONFIG': fake_config}):
            with self.controller() as controller:
                destination = remote_fingerprint(controller, 'origin', expected_repository='fixture/repository')
                self.assertIsNone(query_remote_ref(controller, 'origin', self.ref, destination=destination))
                self.assertEqual(json.loads(trace.read_text()), {'empty': False, 'gh': False, 'config_inherited': True})
                self.assertIsNone(query_remote_ref(controller, 'origin', self.ref, destination=destination, use_gh_credentials=True))
                self.assertEqual(json.loads(trace.read_text()), {'empty': True, 'gh': True, 'config_inherited': True})
        self.assertEqual((self.root / '.git/config').read_bytes(), config_before)

    def test_budget_exhaustion_does_not_reset_or_start_push(self):
        with self.controller(max_attempts=2) as controller:
            with self.assertRaisesRegex(Blocked, 'budget_exhausted'):
                self.push(controller)
            self.assertEqual(controller.state.read()['commands_started'], 2)
        with self.controller(max_attempts=2) as controller:
            with self.assertRaisesRegex(Blocked, 'budget_exhausted'):
                self.push(controller)
            self.assertEqual(controller.state.read()['commands_started'], 2)
        self.assertIsNone(self.actual())


if __name__ == '__main__':
    unittest.main()
