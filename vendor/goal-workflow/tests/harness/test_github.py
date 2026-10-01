import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'skills/harness-init/assets/project'))
from harness.github import AdapterError, GitHubAdapter


class Fixture:
    def __init__(self, routes):
        self.routes, self.calls = routes, []
    def __call__(self, argv, timeout):
        self.calls.append((argv, timeout))
        key = next((k for k in self.routes if k in argv), None)
        if key is None:
            raise AssertionError(argv)
        value = self.routes[key]
        if isinstance(value, Exception):
            raise value
        if callable(value):
            value = value()
        if isinstance(value, subprocess.CompletedProcess):
            return value
        return subprocess.CompletedProcess(argv, 0, json.dumps(value), '')


def issue(n, body='', state='open', repo='o/r'):
    return {'number': n, 'title': f'task {n}', 'body': body, 'state': state,
            'repository_url': f'https://api.github.com/repos/{repo}'}


def pr():
    return {'number': 8, 'head': {'sha': 'source', 'label': 'o:feature'},
            'base': {'sha': 'target', 'ref': 'main'}, 'state': 'open', 'merged': False, 'draft': False}


class GitHubTests(unittest.TestCase):
    def adapter(self, routes, **config):
        self.fixture = Fixture(routes)
        return GitHubAdapter(dict(repository='o/r', **config), self.fixture)

    def test_pagination_filters_prs(self):
        a = self.adapter({'repos/o/r/issues?state=open&per_page=100': [[issue(1)], [issue(201), dict(issue(2), pull_request={})]]})
        self.assertEqual([x['number'] for x in a.list_tasks()], [1, 201])
        self.assertIn('--paginate', self.fixture.calls[0][0])
        self.assertGreater(self.fixture.calls[0][1], 0)

    def test_native_plus_body_closed_and_cross_repository(self):
        a = self.adapter({'repos/o/r/issues/1': issue(1, 'Depends on: #2, x/y#9\nsee #55'),
                          'repos/o/r/issues/1/dependencies/blocked_by?per_page=100': [[issue(2, state='closed')], [issue(301)]],
                          'repos/o/r/issues/2': issue(2, state='closed'), 'repos/x/y/issues/9': issue(9, repo='x/y')})
        deps = a.dependencies(1)
        self.assertEqual({x['id'] for x in deps}, {'github:github.com:o/r#2', 'github:github.com:o/r#301', 'github:github.com:x/y#9'})
        self.assertFalse(a.dependency_satisfied(deps[0], None))
        self.assertTrue(a.dependency_satisfied(deps[0], dict(status='delivered', verified_delivery=True, delivered_sha='abc')))

    def test_native_query_failure_not_fallback(self):
        for code in [1, 4]:
            a = self.adapter({'repos/o/r/issues/1': issue(1), 'repos/o/r/issues/1/dependencies/blocked_by?per_page=100': subprocess.CompletedProcess([], code, '', 'HTTP 404 or auth')})
            with self.assertRaises(AdapterError): a.dependencies(1)

    def test_timeout_and_malformed_fail_closed(self):
        for result in [subprocess.TimeoutExpired('gh', 1), subprocess.CompletedProcess([], 0, 'bad', ''), {}]:
            a = self.adapter({'repos/o/r/issues?state=open&per_page=100': result})
            with self.assertRaises(AdapterError): a.list_tasks()

    def test_cycles_block_even_closed(self):
        routes = {'repos/o/r/issues?state=open&per_page=100': [[issue(1)]]}
        for n, dep in [(1, 2), (2, 1)]:
            routes[f'repos/o/r/issues/{n}'] = issue(n, state='closed' if n == 2 else 'open')
            routes[f'repos/o/r/issues/{n}/dependencies/blocked_by?per_page=100'] = [[issue(dep)]]
        with self.assertRaisesRegex(AdapterError, 'cycle'): self.adapter(routes).dependency_graph()

    def checks_routes(self, conclusion='success', sha='source'):
        return {'repos/o/r/pulls/8': pr(),
                f'repos/o/r/commits/{sha}/check-runs?per_page=100': [{'check_runs': [{'id': 1, 'head_sha': sha, 'name': 'test', 'status': 'completed', 'conclusion': conclusion}]}],
                f'repos/o/r/commits/{sha}/statuses?per_page=100': [[]]}

    def test_checks_exact_sha_skipped_missing(self):
        for conclusion, expected in [('success', 'pass'), ('skipped', 'blocked'), ('neutral', 'blocked'), ('failure', 'blocked'), (None, 'blocked')]:
            a = self.adapter(self.checks_routes(conclusion))
            self.assertEqual(a.checks(8, 'source', ['test'])['status'], expected)
            self.assertEqual(a.checks(8, 'source', ['missing'])['status'], 'blocked')
        with self.assertRaises(AdapterError): a.checks(8, 'source', [])

    def test_checks_detect_race(self):
        routes = self.checks_routes()
        count = [0]
        def shifting():
            value = pr()
            count[0] += 1
            if count[0] > 1: value['head']['sha'] = 'new'
            return value
        routes['repos/o/r/pulls/8'] = shifting
        with self.assertRaisesRegex(AdapterError, 'changed'): self.adapter(routes).checks(8, 'source', ['test'])

    def test_source_target_delivery_semantics(self):
        a = self.adapter({'repos/o/r/pulls/8': pr()})
        evidence = dict(status='pass', source_sha='source', target_sha='target', checked_sha='candidate', candidate_tree='tree')
        self.assertEqual(a.reconcile(8, evidence, 'target')['status'], 'verified')
        self.assertEqual(a.reconcile(8, evidence, 'new-target')['status'], 'stale')
        merged = dict(pr(), merged=True, state='closed', merge_commit_sha='squash')
        a = self.adapter({'repos/o/r/pulls/8': merged})
        self.assertEqual(a.reconcile(8, evidence, 'squash')['status'], 'blocked')
        result = a.reconcile(8, evidence, 'squash', delivered_tree='tree', delivered_reachable=True)
        self.assertEqual(result['status'], 'delivered')
        self.assertEqual(result['delivered_sha'], 'squash')

    def test_create_recovery_reuses_pr_after_timeout(self):
        key = 'repos/o/r/pulls?state=all&per_page=100&head=o%3Afeature&base=main'
        queries = [0]
        def find():
            queries[0] += 1
            return [[]] if queries[0] == 1 else [[pr()]]
        a = self.adapter({key: find, 'create': subprocess.TimeoutExpired('gh', 1)})
        self.assertEqual(a.ensure_pr('o:feature', 'main', 'title', 'body', True)['number'], 8)
        self.assertEqual(sum('create' in c[0] for c in self.fixture.calls), 1)

    def test_creation_denied_without_authorization(self):
        a = self.adapter({'repos/o/r/pulls?state=all&per_page=100&head=o%3Afeature&base=main': [[]]})
        with self.assertRaisesRegex(AdapterError, 'authorization'): a.ensure_pr('o:feature', 'main', 't', 'b')

    def test_duplicate_pr_identity_blocks(self):
        a = self.adapter({'repos/o/r/pulls?state=all&per_page=100&head=o%3Afeature&base=main': [[pr(), pr()]]})
        with self.assertRaisesRegex(AdapterError, 'Multiple'): a.find_pr('o:feature', 'main')

    def test_merge_requires_rules_and_queue_evidence(self):
        evidence = dict(status='pass', source_sha='source', target_sha='target', checked_sha='source')
        for config in [{}, {'merge_policy': 'strict'}, {'merge_policy': 'queue', 'rules_verified': True}]:
            a = self.adapter({'repos/o/r/pulls/8': pr()}, github=config)
            with self.assertRaises(AdapterError): a.request_merge(8, evidence, 'target', True)

