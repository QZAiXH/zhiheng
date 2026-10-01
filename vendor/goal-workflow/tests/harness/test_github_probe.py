"""Read-only GitHub protocol tests using a simulated gh, with no live API calls."""
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2] / "skills/harness-init/assets/project"
sys.path.insert(0, str(PROJECT))
from harness.github_probe import probe_github
from harness.runtime import Controller
from harness.state import Blocked

SIMULATED_GH = r'''
import base64,json,sys,time
from pathlib import Path
args=sys.argv[1:];home=Path(__file__).parent
settings=json.loads((home/'behavior.json').read_text()) if (home/'behavior.json').exists() else {}
with (home/'calls.jsonl').open('a') as f:f.write(json.dumps(args)+'\n')
def emit(value):print(json.dumps(value));sys.exit(0)
def fail(message):print(message,file=sys.stderr);sys.exit(1)
if args==['--version']:print('gh SIMULATED TEST');sys.exit(0)
if args[:2]==['auth','status']:
 if settings.get('auth_fail'):fail('simulated authentication failure')
 print('simulated authenticated test account');sys.exit(0)
if args[0]!='api':fail('MUTATION OR UNKNOWN COMMAND REFUSED BY FIXTURE')
endpoint=next((arg for arg in args[1:] if arg=='user' or arg.startswith('repos/')),None)
if settings.get('slow_user') and endpoint=='user':time.sleep(10)
sha='a'*40;queue='b'*40
issue={'number':7,'title':'Pilot fixture task','body':'','state':'open','repository_url':'https://api.github.com/repos/example/project','html_url':'https://github.com/example/project/issues/7'}
pr={'number':13,'head':{'sha':'d'*40},'base':{'sha':sha,'ref':'main'}}
if endpoint=='user':emit({'login':'test-fixture-user','id':1})
if endpoint=='repos/example/project':emit({'full_name':'example/project','permissions':{'pull':True,'push':not settings.get('no_push')},'archived':False,'disabled':False})
if endpoint=='repos/example/project/branches/main':
 state=home/'branch-count';count=int(state.read_text())+1 if state.exists() else 1;state.write_text(str(count))
 emit({'name':'main','commit':{'sha':'f'*40 if settings.get('target_advanced') and count>1 else sha}})
if '/issues?' in endpoint:emit([[],[] if settings.get('no_tasks') else [issue]])
if '/issues/7/dependencies/blocked_by?' in endpoint:
 if settings.get('dependency_error'):fail('simulated dependency permission failure')
 emit([[]])
if endpoint.endswith('/issues/7'):emit(issue)
if '/pulls?' in endpoint:emit([[pr]])
if endpoint.endswith('/pulls/13'):emit(pr)
if '/check-runs?' in endpoint:
 actual=endpoint.split('/commits/',1)[1].split('/',1)[0]
 emit([{'check_runs':[] if settings.get('missing_checks') else [{'id':3,'name':'unit','head_sha':actual,'status':'completed','conclusion':'success','html_url':'https://github.com/example/project/checks/3'}]}])
if '/statuses?' in endpoint:emit([[]])
if '/rules/branches/' in endpoint:
 if settings.get('rules_error'):fail('simulated rules inaccessible')
 rows=[] if settings.get('missing_rules') else [{'type':'required_status_checks','parameters':{'strict_required_status_checks_policy':True,'required_status_checks':[{'context':'unit'}]}}]
 if settings.get('queue'):rows.append({'type':'merge_queue','parameters':{}})
 emit([rows])
if '/actions/workflows?' in endpoint:
 emit([{'workflows':[] if settings.get('no_workflows') else [{'id':9,'name':'CI','path':'.github/workflows/ci.yml','state':'active'}]}])
if '/contents/.github/workflows/ci.yml?' in endpoint:
 content='on: [pull_request, merge_group]\njobs:\n  unit: {}\n'
 if settings.get('changed_queue_workflow') and ('ref='+queue) in endpoint:content='old workflow content\n'
 emit({'type':'file','encoding':'base64','sha':'c'*40,'content':base64.b64encode(content.encode()).decode()})
if '/actions/runs?event=merge_group' in endpoint:
 emit([{'workflow_runs':[] if settings.get('no_merge_group') else [{'id':11,'workflow_id':9,'event':'merge_group','status':'completed','conclusion':'success','head_sha':queue,'head_branch':'gh-readonly-queue/main/pr-13-fixture','pull_requests':[]}]}])
fail('Unknown simulated endpoint: '+str(endpoint))
'''


