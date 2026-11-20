from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'delivery_config.py'
GUIDE = Path('docs/agents/issue-tracker.md')
GITHUB_GUIDE = (
    '# 工单指南\n\n'
    '使用 GitHub Issues。\n'
    '- 读取工单 `gh issue view <number> -R github.example/team/tickets`\n'
    '- 可以从 PR 正文接收开发请求。\n'
    '\n## 项目手写备注\n\n历史工单见 `github.example/team/old/issues/19`。\n'
).encode()
GITLAB_GUIDE = (
    '# 工单指南\n\n'
    '使用 GitLab Issues。\n'
    '- 读取工单 `glab issue view <iid> -R https://gitlab.example/team/tickets`\n'
    '- 接收 MR 请求的规则沿用项目约定。\n'
).encode()
LOCAL_GUIDE = (
    '# 工单指南\n\n'
    '使用本地 Markdown。\n'
    '- 工单位于 `.scratch/<feature>/issues/`，保留 `Status:` 与 `## Comments`。\n'
).encode()


class DeliveryConfigTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.folder = Path(temp.name)
        self.repo = self.folder / 'repo'
        self.repo.mkdir()
        subprocess.run(['git', 'init', '-q'], cwd=self.repo, check=True, capture_output=True)
        self.guide = self.repo / GUIDE
        self.guide.parent.mkdir(parents=True)
        self.before = self.folder / 'baseline.md'
        self.after = self.folder / 'approved.md'
        self.draft = self.folder / 'draft.md'

    def config(self, *args, check=True):
        return subprocess.run(
            [sys.executable, '-B', str(SCRIPT), *args], cwd=self.repo,
            check=check, capture_output=True,
        )

    def preview(self, tracker, mode, draft=None):
        self.baseline = '/dev/null'
        if self.guide.exists():
            self.before.write_bytes(self.guide.read_bytes())
            self.baseline = str(self.before)
        self.draft.write_bytes(self.before.read_bytes() if draft is None else draft)
        self.after.write_bytes(self.config('prepare', self.draft, tracker, mode).stdout)
        diff = subprocess.run(
            ['diff', '-u', self.baseline, self.after], cwd=self.folder, capture_output=True,
        )
        self.assertIn(diff.returncode, (0, 1), diff.stderr)
        return diff.stdout

    def apply_preview(self, check=True):
        baseline_args = ('--baseline', self.before) if self.baseline != '/dev/null' else ()
        return self.config('apply', self.guide, self.after, *baseline_args, check=check)

    def assert_mode(self, mode):
        self.assertEqual(self.config('read', self.guide).stdout, f'{mode}\n'.encode())

    def test_first_setup_for_each_tracker_and_github_choice(self):
        for tracker, mode, draft in (
            ('github', 'github-pr', GITHUB_GUIDE), ('github', 'local', GITHUB_GUIDE),
            ('gitlab', 'local', GITLAB_GUIDE), ('local', 'local', LOCAL_GUIDE),
        ):
            with self.subTest(tracker=tracker, mode=mode):
                marker = f'<!-- harness-delivery: {mode} -->\n'.encode()
                self.assertIn(b'+' + marker, self.preview(tracker, mode, draft))
                self.assertFalse(self.guide.exists())

                self.apply_preview()
                self.assertEqual(self.guide.read_bytes(), draft + b'\n' + marker)
                self.assert_mode(mode)
                self.guide.unlink()

    def test_legacy_github_completion_and_two_zero_diff_reruns(self):
        self.guide.write_bytes(GITHUB_GUIDE)
        self.assert_mode('missing')
        preview = self.preview('github', 'github-pr')
        self.assertEqual(self.guide.read_bytes(), GITHUB_GUIDE)
        self.assertIn(b'+<!-- harness-delivery: github-pr -->', preview)
        self.assertNotIn(b'\n- ', preview)

        self.apply_preview()
        approved = self.guide.read_bytes()
        self.assertEqual(approved, GITHUB_GUIDE + b'\n<!-- harness-delivery: github-pr -->\n')
        before_reruns = self.guide.stat()
        for _ in range(2):
            self.assert_mode('github-pr')
            self.assertEqual(self.preview('github', 'github-pr'), b'')
            self.assertEqual(self.guide.read_bytes(), approved)
        self.apply_preview()
        after_reruns = self.guide.stat()
        self.assertEqual(after_reruns.st_ino, before_reruns.st_ino)
        self.assertEqual(after_reruns.st_mtime_ns, before_reruns.st_mtime_ns)

    def test_mode_switch_updates_one_line_and_preserves_request_intake(self):
        original = GITHUB_GUIDE.replace(b'\n', b'\r\n') + b'\r\n<!-- harness-delivery: local -->'
        self.guide.write_bytes(original)
        self.assert_mode('local')
        self.assertTrue(self.preview('github', 'github-pr'))
        self.assertEqual(self.guide.read_bytes(), original)

        self.apply_preview()
        self.assert_mode('github-pr')
        self.assertEqual(self.guide.read_bytes(), original.replace(b': local -->', b': github-pr -->'))

    def test_tracker_switch_previews_targeted_edits_and_delivery_together(self):
        original = GITHUB_GUIDE + b'\n<!-- harness-delivery: github-pr -->\n'
        self.guide.write_bytes(original)
        note = '## 项目手写备注'.encode()
        start = original.index('使用 GitHub Issues。'.encode())
        end = original.index(note)
        localized_tracker_passages = LOCAL_GUIDE.split(b'\n\n', 1)[1]
        draft = original[:start] + localized_tracker_passages + b'\n' + original[end:]
        preview = self.preview('local', 'local', draft)
        self.assertIn(b'-<!-- harness-delivery: github-pr -->', preview)
        self.assertIn(b'+<!-- harness-delivery: local -->', preview)
        self.assertIn(b'-' + '使用 GitHub Issues。'.encode(), preview)
        self.assertIn(b'+' + '使用本地 Markdown。'.encode(), preview)
        self.assertEqual(self.guide.read_bytes(), original)

        self.apply_preview()
        self.assertEqual(self.guide.read_bytes(), draft.replace(b': github-pr -->', b': local -->'))
        self.assert_mode('local')
        self.assertEqual(self.preview('local', 'local'), b'')

    def test_stale_preview_leaves_the_current_guide_alone(self):
        original = GITHUB_GUIDE + b'\n<!-- harness-delivery: local -->\n'
        self.guide.write_bytes(original)
        self.assertTrue(self.preview('github', 'github-pr'))
        intervening_edit = original.replace(b'github.example/team/old', b'github.example/team/archive')
        self.guide.write_bytes(intervening_edit)

        result = self.apply_preview(check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.guide.read_bytes(), intervening_edit)

    def test_competing_updates_from_the_same_baseline_do_not_overwrite_each_other(self):
        self.guide.write_bytes(GITHUB_GUIDE)
        self.assertTrue(self.preview('github', 'github-pr'))
        other = self.folder / 'other-approved.md'
        other.write_bytes(self.config('prepare', self.draft, 'github', 'local').stdout)

        def apply(candidate):
            return self.config(
                'apply', self.guide, candidate, '--baseline', self.before, check=False,
            )

        with ThreadPoolExecutor(max_workers=2) as executor:
            candidates = (self.after, other)
            results = list(executor.map(apply, candidates))
        self.assertCountEqual([result.returncode for result in results], [0, 1])
        winner = candidates[0] if results[0].returncode == 0 else candidates[1]
        self.assertEqual(self.guide.read_bytes(), winner.read_bytes())

    def test_apply_through_a_symlink_preserves_the_link_and_target_mode(self):
        target = self.guide.with_name('tracked-guide.md')
        target.write_bytes(GITHUB_GUIDE)
        target.chmod(0o640)
        self.guide.symlink_to(target.name)
        self.assertTrue(self.preview('github', 'local'))

        self.apply_preview()
        self.assertTrue(self.guide.is_symlink())
        self.assertEqual(target.stat().st_mode & 0o777, 0o640)
        self.assert_mode('local')

    def test_malformed_or_duplicate_lines_require_a_repair(self):
        for suffix in (
            b'<!-- harness-delivery: auto -->\n',
            b'<!-- harness-delivery local -->\n',
            b'<!-- harness-delivery: local -->\n<!-- harness-delivery: github-pr -->\n',
        ):
            with self.subTest(suffix=suffix):
                original = GITHUB_GUIDE + b'\n' + suffix
                self.guide.write_bytes(original)
                for operation in (('read', self.guide), ('prepare', self.guide, 'github', 'local')):
                    result = self.config(*operation, check=False)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertEqual(result.stdout, b'')
                self.assertEqual(self.guide.read_bytes(), original)

    def test_fenced_examples_survive_migration_and_mode_changes(self):
        examples = (
            b'  ````html\r\n<!-- harness-delivery: local -->\r\n```\r\n'
            b'<!-- harness-delivery: example -->\r\n   `````\r\n'
            b'~~~text\r\n<!-- harness-delivery: github-pr -->\r\n~~~\r\n'
        )
        self.guide.write_bytes(examples)
        self.assert_mode('missing')
        self.preview('github', 'github-pr')
        self.apply_preview()
        self.assert_mode('github-pr')
        self.preview('github', 'local')
        self.apply_preview()
        self.assertEqual(self.guide.read_bytes(), examples + b'\r\n<!-- harness-delivery: local -->\r\n')

    def test_new_setting_stays_outside_an_unclosed_fence(self):
        prefix = b'# Guide\n\n'
        example = b'```md\n<!-- harness-delivery: github-pr -->'
        self.guide.write_bytes(prefix + example)
        self.assert_mode('missing')
        self.preview('github', 'local')
        self.apply_preview()
        self.assert_mode('local')
        self.assertEqual(self.guide.read_bytes(), prefix + b'<!-- harness-delivery: local -->\n\n' + example)
        self.assertEqual(self.preview('github', 'local'), b'')

    def test_non_github_tracker_cannot_prepare_github_pr_mode(self):
        for tracker, original in (('gitlab', GITLAB_GUIDE), ('local', LOCAL_GUIDE)):
            with self.subTest(tracker=tracker):
                self.guide.write_bytes(original)
                result = self.config('prepare', self.guide, tracker, 'github-pr', check=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, b'')
                self.assertEqual(self.guide.read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
