"""Test portable probe orchestration with a FAKE Codex binary, never a model."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class HostProbeTests(unittest.TestCase):
    def test_model_mode_requires_explicit_model_and_budget_before_writes(self):
        with tempfile.TemporaryDirectory(prefix="host-probe-guard-") as directory:
            output = Path(directory) / "result"
            for options in ([], ["--model", "gpt-6.1-sol"], ["--max-model-calls", "4"],
                            ["--model", " ", "--max-model-calls", "4"],
                            ["--model", "gpt-6.1-sol", "--max-model-calls", "0"],
                            ["--model", "gpt-6.1-sol", "--max-model-calls", "5"]):
                with self.subTest(options=options):
                    result = subprocess.run([sys.executable, str(ROOT / "scripts/codex-host-acceptance.py"),
                        "--run-models", "--codex", "/nonexistent/must-not-run", "--output", str(output), *options],
                        capture_output=True, text=True, timeout=5)
                    self.assertEqual(result.returncode, 2, result.stderr)
                    self.assertFalse(output.exists())

    def test_prepare_only_never_invokes_codex(self):
        with tempfile.TemporaryDirectory(prefix="host-probe-free-") as directory:
            output = Path(directory) / "result"
            result = subprocess.run([sys.executable, str(ROOT / "scripts/codex-host-acceptance.py"),
                "--codex", "/nonexistent/must-not-run", "--output", str(output)],
                capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            summary = json.loads((output / "summary.json").read_text())
            self.assertEqual(summary["status"], "prepared")
            self.assertEqual(summary["model_calls_started"], 0)
            self.assertFalse(any(row["name"].startswith("codex") for row in summary["steps"]))

    def test_prepare_only_and_fake_cli_protocol(self):
        with tempfile.TemporaryDirectory(prefix="host-probe-selftest-") as directory:
            directory = Path(directory)
            fake = directory / "fake-codex"
            fake.write_text("#!" + sys.executable + "\n" + '''
import json, pathlib, sys
args=sys.argv[1:]
if '--version' in args:
    print('FAKE codex: protocol test only'); raise SystemExit(0)
if '--help' in args:
    print('FAKE help --model --config'); raise SystemExit(0)
assert '--sandbox' in args and not any('bypass' in x for x in args)
assert args[args.index('--model')+1]=='gpt-6.1-sol'
for option in ('review_model="gpt-6.1-sol"','model_reasoning_effort="low"','service_tier="default"'):
    assert option in args, args
if pathlib.Path(__file__).with_name('fail-model').exists(): raise SystemExit(7)
text='AC-POS AC-NEG fixture passed'
if 'resume' in args:
    assert args[args.index('resume')+1]=='fixture-session-exact'
    assert '--last' not in args
elif 'review' not in args and 'handoff.md' not in args[-1]:
    pathlib.Path('calculator.py').write_text('def add(a, b):\\n    return a + b\\n')
    text='HOST_SKILL_LOADED '+text
if '--output-last-message' in args:
    pathlib.Path(args[args.index('--output-last-message')+1]).write_text(text)
print(json.dumps({'type':'thread.started','thread_id':'fixture-session-exact'}))
''')
            fake.chmod(0o700)
            output = directory / "result"
            result = subprocess.run([sys.executable, str(ROOT / "scripts/codex-host-acceptance.py"),
                                     "--run-models", "--codex", str(fake), "--timeout", "10",
                                     "--model", "gpt-6.1-sol", "--max-model-calls", "4",
                                     "--output", str(output)], capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            summary = json.loads((output / "summary.json").read_text())
            self.assertEqual(summary["created_session_id"], "fixture-session-exact")
            names = {row["name"] for row in summary["steps"]}
            self.assertTrue({"implement", "independent-review", "exact-session-resume", "fresh-context-handoff"} <= names)
            self.assertIn("cancellation/descendant shutdown", summary["not_certified"])
            self.assertEqual(summary["model_calls_started"], 4)
            self.assertEqual(summary["limits"]["script_retries"], 0)
            calls = [row for row in summary["steps"] if "model_call_number" in row]
            self.assertEqual([row["model_call_number"] for row in calls], [1, 2, 3, 4])
            for row in calls:
                self.assertEqual(row["model_policy"]["model"], "gpt-6.1-sol")
                self.assertEqual(row["model_policy"]["reasoning_effort"], "low")
                self.assertEqual(row["model_policy"]["service_tier"], "default")

            # One allowed invocation cannot accidentally run review/resume.
            limited = directory / "limited"
            argv = [sys.executable, str(ROOT / "scripts/codex-host-acceptance.py"),
                    "--run-models", "--codex", str(fake), "--timeout", "10",
                    "--model", "gpt-6.1-sol", "--max-model-calls", "1", "--output", str(limited)]
            result = subprocess.run(argv, capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 1)
            summary = json.loads((limited / "summary.json").read_text())
            self.assertEqual(summary["model_calls_started"], 1)
            self.assertIn("budget exhausted", summary["reason"])
            self.assertNotIn("independent-review", [row["name"] for row in summary["steps"]])

            # A failed start is charged once and never retried.
            fake.with_name("fail-model").touch()
            failed = directory / "failed"
            argv[-1] = str(failed)
            result = subprocess.run(argv, capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 1)
            summary = json.loads((failed / "summary.json").read_text())
            self.assertEqual(summary["model_calls_started"], 1)
            calls = [row for row in summary["steps"] if "model_call_number" in row]
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0]["exit_code"], 7)


if __name__ == "__main__":
    unittest.main(verbosity=2)
