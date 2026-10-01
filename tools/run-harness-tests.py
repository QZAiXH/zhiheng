#!/usr/bin/env python3
"""Run an exhaustive, disjoint shard of the native Harness test discovery."""
from __future__ import annotations

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import sys
import unittest

SUITES = ('core', 'local', 'github', 'knowledge')
ROOT = Path(__file__).resolve().parents[1]
SCOPE_FILE = ROOT / 'vendor/goal-workflow/docs/evidence/controller-commit-test-scope.json'


def flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item


def group_for(test):
    parts = test.id().split('.')
    module = parts[0]
    if module == 'test_cli_e2e':
        return 'local'
    if module == 'test_github_cli_e2e':
        return 'github'
    if module == 'test_worktree_knowledge_e2e':
        return 'knowledge'
    if module == 'test_controller_commit_e2e' and len(parts) > 1:
        if parts[1] == 'ControllerCommitLocalE2E':
            return 'local'
        if parts[1] == 'ControllerCommitGitHubE2E':
            return 'github'
    # New test modules/classes are included here, never silently discarded.
    return 'core'


def partition(tests):
    result = {name: [] for name in SUITES}
    for test in tests:
        result[group_for(test)].append(test)
    original = Counter(t.id() for t in tests)
    combined = Counter(t.id() for group in result.values() for t in group)
    if combined != original:
        raise RuntimeError('test shard partition differs from complete discovery')
    return result


def functional_scope(tests, scope):
    """Never dispatch unlisted Controller-commit tests after an audit block."""
    restricted = [test for test in tests if test.id().split('.')[0].startswith('test_controller_commit')]
    if restricted and scope is None:
        raise ValueError('Controller-commit test scope is missing; refusing unscreened execution')
    if not restricted:
        return tests, []
    allowed = set(scope.get('allowed_test_ids', []))
    paused = set(scope.get('paused_test_ids', []))
    if allowed & paused:
        raise ValueError('Test scope contains overlapping allowed and paused IDs')
    seen = {test.id() for test in restricted}
    if allowed - seen:
        raise ValueError('Approved test IDs are absent from discovery; reconcile the scope manifest')
    selected, deferred = [], []
    for test in tests:
        if test.id().split('.')[0].startswith('test_controller_commit') and test.id() not in allowed:
            deferred.append(test)
        else:
            selected.append(test)
    return selected, deferred


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite', choices=(*SUITES, 'all'), default='all')
    parser.add_argument('--list', action='store_true', help='Discover and verify partition without running tests')
    args = parser.parse_args()
    # Synthetic test repositories have declared local policy. Do not inherit
    # a runner account's unrelated global/system Git execution settings.
    # These are process-local settings, never written to host configuration.
    os.environ['GIT_CONFIG_NOSYSTEM'] = '1'
    os.environ['GIT_CONFIG_GLOBAL'] = os.devnull
    loader = unittest.TestLoader()
    discovered = list(flatten(loader.discover(str(ROOT / 'vendor/goal-workflow/tests/harness'))))
    if loader.errors:
        print('\n'.join(loader.errors), file=sys.stderr)
        return 2
    scope = json.loads(SCOPE_FILE.read_text()) if SCOPE_FILE.is_file() else None
    try:
        eligible, deferred = functional_scope(discovered, scope)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    grouped = partition(eligible)
    selected = eligible if args.suite == 'all' else grouped[args.suite]
    if not selected:
        print('Refusing an empty test selection', file=sys.stderr)
        return 2
    print(json.dumps({'suite': args.suite, 'complete_discovery_count': len(discovered),
                      'partition_counts': {key: len(value) for key, value in grouped.items()},
                      'selected_count': len(selected), 'deferred_count': len(deferred),
                      'deferred_test_ids': [test.id() for test in deferred],
                      'synthetic_git_configuration': {
                          'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': os.devnull,
                          'repository_local_configuration': 'preserved'},
                      'full_verification_complete': False if deferred else None}, sort_keys=True), flush=True)
    if args.list:
        print(json.dumps({key: [test.id() for test in value] for key, value in grouped.items()}, indent=2))
        return 0
    if args.suite == 'all' and deferred:
        print('Full verification is blocked; use an explicit functional shard without deferred tests', file=sys.stderr)
        return 2
    if deferred:
        print('FUNCTIONAL SUBSET ONLY: deferred cases and independent review remain unverified', file=sys.stderr)
    result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(selected))
    if result.skipped:
        print('Required native verification has skipped tests; inspect scope before acceptance', file=sys.stderr)
    return 0 if result.wasSuccessful() and not result.skipped else 1


if __name__ == '__main__':
    raise SystemExit(main())
