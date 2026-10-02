import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "skills/harness-init/assets/project"))
from harness.knowledge import SerenaAdapter, parse_reference_report, verify_durable_evidence
from harness.state import Blocked


class KnowledgeUnitTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="harness-knowledge-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "repo"
        self.root.mkdir()
        self.git("init", "--quiet")
        (self.root / "README.md").write_text("# Project\nRun tests with python -m unittest\n")
        self.git("add", "README.md")
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                 "commit", "--quiet", "-m", "durable source")

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.root), *args],
                              capture_output=True, text=True, check=True).stdout.strip()

    def test_exit_zero_with_stale_references_fails(self):
        with self.assertRaisesRegex(Blocked, "2 stale"):
            parse_reference_report("Stale references (2):\n  - `mem:missing` in `core`\n", 0)

    def test_native_clean_report_is_required(self):
        self.assertTrue(parse_reference_report("✓ No referential integrity issues found.\n")["clean"])
        for output in ("", "OK", "Stale references (0):", "possibly fine"):
            with self.assertRaises(Blocked):
                parse_reference_report(output)

    def test_durable_reference_binds_actual_git_commit_and_bytes(self):
        refs = verify_durable_evidence(self.root, ["README.md#project"])
        self.assertEqual(self.git("rev-parse", "HEAD"), refs[0]["commit"])
        self.assertEqual(64, len(refs[0]["sha256"]))
        (self.root / "README.md").write_text("Changed after commit")
        with self.assertRaisesRegex(Blocked, "differs"):
            verify_durable_evidence(self.root, ["README.md"])

    def test_temporary_untracked_external_and_traversal_rejected(self):
        (self.root / "untracked.md").write_text("not durable yet")
        for ref in (".harness/runs/one/log.md", "tmp/log.md", "../README.md",
                    "https://example.com/transient", "untracked.md"):
            with self.subTest(ref=ref), self.assertRaises(Blocked):
                verify_durable_evidence(self.root, [ref])

    def test_maintenance_only_is_not_core_readiness(self):
        directory = self.root / ".serena/memories"
        directory.mkdir(parents=True)
        (directory / "memory_maintenance.md").write_text("template only")
        adapter = SerenaAdapter(self.root, "/nonexistent", Path(self.temp.name) / "home")
        with self.assertRaisesRegex(Blocked, "core.md"):
            adapter.read_core()


SERENA = os.environ.get("HARNESS_TEST_SERENA")
SERENA_PYTHON = os.environ.get("HARNESS_TEST_SERENA_PYTHON")


@unittest.skipUnless(SERENA and SERENA_PYTHON, "Set HARNESS_TEST_SERENA and HARNESS_TEST_SERENA_PYTHON for native pinned tests")
class NativeSerenaTests(KnowledgeUnitTests):
    def setUp(self):
        super().setUp()
        self.home = Path(self.temp.name) / "serena-home"
        self.adapter = SerenaAdapter(self.root, SERENA, self.home, timeout_seconds=30,
                                     python_executable=SERENA_PYTHON)

    def test_native_lifecycle_preservation_and_broken_reference(self):
        version = self.adapter.probe_version()
        self.assertIn("1.7.0", version["version_output"])
        created = self.adapter.create_project(["python"])
        self.assertTrue(created["project_created"])
        self.assertFalse(created["onboarding_completed"])
        self.adapter.initialize_maintenance()
        maintenance = self.root / ".serena/memories/memory_maintenance.md"
        customized = maintenance.read_text() + "\nProject customization preserved.\n"
        maintenance.write_text(customized)
        self.adapter.initialize_maintenance()
        self.assertEqual(customized, maintenance.read_text())
        instructions = self.adapter.onboarding_instructions()
        self.assertGreater(len(instructions["instructions"]), 100)
        self.assertFalse(instructions["onboarding_completed"])
        self.assertFalse(instructions["host_activated"])
        core = "# Project core\nSmall test repository. Tests: python -m unittest.\nEvidence: [README](README.md).\n"
        written = self.adapter.write_new_memory("core", core, ["README.md"])
        self.assertEqual("core", written["memory"])
        self.assertEqual(core, self.adapter.read_core()["content"].rstrip("\n") + "\n")
        self.assertTrue(self.adapter.check_references()["clean"])
        report = self.adapter.readiness(["README.md"])
        self.assertTrue(report["structural_ready"])
        self.assertFalse(report["onboarding_completed"])
        self.assertTrue(report["semantic_review_required"])
        with self.assertRaisesRegex(Blocked, "Existing memory preserved"):
            self.adapter.write_new_memory("core", "replacement", ["README.md"])
        self.assertEqual(core, (self.root / ".serena/memories/core.md").read_text())
        (self.root / ".serena/memories/core.md").write_text(core + "\nBroken: `mem:missing_module`\n")
        with self.assertRaisesRegex(Blocked, "stale"):
            self.adapter.check_references()

    def test_copied_native_project_requires_registration(self):
        self.adapter.create_project(["python"])
        self.adapter.initialize_maintenance()
        copied = Path(self.temp.name) / "copy"
        shutil.copytree(self.root, copied)
        fresh_home = Path(self.temp.name) / "fresh-home"
        adapter = SerenaAdapter(copied, SERENA, fresh_home, python_executable=SERENA_PYTHON)
        before = (copied / ".serena/project.yml").read_bytes()
        registration = adapter.register_existing()
        self.assertTrue(registration["registered"])
        self.assertFalse(registration["host_activated"])
        self.assertFalse(registration["onboarding_completed"])
        adapter.initialize_maintenance()
        self.assertEqual(before, (copied / ".serena/project.yml").read_bytes())


if __name__ == "__main__":
    unittest.main()
