"""Native isolated Git/CAS + contract/receipt tests; no models or network.

Receipt gate tests explicitly mock host observations. These tests do not prove
an actual Codex/controller implementation task or model-side Git permissions.
"""
import copy
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_contracts as contracts
import test_capabilities_audit as receipts
from harness.capabilities import record_capabilities, require_capabilities, REQUIRED_LIVE
from harness.harness_check import Validator
from harness.p0 import probe
from harness.p0_controller_commit import probe_controller_commit
from harness.runtime import Controller
from harness.state import Blocked, atomic_json


class CommitModeContracts(unittest.TestCase):
    setUp = contracts.HarnessCheckTests.setUp
    fixture = contracts.HarnessCheckTests.fixture
    report = contracts.HarnessCheckTests.report

    def valid(self, mode=None, paths=None):
        bundle = copy.deepcopy(self.bundle)
        if mode is not None:
            bundle["config"]["host"] = {"commit_mode": mode}
        if paths is not None:
            bundle["tasks"][0]["allowed_paths"] = paths
        checker = Validator(bundle)
        return checker.preflight(), checker.errors

    def test_absent_mode_and_explicit_model_mode_preserve_legacy_tasks(self):
        self.assertTrue(self.valid()[0])
        self.assertTrue(self.valid("model_commit")[0])

    def test_invalid_mode_and_controller_missing_paths_fail_closed(self):
        for mode in ("auto", "", False, [], "controller-commit"):
            okay, errors = self.valid(mode)
            self.assertFalse(okay)
            self.assertTrue(any(error["path"] == "config.host.commit_mode" for error in errors))
        self.assertFalse(self.valid("controller_commit")[0])
        self.bundle["config"]["host"] = {"commit_mode": None}
        self.assertFalse(Validator(self.bundle).preflight())

    def test_controller_allows_only_explicit_normalized_file_paths(self):
        self.assertTrue(self.valid("controller_commit", ["src/new.py", "tests/test_new.py"])[0])
        for paths in ([], ["src/"], ["src/*"], ["src/?.py"], ["src/[ab].py"], ["!src/a.py"],
                      [":(literal)src/a.py"], ["../a.py"], ["/tmp/a"], [".git/config"],
                      ["src/.GIT/config"], [".loop-state.json"], ["-option"], ["a.py", "A.py"], ["a.py", "a.py"], [False],
                      ["a/./b"], ["a\\b"], ["a", "a/b"], ["a/é.py", "a/é.py"], ["a"] * 501):
            with self.subTest(paths=paths):
                self.assertFalse(self.valid("controller_commit", paths)[0])

    def test_directory_and_symlink_allowed_paths_are_refused(self):
        (self.root / "source").mkdir()
        (self.root / "linked").symlink_to(self.root / "source", target_is_directory=True)
        self.assertFalse(self.valid("controller_commit", ["source"])[0])
        self.assertFalse(self.valid("controller_commit", ["linked/new.py"])[0])


