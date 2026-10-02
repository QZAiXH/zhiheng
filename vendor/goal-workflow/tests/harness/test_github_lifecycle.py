"""Offline contract fixtures for durable waiting, remote cancellation and Issue closeout."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'skills/harness-init/assets/project'))
from harness.github import AdapterError, GitHubAdapter
from test_github import Fixture, issue, pr
import test_github as fixtures


class IssueFixture:
    def __init__(self, *, comment_timeout=False, close_timeout=False):
        self.comments = []
        self.closed = False
        self.calls = []
        self.comment_timeout, self.close_timeout = comment_timeout, close_timeout
    def __call__(self, argv, timeout):
        self.calls.append(argv)
        endpoint = next((x for x in argv if x.startswith('repos/')), '')
        if endpoint == 'repos/o/r/pulls/8':
            result = dict(pr(), merged=True, merge_commit_sha='delivered')
        elif endpoint == 'repos/o/r/git/ref/heads/main': result = {'object': {'sha': 'tip'}}
        elif endpoint == 'repos/o/r/compare/delivered...tip': result = {'status': 'ahead', 'base_commit': {'sha': 'delivered'}}
        elif endpoint == 'repos/o/r/issues/1/comments?per_page=100': result = [self.comments]
        elif endpoint == 'repos/o/r/issues/1/comments':
            body = next(x[5:] for x in argv if x.startswith('body='))
            self.comments.append({'id': 91, 'body': body, 'html_url': 'https://github.com/o/r/issues/1#issuecomment-91'})
            if self.comment_timeout: raise subprocess.TimeoutExpired('gh', 1)
            result = self.comments[0]
        elif endpoint == 'repos/o/r/issues/1':
            if 'PATCH' in argv:
                self.closed = True
                if self.close_timeout: raise subprocess.TimeoutExpired('gh', 1)
            result = dict(issue(1, state='closed' if self.closed else 'open'), state_reason='completed' if self.closed else None)
        else: raise AssertionError(argv)
        return subprocess.CompletedProcess(argv, 0, json.dumps(result), '')


class IssueCompletionTests(unittest.TestCase):
    def delivery(self):
        return dict(status='delivered', verified_delivery=True, delivered_sha='delivered', source_sha='source', pr=8)
    def test_complete_issue_and_resume_no_duplicate(self):
        f = IssueFixture()
        a = GitHubAdapter({'repository': 'o/r'}, f)
        first = a.complete_issue(1, self.delivery(), 'Verified report link', True)
        self.assertEqual(first['status'], 'completed')
        second = a.complete_issue(1, self.delivery(), 'Verified report link', True)
        self.assertEqual(second['receipt_id'], 91)
        self.assertEqual(sum('POST' in c for c in f.calls), 1)
        self.assertEqual(sum('PATCH' in c for c in f.calls), 1)
    def test_timeout_after_side_effect_reconciles(self):
        f = IssueFixture(comment_timeout=True, close_timeout=True)
        a = GitHubAdapter({'repository': 'o/r'}, f)
        self.assertEqual(a.complete_issue(1, self.delivery(), 'report', True)['status'], 'completed')
        self.assertEqual(sum('POST' in c for c in f.calls), 1)
        self.assertEqual(sum('PATCH' in c for c in f.calls), 1)
    def test_unauthorized_or_unverified_never_writes(self):
        f = IssueFixture()
        a = GitHubAdapter({'repository': 'o/r'}, f)
        with self.assertRaises(AdapterError): a.complete_issue(1, self.delivery(), 'report')
        with self.assertRaises(AdapterError): a.complete_issue(1, dict(self.delivery(), verified_delivery=False), 'report', True)
        self.assertFalse(any('POST' in c or 'PATCH' in c for c in f.calls))
    def test_closed_alone_is_not_completion(self):
        f = IssueFixture()
        f.closed = True
        a = GitHubAdapter({'repository': 'o/r'}, f)
        with self.assertRaises(AdapterError): a.complete_issue(1, {'status': 'closed'}, '', True)
    def test_wrong_delivery_sha_blocks(self):
        f = IssueFixture()
        a = GitHubAdapter({'repository': 'o/r'}, f)
        with self.assertRaises(AdapterError): a.complete_issue(1, dict(self.delivery(), delivered_sha='wrong'), '', True)
        self.assertFalse(any('POST' in c for c in f.calls))


class RemoteFixture:
    def __init__(self, merge_on_disable=False, timeout=False):
        self.state = dict(id='PR_node', state='OPEN', merged=False, autoMergeRequest={'enabledAt': 'date'}, mergeQueueEntry={'id': 'Q'})
        self.calls = []
        self.merge_on_disable, self.timeout = merge_on_disable, timeout
    def __call__(self, argv, timeout):
        self.calls.append(argv)
        query = next(x for x in argv if x.startswith('query='))
        if 'disablePullRequestAutoMerge(input' in query:
            self.state['autoMergeRequest'] = None
            if self.merge_on_disable: self.state['merged'] = True
            if self.timeout: raise subprocess.TimeoutExpired('gh', 1)
            result = {'disablePullRequestAutoMerge': {'pullRequest': {'id': 'PR_node'}}}
        elif 'dequeuePullRequest(input' in query:
            self.state['mergeQueueEntry'] = None
            result = {'dequeuePullRequest': {'mergeQueueEntry': {'id': 'Q'}}}
        else: result = {'repository': {'pullRequest': copy.deepcopy(self.state)}}
        return subprocess.CompletedProcess(argv, 0, json.dumps({'data': result}), '')


class CancellationTests(unittest.TestCase):
    def test_cancel_native_queue_and_auto_merge(self):
        f = RemoteFixture()
        a = GitHubAdapter({'repository': 'o/r'}, f)
        result = a.cancel_remote(8, True)
        self.assertEqual(result['status'], 'cancelled')
        mutations = [c for c in f.calls if any('query=mutation' in x for x in c)]
        self.assertEqual(len(mutations), 2)
        self.assertEqual(a.cancel_remote(8, True)['status'], 'cancelled')
        self.assertEqual(len([c for c in f.calls if any('query=mutation' in x for x in c)]), 2)
    def test_cancel_race_merges_does_not_claim_cancelled(self):
        a = GitHubAdapter({'repository': 'o/r'}, RemoteFixture(merge_on_disable=True))
        self.assertEqual(a.cancel_remote(8, True)['status'], 'already_delivered')
    def test_cancel_timeout_partial_not_success(self):
        a = GitHubAdapter({'repository': 'o/r'}, RemoteFixture(timeout=True))
        self.assertEqual(a.cancel_remote(8, True)['status'], 'unknown')
    def test_no_authorization_no_mutation(self):
        f = RemoteFixture()
        with self.assertRaises(AdapterError): GitHubAdapter({'repository': 'o/r'}, f).cancel_remote(8)
        self.assertFalse(any(any('query=mutation' in x for x in c) for c in f.calls))


class WaitTests(unittest.TestCase):
    def adapter(self):
        a = GitHubAdapter({'repository': 'o/r', 'limits': {'ci_wait_seconds': 5, 'query_attempts': 2, 'poll_seconds': 1}}, Fixture({}))
        a.checks = lambda *args: {'status': 'blocked', 'checks': {'test': {'status': 'pending'}}}
        return a
    def test_total_attempts_survive_resume(self):
        a = self.adapter()
        budget, snapshots, clock = {}, [], [10.0]
        result = a.wait_checks(8, 'sha', ['test'], budget, lambda b: snapshots.append(copy.deepcopy(b)),
                               now=lambda: clock[0], sleep=lambda n: clock.__setitem__(0, clock[0] + n))
        self.assertEqual(result['status'], 'blocked')
        self.assertEqual(budget['attempts'], 2)
        before = len(snapshots)
        self.assertEqual(a.wait_checks(8, 'sha', ['test'], budget, lambda b: snapshots.append(b), now=lambda: clock[0])['status'], 'blocked')
        self.assertEqual(budget['attempts'], 2)
        self.assertEqual(snapshots[0]['attempts'], 1)
    def test_downtime_consumes_wait_window(self):
        a = self.adapter()
        budget = {'started_at': 0, 'attempts': 1, 'elapsed_seconds': 1}
        result = a.wait_checks(8, 'sha', ['test'], budget, lambda b: None, now=lambda: 10)
        self.assertEqual(result['status'], 'blocked')
        self.assertEqual(budget['attempts'], 1)
    def test_cancel_local_never_claims_remote_cancel(self):
        result = self.adapter().wait_checks(8, 'sha', ['test'], {}, lambda b: None, cancelled=lambda: True)
        self.assertFalse(result['remote_cancelled'])
        self.assertEqual(result['status'], 'cancelled_local')
    def test_persist_required_before_query(self):
        with self.assertRaises(AdapterError): self.adapter().wait_checks(8, 'sha', ['test'], {}, None)
    def test_query_unknown_preserves_attempt(self):
        a = self.adapter()
        a.checks = lambda *args: (_ for _ in ()).throw(AdapterError('auth unknown'))
        budget = {}
        result = a.wait_checks(8, 'sha', ['test'], budget, lambda b: None)
        self.assertEqual(result['status'], 'blocked')
        self.assertEqual(budget['attempts'], 1)


class MergeGroupTests(unittest.TestCase):
    def routes(self, associated=True):
        routes = fixtures.GitHubTests().checks_routes(sha='group')
        association = [{'number': 8, 'head': {'sha': 'source'}, 'base': {'ref': 'main'}}] if associated else []
        routes['repos/o/r/actions/runs?head_sha=group&event=merge_group&per_page=100'] = [{'workflow_runs': [{
            'id': 10, 'workflow_id': 1, 'event': 'merge_group', 'head_sha': 'group',
            'pull_requests': association, 'status': 'completed', 'conclusion': 'success'}]}]
        return routes
    def test_actual_event_and_membership_proof(self):
        a = GitHubAdapter({'repository': 'o/r'}, Fixture(self.routes()))
        result = a.merge_group_evidence('group', 8, ['test'])
        self.assertEqual(result['event'], 'merge_group')
        self.assertEqual(result['source_sha'], 'source')
    def test_event_without_native_membership_blocks(self):
        a = GitHubAdapter({'repository': 'o/r'}, Fixture(self.routes(False)))
        with self.assertRaisesRegex(AdapterError, 'association'): a.merge_group_evidence('group', 8, ['test'])
    def test_commit_tree_exact_identity(self):
        a = GitHubAdapter({'repository': 'o/r'}, Fixture({'repos/o/r/git/commits/sha': {'sha': 'sha', 'tree': {'sha': 'tree'}}}))
        self.assertEqual(a.commit_tree('sha'), 'tree')

if __name__ == '__main__': unittest.main()
