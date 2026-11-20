import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from subprocess import run


SKILL = Path(__file__).resolve().parents[1]
SCRIPT = SKILL / "scripts" / "pull_request.py"
ISSUE = "https://github.com/Tracker/requests/issues/20"
BRANCH = "task/20"


class DeliveryTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="commit-pr-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.repo = self.root / "repo"
        self.task = self.root / "task"
        self.state_path = self.root / "github.json"
        self.write_state(pr=None, creates=0, checks={})
        fixture = (SKILL / "tests" / "fake_github.py").read_text()
        for command in ("gh", "ssh"):
            executable = self.root / command
            executable.write_text(f"#!{sys.executable}\n{fixture}")
            executable.chmod(0o755)
        self.env = {
            **os.environ, "PATH": f"{self.root}{os.pathsep}{os.environ['PATH']}",
            "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_SSH_COMMAND": str(self.root / "ssh"), "GIT_SSH_VARIANT": "ssh",
            "DELIVERY_FIXTURE": str(self.root),
        }
        self.git("init", "-b", "main", self.repo, cwd=self.root)
        self.git("config", "user.name", "Fixture", cwd=self.repo)
        self.git("config", "user.email", "fixture@example.org", cwd=self.repo)
        for name in ("feature", "other"):
            (self.repo / name).write_text("before\n")
        self.git("add", "feature", "other", cwd=self.repo)
        self.git("commit", "-m", "base", cwd=self.repo)
        self.base = self.git("rev-parse", "HEAD", cwd=self.repo)
        for owner in ("Code", "Fork"):
            self.git("clone", "--bare", self.repo, self.root / f"{owner}.git", cwd=self.root)
        self.git("remote", "add", "fork", "git@github.com:Fork/app.git", cwd=self.repo)
        self.git("worktree", "add", "-b", BRANCH, self.task, cwd=self.repo)
        self.head = self.commit("feature implemented")
        self.body = self.root / "pr.md"
        self.body.write_text("Make the reviewed case work.\n\nVerified with the fixture.\n")

    def git(self, *args, cwd=None):
        result = run(["git", *args], cwd=cwd or self.task, env=self.env,
                     capture_output=True, text=True, check=True)
        return result.stdout.strip()

    def state(self):
        return json.loads(self.state_path.read_text())

    def write_state(self, **changes):
        state = self.state() if self.state_path.exists() else {}
        self.state_path.write_text(json.dumps({**state, **changes}))

    def commit(self, text):
        path = self.task / "feature"
        path.write_text(text + "\n")
        self.git("add", "--", "feature")
        self.git("commit", "-m", text)
        return self.git("rev-parse", "HEAD")

    def args(self, head, issue):
        return ["--repo", "Code/app", "--base", "main", "--head-repo", "Fork/app",
                "--branch", BRANCH, "--head", head, "--issue", issue]

    def command(self, mode, *args, head=None, issue=ISSUE, result=0):
        proc = run([sys.executable, "-B", SCRIPT, mode, *self.args(head or self.head, issue), *args],
                   cwd=self.task, env=self.env, capture_output=True, text=True)
        self.assertEqual(proc.returncode, result, proc.stdout + proc.stderr)
        return json.loads(proc.stdout)

    def publish(self, *args, **kwargs):
        return self.command("publish", "--remote", "fork", "--title", "Implement ticket 20",
                            "--body-file", self.body, *args, **kwargs)

    def check(self, *args, **kwargs):
        return self.command("checks", "--pr", "41", *args, **kwargs)

    def put_checks(self, head, check=None, status=None):
        checks = self.state()["checks"]
        checks[head] = {"check": check or {}, "status": status or {}}
        self.write_state(checks=checks)

    def merge(self, head=None):
        return hashlib.sha1((self.base + (head or self.head)).encode()).hexdigest()

    def test_current_pr_checks_pass(self):
        published = self.publish()
        self.put_checks(self.head, check={"ci": "success"}, status={"ci": "success"})
        report = self.check("--expect", "ci")
        self.assertEqual(published["pr"], report["scope"]["pr"])
        self.assertEqual(report["scope"]["head"], self.head)
        self.assertEqual(report["effective_sha"], self.head)
        self.assertEqual([row["id"] for row in report["observations"][self.head]],
                         ["check:1", "status:1"])
        self.assertEqual(report["state"], "passed")

    def test_failed_merge_check_then_fix_same_pr(self):
        self.publish()
        self.put_checks(self.head, check={"ci": "success"})
        self.put_checks(self.merge(), check={"ci": "failure"})
        failure = self.check("--expect", "ci", result=1)
        self.assertEqual(failure["effective_sha"], self.merge())
        self.assertEqual(failure["state"], "failed")
        fixed = self.commit("fix ci issue")
        self.assertEqual(self.publish("--pr", "41", head=fixed)["number"], 41)
        self.put_checks(self.merge(fixed), check={"ci": "success"})
        passing = self.check("--expect", "ci", head=fixed)
        self.assertEqual(passing["effective_sha"], self.merge(fixed))
        self.assertEqual(passing["state"], "passed")
        self.assertEqual(self.state()["creates"], 1)

    def test_earlier_pass_does_not_satisfy_new_head(self):
        self.publish()
        self.put_checks(self.head, check={"ci": "success"})
        self.assertEqual(self.check("--expect", "ci")["state"], "passed")
        next_head = self.commit("fix again")
        self.publish("--pr", "41", head=next_head)
        self.put_checks(next_head, check={"ci": "pending"})
        waiting = self.check("--expect", "ci", head=next_head, result=2)
        self.assertEqual(waiting["state"], "waiting")
        self.assertNotIn(self.head, waiting["observations"])
        self.assertIn("head changed", self.check(result=2)["reason"])

    def test_expected_checks_not_reported_and_merge_pending(self):
        self.publish()
        report = self.check("--expect", "ci", result=2)
        self.assertEqual(report["missing"]["effective"], ["ci"])
        self.put_checks(self.head, status={"ci": "success"})
        missing_merge = self.check("--expect-merge", "ci", result=2)
        self.assertEqual(missing_merge["missing"]["merge"], ["ci"])
        self.put_checks(self.merge(), check={"ci": "pending"})
        self.assertEqual(self.check("--expect", "ci", result=2)["effective_sha"], self.merge())

    def test_confirmed_no_applicable_checks(self):
        self.publish()
        self.assertEqual(self.check(result=2)["state"], "waiting")
        report = self.check("--none", "No active CI rules, workflows or external integration")
        self.assertEqual(report["state"], "no-applicable-checks")
        self.assertIn("No active CI rules", report["reason"])
        self.assertEqual(self.check("--none", "empty", "--expect", "ci", result=2)["state"], "waiting")

    def test_retry_reads_back_unknown_writes_and_reuses_pr(self):
        self.write_state(lost_push=True, lost_create=True)
        first = self.publish()
        self.assertTrue(any(item.startswith("git push exited") for item in first["recovered_writes"]))
        self.assertIn("gh api exited 22", first["recovered_writes"])
        self.assertEqual(self.publish()["number"], first["number"])
        self.assertEqual(self.state()["creates"], 1)
        self.assertEqual(self.git("rev-list", "--count", f"{self.base}..HEAD"), "1")
        self.assertTrue(self.state()["pr"]["body"].endswith(f"Refs {ISSUE}\n"))

    def test_existing_template_keeps_inline_ticket_links_and_body(self):
        self.publish()
        for body, issue in [
            (f"See {ISSUE} for the business case.", ISSUE),
            (f"Read [the original request]({ISSUE}) before reviewing.", ISSUE),
            ("Addresses Tracker/requests#20 in a different repository.", ISSUE),
            ("Recorded in #20 with the business case.", "https://github.com/Code/app/issues/20"),
            ("Tracked at [GitLab](https://gitlab.example.org/ops/work/-/issues/20).",
             "https://gitlab.example.org/ops/work/-/issues/20"),
        ]:
            with self.subTest(body=body):
                self.write_state(pr={**self.state()["pr"], "body": body})
                self.assertEqual(self.publish(issue=issue)["number"], 41)
                self.assertEqual(self.state()["pr"]["body"], body)
        self.write_state(pr={**self.state()["pr"], "body": "Different tracker: Unrelated/app#20"})
        self.assertIn("original ticket", self.publish(result=2)["reason"])
        self.assertEqual(self.state()["creates"], 1)

    def test_mixed_index_retains_unrelated_staged_change(self):
        hook_log = self.root / "hook-ran"
        hooks = self.root / "hooks"
        hooks.mkdir()
        hook = hooks / "pre-commit"
        hook.write_text(f'#!/bin/sh\nprintf "ran\\n" > "{hook_log}"\n')
        hook.chmod(0o755)
        self.git("config", "core.hooksPath", str(hooks))
        (self.task / "other").write_text("unrelated staged edit\n")
        self.git("add", "--", "other")
        staged = self.git("diff", "--cached", "--", "other")
        (self.task / "feature").write_text("reviewed task fix\n")
        self.git("--literal-pathspecs", "commit", "--only", "-m", "task fix", "--", "feature")
        self.assertEqual(self.git("show", "--format=", "--name-only", "HEAD"), "feature")
        self.assertEqual(self.git("diff", "--cached", "--", "other"), staged)
        self.assertEqual(self.git("status", "--short", cwd=self.repo), "")
        self.assertEqual(hook_log.read_text(), "ran\n")

    def test_remote_race_does_not_overwrite_unrelated_commit(self):
        self.publish()
        fork = self.root / "Fork.git"
        tree = self.git("--git-dir", fork, "rev-parse", f"{self.head}^{{tree}}")
        outside = self.git("--git-dir", fork, "commit-tree", tree, "-p", self.head, "-m", "outside")
        self.write_state(race_tip=outside)
        fixed = self.commit("fix")
        self.assertIn("was not confirmed", self.publish("--pr", "41", head=fixed, result=2)["reason"])
        self.assertEqual(self.git("--git-dir", fork, "rev-parse", f"refs/heads/{BRANCH}"), outside)
        self.assertEqual(self.state()["creates"], 1)

    def test_invalid_merge_or_base_movement_discards_observation(self):
        self.publish()
        self.put_checks(self.merge(), check={"ci": "success"})
        self.write_state(stale_merge=True)
        self.assertIn("does not bind", self.check("--expect", "ci", result=2)["reason"])
        self.write_state(stale_merge=False, move_base_during_checks=self.base_after_change())
        report = self.check("--expect", "ci", result=2)
        self.assertEqual(report["state"], "waiting")
        self.assertNotIn("observations", report)

    def base_after_change(self):
        repo = self.root / "Code.git"
        tree = self.git("--git-dir", repo, "rev-parse", f"{self.base}^{{tree}}")
        return self.git("--git-dir", repo, "commit-tree", tree, "-p", self.base, "-m", "base update")


if __name__ == "__main__":
    unittest.main()
