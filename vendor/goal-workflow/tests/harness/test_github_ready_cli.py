"""Real CLI/state ready journaling with explicit simulated proof/platform reads."""
import contextlib
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch
sys.path.insert(0,str(Path(__file__).resolve().parent))
import test_local_audit as fixtures
from harness import cli

class ReadyCli(unittest.TestCase):
    commit=fixtures.LocalAudit.commit
    tearDown=fixtures.LocalAudit.tearDown
    def setUp(self):
        fixtures.LocalAudit.setUp(self)
        self.config={'mode':'github','repository_root':str(self.root),'repository':'owner/repo','github':{'target_branch':'main'},'checks':self.checks,'environment':{},'limits':dict(fixtures.LIMITS,task_attempts=3,repair_attempts=2)}
        self.task={'id':'feature','source':'feature','target':'main','spec':'spec.md'}
        self.adapter=MagicMock()
        self.adapter.read_pr.return_value={'number':1,'state':'open','draft':True,'head':{'sha':'h','ref':'feature','repo':{'full_name':'owner/repo'}},'base':{'ref':'main'}}
        self.adapter.branch_head.return_value='t'
    def invoke(self, action, params, outcome):
        args=['github','--bundle','fixture','--run','ready-audit',action,'--args',json.dumps(params)]
        with patch.object(cli,'load',return_value={'config':self.config,'tasks':[self.task]}),patch.object(cli,'preflight',return_value=self.config),patch.object(cli,'require_capabilities'),patch.object(cli,'verified_evidence',return_value={'H':'h','T':'t'}),patch.object(cli.local,'check_fresh'),patch('harness.github.GitHubAdapter',return_value=self.adapter),patch('harness.github.github_action',side_effect=outcome) as called,contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
            result=cli.main(args)
        return result,called
    def state(self):
        path=self.root/'.loop-state.json'
        return json.loads(path.read_text()) if path.exists() else {'remote_operations':[]}
    def test_auth_and_identity_required_before_intent(self):
        code,called=self.invoke('ready',{'task_id':'feature','number':1},lambda *_a,**_k: {})
        self.assertEqual(code,1);called.assert_not_called()
        self.assertEqual(self.state()['remote_operations'],[])
        self.adapter.read_pr.return_value['base']['ref']='wrong'
        code,called=self.invoke('ready',{'task_id':'feature','number':1,'authorized':True},lambda *_a,**_k: {})
        self.assertEqual(code,1);called.assert_not_called()
        self.assertEqual(self.state()['remote_operations'],[])
    def test_unknown_ready_only_resolved_by_read_not_repeated(self):
        params={'task_id':'feature','number':1,'authorized':True}
        def unknown(*_a,**_k):
            self.assertEqual(self.state()['remote_operations'][-1]['status'],'intent')
            return {'status':'unknown','pr':1}
        code,called=self.invoke('ready',params,unknown)
        self.assertEqual(code,0);self.assertEqual(called.call_count,1)
        self.assertEqual(self.state()['remote_operations'][-1]['status'],'unknown')
        code,called=self.invoke('ready',params,unknown)
        self.assertEqual(code,1);called.assert_not_called()
        self.adapter.read_pr.return_value['draft']=False
        self.adapter.read_pr.return_value['head']['sha']='new-head-after-unknown'
        self.adapter.branch_head.return_value='new-target-after-unknown'
        def observe(_config,action,args,**_kwargs):
            self.assertEqual(action,'reconcile-ready')
            self.assertIs(args['authorized'],False)
            return {'status':'ready','pr':1}
        code,called=self.invoke('reconcile-ready',params,observe)
        self.assertEqual(code,0);self.assertEqual(called.call_count,1)
        self.assertEqual(self.state()['remote_operations'][-1]['status'],'observed')
    def test_stale_target_blocks_ready_before_intent(self):
        self.adapter.branch_head.return_value='changed'
        code,called=self.invoke('ready',{'task_id':'feature','number':1,'authorized':True},lambda *_a,**_k: {})
        self.assertEqual(code,1);called.assert_not_called()
        self.assertEqual(self.state()['remote_operations'],[])