class NativeCommitProbe(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        subprocess.run(["git", "init", "--template=", str(self.root)], check=True, capture_output=True)
        # The actual repository needs its own valid identity; command-scoped
        # identity on the baseline commit cannot authorize later Controller writes.
        subprocess.run(["git", "-C", str(self.root), "config", "user.name", "Fixture"], check=True)
        subprocess.run(["git", "-C", str(self.root), "config", "user.email", "f@example.invalid"], check=True)
        subprocess.run(["git", "-C", str(self.root), "-c", "user.name=Fixture", "-c", "user.email=f@example.invalid",
                        "commit", "--allow-empty", "-m", "base"], check=True, capture_output=True)
        self.limits = {"command_seconds": 5, "stop_grace_seconds": .2, "total_seconds": 60, "max_attempts": 100}
        self.config = {"mode": "local", "repository_root": str(self.root), "environment": {},
                       "host": {"commit_mode": "controller_commit"},
                       "limits": {"command_seconds": 5, "stop_grace_seconds": .2, "task_seconds": 60},
                       "p0": {"executables": {"codex": "/missing/codex"}}}

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.root), *args], text=True).strip()

    def test_actual_native_object_and_both_cas_outcomes_with_cleanup(self):
        before = self.git("show-ref")
        with Controller(self.root, "local", "commit-probe", self.limits) as controller:
            report = probe_controller_commit(controller, 5)
            self.assertEqual(report["status"], "verified", report)
            self.assertEqual(report["model_calls"], 0)
            self.assertFalse(report["proves_model_controller_split"])
            self.assertEqual(report["host_boundary"]["status"], "not_observed")
            self.assertFalse(Path(report["probe_directory"]).exists())
            proof = report["observation"]
            self.assertTrue(proof["cas_rejection_observed"])
            self.assertTrue(proof["cas_update_observed"])
            self.assertTrue(proof["ref_cleanup_observed"])
            self.assertNotEqual(proof["initial_commit"], proof["commit"])
            self.assertTrue(any(row["argv"][0] == "update-ref" and row["exit_code"] != 0 for row in proof["commands"]))
            self.assertGreaterEqual(len(controller.state.read()["attempts"]), 2)
            self.assertEqual(self.git("show-ref"), before)
            for descriptor in report["logs"].values():
                self.assertEqual(hashlib.sha256(Path(descriptor["path"]).read_bytes()).hexdigest(), descriptor["sha256"])
            self.assertEqual(hashlib.sha256(Path(report["report_path"]).read_bytes()).hexdigest(), report["report_sha256"])

    def test_hook_policy_rejected_without_executing_hook_or_probe(self):
        marker = self.root / "hook-executed"
        hook = self.root / ".git/hooks/reference-transaction"
        hook.parent.mkdir(exist_ok=True)
        hook.write_text("#!/bin/sh\ntouch " + str(marker) + "\n")
        hook.chmod(0o700)
        with Controller(self.root, "local", "commit-hook", self.limits) as controller:
            report = probe_controller_commit(controller, 5)
        self.assertEqual(report["status"], "blocked", report)
        self.assertNotIn("probe_directory", report)
        self.assertFalse(marker.exists())
        self.assertTrue(Path(report["report_path"]).is_file())
        self.assertTrue(any(name.startswith("policy-") for name in report["logs"]))

    def test_custom_filters_signing_and_hooks_path_block_before_native_probe(self):
        for key, value in (("filter.probe.clean", "false"), ("commit.gpgsign", "true"),
                           ("core.hooksPath", "/missing/custom-hooks")):
            with self.subTest(key=key):
                self.git("config", key, value)
                with Controller(self.root, "local", "commit-policy", self.limits) as controller:
                    report = probe_controller_commit(controller, 5)
                self.assertEqual(report["status"], "blocked", report)
                self.assertNotIn("probe_directory", report)
                self.git("config", "--unset", key)

    def test_direct_probe_requires_held_lock_and_rejects_evidence_symlink(self):
        controller = Controller(self.root, "local", "commit-lock", self.limits)
        with self.assertRaisesRegex(Blocked, "entered locked"):
            probe_controller_commit(controller, 5)
        target = self.root / "not-an-evidence-archive"
        target.mkdir()
        (controller.common / "harness-p0-controller-commit").symlink_to(target, target_is_directory=True)
        with controller, self.assertRaisesRegex(Blocked, "symlink"):
            probe_controller_commit(controller, 5)
        self.assertEqual(list(target.iterdir()), [])

    def test_failure_evidence_and_temp_repo_are_preserved(self):
        with Controller(self.root, "local", "commit-failure", self.limits) as controller:
            with patch("harness.p0_controller_commit._PROGRAM", "import sys; print('{\"ok\": false}'); sys.exit(1)"):
                report = probe_controller_commit(controller, 5)
        self.assertEqual(report["status"], "blocked")
        preserved = Path(report["preserved_probe_directory"])
        self.addCleanup(shutil.rmtree, preserved)
        self.assertTrue(preserved.is_dir())
        self.assertTrue(Path(report["logs"]["stdout"]["path"]).is_file())

    def test_probe_consumes_the_existing_controller_budget(self):
        limits = dict(self.limits, max_attempts=1)
        with Controller(self.root, "local", "commit-budget", limits) as controller:
            controller.execute([sys.executable, "-c", "print('spent')"], self.root,
                               "spent-budget", self.root / ".git/spent.log")
            report = probe_controller_commit(controller, 5)
            self.assertEqual(report["status"], "blocked")
            self.assertIn("budget_exhausted", report["detail"])
            self.assertEqual(controller.state.read()["commands_started"], 1)

    def test_p0_requires_actual_entered_controller_and_keeps_host_gaps(self):
        report = probe(self.config)
        self.assertEqual(report["capabilities"]["controller_commit"]["status"], "blocked")
        with Controller(self.root, "local", "p0-controller-commit", self.limits) as controller:
            report = probe(self.config, controller)
        self.assertEqual(report["capabilities"]["controller_commit"]["status"], "verified", report)
        self.assertEqual(report["capabilities"]["host_session_start"]["status"], "blocked")
        self.assertEqual(report["capabilities"]["model_git_commit"]["status"], "not_applicable")
        self.assertFalse(report["capabilities"]["controller_commit"]["proves_model_controller_split"])

    def test_default_model_commit_has_no_model_git_permission_proof(self):
        del self.config["host"]["commit_mode"]
        self.config["p0"]["model_git_commit"] = {"status": "verified", "caller_claim": True}
        with Controller(self.root, "local", "p0-model-commit", self.limits) as controller:
            report = probe(self.config, controller)
        self.assertEqual(report["capabilities"]["repository_write"]["status"], "verified")
        self.assertEqual(report["capabilities"]["model_git_commit"]["status"], "blocked")
        self.assertEqual(report["capabilities"]["controller_commit"]["status"], "not_applicable")

    def test_unknown_project_probe_stop_prevents_further_dispatch(self):
        def unknown(controller, timeout):
            atomic_json(controller.journal, {"stopped": False, "processes": []})
            return {"status": "blocked", "detail": "fixture unknown stop", "scope": "fixture",
                    "report_path": str(controller.journal), "report_sha256": "fixture"}
        with Controller(self.root, "local", "unknown-stop", self.limits) as controller:
            with patch("harness.p0_controller_commit.probe_controller_commit", side_effect=unknown):
                result = probe(self.config, controller)
            self.assertEqual(controller.state.read()["commands_started"], 0)
        self.assertEqual(result["capabilities"]["project_execution_stop"]["status"], "blocked")
        self.assertEqual(result["capabilities"]["repository_write"]["status"], "blocked")