class GitHubP0Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.repo = self.base / 'controller'
        self.repo.mkdir()
        subprocess.run(['git','init','--template=',str(self.repo)],check=True,capture_output=True)
        self.project = self.base / 'project'
        self.project.mkdir()
        tool=self.base/'simulated-gh';tool.mkdir()
        self.executable=tool/'gh-fixture'
        self.executable.write_text('#!'+sys.executable+'\n'+SIMULATED_GH)
        self.executable.chmod(0o700)
        self.config={'mode':'github','repository_root':str(self.project),
                     'github':{'repository':'example/project','server':'github.com','target_branch':'main',
                               'baseline_policy':'strict','required_checks':['unit']},
                     'limits':{'request_seconds':1,'ci_wait_seconds':20},
                     'p0':{'github_max_requests':50,'github_total_seconds':20}}
        self.limits={'command_seconds':1,'stop_grace_seconds':0.1,'total_seconds':30,'max_attempts':50}

    def behavior(self,**options):
        (self.executable.parent/'behavior.json').write_text(json.dumps(options))

    def run_probe(self):
        with Controller(self.repo,'local','github-protocol-test',self.limits) as controller:
            return probe_github(self.config,controller,str(self.base/'artifacts'),executable=str(self.executable))

    def test_strict_auth_reads_and_actual_server_rules_separately_verified(self):
        result=self.run_probe()
        self.assertEqual(result['status'],'verified',result)
        self.assertEqual(result['automatic_merge_rules']['status'],'verified',result)
        self.assertEqual(result['observations']['task_listing']['count'],1)
        self.assertTrue(result['observations']['pull_requests']['read_sample_observed'])
        self.assertTrue(result['observations']['target_checks']['all_required_passed'])
        self.assertEqual(list(self.project.iterdir()),[])
        self.assertEqual(hashlib.sha256(Path(result['report_path']).read_bytes()).hexdigest(),result['report_sha256'])
        for item in result['logs'].values():
            for label in ('stdout','stderr'):
                self.assertEqual(hashlib.sha256(Path(item[label]['path']).read_bytes()).hexdigest(),item[label]['sha256'])
            self.assertTrue(item['argv'][1:3]==['auth','status'] or item['argv'][1]=='api')
            self.assertNotIn('--method',item['argv'])
            self.assertNotIn('--show-token',item['argv'])

    def test_review_only_survives_missing_rules_checks_workflows(self):
        self.config['github']['baseline_policy']='review_only'
        self.behavior(rules_error=True,missing_checks=True,no_workflows=True)
        result=self.run_probe()
        self.assertEqual(result['status'],'verified',result)
        self.assertEqual(result['automatic_merge_rules']['status'],'not_applicable')
        self.assertFalse(result['observations']['target_checks']['all_required_passed'])
        calls=(self.executable.parent/'calls.jsonl').read_text()
        self.assertNotIn('/rules/branches/',calls)

    def test_missing_rules_only_blocks_automatic_merge(self):
        self.behavior(missing_rules=True)
        result=self.run_probe()
        self.assertEqual(result['status'],'verified',result)
        self.assertEqual(result['automatic_merge_rules']['status'],'blocked')

    def test_rule_access_failure_preserves_read_handoff_capability(self):
        self.behavior(rules_error=True)
        result=self.run_probe()
        self.assertEqual(result['status'],'verified',result)
        self.assertEqual(result['automatic_merge_rules']['status'],'blocked')

    def test_missing_business_checks_not_mislabeled_passed(self):
        self.behavior(missing_checks=True)
        result=self.run_probe()
        self.assertEqual(result['status'],'verified',result)
        self.assertFalse(result['observations']['target_checks']['all_required_passed'])
        self.assertEqual(result['automatic_merge_rules']['status'],'blocked')

    def test_auth_or_permissions_failure_blocks_authenticated_capability(self):
        self.behavior(auth_fail=True)
        result=self.run_probe()
        self.assertEqual(result['status'],'blocked')
        self.assertIn('authentication',result['detail'])
        self.assertTrue(result['logs'])

    def test_no_existing_task_blocks_task_read_proof(self):
        self.behavior(no_tasks=True)
        result=self.run_probe()
        self.assertEqual(result['status'],'blocked')
        self.assertIn('existing task',result['detail'])

    def test_native_dependency_read_failure_never_means_empty(self):
        self.behavior(dependency_error=True)
        result=self.run_probe()
        self.assertEqual(result['status'],'blocked')
        self.assertIn('dependency permission',result['detail'])

    def test_configured_rules_verified_boolean_is_ignored(self):
        self.config['github']['rules_verified']=True
        self.behavior(missing_rules=True)
        self.assertEqual(self.run_probe()['automatic_merge_rules']['status'],'blocked')

    def test_queue_requires_real_event_and_unchanged_workflow_source(self):
        self.config['github']['baseline_policy']='merge_queue'
        self.behavior(queue=True)
        result=self.run_probe()
        self.assertEqual(result['automatic_merge_rules']['status'],'verified',result)
        self.assertEqual(result['observations']['merge_group']['event'],'merge_group')

    def test_queue_missing_merge_group_cannot_be_claimed(self):
        self.config['github']['baseline_policy']='merge_queue'
        self.behavior(queue=True,no_merge_group=True)
        result=self.run_probe()
        self.assertEqual(result['status'],'verified')
        self.assertEqual(result['automatic_merge_rules']['status'],'blocked')

    def test_queue_workflow_drift_blocks_automatic_capability(self):
        self.config['github']['baseline_policy']='merge_queue'
        self.behavior(queue=True,changed_queue_workflow=True)
        result=self.run_probe()
        self.assertEqual(result['automatic_merge_rules']['status'],'blocked')
        self.assertIn('differs',result['automatic_merge_rules']['detail'])

    def test_target_drift_is_recorded_and_blocks_auto_merge(self):
        self.behavior(target_advanced=True)
        result=self.run_probe()
        self.assertEqual(result['status'],'verified')
        self.assertTrue(result['observations']['target_snapshot_stale'])
        self.assertEqual(result['automatic_merge_rules']['status'],'blocked')

    def test_request_limit_exhaustion_does_not_reset(self):
        self.config['p0']['github_max_requests']=2
        result=self.run_probe()
        self.assertEqual(result['status'],'blocked')
        self.assertIn('request bound',result['detail'])

    def test_timeout_is_blocked_with_owned_process_stopped(self):
        self.behavior(slow_user=True)
        self.config['limits']['request_seconds']=0.15
        result=self.run_probe()
        self.assertEqual(result['status'],'blocked')
        self.assertTrue(any(item.get('execution',{}).get('reason')=='timeout' for item in result['logs'].values()))

    def test_explicit_target_branch_required_before_any_query(self):
        del self.config['github']['target_branch']
        with self.assertRaises(Blocked):self.run_probe()
        self.assertFalse((self.executable.parent/'calls.jsonl').exists())

    def test_local_mode_does_not_need_a_controller_or_gh(self):
        result=probe_github({'mode':'local'},None,None)
        self.assertEqual(result['status'],'not_applicable')
        self.assertFalse((self.executable.parent/'calls.jsonl').exists())


if __name__=='__main__':unittest.main()
