"""Task lifecycle tests using real temporary Git repositories and worktrees."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "zh" / "scripts" / "task.py"


class TaskTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.main = self.root / "project"
        self.task_tree = self.root / "project-feature"
        self.main.mkdir()
        self.git(self.main, "init", "-b", "main")
        self.git(self.main, "config", "user.name", "Test")
        self.git(self.main, "config", "user.email", "test@example.invalid")
        (self.main / "base.txt").write_text("base\n")
        self.git(self.main, "add", ".")
        self.git(self.main, "commit", "-m", "base")
        self.create()

    def git(self, where: Path, *args: str, good: bool = True) -> subprocess.CompletedProcess:
        result = subprocess.run(["git", "-C", str(where), *args], text=True,
                                capture_output=True)
        if good and result.returncode:
            self.fail(f"git {' '.join(args)}: {result.stderr}")
        return result

    def task(self, command: str, *args: str, good: bool = True) -> subprocess.CompletedProcess:
        result = subprocess.run([sys.executable, str(SCRIPT), command, "--repo",
                                 str(self.main), "--id", "demo", *args],
                                text=True, capture_output=True)
        if good and result.returncode:
            self.fail(f"task {command}: {result.stderr}")
        return result

    def create(self) -> None:
        self.task("create", "--target", "main", "--branch", "feat/demo",
                  "--worktree", str(self.task_tree))

    def commit_feature(self, name: str = "feature.txt", content: str = "feature\n") -> str:
        (self.task_tree / name).write_text(content)
        self.git(self.task_tree, "add", name)
        self.git(self.task_tree, "commit", "-m", "feature")
        return self.git(self.task_tree, "rev-parse", "HEAD").stdout.strip()

    def evidence(self, text: str = "independent review: pass\n") -> Path:
        path = self.root / "review.txt"
        path.write_text(text)
        return path

    def review(self, result: str = "pass") -> None:
        self.task("review", "--result", result, "--evidence", str(self.evidence()))

    def state(self) -> dict:
        common = Path(self.git(self.main, "rev-parse", "--git-common-dir").stdout.strip())
        if not common.is_absolute():
            common = self.main / common
        return json.loads((common / "zh" / "tasks" / "demo" / "state.json").read_text())

    def state_path(self) -> Path:
        return self.main / ".git" / "zh" / "tasks" / "demo" / "state.json"

    def test_normal_finish_and_repeat_preserve_branch_and_record(self) -> None:
        candidate = self.commit_feature()
        self.review()
        dry = self.task("finish", "--check", "test -f feature.txt", "--dry-run")
        self.assertEqual(self.git(self.main, "rev-parse", "HEAD").stdout.strip(),
                         self.state()["target_sha"])
        self.assertIn("would_merge", dry.stdout)
        self.task("finish", "--check", "test -f feature.txt")
        self.assertEqual(self.git(self.main, "rev-parse", "HEAD").stdout.strip(), candidate)
        self.assertFalse(self.task_tree.exists())
        self.assertEqual(self.git(self.main, "rev-parse", "feat/demo").stdout.strip(), candidate)
        self.assertEqual(self.state()["phase"], "done")
        self.task("finish")
        self.assertTrue((self.main / ".git" / "zh" / "tasks" / "demo" / "task.md").exists())

    def test_target_advance_requires_integration_and_new_review(self) -> None:
        self.commit_feature()
        self.review()
        (self.main / "target.txt").write_text("new target\n")
        self.git(self.main, "add", ".")
        self.git(self.main, "commit", "-m", "advance")
        refused = self.task("finish", "--check", "true", good=False)
        self.assertIn("target changed", refused.stderr)
        self.assertTrue(self.task_tree.exists())
        self.git(self.task_tree, "merge", "main")
        self.review()
        self.task("finish", "--check", "test -f target.txt")
        self.assertEqual(self.state()["phase"], "done")

    def test_divergence_and_conflict_preserve_worktrees(self) -> None:
        (self.task_tree / "base.txt").write_text("task\n")
        self.git(self.task_tree, "add", ".")
        self.git(self.task_tree, "commit", "-m", "task")
        (self.main / "base.txt").write_text("target\n")
        self.git(self.main, "add", ".")
        self.git(self.main, "commit", "-m", "target")
        self.review()
        refused = self.task("finish", "--check", "true", good=False)
        self.assertIn("cannot fast-forward", refused.stderr)
        merge = self.git(self.task_tree, "merge", "main", good=False)
        self.assertNotEqual(merge.returncode, 0)
        self.assertEqual((self.main / "base.txt").read_text(), "target\n")
        self.assertTrue(self.task_tree.exists())

    def test_dirty_target_and_untracked_source(self) -> None:
        self.commit_feature()
        self.review()
        (self.main / "untracked.txt").write_text("keep\n")
        refused = self.task("finish", "--check", "true", good=False)
        self.assertIn("target worktree is dirty", refused.stderr)
        self.assertEqual((self.main / "untracked.txt").read_text(), "keep\n")
        (self.main / "untracked.txt").unlink()
        (self.task_tree / "user.txt").write_text("keep this\n")
        refused = self.task("finish", "--check", "true", good=False)
        self.assertIn("task worktree has uncommitted", refused.stderr)
        self.assertEqual((self.task_tree / "user.txt").read_text(), "keep this\n")

    def test_ignored_source_blocks_cleanup_after_successful_merge(self) -> None:
        self.commit_feature(".gitignore", "generated/\n")
        self.review()
        generated = self.task_tree / "generated"
        generated.mkdir()
        (generated / "important.txt").write_text("preserve\n")
        refused = self.task("finish", "--check", "test -f .gitignore", good=False)
        self.assertIn("cleanup blocked", refused.stderr)
        self.assertEqual(self.state()["phase"], "cleanup_blocked")
        self.assertEqual((generated / "important.txt").read_text(), "preserve\n")
        (generated / "important.txt").unlink()
        generated.rmdir()
        self.task("finish")
        self.assertEqual(self.state()["phase"], "done")

    def test_noncolliding_ignored_target_is_preserved(self) -> None:
        (self.main / ".gitignore").write_text("build/\n")
        self.git(self.main, "add", ".gitignore")
        self.git(self.main, "commit", "-m", "ignore build")
        self.git(self.task_tree, "merge", "main")
        self.commit_feature()
        self.review()
        build = self.main / "build"
        build.mkdir()
        (build / "local.txt").write_text("keep\n")
        self.task("finish", "--check", "test -f feature.txt")
        self.assertEqual((build / "local.txt").read_text(), "keep\n")

    def test_ignored_target_collision_is_refused(self) -> None:
        (self.main / ".gitignore").write_text("build/\n")
        self.git(self.main, "add", ".gitignore")
        self.git(self.main, "commit", "-m", "ignore build")
        self.git(self.task_tree, "merge", "main")
        build = self.task_tree / "build"
        build.mkdir()
        (build / "output.txt").write_text("candidate\n")
        self.git(self.task_tree, "add", "-f", "build/output.txt")
        self.git(self.task_tree, "commit", "-m", "track generated path")
        self.review()
        target_build = self.main / "build"
        target_build.mkdir()
        (target_build / "output.txt").write_text("valuable local data\n")
        refused = self.task("finish", "--check", "true", good=False)
        self.assertNotEqual(refused.returncode, 0)
        self.assertEqual((target_build / "output.txt").read_text(), "valuable local data\n")
        self.assertTrue(self.task_tree.exists())

    def test_failed_and_stale_review_or_check(self) -> None:
        self.commit_feature()
        self.review("fail")
        refused = self.task("finish", "--check", "true", good=False)
        self.assertIn("passing independent review", refused.stderr)
        self.review()
        self.commit_feature("later.txt", "later\n")
        refused = self.task("finish", "--check", "true", good=False)
        self.assertIn("candidate changed", refused.stderr)
        self.review()
        Path(self.state()["review"]["evidence"]).write_text("changed evidence\n")
        refused = self.task("finish", "--check", "true", good=False)
        self.assertIn("review evidence is missing or changed", refused.stderr)
        # Re-recording the source restores a valid immutable snapshot.
        new_evidence = self.evidence("new independent review: pass\n")
        self.task("review", "--result", "pass", "--evidence", str(new_evidence))
        refused = self.task("finish", "--check", "false", good=False)
        self.assertIn("integration check failed", refused.stderr)
        self.assertEqual(self.state()["phase"], "check_failed")
        self.assertTrue(self.task_tree.exists())
        self.task("finish", "--check", "true")

    def test_interrupted_after_merge_recovers(self) -> None:
        candidate = self.commit_feature()
        self.review()
        state = self.state()
        state["phase"] = "merge_intent"
        self.state_path().write_text(json.dumps(state))
        self.git(self.main, "merge", "--ff-only", candidate)
        self.task("finish", "--check", "test -f feature.txt")
        self.assertEqual(self.state()["phase"], "done")

    def test_keep_worktree_and_cleanup_interruption(self) -> None:
        self.commit_feature()
        self.review()
        self.task("finish", "--check", "test -f feature.txt", "--keep-worktree")
        self.assertEqual(self.state()["phase"], "checked")
        self.assertTrue(self.task_tree.exists())
        self.task("finish", "--keep-worktree")
        self.assertTrue(self.task_tree.exists())
        state = self.state()
        state["phase"] = "cleanup_intent"
        self.state_path().write_text(json.dumps(state))
        self.git(self.main, "worktree", "remove", str(self.task_tree))
        self.task("finish")
        self.assertEqual(self.state()["phase"], "done")

    def test_missing_worktree_without_cleanup_intent_is_not_done(self) -> None:
        self.commit_feature()
        self.review()
        self.task("finish", "--check", "true", "--keep-worktree")
        self.git(self.main, "worktree", "remove", str(self.task_tree))
        refused = self.task("finish", good=False)
        self.assertIn("missing without a recorded cleanup intent", refused.stderr)

    def test_check_evidence_and_target_state_are_required(self) -> None:
        self.commit_feature()
        self.review()
        refused = self.task("finish", "--check", "touch generated.txt", good=False)
        self.assertIn("evidence is invalid", refused.stderr)
        self.assertEqual(self.state()["phase"], "check_invalid")
        self.assertTrue((self.main / "generated.txt").exists())
        (self.main / "generated.txt").unlink()
        self.task("finish", "--check", "true", "--keep-worktree")
        Path(self.state()["check"]["log"]).write_text("tampered")
        refused = self.task("finish", good=False)
        self.assertIn("post-merge --check", refused.stderr)
        self.task("finish", "--check", "true")

    def test_adopt_existing_worktree(self) -> None:
        self.git(self.main, "worktree", "add", "-b", "feat/second",
                 str(self.root / "existing"), "main")
        result = self.task("adopt", "--target", "main", "--branch", "feat/second",
                           "--worktree", str(self.root / "existing"), good=False)
        self.assertIn("already registered", result.stderr)
        result = subprocess.run([sys.executable, str(SCRIPT), "adopt", "--repo",
                                 str(self.main), "--id", "second", "--target", "main",
                                 "--branch", "feat/second", "--worktree",
                                 str(self.root / "existing")], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
