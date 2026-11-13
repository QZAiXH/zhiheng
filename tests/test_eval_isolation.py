"""Regression checks for preserving accepted TDD evaluation evidence."""

import hashlib
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch


SOURCE = Path(__file__).resolve().parent / "evals/run_tdd_resources.py"
SKILLS = Path(__file__).resolve().parents[1] / "skills"
RESOURCES = ("zh-tdd/SKILL.md", "zh-tdd/references/tests.md",
             "zh-tdd/references/mocking.md")


class TDDRunnerIsolation(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.runner = root / "tests/evals/run_tdd_resources.py"
        self.runner.parent.mkdir(parents=True)
        shutil.copy2(SOURCE, self.runner)
        (root / "skills").symlink_to(SKILLS, target_is_directory=True)
        self.runs = root / "docs/evidence/i03-tdd-followup/runs"

    def accepted(self, name):
        old = self.runs / name
        old.mkdir(parents=True)
        for filename in ("request.txt", "inputs.json", "launch.json", "events.jsonl",
                         "stderr.log", "result.json"):
            (old / filename).write_bytes(("accepted " + filename).encode())
        return old, {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in old.iterdir()}

    def assert_accepted(self, old, fingerprints):
        self.assertEqual({p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in old.iterdir()}, fingerprints)

    def invoke(self, name, process):
        with patch.dict(os.environ, {"ZH_EVAL_RUN_ID": name}):
            with patch("subprocess.run", side_effect=process):
                with self.assertRaises(SystemExit) as outcome:
                    runpy.run_path(str(self.runner), run_name="__main__")
        return outcome.exception.code

    def test_existing_run_rejected_before_write_or_process(self):
        old, fingerprints = self.accepted("same-id")
        calls = []

        def process(*args, **kwargs):
            calls.append(args)
            raise AssertionError("process started")

        with self.assertRaises(FileExistsError):
            self.invoke("same-id", process)
        self.assertEqual(calls, [])
        self.assert_accepted(old, fingerprints)

    def test_success_and_timeout_keep_separate_complete_records(self):
        old, fingerprints = self.accepted("accepted")

        def success(command, **kwargs):
            if command[:3] == ["python3", "-B", "-m"]:
                return subprocess.CompletedProcess(command, 0, "", "tests passed")
            project = Path(command[command.index("-C") + 1])
            events = [
                {"type": "item.completed", "item": {
                    "type": "command_execution", "exit_code": 0,
                    "command": f"cat .agents/skills/{name}",
                    "aggregated_output": (project / ".agents/skills" / name).read_text(),
                }} for name in RESOURCES
            ]
            return subprocess.CompletedProcess(command, 0,
                                               "\n".join(json.dumps(e) for e in events) + "\n", "")

        self.assertEqual(self.invoke("successful", success), 0)
        new = self.runs / "successful"
        self.assertEqual(json.loads((new / "result.json").read_text())["exit"], 0)
        self.assertEqual(json.loads((new / "launch.json").read_text())["runner_sha256"],
                         hashlib.sha256(self.runner.read_bytes()).hexdigest())
        self.assertTrue((new / "project/receipt.py").exists())
        successful_files = {p.relative_to(new).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in new.rglob("*") if p.is_file()}
        self.assertTrue({"runner.py", "request.txt", "inputs.json", "launch.json",
                         "events.jsonl", "stderr.log", "result.json",
                         "parent-tests.stdout", "parent-tests.stderr",
                         "project/receipt.py"} <= successful_files.keys())

        def timeout(command, **kwargs):
            raise subprocess.TimeoutExpired(command, 360, output=b'{"type":"turn.started"}\n',
                                            stderr=b"timeout diagnostic")

        self.assertEqual(self.invoke("timed-out", timeout), 1)
        timed = self.runs / "timed-out"
        self.assertEqual((timed / "events.jsonl").read_bytes(), b'{"type":"turn.started"}\n')
        self.assertEqual((timed / "stderr.log").read_bytes(), b"timeout diagnostic")
        self.assertEqual(json.loads((timed / "result.json").read_text())["exit"], "timeout")
        self.assert_accepted(old, fingerprints)
        self.assertEqual(
            {p.relative_to(new).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in new.rglob("*") if p.is_file()}, successful_files)


if __name__ == "__main__":
    unittest.main()