class CommitReceiptBinding(unittest.TestCase):
    setUp = receipts.CapabilitiesAudit.setUp
    tearDown = receipts.CapabilitiesAudit.tearDown
    commit = receipts.CapabilitiesAudit.commit
    controller = receipts.CapabilitiesAudit.controller

    def test_live_receipt_requires_mode_specific_proof(self):
        (self.root / "semantic-review.md").write_text("# Operator fixture review\nSources reviewed for gate-only test.\n")
        self.commit("semantic fixture")
        observed = {"capabilities": {name: {"status": "verified", "fixture": "mocked"} for name in REQUIRED_LIVE}}
        with self.controller() as controller, patch("harness.p0.probe", return_value=observed):
            result = record_capabilities(controller, self.config, "live", "semantic-review.md", True)
            self.assertIn("model_git_commit", result["unverified"])
            with self.assertRaisesRegex(Blocked, "model_git_commit"):
                require_capabilities(controller, self.config)
            self.config["host"]["commit_mode"] = "controller_commit"
            result = record_capabilities(controller, self.config, "live", "semantic-review.md", True)
            self.assertIn("controller_commit", result["unverified"])
            observed["capabilities"]["controller_commit"] = {"status": "verified", "fixture": "mocked"}
            result = record_capabilities(controller, self.config, "live", "semantic-review.md", True)
            self.assertEqual(result["status"], "ready")
            self.assertEqual(require_capabilities(controller, self.config)["status"], "ready")

    def test_controller_probe_logs_and_report_are_bound_and_mode_drift_expires(self):
        self.config["host"]["commit_mode"] = "controller_commit"
        with self.controller() as controller:
            native = controller.common / "native-commit.stdout"
            report = controller.common / "native-commit-report.json"
            native.write_text("isolated mocked native output\n")
            report.write_text('{"fixture": "mocked native report"}\n')
            observed = {"capabilities": {"controller_commit": {"status": "verified", "fixture": "mocked"}},
                        "controller_commit_probe": {"logs": {"stdout": {"path": str(native)}}, "report_path": str(report)}}
            with patch("harness.p0.probe", return_value=observed):
                receipt = record_capabilities(controller, self.config, "simulation")
            self.assertIn(str(native), receipt["raw_logs"])
            self.assertIn(str(report), receipt["raw_logs"])
            require_capabilities(controller, self.config)
            changed = copy.deepcopy(self.config)
            changed["host"]["commit_mode"] = "model_commit"
            with self.assertRaisesRegex(Blocked, "stale"):
                require_capabilities(controller, changed)
            report.write_text("changed probe evidence")
            with self.assertRaisesRegex(Blocked, "raw capability evidence"):
                require_capabilities(controller, self.config)

    def test_simulation_controller_mode_cannot_skip_native_commit_capability(self):
        self.config["host"]["commit_mode"] = "controller_commit"
        with self.controller() as controller, patch("harness.p0.probe", return_value={"capabilities": {}}):
            record_capabilities(controller, self.config, "simulation")
            with self.assertRaisesRegex(Blocked, "controller_commit capability"):
                require_capabilities(controller, self.config)


if __name__ == "__main__":
    unittest.main(verbosity=2)
