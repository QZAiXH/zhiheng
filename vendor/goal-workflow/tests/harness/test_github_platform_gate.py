"""Platform-gate unit fixtures, not live GitHub/real-Codex acceptance."""
import copy
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from harness.cli import github_platform_verify, github_verified_args
from harness.runtime import Controller
from harness.state import Blocked

class PlatformGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);subprocess.run(['git','init','-q',str(self.root)],check=True)
        self.limits={'command_seconds':2,'stop_grace_seconds':.2,'total_seconds':10,'max_attempts':5}
        self.config={'mode':'github','github':{'required_checks':['test'],'repository':'example/repo'}}
        self.task={'id':'task-one','source':'feature','target':'main'};self.bundle={'tasks':[self.task]}
        self.proof={'H':'h'*40,'T':'t'*40,'C':'c'*40,'target_ref':'main','tree':'tree-fixture','verification_tier':'simulation'}
        self.pr={'number':3,'head':{'sha':self.proof['H'],'ref':'feature','repo':{'full_name':'example/repo'}},'base':{'sha':self.proof['T'],'ref':'main'},'merge_commit_sha':'m'*40}
        self.adapter=MagicMock();self.adapter.read_pr.return_value=copy.deepcopy(self.pr)
        self.adapter.branch_head.return_value=self.proof['T']
        self.adapter.branch_head.return_value=self.proof['T']
        self.adapter.commit_tree.return_value='tree-fixture'
        self.adapter.checks.return_value={'status':'pass','checked_sha':'m'*40,'checks':{'test':{'status':'pass'}}}
    def invoke(self):
        with Controller(self.root,'github','run-one',self.limits) as controller:
            state=controller.state.read();state['tasks']['task-one']={'status':'validating','local_validation':'passed','verification_tier':'simulation'}
            controller.state.write(state,state['revision'])
            with patch('harness.cli.verified_evidence',return_value=self.proof),patch('harness.github.GitHubAdapter',return_value=self.adapter):
                result=github_platform_verify(controller,self.config,self.bundle,{'task_id':'task-one','number':3})
                return result,controller.state.read()
    def test_passing_current_platform_gate_promotes_with_simulation_label(self):
        result,state=self.invoke();self.assertEqual(result['status'],'verified');self.assertEqual(result['verification_tier'],'simulation')
        self.assertEqual(state['tasks']['task-one']['platform_evidence']['checked_sha'],'m'*40)
        self.adapter.checks.assert_called_once_with(3,'m'*40,['test'])
    def test_missing_or_failed_ci_never_promotes(self):
        self.adapter.checks.return_value={'status':'blocked','checks':{}}
        with self.assertRaisesRegex(Blocked,'CI incomplete'):self.invoke()
    def test_changed_source_blocks(self):
        self.adapter.read_pr.return_value['head']['sha']='x'*40
        with self.assertRaisesRegex(Blocked,'head or target'):self.invoke()
    def test_stale_embedded_pr_base_does_not_hide_real_target_advance(self):
        self.adapter.branch_head.return_value='f'*40
        with self.assertRaisesRegex(Blocked,'head or target'):self.invoke()
        self.adapter.branch_head.assert_called_once_with('main')
    def test_wrong_actual_tree_blocks(self):
        self.adapter.commit_tree.return_value='wrong'
        with self.assertRaisesRegex(Blocked,'object differs'):self.invoke()
    def test_source_race_after_checks_blocks(self):
        changed=copy.deepcopy(self.pr);changed['head']['sha']='z'*40
        self.adapter.read_pr.side_effect=[self.pr,changed]
        self.adapter.branch_head.side_effect=[self.proof['T'],'z'*40]
        with self.assertRaisesRegex(Blocked,'changed during'):self.invoke()
    def test_metadata_sensitive_candidate_blocks_tree_only_equivalence(self):
        self.task['tests_depend_on_commit_metadata']=True
        with self.assertRaisesRegex(Blocked,'commit-sensitive'):self.invoke()
    def test_stale_pr_base_cannot_hide_actual_target_branch_advance(self):
        self.adapter.branch_head.return_value='f'*40
        with self.assertRaises(Blocked):self.invoke()
    def test_actual_target_branch_race_after_checks_blocks(self):
        self.adapter.branch_head.side_effect=[self.proof['T'],'f'*40]
        with self.assertRaises(Blocked):self.invoke()
    def test_wrong_target_branch_same_sha_is_not_authorized_destination(self):
        self.adapter.read_pr.return_value['base']['ref']='wrong-target'
        with self.assertRaises(Blocked):self.invoke()
    def test_retargeted_pr_same_sha_after_checks_is_rejected(self):
        changed=copy.deepcopy(self.pr);changed['base']['ref']='wrong-target'
        self.adapter.read_pr.side_effect=[self.pr,changed]
        with self.assertRaises(Blocked):self.invoke()
    def test_wrong_source_repository_same_sha_is_rejected(self):
        self.adapter.read_pr.return_value['head']['repo']['full_name']='other/repo'
        with self.assertRaises(Blocked):self.invoke()
    def reconcile(self, sensitive, delivered):
        self.task['tests_depend_on_commit_metadata']=sensitive
        self.config['github']['remote']='origin'
        self.adapter.read_pr.return_value.update(merged=True,merge_commit_sha=delivered)
        with Controller(self.root,'github','run-one',self.limits) as controller:
            state=controller.state.read()
            state['tasks']['task-one']={'status':'verified','platform_evidence':{'checked_sha':self.proof['C']}}
            controller.state.write(state,state['revision'])
            with patch('harness.cli.verified_evidence',return_value=self.proof), patch('harness.github.GitHubAdapter',return_value=self.adapter), patch.object(controller,'git',side_effect=['','target-after-merge','tree-fixture','']):
                if sensitive and delivered != self.proof['C']:
                    with self.assertRaisesRegex(Blocked,'commit-sensitive checks must be rerun'):
                        github_verified_args(controller,self.config,self.bundle,'reconcile',{'task_id':'task-one','number':3})
                    saved=controller.state.read()['tasks']['task-one']
                    self.assertEqual(saved['status'],'verified')
                    self.assertNotIn('D',saved)
                    self.assertEqual(saved['physical_delivery'],{'commit':delivered,'tree':'tree-fixture','target':'target-after-merge','reachable':True,'verified_delivery':False,'reason':'commit-sensitive delivered object differs from validated candidate'})
                else:
                    result=github_verified_args(controller,self.config,self.bundle,'reconcile',{'task_id':'task-one','number':3})
                    self.assertEqual(result['delivered_tree'],'tree-fixture')
                    self.assertTrue(result['delivered_reachable'])
                    self.assertNotIn('physical_delivery',controller.state.read()['tasks']['task-one'])
    def test_metadata_sensitive_reconcile_preserves_physical_fact_without_delivery(self):
        self.reconcile(True,'d'*40)
    def test_metadata_sensitive_reconcile_accepts_exact_checked_commit(self):
        self.reconcile(True,self.proof['C'])
    def test_tree_sensitive_reconcile_allows_distinct_tree_equivalent_commit(self):
        self.reconcile(False,'d'*40)
if __name__=='__main__':unittest.main()
