import importlib.util
import json
import os
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[2] / "scripts/install-codex-skills.py"
spec = importlib.util.spec_from_file_location("skill_installer", SCRIPT)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


@unittest.skipUnless(sys.platform in {"linux", "darwin"}, "Native macOS/Linux installer lock")
class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="harness-install-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.source = self.base / "source"
        self.destination = self.base / "business"
        self.destination.mkdir()
        (self.destination / "README.md").write_text("Business documentation\n")
        (self.destination / "main.py").write_text("print('user code')\n")
        for name in installer.CHAIN:
            directory = self.source / "skills" / name
            directory.mkdir(parents=True)
            (directory / "SKILL.md").write_text(f"---\nname: {name}\n---\nVersion one\n")
        harness = self.source / "skills/harness-init/assets/project/harness"
        harness.mkdir(parents=True)
        (harness / "__init__.py").write_text("# Self-contained module\n")
        (harness / "controller.py").write_text("raise RuntimeError('must never execute during install')\n")

    def installed(self, name="harness-init"):
        return self.destination / ".agents/skills" / name

    def test_full_chain_install_copies_only_packages(self):
        result = installer.install(self.destination, self.source)
        self.assertEqual("installed", result["status"])
        self.assertEqual(set(installer.CHAIN), {x.name for x in self.installed().parent.iterdir()})
        self.assertTrue((self.installed() / "assets/project/harness/controller.py").is_file())
        self.assertEqual("Business documentation\n", (self.destination / "README.md").read_text())
        self.assertEqual("print('user code')\n", (self.destination / "main.py").read_text())
        self.assertFalse((self.destination / ".loop-state.json").exists())

    def test_selective_harness_is_self_contained(self):
        installer.install(self.destination, self.source, skills=["harness-init"])
        self.assertEqual(["harness-init"], [x.name for x in self.installed().parent.iterdir()])
        self.assertTrue((self.installed() / "assets/project/harness/__init__.py").is_file())

    def test_existing_name_conflict_is_preserved(self):
        self.installed().mkdir(parents=True)
        original = self.installed() / "SKILL.md"
        original.write_text("User's same-name skill")
        with self.assertRaisesRegex(installer.InstallBlocked, "same-name"):
            installer.install(self.destination, self.source, skills=["harness-init"])
        self.assertEqual("User's same-name skill", original.read_text())

    def test_upgrade_and_rollback_verify_manifest_and_backup(self):
        installer.install(self.destination, self.source, skills=["harness-init"])
        original = (self.installed() / "SKILL.md").read_bytes()
        (self.source / "skills/harness-init/SKILL.md").write_text("---\nname: harness-init\n---\nVersion two\n")
        upgraded = installer.install(self.destination, self.source, "upgrade")
        self.assertEqual("upgraded", upgraded["status"])
        self.assertIn("Version two", (self.installed() / "SKILL.md").read_text())
        backup = Path(upgraded["backup"])
        self.assertEqual(original, (backup / "skills/harness-init/SKILL.md").read_bytes())
        rolled = installer.install(self.destination, self.base / "no-longer-present-source", "rollback")
        self.assertEqual("rolled_back", rolled["status"])
        self.assertEqual(original, (self.installed() / "SKILL.md").read_bytes())
        self.assertEqual("Business documentation\n", (self.destination / "README.md").read_text())

    def test_user_edit_blocks_upgrade_and_rollback(self):
        installer.install(self.destination, self.source, skills=["harness-init"])
        edited = self.installed() / "SKILL.md"
        edited.write_text("User customization")
        for action in ("upgrade", "rollback"):
            with self.assertRaisesRegex(installer.InstallBlocked, "user changes"):
                installer.install(self.destination, self.source, action)
            self.assertEqual("User customization", edited.read_text())

    def test_added_user_file_blocks_upgrade(self):
        installer.install(self.destination, self.source, skills=["harness-init"])
        (self.installed() / "personal.md").write_text("Do not remove")
        with self.assertRaisesRegex(installer.InstallBlocked, "user changes"):
            installer.install(self.destination, self.source, "upgrade")
        self.assertEqual("Do not remove", (self.installed() / "personal.md").read_text())

    def test_tampered_backup_blocks_rollback(self):
        installer.install(self.destination, self.source, skills=["harness-init"])
        result = installer.install(self.destination, self.source, "upgrade")
        (Path(result["backup"]) / "skills/harness-init/SKILL.md").write_text("tampered")
        with self.assertRaisesRegex(installer.InstallBlocked, "user changes"):
            installer.install(self.destination, self.source, "rollback")

    def test_destination_symlink_is_refused(self):
        outside = self.base / "outside"
        outside.mkdir()
        (self.destination / ".agents").symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(installer.InstallBlocked, "Symlink"):
            installer.install(self.destination, self.source)
        self.assertEqual([], list(outside.iterdir()))

    def test_simulated_darwin_installer_uses_native_posix_lock(self):
        # Darwin dispatch tested with Linux's real flock; not a real Mac run.
        with patch.object(installer.sys, "platform", "darwin"):
            result = installer.install(self.destination, self.source, skills=["harness-init"])
        self.assertEqual("installed", result["status"])
        self.assertTrue((self.installed() / "SKILL.md").is_file())

    def test_native_windows_refused_without_creating_install_metadata(self):
        with patch.object(installer.sys, "platform", "win32"):
            with self.assertRaisesRegex(installer.InstallBlocked, "native Windows is unsupported"):
                installer.install(self.destination, self.source)
        self.assertFalse((self.destination / ".agents").exists())

    def test_caches_excluded_but_other_source_symlinks_refused(self):
        package = self.source / "skills/harness-init"
        (package / ".venv").mkdir()
        (package / ".venv/python").symlink_to(sys.executable)
        (package / "__pycache__").mkdir()
        (package / "__pycache__/cache.pyc").write_bytes(b"cache")
        installer.install(self.destination, self.source, skills=["harness-init"])
        self.assertFalse((self.installed() / ".venv").exists())
        self.assertFalse((self.installed() / "__pycache__").exists())
        (package / "external").symlink_to(self.base / "absent")
        with self.assertRaisesRegex(installer.InstallBlocked, "Symlink"):
            installer.install(self.destination, self.source, "upgrade")

    def test_real_installed_venv_survives_upgrade_and_rollback(self):
        installer.install(self.destination, self.source, skills=["harness-init"])
        runtime = self.installed() / "assets/project/.venv"
        subprocess.run([sys.executable, "-m", "venv", "--without-pip", str(runtime)], check=True,
                       capture_output=True, text=True)
        self.assertTrue((runtime / "bin/python").exists())
        marker = runtime / "fixture-runtime-marker"
        marker.write_text("Existing local runtime is preserved")
        cached = self.installed() / "assets/project/harness/__pycache__"
        cached.mkdir()
        (cached / "fixture.cpython-312.pyc").write_bytes(b"generated cache")
        (self.source / "skills/harness-init/SKILL.md").write_text("Version two")
        installer.install(self.destination, self.source, "upgrade")
        self.assertEqual("Existing local runtime is preserved", marker.read_text())
        installer.install(self.destination, self.source, "rollback")
        self.assertEqual("Existing local runtime is preserved", marker.read_text())
        (self.installed() / "SKILL.md").write_text("User changed a managed file")
        with self.assertRaisesRegex(installer.InstallBlocked, "user changes"):
            installer.install(self.destination, self.source, "upgrade")

    def test_runtime_directory_symlink_is_refused(self):
        installer.install(self.destination, self.source, skills=["harness-init"])
        outside = self.base / "external-runtime"
        outside.mkdir()
        (self.installed() / "assets/project/.venv").symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(installer.InstallBlocked, "Symlink"):
            installer.install(self.destination, self.source, "upgrade")
        self.assertEqual([], list(outside.iterdir()))

    def test_checkpoint_is_preserved_and_blocks_changes(self):
        checkpoint = self.destination / ".loop-state.json"
        checkpoint.write_text('{"active":true}')
        with self.assertRaisesRegex(installer.InstallBlocked, "checkpoint"):
            installer.install(self.destination, self.source)
        self.assertEqual('{"active":true}', checkpoint.read_text())
        self.assertFalse((self.destination / ".agents").exists())

    def test_partial_swap_failure_restores_old_version_and_leaves_journal(self):
        installer.install(self.destination, self.source, skills=["harness-init"])
        before = (self.installed() / "SKILL.md").read_bytes()
        (self.source / "skills/harness-init/SKILL.md").write_text("Version two")
        real_rename = installer.os.rename
        calls = 0

        def fail_second(src, dest):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("simulated swap failure")
            return real_rename(src, dest)

        with patch.object(installer.os, "rename", side_effect=fail_second):
            with self.assertRaisesRegex(OSError, "simulated"):
                installer.install(self.destination, self.source, "upgrade")
        self.assertEqual(before, (self.installed() / "SKILL.md").read_bytes())
        self.assertTrue((self.destination / ".agents" / installer.JOURNAL).is_file())
        with self.assertRaisesRegex(installer.InstallBlocked, "interrupted"):
            installer.install(self.destination, self.source, "upgrade")


if __name__ == "__main__":
    unittest.main()
