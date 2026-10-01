"""Receipt tamper/drift gates. P0 observations are EXPLICITLY MOCKED here.

Real Git/state/hashes/scope restrictions are exercised. These unit tests cannot
create live-host proof; separate P0 and native integration suites must do that.
"""
import copy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_local_audit as fixtures
from harness.capabilities import record_capabilities, require_capabilities, binding, REQUIRED_LIVE, ZH_CHAIN
from harness.state import Blocked


class CapabilitiesAudit(unittest.TestCase):
    commit = fixtures.LocalAudit.commit
    controller = fixtures.LocalAudit.controller
    tearDown = fixtures.LocalAudit.tearDown

    def setUp(self):
        fixtures.LocalAudit.setUp(self)
        (self.root / ".harness-simulation").write_text("isolated-harness-fixture\n")
        self.commit("explicit simulation scope")
        self.script = Path(self.tmp.name) / "host-fixture.py"
        self.script.write_text("print('fixture')\n")
        skill = Path(self.tmp.name) / "skills/base"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text("---\nname: receipt-fixture\ndescription: isolated fixture\n---\nPreserve gates.\n")
        self.environment["skills_path"] = str(skill)
        self.config = {"ready": True, "mode": "local", "repository_id": "fixture/receipt",
                       "checks": self.checks, "limits": dict(fixtures.LIMITS),
                       "environment": self.environment,
                       "host": {"implementation_argv": [sys.executable, str(self.script)],
                                "review_argv": [sys.executable, str(self.script)]}}

    def record_simulation(self, controller):
        with patch("harness.p0.probe", return_value={"capabilities": {}, "fixture": "mocked P0 observations"}):
            return record_capabilities(controller, self.config, "simulation")

    def test_ready_boolean_without_receipt_is_blocked(self):
        with self.controller() as controller:
            with self.assertRaisesRegex(Blocked, "ready=true is insufficient"):
                require_capabilities(controller, self.config)

    def test_live_gate_has_document_backed_operator_acceptance_path(self):
        # This establishes gate satisfiability only: successful P0 observations
        # are mocked, so it is NOT a real live-host capability acceptance.
        review = self.root / "semantic-review.md"
        review.write_text("# Operator semantic review\nFixture purpose and code checked.\n"
                          "Sources: base.txt, feature branch feature.txt.\n"
                          "Commands and completion boundaries reviewed; no production use claimed.\n")
        self.commit("operator review evidence fixture")
        observed = {"capabilities": {name: {"status": "verified", "fixture": "mocked"} for name in REQUIRED_LIVE}}
        with self.controller() as controller:
            with patch("harness.p0.probe", return_value=observed):
                unapproved = record_capabilities(controller, self.config, "live", semantic_review="semantic-review.md")
                self.assertEqual(unapproved["status"], "blocked")
                self.assertIn("operator_semantic_knowledge_review", unapproved["unverified"])
                approved = record_capabilities(controller, self.config, "live", semantic_review="semantic-review.md",
                                               authorized_semantic=True)
            self.assertEqual(approved["status"], "ready")
            self.assertEqual(len(approved["semantic_review"]), 1)
            self.assertEqual(require_capabilities(controller, self.config)["status"], "ready")

    def test_simulation_never_authorizes_default_delivery(self):
        with self.controller() as controller:
            self.record_simulation(controller)
            self.assertEqual(require_capabilities(controller, self.config)["tier"], "simulation")
            with self.assertRaisesRegex(Blocked, "real delivery"):
                require_capabilities(controller, self.config, delivery=True)
            self.assertEqual(require_capabilities(controller, self.config, delivery=True, simulate_delivery=True)["tier"], "simulation")

    def test_simulation_rejects_remote_added_after_receipt(self):
        with self.controller() as controller:
            self.record_simulation(controller)
            fixtures.git(self.root, "remote", "add", "origin", "https://example.invalid/no-network.git")
            with self.assertRaisesRegex(Blocked, "must not have a remote"):
                require_capabilities(controller, self.config)

    def test_host_script_and_config_changes_expire_receipt(self):
        with self.controller() as controller:
            self.record_simulation(controller)
            changed = copy.deepcopy(self.config)
            changed["limits"]["command_seconds"] += 1
            with self.assertRaisesRegex(Blocked, "stale"):
                require_capabilities(controller, changed)
            self.script.write_text("print('changed host implementation')\n")
            with self.assertRaisesRegex(Blocked, "stale"):
                require_capabilities(controller, self.config)

    def test_actual_skill_instruction_edit_expires_receipt(self):
        skill = Path(self.tmp.name) / "skills/probe"
        skill.mkdir(parents=True)
        instruction = skill / "SKILL.md"
        instruction.write_text("---\nname: probe\ndescription: fixture\n---\nRequire complete evidence.\n")
        self.config["environment"]["skills_path"] = str(skill)
        with self.controller() as controller:
            self.record_simulation(controller)
            require_capabilities(controller, self.config)
            instruction.write_text("---\nname: probe\ndescription: fixture\n---\nChanged workflow instructions.\n")
            with self.assertRaisesRegex(Blocked, "stale"):
                require_capabilities(controller, self.config)

    def test_zh_chain_binds_17_dependencies_but_not_unrelated_personal_skill(self):
        skills = Path(self.tmp.name) / "installed-skills"
        for name in (*ZH_CHAIN, "unrelated-personal"):
            directory = skills / name
            directory.mkdir(parents=True)
            (directory / "SKILL.md").write_text("---\nname: " + name + "\ndescription: fixture\n---\nKeep evidence.\n")
        self.config["environment"].update(skills_path=str(skills), entry_skill="zh")
        with self.controller() as controller:
            self.record_simulation(controller)
            (skills / "unrelated-personal/SKILL.md").write_text("unrelated user edit\n")
            require_capabilities(controller, self.config)
            (skills / "zh/SKILL.md").write_text("changed zh entry\n")
            with self.assertRaisesRegex(Blocked, "stale"):
                require_capabilities(controller, self.config)

    def test_zh_chain_missing_dependency_cannot_record_capabilities(self):
        skills = Path(self.tmp.name) / "incomplete-skills"
        for name in ZH_CHAIN[:-1]:
            directory = skills / name
            directory.mkdir(parents=True)
            (directory / "SKILL.md").write_text("fixture")
        self.config["environment"].update(skills_path=str(skills), entry_skill="zh")
        with self.controller() as controller:
            with self.assertRaises(Blocked):
                self.record_simulation(controller)

    def test_receipt_or_raw_log_tampering_is_rejected(self):
        with self.controller() as controller:
            log = self.root / ".git/fixture-command.log"
            controller.execute([sys.executable, "-c", "print('original')"], self.root, "cap-log", log)
            self.record_simulation(controller)
            log.write_text("replaced output")
            with self.assertRaisesRegex(Blocked, "raw capability evidence"):
                require_capabilities(controller, self.config)

            receipt = Path(controller.state.read()["capability_receipt"]["path"])
            receipt.write_text("{}")
            with self.assertRaisesRegex(Blocked, "missing or altered"):
                require_capabilities(controller, self.config)

    def test_copied_host_drill_logs_are_bound_to_receipt(self):
        with self.controller() as controller:
            log = self.root / ".git/copied-host-start.jsonl"
            log.write_text('{"fixture":"mocked host event"}\n')
            observed = {"capabilities": {}, "host_drills": {"logs": {"start": {"path": str(log)}}}}
            with patch("harness.p0.probe", return_value=observed):
                receipt = record_capabilities(controller, self.config, "simulation")
            self.assertIn(str(log), receipt["raw_logs"], "host drill output was not bound")
            log.write_text("changed host output")
            with self.assertRaisesRegex(Blocked, "raw capability evidence"):
                require_capabilities(controller, self.config)

    def test_installed_code_or_dependency_fingerprint_drift_is_rejected(self):
        with self.controller() as controller:
            self.record_simulation(controller)
            original = binding(controller, self.config)
            for field in ("skill_sha256", "lock_sha256"):
                changed = dict(original, **{field: "different"})
                with patch("harness.capabilities.binding", return_value=changed):
                    with self.assertRaisesRegex(Blocked, "stale"):
                        require_capabilities(controller, self.config)


if __name__ == "__main__":
    unittest.main(verbosity=2)