if __name__ == '__main__': unittest.main()

class GitHubBridgeTests(unittest.TestCase):
    def test_cross_repo_identity_mapping_and_mode_guard(self):
        from harness.github import core_id, normalize_graph, github_action
        ids = ['github:github.com:o/r#1', 'github:github.com:o/other#1']
        graph = {'tasks': {x: {'id': x} for x in ids}, 'dependencies': {ids[0]: [ids[1]], ids[1]: []}}
        result = normalize_graph(graph)
        self.assertNotEqual(core_id(ids[0]), core_id(ids[1]))
        self.assertEqual(result['dependencies'][core_id(ids[0])], [core_id(ids[1])])
        self.assertEqual(result['tasks'][core_id(ids[0])]['source_id'], ids[0])
        with self.assertRaises(AdapterError): github_action({'mode': 'local'}, 'tasks', {})

    def test_config_contract_mapping(self):
        a = GitHubAdapter({'github': {'repository': 'o/r', 'server': 'https://github.example.com'}, 'limits': {'request_seconds': 7}}, Fixture({}))
        self.assertEqual(a.hostname, 'github.example.com')
        self.assertEqual(a.timeout, 7)

    def test_actual_strict_rules(self):
        f = Fixture({'repos/o/r/rules/branches/main?per_page=100': [[{'type': 'required_status_checks', 'parameters': {
            'strict_required_status_checks_policy': True, 'required_status_checks': [{'context': 'test'}]}}]]})
        a = GitHubAdapter({'repository': 'o/r'}, f)
        self.assertEqual(a.inspect_rules('main')['policy'], 'strict')

    def test_status_rerun_latest_not_old_pass(self):
        routes = GitHubTests().checks_routes()
        routes['repos/o/r/commits/source/check-runs?per_page=100'] = [{'check_runs': []}]
        routes['repos/o/r/commits/source/statuses?per_page=100'] = [[{'context': 'test', 'state': 'failure'}, {'context': 'test', 'state': 'success'}]]
        a = GitHubAdapter({'repository': 'o/r'}, Fixture(routes))
        self.assertEqual(a.checks(8, 'source', ['test'])['status'], 'blocked')

    def test_authorized_merge_pending_then_timeout_reconciled(self):
        routes = GitHubTests().checks_routes()
        routes['repos/o/r/rules/branches/main?per_page=100'] = [[{'type': 'required_status_checks', 'parameters': {
            'strict_required_status_checks_policy': True, 'required_status_checks': [{'context': 'test'}]}}]]
        config = {'repository': 'o/r', 'github': {'merge_policy': 'strict', 'rules_verified': True, 'required_checks': ['test']}}
        evidence = dict(status='pass', source_sha='source', target_sha='target', checked_sha='source', baseline_verified=True)
        routes['merge'] = subprocess.CompletedProcess([], 0, '', '')
        f = Fixture(routes)
        a = GitHubAdapter(config, f)
        self.assertEqual(a.request_merge(8, evidence, 'target', True)['status'], 'delivery_pending')
        self.assertIn('--match-head-commit', next(call[0] for call in f.calls if 'merge' in call[0]))
        routes['merge'] = subprocess.TimeoutExpired('gh', 1)
        self.assertEqual(a.request_merge(8, evidence, 'target', True)['status'], 'delivery_unknown')

