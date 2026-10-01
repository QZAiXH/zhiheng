import importlib.util
import contextlib
import io
from pathlib import Path
import unittest
from unittest import mock

spec = importlib.util.spec_from_file_location('harness_ci_partition', Path(__file__).resolve().parents[1] / 'tools/run-harness-tests.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class NamedTest:
    def __init__(self, name):
        self.name = name
    def id(self):
        return self.name


class PartitionTests(unittest.TestCase):
    def test_known_e2e_groups(self):
        expected = {
            'test_cli_e2e.CliE2E.test_tiny': 'local',
            'test_github_cli_e2e.GitHubCliE2E.test_tiny': 'github',
            'test_worktree_knowledge_e2e.WorktreeKnowledgeE2E.test_reads': 'knowledge',
            'test_controller_commit_e2e.ControllerCommitLocalE2E.test_tiny': 'local',
            'test_controller_commit_e2e.ControllerCommitGitHubE2E.test_tiny': 'github',
        }
        for name, group in expected.items():
            with self.subTest(name=name):
                self.assertEqual(group, runner.group_for(NamedTest(name)))

    def test_new_modules_and_classes_never_disappear(self):
        for name in ('test_future_e2e.Future.test_x', 'test_controller_commit_e2e.Future.test_x', 'test_runtime.Runtime.test_x'):
            self.assertEqual('core', runner.group_for(NamedTest(name)))

    def test_partition_preserves_every_discovered_occurrence(self):
        names = ['test_cli_e2e.CliE2E.test_x', 'test_runtime.Runtime.test_x', 'test_runtime.Runtime.test_x']
        groups = runner.partition([NamedTest(name) for name in names])
        self.assertEqual(3, sum(map(len, groups.values())))
        self.assertEqual(2, len(groups['core']))
        self.assertEqual(1, len(groups['local']))

    def test_flatten_retains_nested_test_cases(self):
        first = unittest.FunctionTestCase(lambda: None)
        second = unittest.FunctionTestCase(lambda: None)
        suite = unittest.TestSuite([first, unittest.TestSuite([second])])
        self.assertEqual([first, second], list(runner.flatten(suite)))


class DeferredScopeTests(unittest.TestCase):
    def test_restricted_module_requires_manifest(self):
        with self.assertRaises(ValueError):
            runner.functional_scope([NamedTest('test_controller_commit.Normal.test_x')], None)

    def test_deferred_and_unlisted_cases_never_run(self):
        names = ['test_runtime.Runtime.test_x', 'test_controller_commit.Normal.test_ok',
                 'test_controller_commit.Normal.test_deferred', 'test_controller_commit_new.New.test_unknown']
        scope = {'allowed_test_ids': [names[1]], 'paused_test_ids': [names[2]]}
        selected, deferred = runner.functional_scope([NamedTest(name) for name in names], scope)
        self.assertEqual(names[:2], [test.id() for test in selected])
        self.assertEqual(names[2:], [test.id() for test in deferred])

    def test_manifest_contradictions_fail_closed(self):
        name = 'test_controller_commit.Normal.test_x'
        with self.assertRaises(ValueError):
            runner.functional_scope([NamedTest(name)], {'allowed_test_ids': [name], 'paused_test_ids': [name]})
        with self.assertRaises(ValueError):
            runner.functional_scope([NamedTest(name)], {'allowed_test_ids': [name + 'missing']})

    def test_legacy_scope_is_unchanged(self):
        tests = [NamedTest('test_runtime.Runtime.test_x')]
        selected, deferred = runner.functional_scope(tests, None)
        self.assertEqual(tests, selected)
        self.assertEqual([], deferred)


class FailFastTests(unittest.TestCase):
    def invoke(self, failfast):
        executed = []

        def fail():
            executed.append('first')
            raise AssertionError('intentional fixture failure')

        def later():
            executed.append('later')

        suite = unittest.TestSuite([unittest.FunctionTestCase(fail),
                                    unittest.FunctionTestCase(later)])
        loader = mock.Mock(errors=[])
        loader.discover.return_value = suite
        argv = ['run-harness-tests.py', '--suite', 'core']
        if failfast:
            argv.append('--failfast')
        with mock.patch.object(runner.unittest, 'TestLoader', return_value=loader), \
             mock.patch.object(runner.sys, 'argv', argv), \
             mock.patch.dict(runner.os.environ), \
             contextlib.redirect_stdout(io.StringIO()), \
             contextlib.redirect_stderr(io.StringIO()):
            status = runner.main()
        self.assertEqual(1, status)
        return executed

    def test_explicit_failfast_stops_before_next_test(self):
        self.assertEqual(['first'], self.invoke(True))

    def test_default_ci_behavior_still_collects_failures(self):
        self.assertEqual(['first', 'later'], self.invoke(False))
