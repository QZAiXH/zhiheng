"""P0 tests use temporary repositories; no live host session or Serena service."""
import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[2] / "skills/harness-init/assets/project"
sys.path.insert(0, str(PROJECT))
from harness.harness_check import fingerprint
from harness.p0 import HOST_GAPS, probe
from harness.runtime import Controller


class P0ProbeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.config = {"mode": "local", "repository_root": str(self.root),
                       "environment": {"host": "Codex CLI not yet observed"}, "ready": False,
                       "limits": {"command_seconds": 1, "stop_grace_seconds": 0.1, "task_seconds": 10},
                       "p0": {"executables": {"codex": "/not-installed/codex"}, "max_commands": 8}}

    def test_actual_temp_git_filesystem_parent_child_stop_probe(self):
        result = probe(self.config)
        caps = result["capabilities"]
        self.assertEqual(caps["git_version"]["status"], "verified", caps)
        self.assertEqual(caps["temporary_filesystem_io"]["status"], "verified", caps)
        self.assertEqual(caps["local_process_group_stop"]["status"], "verified", caps)
        self.assertTrue(caps["local_process_group_stop"]["actual_stop_confirmed"])
        self.assertGreaterEqual(len(caps["local_process_group_stop"]["observed_processes"]), 2)
        self.assertNotIn("preserved_probe_directory", result)

    def test_default_does_not_mutate_target_or_enable_ready(self):
        file = self.root / "user.txt"
        file.write_text("keep user data")
        before = copy.deepcopy(self.config)
        result = probe(self.config)
        self.assertEqual(self.config, before)
        self.assertEqual(list(self.root.iterdir()), [file])
        self.assertEqual(file.read_text(), "keep user data")
        self.assertFalse(result["changes_ready"])
        self.assertEqual(result["automation_readiness"]["status"], "blocked")
        self.assertEqual(result["capabilities"]["repository_write"]["status"], "blocked")

    def test_hashes_bind_config_declared_and_observed_environment(self):
        result = probe(self.config)
        self.assertEqual(result["config_sha256"], fingerprint(self.config))
        self.assertEqual(result["declared_environment_sha256"], fingerprint(self.config["environment"]))
        self.assertEqual(result["observed_environment_sha256"], fingerprint(result["observed_environment"]))

    def test_ready_or_capability_claims_cannot_fill_host_gaps(self):
        self.config["ready"] = True
        self.config["p0"].update({name: {"status": "verified"} for name in HOST_GAPS})
        result = probe(self.config)
        self.assertEqual(result["automation_readiness"]["status"], "blocked")
        for name in HOST_GAPS:
            self.assertEqual(result["capabilities"][name]["status"], "blocked")

    def test_missing_git_fails_without_mutating_repo(self):
        self.config["p0"]["executables"]["git"] = "/not-installed/git"
        result = probe(self.config)
        self.assertEqual(result["capabilities"]["git_executable"]["status"], "blocked")
        self.assertEqual(list(self.root.iterdir()), [])

    def test_invalid_limits_fail_before_any_execution(self):
        for bad in (None, 0, -1, True, float("inf")):
            config = copy.deepcopy(self.config)
            config["limits"]["command_seconds"] = bad
            with patch("harness.p0.subprocess.run") as run:
                result = probe(config)
                run.assert_not_called()
            self.assertEqual(result["capabilities"]["configuration"]["status"], "blocked")

    def test_mode_and_host_structure_fail_closed(self):
        for update in ({"mode": None}, {"host": []}, {"repository_root": "relative"}):
            config = copy.deepcopy(self.config)
            config.update(update)
            self.assertEqual(probe(config)["capabilities"]["configuration"]["status"], "blocked")

    def test_local_mode_never_queries_gh(self):
        real_which = shutil.which
        calls = []
        def which(name):
            calls.append(name)
            return real_which(name)
        with patch("harness.p0.shutil.which", side_effect=which):
            result = probe(self.config)
        self.assertNotIn("gh", calls)
        self.assertEqual(result["capabilities"]["github_authenticated_capabilities"]["status"], "not_applicable")

    def test_arbitrary_smoke_command_is_refused(self):
        self.config["p0"]["smoke_argv"] = [sys.executable, "-c", "raise RuntimeError('must not run')"]
        result = probe(self.config)
        self.assertEqual(result["capabilities"]["host_command_smoke"]["status"], "blocked")
        self.assertIn("Only exact Codex read-only", result["capabilities"]["host_command_smoke"]["detail"])

    def test_insufficient_probe_budget_blocks_instead_of_resetting(self):
        self.config["p0"]["max_commands"] = 1
        result = probe(self.config)
        self.assertEqual(result["capabilities"]["temporary_filesystem_io"]["status"], "blocked")
        self.assertEqual(result["capabilities"]["local_process_group_stop"]["status"], "blocked")
        self.assertIn("budget_exhausted", result["capabilities"]["local_process_group_stop"]["detail"])

    def test_target_write_only_under_real_matching_controller(self):
        subprocess.run(["git", "init", "--template=", str(self.root)], check=True, capture_output=True)
        limits = {"command_seconds": 1, "stop_grace_seconds": 0.1, "total_seconds": 10, "max_attempts": 8}
        with Controller(self.root, "local", "test-p0", limits) as controller:
            result = probe(self.config, controller=controller)
            self.assertEqual(result["capabilities"]["repository_write"]["status"], "verified", result)
            self.assertTrue(controller.state.read()["attempts"])
        self.assertFalse(list((self.root / ".git").glob("harness-p0-write-*")))

    def test_serena_not_called_without_matching_controller(self):
        self.config["knowledge"] = {"executable": "/not-installed/serena", "serena_home": str(self.root / "serena-home")}
        self.config["p0"]["register_existing"] = True
        with patch("harness.knowledge.SerenaAdapter") as adapter:
            result = probe(self.config)
            adapter.assert_not_called()
        self.assertEqual(result["capabilities"]["serena_native_probe"]["status"], "blocked")
        self.assertFalse((self.root / "serena-home").exists())


if __name__ == "__main__":
    unittest.main()
