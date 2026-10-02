"""Ordinary P0 scheduling tests: all native/host probes are mocked, no processes."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock
from contextlib import ExitStack
from harness import p0


class P0DispatchOrder(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.events = []
        self.state = {"active": None, "attempts": [], "spent_seconds": 0}
        self.project = Mock(root=self.root, common=self.root, entered=True)
        self.project.state.read.return_value = self.state
        self.project.limits = {"total_seconds": 100, "max_attempts": 100}
        self.project.execute.side_effect = self.write_probe
        self.config = {"repository_root": str(self.root), "mode": "local",
                       "limits": {"command_seconds": 10, "stop_grace_seconds": 1, "task_seconds": 100},
                       "host": {"commit_mode": "controller_commit"},
                       "knowledge": {"executable": "serena", "serena_home": str(self.root)},
                       "p0": {"run_host_drills": True, "max_commands": 100, "model": "fixture", "max_model_calls": 4}}
        self.commit_status = "verified"
        self.stop_ok = True
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        def fake_controller(root, *args):
            controller = Mock(root=Path(root), common=Path(root))
            controller.journal = Path(root) / "journal.json"
            controller.limits = {"total_seconds": 100, "max_attempts": 100}
            controller.state.read.return_value = {"attempts": [], "spent_seconds": 0}
            controller.__enter__ = Mock(return_value=controller)
            controller.__exit__ = Mock(return_value=False)
            return controller
        self.patch("harness.p0.Controller", side_effect=fake_controller)
        self.patch("harness.p0._entered_controller", return_value=True)
        self.patch("harness.p0._execution_stopped", side_effect=lambda c: self.stop_ok)
        self.patch("harness.p0.shutil.which", side_effect=lambda name: "/fixture/" + name)
        self.patch("harness.p0.platform.platform", return_value="mock-platform")
        self.patch("harness.p0.subprocess.run", return_value=Mock(returncode=0))
        self.patch("harness.p0._successful", side_effect=self.free_probe)
        self.patch("harness.p0._execute", side_effect=self.stop_probe)
        self.patch("harness.p0.owned", return_value=None)
        self.patch("harness.p0_controller_commit.probe_controller_commit", side_effect=self.commit_probe)
        adapter = self.patch("harness.knowledge.SerenaAdapter").return_value
        for method in ("probe_version", "read_core", "check_references"):
            getattr(adapter, method).side_effect = lambda m=method: self.events.append(m) or {}
        self.host = self.patch("harness.codex_probe.run_host_drills", side_effect=self.host_probe)
        self.patch("harness.github_probe.probe_github", side_effect=self.github_probe)

    def patch(self, *args, **kwargs):
        return self.stack.enter_context(patch(*args, **kwargs))

    def write_probe(self, *args, **kwargs):
        self.events.append("repository_write")
        return {"exit_code": 0, "reason": None, "stopped": True}

    def commit_probe(self, *args):
        self.events.append("controller_commit")
        return {"status": self.commit_status, "detail": "ordinary mocked prerequisite", "report_path": "fixture.json",
                "report_sha256": "fixture", "scope": "mock"}

    def free_probe(self, controller, argv, name, timeout):
        self.events.append(name)
        return {"status": "verified", "output": "fixture"}

    def stop_probe(self, controller, *args):
        self.events.append("local_process_group_stop")
        identities = [{"pid": 1}, {"pid": 2}]
        controller.journal.write_text(json.dumps({"stopped": True, "processes": identities}))
        return ({"reason": "timeout", "stopped": True}, {"output": '"child_pid": 2'})

    def github_probe(self, *args, **kwargs):
        self.events.append("github_basic")
        return {"status": "verified", "detail": "mock private basic PR support",
                "automatic_merge_rules": {"status": "blocked"}, "report_path": "fixture", "report_sha256": "fixture"}

    def host_probe(self, *args, **kwargs):
        self.events.append("host")
        return {"capabilities": {}, "host_native_stop": {"status": "verified"}, "calls_started": 4}

    def test_native_failure_skips_all_host_calls(self):
        self.commit_status = "blocked"
        result = p0.probe(self.config, self.project)
        self.host.assert_not_called()
        self.assertEqual("blocked", result["capabilities"]["controller_commit"]["status"])
        self.assertEqual(0, result["host_dispatch"]["calls_started"])
        self.assertEqual("skipped_due_to_prerequisite", result["host_dispatch"]["status"])
        self.assertIn("controller_commit", result["host_dispatch"]["blocked_by"])
        self.assertEqual(1, self.events.count("controller_commit"))

    def test_free_probes_precede_single_host_dispatch(self):
        result = p0.probe(self.config, self.project)
        self.assertEqual("host", self.events[-1])
        self.assertEqual(1, self.events.count("controller_commit"))
        self.host.assert_called_once()
        self.assertEqual(4, result["host_dispatch"]["calls_started"])
        self.assertEqual([], result["host_dispatch"]["blocked_by"])

    def test_private_optional_merge_rules_do_not_block_basic_host_drills(self):
        self.config["mode"] = "github"
        result = p0.probe(self.config, self.project)
        self.assertLess(self.events.index("github_basic"), self.events.index("host"))
        self.host.assert_called_once()
        self.assertEqual("blocked", result["capabilities"]["github_automatic_merge_rules"]["status"])

    def test_unknown_prior_stop_dispatches_nothing(self):
        self.stop_ok = False
        result = p0.probe(self.config, self.project)
        self.assertEqual([], self.events)
        self.host.assert_not_called()
        self.assertEqual(0, result["host_dispatch"]["calls_started"])

    def test_exhausted_project_budget_cannot_start_host_or_reset_budget(self):
        self.state["spent_seconds"] = 100
        result = p0.probe(self.config, self.project)
        self.host.assert_not_called()
        self.assertEqual(100, self.state["spent_seconds"])
        self.assertIn("project_budget_exhausted", result["host_dispatch"]["blocked_by"])

    def test_failed_prerequisite_also_skips_optional_smoke(self):
        self.config["p0"].pop("run_host_drills")
        self.config["p0"]["smoke_argv"] = ["not-executed"]
        self.commit_status = "blocked"
        result = p0.probe(self.config, self.project)
        self.assertNotIn("host-smoke", self.events)
        self.assertEqual(0, result["host_dispatch"]["calls_started"])

    def test_missing_native_knowledge_skips_host_without_semantic_override(self):
        self.config.pop("knowledge")
        result = p0.probe(self.config, self.project)
        self.host.assert_not_called()
        self.assertIn("serena_native_probe", result["host_dispatch"]["blocked_by"])
        self.assertEqual(0, result["host_dispatch"]["calls_started"])

    def test_failed_basic_github_access_skips_host(self):
        self.config["mode"] = "github"
        with patch("harness.github_probe.probe_github", return_value={
                "status": "blocked", "detail": "ordinary mocked unavailable repository", 
                "automatic_merge_rules": {"status": "blocked"}, "report_path": "fixture", "report_sha256": "fixture"}):
            result = p0.probe(self.config, self.project)
        self.host.assert_not_called()
        self.assertIn("github_authenticated_capabilities", result["host_dispatch"]["blocked_by"])

    def test_host_exception_does_not_fabricate_zero_calls(self):
        self.host.side_effect = ValueError("mock host report unavailable")
        result = p0.probe(self.config, self.project)
        self.host.assert_called_once()
        self.assertEqual("dispatched", result["host_dispatch"]["status"])
        self.assertIsNone(result["host_dispatch"]["calls_started"])

    def test_invalid_model_is_diagnosed_before_any_native_probe(self):
        self.config["p0"].pop("model")
        result = p0.probe(self.config, self.project)
        self.assertEqual([], self.events)
        self.host.assert_not_called()
        self.assertIn("explicit nonempty model", result["capabilities"]["host_command_smoke"]["detail"])
        self.assertEqual(0, result["host_dispatch"]["calls_started"])

    def test_invalid_call_limit_is_diagnosed_before_any_native_probe(self):
        self.config["p0"]["max_model_calls"] = 0
        result = p0.probe(self.config, self.project)
        self.assertEqual([], self.events)
        self.host.assert_not_called()
        self.assertIn("explicit max_model_calls", result["capabilities"]["host_command_smoke"]["detail"])
        self.assertEqual(["host_model_configuration"], result["host_dispatch"]["blocked_by"])
