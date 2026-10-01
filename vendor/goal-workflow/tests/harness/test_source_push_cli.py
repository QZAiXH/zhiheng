"""CLI boundary tests: capability/proof simulated; no remote request."""
import contextlib
import io
import json
import sys
from pathlib import Path
from unittest.mock import patch
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import test_local_audit as fixture
from harness import cli
from harness.state import Blocked

class SourcePushCLI(unittest.TestCase):
    commit=fixture.LocalAudit.commit
    tearDown=fixture.LocalAudit.tearDown
    def setUp(self):
        fixture.LocalAudit.setUp(self)
        self.config={'mode':'github','repository_root':str(self.root),'repository':'owner/repo','github':{'target_branch':'main'},'checks':self.checks,'environment':{},'limits':dict(fixture.LIMITS,task_attempts=3,repair_attempts=2)}
        self.task={'id':'feature','source':'feature','target':'main','spec':'spec.md'}
    def invoke(self, params, capability_error=False):
        args=['github','--bundle','fixture','--run','source-cli','push-source','--args',json.dumps(params)]
        with patch.object(cli,'load',return_value={'config':self.config,'tasks':[self.task]}),patch.object(cli,'preflight',return_value=self.config),patch.object(cli,'require_capabilities',side_effect=Blocked('missing real capability') if capability_error else None),patch.object(cli,'verified_evidence',return_value={'H':'a'*40}),patch.object(cli.local,'check_fresh'),patch('harness.git_transport.push_source',return_value={'status':'source_published'}) as push,contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
            code=cli.main(args)
        return code,push
    def test_exact_bound_source_repo_and_authorization(self):
        code,push=self.invoke({'task_id':'feature','remote':'origin','authorized':True,'use_gh_credentials':True})
        self.assertEqual(code,0)
        self.assertEqual(push.call_args.args[1:],('feature','feature','a'*40,'origin','refs/heads/feature'))
        self.assertEqual(push.call_args.kwargs,{'expected_repository':'owner/repo','expected_hostname':'github.com','authorized':True,'use_gh_credentials':True})
    def test_server_url_is_normalized_for_actual_destination(self):
        for server, hostname in (("https://github.com", "github.com"), ("https://git.enterprise.example", "git.enterprise.example")):
            self.config['github']['server']=server
            code,push=self.invoke({'task_id':'feature','remote':'origin','authorized':True})
            self.assertEqual(code,0)
            self.assertEqual(push.call_args.kwargs['expected_hostname'],hostname)
    def test_source_cannot_publish_directly_to_delivery_target(self):
        self.task['source']='main'
        code,push=self.invoke({'task_id':'feature','remote':'origin','authorized':True})
        self.assertEqual(code,1);push.assert_not_called()
    def test_wrong_destination_never_reaches_transport(self):
        code,push=self.invoke({'task_id':'feature','remote':'origin','remote_ref':'refs/heads/main','authorized':True})
        self.assertEqual(code,1);push.assert_not_called()
    def test_missing_live_capabilities_never_reaches_transport(self):
        code,push=self.invoke({'task_id':'feature','remote':'origin','authorized':True},True)
        self.assertEqual(code,1);push.assert_not_called()
    def test_local_mode_never_reaches_transport(self):
        self.config['mode']='local'
        code,push=self.invoke({'task_id':'feature','remote':'origin','authorized':True})
        self.assertEqual(code,1);push.assert_not_called()
