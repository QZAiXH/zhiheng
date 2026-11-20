import os
from pathlib import Path
import re
import shlex
from string import Template
import subprocess
from tempfile import TemporaryDirectory
import unittest


SKILLS = Path(__file__).resolve().parents[2]
REFERENCES = SKILLS / "implement-ticket/references"
CREATE, _, RESTORE = (REFERENCES / "task-worktree.md").read_text(
    encoding="utf-8"
).partition("## Reuse or restore")
INTEGRATE = (REFERENCES / "parallel-implementation.md").read_text()
RELEASE = (SKILLS / "accept-delivery/references/delivery-evidence.md").read_text(
    encoding="utf-8"
)


class TaskWorktreeTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory(prefix="zhiheng-worktree-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.main = self.root / "main"
        self.main.mkdir()
        self.env = {
            **os.environ,
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_SYSTEM": os.devnull,
        }
        self.git(self.main, "init", "-b", "main")
        self.git(self.main, "config", "user.name", "Worktree Test")
        self.git(self.main, "config", "user.email", "worktree@example.invalid")
        (self.main / ".gitignore").write_text(".scratch/\n")
        (self.main / "tracked.txt").write_text("base\n")
        self.git(self.main, "add", ".gitignore", "tracked.txt")
        self.git(self.main, "commit", "-m", "base")
        self.base = self.step(CREATE, "git rev-parse --verify ", base="HEAD")
        (self.main / "tracked.txt").write_text("staged\n")
        self.git(self.main, "add", "tracked.txt")
        (self.main / "tracked.txt").write_text("unstaged\n")
        (self.main / "untracked.txt").write_text("untracked\n")

    def git(self, cwd, *args):
        result = subprocess.run(
            ["git", "-C", str(cwd), *args], env=self.env, capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0, f"{args!r}\n{result.stderr}")
        return result.stdout.rstrip("\n")

    def step(self, guide, prefix, *, cwd=None, **values):
        commands = re.findall(r"`(git [^`\n]+)`", guide)
        matches = [command for command in commands if command.startswith(prefix)]
        self.assertEqual(len(matches), 1, f"{prefix!r} matched {matches!r}")
        snippet = re.sub(r"<([\w-]+)>", lambda m: "${" + m[1].replace("-", "_") + "}", matches[0])
        args = [Template(arg).substitute(values) for arg in shlex.split(snippet)[1:]]
        return self.git(cwd or self.main, *args)

    def create(self, name, start):
        path, branch = self.root / f"worktree {name}", f"task/{name}"
        self.step(CREATE, "git worktree add ", branch=branch, worktree=path, start=start)
        self.verify(path, branch, start)
        return path, branch

    def verify(self, path, branch, commit):
        self.assertEqual(self.step(CREATE, "git rev-parse --show-toplevel", cwd=path), str(path))
        self.assertEqual(self.step(CREATE, "git symbolic-ref HEAD", cwd=path), f"refs/heads/{branch}")
        self.assertEqual(self.step(CREATE, "git rev-parse HEAD", cwd=path), commit)

    def inspect(self, path):
        return self.step(RELEASE, 'git -C "$worktree" status ', worktree=path)

    def test_dirty_main_resume_release_and_reopen_ticket(self):
        tracked = self.main / "tracked.txt"
        main_before = self.inspect(self.main)

        path, branch = self.create("single", self.base)
        self.assertEqual((path / tracked.name).read_text(), "base\n")
        draft = path / "change.txt"
        draft.write_text("interrupted work\n")
        self.verify(path, branch, self.base)
        self.assertEqual(draft.read_text(), "interrupted work\n")
        self.git(path, "add", draft.name)
        self.git(path, "commit", "-m", "delivery")
        delivered = self.git(path, "rev-parse", "HEAD")

        ticket = self.root / "ticket.md"
        reports = ("tests.log", "review.md")
        for report in reports:
            (ticket.parent / report).write_text(f"{delivered} passed\n")
        ticket.write_text(
            f"Status: open\nBranch: {branch}\nDelivery: {delivered}\n"
            "Tests: tests.log\nReview: review.md\n",
            encoding="utf-8",
        )

        def reopen_ticket():
            fields = dict(line.split(": ", 1) for line in ticket.read_text().splitlines())
            ref = f"refs/heads/{fields['Branch']}"
            self.assertEqual(self.git(self.main, "rev-parse", "--verify", ref), fields["Delivery"])
            self.assertEqual(fields["Status"], "open")
            for field in ("Tests", "Review"):
                evidence = ticket.parent / fields[field]
                self.assertEqual(evidence.read_text(), f"{delivered} passed\n")

        reopen_ticket()
        self.assertEqual(self.inspect(path), "")
        self.step(RELEASE, "git worktree remove ", worktree=path)
        self.assertFalse(path.exists())
        self.assertNotIn(f"worktree {path}\n", self.step(RELEASE, "git worktree list "))
        reopen_ticket()
        self.step(RESTORE, 'git worktree add "$worktree" ', worktree=path, branch=branch)
        self.verify(path, branch, delivered)

        self.verify(self.main, "main", self.base)
        self.assertEqual(self.inspect(self.main), main_before)
        self.assertEqual(self.git(self.main, "show", ":tracked.txt"), "staged")
        self.assertEqual(tracked.read_text(), "unstaged\n")
        self.assertEqual((self.main / "untracked.txt").read_text(), "untracked\n")

    def test_dependent_slice_starts_at_integration_tip(self):
        integration, branch = self.create("integration", self.base)
        slice_a, _ = self.create("a", self.base)
        slice_b, branch_b = self.create("b", self.base)
        (slice_b / "pending.txt").touch()
        (slice_a / "a.txt").write_text("slice A\n")
        self.git(slice_a, "add", "a.txt")
        self.git(slice_a, "commit", "-m", "slice A")
        commit_a = self.git(slice_a, "rev-parse", "HEAD")
        self.git(integration, "merge", "--no-ff", "-m", "integrate A", commit_a)
        tip = self.git(integration, "rev-parse", "HEAD")
        self.verify(integration, branch, tip)
        self.step(
            INTEGRATE, "git merge-base --is-ancestor ", cwd=integration,
            worker_commit=commit_a, integration_tip=tip,
        )
        self.assertNotEqual(tip, self.base)
        slice_c, _ = self.create("c", tip)
        self.assertEqual((slice_c / "a.txt").read_text(), "slice A\n")
        self.verify(slice_b, branch_b, self.base)
        self.assertFalse((slice_b / "a.txt").exists())
        self.assertIn("?? pending.txt", self.inspect(slice_b))
        self.verify(self.main, "main", self.base)
        self.assertIn("MM tracked.txt", self.inspect(self.main))

    def test_release_inspection_exposes_ignored_only_copy(self):
        path, _ = self.create("ignored", self.base)
        ticket = path / ".scratch/ticket.md"
        ticket.parent.mkdir()
        ticket.write_text("Status: open\n")
        self.assertEqual(self.git(path, "status", "--porcelain=v1"), "")
        self.assertIn("!! .scratch/ticket.md", self.inspect(path))
