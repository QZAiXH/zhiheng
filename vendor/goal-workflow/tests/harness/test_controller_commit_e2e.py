"""Optional controller-commit CLI chains, with native Git and pinned Serena.

The host below only edits and runs deterministic assertions. Product CLI must
inspect the exact approved file scope and create the source commit itself before
the ordinary independent checks/review and delivery chains can proceed. Two
adversarial hosts deliberately violate that contract to exercise preservation.

GitHub scenarios reuse the existing isolated fake-gh/test-only receipt wrapper.
There is no live model, authenticated GitHub, external network, or production
capability claim. Imported fixture classes are never inherited, so their tests
are not rediscovered as controller-commit coverage.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import textwrap
import time
import unittest

import test_cli_e2e as local_fixture
import test_github_cli_e2e as github_fixture


# Keep the same business behavior, reports and separate Serena-aware reviewer.
# Only the implementation's commit responsibility changes in the positive host.
_HOST_COMMIT = '''    subprocess.run(["git", "add", "solution.py", "tests/test_business.py", "docs/reports"], check=True)
    subprocess.run(["git", "commit", "--quiet", "-m", "simulated-host implements " + task], check=True)
    Path(output).write_text("Simulated implementation committed; independent validation still required.\\n")'''
_HOST_EDIT = '''    Path(output).write_text("Simulated implementation edited and tested only; controller commit and independent validation still required.\\n")'''
assert local_fixture.HOST.count(_HOST_COMMIT) == 1, "upstream host fixture changed"
EDIT_ONLY_HOST = local_fixture.HOST.replace(_HOST_COMMIT, _HOST_EDIT)

# Prepended only for the separate native knowledge-promotion scenario. Candidate
# generation and semantic acceptance are deterministic SIMULATED host behavior;
# source-object reads and Serena CLI/API mutations/readback are native operations.
KNOWLEDGE_HOST_PREFIX = r'''
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from harness.knowledge import verify_durable_evidence

mode, task, output, prompt = sys.argv[1:]
sys.argv = sys.argv[:4]
root = Path.cwd().resolve()
task_data = json.JSONDecoder().raw_decode(prompt[prompt.index("{"):])[0]
native_env = dict(os.environ)
native_env.pop("PYTHONPATH", None)
native_env["SERENA_HOME"] = SETTINGS["serena_home"]

def record(event, **facts):
    with Path(SETTINGS["audit"]).open("a") as stream:
        stream.write(json.dumps(dict(event=event, task=task, mode=mode, root=str(root),
                                     pid=os.getpid(), simulation=True, **facts), sort_keys=True) + "\n")

def native(argv, data=None):
    result = subprocess.run(argv, cwd=root, env=native_env, input=data,
                            capture_output=True, text=True, timeout=15)
    record("native_operation", argv=argv, exit_code=result.returncode)
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout

def source_head():
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True,
                          capture_output=True, text=True).stdout.strip()

def read_memory(name):
    text = native([SETTINGS["serena"], "memories", "read", name, str(root)])
    actual = (root / ".serena/memories" / (name + ".md")).read_text()
    assert text.rstrip("\n") == actual.rstrip("\n")
    return actual

if task == "knowledge":
    context = task_data["context"][0]
    delivery = context["business_D"]
    if mode == "implement":
        assert source_head() == delivery, "knowledge must start from actual business D"
    proof = verify_durable_evidence(root, context["sources"], commit=delivery)
    assert {row["commit"] for row in proof} == {delivery}
    code = (root / "solution.py").read_text()
    tests = (root / "tests/test_business.py").read_text()
    walkthrough = (root / "docs/reports/base/walkthrough.md").read_text()
    assert "return a + b" in code
    assert "solution.add(2, 3), 5" in tests and "solution.add(-2, 3), 1" in tests
    assert "native-Serena" in walkthrough
    candidate = ("# Arithmetic implementation and test definitions\nAt delivered commit " + delivery
        + ", add(a, b) returns a + b. Committed tests define assertions for (2, 3) -> 5 and (-2, 3) -> 1.\n"
        + "These source files define behavior and test cases; they are not a durable test-execution record.\n"
        + "Sources at that immutable delivery: solution.py; tests/test_business.py; docs/reports/base/walkthrough.md.\n"
        + "Candidate and semantic review are deterministic SIMULATED fixture behavior, not a real model review.\n")
    link = "\nRead mem:topics/verified_arithmetic for committed implementation and test definitions.\n"
    unrelated_before = (root / ".serena/memories/unrelated.md").read_bytes()
    if mode == "implement":
        core = read_memory("core")
        assert hashlib.sha256(core.encode()).hexdigest() == context["core_before_sha256"]
        assert not (root / ".serena/memories/topics/verified_arithmetic.md").exists()
        record("candidate_supported_by_actual_D", business_D=delivery, source_proof=proof,
               candidate_sha256=hashlib.sha256(candidate.encode()).hexdigest())
        native([SETTINGS["serena"], "memories", "write", "topics/verified_arithmetic", str(root)], candidate)
        payload = {"name": "core", "content": core + link,
                   "expected_sha256": hashlib.sha256(core.encode()).hexdigest()}
        changed = json.loads(native([SETTINGS["serena_python"], SETTINGS["bridge"], "update", str(root)],
                                    json.dumps(payload)))
        assert changed["updated"] is True
        assert read_memory("core") == core + link
        assert read_memory("topics/verified_arithmetic") == candidate
        assert native([SETTINGS["serena"], "memories", "check", str(root)]).strip() == "✓ No referential integrity issues found."
        for kind, relative in task_data["reports"].items():
            report = root / relative
            report.parent.mkdir(parents=True, exist_ok=True)
            report.write_text("# Fixture " + kind + "\nScope: deterministic SIMULATED host / native-Git / native-Serena.\n"
                              + "Knowledge generated from actual business D " + delivery + ".\n"
                              + "Durable sources: solution.py; tests/test_business.py; docs/reports/base/walkthrough.md.\n")
        Path(output).write_text("Simulated implementation edited and tested only; controller commit and independent validation still required.\n")
        record("native_promotion_prepared", business_D=delivery, source_proof=proof)
    else:
        core = read_memory("core")
        assert core.endswith(link)
        assert hashlib.sha256(core[:-len(link)].encode()).hexdigest() == context["core_before_sha256"]
        assert read_memory("topics/verified_arithmetic") == candidate
        assert native([SETTINGS["serena"], "memories", "check", str(root)]).strip() == "✓ No referential integrity issues found."
        record("independent_simulated_knowledge_review", business_D=delivery, source_proof=proof,
               candidate_H=source_head(), candidate_sha256=hashlib.sha256(candidate.encode()).hexdigest())
        Path(output).write_text(json.dumps({"findings": [], "acceptance": [{
            "id": "AC-knowledge", "status": "passed",
            "evidence": "Separate deterministic SIMULATED review verified native core/topic readback against actual immutable business D "
                        + delivery + "; exact code/test/walkthrough source proof: " + json.dumps(proof)
        }]}))
    assert unrelated_before == (root / ".serena/memories/unrelated.md").read_bytes()
    raise SystemExit(0)

if task == "dependent" and mode == "implement":
    context = task_data["context"][0]
    assert source_head() == context["knowledge_D"], "new business worktree must inherit actual knowledge D"
    core = read_memory("core")
    assert hashlib.sha256(core.encode()).hexdigest() == context["core_sha256"]
    names = re.findall(r"mem:([A-Za-z0-9_/-]+)", core)
    assert names == ["topics/verified_arithmetic"]
    topic = read_memory(names[0])
    assert hashlib.sha256(topic.encode()).hexdigest() == context["topic_sha256"]
    assert context["business_D"] in topic
    assert native([SETTINGS["serena"], "memories", "check", str(root)]).strip() == "✓ No referential integrity issues found."
    record("read_prior_knowledge_before_business_edits", business_D=context["business_D"],
           knowledge_D=context["knowledge_D"], HEAD=source_head(),
           core_sha256=hashlib.sha256(core.encode()).hexdigest(),
           topic_sha256=hashlib.sha256(topic.encode()).hexdigest())
'''

AVAILABLE = local_fixture.SERENA and local_fixture.SERENA_PYTHON and local_fixture.GIT
REQUIREMENT = "Native E2E requires explicit pinned Serena executable/Python and Git"


class ControllerCommitAssertions:
    """Helpers only: no discovered or inherited test methods."""

    def enable_controller_commit(self, *, misbehavior=None):
        script = EDIT_ONLY_HOST
        if misbehavior == "host_commit":
            # This is an intentionally adversarial host, not the positive host.
            script = script.replace(_HOST_EDIT, _HOST_COMMIT)
        elif misbehavior == "outside_scope":
            script = script.replace(_HOST_EDIT,
                                    '    (root / "README.md").write_text("Host modified prohibited baseline file\\n")\n'
                                    + _HOST_EDIT)
        self.host.write_text(textwrap.dedent(script))
        if misbehavior is None:
            self.assertNotIn('subprocess.run(["git"', script)
        self.bundle["config"]["host"]["commit_mode"] = "controller_commit"
        self.controller_commit_observations = []
        if hasattr(self, "metrics"):
            self.metrics["commit_mode"] = "controller_commit"
            self.metrics["host_fixture_sha256"] = hashlib.sha256(self.host.read_bytes()).hexdigest()

    @staticmethod
    def allow_exact_files(task):
        task["allowed_paths"] = ["solution.py", "tests/test_business.py", *task["reports"].values()]
        return task

    def implementation_worktree(self, name):
        paths = list((self.repo / ".git/harness-worktrees").glob(name + "-implementation-*"))
        self.assertEqual(1, len(paths), paths)
        return paths[0]

    def assert_controller_capability(self):
        receipt = json.loads((self.repo / ".git/harness.capabilities.json").read_text())
        self.assertEqual("simulation_only", receipt["status"])
        capabilities = receipt["observations"]["capabilities"]
        self.assertEqual("verified", capabilities["controller_commit"]["status"])
        self.assertIn("host_session_start", receipt["unverified"])
        probe = receipt["observations"]["controller_commit_probe"]
        self.assertEqual("verified", probe["status"])
        self.assertEqual(0, probe["model_calls"])
        self.assertFalse(probe["proves_model_controller_split"])
        self.assertTrue(probe["observation"]["cas_rejection_observed"])
        self.assertTrue(probe["observation"]["cas_update_observed"])
        self.assertTrue(probe["observation"]["ref_cleanup_observed"])

    def controlled_source_commands(self, name, operation):
        path = str(self.implementation_worktree(name))
        matches = []
        for row in self.state()["attempts"]:
            argv = row.get("argv", [])
            if argv[:3] != ["git", "-C", path]:
                continue
            arguments = argv[3:]
            while arguments[:1] == ["-c"]:
                self.assertGreaterEqual(len(arguments), 3, "incomplete native Git configuration pair")
                arguments = arguments[2:]
            if arguments[:1] == [operation]:
                matches.append(row)
        return matches

    def assert_controller_commit(self, task, evidence):
        name = task["id"]
        source = self.implementation_worktree(name)
        head = self.git("rev-parse", task["source"])
        self.assertEqual(head, evidence["H"])
        self.assertEqual(head, self.git("rev-parse", "HEAD", cwd=source))
        self.assertEqual(evidence["T"], self.git("rev-parse", head + "^"))
        self.assertEqual("", self.git("status", "--porcelain", cwd=source))
        changed = set(self.git("diff", "--name-only", head + "^", head).splitlines())
        self.assertEqual(set(task["allowed_paths"]), changed)
        self.assertFalse(self.controlled_source_commands(name, "add"))
        self.assertFalse(self.controlled_source_commands(name, "commit"))
        commits = self.controlled_source_commands(name, "commit-tree")
        self.assertEqual(1, len(commits), "source commit must be owned and journaled by the controller")
        self.assertEqual(0, commits[0]["exit_code"])
        self.assertTrue(commits[0]["stopped"])
        self.assertIsNone(commits[0]["reason"])
        updates = self.controlled_source_commands(name, "update-ref")
        self.assertEqual(1, len(updates), "source reference update must be owned and journaled by the controller")
        self.assertIn(head, updates[0]["argv"])
        self.assertIn(evidence["T"], updates[0]["argv"])
        self.assertIn("refs/heads/" + task["source"], updates[0]["argv"])
        self.assertEqual(["refs/heads/" + task["source"], head, evidence["T"]], updates[0]["argv"][-3:])
        operations = [json.loads(p.read_text()) for p in
                      (self.repo / ".git/harness-controller-commits").glob("*/operation.json")]
        operations = [row for row in operations if row["snapshot"]["worktree"] == str(source)]
        self.assertEqual(1, len(operations))
        operation = operations[0]
        self.assertEqual("controller", operation["actor"])
        self.assertEqual("completed", operation["phase"])
        self.assertEqual(head, operation["commit"])
        self.assertEqual(evidence["T"], operation["parent"])
        self.assertEqual("refs/heads/" + task["source"], operation["source_ref"])
        self.assertEqual(self.git("rev-parse", head + "^{tree}"), operation["tree"])
        self.assertEqual(changed, set(operation["changed_paths"]))
        self.assertEqual(changed, set(operation["snapshot"]["allowed_paths"]))
        for relative in task["reports"].values():
            self.assertIn("native-Serena", self.git("show", head + ":" + relative))
        for check in evidence["checks"]:
            self.assertEqual("passed", check["status"])
            self.assertGreaterEqual(check["tests"], 1)
            self.assertEqual(0, check["failed"])
        self.assertEqual([], evidence["review"]["findings"])
        self.assertEqual("passed", evidence["review"]["acceptance"][0]["status"])
        self.assertTrue(evidence["knowledge"]["structural_ready"])
        self.assertEqual("simulation", evidence["verification_tier"])
        saved = self.state()["tasks"][name]
        result = json.loads(Path(saved["evidence"]).with_name("result.json").read_text())
        self.assertEqual(head, result["review"]["binding"]["H"])
        self.assertEqual(evidence["C"], result["review"]["binding"]["C"])
        self.assertTrue(result["review"]["independent"])
        for check in result["checks"]:
            self.assertEqual(result["review"]["binding"], check["binding"])
        outputs = list((self.repo / ".git/harness-runs/e2e-run" / name).glob("*-implementation/host-result.txt"))
        self.assertEqual(1, len(outputs))
        self.assertIn("edited and tested only", outputs[0].read_text())
        prompts = list((self.repo / ".git/harness-runs/e2e-run" / name).glob("*-implementation/prompt.txt"))
        self.assertEqual(1, len(prompts))
        self.assertIn("controller", prompts[0].read_text().lower())
        self.controller_commit_observations.append({
            "task_id": name, "H": head, "T": evidence["T"], "C": evidence["C"],
            "changed_paths": sorted(changed), "controlled_commit_attempt": commits[0]["attempt_id"],
            "independent_review_attempt": evidence["review"]["record"]["attempt_id"],
            "verification_tier": evidence["verification_tier"],
        })

    def preserve_controller_evidence(self):
        directory = os.environ.get("HARNESS_E2E_EVIDENCE_DIR")
        if not directory:
            return
        destination = Path(directory) / self._testMethodName
        destination.mkdir(parents=True, exist_ok=True)
        (destination / "controller-commit-observations.json").write_text(
            json.dumps(self.controller_commit_observations, indent=2, sort_keys=True))
        (destination / "fixture-scope.txt").write_text(__doc__)
        shutil.copyfile(self.host, destination / "simulated-host.py")
        for name in ("knowledge-host-audit.jsonl", "knowledge-chain-proof.json"):
            if (self.base / name).is_file():
                shutil.copyfile(self.base / name, destination / name)
        for source in (self.repo / ".loop-state.json", self.repo / ".git/harness.capabilities.json"):
            if source.is_file():
                shutil.copyfile(source, destination / source.name)
        state = self.state() if (self.repo / ".loop-state.json").is_file() else {}
        receipt_path = self.repo / ".git/harness.capabilities.json"
        receipt = json.loads(receipt_path.read_text()) if receipt_path.is_file() else {}
        originals = set(receipt.get("raw_logs", {}))
        for attempt in state.get("attempts", []):
            originals.update(attempt[key] for key in ("log", "stderr_log") if attempt.get(key))
        raw_directory = destination / "raw-execution-logs"
        raw_directory.mkdir(exist_ok=True)
        index = {}
        for number, original in enumerate(sorted(originals)):
            source = Path(original)
            if source.is_file():
                copied = raw_directory / (str(number) + "-" + source.name)
                shutil.copyfile(source, copied)
                index[original] = {"copied_path": str(copied.relative_to(destination)),
                                   "sha256": hashlib.sha256(copied.read_bytes()).hexdigest()}
        (destination / "execution-log-index.json").write_text(json.dumps(index, indent=2, sort_keys=True))
        metrics = {"scenario": self._testMethodName, "commit_mode": "controller_commit",
                   "tier": "SIMULATED-host-platform-network/native-Git/native-Serena",
                   "comparison_scope": "new optional mode correctness only; no speed/cost advantage claim",
                   "elapsed_seconds": round(time.monotonic() - self.started, 3),
                   "controlled_commands": len(state.get("attempts", [])),
                   "controlled_spent_seconds": state.get("spent_seconds"),
                   "final_task_statuses": {key: value.get("status") for key, value in state.get("tasks", {}).items()},
                   "capability_receipt_status": receipt.get("status"),
                   "controller_commits_proven": len([row for row in self.controller_commit_observations if "H" in row]),
                   "preservation_negatives_proven": len([row for row in self.controller_commit_observations if "negative" in row]),
                   "archived_raw_logs": len(index), "model_calls": 0, "live_network_calls": 0}
        (destination / "controller-mode-metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True))
        runs = self.repo / ".git/harness-runs/e2e-run"
        if runs.exists():
            shutil.copytree(runs, destination / "controller-runs", dirs_exist_ok=True)
        operations = self.repo / ".git/harness-controller-commits"
        if operations.exists():
            shutil.copytree(operations, destination / "controller-commit-operations", dirs_exist_ok=True)


@unittest.skipUnless(AVAILABLE, REQUIREMENT)
class ControllerCommitLocalE2E(ControllerCommitAssertions, unittest.TestCase):
    git = local_fixture.CliE2E.git
    state = local_fixture.CliE2E.state
    deliver_and_close = local_fixture.CliE2E.deliver_and_close

    def setUp(self):
        self.started = time.monotonic()
        local_fixture.CliE2E.setUp(self)
        self.enable_controller_commit()

    def tearDown(self):
        self.preserve_controller_evidence()

    def task(self, name, dependencies=()):
        return self.allow_exact_files(local_fixture.CliE2E.task(self, name, dependencies))

    def save_bundle(self, tasks):
        local_fixture.CliE2E.save_bundle(self, tasks)
        self.assert_controller_capability()

    def cli(self, command, *args, okay=True):
        if not hasattr(self, "native_host_budget"):
            return local_fixture.CliE2E.cli(self, command, *args, okay=okay)
        argv = [sys.executable, "-m", "harness.cli", command, "--bundle", str(self.bundle_path)]
        if command not in ("preflight", "evidence"):
            argv.extend(["--run", "e2e-run"])
        result = subprocess.run(argv + list(args), env=self.env, capture_output=True, text=True,
                                timeout=2 * self.native_host_budget + 90)
        if okay:
            self.assertEqual(0, result.returncode, result.stdout + "\n" + result.stderr)
            return json.loads(result.stdout)
        self.assertNotEqual(0, result.returncode, result.stdout + "\n" + result.stderr)
        return result

    def run_and_verify(self, task, attempt):
        result = self.cli("run", "--attempt", attempt, "--implement")
        self.assertEqual("handoff", result["status"])
        saved = self.state()["tasks"][task["id"]]
        self.assertEqual("verified", saved["status"])
        evidence = json.loads(Path(saved["evidence"]).read_text())
        self.assert_controller_commit(task, evidence)
        self.assertNotIn("D", saved)
        return evidence

    def test_controller_commit_local_tiny_full_cli_chain(self):
        task = self.task("tiny")
        self.save_bundle([task])
        self.assertTrue(self.cli("preflight")["ok"])
        target = self.git("rev-parse", "main")
        evidence = self.run_and_verify(task, "controller-tiny")
        self.assertEqual(target, self.git("rev-parse", "main"))
        denied = self.cli("deliver", "--task", "tiny", "--target-worktree", str(self.repo), "--simulation", okay=False)
        self.assertIn("authorization", denied.stderr)
        denied = self.cli("deliver", "--task", "tiny", "--target-worktree", str(self.repo), "--authorize", okay=False)
        self.assertIn("simulation receipt cannot authorize real delivery", denied.stderr)
        self.assertEqual(target, self.git("rev-parse", "main"))
        self.deliver_and_close("tiny")
        self.assertEqual(evidence["C"], self.state()["tasks"]["tiny"]["D"])
        self.assertEqual("completed", self.cli("run", "--attempt", "controller-tiny-finished")["status"])
        self.assertEqual("", self.git("remote"))

    def test_controller_commit_local_exception_full_cli_chain(self):
        task = self.task("exception")
        self.save_bundle([task])
        evidence = self.run_and_verify(task, "controller-exception")
        self.assertIn("raise ValueError('zero divisor')", self.git("show", evidence["H"] + ":solution.py"))
        self.deliver_and_close("exception")
        self.assertEqual("completed", self.cli("run", "--attempt", "controller-exception-finished")["status"])

    def test_controller_commit_local_dependency_delivery_reconcile(self):
        first, second = self.task("base"), self.task("dependent", ["base"])
        self.save_bundle([first, second])
        self.run_and_verify(first, "controller-first")
        held = self.cli("run", "--attempt", "controller-dependency-held", "--implement")
        self.assertEqual("base", held["tasks"][0]["task_id"])
        self.assertEqual("", self.git("branch", "--list", second["source"]))
        self.deliver_and_close("base")
        evidence = self.run_and_verify(second, "controller-second")
        self.assertEqual(self.state()["tasks"]["base"]["D"], evidence["T"])
        checkpoint = (self.repo / ".loop-state.json").read_bytes()
        self.git("merge", "--ff-only", evidence["C"])
        self.assertEqual(checkpoint, (self.repo / ".loop-state.json").read_bytes())
        observed = self.cli("reconcile", "--task", "dependent")
        self.assertEqual("delivered", observed["status"])
        self.assertEqual(evidence["C"], observed["D"])
        self.assertEqual("completed", self.cli("closeout", "--task", "dependent")["status"])
        self.assertEqual("completed", self.cli("run", "--attempt", "controller-chain-finished")["status"])

    def assert_blocked_work_is_retained(self, task, target):
        name = task["id"]
        source = self.implementation_worktree(name)
        self.assertEqual(target, self.git("rev-parse", "main"))
        self.assertIn("def add", (source / "solution.py").read_text())
        for relative in task["reports"].values():
            self.assertTrue((source / relative).is_file())
        self.assertFalse(self.controlled_source_commands(name, "commit"))
        self.assertFalse(self.controlled_source_commands(name, "commit-tree"))
        self.assertFalse(self.controlled_source_commands(name, "update-ref"))
        self.assertFalse(self.controlled_source_commands(name, "add"))
        saved = self.state()["tasks"].get(name, {})
        self.assertNotIn("D", saved)
        self.assertNotIn(saved.get("status"), ("verified", "delivered", "completed"))
        review_calls = [row for row in self.state()["attempts"]
                        if str(self.host) in row.get("argv", []) and "review" in row["argv"]]
        self.assertFalse(review_calls)
        runs = self.repo / ".git/harness-runs/e2e-run" / name
        self.assertTrue(list(runs.glob("*-implementation/host.log")))
        return source

    def test_controller_commit_blocks_host_commit_and_retains_commit(self):
        self.enable_controller_commit(misbehavior="host_commit")
        task = self.task("hostcommit")
        self.save_bundle([task])
        target = self.git("rev-parse", "main")
        refused = self.cli("run", "--attempt", "controller-refuse-host-commit", "--implement", okay=False)
        self.assertRegex(refused.stderr.lower(), "head|commit|source")
        source = self.assert_blocked_work_is_retained(task, target)
        head = self.git("rev-parse", "HEAD", cwd=source)
        self.assertNotEqual(target, head)
        self.assertIn("simulated-host implements", self.git("log", "-1", "--format=%s", cwd=source))
        self.assertEqual("", self.git("status", "--porcelain", cwd=source))
        self.controller_commit_observations.append({"negative": "host_commit", "preserved_H": head,
                                                    "target_unchanged": target, "blocked": refused.stderr})

    def test_controller_commit_blocks_prohibited_file_and_retains_dirty_data(self):
        self.enable_controller_commit(misbehavior="outside_scope")
        task = self.task("outside")
        self.save_bundle([task])
        target = self.git("rev-parse", "main")
        refused = self.cli("run", "--attempt", "controller-refuse-outside", "--implement", okay=False)
        self.assertRegex(refused.stderr.lower(), "allow|scope|prohibit|readme")
        source = self.assert_blocked_work_is_retained(task, target)
        self.assertEqual(target, self.git("rev-parse", "HEAD", cwd=source))
        self.assertEqual("Host modified prohibited baseline file\n", (source / "README.md").read_text())
        self.assertIn("README.md", self.git("status", "--porcelain", cwd=source))
        self.assertEqual("", self.git("diff", "--cached", "--name-only", cwd=source))
        self.controller_commit_observations.append({"negative": "outside_scope", "target_unchanged": target,
                                                    "dirty_data_preserved": True, "blocked": refused.stderr})

    def test_controller_commit_local_native_knowledge_promotion_chain(self):
        """Business D -> distinct native knowledge D -> new business consumer."""
        # Seven native CLI/API operations at 15 s each, plus 15 s fixture logic.
        # This aggregate is for deterministic native-heavy fixtures only.
        self.native_host_budget = 7 * 15 + 15
        self.bundle["config"]["limits"].update(implementation_seconds=self.native_host_budget,
                                                  review_seconds=self.native_host_budget)
        self.env["SERENA_HOME"] = str(self.home)
        (self.repo / "docs/knowledge-spec.md").write_text(
            "# Knowledge promotion\nAfter actual business delivery D, derive arithmetic knowledge only from committed code, "
            "tests and walkthrough at D. Native-write one topic and append one reviewed core link. Preserve unrelated "
            "memories and existing core bytes. Independently review exact source support; deterministic fixture review "
            "is explicitly SIMULATED. The next business task must dynamically native-read the delivered topic.\n")
        adapter = local_fixture.SerenaAdapter(self.repo, local_fixture.SERENA, self.home,
                                              python_executable=local_fixture.SERENA_PYTHON)
        adapter.write_new_memory("unrelated", "# Unrelated fixture knowledge\nPreserve these exact bytes.\n",
                                 ["README.md", "docs/spec.md"])
        self.git("add", "docs/knowledge-spec.md", ".serena/memories/unrelated.md")
        self.git("commit", "--quiet", "-m", "native knowledge promotion fixture baseline")
        original_core = (self.repo / ".serena/memories/core.md").read_bytes()
        original_unrelated = (self.repo / ".serena/memories/unrelated.md").read_bytes()
        original_maintenance = (self.repo / ".serena/memories/memory_maintenance.md").read_bytes()
        settings = {"serena": local_fixture.SERENA, "serena_python": local_fixture.SERENA_PYTHON,
                    "serena_home": str(self.home), "bridge": str(local_fixture.PACKAGE / "harness/serena_bridge.py"),
                    "audit": str(self.base / "knowledge-host-audit.jsonl")}
        self.host.write_text("SETTINGS = " + repr(settings) + "\n" + textwrap.dedent(KNOWLEDGE_HOST_PREFIX)
                             + "\n" + textwrap.dedent(EDIT_ONLY_HOST))
        for phase, key in (("implement", "implementation_argv"), ("review", "review_argv")):
            self.bundle["config"]["host"][key] = [sys.executable, str(self.host), phase,
                                                   "{task_id}", "{output}", "{prompt}"]
        first = self.task("base")
        self.save_bundle([first])
        self.run_and_verify(first, "knowledge-business-base")
        self.deliver_and_close("base")
        business_D = self.state()["tasks"]["base"]["D"]
        sources = ["solution.py", "tests/test_business.py", "docs/reports/base/walkthrough.md"]
        for source in sources:
            self.assertTrue(self.git("show", business_D + ":" + source))
        knowledge = self.task("knowledge", ["base"])
        knowledge["spec"] = "docs/knowledge-spec.md"
        knowledge["durable_evidence"] = sources + ["docs/knowledge-spec.md"]
        knowledge["allowed_paths"] = [".serena/memories/core.md", ".serena/memories/topics/verified_arithmetic.md",
                                       *knowledge["reports"].values()]
        knowledge["context"] = [{"business_D": business_D, "sources": sources,
                                  "core_before_sha256": hashlib.sha256(original_core).hexdigest()}]
        # Approval records the actual preceding delivery, never a future guess.
        self.save_bundle([first, knowledge])
        promoted = self.run_and_verify(knowledge, "knowledge-native-promotion")
        self.assertEqual(business_D, promoted["T"])
        self.assertEqual(original_core, (self.repo / ".serena/memories/core.md").read_bytes())
        self.assertFalse((self.repo / ".serena/memories/topics/verified_arithmetic.md").exists())
        self.deliver_and_close("knowledge")
        knowledge_D = self.state()["tasks"]["knowledge"]["D"]
        link = b"\nRead mem:topics/verified_arithmetic for committed implementation and test definitions.\n"
        core = (self.repo / ".serena/memories/core.md").read_bytes()
        topic = (self.repo / ".serena/memories/topics/verified_arithmetic.md").read_bytes()
        self.assertEqual(original_core + link, core)
        self.assertIn(business_D.encode(), topic)
        self.assertEqual(original_unrelated, (self.repo / ".serena/memories/unrelated.md").read_bytes())
        self.assertEqual(original_maintenance, (self.repo / ".serena/memories/memory_maintenance.md").read_bytes())
        dependent = self.task("dependent", ["knowledge"])
        dependent["durable_evidence"] += [".serena/memories/core.md", ".serena/memories/topics/verified_arithmetic.md"]
        dependent["context"] = [{"business_D": business_D, "knowledge_D": knowledge_D,
                                  "core_sha256": hashlib.sha256(core).hexdigest(),
                                  "topic_sha256": hashlib.sha256(topic).hexdigest()}]
        self.save_bundle([first, knowledge, dependent])
        consumed = self.run_and_verify(dependent, "knowledge-business-consumer")
        self.assertEqual(knowledge_D, consumed["T"])
        self.deliver_and_close("dependent")
        self.assertEqual("completed", self.cli("run", "--attempt", "knowledge-chain-completed")["status"])
        observations = [json.loads(line) for line in (self.base / "knowledge-host-audit.jsonl").read_text().splitlines()]
        promoted_rows = [row for row in observations if row["event"] == "native_promotion_prepared"]
        review_rows = [row for row in observations if row["event"] == "independent_simulated_knowledge_review"]
        consumed_rows = [row for row in observations if row["event"] == "read_prior_knowledge_before_business_edits"]
        self.assertEqual([1, 1, 1], [len(promoted_rows), len(review_rows), len(consumed_rows)])
        self.assertNotEqual(promoted_rows[0]["pid"], review_rows[0]["pid"])
        self.assertNotEqual(promoted_rows[0]["root"], review_rows[0]["root"])
        self.assertNotEqual(promoted_rows[0]["root"], consumed_rows[0]["root"])
        self.assertEqual(knowledge_D, consumed_rows[0]["HEAD"])
        for row in promoted_rows + review_rows:
            self.assertEqual(set(sources), {item["reference"] for item in row["source_proof"]})
            self.assertEqual({business_D}, {item["commit"] for item in row["source_proof"]})
        writes = [row for row in observations if row["event"] == "native_operation" and "write" in row["argv"]]
        updates = [row for row in observations if row["event"] == "native_operation" and "update" in row["argv"]]
        self.assertEqual(1, len(writes))
        self.assertEqual(1, len(updates))
        self.assertEqual(local_fixture.SERENA, writes[0]["argv"][0])
        self.assertEqual(local_fixture.SERENA_PYTHON, updates[0]["argv"][0])
        self.assertTrue(all(row["exit_code"] == 0 for row in observations if row["event"] == "native_operation"))
        self.assertEqual(core, (self.repo / ".serena/memories/core.md").read_bytes())
        self.assertEqual(topic, (self.repo / ".serena/memories/topics/verified_arithmetic.md").read_bytes())
        self.assertEqual(original_unrelated, (self.repo / ".serena/memories/unrelated.md").read_bytes())
        self.assertEqual(original_maintenance, (self.repo / ".serena/memories/memory_maintenance.md").read_bytes())
        proof = {"tier": "SIMULATED candidate/semantic review; native Git and Serena promotion/readback",
                 "business_D": business_D, "knowledge_D": knowledge_D,
                 "consumer_D": self.state()["tasks"]["dependent"]["D"],
                 "source_references": sources, "core_sha256": hashlib.sha256(core).hexdigest(),
                 "topic_sha256": hashlib.sha256(topic).hexdigest(), "unrelated_memories_preserved": True,
                 "native_host_budget_seconds": self.native_host_budget,
                 "consumer_native_readback": consumed_rows[0]}
        (self.base / "knowledge-chain-proof.json").write_text(json.dumps(proof, indent=2, sort_keys=True))


@unittest.skipUnless(AVAILABLE, REQUIREMENT)
class ControllerCommitGitHubE2E(ControllerCommitAssertions, unittest.TestCase):
    # Explicit helper reuse avoids running GitHubCliE2E's own test methods twice.
    git = local_fixture.CliE2E.git
    state = local_fixture.CliE2E.state
    cli = github_fixture.GitHubCliE2E.cli
    github = github_fixture.GitHubCliE2E.github
    platform = github_fixture.GitHubCliE2E.platform
    update_platform = github_fixture.GitHubCliE2E.update_platform
    audit_rows = github_fixture.GitHubCliE2E.audit_rows
    run_local_validation = github_fixture.GitHubCliE2E.run_local_validation
    ready_pr = github_fixture.GitHubCliE2E.ready_pr
    finish = github_fixture.GitHubCliE2E.finish

    def setUp(self):
        github_fixture.GitHubCliE2E.setUp(self)
        # A native local clone normally hardlinks objects. Recreate this owned
        # empty fixture remote with independent objects to meet the restricted
        # mode's no-external-hardlinks policy, before any P0 receipt is issued.
        remote_head = self.git("--git-dir=" + str(self.remote), "rev-parse", "refs/heads/main")
        shutil.rmtree(self.remote)
        subprocess.run([local_fixture.GIT, "clone", "--quiet", "--bare", "--no-hardlinks",
                        str(self.repo), str(self.remote)],
                       check=True, env=self.env, capture_output=True)
        self.assertEqual(remote_head, self.git("--git-dir=" + str(self.remote), "rev-parse", "refs/heads/main"))
        self.assertTrue(all(path.stat().st_nlink == 1 for path in (self.repo / ".git/objects").glob("??/*")
                            if path.is_file()))
        # The optional restricted policy refuses repositories with executable
        # hooks rather than bypassing them. The original model-commit suite
        # separately proves native pre-push hooks survive controlled transport.
        (self.repo / ".git/hooks/pre-push").unlink()
        self.enable_controller_commit()

    def tearDown(self):
        self.preserve_controller_evidence()
        github_fixture.GitHubCliE2E.tearDown(self)

    def task(self, name, dependencies=(), issue=1):
        return self.allow_exact_files(github_fixture.GitHubCliE2E.task(self, name, dependencies, issue))

    def save_bundle(self, tasks):
        github_fixture.GitHubCliE2E.save_bundle(self, tasks)
        self.assert_controller_capability()

    def run_and_verify(self, task, attempt):
        evidence = self.run_local_validation(task["id"], attempt)
        self.assert_controller_commit(task, evidence)
        return evidence

    def publish_and_verify(self, name):
        """Original transport/PR/CI assertions without an incompatible hook."""
        before_target = self.git("rev-parse", "refs/remotes/origin/main")
        before = len(self.audit_rows("git-transport"))
        denied = self.github("push-source", task_id=name, remote="origin", okay=False)
        self.assertIn("authorization", denied.stderr)
        self.assertEqual(before, len(self.audit_rows("git-transport")))
        pushed = self.github("push-source", task_id=name, remote="origin", authorized=True)
        self.assertEqual("source_published", pushed["status"])
        source = self.git("rev-parse", "feature-" + name)
        self.assertEqual(source, pushed["source_sha"])
        self.assertEqual(source, self.git("--git-dir=" + str(self.remote), "rev-parse", "refs/heads/feature-" + name))
        self.assertEqual(before_target, self.git("--git-dir=" + str(self.remote), "rev-parse", "refs/heads/main"))
        self.assertFalse((self.repo / ".git/hooks/pre-push").exists())
        self.assertFalse((self.base / "native-pre-push.log").exists())
        self.assertTrue(self.github("push-source", task_id=name, remote="origin", authorized=True)["reused"])
        pr = self.github("create-pr", task_id=name, title="SIMULATED " + name,
                         body="Isolated controller-commit CLI fixture; not actual GitHub delivery.", authorized=True)
        number = pr["number"]
        self.assertEqual(source, pr["head"]["sha"])
        self.assertTrue(pr["draft"])
        again = self.github("create-pr", task_id=name, title="SIMULATED " + name, body="same", authorized=True)
        self.assertEqual(number, again["number"])
        checks = json.loads(self.github("checks", number=number, expected_sha=pr["merge_commit_sha"], okay=False).stdout)
        self.assertEqual("blocked", checks["status"])
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

    def test_controller_commit_github_tiny_full_cli_chain(self):
        task = self.task("tiny")
        self.save_bundle([task])
        self.assertTrue(self.cli("preflight")["ok"])
        evidence = self.run_and_verify(task, "controller-github-tiny")
        pr = self.publish_and_verify("tiny")
        self.assertEqual(evidence["H"], pr["head"]["sha"])
        self.finish("tiny", pr["number"])
        self.assertEqual("completed", self.cli("run", "--attempt", "controller-github-tiny-finished")["status"])
        self.assertEqual(1, len(self.audit_rows("native-business-test")))
        self.assertEqual(1, len(self.audit_rows("merge")))

    def test_controller_commit_github_exception_full_cli_chain(self):
        task = self.task("exception")
        self.save_bundle([task])
        evidence = self.run_and_verify(task, "controller-github-exception")
        self.assertIn("raise ValueError('zero divisor')", self.git("show", evidence["H"] + ":solution.py"))
        pr = self.publish_and_verify("exception")
        self.finish("exception", pr["number"])
        self.assertEqual("completed", self.cli("run", "--attempt", "controller-github-exception-finished")["status"])

    def test_controller_commit_github_dependencies_full_cli_chain(self):
        first = self.task("base", issue=1)
        second = self.task("dependent", ["base"], issue=2)
        self.save_bundle([first, second])
        self.run_and_verify(first, "controller-github-base")
        pr = self.publish_and_verify("base")
        held = self.cli("run", "--attempt", "controller-github-held", "--implement")
        self.assertEqual("base", held["tasks"][0]["task_id"])
        self.assertEqual("", self.git("branch", "--list", second["source"]))
        self.finish("base", pr["number"])
        evidence = self.run_and_verify(second, "controller-github-dependent")
        self.assertEqual(self.state()["tasks"]["base"]["D"], evidence["T"])
        self.assertIn("def double_sum", self.git("show", evidence["H"] + ":solution.py"))
        pr = self.publish_and_verify("dependent")
        self.finish("dependent", pr["number"])
        self.assertEqual("completed", self.cli("run", "--attempt", "controller-github-chain-finished")["status"])
        self.assertEqual(2, len(self.audit_rows("native-business-test")))
        self.assertEqual(2, len(self.audit_rows("merge")))


if __name__ == "__main__":
    unittest.main()
