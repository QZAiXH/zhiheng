"""Real process/Git lifecycle; platform behavior is a local fake command only."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_local_audit as fixtures
from harness.github import controlled_runner
from harness.runtime import Controller, owned
from harness.state import Blocked

PACKAGE = Path(__file__).resolve().parents[2] / "skills/harness-init/assets/project"
LIMITS = {"command_seconds": 5, "request_seconds": 5, "total_seconds": 50,
          "max_attempts": 100, "stop_grace_seconds": 0.3}


class SupervisedCommands(unittest.TestCase):
    commit = fixtures.LocalAudit.commit
    setUp = fixtures.LocalAudit.setUp
    tearDown = fixtures.LocalAudit.tearDown

    def controller(self):
        return Controller(self.root, "local", "supervised-run", dict(LIMITS))

    def test_platform_runner_preserves_raw_exit_stdout_stderr_and_budget(self):
        with self.controller() as controller:
            result = controlled_runner(controller)([sys.executable, "-c",
                "import sys; print('out'); print('err',file=sys.stderr); raise SystemExit(7)"], 2)
            self.assertEqual(result.returncode, 7)
            self.assertEqual(result.stdout.strip(), "out")
            self.assertEqual(result.stderr.strip(), "err")
            state = controller.state.read()
            self.assertEqual(state["attempts"][-1]["exit_code"], 7)
            self.assertTrue(state["attempts"][-1]["stopped"])
            self.assertGreater(state["spent_seconds"], 0)

    def test_platform_timeout_is_not_remote_failure_or_success(self):
        with self.controller() as controller:
            with self.assertRaises(subprocess.TimeoutExpired):
                controlled_runner(controller)([sys.executable, "-c", "import time; time.sleep(30)"], 0.1)
            self.assertEqual(controller.state.read()["attempts"][-1]["reason"], "timeout")
            self.assertTrue(controller.state.read()["attempts"][-1]["stopped"])

    def _crash_and_assert_takeover_blocked(self, operation, min_processes=1):
        code = ("import sys;sys.path.insert(0,%r); from harness.runtime import Controller; "
                "from harness.github import controlled_runner; c=Controller(%r,'local','supervised-run',%r); "
                "c.__enter__(); %s") % (str(PACKAGE), str(self.root), LIMITS, operation)
        process = subprocess.Popen([sys.executable, "-c", code], start_new_session=True,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        identities = []
        try:
            journal = self.root / ".git/harness.execution.json"
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                if journal.exists():
                    identities = json.loads(journal.read_text()).get("processes", [])
                    if len(identities) >= min_processes:
                        break
                time.sleep(0.01)
            self.assertGreaterEqual(len(identities), min_processes, "fixture command was not journaled")
            process.kill()
            process.communicate(timeout=3)
            self.assertTrue(any(owned(item) for item in identities), "fixture writer did not survive controller crash")
            with self.assertRaises(Blocked):
                with self.controller():
                    self.fail("unreconciled writer was bypassed")
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate(timeout=3)
            if identities and any(owned(item) for item in identities):
                try:
                    os.killpg(identities[0]["pid"], signal.SIGKILL)
                except ProcessLookupError:
                    pass
            for item in identities:
                child = owned(item)
                if child:
                    child.kill()

    def test_platform_runner_child_survives_controller_crash_but_blocks_takeover(self):
        self._crash_and_assert_takeover_blocked(
            "controlled_runner(c)([sys.executable,'-c','import time;time.sleep(30)'],5)")

    def test_real_git_with_running_hook_is_journaled_across_controller_crash(self):
        hooks = Path(self.tmp.name) / "hooks"
        hooks.mkdir()
        hook = hooks / "post-checkout"
        hook.write_text("#!/bin/sh\nsleep 30\n")
        hook.chmod(0o700)
        fixtures.git(self.root, "config", "core.hooksPath", str(hooks))
        self._crash_and_assert_takeover_blocked("c.git('checkout','feature')", min_processes=2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
