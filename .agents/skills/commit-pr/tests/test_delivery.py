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
        self.write_state(pr=None, creates=0, checks={}, rules=[])
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
        draft = "Make the reviewed case work.\n\nVerified with the fixture.\n"
        self.body.write_text(draft)
        self.render_fixture(draft, "<p>Make the reviewed case work.</p><p>Verified with the fixture.</p>",
                            add_ref=True)

    def git(self, *args, cwd=None):
        result = run(["git", *args], cwd=cwd or self.task, env=self.env,
                     capture_output=True, text=True, check=True)
        return result.stdout.strip()

    def state(self):
        return json.loads(self.state_path.read_text())

    def write_state(self, **changes):
        state = self.state() if self.state_path.exists() else {}
        self.state_path.write_text(json.dumps({**state, **changes}))

    def render_fixture(self, body, html, *, add_ref=False):
        renderings = {**self.state().get("renderings", {}), body: html}
        if add_ref:
            renderings[body + f"\nRefs {ISSUE}\n"] = html + f'<p>Refs <a href="{ISSUE}">{ISSUE}</a></p>'
        self.write_state(renderings=renderings)

    def commit(self, text):
        path = self.task / "feature"
        path.write_text(text + "\n")
        self.git("add", "--", "feature")
        self.git("commit", "-m", text)
        return self.git("rev-parse", "HEAD")

    def args(self, head, issue):
        return ["--repo", "Code/app", "--base", "main", "--head-repo", "Fork/app",
                "--branch", BRANCH, "--head", head, "--issue", issue]

    def command(self, mode, *args, head=None, issue=ISSUE, result=0, cwd=None):
        proc = run([sys.executable, "-B", SCRIPT, mode, *self.args(head or self.head, issue), *args],
                   cwd=cwd or self.task, env=self.env, capture_output=True, text=True)
        self.assertEqual(proc.returncode, result, proc.stdout + proc.stderr)
        return json.loads(proc.stdout)

    def publish(self, *args, **kwargs):
        return self.command("publish", "--remote", "fork", "--title", "Implement ticket 20",
                            "--body-file", self.body, *args, **kwargs)

    def check(self, *args, **kwargs):
        return self.command("checks", "--pr", "41", *args, **kwargs)

    def put_checks(self, head, check=None, status=None):
        checks = self.state()["checks"]
        checks[head] = {"check": check or [], "status": status or {}}
        self.write_state(checks=checks)

    def merge(self, head=None):
        return hashlib.sha1((self.base + (head or self.head)).encode()).hexdigest()

    def test_current_pr_checks_pass(self):
        published = self.publish()
        self.assertEqual(published["recovered_writes"], [])
        self.assertEqual(self.state()["creates"], 1)
        readback = run(["gh", "api", "--hostname", "github.com", "repos/Code/app/pulls/41"],
                       env=self.env, text=True, capture_output=True, check=True)
        pr = json.loads(readback.stdout)
        self.assertNotIn("body_html", pr)
        self.assertEqual(pr["title"], "Implement ticket 20")
        self.assertEqual(pr["body"], self.body.read_text() + f"\nRefs {ISSUE}\n")
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

    def test_plain_expect_honors_classic_and_active_app_requirements(self):
        self.publish()
        self.write_state(
            classic={"required_status_checks": {"contexts": ["ci"], "checks": [
                {"context": "ci", "app_id": 7},
            ]}},
            rules=[{"type": "required_status_checks", "parameters": {"required_status_checks": [
                {"context": "ci", "integration_id": 77},
            ]}}],
        )
        for apps, missing_app in [([5], 7), ([7], 77), ([77], 7)]:
            with self.subTest(apps=apps):
                self.put_checks(self.head, check=[("ci", "success", app) for app in apps])
                report = self.check("--expect", "ci", result=2)
                self.assertIn(missing_app, [item["app_id"] for item in report["missing"]["required"]])
        self.put_checks(self.head, check=[("ci", "success", 7), ("ci", "success", 77)])
        self.assertEqual(self.check("--expect", "ci")["state"], "passed")

    def test_ruleset_only_branch_and_legacy_publisher_are_distinct(self):
        self.publish()
        self.write_state(rules=[{"type": "required_status_checks", "parameters": {"required_status_checks": [
            {"context": "ci", "integration_id": 77},
        ]}}])
        self.put_checks(self.head, check={"ci": "success"})
        self.assertEqual(self.check("--expect", "ci", result=2)["state"], "waiting")
        self.put_checks(self.head, status={"ci": "success"})
        report = self.check("--expect", "ci", result=2)
        self.assertEqual(report["missing"]["required"], [{"name": "ci", "kind": "status", "app_id": 77}])
        self.put_checks(self.head, check=[("ci", "success", 77)])
        self.assertEqual(self.check("--expect", "ci")["state"], "passed")

    def test_same_name_check_and_status_wait_independently(self):
        self.publish()
        self.write_state(rules=[{"type": "required_status_checks", "parameters": {"required_status_checks": [
            {"context": "ci"},
        ]}}])
        self.put_checks(self.head, check={"ci": "success"})
        self.assertEqual(self.check("--expect", "ci", "--expect-status", "ci",
                                    result=2)["missing"]["status"], ["ci"])
        self.put_checks(self.head, status={"ci": "success"})
        self.assertEqual(self.check("--expect", "ci", "--expect-check", "ci",
                                    result=2)["missing"]["check"], ["ci"])
        self.put_checks(self.merge(), check={"ci": "success"})
        report = self.check("--expect", "ci", result=2)
        self.assertEqual(report["effective_sha"], self.merge())
        self.assertEqual(report["missing"]["required"], [{"name": "ci", "kind": "status", "app_id": None}])
        self.put_checks(self.merge(), check={"ci": "success"}, status={"ci": "pending"})
        self.assertEqual(self.check("--expect", "ci", result=2)["state"], "waiting")
        self.put_checks(self.merge(), check={"ci": "success"}, status={"ci": "success"})
        self.assertEqual(self.check("--expect", "ci", "--expect-status", "ci")["state"], "passed")

    def test_inaccessible_rules_and_classic_source_remain_unverified(self):
        self.publish()
        self.put_checks(self.head, check={"ci": "success"})
        self.write_state(rules_inaccessible=True)
        self.assertIn("active branch rules", self.check("--expect", "ci", result=2)["reason"])
        self.write_state(rules_inaccessible=False, classic="inaccessible")
        self.assertIn("classic branch protection", self.check("--expect", "ci", result=2)["reason"])
        self.write_state(classic={"required_status_checks": {"contexts": ["ci"]}})
        self.assertIn("classic status check sources", self.check("--expect", "ci", result=2)["reason"])

    def test_classic_details_resolve_context_only_summary(self):
        self.publish()
        self.write_state(
            classic={"required_status_checks": {"contexts": ["ci"]}},
            classic_status_details={"contexts": ["ci"], "checks": [{"context": "ci", "app_id": -1}]},
        )
        self.put_checks(self.head, status={"ci": "success"})
        self.assertEqual(self.check("--expect", "ci")["state"], "passed")

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
        local = "local:Tracker/requests/tickets/20.md#acceptance"
        gitlab = "https://gitlab.example.org/ops/work/-/issues/20"
        same_repo = "https://github.com/Code/app/issues/20"
        for body, html, issue in [
            (f"See {ISSUE}.", f"<p>See {ISSUE}.</p>", ISSUE),
            (f"[the original request]({ISSUE})", f'<p><a href="{ISSUE}">the original request</a></p>', ISSUE),
            ("Addresses Tracker/requests#20.", f'<p>Addresses <a href="{ISSUE}">Tracker/requests#20</a>.</p>',
             ISSUE),
            ("Recorded in #20.", '<p>Recorded in <a href="/Code/app/issues/20">#20</a>.</p>', same_repo),
            ("Recorded in **#20**.", "<p>Recorded in <strong>#20</strong>.</p>", same_repo),
            (f"[GitLab]({gitlab})", f'<p><a href="{gitlab}">GitLab</a></p>', gitlab),
            (f"Refs {local}", f"<p>Refs {local}</p>", local),
        ]:
            with self.subTest(body=body):
                self.render_fixture(body, html)
                self.write_state(pr={**self.state()["pr"], "body": body})
                self.assertEqual(self.publish(issue=issue)["number"], 41)
                self.assertEqual(self.state()["pr"]["body"], body)
        body = "Different tracker: Unrelated/app#20"
        self.render_fixture(body, f"<p>{body}</p>")
        self.write_state(pr={**self.state()["pr"], "body": body})
        self.assertIn("original ticket", self.publish(result=2)["reason"])
        self.assertEqual(self.state()["creates"], 1)

    def test_template_examples_are_preserved_but_do_not_link_the_ticket(self):
        template = (
            f"## Change\n\n<!-- \nExample: {ISSUE}\n-->\n"
            f"```md\nSee [issue]({ISSUE})\n```\n"
            f"> ~~~~\n> Tracker/requests#20\n> ~~~~~\n"
            f"\n    See {ISSUE}\n\nUse ``Tracker/requests#20`` in the example.\n"
            f"<pre><code>{ISSUE}</code></pre>\n"
        )
        self.body.write_text(template)
        self.render_fixture(
            template, f"<h2>Change</h2><!-- {ISSUE} --><pre><code>{ISSUE}</code></pre>"
            "<blockquote><pre><code>Tracker/requests#20</code></pre></blockquote>"
            f"<pre><code>See {ISSUE}</code></pre><p>Use <code>Tracker/requests#20</code>.</p>"
            f"<pre><code>{ISSUE}</code></pre>", add_ref=True,
        )
        self.assertEqual(self.publish()["recovered_writes"], [])
        self.assertEqual(self.state()["pr"]["body"], template + f"\nRefs {ISSUE}\n")
        examples = [
            (f"<!-- {ISSUE} -->", f"<!-- {ISSUE} -->"),
            (f"```md\n[issue]({ISSUE})\n```", f"<pre><code>[issue]({ISSUE})</code></pre>"),
            (f"~~~~\n{ISSUE}\n~~~~~", f"<pre><code>{ISSUE}</code></pre>"),
            (f"~~~\n> ~~~\n    ~~~\n{ISSUE}\n~~~", f"<pre><code>{ISSUE}</code></pre>"),
            (f"\n    {ISSUE}\n", f"<pre><code>{ISSUE}</code></pre>"),
            ("Use ``Tracker/requests#20`` in the example.", "<p>Use <code>Tracker/requests#20</code>.</p>"),
            (f"<pre><code>{ISSUE}</code></pre>", f"<pre><code>{ISSUE}</code></pre>"),
        ]
        fixed = self.commit("new task 20 revision")
        for example, html in examples:
            with self.subTest(example=example):
                body = f"{example}\n\nRelated to Tracker/requests#21\n"
                self.render_fixture(body, html + "<p>Related to Tracker/requests#21</p>")
                self.write_state(pr={**self.state()["pr"], "body": body})
                self.assertIn("original ticket", self.publish("--pr", "41", head=fixed, result=2)["reason"])
                self.assertIn("original ticket", self.check(result=2)["reason"])
        self.assertEqual(self.remote_tip(), self.head)
        self.assertEqual(self.state()["creates"], 1)

    def test_unused_reference_does_not_authorize_another_ticket(self):
        other = ISSUE.removesuffix("20") + "21"
        template = f"Related to [request 21]({other}).\n\n[template-example]: {ISSUE}\n"
        self.body.write_text(template)
        rendered = f'<p>Related to <a href="{other}">request 21</a>.</p>'
        self.render_fixture(template, rendered)
        self.assertEqual(self.publish(issue=other)["number"], 41)
        self.assertEqual(self.state()["pr"]["body"], template)

        updated = self.commit("change for ticket 20")
        for args in [(), ("--pr", "41")]:
            self.assertIn("original ticket", self.publish(*args, head=updated, result=2)["reason"])
        self.assertIn("original ticket", self.check(result=2)["reason"])
        self.assertEqual(self.remote_tip(), self.head)
        self.assertEqual(self.state()["creates"], 1)

    def test_nested_list_preserves_used_reference_and_reuses_pr(self):
        inline = ("1. Delivery summary\n   - Implementation details.\n"
                  f"     Related to [request 20]({ISSUE}).\n")
        template = (inline.replace(f"[request 20]({ISSUE})", "[request 20][original-ticket]")
                    + f"\n[original-ticket]: {ISSUE}\n")
        rendered = (f'<ol><li>Delivery summary<ul><li>Implementation details. '
                    f'Related to <a href="{ISSUE}">request 20</a>.</li></ul></li></ol>')
        self.body.write_text(template)
        self.render_fixture(template, rendered)
        self.assertEqual(self.publish()["number"], 41)
        self.assertEqual(self.state()["pr"]["body"], template)

        self.render_fixture(inline, rendered)
        self.write_state(pr={**self.state()["pr"], "body": inline})
        updated = self.commit("update nested list delivery")
        self.assertEqual(self.publish("--pr", "41", head=updated)["number"], 41)
        self.assertEqual(self.remote_tip(), updated)
        self.assertEqual(self.state()["pr"]["body"], inline)
        self.assertEqual(self.state()["creates"], 1)

    def test_clickable_code_label_preserves_template_and_reuses_pr(self):
        template = f"Related to [`request #20`]({ISSUE}).\n"
        rendered = f'<p>Related to <a href="{ISSUE}"><code>request #20</code></a>.</p>'
        self.body.write_text(template)
        self.render_fixture(template, rendered)
        self.assertEqual(self.publish()["number"], 41)
        self.assertEqual(self.state()["pr"]["body"], template)
        self.assertEqual(self.publish()["number"], 41)
        self.assertEqual(self.state()["creates"], 1)

    def test_draft_adds_visible_reference_and_keeps_template(self):
        other = ISSUE.removesuffix("20") + "21"
        template = (f"Related to [request 21]({other}).\n\n[template-example]: {ISSUE}\n"
                    "<!-- unfinished template comment\n")
        reference = f"Refs {ISSUE}\n"
        html = f'<p>Related to <a href="{other}">request 21</a>.</p>'
        self.body.write_text(template)
        self.render_fixture(template, html)
        self.render_fixture(template + "\n" + reference, html)
        self.render_fixture(reference + "\n" + template,
                            f'<p>Refs <a href="{ISSUE}">{ISSUE}</a></p>' + html)
        self.assertEqual(self.publish()["number"], 41)
        self.assertEqual(self.state()["pr"]["body"], reference + "\n" + template)

    def test_hidden_content_and_misleading_labels_do_not_authorize_updates(self):
        self.publish()
        issue = "https://github.com/Code/app/issues/20"
        other = "https://github.com/Code/app/issues/21"
        external = "https://example.org/#20"
        body = (f"[{issue}]({other}) and [#20]({external})\n\n"
                f"Plain fragment: {external}\n\n<div hidden><div><a href=\"{issue}\">#20</a></div></div>"
                f'<span style="display: none"> {issue} </span>'
                f'<script> {issue} </script><style> {issue} </style>')
        html = (f'<p><a href="{other}">{issue}</a> and <a href="{external}">#20</a></p>'
                f"<p>Plain fragment: {external}</p>" + body[body.index("<div hidden>"):])
        self.render_fixture(body, html)
        self.write_state(pr={**self.state()["pr"], "body": body})
        updated = self.commit("change for the original ticket")
        self.assertIn("original ticket", self.publish(issue=issue, head=updated, result=2)["reason"])
        self.assertIn("original ticket", self.check(issue=issue, result=2)["reason"])
        self.assertEqual(self.remote_tip(), self.head)
        self.assertEqual(self.state()["creates"], 1)

    def test_missing_rendering_blocks_before_remote_writes(self):
        self.write_state(markdown_error=True)
        self.assertIn("gh api exited 1", self.publish(result=2)["reason"])
        self.assertEqual(self.git("--git-dir", self.root / "Fork.git", "branch", "--list", BRANCH), "")
        self.assertEqual(self.state()["creates"], 0)

        self.write_state(markdown_error=False)
        self.publish()
        updated = self.commit("change after renderer failure")
        self.write_state(missing_pr_html="get")
        self.assertIn("rendered PR body", self.publish(head=updated, result=2)["reason"])
        self.assertIn("rendered PR body", self.check(result=2)["reason"])

        self.git("--git-dir", self.root / "Code.git", "update-ref", "refs/heads/release", self.base)
        self.write_state(missing_pr_html="list", pr={**self.state()["pr"], "base": "release", "state": "closed"})
        report = self.publish("--previous-head", self.head, head=updated, result=2)
        self.assertIn("rendered PR body", report["reason"])
        self.assertEqual(self.remote_tip(), self.head)
        self.assertEqual(self.state()["creates"], 1)

    def test_retargeted_closed_pr_blocks_retry_without_recorded_number(self):
        self.publish()
        self.git("--git-dir", self.root / "Code.git", "update-ref", "refs/heads/release", self.base)
        self.write_state(pr={**self.state()["pr"], "base": "release", "state": "closed"})
        for args in [("--pr", "41"), ()]:
            with self.subTest(args=args):
                report = self.publish(*args, result=2)
                self.assertIn("closed", report["reason"])
                self.assertIn("release", report["reason"])
                self.assertIn("#41", report["reason"])
        self.assertEqual(self.state()["creates"], 1)

    def test_publish_after_recreating_cleaned_task_worktree(self):
        self.git("worktree", "remove", self.task, cwd=self.repo)
        self.assertFalse(self.task.exists())
        self.assertEqual(self.git("rev-parse", f"refs/heads/{BRANCH}", cwd=self.repo), self.head)
        refusal = self.publish(cwd=self.repo, result=2)
        self.assertIn("linked task worktree", refusal["reason"])
        self.assertEqual(self.state()["creates"], 0)
        self.git("worktree", "add", self.task, BRANCH, cwd=self.repo)
        self.assertEqual(self.git("rev-parse", "HEAD"), self.head)
        self.assertEqual(self.publish()["recovered_writes"], [])
        self.assertEqual(self.remote_tip(), self.head)
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
        message_file = self.root / "message.txt"
        message_file.write_text("task fix\n")
        (self.task / "new").write_text("new ticket file\n")
        self.git("add", "--", "new")
        self.git("--literal-pathspecs", "commit", "--only", "-F", message_file, "--", "feature", "new")
        self.assertEqual(self.git("show", "--format=", "--name-only", "HEAD").splitlines(), ["feature", "new"])
        self.assertEqual(self.git("log", "-1", "--format=%s"), "task fix")
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

    def remote_tip(self):
        return self.git("--git-dir", self.root / "Fork.git", "rev-parse", f"refs/heads/{BRANCH}")

    def test_remote_race_does_not_undo_ancestor_rollback(self):
        self.publish()
        fixed = self.commit("verified fast forward")
        self.write_state(race_tip=self.base)
        self.assertIn("was not confirmed", self.publish("--pr", "41", head=fixed, result=2)["reason"])
        self.assertEqual(self.remote_tip(), self.base)
        self.assertEqual(self.state()["creates"], 1)

    def test_remote_race_does_not_overwrite_concurrent_branch_creation(self):
        self.write_state(race_tip=self.base)
        self.assertIn("was not confirmed", self.publish(result=2)["reason"])
        self.assertEqual(self.remote_tip(), self.base)
        self.assertEqual(self.state()["creates"], 0)

    def test_verified_pr_branch_cannot_be_pushed_backwards(self):
        self.publish()
        self.git("reset", "--hard", self.base)
        self.assertIn("merge-base", self.publish("--pr", "41", head=self.base, result=2)["reason"])
        self.assertEqual(self.remote_tip(), self.head)

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
