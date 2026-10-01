"""Pure CLI wiring tests; native commit proof is deliberately mocked here.

These tests exercise argument routing and approvals only. They execute no Git,
models, shell helpers, or external operations and are not a security audit.
"""
import contextlib
import copy
import io
from pathlib import Path
import unittest
from unittest.mock import patch

from harness import cli
from harness.state import Blocked
from harness.workflow import commit_mode


class MemoryState:
    def __init__(self):
        self.data = {"revision": 0, "tasks": {}}
        self.writes = 0

    def read(self):
        return copy.deepcopy(self.data)

    def write(self, data, revision):
        if revision != self.data["revision"]:
            raise AssertionError("stale test revision")
        self.data = copy.deepcopy(data)
        self.data["revision"] += 1
        self.writes += 1
        return self.read()


class ControllerCommitCLI(unittest.TestCase):
    def setUp(self):
        self.config = {"mode": "local", "repository_root": "/fixture", "checks": [],
                       "limits": {"task_attempts": 3, "repair_attempts": 2},
                       "host": {"commit_mode": "controller_commit"}}
        self.task = {"id": "tiny"}
        self.state = MemoryState()
        self.controller = type("FixtureController", (), {
            "state": self.state, "__enter__": lambda obj: obj,
            "__exit__": lambda obj, *exc: None})()
        self.receipt = {"status": "committed", "actor": "controller", "operation_id": "operation-one",
                        "H": "a" * 40, "index_synced": True}

    def invoke(self, command, *extra, capability=None):
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(cli, "load", return_value={"config": self.config, "tasks": [self.task]}))
            stack.enter_context(patch.object(cli, "preflight", return_value=self.config))
            stack.enter_context(patch.object(cli, "Controller", return_value=self.controller))
            caps = stack.enter_context(patch.object(cli, "require_capabilities", side_effect=capability))
            approved = stack.enter_context(patch("harness.workflow.require_approved_contract"))
            path = stack.enter_context(patch("harness.controller_commit.operation_worktree", return_value=Path("/fixture-worktree")))
            reconcile = stack.enter_context(patch("harness.controller_commit.reconcile", return_value=self.receipt))
            recover = stack.enter_context(patch("harness.controller_commit.recover_index", return_value=self.receipt))
            stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
            stack.enter_context(contextlib.redirect_stderr(io.StringIO()))
            result = cli.main([command, "--bundle", "fixture.json", "--run", "fixture-run",
                               "--task", "tiny", "--operation", "operation-one", *extra])
            return result, caps, approved, path, reconcile, recover

    def test_read_only_reconcile_does_not_request_capability_or_write_receipt(self):
        result, caps, approved, path, reconcile, recover = self.invoke("commit-reconcile")
        self.assertEqual(0, result)
        caps.assert_not_called(); approved.assert_not_called(); recover.assert_not_called()
        path.assert_called_once_with(self.controller, "operation-one")
        reconcile.assert_called_once_with(self.controller, self.config, self.task, Path("/fixture-worktree"), "operation-one")
        self.assertEqual(0, self.state.writes)

    def test_index_recovery_requires_explicit_authorization(self):
        result, caps, approved, path, reconcile, recover = self.invoke("commit-recover-index")
        self.assertEqual(1, result)
        caps.assert_not_called(); approved.assert_not_called(); recover.assert_not_called()
        self.assertEqual(0, self.state.writes)

    def test_stale_capability_prevents_index_recovery(self):
        result, caps, approved, path, reconcile, recover = self.invoke(
            "commit-recover-index", "--authorize", capability=Blocked("fixture stale capability"))
        self.assertEqual(1, result)
        caps.assert_called_once_with(self.controller, self.config)
        approved.assert_not_called(); recover.assert_not_called()
        self.assertEqual(0, self.state.writes)

    def test_authorized_recovery_records_actor_once(self):
        for _ in range(2):
            result, caps, approved, path, reconcile, recover = self.invoke("commit-recover-index", "--authorize")
            self.assertEqual(0, result)
            approved.assert_called_once_with(self.controller, self.config, self.task)
            recover.assert_called_once_with(self.controller, self.config, self.task, Path("/fixture-worktree"), "operation-one")
        self.assertEqual([self.receipt], self.state.data["tasks"]["tiny"]["controller_commits"])
        self.assertEqual(1, self.state.writes)

    def test_commit_mode_default_and_unknown(self):
        self.assertEqual("model_commit", commit_mode({}))
        self.assertEqual("controller_commit", commit_mode(self.config))
        with self.assertRaises(Blocked):
            commit_mode({"host": {"commit_mode": "automatic"}})


if __name__ == "__main__":
    unittest.main()