class QueueCompletionTests(unittest.TestCase):
    def test_merged_queue_requires_merge_group_evidence(self):
        merged = dict(pr(), merged=True, state='closed', merge_commit_sha='merged')
        a = GitHubAdapter({'repository': 'o/r', 'github': {'baseline_policy': 'merge_queue'}}, Fixture({'repos/o/r/pulls/8': merged}))
        evidence = dict(status='pass', source_sha='source', target_sha='target', checked_sha='source', candidate_tree='tree')
        self.assertEqual(a.reconcile(8, evidence, 'merged', 'tree', True)['status'], 'blocked')
        evidence.update(event='merge_group', merge_group_sha='group', checked_sha='group')
        self.assertEqual(a.reconcile(8, evidence, 'merged', 'tree', True)['status'], 'delivered')

    def test_delivered_commit_not_target_reachable_is_blocked(self):
        merged = dict(pr(), merged=True, state='closed', merge_commit_sha='merged')
        a = GitHubAdapter({'repository': 'o/r'}, Fixture({'repos/o/r/pulls/8': merged}))
        evidence = dict(status='pass', source_sha='source', target_sha='target', checked_sha='source', candidate_tree='tree')
        self.assertEqual(a.reconcile(8, evidence, 'other', 'tree', False)['status'], 'blocked')
