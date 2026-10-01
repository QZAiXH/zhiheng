"""Independent local Git and evidence tests, with no remotes or GitHub calls."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import shutil
import os

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "skills/harness-init/assets/project"))
from harness.runtime import Controller
from harness.local import prepare_candidate, run_checks, check_fresh, deliver, reconcile_delivery, push_delivery
from harness.state import Blocked

LIMITS = {"command_seconds": 2.0, "total_seconds": 20.0,
          "max_attempts": 20, "stop_grace_seconds": 0.3}


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True,
                                   stderr=subprocess.DEVNULL).strip()


class LocalAudit(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="harness-local-audit-")
        self.root = Path(self.tmp.name) / "repo"
        self.root.mkdir()
        git(self.root, "init", "-b", "main")
        git(self.root, "config", "user.name", "Fixture")
        git(self.root, "config", "user.email", "fixture@example.invalid")
        (self.root / "base.txt").write_text("base\n")
        (self.root / ".gitignore").write_text(".loop-state.json\n")
        self.commit("base")
        git(self.root, "checkout", "-b", "feature")
        (self.root / "feature.txt").write_text("feature\n")
        self.commit("feature")
        git(self.root, "checkout", "main")
        self.spec = Path(self.tmp.name) / "spec.md"
        self.spec.write_text("AC-1: feature works\n")
        self.checks = [{"id": "unit", "argv": [sys.executable, "-c", "pass"], "required": True}]
        self.environment = {"host": "test", "lock_hash": "original"}

    def commit(self, message):
        git(self.root, "add", ".")
        git(self.root, "commit", "-m", message)

    def tearDown(self):
        self.tmp.cleanup()

    def controller(self):
        return Controller(self.root, "local", "local-audit", dict(LIMITS))

    def candidate(self, controller):
        return prepare_candidate(controller, "feature", "main", "TASK-alpha", "attempt-A",
                                 self.spec, self.checks, self.environment)

    def test_nonnumeric_id_candidate_and_authorized_ff_delivery(self):
        with self.controller() as controller:
            candidate = self.candidate(controller)
            self.assertEqual(git(self.root, "rev-parse", "main"), candidate["T"])
            check_fresh(self.root, candidate, self.spec, self.checks, self.environment)
            candidate["status"] = "verified"
            delivered = deliver(controller, candidate, self.root, self.spec,
                                self.checks, self.environment, authorized=True)
            self.assertEqual(delivered["D"], candidate["C"])
            self.assertEqual(reconcile_delivery(self.root, candidate, "main")["status"], "delivered")

    def test_local_github_remote_does_not_require_gh_or_push(self):
        git(self.root, "remote", "add", "origin", "https://github.com/fixture/no-network.git")
        isolated_bin = Path(self.tmp.name) / "bin"
        isolated_bin.mkdir()
        (isolated_bin / "git").symlink_to(shutil.which("git"))
        with patch.dict(os.environ, {"PATH": str(isolated_bin)}):
            self.assertIsNone(shutil.which("gh"))
            with self.controller() as controller:
                candidate = self.candidate(controller)
                results = run_checks(controller, candidate, self.checks, "no-gh",
                                     Path(self.tmp.name) / "logs")
                self.assertTrue(all(row["status"] == "passed" for row in results))
                candidate["status"] = "verified"
                result = deliver(controller, candidate, self.root, self.spec,
                                 self.checks, self.environment, authorized=True)
                self.assertEqual(result["status"], "delivered")
                self.assertEqual(git(self.root, "for-each-ref", "refs/remotes"), "")

    def test_stale_spec_checks_and_environment_fail(self):
        with self.controller() as controller:
            candidate = self.candidate(controller)
            changed = copy.deepcopy(self.checks)
            changed[0]["argv"] = ["false"]
            with self.assertRaises(Blocked):
                check_fresh(self.root, candidate, self.spec, changed, self.environment)
            with self.assertRaises(Blocked):
                check_fresh(self.root, candidate, self.spec, self.checks, {"host": "changed"})
            self.spec.write_text("AC-1: materially different\n")
            with self.assertRaises(Blocked):
                check_fresh(self.root, candidate, self.spec, self.checks, self.environment)

    def test_target_moves_and_old_evidence_is_rejected(self):
        with self.controller() as controller:
            candidate = self.candidate(controller)
            (self.root / "new-target.txt").write_text("new target")
            self.commit("move target")
            candidate["status"] = "verified"
            before = git(self.root, "rev-parse", "main")
            with self.assertRaises(Blocked):
                deliver(controller, candidate, self.root, self.spec, self.checks,
                        self.environment, authorized=True)
            self.assertEqual(git(self.root, "rev-parse", "main"), before)

    def test_dirty_target_is_preserved(self):
        with self.controller() as controller:
            candidate = self.candidate(controller)
            candidate["status"] = "verified"
            (self.root / "base.txt").write_text("user unsaved change")
            with self.assertRaises(Blocked):
                deliver(controller, candidate, self.root, self.spec, self.checks,
                        self.environment, authorized=True)
            self.assertEqual((self.root / "base.txt").read_text(), "user unsaved change")
            self.assertEqual(git(self.root, "rev-parse", "main"), candidate["T"])

    def test_modified_candidate_is_rejected(self):
        with self.controller() as controller:
            candidate = self.candidate(controller)
            (Path(candidate["candidate_path"]) / "feature.txt").write_text("post-validation change")
            with self.assertRaises(Blocked):
                check_fresh(self.root, candidate, self.spec, self.checks, self.environment)

    def test_failed_combination_check_does_not_move_target(self):
        (self.root / "target-only.txt").write_text("incompatible target feature")
        self.commit("target feature")
        feature_only = Path(self.tmp.name) / "feature-only"
        git(self.root, "worktree", "add", "--detach", str(feature_only), "feature")
        code = "from pathlib import Path; raise SystemExit(4 if Path('feature.txt').exists() and Path('target-only.txt').exists() else 0)"
        argv = [sys.executable, "-c", code]
        self.assertEqual(subprocess.run(argv, cwd=self.root).returncode, 0)
        self.assertEqual(subprocess.run(argv, cwd=feature_only).returncode, 0)
        with self.controller() as controller:
            candidate = self.candidate(controller)
            results = run_checks(controller, candidate,
                                 [{"id": "combination", "argv": argv}],
                                 "combination", Path(self.tmp.name) / "logs")
            self.assertEqual(results[0]["status"], "failed")
            self.assertEqual(results[0]["exit_code"], 4)
            self.assertEqual(git(self.root, "rev-parse", "main"), candidate["T"])

    def test_stale_successful_junit_cannot_certify_new_command(self):
        with self.controller() as controller:
            candidate = self.candidate(controller)
            report = Path(candidate["candidate_path"]) / "old.xml"
            report.write_text('<testsuite><testcase name="old"/></testsuite>')
            try:
                results = run_checks(controller, candidate,
                                     [{"id": "stale", "kind": "tests", "junit": "old.xml",
                                       "argv": [sys.executable, "-c", "pass"]}],
                                     "stale", Path(self.tmp.name) / "logs")
            except Blocked:
                return
            self.assertNotEqual(results[0]["status"], "passed",
                                "a preexisting report certified a command that ran zero tests")

    def test_zero_skipped_and_missing_reports_fail(self):
        with self.controller() as controller:
            candidate = self.candidate(controller)
            for index, contents in enumerate(['<testsuite/>', '<testsuite><testcase><skipped/></testcase></testsuite>', None]):
                filename = "report-%s.xml" % index
                program = ("from pathlib import Path; Path(%r).write_text(%r)" % (filename, contents)) if contents else "pass"
                results = run_checks(controller, candidate,
                                     [{"id": "case-%s" % index, "kind": "tests", "junit": filename,
                                       "argv": [sys.executable, "-c", program]}],
                                     "negative-%s" % index, Path(self.tmp.name) / ("logs-%s" % index))
                self.assertEqual(results[0]["status"], "failed")

    def test_explicit_local_push_uses_actual_bare_remote_and_reuses_commit(self):
        remote = Path(self.tmp.name) / "remote.git"
        subprocess.run(["git", "init", "--bare", "--quiet", str(remote)], check=True)
        git(self.root, "remote", "add", "sandbox", str(remote))
        with self.controller() as controller:
            candidate = self.candidate(controller)
            candidate["status"] = "verified"
            actual = deliver(controller, candidate, self.root, self.spec,
                             self.checks, self.environment, authorized=True)
            state = controller.state.read()
            state["tasks"]["TASK-alpha"] = actual
            controller.state.write(state, state["revision"])
            with self.assertRaises(Blocked):
                push_delivery(controller, "TASK-alpha", "sandbox", "refs/heads/acceptance")
            first = push_delivery(controller, "TASK-alpha", "sandbox", "refs/heads/acceptance", authorized=True)
            self.assertTrue(first["pushed"])
            self.assertEqual(git(self.root, "ls-remote", "sandbox", "refs/heads/acceptance").split()[0], candidate["C"])
            operations = len(controller.state.read()["remote_operations"])
            second = push_delivery(controller, "TASK-alpha", "sandbox", "refs/heads/acceptance", authorized=True)
            self.assertTrue(second["reused"])
            self.assertEqual(len(controller.state.read()["remote_operations"]), operations)

    def test_successful_remote_push_with_old_intent_is_reconciled(self):
        remote = Path(self.tmp.name) / "remote.git"
        subprocess.run(["git", "init", "--bare", "--quiet", str(remote)], check=True)
        git(self.root, "remote", "add", "sandbox", str(remote))
        with self.controller() as controller:
            candidate = self.candidate(controller)
            candidate["status"] = "verified"
            actual = deliver(controller, candidate, self.root, self.spec,
                             self.checks, self.environment, authorized=True)
            state = controller.state.read()
            state["tasks"]["TASK-alpha"] = actual
            state["remote_operations"].append({"action": "git-push", "remote": "sandbox",
                "ref": "refs/heads/acceptance", "D": actual["D"], "status": "intent"})
            controller.state.write(state, state["revision"])
            # Actual remote update, deliberately omit its completion checkpoint.
            git(self.root, "push", "sandbox", actual["D"] + ":refs/heads/acceptance")
            result = push_delivery(controller, "TASK-alpha", "sandbox", "refs/heads/acceptance", authorized=True)
            self.assertTrue(result["reused"])
            self.assertEqual(controller.state.read()["remote_operations"][0]["status"], "observed")


if __name__ == "__main__":
    unittest.main(verbosity=2)
