"""Commit-object identity gate with simulated platform/proof and real Controller."""
import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent))
import test_github_platform_gate as fixtures
from harness.cli import github_verified_args
from harness.runtime import Controller
from harness.state import Blocked

class CommitSensitiveMerge(unittest.TestCase):
    def setUp(self):
        fixtures.PlatformGateTests.setUp(self)
        self.config.update(checks=[],environment={})
        self.config['github']['baseline_policy']='strict'
        self.task.update(tests_depend_on_commit_metadata=True,spec='spec.md')
        self.pr.update(state='open',draft=False)
        self.adapter.inspect_rules.return_value={'rules_verified':True,'policy':'strict','required_checks':['test']}
        self.adapter._api.return_value={'tree':{'sha':self.proof['tree']}}
    def invoke_merge(self, checked):
        self.pr['merge_commit_sha']=checked
        self.adapter.read_pr.return_value=copy.deepcopy(self.pr)
        with Controller(self.root,'github','metadata-merge',self.limits) as controller,patch('harness.cli.verified_evidence',return_value=self.proof),patch('harness.github.GitHubAdapter',return_value=self.adapter),patch('harness.cli.local.check_fresh'):
            return github_verified_args(controller,self.config,self.bundle,'merge',{'task_id':'task-one','number':3})
    def test_exact_validated_object_is_allowed(self):
        result=self.invoke_merge(self.proof['C'])
        self.assertEqual(result['evidence']['checked_sha'],self.proof['C'])
    def test_only_tree_equal_different_object_is_blocked(self):
        with self.assertRaisesRegex(Blocked,'commit-sensitive'):
            self.invoke_merge('d'*40)
