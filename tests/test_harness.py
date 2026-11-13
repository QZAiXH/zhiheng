"""Behavior tests for the three public CLI commands; all samples are temporary."""

from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import yaml


SCRIPT = Path(__file__).resolve().parents[1] / "skills/zh/scripts/harness.py"


class HarnessCLI(unittest.TestCase):
    def setUp(self):
        self.base_env = {key: value for key, value in os.environ.items()
                         if key not in {"GIT_DIR", "GIT_COMMON_DIR", "GIT_WORK_TREE"}}
        self.temp = tempfile.TemporaryDirectory(prefix="zh-harness-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.task = self.root / "docs/tasks/T-20261112-001/README.md"
        self.task_data = {"schema_version": 1, "kind": "task", "id": "T-20261112-001",
                          "revision": 1, "status": "待处理", "phase": "实施",
                          "delivery_target": "本地交付", "plan": None}
        self.save_task()
        self.write("src/main.py", "print('hello')\n")
        self.write("spec.md", "# Confirmed specification\n")
        self.write("test.log", "1 test passed\n")
        self.scope_data = {"schema_version": 1, "root": ".", "paths": ["src"],
                           "sources": [{"id": "SPEC", "path": "spec.md", "revision": 1}],
                           "checks": [{"id": "C01", "command": "python -m unittest", "evidence": ["test.log"]}],
                           "conditions": {"environment": "local"}}
        self.scope = self.root / "scope.yaml"
        self.save_scope()
        self.manifest = self.root / "manifest.json"

    def write(self, relative, text):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def record(self, path, data, body="# Goal\nDeliver the requested behavior.\n"):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("---\n" + yaml.safe_dump(data, allow_unicode=True, sort_keys=False) + "---\n" + body, encoding="utf-8")

    def save_task(self, body="# Goal\nDeliver the requested behavior.\n"):
        self.record(self.task, self.task_data, body)

    def save_scope(self):
        self.scope.write_text(yaml.safe_dump(self.scope_data, allow_unicode=True, sort_keys=False), encoding="utf-8")

    def cli(self, command, code=0, extra=(), env=None):
        args = [sys.executable, "-B", str(SCRIPT), command, "--task", str(self.task)]
        if command == "snapshot":
            args += ["--scope", str(self.scope), "--output", str(self.manifest)]
        elif command == "compare":
            args += ["--manifest", str(self.manifest)]
        args += list(extra)
        result = subprocess.run(args, cwd=self.root, text=True, capture_output=True,
                                env=env if env is not None else self.base_env, timeout=30)
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        self.assertEqual(result.stderr, "", result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["command"], command)
        self.assertIn("applicability", payload)
        return payload

    def codes(self, payload):
        return {item["code"] for item in payload["findings"]}

    def plan(self):
        self.task_data["plan"] = "plan.md"
        self.save_task()
        self.plan_path = self.task.parent / "plan.md"
        self.plan_data = {"schema_version": 1, "kind": "plan", "task_ref": "README.md", "items": [
            {"id": "S01", "revision": 1, "status": "待处理", "depends_on": [], "assignee": None, "detail": "tasks/S01.md"},
            {"id": "S02", "revision": 1, "status": "待处理", "depends_on": ["S01"], "assignee": None, "detail": "tasks/S02.md"}]}
        for identity in ("S01", "S02"):
            self.record(self.task.parent / f"tasks/{identity}.md", {"schema_version": 1, "kind": "slice",
                        "plan_ref": "../plan.md", "slice_id": identity})
        self.record(self.plan_path, self.plan_data)

    def verification(self):
        status = self.task_data["status"]
        plan_items = deepcopy(self.plan_data["items"]) if hasattr(self, "plan_data") else None
        self.task_data["status"] = "待处理"
        if plan_items:
            for item in self.plan_data["items"]:
                item["status"] = "待处理"
            self.record(self.plan_path, self.plan_data)
        self.task_data["verification"] = "verification.md"
        self.save_task()
        self.verification_path = self.task.parent / "verification.md"
        self.write(self.task.parent.relative_to(self.root) / "evidence/test.log", "PASS\n")
        self.verification_data = {"schema_version": 1, "kind": "verification", "task_ref": "README.md",
            "task_revision": 1, "checks": [{"id": "C01", "result": "通过", "evidence": ["evidence/test.log"]}],
            "acceptance": []}
        self.scope_data["checks"][0]["evidence"] = [str(self.verification_path.parent.relative_to(self.root) / "evidence/test.log")]
        self.save_scope()
        self.record(self.verification_path, self.verification_data)
        self.cli("snapshot")
        self.task_data["status"] = status
        self.save_task()
        if plan_items:
            self.plan_data["items"] = plan_items
            self.record(self.plan_path, self.plan_data)
        self.verification_data["manifest"] = "../../../manifest.json"
        self.verification_data["acceptance"] = [{"id": "A01", "revision": 1, "result": "通过", "check_ids": ["C01"]}]
        self.record(self.verification_path, self.verification_data)

    def git(self, *args):
        result = subprocess.run(["git", "-C", str(self.root), *args], text=True,
                                capture_output=True, env=self.base_env, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout.strip()

    def git_init(self):
        self.git("init", "-q")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "user.name", "Harness Test")
        self.git("add", ".")
        self.git("commit", "-qm", "Initial sample")

    def test_valid_task_and_non_git_snapshot_compare(self):
        self.write("test.log", "abc")
        before = self.task.read_bytes()
        self.cli("validate")
        self.cli("snapshot")
        manifest = json.loads(self.manifest.read_text())
        self.assertEqual(manifest["files"]["test.log"]["sha256"], "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")
        self.assertFalse(manifest["git"]["available"])
        result = self.cli("compare")
        self.assertTrue(all(item["state"] == "unchanged" for item in result["comparisons"]))
        self.assertEqual(before, self.task.read_bytes())

    def test_valid_plan(self):
        self.plan()
        result = self.cli("validate")
        self.assertEqual(len(result["records"]), 4)

    def test_nested_duplicate_yaml_key(self):
        self.task.write_text(self.task.read_text().replace("plan: null", "plan: null\nextra:\n  x: 1\n  x: 2"))
        self.assertIn("duplicate_key", self.codes(self.cli("validate", 1)))

    def test_unsafe_and_invalid_yaml_rejected(self):
        for value in ("x: [", "x: !!python/object/apply:os.system ['echo forbidden']"):
            with self.subTest(value=value):
                self.task.write_text("---\n" + value + "\n---\n")
                self.assertIn("invalid_yaml", self.codes(self.cli("validate", 1)))

    def test_unknown_version_kind_state_and_bad_revision(self):
        for field, value in (("schema_version", 2), ("schema_version", True), ("kind", "alien"),
                             ("kind", []), ("status", "done"), ("revision", True)):
            with self.subTest(field=field, value=value):
                data = deepcopy(self.task_data)
                data[field] = value
                self.record(self.task, data)
                self.cli("validate", 1)

    def test_duplicate_slice_and_task_ids(self):
        self.plan()
        self.plan_data["items"].append(deepcopy(self.plan_data["items"][0]))
        self.record(self.plan_path, self.plan_data)
        self.assertIn("duplicate_id", self.codes(self.cli("validate", 1)))
        self.task_data["plan"] = None
        self.save_task()
        self.record(self.task.parent.parent / "another/README.md", self.task_data)
        self.assertIn("duplicate_id", self.codes(self.cli("validate", 1)))

    def test_missing_dependency_and_cycle(self):
        self.plan()
        self.plan_data["items"][0]["depends_on"] = ["S99"]
        self.record(self.plan_path, self.plan_data)
        self.assertIn("missing_dependency", self.codes(self.cli("validate", 1)))
        self.plan_data["items"][0]["depends_on"] = ["S02"]
        self.record(self.plan_path, self.plan_data)
        self.assertIn("dependency_cycle", self.codes(self.cli("validate", 1)))

    def test_broken_plan_detail_and_markdown_links(self):
        self.task_data["plan"] = "absent.md"
        self.save_task()
        self.assertIn("broken_reference", self.codes(self.cli("validate", 1)))
        self.task_data["plan"] = None
        self.save_task("[spec](absent.md)\n![image](absent.png)\n[remote](https://example.invalid/spec)\n")
        result = self.cli("validate", 1)
        self.assertEqual(len(result["findings"]), 2)
        self.plan()
        (self.task.parent / "tasks/S01.md").unlink()
        self.assertIn("broken_reference", self.codes(self.cli("validate", 1)))

    def test_wrong_back_reference_and_duplicate_authority(self):
        self.plan()
        self.record(self.task.parent / "tasks/S01.md", {"schema_version": 1, "kind": "slice", "plan_ref": "../README.md",
            "slice_id": "S99", "status": "待处理", "revision": 1})
        result = self.cli("validate", 1)
        self.assertTrue({"wrong_reference", "duplicate_authority"} <= self.codes(result))

    def test_completed_requires_current_acceptance_and_evidence(self):
        self.task_data["status"] = "已完成"
        self.save_task()
        self.assertIn("missing_acceptance", self.codes(self.cli("validate", 1)))
        self.verification()
        self.cli("validate")
        (self.task.parent / "evidence/test.log").unlink()
        self.assertIn("broken_reference", self.codes(self.cli("validate", 1)))

    def test_pending_verification_template_can_have_no_execution_results(self):
        self.verification()
        self.record(self.verification_path, {"schema_version": 1, "kind": "verification", "task_ref": "README.md",
                                           "task_revision": 1, "manifest": None})
        self.cli("validate")

    def test_acceptance_rejects_missing_failed_check_or_old_revision(self):
        self.verification()
        original = deepcopy(self.verification_data)
        changes = [("missing_check", lambda d: d["acceptance"][0].update(check_ids=["C99"])),
                   ("unmet_check", lambda d: d["checks"][0].update(result="失败")),
                   ("stale_revision", lambda d: d.update(task_revision=2)),
                   ("stale_revision", lambda d: d["acceptance"][0].update(revision=2)),
                   ("missing_evidence", lambda d: d["checks"][0].update(evidence=[]))]
        for code, change in changes:
            with self.subTest(code=code):
                value = deepcopy(original)
                change(value)
                self.record(self.verification_path, value)
                self.assertIn(code, self.codes(self.cli("validate", 1)))

    def test_completed_slice_requires_its_own_acceptance(self):
        self.plan()
        self.plan_data["items"][0]["status"] = "已完成"
        self.record(self.plan_path, self.plan_data)
        self.verification()
        self.assertIn("missing_acceptance", self.codes(self.cli("validate", 1)))
        self.verification_data["acceptance"].append({"id": "A02", "slice_id": "S01", "revision": 1,
                                                   "result": "通过", "check_ids": ["C01"]})
        self.record(self.verification_path, self.verification_data)
        self.cli("validate")

    def test_return_rejects_old_requirement_and_source_revisions(self):
        self.task_data["sources"] = [{"id": "SPEC", "path": "../../../spec.md", "revision": "r2"}]
        self.task_data["records"] = ["return.md"]
        self.save_task()
        path = self.task.parent / "return.md"
        value = {"schema_version": 1, "kind": "return", "task_ref": "README.md", "task_revision": 1,
                 "dispatch_id": "D01", "workspace": ".", "write_scope": [],
                 "sources": [{"id": "SPEC", "path": "../../../spec.md", "revision": "r2"}]}
        self.record(path, value)
        self.cli("validate")
        value["sources"][0]["revision"] = "r1"
        self.record(path, value)
        self.assertIn("stale_source", self.codes(self.cli("validate", 1)))
        value["task_revision"] = 0
        self.record(path, value)
        self.assertIn("stale_revision", self.codes(self.cli("validate", 1)))

    def test_status_and_requirements_are_reported_separately(self):
        self.cli("snapshot")
        self.task_data["status"] = "执行中"
        self.save_task()
        result = self.cli("compare", 1)
        self.assertTrue(any(x["category"] == "task_status" and x["state"] == "changed" for x in result["comparisons"]))
        self.assertTrue(any(x["category"] == "requirement_revision" and x["state"] == "unchanged" for x in result["comparisons"]))
        self.task_data["revision"] = 2
        self.save_task()
        result = self.cli("compare", 1)
        self.assertTrue(any(x["category"] == "requirement_revision" and x["state"] == "changed" for x in result["comparisons"]))

    def test_directory_additions_deletions_and_evidence_changes(self):
        self.cli("snapshot")
        self.write("src/new.py", "added\n")
        (self.root / "src/main.py").unlink()
        self.write("test.log", "2 tests passed\n")
        result = self.cli("compare", 1)
        states = {(x["category"], x["field"]): x["state"] for x in result["comparisons"]}
        self.assertEqual(states[("files", "src/main.py")], "missing")
        self.assertEqual(states[("files", "src/new.py")], "changed")
        self.assertEqual(states[("files", "test.log")], "changed")

    def test_source_content_and_declared_revision_are_independent(self):
        self.cli("snapshot")
        self.write("spec.md", "# New specification\n")
        result = self.cli("compare", 1)
        states = {(x["category"], x["field"]): x["state"] for x in result["comparisons"]}
        self.assertEqual(states[("files", "spec.md")], "changed")
        self.assertEqual(states[("sources", "scope:SPEC.revision")], "unchanged")
        self.scope_data["sources"][0]["revision"] = 2
        self.save_scope()
        result = self.cli("compare", 1)
        self.assertTrue(any(x["category"] == "sources" and x["field"].endswith(".revision") and x["state"] == "changed" for x in result["comparisons"]))

    def test_missing_scope_or_evidence_never_becomes_unchanged(self):
        self.cli("snapshot")
        (self.root / "test.log").unlink()
        result = self.cli("compare", 1)
        self.assertTrue(any(x["category"] == "files" and x["field"] == "test.log" and x["state"] == "missing" for x in result["comparisons"]))
        self.scope.unlink()
        result = self.cli("compare", 1)
        self.assertTrue(result["comparisons"])
        self.assertTrue(all(x["state"] == "unverifiable" for x in result["comparisons"]))

    def test_snapshot_self_exclusion_is_repeatable_inside_scope(self):
        self.scope_data["paths"] = ["."]
        self.save_scope()
        self.manifest = self.root / "outputs/manifest.json"
        self.cli("snapshot")
        original = self.manifest.read_bytes()
        self.cli("compare")
        self.cli("snapshot")
        self.assertEqual(self.manifest.read_bytes(), original)
        self.assertNotIn("outputs/manifest.json", json.loads(original)["files"])

    def test_snapshot_refuses_missing_scope_member_and_output_as_evidence(self):
        self.scope_data["paths"].append("absent")
        self.save_scope()
        result = self.cli("snapshot", 1)
        self.assertFalse(result["written"])
        self.assertFalse(self.manifest.exists())
        self.scope_data["paths"] = ["src"]
        self.scope_data["checks"][0]["evidence"] = ["manifest.json"]
        self.save_scope()
        self.assertIn("self_reference", self.codes(self.cli("snapshot", 1)))

    def test_scope_boundary_and_symlink_are_explicit_gaps(self):
        self.scope_data["paths"] = ["../outside"]
        self.save_scope()
        self.assertIn("outside_scope", self.codes(self.cli("snapshot", 1)))
        self.scope_data["paths"] = ["src"]
        self.save_scope()
        (self.root / "src/link").symlink_to(self.root / "spec.md")
        self.assertIn("symlink", self.codes(self.cli("snapshot", 1)))

    def test_symlink_replacement_is_unverifiable(self):
        self.cli("snapshot")
        (self.root / "src/main.py").unlink()
        (self.root / "src/main.py").symlink_to(self.root / "spec.md")
        result = self.cli("compare", 1)
        self.assertTrue(any(x["category"] == "files" and x["field"] == "src/main.py" and x["state"] == "unverifiable" for x in result["comparisons"]))

    def test_scope_version_duplicate_key_and_undefined_root(self):
        self.scope.write_text("schema_version: 2\nroot: .\npaths: [src]\n")
        self.assertIn("unsupported_version", self.codes(self.cli("snapshot", 1)))
        self.scope.write_text("schema_version: 1\nroot: .\npaths: [src]\nchecks:\n - id: C1\n   id: C2\n")
        self.assertIn("duplicate_key", self.codes(self.cli("snapshot", 1)))
        self.scope.write_text("schema_version: 1\npaths: [src]\n")
        self.cli("snapshot", 1)

    def test_minimum_scope_requires_no_fabricated_check_claim(self):
        self.scope_data = {"schema_version": 1, "root": ".", "paths": ["src"]}
        self.save_scope()
        self.cli("snapshot")
        manifest = json.loads(self.manifest.read_text())
        self.assertEqual(manifest["checks"], {})
        self.assertEqual(manifest["conditions"], {})

    def test_conditions_and_check_identifiers_are_observed(self):
        self.cli("snapshot")
        self.scope_data["conditions"]["environment"] = "staging"
        self.scope_data["checks"][0]["command"] = "python -m unittest -v"
        self.save_scope()
        result = self.cli("compare", 1)
        groups = {x["category"] for x in result["comparisons"] if x["state"] == "changed"}
        self.assertTrue({"checks", "conditions"} <= groups)

    def test_compare_invalid_conditions_preserves_json_and_other_observations(self):
        self.cli("snapshot")
        baseline = self.manifest.read_bytes()
        for conditions in ([], None, "local"):
            with self.subTest(conditions=conditions):
                self.scope_data["conditions"] = conditions
                self.save_scope()
                result = self.cli("compare", 1)
                self.assertEqual(result["status"], "issues")
                self.assertTrue(any(x["code"] == "invalid_field" and x["field"] == "conditions"
                                    for x in result["findings"]))
                self.assertTrue(any(x["category"] == "conditions" and x["state"] == "unverifiable"
                                    and not x["reusable"] for x in result["comparisons"]))
                self.assertTrue(any(x["category"] == "files" and x["field"] == "src/main.py"
                                    and x["state"] == "unchanged" for x in result["comparisons"]))
                self.assertFalse(self.cli("snapshot", 1)["written"])
                self.assertEqual(self.manifest.read_bytes(), baseline)
        self.scope_data["conditions"] = {"environment": "local"}
        self.save_scope()
        self.cli("compare")

    def test_slice_acceptance_requires_manifest_slice_identity_and_revision(self):
        self.plan()
        self.verification()
        original = json.loads(self.manifest.read_text())
        self.assertEqual(original["slices"]["S01"]["revision"], 1)
        self.plan_data["items"][0].update(revision=2, status="已完成")
        self.record(self.plan_path, self.plan_data)
        acceptance = {"id": "A02", "slice_id": "S01", "revision": 2,
                      "result": "通过", "check_ids": ["C01"]}
        self.verification_data["acceptance"].append(acceptance)
        self.record(self.verification_path, self.verification_data)
        result = self.cli("validate", 1)
        self.assertTrue(any(x["code"] == "stale_manifest" and "S01" in x["field"]
                            for x in result["findings"]))
        del original["slices"]["S01"]
        self.manifest.write_text(json.dumps(original))
        self.assertIn("stale_manifest", self.codes(self.cli("validate", 1)))
        self.plan_data["items"][0]["status"] = "待处理"
        self.record(self.plan_path, self.plan_data)
        self.verification_data["acceptance"] = []
        self.record(self.verification_path, self.verification_data)
        self.cli("snapshot")
        self.assertEqual(json.loads(self.manifest.read_text())["slices"]["S01"]["revision"], 2)
        self.plan_data["items"][0]["status"] = "已完成"
        self.record(self.plan_path, self.plan_data)
        self.verification_data["acceptance"] = [acceptance]
        self.record(self.verification_path, self.verification_data)
        self.cli("validate")

    def test_existing_damaged_records_are_not_reported_as_missing(self):
        self.plan()
        self.cli("snapshot")
        records = [self.task, self.plan_path, self.task.parent / "tasks/S01.md"]
        original = {path: path.read_bytes() for path in records}
        for path in records:
            with self.subTest(record=path.name):
                try:
                    path.write_text("---\nschema_version: 1\nkind: task\nid: [\n---\n")
                    result = self.cli("compare", 1)
                    self.assertIn("invalid_yaml", self.codes(result))
                    relative = str(path.relative_to(self.root))
                    entries = [x for x in result["comparisons"]
                               if x["category"] in {"files", "records"} and x["field"] == relative]
                    self.assertEqual({x["category"] for x in entries}, {"files", "records"})
                    self.assertTrue(all(x["state"] in {"changed", "unverifiable"} and not x["reusable"]
                                        for x in entries))
                finally:
                    path.write_bytes(original[path])
        self.cli("compare")
        self.task.unlink()
        result = self.cli("compare", 1)
        self.assertTrue(any(x["category"] == "files" and x["field"] == str(self.task.relative_to(self.root))
                            and x["state"] == "missing" for x in result["comparisons"]))

    def test_markdown_parenthesized_destinations_and_real_broken_links(self):
        cases = [
            ("spec(v2).md", "../../../spec(v2).md"),
            ("spec(v2(draft)).md", "../../../spec(v2(draft)).md"),
            ("spec(v2).md", "<../../../spec(v2).md>"),
            ("spec(v2).md", r"../../../spec\(v2\).md"),
        ]
        for filename, destination in cases:
            with self.subTest(destination=destination):
                path = self.write(filename, "# Specification\n")
                self.save_task(f'[spec]({destination} "Specification")\n')
                self.cli("validate")
                self.cli("snapshot")
                path.unlink()
                self.assertIn("broken_reference", self.codes(self.cli("validate", 1)))
                self.assertFalse(self.cli("snapshot", 1)["written"])
        self.write("spec(v2).md", "# Specification\n")
        references_and_images = [
            "[spec][current]\n\n[current]: ../../../spec(v2).md\n",
            "![spec](<../../../spec(v2).md>)\n",
            "![spec][current]\n\n[current]: <../../../spec(v2).md>\n",
            "[unused]: <../../../spec(v2).md>\n",
        ]
        for body in references_and_images:
            with self.subTest(body=body):
                path = self.write("spec(v2).md", "# Specification\n")
                self.save_task(body)
                self.cli("validate")
                self.cli("snapshot")
                path.unlink()
                self.assertIn("broken_reference", self.codes(self.cli("validate", 1)))
                self.assertFalse(self.cli("snapshot", 1)["written"])

    def test_markdown_code_examples_are_ignored_but_real_links_are_checked(self):
        examples = [
            "```markdown\n[example](missing.md)\n[unused]: absent.md\n```\n",
            "~~~markdown\n[example](missing.md)\n~~~\n",
            "````markdown\n```\n[example](missing.md)\n```\n````\n",
            "    [example](missing.md)\n",
            "`[example](missing.md)`\n",
            "`` a ` marker [example](missing.md) ``\n",
            "`[example]\n(missing.md)`\n",
        ]
        for example in examples:
            with self.subTest(example=example):
                self.save_task(example + "\n[spec](../../../spec.md)\n")
                self.cli("validate")
                self.cli("snapshot")
                self.save_task(example + "\n[real](../../../missing.md)\n")
                result = self.cli("validate", 1)
                self.assertEqual([x["code"] for x in result["findings"]], ["broken_reference"])
                self.assertFalse(self.cli("snapshot", 1)["written"])

    def test_markdown_container_code_blocks_are_not_dependencies(self):
        examples = [
            "> ~~~markdown\n> [example](missing.md)\n> ~~~\n",
            "- ```markdown\n  [example](missing.md)\n  ```\n",
        ]
        for example in examples:
            with self.subTest(example=example):
                self.assertFalse((self.task.parent / "missing.md").exists())
                self.save_task(example + "\n[spec](../../../spec.md)\n")
                self.cli("validate")
                self.cli("snapshot")
                self.assertTrue(json.loads(self.manifest.read_text())["complete"])
                self.save_task(example + "\n[real](missing.md)\n")
                self.assertIn("broken_reference", self.codes(self.cli("validate", 1)))
                before = self.manifest.read_bytes()
                self.assertFalse(self.cli("snapshot", 1)["written"])
                self.assertEqual(self.manifest.read_bytes(), before)

    def test_markdown_indented_paragraph_and_list_continuations_are_links(self):
        templates = [
            "Paragraph continues\n    [real]({target})\n",
            "- source:\n    [real]({target})\n",
        ]
        for template in templates:
            with self.subTest(template=template):
                self.assertFalse((self.task.parent / "missing.md").exists())
                self.save_task(template.format(target="missing.md"))
                self.assertIn("broken_reference", self.codes(self.cli("validate", 1)))
                result = self.cli("snapshot", 1)
                self.assertFalse(result["written"])
                self.assertFalse(self.manifest.exists())
                self.save_task(template.format(target="../../../spec.md"))
                self.cli("validate")
                self.cli("snapshot")
                self.assertTrue(json.loads(self.manifest.read_text())["complete"])
                self.manifest.unlink()

    def test_decoded_colon_is_a_local_markdown_filename(self):
        target = self.write("docs/tasks/T-20261112-001/api:v2.md", "# API\n")
        self.save_task("[source](api%3Av2.md)\n")
        self.cli("validate")
        self.cli("snapshot")
        before = self.manifest.read_bytes()
        target.unlink()
        self.assertIn("broken_reference", self.codes(self.cli("validate", 1)))
        self.assertFalse(self.cli("snapshot", 1)["written"])
        self.assertEqual(self.manifest.read_bytes(), before)

    def test_image_alt_text_nested_markup_is_not_a_file_dependency(self):
        image = self.write("docs/tasks/T-20261112-001/diagram.png", "image bytes")
        for alt in ("diagram [source](missing.md)", "diagram ![inner](missing.png)"):
            with self.subTest(alt=alt):
                self.save_task(f"![{alt}](diagram.png)\n")
                self.cli("validate")
                self.cli("snapshot")
                self.assertTrue(json.loads(self.manifest.read_text())["complete"])
                image.unlink()
                self.assertIn("broken_reference", self.codes(self.cli("validate", 1)))
                self.assertFalse(self.cli("snapshot", 1)["written"])
                image.write_text("image bytes")
        self.save_task("![diagram [source](missing.md)](diagram.png)\n[real](missing.md)\n")
        self.assertIn("broken_reference", self.codes(self.cli("validate", 1)))

    def test_manifest_missing_fields_and_unknown_version(self):
        for value in ({"schema_version": 1, "kind": "manifest", "complete": True},
                      {"schema_version": 2, "kind": "manifest", "complete": True}):
            with self.subTest(value=value):
                self.manifest.write_text(json.dumps(value))
                self.cli("compare", 1)

    def test_non_json_yaml_values_are_structural_errors(self):
        for value in ("2026-11-12", "!!set {a: null}", ".nan", "&loop [*loop]"):
            with self.subTest(value=value):
                self.scope.write_text("schema_version: 1\nroot: .\npaths: [src]\nconditions:\n  value: " + value + "\n")
                self.assertIn("invalid_value", self.codes(self.cli("snapshot", 1)))

    def test_snapshot_cannot_overwrite_an_explicit_or_existing_artifact(self):
        self.scope_data["paths"] = ["src/main.py"]
        self.save_scope()
        self.manifest = self.root / "src/main.py"
        before = self.manifest.read_bytes()
        self.cli("snapshot", 1)
        self.assertEqual(before, self.manifest.read_bytes())
        self.scope_data["paths"] = ["src"]
        self.save_scope()
        self.cli("snapshot", 1)
        self.assertEqual(before, self.manifest.read_bytes())

    def test_return_requires_dispatch_workspace_scope_and_all_sources(self):
        self.task_data["sources"] = [{"id": "SPEC", "path": "../../../spec.md", "revision": "r2"}]
        self.task_data["records"] = ["return.md"]
        self.save_task()
        value = {"schema_version": 1, "kind": "return", "task_ref": "README.md", "task_revision": 1}
        path = self.task.parent / "return.md"
        self.record(path, value)
        result = self.cli("validate", 1)
        self.assertIn("missing_source", self.codes(result))
        self.assertTrue({"dispatch_id", "workspace", "write_scope"} <= {x["field"] for x in result["findings"]})
        value.update(dispatch_id="D01", workspace=".", write_scope=[], source_versions={"SPEC": "r2"})
        self.record(path, value)
        self.cli("validate")

    def test_acceptance_requires_matching_manifest_and_bound_evidence(self):
        self.verification()
        self.verification_data["manifest"] = None
        self.record(self.verification_path, self.verification_data)
        self.assertIn("missing_manifest", self.codes(self.cli("validate", 1)))
        self.verification_data["manifest"] = "../../../manifest.json"
        self.record(self.verification_path, self.verification_data)
        manifest = json.loads(self.manifest.read_text())
        manifest["task"]["revision"] = 2
        self.manifest.write_text(json.dumps(manifest))
        self.assertIn("stale_manifest", self.codes(self.cli("validate", 1)))
        manifest["task"]["revision"] = 1
        self.manifest.write_text(json.dumps(manifest))
        (self.task.parent / "evidence/test.log").write_text("FAIL\n")
        self.assertIn("stale_evidence", self.codes(self.cli("validate", 1)))

    def test_manifest_cannot_hide_changes_by_extending_exclusions(self):
        self.cli("snapshot")
        manifest = json.loads(self.manifest.read_text())
        manifest["excluded_paths"].append("src/main.py")
        self.manifest.write_text(json.dumps(manifest))
        self.assertIn("invalid_manifest", self.codes(self.cli("compare", 1)))

    def test_malformed_nested_manifest_and_local_link_are_structural_errors(self):
        self.cli("snapshot")
        manifest = json.loads(self.manifest.read_text())
        manifest["git"]["index"] = []
        self.manifest.write_text(json.dumps(manifest))
        self.assertIn("invalid_manifest", self.codes(self.cli("compare", 1)))
        self.save_task("[invalid URL](http://[broken)\n")
        self.assertIn("invalid_reference", self.codes(self.cli("validate", 1)))

    def test_git_staged_change_with_identical_worktree_bytes(self):
        self.git_init()
        self.write("src/main.py", "changed\n")
        self.cli("snapshot")
        self.git("add", "src/main.py")
        result = self.cli("compare", 1)
        states = {(x["category"], x["field"]): x["state"] for x in result["comparisons"]}
        self.assertEqual(states[("files", "src/main.py")], "unchanged")
        self.assertEqual(states[("git_index", "src/main.py")], "changed")
        self.assertEqual(states[("git_status", "src/main.py")], "changed")

    def test_git_worktree_and_untracked_content_changes(self):
        self.git_init()
        self.write("src/untracked file.py", "untracked original\n")
        self.cli("snapshot")
        manifest = json.loads(self.manifest.read_text())
        self.assertIn("src/untracked file.py", manifest["git"]["untracked"])
        self.write("src/main.py", "modified tracked\n")
        self.write("src/untracked file.py", "untracked changed\n")
        result = self.cli("compare", 1)
        changed_files = {x["field"] for x in result["comparisons"] if x["category"] == "files" and x["state"] == "changed"}
        self.assertTrue({"src/main.py", "src/untracked file.py"} <= changed_files)

    def test_git_ignored_content_and_self_exclusion(self):
        self.scope_data["paths"] = ["."]
        self.save_scope()
        self.write(".gitignore", "src/ignored.py\n")
        self.git_init()
        self.write("src/ignored.py", "ignored sample\n")
        self.cli("snapshot")
        before = self.manifest.read_bytes()
        self.cli("snapshot")
        self.assertEqual(before, self.manifest.read_bytes())
        self.cli("compare")
        manifest = json.loads(before)
        self.assertIn("src/ignored.py", manifest["files"])
        self.assertNotIn("manifest.json", manifest["git"]["untracked"])
        self.assertFalse(any(key.startswith(".git/") for key in manifest["files"]))

    def test_git_commit_change_is_visible(self):
        self.git_init()
        self.cli("snapshot")
        self.git("commit", "--allow-empty", "-qm", "New source revision")
        result = self.cli("compare", 1)
        self.assertTrue(any(x["category"] == "git" and x["field"] == "head" and x["state"] == "changed" for x in result["comparisons"]))

    def test_missing_git_is_runtime_exit_two(self):
        result = self.cli("snapshot", 2, env={**self.base_env, "PATH": ""})
        self.assertIn("runtime_error", self.codes(result))

    def test_damaged_git_marker_is_not_treated_as_non_git(self):
        self.write(".git", "gitdir: /nonexistent-zhiheng-gitdir\n")
        result = self.cli("snapshot", 2)
        self.assertIn("runtime_error", self.codes(result))
        self.assertFalse(self.manifest.exists())

    def test_explicit_invalid_git_dir_rejects_snapshot_and_compare(self):
        self.cli("snapshot")
        original = self.manifest.read_bytes()
        env = {**self.base_env, "GIT_DIR": str(self.root / "nonexistent-gitdir")}
        self.assertIn("runtime_error", self.codes(self.cli("compare", 2, env=env)))
        self.assertEqual(self.manifest.read_bytes(), original)
        self.manifest.unlink()
        self.assertIn("runtime_error", self.codes(self.cli("snapshot", 2, env=env)))
        self.assertFalse(self.manifest.exists())

    def test_valid_external_git_dir_is_observed(self):
        external = self.root.parent / f"{self.root.name}-gitdir"
        self.addCleanup(shutil.rmtree, external, ignore_errors=True)
        self.git("init", "-q", "--separate-git-dir", str(external))
        (self.root / ".git").unlink()
        env = {**self.base_env, "GIT_DIR": str(external), "GIT_WORK_TREE": str(self.root)}
        self.cli("snapshot", env=env)
        self.assertTrue(json.loads(self.manifest.read_text())["git"]["available"])
        self.cli("compare", env=env)

    def test_explicit_empty_git_dir_is_a_runtime_error(self):
        self.cli("snapshot")
        original = self.manifest.read_bytes()
        env = {**self.base_env, "GIT_DIR": ""}
        self.assertIn("runtime_error", self.codes(self.cli("compare", 2, env=env)))
        self.assertEqual(self.manifest.read_bytes(), original)
        self.manifest.unlink()
        self.assertIn("runtime_error", self.codes(self.cli("snapshot", 2, env=env)))
        self.assertFalse(self.manifest.exists())

    def test_invalid_arguments_exit_two_and_json(self):
        result = subprocess.run([sys.executable, "-B", str(SCRIPT), "validate"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)["status"], "error")
        self.assertEqual(result.stderr, "")


if __name__ == "__main__":
    unittest.main()
