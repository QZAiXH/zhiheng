"""Draft-to-ready state transitions, uncertainty and merge prerequisite."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'skills/harness-init/assets/project'))
from harness.github import AdapterError, GitHubAdapter, github_action
from test_github import pr


class ReadyFixture:
    def __init__(self, draft=True, fail=False, apply=True, fail_read_after=False):
        self.pr = dict(pr(), draft=draft)
        self.fail, self.apply, self.fail_read_after = fail, apply, fail_read_after
        self.calls = []
        self.writes = 0
    def __call__(self, argv, timeout):
        self.calls.append(argv)
        if argv[1:3] == ['pr', 'ready']:
            self.writes += 1
            if self.apply: self.pr['draft'] = False
            if self.fail: raise subprocess.TimeoutExpired('gh', 1)
            return subprocess.CompletedProcess(argv, 0, '', '')
        if self.writes and self.fail_read_after:
            raise subprocess.TimeoutExpired('gh', 1)
        if 'repos/o/r/pulls/8' not in argv: raise AssertionError(argv)
        return subprocess.CompletedProcess(argv, 0, json.dumps(self.pr), '')


class ReadyTests(unittest.TestCase):
    def adapter(self, fixture): return GitHubAdapter({'repository': 'o/r'}, fixture)
    def test_readonly_draft_does_not_write(self):
        f = ReadyFixture()
        self.assertEqual(self.adapter(f).ready_for_review(8)['status'], 'draft')
        self.assertEqual(f.writes, 0)
    def test_authorized_transition_reads_actual_result(self):
        f = ReadyFixture()
        result = self.adapter(f).ready_for_review(8, True)
        self.assertEqual(result['status'], 'ready')
        self.assertFalse(result['observed']['draft'])
        self.assertEqual(f.writes, 1)
        self.assertEqual(f.calls[1], ['gh', 'pr', 'ready', '8', '--repo', 'o/r'])
    def test_already_ready_is_idempotent(self):
        f = ReadyFixture(False)
        self.assertEqual(self.adapter(f).ready_for_review(8, True)['status'], 'ready')
        self.assertEqual(f.writes, 0)
    def test_timeout_after_write_reconciles_without_retry(self):
        f = ReadyFixture(fail=True)
        self.assertEqual(self.adapter(f).ready_for_review(8, True)['status'], 'ready')
        self.assertEqual(f.writes, 1)
    def test_timeout_before_write_is_unknown(self):
        f = ReadyFixture(fail=True, apply=False)
        self.assertEqual(self.adapter(f).ready_for_review(8, True)['status'], 'unknown')
        self.assertEqual(f.writes, 1)
    def test_failed_confirmation_read_is_unknown(self):
        f = ReadyFixture(fail_read_after=True)
        self.assertEqual(self.adapter(f).ready_for_review(8, True)['status'], 'unknown')
        self.assertEqual(f.writes, 1)
    def test_missing_draft_and_closed_states_fail_closed(self):
        for changes in [{'draft': None}, {'draft': 'false'}, {'state': 'closed'}, {'merged': True}, {'number': 9}]:
            with self.subTest(changes=changes):
                f = ReadyFixture()
                f.pr.update(changes)
                with self.assertRaises(AdapterError): self.adapter(f).ready_for_review(8, True)
                self.assertEqual(f.writes, 0)
    def test_native_success_without_observed_transition_is_unknown(self):
        f = ReadyFixture(apply=False)
        self.assertEqual(self.adapter(f).ready_for_review(8, True)['status'], 'unknown')
        self.assertEqual(f.writes, 1)
    def test_bridge_reconcile_ignores_authorize(self):
        f = ReadyFixture()
        config = {'mode': 'github', 'repository': 'o/r'}
        self.assertEqual(github_action(config, 'reconcile-ready', {'number': 8, 'authorized': True}, run=f)['status'], 'draft')
        self.assertEqual(f.writes, 0)
        self.assertEqual(github_action(config, 'ready', {'number': 8, 'authorized': True}, run=f)['status'], 'ready')
        self.assertEqual(f.writes, 1)
    def test_merge_draft_fails_before_any_write(self):
        f = ReadyFixture()
        with self.assertRaisesRegex(AdapterError, 'Draft PR'):
            self.adapter(f).request_merge(8, {}, 'target', True)
        self.assertEqual(f.writes, 0)
        self.assertEqual(len(f.calls), 1)

if __name__ == '__main__': unittest.main()
