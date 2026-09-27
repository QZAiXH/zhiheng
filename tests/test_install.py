"""Exercise observable install/rollback behavior in isolated real directories."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / 'tools/install.py'
SPEC = importlib.util.spec_from_file_location('zh_install_under_test', MODULE)
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)


def files(root):
    return {str(p.relative_to(root)): p.read_bytes()
            for p in root.rglob('*') if p.is_file()}


class InstallationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='zh-install-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source, self.target, self.backups = (self.root / n for n in ('source', 'target', 'backups'))
        self.source.mkdir()
        self.target.mkdir()
        for name in installer.SKILLS:
            folder = self.source / name
            folder.mkdir()
            (folder / 'SKILL.md').write_text(f'---\nname: {name}\ndescription: Exercise local skill operation.\n---\n\n# Skill\n\nRead [details](references/details.md).\n')
            (folder / 'references').mkdir()
            (folder / 'references/details.md').write_text('Meaningful details.\n')
            (folder / 'LICENSE').write_text('MIT License\nCopyright (c) 2026 Test Fixture\n')
            (folder / 'agents').mkdir()
            (folder / 'agents/openai.yaml').write_text(f'interface:\n  display_name: "{name}"\n  short_description: "Exercise installation using a complete skill fixture"\n')
        (self.source / 'zh/scripts').mkdir()
        (self.source / 'zh/scripts/task.py').write_text('print("fixture task entrypoint")\n')
        old = self.target / 'zhiheng'
        old.mkdir()
        (old / 'SKILL.md').write_bytes(b'legacy skill\n')
        (old / 'history.bin').write_bytes(b'\x00\xffhistorical evidence\n')
        unrelated = self.target / 'unrelated'
        unrelated.mkdir()
        (unrelated / 'SKILL.md').write_text('Keep this exact content.\n')
        self.before = files(self.target)

    def install(self, **kwargs):
        return installer.install(self.source, self.target, self.backups, **kwargs)

    def restore(self, backup_id, **kwargs):
        return installer.restore(backup_id, self.backups, self.target, **kwargs)

    def test_preview_is_write_free(self):
        before = files(self.root)
        result = self.install(dry_run=True)
        self.assertTrue(result['dry_run'])
        self.assertEqual(files(self.root), before)
        self.assertFalse(self.backups.exists())

    def test_install_and_restore_preserve_exact_original_and_current_edits(self):
        result = self.install()
        backup = Path(result['backup'])
        self.assertEqual(files(backup / 'original/zhiheng'), files_backup_legacy(self.before))
        self.assertFalse((self.target / 'zhiheng').exists())
        self.assertEqual((self.target / 'unrelated/SKILL.md').read_bytes(), self.before['unrelated/SKILL.md'])
        for name in installer.SKILLS:
            self.assertEqual(files(self.target / name), files(self.source / name))
        (self.target / 'zh/local-notes.txt').write_text('new user content after installation')
        current = files(self.target / 'zh')
        before_preview = files(self.root)
        self.restore(result['backup_id'], dry_run=True)
        self.assertEqual(files(self.root), before_preview)
        restored = self.restore(result['backup_id'])
        self.assertEqual(files(self.target), self.before)
        self.assertEqual(files(Path(restored['archive']) / 'zh'), current)
        # Repeated restore cannot discard a later user edit.
        (self.target / 'zhiheng/after-restore.txt').write_text('keep')
        once = files(self.target)
        self.restore(result['backup_id'])
        self.assertEqual(files(self.target), once)

    def test_reinstall_has_unique_backup_and_restores_previous_generation(self):
        first = self.install()
        (self.target / 'zh/local.txt').write_text('preserved between installs')
        previous = files(self.target)
        second = self.install()
        self.assertNotEqual(first['backup_id'], second['backup_id'])
        self.restore(second['backup_id'])
        self.assertEqual(files(self.target), previous)

    def test_invalid_source_never_changes_target(self):
        (self.source / 'zh-plan/SKILL.md').write_text('not a skill')
        with self.assertRaises(installer.InstallError):
            self.install()
        self.assertEqual(files(self.target), self.before)
        self.assertFalse(self.backups.exists())

    def test_missing_resource_is_rejected_before_mutation(self):
        (self.source / 'zh/references/details.md').unlink()
        with self.assertRaises(installer.InstallError):
            self.install()
        self.assertEqual(files(self.target), self.before)
        self.assertFalse(self.backups.exists())

    def test_missing_script_is_rejected_before_mutation(self):
        (self.source / 'zh/scripts/task.py').unlink()
        with self.assertRaises(installer.InstallError):
            self.install()
        self.assertEqual(files(self.target), self.before)
        self.assertFalse(self.backups.exists())

    def test_interrupted_install_is_recoverable_and_blocks_new_install(self):
        rename = Path.rename
        def fail_new_plan(path, destination):
            if path.name == 'zh-plan' and path.parent.name == 'new':
                raise OSError('injected disk failure')
            return rename(path, destination)
        with patch.object(Path, 'rename', fail_new_plan):
            with self.assertRaises(installer.InstallError):
                self.install()
        folder, = self.backups.iterdir()
        self.assertEqual(files(folder / 'original/zhiheng'), files_backup_legacy(self.before))
        with self.assertRaises(installer.InstallError):
            self.install()
        self.restore(folder.name)
        self.assertEqual(files(self.target), self.before)
        self.assertFalse(any(self.target.glob('.zh-install-*')))

    def test_interrupted_restore_keeps_archive_and_can_retry(self):
        result = self.install()
        (self.target / 'zh/new-evidence.txt').write_text('must remain recoverable')
        copytree = installer.shutil.copytree
        def fail_legacy_copy(source, destination, *args, **kwargs):
            if Path(destination) == self.target / 'zhiheng':
                raise OSError('injected restore failure')
            return copytree(source, destination, *args, **kwargs)
        with patch.object(installer.shutil, 'copytree', fail_legacy_copy):
            with self.assertRaises(installer.InstallError):
                self.restore(result['backup_id'])
        archives = Path(result['backup']) / 'restore-archives'
        self.assertTrue(any(p.read_text() == 'must remain recoverable'
                            for p in archives.rglob('new-evidence.txt')))
        self.restore(result['backup_id'])
        self.assertEqual(files(self.target), self.before)

    def test_symlink_and_overlap_are_rejected_without_touching_destination(self):
        link = self.root / 'target-link'
        link.symlink_to(self.target, target_is_directory=True)
        with self.assertRaises(installer.InstallError):
            installer.install(self.source, link, self.backups)
        with self.assertRaises(installer.InstallError):
            installer.install(self.source, self.target, self.target / 'backups')
        self.assertEqual(files(self.target), self.before)


def files_backup_legacy(snapshot):
    return {name.removeprefix('zhiheng/'): value for name, value in snapshot.items()
            if name.startswith('zhiheng/')}


if __name__ == '__main__':
    unittest.main()
