"""simulated-host / native-Git / native-Serena CLI end-to-end fixtures.

This suite does not establish real Codex session/review/resume capability.
All Git repositories, Serena homes, host executables, and checkpoints are real
temporary files; CLI/state/Git are not mocked. Delivery crash-boundary coverage
performs the real Git update without modifying the controller's checkpoint.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "skills/harness-init/assets/project"
sys.path.insert(0, str(PACKAGE))
from harness.harness_check import scaffold
from harness.knowledge import SerenaAdapter

SERENA = os.environ.get("HARNESS_TEST_SERENA")
SERENA_PYTHON = os.environ.get("HARNESS_TEST_SERENA_PYTHON")
GIT = shutil.which("git")

HOST = r'''
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

mode, task, output = sys.argv[1:]
root = Path.cwd()
def behavior():
    spec = importlib.util.spec_from_file_location("fixture_solution", root / "solution.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if task == "exception":
        assert module.divide(8, 2) == 4
        try:
            module.divide(1, 0)
        except ValueError as exc:
            assert str(exc) == "zero divisor"
        else:
            raise AssertionError("expected explicit ValueError")
    else:
        assert module.add(2, 3) == 5
        assert module.add(-2, 3) == 1
        if task == "dependent":
            assert module.double_sum(2, 3) == 10

if mode == "implement":
    if task == "exception":
        code = "def divide(a, b):\n    if b == 0:\n        raise ValueError('zero divisor')\n    return a / b\n"
        test = "self.assertEqual(solution.divide(8, 2), 4)\n        with self.assertRaisesRegex(ValueError, 'zero divisor'):\n            solution.divide(1, 0)"
    else:
        code = "def add(a, b):\n    return a + b\n"
        test = "self.assertEqual(solution.add(2, 3), 5)\n        self.assertEqual(solution.add(-2, 3), 1)"
        if task == "dependent":
            assert "def add" in (root / "solution.py").read_text(), "dependency absent from baseline"
            code += "\ndef double_sum(a, b):\n    return 2 * add(a, b)\n"
            test += "\n        self.assertEqual(solution.double_sum(2, 3), 10)"
    (root / "solution.py").write_text(code.replace("\\n", "\n"))
    tests = "import unittest\nimport solution\n\nclass Business(unittest.TestCase):\n    def test_behavior(self):\n        " + test + "\n"
    (root / "tests/test_business.py").write_text(tests.replace("\\n", "\n"))
    for name in ("note", "walkthrough", "delivery"):
        path = root / "docs/reports" / task / (name + ".md")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# Fixture " + name + "\nScope: simulated-host / native-Git / native-Serena.\nTask " + task + ". See README.md and committed tests.\n")
    behavior()
    subprocess.run(["git", "add", "solution.py", "tests/test_business.py", "docs/reports"], check=True)
    subprocess.run(["git", "commit", "--quiet", "-m", "simulated-host implements " + task], check=True)
    Path(output).write_text("Simulated implementation committed; independent validation still required.\n")
elif mode == "review":
    behavior()
    assert (root / ".serena/memories/core.md").read_text().strip()
    assert (root / "README.md").read_text().strip()
    Path(output).write_text(json.dumps({"findings": [], "acceptance": [{
        "id": "AC-" + task, "status": "passed",
        "evidence": "Separate deterministic simulated-host process executed business assertions and read committed core/source; no real Codex review claim"
    }]}))
else:
    raise SystemExit("unknown simulated host action")
'''

RUN_TESTS = '''
import pathlib
import sys
import unittest
import xml.etree.ElementTree as ET
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
suite = unittest.defaultTestLoader.discover("tests", pattern="test_business.py")
result = unittest.TextTestRunner(verbosity=2).run(suite)
xml = ET.Element("testsuite", tests=str(result.testsRun))
for number in range(result.testsRun):
    case = ET.SubElement(xml, "testcase", name="business-" + str(number))
    if result.failures or result.errors:
        ET.SubElement(case, "failure").text = str(result.failures + result.errors)
    if result.skipped:
        ET.SubElement(case, "skipped")
ET.ElementTree(xml).write("junit.xml")
raise SystemExit(0 if result.wasSuccessful() and result.testsRun else 1)
'''


@unittest.skipUnless(SERENA and SERENA_PYTHON and GIT, "Native E2E requires explicit pinned Serena executable/Python and Git")
class CliE2E(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="harness-cli-e2e-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.repo = self.base / "repo"
        self.repo.mkdir()
        self.bin = self.base / "bin"
        self.bin.mkdir()
        (self.bin / "git").symlink_to(GIT)
        self.env = os.environ.copy()
        self.env["PATH"] = str(self.bin)
        self.env["PYTHONPATH"] = str(PACKAGE) + os.pathsep + os.environ.get("PYTHONPATH", "")
        self.env["PYTHONDONTWRITEBYTECODE"] = "1"
        self.assertIsNone(shutil.which("gh", path=self.env["PATH"]))
        self.git("init", "--quiet", "-b", "main")
        self.git("config", "user.name", "E2E Fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        (self.repo / ".gitignore").write_text(".loop-state.json\n.harness/\n__pycache__/\njunit.xml\n")
        (self.repo / ".harness-simulation").write_text("isolated-harness-fixture\n")
        (self.repo / "README.md").write_text("# Fixture project\nPython arithmetic, unittest checks. Local only; simulated host.\n")
        (self.repo / "solution.py").write_text("# Implementation pending\n")
        (self.repo / "tests").mkdir()
        (self.repo / "tests/run_business.py").write_text(textwrap.dedent(RUN_TESTS))
        (self.repo / "docs").mkdir()
        (self.repo / "docs/spec.md").write_text("# Acceptance\nImplement the named arithmetic task, including explicit error behavior where requested.\n")
        self.git("add", ".")
        self.git("commit", "--quiet", "-m", "native-Git fixture baseline")
        self.home = self.base / "serena-home"
        adapter = SerenaAdapter(self.repo, SERENA, self.home, python_executable=SERENA_PYTHON)
        adapter.create_project(["python"])
        adapter.initialize_maintenance()
        adapter.write_new_memory("core", "# Fixture core\nPython arithmetic fixture. Run python tests/run_business.py.\nSources: README.md and docs/spec.md. Preserve explicit error behavior.\n", ["README.md", "docs/spec.md"])
        self.git("add", ".serena")
        self.git("commit", "--quiet", "-m", "native-Serena fixture knowledge")
        self.host = self.base / "simulated_host.py"
        self.host.write_text(textwrap.dedent(HOST))
        self.bundle_path = self.base / "bundle.json"
        self.bundle = scaffold("local")
        config = self.bundle["config"]
        config.update(ready=True, repository_id="fixture-local", repository_root=str(self.repo))
        config["environment"] = {key: "fixture-observed" for key in config["environment"]}
        config["environment"].update(host="simulated-host", model="deterministic-fixture-no-model",
                                      os=sys.platform, git=self.git("--version"), runtime=sys.version.split()[0],
                                      skills_revision="fixture-current-tree", skills_path=str(ROOT / "skills/harness-init"),
                                      dependency_lock_sha256=hashlib.sha256((PACKAGE / "uv.lock").read_bytes()).hexdigest(),
                                      stop_method="owned-local-process-group", lock_backend="UnixFileLock")
        config["limits"] = {"command_seconds": 30, "stop_grace_seconds": 1,
                            "implementation_seconds": 20, "review_seconds": 20,
                            "repair_attempts": 2, "task_seconds": 600, "task_attempts": 5}
        config["checks"] = [{"id": "business", "kind": "test", "argv": [sys.executable, "tests/run_business.py"],
                              "timeout_seconds": 10, "min_executed": 1, "junit": "junit.xml"}]
        config["host"] = {"implementation_argv": [sys.executable, str(self.host), "implement", "{task_id}", "{output}"],
                          "review_argv": [sys.executable, str(self.host), "review", "{task_id}", "{output}"]}
        config["knowledge"] = {"executable": SERENA, "python_executable": SERENA_PYTHON,
                               "serena_home": str(self.home)}
        config["p0"] = {"register_existing": True, "max_commands": 8}
        self.assertEqual("", self.git("remote"))

    def git(self, *args, cwd=None):
        return subprocess.run([GIT, "-C", str(cwd or self.repo), *args], capture_output=True,
                              text=True, check=True, env=self.env).stdout.strip()

    def task(self, name, dependencies=()):
        return {"id": name, "source": "feature-" + name, "target": "main", "spec": "docs/spec.md",
                "dependencies": list(dependencies), "acceptance_ids": ["AC-" + name],
                "durable_evidence": ["README.md", "docs/spec.md"],
                "reports": {kind: f"docs/reports/{name}/{kind}.md" for kind in ("note", "walkthrough", "delivery")}}

    def save_bundle(self, tasks):
        self.bundle["tasks"] = tasks
        self.bundle_path.write_text(json.dumps(self.bundle))
        # The fixture operator approves concrete task/spec/check/budget bytes
        # before any simulated host may run; the host cannot weaken this gate.
        for task in tasks:
            result = self.cli("approve-contract", "--task", task["id"], "--authorize")
            self.assertTrue(result)
        # A receipt runs actual P0 component observations and binds these exact
        # config/host/package bytes. It deliberately remains simulation-only.
        receipt = self.cli("record-capabilities", "--tier", "simulation")
        self.assertEqual("simulation_only", receipt["status"])
        self.assertTrue(receipt["unverified"], "a simulated host must not erase real-host P0 gaps")

    def cli(self, command, *args, okay=True):
        argv = [sys.executable, "-m", "harness.cli", command, "--bundle", str(self.bundle_path)]
        if command not in ("preflight", "evidence"):
            argv.extend(["--run", "e2e-run"])
        result = subprocess.run(argv + list(args), env=self.env, capture_output=True, text=True, timeout=90)
        if okay:
            self.assertEqual(0, result.returncode, result.stdout + "\n" + result.stderr)
            return json.loads(result.stdout)
        self.assertNotEqual(0, result.returncode, result.stdout + "\n" + result.stderr)
        return result

    def state(self):
        return json.loads((self.repo / ".loop-state.json").read_text())

    def deliver_and_close(self, name):
        delivered = self.cli("deliver", "--task", name, "--target-worktree", str(self.repo), "--authorize", "--simulation")
        self.assertEqual("delivered", delivered["status"])
        self.assertEqual(self.git("rev-parse", "main"), delivered["D"])
        result = self.cli("closeout", "--task", name)
        self.assertEqual("completed", result["status"])
        return result

    def test_tiny_function_real_run_validate_deliver_closeout(self):
        self.save_bundle([self.task("tiny")])
        self.assertTrue(self.cli("preflight")["ok"])
        result = self.cli("run", "--attempt", "tiny-run", "--implement")
        self.assertEqual("handoff", result["status"])
        self.assertEqual("verified", self.state()["tasks"]["tiny"]["status"])
        before = self.git("rev-parse", "main")
        refused = self.cli("deliver", "--task", "tiny", "--target-worktree", str(self.repo), "--simulation", okay=False)
        self.assertIn("authorization", refused.stderr)
        self.assertEqual(before, self.git("rev-parse", "main"))
        production_refused = self.cli("deliver", "--task", "tiny", "--target-worktree", str(self.repo), "--authorize", okay=False)
        self.assertIn("simulation receipt cannot authorize real delivery", production_refused.stderr)
        self.assertEqual(before, self.git("rev-parse", "main"))
        self.deliver_and_close("tiny")
        self.assertEqual("", self.git("remote"))
        self.assertEqual("completed", self.cli("run", "--attempt", "nothing-left")["status"])

    def test_exception_path_explicit_validate_then_deliver_closeout(self):
        task = self.task("exception")
        self.save_bundle([task])
        source = self.base / "exception-source"
        self.git("worktree", "add", "--quiet", "-b", task["source"], str(source), "main")
        subprocess.run([sys.executable, str(self.host), "implement", "exception", str(self.base / "host-result.txt")],
                       cwd=source, env=self.env, check=True, capture_output=True, text=True)
        result = self.cli("validate", "--task", "exception", "--attempt", "exception-validate")
        self.assertEqual("verified", result["status"])
        self.assertGreaterEqual(result["checks"][0]["tests"], 1)
        self.assertEqual(0, result["checks"][0]["failed"])
        self.deliver_and_close("exception")

    def test_dependency_handoff_then_native_delivery_boundary_reconciliation(self):
        first, second = self.task("base"), self.task("dependent", ["base"])
        self.save_bundle([first, second])
        self.cli("run", "--attempt", "chain-first", "--implement")
        held = self.cli("run", "--attempt", "still-held", "--implement")
        self.assertEqual("base", held["tasks"][0]["task_id"])
        self.assertEqual("", self.git("branch", "--list", second["source"]))
        failed = self.cli("validate", "--task", "dependent", "--attempt", "premature", okay=False)
        self.assertIn("dependency not delivered", failed.stderr)
        self.deliver_and_close("base")
        self.cli("run", "--attempt", "chain-second", "--implement")
        saved = self.state()["tasks"]["dependent"]
        self.assertEqual("verified", saved["status"])
        evidence = json.loads(Path(saved["evidence"]).read_text())
        # Real physical delivery, with no state mutation: reproduce the crash
        # boundary between successful Git update and checkpoint persistence.
        checkpoint_before = (self.repo / ".loop-state.json").read_bytes()
        self.git("merge", "--ff-only", evidence["C"])
        self.assertEqual(checkpoint_before, (self.repo / ".loop-state.json").read_bytes())
        reconciled = self.cli("reconcile", "--task", "dependent")
        self.assertEqual("delivered", reconciled["status"])
        self.assertEqual(evidence["C"], reconciled["D"])
        completed = self.cli("closeout", "--task", "dependent")
        self.assertEqual("completed", completed["status"])
        self.assertEqual("completed", self.cli("run", "--attempt", "chain-finished")["status"])
        self.assertEqual("", self.git("remote"))


if __name__ == "__main__":
    unittest.main()
