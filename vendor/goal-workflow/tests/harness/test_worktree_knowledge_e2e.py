"""Simulation-only regression for native Serena registration of real Git worktrees.

Uses pinned Serena 1.7.0 CLI/API and real Git/controller processes. Hosts are
separate deterministic Python processes, never models; no network or credentials.
The original CliE2E fixture and all production files are left untouched.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import textwrap
import time
import unittest

_FIXTURE_PATH = Path(__file__).with_name("test_cli_e2e.py")
_SPEC = importlib.util.spec_from_file_location("worktree_cli_fixture", _FIXTURE_PATH)
_FIXTURE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_FIXTURE)
from harness.knowledge import SerenaAdapter

SERENA, SERENA_PYTHON, GIT = _FIXTURE.SERENA, _FIXTURE.SERENA_PYTHON, _FIXTURE.GIT

# Every memory consumed by either host is read through the actual pinned CLI.
# Expected bytes and invocation receipts are external fixture evidence, not a
# second knowledge store. The original business assertions remain independent.
NATIVE_HOST_PREFIX = r'''
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

mode, task, output, serena, serena_python, audit, expected_path = sys.argv[1:]
root = Path.cwd().resolve()
expected = json.loads(Path(expected_path).read_text())
assert os.environ.get("SERENA_HOME") == expected["serena_home"]
env = dict(os.environ)
env.pop("PYTHONPATH", None)
def native(*args):
    started = time.monotonic()
    result = subprocess.run([serena, *args], cwd=root, env=env, capture_output=True, text=True, timeout=15)
    with Path(audit).open("a") as stream:
        stream.write(json.dumps({"phase": "native_command", "mode": mode, "argv": list(args),
            "elapsed_seconds": time.monotonic() - started, "exit_code": result.returncode}) + "\n")
    assert result.returncode == 0, result.stderr
    return result.stdout

with Path(audit).open("a") as stream:
    stream.write(json.dumps({"phase": "started", "mode": mode, "root": str(root), "pid": os.getpid()}) + "\n")
version = native("--version").strip()
assert version.startswith("Serena 1.7.0"), version
registry = subprocess.run([serena_python, "-c",
    "import json; from serena.config.serena_config import SerenaConfig; "
    "print(json.dumps(SerenaConfig.from_config_file().project_paths))"],
    cwd=root, env=env, capture_output=True, text=True, timeout=15)
assert registry.returncode == 0, registry.stderr
registered_paths = json.loads(registry.stdout)
assert str(root) in registered_paths, registered_paths
contents = {}
def read_memory(name, follow=True):
    if name in contents:
        return
    contents[name] = native("memories", "read", name, str(root)).rstrip("\n")
    assert hashlib.sha256(contents[name].encode()).hexdigest() == expected["memories"][name], name
    if follow:
        for reference in re.findall(r"mem:([A-Za-z0-9_/-]+)", contents[name]):
            read_memory(reference)
# Native maintenance includes illustrative references, not project graph edges.
read_memory("memory_maintenance", follow=False)
read_memory("core")
assert set(contents) == set(expected["memories"]), sorted(contents)
assert native("memories", "check", str(root)).strip() == "✓ No referential integrity issues found."
with Path(audit).open("a") as stream:
    stream.write(json.dumps({"phase": "native_reads_passed", "mode": mode, "root": str(root),
        "pid": os.getpid(), "version": version, "registered_paths": registered_paths,
        "memories": {name: hashlib.sha256(content.encode()).hexdigest() for name, content in contents.items()},
        "verification_tier": "simulation"}) + "\n")
sys.argv = sys.argv[:4]
'''


@unittest.skipUnless(SERENA and SERENA_PYTHON and GIT,
                     "Native worktree E2E requires explicit pinned Serena executable/Python and Git")
class WorktreeKnowledgeE2E(unittest.TestCase):
    # Reuse setup/helpers only; do not inherit or rerun the original test cases.
    git = _FIXTURE.CliE2E.git
    task = _FIXTURE.CliE2E.task
    save_bundle = _FIXTURE.CliE2E.save_bundle
    state = _FIXTURE.CliE2E.state

    def cli(self, command, *args, okay=True):
        started = time.monotonic()
        try:
            argv = [sys.executable, "-m", "harness.cli", command, "--bundle", str(self.bundle_path)]
            if command not in ("preflight", "evidence"):
                argv.extend(["--run", "e2e-run"])
            # Two native-heavy fake-host stages plus bounded Controller setup.
            result = subprocess.run(argv + list(args), env=self.env, capture_output=True,
                                    text=True, timeout=2 * self.native_host_budget + 60)
            if okay:
                self.assertEqual(0, result.returncode, result.stdout + "\n" + result.stderr)
                return json.loads(result.stdout)
            self.assertNotEqual(0, result.returncode, result.stdout + "\n" + result.stderr)
            return result
        except (AssertionError, subprocess.TimeoutExpired) as exc:
            # Keep diagnostic bytes in test output before TemporaryDirectory
            # cleanup. This fixture contains no model/provider credentials.
            details = {"command": command, "args": args, "elapsed_seconds": time.monotonic() - started,
                       "limits": self.bundle["config"]["limits"], "attempts": [], "host_reads": self.observations()}
            checkpoint = self.repo / ".loop-state.json"
            if checkpoint.exists():
                for row in json.loads(checkpoint.read_text()).get("attempts", []):
                    if str(self.host) in row.get("argv", []):
                        item = dict(row)
                        for field in ("log", "stderr_log"):
                            if row.get(field) and Path(row[field]).is_file():
                                item[field + "_content"] = Path(row[field]).read_text(errors="replace")
                        details["attempts"].append(item)
            rendered = json.dumps(details, ensure_ascii=False, indent=2)
            print("NATIVE_WORKTREE_FAILURE_DIAGNOSTICS=" + rendered, flush=True)
            raise AssertionError(str(exc) + "\n" + rendered) from exc

    def setUp(self):
        _FIXTURE.CliE2E.setUp(self)
        # Six native CLI reads/checks plus one native registry Python process,
        # each capped at 15 s, and 15 s for deterministic fixture assertions.
        # This is a fake-host fixture budget, never a real-model setting.
        self.native_host_budget = 7 * 15 + 15
        self.bundle["config"]["limits"].update(implementation_seconds=self.native_host_budget,
                                                  review_seconds=self.native_host_budget)
        self.env["SERENA_HOME"] = str(self.home)
        self.adapter = SerenaAdapter(self.repo, SERENA, self.home, python_executable=SERENA_PYTHON)
        sources = ["README.md", "docs/spec.md"]
        self.adapter.write_new_memory("topics/arithmetic/edge_cases",
            "# Arithmetic edge cases\nPreserve negative operands and explicit zero-divisor errors.\nSources: docs/spec.md.\n", sources)
        self.adapter.write_new_memory("topics/arithmetic",
            "# Arithmetic conventions\nRead mem:topics/arithmetic/edge_cases before editing.\nSources: README.md and docs/spec.md.\n", sources)
        core = self.repo / ".serena/memories/core.md"
        self.adapter.update_memory("core", core.read_text() + "Read mem:topics/arithmetic for domain conventions.\n",
                                   sources, hashlib.sha256(core.read_bytes()).hexdigest())
        self.assertTrue(self.adapter.check_references()["clean"])
        self.git("add", ".serena")
        self.git("commit", "--quiet", "-m", "native multilayer memory chain")
        self.audit = self.base / "host-invocations-tiny.jsonl"
        self.expected = self.base / "native-memory-expectations.json"
        self.expected.write_text(json.dumps({"serena_home": str(self.home), "memories": {
            str(path.relative_to(self.repo / ".serena/memories")).removesuffix(".md"):
                hashlib.sha256(path.read_text().rstrip("\n").encode()).hexdigest()
            for path in (self.repo / ".serena/memories").rglob("*.md")}}))
        business_host = _FIXTURE.HOST.replace(
            'assert (root / ".serena/memories/core.md").read_text().strip()', 'assert contents["core"].strip()')
        # A same-worktree recovery may already contain the desired implementation.
        business_host = business_host.replace(
            'subprocess.run(["git", "commit", "--quiet", "-m", "simulated-host implements " + task], check=True)',
            'if subprocess.run(["git", "diff", "--cached", "--quiet"]).returncode:\n'
            '        subprocess.run(["git", "commit", "--quiet", "-m", "simulated-host implements " + task], check=True)')
        self.host.write_text(textwrap.dedent(NATIVE_HOST_PREFIX) + "\n" + textwrap.dedent(business_host))
        for mode, key in (("implement", "implementation_argv"), ("review", "review_argv")):
            self.bundle["config"]["host"][key] = [sys.executable, str(self.host), mode, "{task_id}", "{output}",
                SERENA, SERENA_PYTHON, str(self.base / "host-invocations-{task_id}.jsonl"), str(self.expected)]
        self.sibling = self.base / "unrelated-worktree"
        self.git("worktree", "add", "--quiet", "--detach", str(self.sibling), "main")
        self.original_knowledge = self.knowledge_bytes(self.repo)
        self.sibling_knowledge = self.knowledge_bytes(self.sibling)
        self.main_head = self.git("rev-parse", "main")

    @staticmethod
    def knowledge_bytes(root):
        return {str(path.relative_to(root)): path.read_bytes()
                for path in (Path(root) / ".serena").rglob("*")
                if path.is_file() and (path.name == "project.yml" or "memories" in path.parts)}

    def native(self, *args, cwd=None, okay=True):
        env = dict(self.env)
        env.pop("PYTHONPATH", None)
        result = subprocess.run([SERENA, *args], cwd=cwd or self.repo, env=env,
                                capture_output=True, text=True, timeout=30)
        if okay:
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        else:
            self.assertNotEqual(0, result.returncode, result.stdout + result.stderr)
        return result

    def observations(self):
        return [json.loads(line) for line in self.audit.read_text().splitlines()] if self.audit.exists() else []

    def assert_preserved(self, primary=None):
        self.assertEqual(primary if primary is not None else self.original_knowledge, self.knowledge_bytes(self.repo))
        self.assertEqual(self.sibling_knowledge, self.knowledge_bytes(self.sibling))
        self.assertEqual("", self.git("status", "--porcelain"))
        self.assertEqual("", self.git("status", "--porcelain", cwd=self.sibling))
        self.assertFalse((self.sibling / ".loop-state.json").exists())
        state = self.state()
        self.assertIsNone(state["active"])
        self.assertEqual(len(state["attempts"]), state["commands_started"])
        self.assertTrue(all(row["stopped"] for row in state["attempts"]))
        self.assertTrue(json.loads((self.repo / ".git/harness.execution.json").read_text())["stopped"])

    def assert_no_host(self):
        self.assertEqual([], self.observations())
        self.assertFalse(any(str(self.host) in row.get("argv", []) for row in self.state()["attempts"]))

    def test_new_worktrees_native_reads_review_and_persisted_registration_recovery(self):
        # Merely checking out committed project.yml and memories is insufficient.
        missing = self.native("memories", "read", "memory_maintenance", str(self.sibling), okay=False)
        self.assertIn("No Serena project found", missing.stderr)
        task = self.task("tiny")
        task["durable_evidence"].append(task["reports"]["walkthrough"])
        self.assertFalse((self.repo / task["reports"]["walkthrough"]).exists())
        self.save_bundle([task])
        result = self.cli("run", "--attempt", "native-worktree", "--implement")
        self.assertEqual("handoff", result["status"])
        evidence = result["tasks"][0]
        self.assertEqual("verified", evidence["status"])
        self.assertEqual("simulation", evidence["verification_tier"])
        self.assertIn(task["reports"]["walkthrough"],
                      [item["reference"] for item in evidence["knowledge"]["durable_evidence"]])
        reads = [row for row in self.observations() if row["phase"] == "native_reads_passed"]
        self.assertEqual(["implement", "review"], [row["mode"] for row in reads])
        self.assertNotEqual(reads[0]["pid"], reads[1]["pid"])
        self.assertNotEqual(reads[0]["root"], reads[1]["root"])
        self.assertEqual(evidence["candidate_path"], reads[1]["root"])
        expected = json.loads(self.expected.read_text())["memories"]
        for row in reads:
            self.assertEqual(expected, row["memories"])
            self.assertIn(row["root"], row["registered_paths"])
            self.assertNotIn(str(self.sibling), row["registered_paths"])
            self.assertEqual(self.original_knowledge, self.knowledge_bytes(Path(row["root"])))
            self.assertEqual("", self.git("status", "--porcelain", cwd=Path(row["root"])))
        attempts = self.state()["attempts"]
        for row in reads:
            host_index = next(index for index, attempt in enumerate(attempts)
                              if str(self.host) in attempt.get("argv", []) and row["mode"] in attempt["argv"])
            registrations = [attempt for attempt in attempts[:host_index]
                if "register" in attempt.get("argv", []) and row["root"] in attempt["argv"]]
            self.assertTrue(registrations, "exact worktree must be natively registered before its host starts")
            self.assertTrue(all(item["exit_code"] == 0 and item["stopped"] for item in registrations))
        self.assertEqual(self.main_head, self.git("rev-parse", "main"))
        self.assert_preserved()
        implementation = Path(reads[0]["root"])
        prior_attempts = len(self.state()["attempts"])
        # Re-enter the same repository controller in a fresh process. The real
        # registry must survive; repair must reuse that same worktree and lock.
        script = r'''
import json, sys
from pathlib import Path
from harness.cli import config_limits
from harness.runtime import Controller
from harness.state import Blocked
from harness.workflow import repair_task
bundle = json.loads(Path(sys.argv[1]).read_text())
config, task = bundle["config"], bundle["tasks"][0]
with Controller(config["repository_root"], "local", "e2e-run", config_limits(config)) as controller:
    try:
        with Controller(sys.argv[3], "local", "e2e-run", config_limits(config)):
            raise AssertionError("another worktree bypassed the shared run lock")
    except Blocked as exc:
        assert "active controller" in str(exc) or "lock" in str(exc).lower(), str(exc)
    result = repair_task(controller, config, task, sys.argv[2], "native-recovered",
                         "Simulation-only re-entry: verify native knowledge remains readable before any repair.")
    assert result["exit_code"] == 0 and result["stopped"]
'''
        recovered = subprocess.run([sys.executable, "-c", textwrap.dedent(script), str(self.bundle_path),
                                    str(implementation), str(self.sibling)], env=self.env,
                                   capture_output=True, text=True, timeout=90)
        self.assertEqual(0, recovered.returncode, recovered.stdout + recovered.stderr)
        reads_after = [row for row in self.observations() if row["phase"] == "native_reads_passed"]
        self.assertEqual(3, len(reads_after))
        self.assertEqual(str(implementation), reads_after[-1]["root"])
        self.assertEqual(expected, reads_after[-1]["memories"])
        self.assertGreater(len(self.state()["attempts"]), prior_attempts)
        self.assertEqual(1, self.state()["tasks"]["tiny"]["repair_attempts"])
        self.assert_preserved()
        self.assertEqual("", self.git("status", "--porcelain", cwd=implementation))

    def _commit_fault_and_run(self, mutate, expected_error):
        self.save_bundle([self.task("tiny")])
        mutate()
        self.git("add", "-A", ".serena")
        self.git("commit", "--quiet", "-m", "intentional native knowledge failure fixture")
        before = self.knowledge_bytes(self.repo)
        failed = self.cli("run", "--attempt", "knowledge-refused", "--implement", okay=False)
        self.assertIn(expected_error, failed.stderr)
        self.assert_no_host()
        self.assert_preserved(primary=before)
        worktree = self.repo / ".git/harness-worktrees/tiny-implementation-knowledge-refused-0"
        self.assertTrue(worktree.is_dir(), "failed knowledge gate must retain the actual source worktree")
        self.assertEqual(before, self.knowledge_bytes(worktree))
        self.assertEqual("", self.git("status", "--porcelain", cwd=worktree))
        return failed

    def test_missing_project_blocks_host_without_creating_knowledge(self):
        self._commit_fault_and_run(lambda: (self.repo / ".serena/project.yml").unlink(), "Required file missing")

    def test_missing_core_blocks_host_without_silent_onboarding(self):
        self._commit_fault_and_run(lambda: (self.repo / ".serena/memories/core.md").unlink(), "Required file missing")

    def test_stale_memory_reference_blocks_host_and_preserves_sources(self):
        core = self.repo / ".serena/memories/core.md"
        self._commit_fault_and_run(lambda: core.write_text(core.read_text() + "Broken fixture link mem:topics/missing.\n"),
                                  "stale memory references")

    def test_native_registration_failure_blocks_host_and_is_journaled(self):
        project = self.repo / ".serena/project.yml"
        self._commit_fault_and_run(lambda: project.write_text("project_name: invalid-native-fixture\nlanguages: [invalid-language-fixture]\n"),
                                  "Controlled native Serena call failed")
        registration = [row for row in self.state()["attempts"] if "register" in row.get("argv", [])
                        and any("tiny-implementation-" in arg for arg in row["argv"])]
        self.assertEqual(1, len(registration))
        self.assertNotEqual(0, registration[0]["exit_code"])
        self.assertTrue(Path(registration[0]["stderr_log"]).read_text().strip())


if __name__ == "__main__":
    unittest.main()
