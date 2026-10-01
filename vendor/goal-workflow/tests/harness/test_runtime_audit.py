"""Independent fault tests; all subprocesses and Git edits are isolated fixtures."""
import copy
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "skills/harness-init/assets/project"))
import psutil
from harness.runtime import Controller, identity, owned
from harness.state import Blocked, State

LIMITS = {"command_seconds": 2.0, "total_seconds": 20.0,
          "max_attempts": 20, "stop_grace_seconds": 0.3}


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True,
                                   stderr=subprocess.DEVNULL).strip()


class Audit(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="harness-independent-")
        self.root = Path(self.tmp.name) / "repo"
        self.root.mkdir()
        git(self.root, "init", "-b", "main")
        git(self.root, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
            "commit", "--allow-empty", "-m", "fixture")

    def tearDown(self):
        self.tmp.cleanup()

    def controller(self, root=None):
        return Controller(root or self.root, "local", "audit-run", dict(LIMITS))

    def test_stale_revision_and_attempt_cannot_write(self):
        with self.controller() as controller:
            initial = controller.state.read()
            initial["active"] = {"attempt_id": "current", "processes": [], "stopped": False}
            current = controller.state.write(initial, 0)
            with self.assertRaises(Blocked):
                controller.state.write(current, 0)
            with self.assertRaises(Blocked):
                controller.state.write(current, current["revision"], "old")
            self.assertEqual(controller.state.read(), current)

    def test_budget_and_history_cannot_be_erased(self):
        with self.controller() as controller:
            state = controller.state.read()
            state["spent_seconds"] = 5
            state["attempts"] = [{"attempt_id": "old", "exit_code": 7}]
            state = controller.state.write(state, 0)
            altered = copy.deepcopy(state)
            altered["spent_seconds"] = 0
            with self.assertRaises(Blocked):
                controller.state.write(altered, state["revision"])
            altered = copy.deepcopy(state)
            altered["attempts"] = []
            with self.assertRaises(Blocked):
                controller.state.write(altered, state["revision"])

    def test_live_controller_blocks_related_worktree(self):
        worktree = Path(self.tmp.name) / "second"
        git(self.root, "worktree", "add", "-b", "second", str(worktree))
        with self.controller():
            with self.assertRaises(Blocked):
                with self.controller(worktree):
                    self.fail("concurrent linked worktree acquired run permission")

    def test_orphan_record_blocks_recovery_from_related_worktree(self):
        worktree = Path(self.tmp.name) / "second"
        git(self.root, "worktree", "add", "-b", "second", str(worktree))
        script = ("import sys; sys.path.insert(0,%r); from harness.runtime import Controller; "
                  "c=Controller(%r,'local','audit-run',%r); c.__enter__(); "
                  "c.execute([sys.executable,'-c','import time; time.sleep(30)'],%r,'crash',%r)") % (
                  str(ROOT / "skills/harness-init/assets/project"), str(self.root), LIMITS,
                  str(self.root), str(self.root / "crash.log"))
        process = subprocess.Popen([sys.executable, "-c", script], start_new_session=True)
        identities = []
        try:
            journal = self.root / ".git/harness.execution.json"
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                if journal.exists():
                    identities = json.loads(journal.read_text()).get("processes", [])
                    if identities:
                        break
                time.sleep(0.01)
            self.assertTrue(identities, "fixture did not start execution")
            process.kill()
            process.wait(timeout=3)
            self.assertTrue(any(psutil.pid_exists(record["pid"]) for record in identities))
            with self.assertRaises(Blocked):
                with self.controller(worktree):
                    self.fail("related worktree bypassed unresolved old execution")
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=3)
            for record in identities:
                try:
                    child = psutil.Process(record["pid"])
                    if abs(child.create_time() - record["created"]) < 0.01:
                        child.kill()
                except psutil.NoSuchProcess:
                    pass

    def test_crash_recovery_preserves_attempt_and_consumed_budget(self):
        worktree = Path(self.tmp.name) / "second"
        git(self.root, "worktree", "add", "-b", "second", str(worktree))
        script = ("import sys; sys.path.insert(0,%r); from harness.runtime import Controller; "
                  "c=Controller(%r,'local','audit-run',%r); c.__enter__(); "
                  "c.execute([sys.executable,'-c','import time; time.sleep(30)'],%r,'crash',%r)") % (
                  str(ROOT / "skills/harness-init/assets/project"), str(self.root), LIMITS,
                  str(self.root), str(self.root / "crash.log"))
        process = subprocess.Popen([sys.executable, "-c", script], start_new_session=True)
        identities = []
        try:
            journal = self.root / ".git/harness.execution.json"
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                if journal.exists():
                    identities = json.loads(journal.read_text()).get("processes", [])
                    if identities:
                        break
                time.sleep(0.01)
            self.assertTrue(identities, "fixture did not start execution")
            process.kill()
            process.wait(timeout=3)
            self.assertTrue(any(psutil.pid_exists(record["pid"]) for record in identities))
            for record in identities:
                child = psutil.Process(record["pid"])
                if abs(child.create_time() - record["created"]) < 0.01:
                    child.kill()
            deadline = time.monotonic() + 2
            while any(owned(record) for record in identities) and time.monotonic() < deadline:
                time.sleep(0.01)
            Controller.reconcile_stopped(self.root, "local", "audit-run", dict(LIMITS))
            with self.controller() as recovered:
                state = recovered.state.read()
                self.assertGreater(state["spent_seconds"], 0, "crashed execution erased consumed time")
                self.assertGreaterEqual(len(state["attempts"]), 1, "crashed execution erased attempted work")
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=3)
            for record in identities:
                try:
                    child = psutil.Process(record["pid"])
                    if abs(child.create_time() - record["created"]) < 0.01:
                        child.kill()
                except psutil.NoSuchProcess:
                    pass

    def test_failed_command_preserves_exit_code(self):
        with self.controller() as controller:
            result = controller.execute([sys.executable, "-c", "raise SystemExit(7)"],
                                        self.root, "fail", self.root / "fail.log")
            self.assertEqual(result["exit_code"], 7)
            self.assertTrue(result["stopped"])

    def test_reused_pid_identity_is_not_owned(self):
        record = identity(psutil.Process(os.getpid()))
        record["created"] -= 60
        self.assertIsNone(owned(record))
        self.assertIsNotNone(owned(identity(psutil.Process(os.getpid()))))

    def test_mode_mismatch_and_corruption_preserve_checkpoint(self):
        with self.controller() as controller:
            original = controller.state.write(controller.state.read(), 0)
        with self.assertRaises(Blocked):
            with Controller(self.root, "github", "audit-run", dict(LIMITS)):
                pass
        checkpoint = self.root / ".loop-state.json"
        self.assertEqual(json.loads(checkpoint.read_text()), original)
        checkpoint.write_text('{"incomplete":')
        with self.assertRaises(Blocked):
            with self.controller():
                pass
        self.assertEqual(checkpoint.read_text(), '{"incomplete":')

    def test_budget_survives_new_controller(self):
        limits = dict(LIMITS, max_attempts=1)
        with Controller(self.root, "local", "audit-run", limits) as controller:
            controller.execute([sys.executable, "-c", "pass"], self.root,
                               "first", self.root / "first.log")
        with Controller(self.root, "local", "audit-run", limits) as controller:
            with self.assertRaises(Blocked):
                controller.execute([sys.executable, "-c", "pass"], self.root,
                                   "second", self.root / "second.log")
            self.assertEqual(len(controller.state.read()["attempts"]), 1)
        self.assertFalse((self.root / "second.log").exists())

    def test_timeout_preserves_failure_and_budget(self):
        with self.controller() as controller:
            result = controller.execute([sys.executable, "-c", "import time; time.sleep(30)"],
                                        self.root, "timeout", self.root / "timeout.log", timeout=0.1)
            self.assertEqual(result["reason"], "timeout")
            self.assertTrue(result["stopped"])
            self.assertNotEqual(result["exit_code"], 0)
            self.assertGreater(controller.state.read()["spent_seconds"], 0)

    def test_sigint_cancels_owned_execution_and_records_reason(self):
        script = ("import sys,json; sys.path.insert(0,%r); from harness.runtime import Controller; "
                  "c=Controller(%r,'local','audit-run',%r); c.__enter__(); "
                  "r=c.execute([sys.executable,'-c','import time; time.sleep(30)'],%r,'cancel',%r); "
                  "c.__exit__(None,None,None); print(json.dumps(r))") % (
                  str(ROOT / "skills/harness-init/assets/project"), str(self.root), LIMITS,
                  str(self.root), str(self.root / "cancel.log"))
        process = subprocess.Popen([sys.executable, "-c", script], start_new_session=True,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        identities = []
        try:
            journal = self.root / ".git/harness.execution.json"
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                if journal.exists():
                    identities = json.loads(journal.read_text()).get("processes", [])
                    if identities:
                        break
                time.sleep(0.01)
            self.assertTrue(identities)
            process.send_signal(signal.SIGINT)
            stdout, stderr = process.communicate(timeout=4)
            self.assertEqual(process.returncode, 0, stderr)
            record = json.loads(stdout)
            self.assertEqual(record["reason"], "cancelled")
            self.assertTrue(record["stopped"])
            self.assertFalse(any(owned(item) for item in identities))
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate(timeout=3)
            for item in identities:
                child = owned(item)
                if child:
                    child.kill()

    def test_short_parent_cannot_leave_unobserved_same_group_child(self):
        pidfile = self.root / "child.pid"
        marker = self.root / "child-lived"
        child_code = "import time,pathlib; time.sleep(0.7); pathlib.Path(%r).write_text('alive'); time.sleep(5)" % str(marker)
        parent_code = ("import subprocess,sys,pathlib; p=subprocess.Popen([sys.executable,'-c',%r]); "
                       "pathlib.Path(%r).write_text(str(p.pid))") % (child_code, str(pidfile))
        try:
            with self.controller() as controller:
                result = controller.execute([sys.executable, "-c", parent_code], self.root,
                                            "short-parent", self.root / "short-parent.log")
            time.sleep(0.8)
            self.assertFalse(marker.exists(), "child continued writing after stopped=true: %r" % result)
        finally:
            if pidfile.exists():
                try:
                    process = psutil.Process(int(pidfile.read_text()))
                    # This PID is created by the bounded fixture in the current test.
                    if process.is_running() and process.status() != psutil.STATUS_ZOMBIE:
                        process.terminate()
                        try:
                            process.wait(timeout=2)
                        except psutil.TimeoutExpired:
                            process.kill()
                except psutil.NoSuchProcess:
                    pass


if __name__ == "__main__":
    unittest.main(verbosity=2)
