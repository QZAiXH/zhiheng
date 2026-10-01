"""Real Git/worktree initializer tests; no live project or remote is touched."""

import hashlib
import ctypes
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


HERE = Path(__file__).resolve()
if (HERE.parents[1] / "scripts" / "init_project.py").is_file():
    SCRIPTS = HERE.parents[1] / "scripts"
else:
    SCRIPTS = HERE.parents[2] / "skills" / "harness-init" / "assets" / "project" / "harness"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("init_project_under_test", SCRIPTS / "init_project.py")
init = importlib.util.module_from_spec(spec)
spec.loader.exec_module(init)


@unittest.skipUnless(sys.platform in {"linux", "darwin"}, "Initializer supports macOS and Linux/WSL")
class InitProjectTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="harness-init-test-")
        self.addCleanup(self.temp.cleanup)
        # macOS commonly exposes /var as a symlink to /private/var; Git and the
        # initializer intentionally report the canonical working-tree path.
        self.root = Path(self.temp.name).resolve() / "repo"
        self.root.mkdir()
        self.git("init", "--quiet")
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                 "commit", "--quiet", "--allow-empty", "-m", "test baseline")
        self.common = self.root / ".git"

    def git(self, *args):
        result = subprocess.run(["git", "-C", str(self.root), *args],
                                capture_output=True, text=True, check=True)
        return result.stdout.strip()

    def invoke(self, *args, repo=None):
        return subprocess.run(
            [sys.executable, str(SCRIPTS / "init_project.py"), "--repo", str(repo or self.root), *args],
            capture_output=True, text=True,
        )

    def snapshot(self):
        return {
            str(p.relative_to(self.root)): ("dir" if p.is_dir() else p.read_bytes())
            for p in self.root.rglob("*")
        }

    def test_create_consistent_draft_only(self):
        before_head = self.git("rev-parse", "HEAD")
        result = self.invoke("--mode", "local")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual("initialized_draft", report["status"])
        self.assertFalse(report["ready"])
        config_bytes = (self.root / ".harness/config.json").read_bytes()
        config = json.loads(config_bytes)
        manifest = json.loads((self.root / ".harness/manifest.json").read_bytes())
        self.assertFalse(config["ready"])
        self.assertGreater(len(config["missing_p0"]), 10)
        self.assertEqual(str(self.root), config["repository_root"])
        self.assertEqual("local", config["mode"])
        self.assertNotIn("github", config)
        self.assertEqual([], config["checks"])
        self.assertEqual({"commit_mode": "controller_commit"}, config["host"])
        self.assertIn("task.allowed_paths", config["missing_p0"])
        self.assertIn("approved_contract", config["missing_p0"])
        self.assertFalse(manifest["ready"])
        self.assertEqual(hashlib.sha256(config_bytes).hexdigest(),
                         manifest["generated_files"][".harness/config.json"]["sha256"])
        self.assertEqual(hashlib.sha256((SCRIPTS / "init_project.py").read_bytes()).hexdigest(),
                         manifest["generator"]["sha256"])
        self.assertEqual(before_head, self.git("rev-parse", "HEAD"))
        self.assertEqual({"config.json", "manifest.json"},
                         {p.name for p in (self.root / ".harness").iterdir()})
        self.assertFalse((self.root / ".serena").exists())
        self.assertFalse((self.root / "AGENTS.md").exists())
        self.assertFalse((self.root / ".loop-state.json").exists())

    def test_default_local_never_uses_remote_or_gh(self):
        self.assertEqual("", self.git("remote"))
        real_run = init.subprocess.run
        calls = []

        def spy(argv, **kwargs):
            calls.append(argv)
            self.assertEqual("git", argv[0])
            self.assertNotIn("remote", argv)
            self.assertNotIn("fetch", argv)
            self.assertNotIn("push", argv)
            return real_run(argv, **kwargs)

        with patch.object(init.subprocess, "run", side_effect=spy):
            result = init.initialize(self.root)
        self.assertEqual("local", result["mode"])
        self.assertTrue(calls)

    def test_github_is_explicit_draft_without_authentication(self):
        result = self.invoke("--mode", "github")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        config = json.loads((self.root / ".harness/config.json").read_text())
        self.assertEqual("github", config["mode"])
        self.assertEqual("", config["github"]["repository"])
        self.assertFalse(config["ready"])

    def test_user_config_is_preserved_and_needs_review(self):
        harness = self.root / ".harness"
        harness.mkdir()
        original = b'{"mode":"github","user_setting":"do not touch"}\n'
        (harness / "config.json").write_bytes(original)
        before = self.snapshot()
        result = self.invoke()
        self.assertEqual(2, result.returncode)
        self.assertEqual("needs_review", json.loads(result.stdout)["status"])
        self.assertEqual(before, self.snapshot())

    def test_existing_checkpoint_refuses_even_when_lock_is_free(self):
        (self.root / ".loop-state.json").write_text('{"status":"running"}')
        before = self.snapshot()
        result = self.invoke()
        self.assertEqual(2, result.returncode)
        self.assertIn("recovery controller", json.loads(result.stdout)["reason"])
        self.assertEqual(before, self.snapshot())

    def test_dangling_checkpoint_symlink_is_also_refused(self):
        (self.root / ".loop-state.json").symlink_to(self.root / "absent")
        result = self.invoke()
        self.assertEqual(2, result.returncode)
        self.assertIn("recovery controller", json.loads(result.stdout)["reason"])
        self.assertFalse((self.root / ".harness").exists())

    def test_harness_symlink_does_not_escape_repo(self):
        outside = Path(self.temp.name) / "outside"
        outside.mkdir()
        (self.root / ".harness").symlink_to(outside, target_is_directory=True)
        result = self.invoke()
        self.assertEqual(2, result.returncode)
        self.assertIn("symlink", json.loads(result.stdout)["reason"])
        self.assertEqual([], list(outside.iterdir()))

    def test_lock_symlink_never_truncates_target(self):
        outside = Path(self.temp.name) / "outside"
        outside.write_bytes(b"private user data")
        (self.common / init.LOCK_NAME).symlink_to(outside)
        result = self.invoke()
        self.assertEqual(2, result.returncode)
        self.assertEqual(b"private user data", outside.read_bytes())
        self.assertFalse((self.root / ".harness").exists())

    def test_nonempty_lock_is_preserved(self):
        lock = self.common / init.LOCK_NAME
        lock.write_bytes(b"unrecognized lock metadata")
        result = self.invoke()
        self.assertEqual(2, result.returncode)
        self.assertEqual(b"unrecognized lock metadata", lock.read_bytes())

    def test_common_lock_excludes_another_worktree(self):
        from filelock import UnixFileLock
        worktree = Path(self.temp.name) / "worktree"
        self.git("worktree", "add", "--quiet", "-b", "other", str(worktree))
        lock = UnixFileLock(str(self.common / init.LOCK_NAME), timeout=0)
        with lock:
            result = self.invoke(repo=worktree)
            self.assertEqual(2, result.returncode, result.stdout + result.stderr)
            self.assertIn("Another process", json.loads(result.stdout)["reason"])
            self.assertFalse((worktree / ".harness").exists())
        result = self.invoke(repo=worktree)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertEqual(str(self.common / init.LOCK_NAME), json.loads(result.stdout)["lock_path"])
        self.assertFalse((self.root / ".harness").exists())

    def test_other_worktree_checkpoint_requires_recovery_even_if_lock_free(self):
        worktree = Path(self.temp.name) / "worktree"
        self.git("worktree", "add", "--quiet", "-b", "other", str(worktree))
        (self.root / ".loop-state.json").write_text('{"active":true}')
        result = self.invoke(repo=worktree)
        self.assertEqual(2, result.returncode)
        self.assertIn("recovery controller", json.loads(result.stdout)["reason"])
        self.assertFalse((worktree / ".harness").exists())

    def test_shared_execution_journal_requires_reconciliation(self):
        (self.common / "harness.execution.json").write_text('{"stopped":false}')
        result = self.invoke()
        self.assertEqual(2, result.returncode)
        self.assertIn("Shared harness.execution.json", json.loads(result.stdout)["reason"])
        self.assertFalse((self.root / ".harness").exists())

    def test_dry_run_is_fully_nonmutating(self):
        before = self.snapshot()
        result = self.invoke("--dry-run")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual("dry_run", report["status"])
        self.assertFalse(report["lock_acquired"])
        self.assertEqual(before, self.snapshot())

    def test_repository_directory_alias_reports_canonical_paths(self):
        # Reproduce the macOS /var -> /private/var distinction without weakening
        # the separate no-symlink rules for .harness or individual artifacts.
        alias = self.root.parent / "directory-alias"
        alias.symlink_to(self.root.parent, target_is_directory=True)
        result = self.invoke(repo=alias / self.root.name)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(str(self.root.resolve()), report["repo"])
        self.assertEqual(str((self.common / init.LOCK_NAME).resolve()), report["lock_path"])
        config = json.loads((self.root / ".harness/config.json").read_text())
        self.assertEqual(str(self.root.resolve()), config["repository_root"])

    def test_interrupted_creation_is_not_repaired_or_overwritten(self):
        real_write = init.exclusive_write

        def interrupted(directory_fd, name, data):
            if name == "manifest.json":
                raise OSError("simulated interruption")
            real_write(directory_fd, name, data)

        with patch.object(init, "exclusive_write", side_effect=interrupted):
            with self.assertRaises(OSError):
                init.initialize(self.root)
        config = (self.root / ".harness/config.json").read_bytes()
        self.assertFalse((self.root / ".harness/manifest.json").exists())
        result = self.invoke()
        self.assertEqual(2, result.returncode)
        self.assertEqual("needs_review", json.loads(result.stdout)["status"])
        self.assertEqual(config, (self.root / ".harness/config.json").read_bytes())
        self.assertFalse((self.root / ".harness/manifest.json").exists())

    def test_unknown_or_network_filesystem_is_refused(self):
        for kind in ("nfs", "cifs", "fuse.sshfs", "9p", "drvfs", "unknown"):
            with self.subTest(kind=kind):
                with patch.object(init.sys, "platform", "linux"), patch.object(Path, "read_text", return_value=f"1 0 0:1 / / rw - {kind} none rw\n"):
                    with self.assertRaisesRegex(init.InitRefused, "Unsupported filesystem"):
                        init.require_local_linux(self.root)

    def test_unsupported_os_is_refused(self):
        with patch.object(init.sys, "platform", "win32"):
            with self.assertRaisesRegex(init.InitRefused, "native Windows is unsupported"):
                init.initialize(self.root)

    def test_simulated_darwin_requires_local_apfs_or_hfs(self):
        for kind in ("apfs", "hfs"):
            with self.subTest(kind=kind), patch.object(init.sys, "platform", "darwin"), \
                    patch.object(init, "_darwin_filesystem", return_value=(kind, True)):
                self.assertEqual({str(self.root): kind}, init.require_supported_local_filesystems(self.root))
        for observation in (("apfs", False), ("smbfs", False), ("nfs", False), ("macfuse", True), ("unknown", True)):
            with self.subTest(observation=observation), patch.object(init.sys, "platform", "darwin"), \
                    patch.object(init, "_darwin_filesystem", return_value=observation):
                with self.assertRaisesRegex(init.InitRefused, "only local APFS/HFS"):
                    init.require_supported_local_filesystems(self.root)

    def test_simulated_darwin_native_structure_decodes_type_and_local_flag(self):
        def native_fstatfs(descriptor, address):
            self.assertTrue(os.path.isdir(self.root))
            self.assertGreaterEqual(descriptor, 0)
            record = ctypes.cast(address, ctypes.POINTER(init._DarwinStatfs64)).contents
            record.f_fstypename = b"apfs"
            record.f_flags = init.DARWIN_MNT_LOCAL
            return 0

        with patch.object(init, "_load_darwin_fstatfs", return_value=native_fstatfs):
            self.assertEqual(("apfs", True), init._darwin_filesystem(self.root))
        with patch.object(init, "_load_darwin_fstatfs", return_value=lambda fd, record: -1):
            with self.assertRaisesRegex(init.InitRefused, "fstatfs failed"):
                init._darwin_filesystem(self.root)

    def test_simulated_darwin_uses_dev_fd_and_preserves_actual_lock_exclusion(self):
        # Runs the Darwin alias selection against Linux's real /dev/fd device;
        # this is platform simulation, not evidence of an actual macOS run.
        from filelock import UnixFileLock, Timeout
        with patch.object(init.sys, "platform", "darwin"):
            self.assertEqual("/dev/fd/42", init._descriptor_alias(42))
            with init.repository_lock(self.common, UnixFileLock, Timeout):
                with self.assertRaises(init.InitRefused):
                    with init.repository_lock(self.common, UnixFileLock, Timeout):
                        self.fail("separate descriptor acquired the already locked inode")
        self.assertEqual(b"", (self.common / init.LOCK_NAME).read_bytes())

    def test_simulated_darwin_fails_closed_when_native_api_unavailable(self):
        class EmptyLibrary:
            pass
        with patch.object(init.sys, "platform", "darwin"), \
                patch.object(init.platform, "machine", return_value="x86_64"), \
                patch.object(init.ctypes, "CDLL", return_value=EmptyLibrary()):
            with self.assertRaisesRegex(init.InitRefused, "fstatfs API unavailable"):
                init._load_darwin_fstatfs()


if __name__ == "__main__":
    unittest.main()
