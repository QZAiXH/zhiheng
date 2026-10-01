"""Workflow-control tests with SIMULATED reviewer and native readiness.

Real subprocesses and Git fixtures exercise control flow. The reviewer copies a
fixture response. Native readiness alone is mocked; missing/not-ready production
gates have separate negative tests. These do not establish Codex/Serena integration.
"""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import contextlib
import io

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_local_audit as local_fixtures
LIMITS = local_fixtures.LIMITS
from harness.workflow import validate_task, verified_evidence, approve_contract
from harness.state import Blocked
from harness import cli
from harness.runtime import git
from harness.runtime import Controller


class WorkflowAudit(unittest.TestCase):
    commit = local_fixtures.LocalAudit.commit
    controller = local_fixtures.LocalAudit.controller
    tearDown = local_fixtures.LocalAudit.tearDown

    def setUp(self):
        local_fixtures.LocalAudit.setUp(self)
        self.spec = self.root / "spec.md"
        self.spec.write_text("AC-1: fixture feature is present\n")
        self.commit("acceptance")
        self.payload = Path(self.tmp.name) / "simulated-review.json"
        self.answer = {"findings": [], "acceptance": [{"id": "AC-1", "status": "passed",
                       "evidence": "SIMULATED fixture assertion; not a real model review"}]}
        self.payload.write_text(json.dumps(self.answer))
        self.config = {"ready": True, "mode": "local", "repository_id": "local:fixture", "checks": self.checks,
                       "environment": self.environment,
                       "knowledge": {"executable": str(Path(self.tmp.name) / "simulated-serena"),
                                     "serena_home": str(Path(self.tmp.name) / "simulated-serena-home")},
                       "limits": dict(LIMITS, review_seconds=2, task_attempts=2, repair_attempts=2),
                       "host": {"review_argv": [sys.executable, "-c",
                            "import shutil,sys;shutil.copyfile(sys.argv[1],sys.argv[2])",
                            str(self.payload), "{output}"]}}
        self.task = {"id": "TASK-alpha", "source": "feature", "target": "main",
                     "spec": "spec.md", "acceptance_ids": ["AC-1"], "dependencies": []}
        self.readiness_patch = patch("harness.workflow.SerenaAdapter.readiness",
                                     return_value={"structural_ready": True,
                                                   "core": "SIMULATED native-readiness fixture"})
        self.readiness_mock = self.readiness_patch.start()
        self.addCleanup(self.readiness_patch.stop)
        self.registration_patch = patch("harness.workflow.SerenaAdapter.register_existing",
                                        return_value={"registered": True, "host_activated": False,
                                                      "fixture": "SIMULATED native registration"})
        self.registration_patch.start()
        self.addCleanup(self.registration_patch.stop)
        self.capabilities_patch = patch("harness.workflow.require_capabilities",
                                        return_value={"tier": "simulation", "fixture": "P0 gate mocked for isolated workflow tests"})
        self.capabilities_patch.start()
        self.addCleanup(self.capabilities_patch.stop)
        # The fixture's test author explicitly approves the original baseline;
        # no production path automatically approves a modified contract.
        with self.controller() as controller:
            approve_contract(controller, self.config, self.task, authorized=True)

    def test_weakening_checks_after_approval_blocks_before_execution(self):
        self.config["checks"][0].update(kind="tests", min_executed=0)
        with self.controller() as controller:
            with self.assertRaisesRegex(Blocked, "reviewed baseline"):
                validate_task(controller, self.config, self.task, "weakened-A")
            self.assertEqual(controller.state.read()["attempts"], [])

    def test_github_local_checks_alone_never_mark_generic_verified(self):
        # Fresh isolated mode, not a production mode switch or fallback.
        (self.root / ".loop-state.json").unlink()
        self.config["mode"] = "github"
        self.config["github"] = {"repository": "fixture/repo", "baseline_policy": "strict",
                                 "required_checks": ["remote-required"]}
        with Controller(self.root, "github", "github-local-only", dict(LIMITS)) as controller:
            approve_contract(controller, self.config, self.task, authorized=True)
            try:
                result = validate_task(controller, self.config, self.task, "local-only-A")
            except Blocked:
                result = {}
            self.assertNotEqual(result.get("status"), "verified",
                                "GitHub candidate has no current remote CI proof")
            self.assertNotEqual(controller.state.read()["tasks"].get(self.task["id"], {}).get("status"), "verified")

    def test_missing_native_knowledge_config_refuses_without_mock(self):
        self.readiness_patch.stop()
        self.registration_patch.stop()
        del self.config["knowledge"]
        with self.controller() as controller:
            approve_contract(controller, self.config, self.task, authorized=True)
            with self.assertRaisesRegex(Blocked, "Serena"):
                validate_task(controller, self.config, self.task, "missing-serena-A")
            self.assertEqual(controller.state.read()["attempts"], [])

    def test_native_not_ready_cannot_reach_checks_or_review(self):
        self.readiness_mock.return_value = {"structural_ready": False}
        with self.controller() as controller:
            with self.assertRaisesRegex(Blocked, "knowledge readiness"):
                validate_task(controller, self.config, self.task, "not-ready-A")
            self.assertEqual(controller.state.read()["attempts"], [])

    def test_simulated_review_allows_verified_but_not_delivery(self):
        with self.controller() as controller:
            result = validate_task(controller, self.config, self.task, "validate-A")
            self.assertEqual(result["status"], "verified")
            self.assertNotIn("D", result)
            self.assertEqual(verified_evidence(controller, self.task)["C"], result["C"])

    def test_blocking_review_never_verifies(self):
        self.answer["findings"] = [{"severity": "Blocking", "summary": "fixture defect",
            "location": "feature.txt:1", "evidence": "SIMULATED blocking review"}]
        self.payload.write_text(json.dumps(self.answer))
        with self.controller() as controller:
            with self.assertRaises(Blocked):
                validate_task(controller, self.config, self.task, "blocking-A")
            self.assertEqual(controller.state.read()["tasks"][self.task["id"]]["status"], "blocked")

    def test_missing_acceptance_review_never_verifies(self):
        self.answer["acceptance"][0]["id"] = "WRONG-ID"
        self.payload.write_text(json.dumps(self.answer))
        with self.controller() as controller:
            with self.assertRaises(Blocked):
                validate_task(controller, self.config, self.task, "missing-A")

    def test_exhausted_review_attempts_never_fallthrough(self):
        self.answer["acceptance"][0]["status"] = "failed"
        self.payload.write_text(json.dumps(self.answer))
        with self.controller() as controller:
            for attempt in ("review-one", "review-two", "review-three"):
                with self.assertRaises(Blocked):
                    validate_task(controller, self.config, self.task, attempt)
            state = controller.state.read()["tasks"][self.task["id"]]
            self.assertEqual(state["status"], "blocked")
            self.assertEqual(state["validation_attempts"], 2)

    def test_mutated_check_log_invalidates_evidence(self):
        with self.controller() as controller:
            result = validate_task(controller, self.config, self.task, "tamper-A")
            Path(result["checks"][0]["log"]).write_text("replaced output")
            with self.assertRaises(Blocked):
                verified_evidence(controller, self.task)

    def test_mutated_review_output_invalidates_evidence(self):
        with self.controller() as controller:
            result = validate_task(controller, self.config, self.task, "tamper-review-A")
            Path(result["review"]["response"]).write_text('{}')
            with self.assertRaises(Blocked):
                verified_evidence(controller, self.task)

    def test_task_change_invalidates_evidence(self):
        with self.controller() as controller:
            validate_task(controller, self.config, self.task, "task-change-A")
            changed = copy.deepcopy(self.task)
            changed["acceptance_ids"].append("AC-new")
            with self.assertRaises(Blocked):
                verified_evidence(controller, changed)

    def test_optional_check_cannot_silently_remove_contract(self):
        self.config["checks"][0]["required"] = False
        with self.controller() as controller:
            with self.assertRaises(Blocked):
                validate_task(controller, self.config, self.task, "optional-A")

    def test_cli_reconcile_cannot_promote_tampered_evidence(self):
        with self.controller() as controller:
            validate_task(controller, self.config, self.task, "reconcile-tamper-A")
            saved = controller.state.read()["tasks"][self.task["id"]]
            path = Path(saved["evidence"])
            evidence = json.loads(path.read_text())
            evidence["C"] = git(self.root, "rev-parse", "main")
            evidence["tree"] = git(self.root, "rev-parse", "main^{tree}")
            path.write_text(json.dumps(evidence))
        config = dict(self.config, repository_root=str(self.root))
        config["limits"] = dict(config["limits"], repair_attempts=2)
        bundle = {"config": config, "tasks": [self.task]}
        # Only parsing/preflight are replaced; the real CLI, lock, state and Git
        # reconciliation path run. This isolates evidence authenticity handling.
        with patch.object(cli, "load", return_value=bundle), patch.object(cli, "preflight", return_value=config):
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                code = cli.main(["reconcile", "--bundle", "fixture-only", "--run", "local-audit",
                                 "--task", self.task["id"]])
        self.assertNotEqual(code, 0, "tampered C promoted undelivered target to delivered")
        with self.controller() as controller:
            self.assertNotEqual(controller.state.read()["tasks"][self.task["id"]]["status"], "delivered")

    def test_cli_reconcile_is_idempotent_after_actual_delivery(self):
        with self.controller() as controller:
            result = validate_task(controller, self.config, self.task, "reconcile-twice-A")
            git(self.root, "merge", "--ff-only", result["C"])
        config = dict(self.config, repository_root=str(self.root))
        bundle = {"config": config, "tasks": [self.task]}
        with patch.object(cli, "load", return_value=bundle), patch.object(cli, "preflight", return_value=config):
            for _ in range(2):
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    code = cli.main(["reconcile", "--bundle", "fixture-only", "--run", "local-audit",
                                     "--task", self.task["id"]])
                self.assertEqual(code, 0, "repeated factual reconciliation downgraded a valid delivery")
        with self.controller() as controller:
            self.assertEqual(controller.state.read()["tasks"][self.task["id"]]["status"], "delivered")


if __name__ == "__main__":
    unittest.main(verbosity=2)
