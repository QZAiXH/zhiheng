"""Protocol tests with an explicitly simulated executable; never live-host acceptance."""
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2] / "skills/harness-init/assets/project"
sys.path.insert(0, str(PROJECT))
from harness.codex_probe import ProbeFailed, parse_events, run_host_drills
from harness.p0 import probe
from harness.runtime import Controller
from harness.state import Blocked

SIMULATOR = r'''
import json,re,sys,uuid,subprocess,time,shlex
from pathlib import Path
args=sys.argv[1:]
home=Path(__file__).parent
settings=json.loads((home/'behavior.json').read_text()) if (home/'behavior.json').exists() else {}
with (home/'calls.jsonl').open('a') as f:f.write(json.dumps(args)+'\n')
if '--version' in args:print('codex-cli SIMULATED TEST EXECUTABLE');sys.exit(0)
if '--help' in args:print('SIMULATED help');sys.exit(0)
assert args[args.index('--model')+1] == 'gpt-6.1-sol'
for option in ('review_model="gpt-6.1-sol"','model_reasoning_effort="low"','service_tier="default"'):
 assert option in args, args
def event(x):print(json.dumps(x),flush=True)
if settings.get('auth_fail'):
 event({'type':'error','message':'simulated authentication failure'});sys.exit(1)
statefile=home/'state.json'
prompt=args[-1]
if 'resume' in args:
 state=json.loads(statefile.read_text());sid=state['id'];nonce=state['nonce']
 text='HARNESS_P0_RESUME:'+('wrong' if settings.get('wrong_resume') else nonce)
elif 'bounded local cancellation drill' in prompt:
 sid=str(uuid.uuid4());event({'type':'thread.started','thread_id':sid})
 argv=json.JSONDecoder().raw_decode(prompt.split('Exact argv: ',1)[1])[0]
 if not settings.get('omit_cancel_trace'):
  event({'type':'item.started','item':{'type':'command_execution','status':'in_progress','command':shlex.join(argv)}})
 if settings.get('omit_cancel_child'):
  time.sleep(10)
 else:
  subprocess.Popen(argv).wait()
 sys.exit(0)
elif 'independent review session' in prompt:
 state=json.loads(statefile.read_text());sid=state['id'] if settings.get('same_review_session') else str(uuid.uuid4())
 source=Path('fixture.py').read_text();spec=Path('acceptance.md').read_text()
 event({'type':'thread.started','thread_id':sid})
 if not settings.get('omit_reads'):
  event({'type':'item.completed','item':{'type':'command_execution','status':'completed','exit_code':0,
       'command':'cat fixture.py acceptance.md','aggregated_output':source+spec}})
 text=json.dumps({'acceptance_id':'AC-discount','status':'passed' if settings.get('miss_bug') else 'failed',
       'actual':110,'expected':90,'finding':'The addition at line 2 raises the subtotal instead of subtracting the discount.',
       'location':'fixture.py:2'})
 event({'type':'item.completed','item':{'type':'agent_message','text':text}})
 event({'type':'turn.completed'});sys.exit(0)
else:
 sid=str(uuid.uuid4());nonce=re.search(r'Remember the nonce ([0-9a-f]+)',prompt).group(1)
 statefile.write_text(json.dumps({'id':sid,'nonce':nonce}))
 text='WRONG' if settings.get('wrong_start') else 'HARNESS_P0_START:'+nonce
event({'type':'thread.started','thread_id':sid})
event({'type':'item.completed','item':{'type':'agent_message','text':text}})
event({'type':'turn.completed'})
'''


def host_drill_diagnostics(result):
    """Keep report evidence in assertion failures after temporary files are removed."""
    summary = {key: result.get(key) for key in ("calls_started", "call_limit", "report_path")}
    steps = {}
    for step, name in (("start", "host_session_start"), ("review", "host_independent_review"),
                       ("resume", "host_session_resume"), ("cancel", "host_native_stop")):
        capability = (result.get("host_native_stop", {}) if step == "cancel"
                      else result.get("capabilities", {}).get(name, {}))
        log = result.get("logs", {}).get(step, {})
        execution = log.get("execution", {})
        steps[step] = {key: capability.get(key) for key in ("status", "detail")}
        steps[step].update({key: execution.get(key) for key in ("exit_code", "reason", "stopped")})
        if "error" in log:
            steps[step]["error"] = log["error"]
    summary["steps"] = steps
    return "host drill report: " + json.dumps(summary, ensure_ascii=False, sort_keys=True)


class CodexProbeProtocolTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.repo = self.base / "probe-repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "--template=", str(self.repo)], check=True, capture_output=True)
        self.project = self.base / "user-project"
        self.project.mkdir()
        tool = self.base / "simulated-tool"
        tool.mkdir()
        self.executable = tool / "codex-fixture"
        self.executable.write_text("#!" + sys.executable + "\n" + SIMULATOR)
        self.executable.chmod(0o700)
        self.output = self.base / "artifacts"
        self.limits = {"command_seconds": 2, "stop_grace_seconds": 0.1, "total_seconds": 30, "max_attempts": 8}

    def behavior(self, **options):
        (self.executable.parent / "behavior.json").write_text(json.dumps(options))

    def run_drills(self, cancel_options=None, model="gpt-6.1-sol", max_model_calls=4):
        with Controller(self.repo, "local", "protocol-test", self.limits) as controller:
            return run_host_drills(controller, str(self.executable), str(self.output),
                project_root=self.project, timeout_seconds=2, config_sha256="a"*64,
                declared_environment_sha256="b"*64, model=model, max_model_calls=max_model_calls,
                cancel_options=cancel_options)

    def test_missing_or_invalid_model_budget_blocks_before_calls_or_artifacts(self):
        for model, budget in ((None, 4), ("", 4), (" ", 4), ("gpt-6.1-sol", None),
                              ("gpt-6.1-sol", True), ("gpt-6.1-sol", 0), ("gpt-6.1-sol", 5)):
            with self.subTest(model=model, budget=budget):
                with self.assertRaises(Blocked):
                    self.run_drills(model=model, max_model_calls=budget)
        self.assertFalse((self.executable.parent/'calls.jsonl').exists())
        self.assertFalse(self.output.exists())

    def test_explicit_one_call_budget_never_starts_review_or_resume(self):
        result = self.run_drills(max_model_calls=1)
        diagnostic = host_drill_diagnostics(result)
        self.assertEqual(result["calls_started"], 1, msg=diagnostic)
        self.assertEqual(result["call_limit"], 1, msg=diagnostic)
        self.assertEqual(set(result["logs"]), {"start"}, msg=diagnostic)
        self.assertEqual(result["capabilities"]["host_session_start"]["status"], "verified", msg=diagnostic)
        self.assertEqual(result["capabilities"]["host_independent_review"]["status"], "blocked", msg=diagnostic)
        self.assertEqual(result["capabilities"]["host_session_resume"]["status"], "blocked", msg=diagnostic)

    def test_explicit_fourth_simulated_owned_cancellation_proof(self):
        result = self.run_drills({"startup_seconds": 1, "total_seconds": 1.5, "sleep_seconds": 5})
        diagnostic = host_drill_diagnostics(result)
        self.assertEqual(result["calls_started"], 4, msg=diagnostic)
        cancellation = result["host_native_stop"]
        self.assertEqual(cancellation["status"], "verified", msg=diagnostic)
        self.assertTrue(cancellation["observation"]["signal_sent"], msg=diagnostic)
        self.assertTrue(cancellation["observation"]["all_recorded_processes_stopped"], msg=diagnostic)
        self.assertFalse(cancellation["remote_cancellation_verified"], msg=diagnostic)
        self.assertEqual(cancellation["scope"], "configured_local_cli_and_owned_descendants", msg=diagnostic)
        self.assertTrue(Path(cancellation["fixture"]["path"]).exists(), msg=diagnostic)
        self.assertIn("cancel", result["logs"], msg=diagnostic)

    def test_cancellation_trace_without_real_owned_child_is_not_proof(self):
        self.behavior(omit_cancel_child=True)
        result = self.run_drills({"startup_seconds": 0.5, "total_seconds": 1, "sleep_seconds": 5})
        self.assertEqual(result["host_native_stop"]["status"], "blocked")
        self.assertFalse(result["host_native_stop"]["observation"]["signal_sent"])

    def test_real_child_without_command_trace_is_not_host_proof(self):
        self.behavior(omit_cancel_trace=True)
        result = self.run_drills({"startup_seconds": 0.5, "total_seconds": 1, "sleep_seconds": 5})
        self.assertEqual(result["host_native_stop"]["status"], "blocked")
        self.assertFalse(result["host_native_stop"]["observation"]["signal_sent"])

    def test_cancel_limits_fail_before_any_model_call(self):
        for limits in ({}, {"startup_seconds": 0, "total_seconds": 1, "sleep_seconds": 5},
                       {"startup_seconds": 2, "total_seconds": 1, "sleep_seconds": 5},
                       {"startup_seconds": 1, "total_seconds": 2, "sleep_seconds": 1}):
            with self.subTest(limits=limits):
                with self.assertRaises(Blocked):
                    self.run_drills(limits)
        self.assertFalse((self.executable.parent/'calls.jsonl').exists())

    def test_simulated_protocol_success_three_calls_and_hashes(self):
        result = self.run_drills()
        diagnostic = host_drill_diagnostics(result)
        self.assertEqual(result["calls_started"], 3, msg=diagnostic)
        for capability in result["capabilities"].values():
            self.assertEqual(capability["status"], "verified", msg=diagnostic)
        self.assertEqual(result["host_native_stop"]["status"], "blocked", msg=diagnostic)
        for item in result["logs"].values():
            self.assertEqual(hashlib.sha256(Path(item["path"]).read_bytes()).hexdigest(), item["sha256"], msg=diagnostic)
            self.assertEqual(item["argv"][item["argv"].index("--model")+1], "gpt-6.1-sol", msg=diagnostic)
            self.assertEqual(item["model_policy"]["reasoning_effort"], "low", msg=diagnostic)
            self.assertEqual(item["argv"][item["argv"].index("--disable")+1], "multi_agent", msg=diagnostic)
            self.assertFalse(item["model_policy"]["multi_agent"], msg=diagnostic)
            self.assertEqual(item["model_policy"]["service_tier"], "default", msg=diagnostic)
            self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", item["argv"], msg=diagnostic)
            self.assertIn("read-only", item["argv"], msg=diagnostic)
        self.assertEqual(hashlib.sha256(Path(result["report_path"]).read_bytes()).hexdigest(), result["report_sha256"], msg=diagnostic)
        self.assertEqual(list(self.project.iterdir()), [], msg=diagnostic)
        state=json.loads((self.executable.parent/'state.json').read_text())
        self.assertNotIn(state['nonce'], result['logs']['resume']['argv'][-1], msg=diagnostic)
        self.assertIn(state['id'], result['logs']['resume']['argv'], msg=diagnostic)

    def test_auth_failure_blocks_and_preserves_raw_log(self):
        self.behavior(auth_fail=True)
        result = self.run_drills()
        self.assertEqual(result["calls_started"], 1)
        self.assertEqual(result["capabilities"]["host_session_start"]["status"], "blocked")
        self.assertTrue(Path(result["logs"]["start"]["path"]).exists())

    def test_wrong_start_marker_is_not_success(self):
        self.behavior(wrong_start=True)
        result = self.run_drills()
        self.assertEqual(result["calls_started"], 1)
        self.assertEqual(result["capabilities"]["host_session_start"]["status"], "blocked")

    def test_independent_review_requires_new_session_actual_reads_and_bug(self):
        for flag in ("same_review_session", "omit_reads", "miss_bug"):
            with self.subTest(flag=flag):
                # Separate controller/task workspace for each run; never reuse an attempt.
                if flag != "same_review_session":
                    self.repo = self.base / ("repo-" + flag)
                    self.repo.mkdir()
                    subprocess.run(["git", "init", "--template=", str(self.repo)], check=True, capture_output=True)
                self.behavior(**{flag: True})
                result = self.run_drills()
                self.assertEqual(result["capabilities"]["host_independent_review"]["status"], "blocked")
                self.assertEqual(result["capabilities"]["host_session_resume"]["status"], "verified")
                self.assertEqual(result["calls_started"], 3)

    def test_resume_must_recall_original_nonce(self):
        self.behavior(wrong_resume=True)
        self.assertEqual(self.run_drills()["capabilities"]["host_session_resume"]["status"], "blocked")

    def test_output_inside_user_project_requires_matching_controller(self):
        self.output = self.project / "artifacts"
        with self.assertRaises(Blocked):
            self.run_drills()
        self.assertFalse(self.output.exists())

    def test_json_parser_rejects_missing_and_conflicting_session_events(self):
        session="01234567-89ab-cdef-0123-456789abcdef"
        valid=[{"type":"thread.started","thread_id":session},
               {"type":"item.completed","item":{"type":"agent_message","text":"final"}},
               {"type":"turn.completed"}]
        def encode(events):return "\n".join(json.dumps(x) for x in events).encode()
        self.assertEqual(parse_events(encode(valid))["thread_id"], session)
        for events in (valid[1:], valid[:-1], valid+[{'type':'thread.started','thread_id':'11234567-89ab-cdef-0123-456789abcdef'}],
                       valid+[{'type':'turn.failed'}]):
            with self.assertRaises(ProbeFailed):parse_events(encode(events))

    def test_p0_integration_gates_real_calls_and_never_fake_readiness(self):
        config={"mode":"local","repository_root":str(self.project),"environment":{"host":"SIMULATED TEST"},
                "limits":{"command_seconds":2,"stop_grace_seconds":0.1,"task_seconds":30},
                "p0":{"max_commands":8,"run_host_drills":True,"output_dir":str(self.output),
                      "model":"gpt-6.1-sol","max_model_calls":3,
                      "executables":{"codex":str(self.executable)}}}
        # Protocol-only integration: native prerequisites are explicitly simulated.
        with patch("harness.p0._host_prerequisites", return_value=[]):
            result=probe(config)
        self.assertEqual(result["host_drills"]["calls_started"],3)
        self.assertEqual(result["capabilities"]["host_session_resume"]["status"],"verified")
        self.assertEqual(result["capabilities"]["host_native_stop"]["status"],"blocked")
        self.assertEqual(result["automation_readiness"]["status"],"blocked")
        self.assertFalse(result["changes_ready"])

    def test_p0_missing_explicit_model_never_starts_model(self):
        config={"mode":"local","repository_root":str(self.project),"environment":{"host":"SIMULATED TEST"},
                "limits":{"command_seconds":2,"stop_grace_seconds":0.1,"task_seconds":30},
                "p0":{"max_commands":8,"run_host_drills":True,"output_dir":str(self.output),
                      "max_model_calls":3,"executables":{"codex":str(self.executable)}}}
        result=probe(config)
        self.assertEqual(result["capabilities"]["host_command_smoke"]["status"], "blocked")
        self.assertIn("explicit nonempty model", result["capabilities"]["host_command_smoke"]["detail"])
        self.assertFalse((self.executable.parent/'calls.jsonl').exists())
        self.assertEqual(0, result["host_dispatch"]["calls_started"])

    def test_optional_smoke_has_same_model_guard_and_records_explicit_policy(self):
        config={"mode":"local","repository_root":str(self.project),"environment":{"host":"SIMULATED TEST"},
                "limits":{"command_seconds":2,"stop_grace_seconds":0.1,"task_seconds":30},
                "p0":{"max_commands":8,"executables":{"codex":str(self.executable)},
                      "smoke_argv":[str(self.executable),"exec","--sandbox","read-only","--json","--cd",
                                    "{worktree}","Remember the nonce abc123"]}}
        result=probe(config)
        self.assertEqual(result["capabilities"]["host_command_smoke"]["status"], "blocked")
        self.assertIn("explicit nonempty model", result["capabilities"]["host_command_smoke"]["detail"])
        self.assertFalse((self.executable.parent/'state.json').exists())
        config["p0"].update(model="gpt-6.1-sol", max_model_calls=1)
        # Native prerequisites are mocked only to isolate the fake-host smoke protocol.
        with patch("harness.p0._host_prerequisites", return_value=[]):
            result=probe(config)
        self.assertEqual(result["capabilities"]["host_command_smoke"]["status"], "verified")
        self.assertEqual(result["host_smoke_policy"]["calls_started"], 1)
        self.assertEqual(result["host_smoke_policy"]["service_tier"], "default")

    def test_smoke_and_host_drills_are_rejected_together_before_execution(self):
        config={"mode":"local","repository_root":str(self.project),"environment":{"host":"SIMULATED TEST"},
                "limits":{"command_seconds":2,"stop_grace_seconds":0.1,"task_seconds":30},
                "p0":{"run_host_drills":True,"model":"gpt-6.1-sol","max_model_calls":4,
                      "output_dir":str(self.output),"executables":{"codex":str(self.executable)},
                      "smoke_argv":[str(self.executable),"exec","--sandbox","read-only","--json","--cd",
                                    "{worktree}","Remember the nonce abc123"]}}
        result=probe(config)
        self.assertEqual(result["capabilities"]["configuration"]["status"], "blocked")
        self.assertIn("mutually exclusive", result["capabilities"]["configuration"]["detail"])
        self.assertFalse((self.executable.parent/'calls.jsonl').exists())
        self.assertFalse(self.output.exists())


if __name__ == '__main__':unittest.main()
