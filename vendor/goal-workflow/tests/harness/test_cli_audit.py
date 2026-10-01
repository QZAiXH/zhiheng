"""Entrypoint wiring with a SIMULATED GitHub adapter; no external requests."""
import contextlib
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_local_audit as fixtures
from harness import cli
from harness.runtime import Controller
from filelock import FileLock, Timeout


class CliAudit(unittest.TestCase):
    commit = fixtures.LocalAudit.commit
    tearDown = fixtures.LocalAudit.tearDown

    def setUp(self):
        fixtures.LocalAudit.setUp(self)
        self.config = {"mode": "github", "repository_root": str(self.root), "checks": self.checks,
                       "limits": dict(fixtures.LIMITS, task_attempts=3, repair_attempts=2)}
        self.bundle = {"config": self.config, "tasks": []}
        self.args = ["github", "--bundle", "fixture-only", "--run", "github-audit", "merge",
                     "--args", json.dumps({"authorized": True, "number": 1})]

    def invoke(self, adapter, simulate_verified_proof=True):
        with patch.object(cli, "load", return_value=self.bundle), patch.object(cli, "preflight", return_value=self.config):
            proof = patch.object(cli, "github_verified_args", side_effect=lambda c, config, bundle, action, args: args) if simulate_verified_proof else contextlib.nullcontext()
            capabilities = patch.object(cli, "require_capabilities", return_value={"tier": "simulation", "fixture": "mocked capability boundary"}) if simulate_verified_proof else contextlib.nullcontext()
            with proof, capabilities:
                with patch("harness.github.github_action", side_effect=adapter) as called:
                    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                        code = cli.main(self.args)
            return code, called.call_count

    def test_fabricated_merge_json_without_verified_task_never_calls_adapter(self):
        self.args[-1] = json.dumps({"authorized": True, "number": 1, "task_id": "absent",
                                   "evidence": {"status": "pass", "baseline_verified": True},
                                   "delivered_reachable": True})
        code, count = self.invoke(lambda *_: {"status": "delivery_pending"}, simulate_verified_proof=False)
        self.assertEqual(code, 1)
        self.assertEqual(count, 0)

    def test_github_mutation_holds_lock_and_persists_intent_first(self):
        def adapter(*args):
            with self.assertRaises(Timeout):
                with FileLock(str(self.root / ".git/harness.run.lock"), timeout=0):
                    pass
            state = json.loads((self.root / ".loop-state.json").read_text())
            self.assertEqual(state["remote_operations"][-1]["status"], "intent")
            return {"status": "delivery_pending", "pr": 1, "remote_operation": "auto_merge_requested"}
        code, count = self.invoke(adapter)
        self.assertEqual(count, 1)

    def test_active_controller_prevents_github_mutation(self):
        with Controller(self.root, "github", "github-audit", cli.config_limits(self.config)):
            code, count = self.invoke(lambda *_: {"status": "delivery_pending"})
        self.assertEqual(code, 1)
        self.assertEqual(count, 0)

    def test_unknown_return_value_blocks_repeat_mutation(self):
        def unknown(*args):
            return {"status": "delivery_unknown", "pr": 1,
                    "remote_operation": "merge_request_outcome_unknown"}
        code, count = self.invoke(unknown)
        self.assertEqual(count, 1)
        state = json.loads((self.root / ".loop-state.json").read_text())
        self.assertEqual(state["remote_operations"][-1]["status"], "unknown")
        code, count = self.invoke(unknown)
        self.assertEqual(code, 1)
        self.assertEqual(count, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
