"""Test portable probe orchestration with a FAKE Codex binary, never a model."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class HostProbeTests(unittest.TestCase):
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
    print('FAKE help'); raise SystemExit(0)
assert '--sandbox' in args and not any('bypass' in x for x in args)
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
                                     "--output", str(output)], capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            summary = json.loads((output / "summary.json").read_text())
            self.assertEqual(summary["created_session_id"], "fixture-session-exact")
            names = {row["name"] for row in summary["steps"]}
            self.assertTrue({"implement", "independent-review", "exact-session-resume", "fresh-context-handoff"} <= names)
            self.assertIn("cancellation/descendant shutdown", summary["not_certified"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
