"""SIMULATED host/platform/network, native Git + pinned Serena CLI E2E.

The exact arithmetic project, spec, implementation/review script and business
checks are reused from test_cli_e2e. All repositories and remote Git objects are
real and temporary. Product CLI, contracts, controller, checks, adapter, intents,
CAS, rules, dependency and delivery proof are exercised in subprocesses.

Explicit fixture-only injection (fixtures/github_cli_fixture.py):
* simulation_scope permits only this marked temporary repo's single exact fake
  GitHub URL mapped by the fixture executable to its own native bare repository
* cli.require_capabilities passes simulate_delivery=True to the original checker
  for delivery; receipt integrity/bindings/raw logs remain checked, receipts stay
  simulation_only with real-host gaps, and normal production CLI refuses them

The fake gh protocol runs committed business tests, models pending checks and
strict/private-no-rules behavior, and native Git performs push/hooks/fetch and
squash delivery. It is not a real Codex session, authenticated GitHub/CI execution,
external network transport, real merge protection or dual-mode P5 acceptance.
No live credentials, hosts, APIs or remote repositories are used.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

import test_cli_e2e as local_fixture

PACKAGE = local_fixture.PACKAGE
HELPER = Path(__file__).with_name("fixtures") / "github_cli_fixture.py"
URL = "https://github.com/fixture/arithmetic.git"
REPOSITORY = "fixture/arithmetic"


@unittest.skipUnless(local_fixture.SERENA and local_fixture.SERENA_PYTHON and local_fixture.GIT,
                     "Native E2E requires explicit pinned Serena executable/Python and Git")
class GitHubCliE2E(unittest.TestCase):
    git = local_fixture.CliE2E.git
    state = local_fixture.CliE2E.state

    def setUp(self):
        self.started = time.monotonic()
        local_fixture.CliE2E.setUp(self)
        self.metrics = {"scenario": self._testMethodName, "baseline_git_tree": self.git("rev-parse", "HEAD^{tree}"), "tier": "SIMULATED-host-platform-network/native-Git/native-Serena",
                        "baseline_files_sha256": {name: hashlib.sha256((self.repo / name).read_bytes()).hexdigest()
                                                 for name in ("README.md", "solution.py", "docs/spec.md", "tests/run_business.py")},
                        "host_fixture_sha256": hashlib.sha256(self.host.read_bytes()).hexdigest(),
                        "tokens": "unknown: no live model", "api_cost": "unknown: no live API",
                        "human_effort": "unknown: deterministic fixture operator"}
        self.cli_calls = []
        self.env = {key: value for key, value in self.env.items()
                    if not key.startswith(("GH_", "GITHUB_", "GIT_", "CODEX_", "OPENAI_", "AZURE_"))}
        self.env.update(HOME=str(self.base / "empty-home"), XDG_CONFIG_HOME=str(self.base / "empty-config"),
                        GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                        GIT_TERMINAL_PROMPT="0", GIT_ALLOW_PROTOCOL="file", GH_PROMPT_DISABLED="1",
                        GIT_AUTHOR_NAME="Simulated Platform", GIT_AUTHOR_EMAIL="simulation@example.invalid",
                        GIT_COMMITTER_NAME="Simulated Platform", GIT_COMMITTER_EMAIL="simulation@example.invalid",
                        HARNESS_GITHUB_FIXTURE_ROOT=str(self.base), HARNESS_GITHUB_FIXTURE_NATIVE_GIT=local_fixture.GIT)
        (self.base / "empty-home").mkdir()
        (self.base / "empty-config").mkdir()
        (self.base / "SIMULATED_GITHUB_ONLY").write_text("no-network; no-model; simulation-only\n")
        self.remote = self.base / "remote.git"
        subprocess.run([local_fixture.GIT, "clone", "--quiet", "--bare", str(self.repo), str(self.remote)],
                       check=True, env=self.env, capture_output=True)
        helper = "#!" + sys.executable + "\n" + HELPER.read_text()
        for name in ("git", "gh", "fixture_cli.py"):
            path = self.bin / name
            if path.is_symlink():
                path.unlink()
            path.write_text(helper)
            path.chmod(0o700)
        self.git("remote", "add", "origin", URL)
        subprocess.run([str(self.bin / "git"), "-C", str(self.repo), "fetch", "--no-tags", "origin", "main"],
                       check=True, env=self.env, capture_output=True)
        self.platform_path = self.base / "platform.json"
        self.platform_path.write_text(json.dumps({"private": False, "rules": "strict", "issues": {}, "comments": {}, "prs": {}, "next_pr": 1}))
        # Prove the native pre-push hook chain is preserved by product source CAS.
        hook = self.repo / ".git/hooks/pre-push"
        hook.write_text("#!" + sys.executable + "\nfrom pathlib import Path\nimport sys\n"
                        "with Path(" + repr(str(self.base / "native-pre-push.log")) + ").open('a') as out:\n"
                        "    out.write(sys.stdin.read())\n")
        hook.chmod(0o700)
        config = self.bundle["config"]
        config.update(mode="github", repository_id="SIMULATED-github-arithmetic")
        config["github"] = {"server": "https://github.com", "repository": REPOSITORY,
                            "gh_version": "SIMULATED-E2E-TRANSPORT", "baseline_policy": "strict",
                            "target_branch": "main", "remote": "origin", "required_checks": ["business"],
                            "native_dependencies": True, "rules_mechanism": "rulesets"}
        config["environment"]["host"] = "SIMULATED deterministic business host"
        config["limits"].update(request_seconds=10, query_attempts=4, ci_wait_seconds=30,
                                merge_queue_wait_seconds=30, poll_seconds=0.01, control_commands=2500)
        config["p0"].update(github_total_seconds=30, github_max_requests=40, max_commands=50,
                            output_dir=str(self.base / "p0-artifacts"))

    def platform(self):
        return json.loads(self.platform_path.read_text())

    def update_platform(self, **changes):
        data = self.platform()
        data.update(changes)
        self.platform_path.write_text(json.dumps(data))

    def task(self, name, dependencies=(), issue=1):
        task = local_fixture.CliE2E.task(self, name, dependencies)
        task.update(target="refs/remotes/origin/main", github_base="main", issue_number=issue,
                    source_id=f"github:github.com:{REPOSITORY}#{issue}")
        return task

    def save_bundle(self, tasks):
        data = self.platform()
        for task in tasks:
            number = task["issue_number"]
            dependencies = [next(t["issue_number"] for t in tasks if t["id"] == dep) for dep in task["dependencies"]]
            data["issues"][str(number)] = {"number": number, "title": "SIMULATED arithmetic " + task["id"],
                                         "body": "Depends on: " + ", ".join("#" + str(dep) for dep in dependencies) if dependencies else "Fixture arithmetic task",
                                         "state": "open", "state_reason": None, "dependencies": dependencies,
                                         "repository_url": "https://api.github.com/repos/" + REPOSITORY}
        self.platform_path.write_text(json.dumps(data))
        local_fixture.CliE2E.save_bundle(self, tasks)
        self.receipt = json.loads((self.repo / ".git/harness.capabilities.json").read_text())
        self.metrics["capability_receipt_status"] = self.receipt["status"]
        self.metrics["capability_runtime_sha256"] = self.receipt["binding"]["runtime_sha256"]
        self.assertEqual("simulation", self.receipt["tier"])
        self.assertEqual("simulation_only", self.receipt["status"])
        self.assertIn("host_session_start", self.receipt["unverified"])
        self.assertIn("host_independent_review", self.receipt["unverified"])
        for name in ("serena_version", "serena_core_read", "serena_references", "repository_write", "local_process_group_stop"):
            self.assertEqual("verified", self.receipt["observations"]["capabilities"][name]["status"], name)
        self.assertTrue(self.receipt["raw_logs"])
        platform_probe = self.receipt["observations"]["github_probe"]
        self.assertEqual("verified", platform_probe["status"])
        self.assertTrue(platform_probe["logs"])
        self.assertEqual(REPOSITORY, platform_probe["observations"]["repository"]["full_name"])
        self.assertIn("SIMULATED", platform_probe["observations"]["authentication"]["login"])
        # Baseline has no business implementation/CI history, so even the
        # simulated P0 may not infer enforcing automatic delivery readiness.
        self.assertIn(platform_probe["automatic_merge_rules"]["status"], ("blocked", "not_applicable"))
        # Every scenario first exercises the unmodified CLI failure, not a claim
        # that fixture injection authorizes ordinary GitHub-mode delivery.
        before = len(self.audit_rows("gh"))
        refused = self.cli("run", "--attempt", "unpatched-production-refusal", "--implement", okay=False, injected=False)
        self.assertIn("simulation fixture must not have a remote", refused.stderr)
        self.assertEqual(before, len(self.audit_rows("gh")))
        self.assertEqual("", self.git("branch", "--list", "feature-*"))

    def cli(self, command, *args, okay=True, injected=True):
        launcher = [sys.executable, str(self.bin / "fixture_cli.py")] if injected else [sys.executable, "-m", "harness.cli"]
        argv = launcher + [command, "--bundle", str(self.bundle_path)]
        if command not in ("preflight", "evidence"):
            argv += ["--run", "e2e-run"]
        self.cli_calls.append({"command": command, "args": list(args), "injected": injected})
        result = subprocess.run(argv + list(args), env=self.env, capture_output=True, text=True, timeout=120)
        if okay:
            self.assertEqual(0, result.returncode, result.stdout + "\n" + result.stderr)
            return json.loads(result.stdout)
        self.assertNotEqual(0, result.returncode, result.stdout + "\n" + result.stderr)
        return result

    def github(self, action, okay=True, **args):
        return self.cli("github", action, "--args", json.dumps(args), okay=okay)

    def audit_rows(self, kind=None):
        path = self.base / "transport-audit.jsonl"
        rows = [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []
        return [row for row in rows if row["kind"] == kind] if kind else rows

    def run_local_validation(self, name, attempt):
        result = self.cli("run", "--attempt", attempt, "--implement")
        self.assertEqual("handoff", result["status"])
        saved = self.state()["tasks"][name]
        self.assertEqual("validating", saved["status"])
        self.assertEqual("passed", saved["local_validation"])
        self.assertEqual("simulation", saved["verification_tier"])
        evidence = json.loads(Path(saved["evidence"]).read_text())
        self.assertGreaterEqual(evidence["checks"][0]["tests"], 1)
        self.assertEqual(0, evidence["checks"][0]["failed"])
        return evidence

    def publish_and_verify(self, name, *, negative=True):
        before_target = self.git("rev-parse", "refs/remotes/origin/main")
        before = len(self.audit_rows("git-transport"))
        if negative:
            denied = self.github("push-source", task_id=name, remote="origin", okay=False)
            self.assertIn("authorization", denied.stderr)
            self.assertEqual(before, len(self.audit_rows("git-transport")))
        pushed = self.github("push-source", task_id=name, remote="origin", authorized=True)
        self.assertEqual("source_published", pushed["status"])
        source = self.git("rev-parse", "feature-" + name)
        self.assertEqual(source, pushed["source_sha"])
        self.assertEqual(source, self.git("--git-dir=" + str(self.remote), "rev-parse", "refs/heads/feature-" + name))
        self.assertEqual(before_target, self.git("--git-dir=" + str(self.remote), "rev-parse", "refs/heads/main"))
        self.assertTrue((self.base / "native-pre-push.log").read_text().strip())
        self.assertTrue(self.github("push-source", task_id=name, remote="origin", authorized=True)["reused"])
        pr = self.github("create-pr", task_id=name, title="SIMULATED " + name,
                         body="Isolated CLI fixture; not actual GitHub delivery.", authorized=True)
        number = pr["number"]
        self.assertEqual(source, pr["head"]["sha"])
        self.assertTrue(pr["draft"])
        again = self.github("create-pr", task_id=name, title="SIMULATED " + name, body="same", authorized=True)
        self.assertEqual(number, again["number"])
        checks = json.loads(self.github("checks", number=number, expected_sha=pr["merge_commit_sha"], okay=False).stdout)
        self.assertEqual("blocked", checks["status"])
        if negative:
            denied = self.github("verify", task_id=name, number=number, okay=False)
            self.assertIn("CI incomplete", denied.stderr)
            self.assertEqual("validating", self.state()["tasks"][name]["status"])
        waited = self.github("wait-checks", number=number, expected_sha=pr["merge_commit_sha"])
        self.assertEqual("pass", waited["status"])
        self.assertGreaterEqual(waited["budget"]["attempts"], 2)
        self.assertIn(str(number) + ":" + pr["merge_commit_sha"], self.state()["platform_waits"])
        verified = self.github("verify", task_id=name, number=number)
        self.assertEqual("verified", verified["status"])
        self.assertEqual("simulation", verified["verification_tier"])
        self.assertNotIn("D", self.state()["tasks"][name])
        refused = self.github("complete-issue", core_task_id=name, authorized=True, okay=False)
        self.assertIn("actual verified delivery", refused.stderr)
        return pr

    def ready_pr(self, name, number):
        # The product ready action rechecks stored proof and exact PR identity.
        denied = self.github("ready", task_id=name, number=number, okay=False)
        self.assertIn("authorization", denied.stderr)
        result = self.github("ready", task_id=name, number=number, authorized=True)
        self.assertEqual("ready", result["status"])
        self.assertFalse(self.platform()["prs"][str(number)]["draft"])
        observed = self.github("reconcile-ready", task_id=name, number=number)
        self.assertEqual("ready", observed["status"])

    def finish(self, name, number, *, merge=True):
        if merge:
            before_ops = len(self.state()["remote_operations"])
            refused = self.github("merge", task_id=name, number=number, authorized=True, okay=False)
            self.assertIn("draft", refused.stderr)
            self.assertEqual(before_ops, len(self.state()["remote_operations"]))
            self.ready_pr(name, number)
            requested = self.github("merge", task_id=name, number=number, authorized=True)
            self.assertEqual("delivery_pending", requested["status"])
            self.assertEqual("verified", self.state()["tasks"][name]["status"])
            self.assertNotIn("D", self.state()["tasks"][name])
            self.assertEqual("pending", self.state()["remote_operations"][-1]["status"])
        checkpoint = (self.repo / ".loop-state.json").read_bytes()
        remote_sha = self.git("--git-dir=" + str(self.remote), "rev-parse", "refs/heads/main")
        self.assertEqual(checkpoint, (self.repo / ".loop-state.json").read_bytes())
        reconciled = self.github("reconcile", task_id=name, number=number)
        self.assertEqual("delivered", reconciled["status"])
        self.assertTrue(reconciled["verified_delivery"])
        self.assertEqual(remote_sha, reconciled["delivered_sha"])
        self.assertEqual(remote_sha, self.git("rev-parse", "refs/remotes/origin/main"))
        self.assertEqual("delivered", self.state()["tasks"][name]["status"])
        self.assertEqual("delivered", self.github("reconcile", task_id=name, number=number)["status"])
        denied = self.cli("closeout", "--task", name, okay=False)
        self.assertIn("Issue completion", denied.stderr)
        completed = self.github("complete-issue", core_task_id=name, body="SIMULATED verified committed arithmetic/report delivery", authorized=True)
        self.assertEqual("completed", completed["status"])
        readback = self.github("reconcile-issue", core_task_id=name, body="SIMULATED verified committed arithmetic/report delivery")
        self.assertEqual(completed["receipt_id"], readback["receipt_id"])
        result = self.cli("closeout", "--task", name)
        self.assertEqual("completed", result["status"])
        self.assertEqual("simulation", result["verification_tier"])
        self.assertEqual(1, len(self.platform()["comments"][str(completed["issue"]["number"])]))
        return result

    def test_tiny_function_full_cli_github_chain(self):
        self.save_bundle([self.task("tiny")])
        self.assertTrue(self.cli("preflight")["ok"])
        # Integrity checks are not replaced: a single altered P0 log blocks run.
        log = Path(next(iter(self.receipt["raw_logs"])))
        original = log.read_bytes()
        log.write_bytes(original + b"fixture tamper\n")
        refused = self.cli("run", "--attempt", "tampered-p0", "--implement", okay=False)
        self.assertIn("raw capability evidence", refused.stderr)
        log.write_bytes(original)
        self.run_local_validation("tiny", "tiny-run")
        pr = self.publish_and_verify("tiny")
        self.finish("tiny", pr["number"])
        self.assertEqual("completed", self.cli("run", "--attempt", "tiny-completed")["status"])

    def test_exception_function_full_cli_github_chain(self):
        self.save_bundle([self.task("exception")])
        evidence = self.run_local_validation("exception", "exception-run")
        code = self.git("show", evidence["H"] + ":solution.py")
        self.assertIn("raise ValueError('zero divisor')", code)
        pr = self.publish_and_verify("exception")
        self.finish("exception", pr["number"])
        self.assertEqual("completed", self.cli("run", "--attempt", "exception-completed")["status"])

    def test_dependent_functions_cli_github_delivery_and_recovery(self):
        self.save_bundle([self.task("base", issue=1), self.task("dependent", ["base"], issue=2)])
        graph = self.github("graph")
        from harness.github import core_id
        first_id = core_id("github:github.com:" + REPOSITORY + "#1")
        second_id = core_id("github:github.com:" + REPOSITORY + "#2")
        self.assertEqual([first_id], graph["dependencies"][second_id])
        self.run_local_validation("base", "base-run")
        pr = self.publish_and_verify("base")
        held = self.cli("run", "--attempt", "dependency-not-delivered", "--implement")
        self.assertEqual("base", held["tasks"][0]["task_id"])
        self.assertEqual("", self.git("branch", "--list", "feature-dependent"))
        refused = self.cli("validate", "--task", "dependent", "--attempt", "premature", okay=False)
        self.assertIn("dependency not delivered", refused.stderr)
        self.finish("base", pr["number"])
        base_delivery = self.state()["tasks"]["base"]["D"]
        evidence = self.run_local_validation("dependent", "dependent-run")
        self.assertEqual(base_delivery, evidence["T"])
        self.assertIn("def double_sum", self.git("show", evidence["H"] + ":solution.py"))
        pr = self.publish_and_verify("dependent")
        self.finish("dependent", pr["number"])
        self.assertEqual("completed", self.cli("run", "--attempt", "chain-completed")["status"])
        self.assertEqual(2, len(self.audit_rows("merge")))
        self.assertEqual(2, len(self.audit_rows("native-business-test")))

    def test_private_no_rules_retains_review_handoff_then_manual_reconcile(self):
        self.bundle["config"]["github"]["baseline_policy"] = "review_only"
        self.update_platform(private=True, rules="inaccessible")
        self.save_bundle([self.task("tiny")])
        self.run_local_validation("tiny", "private-run")
        inaccessible = self.github("rules", base="main", okay=False)
        self.assertIn("403", inaccessible.stderr)
        pr = self.publish_and_verify("tiny")
        before = len(self.audit_rows("gh"))
        refused = self.github("merge", task_id="tiny", number=pr["number"], authorized=True, okay=False)
        self.assertIn("manual handoff", refused.stderr)
        self.assertEqual(before, len(self.audit_rows("gh")))
        self.assertEqual("verified", self.state()["tasks"]["tiny"]["status"])
        self.assertNotIn("D", self.state()["tasks"]["tiny"])
        self.assertFalse(self.platform()["prs"][str(pr["number"])]["merged"])
        # Explicitly simulated external operator, not a hidden product bypass:
        # the native remote changes, but checkpoint bytes do not. Reconcile must
        # independently fetch and prove the resulting immutable tree/ancestry.
        checkpoint = (self.repo / ".loop-state.json").read_bytes()
        code = ("import runpy; m=runpy.run_path(" + repr(str(self.bin / "gh")) + "); "
                "s=m['load_state'](); s['prs'][" + repr(str(pr["number"])) + "]['draft']=False; "
                "m['merge_pr'](s," + str(pr["number"]) + ",manual=True); m['save_state'](s)")
        subprocess.run([sys.executable, "-c", code], check=True, env=self.env, capture_output=True, text=True)
        self.assertEqual(checkpoint, (self.repo / ".loop-state.json").read_bytes())
        self.finish("tiny", pr["number"], merge=False)
        self.assertEqual(1, len(self.audit_rows("manual-merge")))
        self.assertFalse(self.audit_rows("merge"))

    def tearDown(self):
        if not hasattr(self, "metrics"):
            return
        self.metrics["elapsed_seconds"] = round(time.monotonic() - self.started, 3)
        self.metrics["product_cli_invocations"] = len(self.cli_calls)
        path = self.repo / ".loop-state.json"
        if path.exists():
            state = self.state()
            attempts = state.get("attempts", [])
            self.metrics["controlled_commands"] = len(attempts)
            self.metrics["controlled_spent_seconds"] = state.get("spent_seconds")
            self.metrics["simulated_host_implementation_calls"] = sum(str(self.host) in row.get("argv", []) and "implement" in row["argv"] for row in attempts)
            self.metrics["simulated_host_review_calls"] = sum(str(self.host) in row.get("argv", []) and "review" in row["argv"] for row in attempts)
            self.metrics["final_task_statuses"] = {key: value.get("status") for key, value in state["tasks"].items()}
            self.metrics["business_outputs"] = {}
            for key, task in state["tasks"].items():
                if task.get("evidence") and Path(task["evidence"]).is_file():
                    evidence = json.loads(Path(task["evidence"]).read_text())
                    commit = evidence["H"]
                    outputs = {}
                    for name in ("solution.py", "tests/test_business.py"):
                        raw = subprocess.run([local_fixture.GIT, "-C", str(self.repo), "show", commit + ":" + name],
                                             env=self.env, check=True, capture_output=True).stdout
                        outputs[name] = hashlib.sha256(raw).hexdigest()
                    self.metrics["business_outputs"][key] = outputs
        self.metrics["gh_protocol_calls"] = len(self.audit_rows("gh"))
        self.metrics["native_ci_business_runs"] = len(self.audit_rows("native-business-test"))
        self.metrics["simulated_network_operations"] = len(self.audit_rows("git-transport"))
        self.metrics["simulated_external_manual_merges"] = len(self.audit_rows("manual-merge"))
        print("HARNESS_GITHUB_CLI_E2E_METRICS " + json.dumps(self.metrics, sort_keys=True), flush=True)
        evidence_dir = os.environ.get("HARNESS_E2E_EVIDENCE_DIR")
        if evidence_dir:
            directory = Path(evidence_dir) / self._testMethodName
            directory.mkdir(parents=True, exist_ok=True)
            (directory / "metrics.json").write_text(json.dumps(self.metrics, indent=2, sort_keys=True))
            for source in (self.base / "transport-audit.jsonl", self.platform_path,
                           self.repo / ".git/harness.capabilities.json", path):
                if source.exists():
                    shutil.copyfile(source, directory / source.name)
            if hasattr(self, "receipt"):
                raw_directory = directory / "raw-capability-logs"
                raw_directory.mkdir(exist_ok=True)
                index = {}
                for number, (original, digest) in enumerate(self.receipt["raw_logs"].items()):
                    source = Path(original)
                    if source.is_file():
                        name = str(number) + "-" + source.name
                        shutil.copyfile(source, raw_directory / name)
                        index[original] = {"copied_path": "raw-capability-logs/" + name, "sha256": digest}
                (directory / "raw-log-index.json").write_text(json.dumps(index, indent=2, sort_keys=True))


@unittest.skipUnless(local_fixture.GIT, "Native Git is required for fixture isolation proof")
class FixtureTransportIsolation(unittest.TestCase):
    def test_only_exact_bare_transport_can_run(self):
        self.exercise_transport()

    def test_root_alias_does_not_authorize_remote_aliases(self):
        self.exercise_transport(root_alias=True)

    def exercise_transport(self, root_alias=False):
        # A nested temporary producer root catches accidental reliance on the
        # subprocess default /tmp even on Linux; macOS often uses /var/folders.
        with tempfile.TemporaryDirectory(prefix="transport-parent-") as parent:
            with tempfile.TemporaryDirectory(prefix="harness-cli-e2e-", dir=parent) as directory:
                base = Path(directory).resolve()
                visible = base
                if root_alias:
                    visible = base.parent / (base.name + "-alias")
                    visible.symlink_to(base, target_is_directory=True)
                    self.addCleanup(visible.unlink, missing_ok=True)
                repo, bare, bin_path = base / "repo", base / "remote.git", base / "bin"
                bin_path.mkdir()
                env = {"PATH": str(bin_path), "HOME": str(base), "GIT_CONFIG_NOSYSTEM": "1",
                       "GIT_CONFIG_GLOBAL": os.devnull, "GIT_ALLOW_PROTOCOL": "file",
                       # Preserve the producer's canonical namespace explicitly
                       # when constructing a credential-free child environment.
                       "TMPDIR": str(base.parent),
                       "HARNESS_GITHUB_FIXTURE_ROOT": str(visible),
                       "HARNESS_GITHUB_FIXTURE_NATIVE_GIT": local_fixture.GIT}
                def checked(argv):
                    result = subprocess.run(argv, env=env, capture_output=True, text=True)
                    self.assertEqual(0, result.returncode,
                                     "argv=" + repr(argv) + "\nstdout=" + result.stdout + "\nstderr=" + result.stderr)
                    return result
                def git(*args):
                    return checked([local_fixture.GIT, *args])
                observed_temp = checked([sys.executable, "-c", "import tempfile; print(tempfile.gettempdir())"])
                self.assertEqual(base.parent, Path(observed_temp.stdout.strip()).resolve())
                git("init", "--quiet", "-b", "main", str(repo))
                git("-C", str(repo), "config", "user.name", "Fixture")
                git("-C", str(repo), "config", "user.email", "fixture@example.invalid")
                (repo / "file").write_text("fixture")
                git("-C", str(repo), "add", ".")
                git("-C", str(repo), "commit", "--quiet", "-m", "baseline")
                git("clone", "--quiet", "--bare", str(repo), str(bare))
                (base / "SIMULATED_GITHUB_ONLY").write_text("no-network; no-model; simulation-only\n")
                shim = bin_path / "git"
                shim.write_text("#!" + sys.executable + "\n" + HELPER.read_text())
                shim.chmod(0o700)
                git("-C", str(repo), "remote", "add", "origin", URL)
                invoked_shim, invoked_repo = visible / "bin/git", visible / "repo"
                for args in (("fetch", "--no-tags", "origin", "main"),
                             ("ls-remote", "--refs", URL, "refs/heads/main"),
                             ("push", "--porcelain", URL, "HEAD:refs/heads/feature")):
                    checked([str(invoked_shim), "-C", str(invoked_repo), *args])
                rows = [json.loads(line) for line in (base / "transport-audit.jsonl").read_text().splitlines()]
                self.assertEqual(["fetch", "ls-remote", "push"], [row["command"] for row in rows])
                for row in rows:
                    self.assertIn(str(bare), row["actual_argv"])
                    self.assertNotIn(URL, row["actual_argv"])
                    self.assertNotIn("origin", row["actual_argv"])
                    self.assertEqual("file", row["allowed_protocols"])
                same_alias = base / "same-remote-alias.git"
                same_alias.symlink_to(bare, target_is_directory=True)
                other = base / "other.git"
                git("clone", "--quiet", "--bare", str(repo), str(other))
                other_alias = base / "other-remote-alias.git"
                other_alias.symlink_to(other, target_is_directory=True)
                for destination in ("https://github.com/other/repo.git", str(other), "other-remote",
                                    str(same_alias), str(other_alias)):
                    blocked = subprocess.run([str(invoked_shim), "-C", str(invoked_repo), "ls-remote", destination],
                                             env=env, capture_output=True, text=True)
                    self.assertNotEqual(0, blocked.returncode)
                    self.assertIn("unapproved", blocked.stderr)
                self.assertEqual(3, len((base / "transport-audit.jsonl").read_text().splitlines()))


if __name__ == "__main__":
    unittest.main()
