#!/usr/bin/env python3
"""Synthetic fixtures only. Every assertion exercises the actual CLI subprocess."""
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2] / "skills/harness-init/assets/project"
sys.path.insert(0, str(PROJECT))
from harness.harness_check import ENV_FIELDS, GITHUB_LIMITS, LOCAL_LIMITS, fingerprint, check_fingerprint, scaffold
from harness.contracts import Validator, evaluate_bundle, schema_errors

SCRIPT = PROJECT / "harness/harness_check.py"


class HarnessCheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bundle_path = self.root / "bundle.json"
        self.bundle = self.fixture()

    def fixture(self, mode="local"):
        bundle = scaffold(mode)
        config = bundle["config"]
        config["repository_id"] = "example/project"
        config["repository_root"] = str(self.root)
        config["environment"] = {
            "host": "Codex CLI 0.0-fixture", "model": "fixture-model", "os": "fixture-linux",
            "git": "2.47.0-fixture", "runtime": "Python 3.11-fixture",
            "skills_revision": "fixture-skills-v1", "skills_path": "skills/harness-init",
            "dependency_lock_sha256": "d" * 64, "stop_method": "fixture-process-group",
            "lock_backend": "fixture-native-lock"}
        config["limits"] = {name: 100 for name in LOCAL_LIMITS}
        config["limits"].update(repair_attempts=2, task_attempts=3, task_seconds=1000)
        config["checks"] = [{"id": "unit", "kind": "test", "argv": ["python3", "-m", "unittest"],
                             "timeout_seconds": 20, "min_executed": 1},
                            {"id": "lint", "kind": "tool", "argv": ["lint-fixture"],
                             "timeout_seconds": 10}]
        if mode == "github":
            config["github"] = {"server": "https://github.com", "repository": "example/project",
                                "gh_version": "fixture-gh", "baseline_policy": "strict"}
            config["limits"].update({name: 100 for name in GITHUB_LIMITS})
            config["limits"]["query_attempts"] = 2
        task = {"id": "task-login", "dependencies": [], "acceptance_ids": ["AC-login", "AC-errors"],
                "reports": {"note": "docs/task-login.html", "walkthrough": "tasks/walkthrough-login.md",
                            "delivery": "docs/delivery-login.md"}}
        bundle["tasks"] = [task]
        cp = {"mode": mode, "repository_id": config["repository_id"], "task_id": task["id"],
              "run_id": "run-one", "attempt_id": "attempt-one", "revision": 7,
              "consumed": {"task_seconds": 12, "attempts_started": 1, "repair_attempts": 0}}
        bundle["checkpoint"] = cp
        binding = {"H": "a" * 40, "T": "b" * 40, "C": "c" * 40, "C_kind": "commit",
                   "spec_sha256": "e" * 64, "checks_sha256": check_fingerprint(config),
                   "environment_sha256": fingerprint(config["environment"]), "task_sha256": fingerprint(task)}
        snap = {key: cp[key] for key in ("mode", "repository_id", "task_id", "run_id", "attempt_id")}
        snap.update(checkpoint_revision=cp["revision"], binding=binding)
        bundle["input"] = copy.deepcopy(snap)
        bundle["input"].update(required_acceptance_ids=task["acceptance_ids"][:], required_check_ids=["unit", "lint"])
        bundle["current"] = copy.deepcopy(snap)
        result = bundle["result"] = copy.deepcopy(snap)
        result.update(stop_reason="completed", unresolved_items=[])
        record = {"run_id": cp["run_id"], "attempt_id": cp["attempt_id"], "binding": binding}
        result["checks"] = []
        for cid, counts in (("unit", {"executed": 4, "passed": 4, "failed": 0, "skipped": 0}),
                            ("lint", {"evaluated": 6, "failed": 0})):
            check = copy.deepcopy(record)
            check.update(id=cid, status="passed", exit_code=0, counts=counts,
                         report=self.report("reports/" + cid + ".txt", cid + " fixture report\n"))
            result["checks"].append(check)
        review = result["review"] = copy.deepcopy(record)
        review.update(status="completed", independent=True, findings=[], unresolved_items=[],
                      report=self.report("reports/review.txt", "Synthetic independent-review fixture\n"))
        result["acceptance"] = [{"id": "AC-login", "status": "passed", "evidence_ids": ["unit", "review"]},
                                {"id": "AC-errors", "status": "passed", "evidence_ids": ["unit", "lint"]}]
        return bundle

    def report(self, path, content):
        file = self.root / path
        file.parent.mkdir(parents=True, exist_ok=True)
        raw = content.encode()
        file.write_bytes(raw)
        return {"path": path, "sha256": hashlib.sha256(raw).hexdigest()}

    def cli(self, command="evidence", expected=0, bundle=None, raw=None):
        if raw is None:
            raw = json.dumps(self.bundle if bundle is None else bundle)
        self.bundle_path.write_text(raw, encoding="utf-8")
        result = subprocess.run([sys.executable, str(SCRIPT), command, "--bundle", str(self.bundle_path)],
                                capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        self.assertEqual(result.stderr, "")
        payload = json.loads(result.stdout)
        self.assertEqual(payload["ok"], expected == 0)
        if expected:
            self.assertEqual(payload["decision"], "blocked")
            self.assertTrue(payload["errors"])
        return payload

    def test_actual_jsonschema_accepts_full_valid_input_and_result(self):
        self.assertEqual(schema_errors(self.bundle["input"], "input"), [])
        self.assertEqual(schema_errors(self.bundle["result"], "result"), [])
        self.assertEqual(evaluate_bundle(self.bundle, "evidence")["decision"],
                         "eligible_for_independent_verification")

    def test_actual_jsonschema_rejects_missing_structural_fields(self):
        for kind, field in (("input", "required_acceptance_ids"), ("result", "review")):
            value = copy.deepcopy(self.bundle[kind])
            del value[field]
            self.assertTrue(schema_errors(value, kind))

    def test_schema_catches_malformed_unresolved_item_extensions(self):
        self.bundle["result"]["unresolved_items"] = [False]
        result = evaluate_bundle(self.bundle, "evidence")
        self.assertFalse(result["ok"])
        self.assertTrue(any(item.get("source") == "jsonschema" for item in result["errors"]))

    def test_repeated_validation_is_idempotent(self):
        validator = Validator(self.bundle)
        self.assertTrue(validator.preflight(), validator.errors)
        self.assertTrue(validator.evidence(), validator.errors)
        self.assertTrue(validator.evidence(), validator.errors)

    def test_valid_local_reports_only_eligibility(self):
        result = self.cli()
        self.assertEqual(result["decision"], "eligible_for_independent_verification")
        self.assertIn("untrusted", result["notice"])
        self.assertNotIn("verified", result)

    def test_valid_github_fixture_no_network_or_gh(self):
        self.cli(bundle=self.fixture("github"))

    def test_preflight_allows_new_run_without_result(self):
        bundle = {key: self.bundle[key] for key in ("version", "config", "tasks")}
        bundle["checkpoint"] = None
        self.assertEqual(self.cli("preflight", bundle=bundle)["decision"], "configuration_consistent")

    def test_scaffolds_are_explicit_incomplete_and_do_not_write(self):
        for mode in ("local", "github"):
            before = sorted(str(p.relative_to(self.root)) for p in self.root.rglob("*"))
            result = subprocess.run([sys.executable, str(SCRIPT), "scaffold", "--mode", mode],
                                    cwd=self.root, capture_output=True, text=True, timeout=5)
            self.assertEqual(result.returncode, 0)
            bundle = json.loads(result.stdout)
            self.assertEqual(bundle["config"]["mode"], mode)
            self.assertEqual(bundle["config"]["environment"]["host"], "")
            self.assertEqual(before, sorted(str(p.relative_to(self.root)) for p in self.root.rglob("*")))
            self.cli("preflight", expected=1, bundle=bundle)

    def test_missing_each_environment_field_blocks(self):
        for name in ENV_FIELDS:
            with self.subTest(name=name):
                b = copy.deepcopy(self.bundle)
                del b["config"]["environment"][name]
                self.cli("preflight", expected=1, bundle=b)

    def test_all_required_limits_reject_missing_zero_negative_bool_nonfinite(self):
        for name in LOCAL_LIMITS:
            for bad in (None, 0, -1, True, float("inf"), "unlimited"):
                with self.subTest(name=name, bad=bad):
                    b = copy.deepcopy(self.bundle)
                    b["config"]["limits"][name] = bad
                    self.cli("preflight", expected=1, bundle=b)

    def test_github_wait_limits_required(self):
        for name in GITHUB_LIMITS:
            b = self.fixture("github")
            del b["config"]["limits"][name]
            self.cli("preflight", expected=1, bundle=b)

    def test_repair_rounds_and_integer_attempts(self):
        for name, val in (("repair_attempts", 3), ("task_attempts", 1.5), ("query_attempts", 1.5)):
            b = self.fixture("github")
            b["config"]["limits"][name] = val
            self.cli("preflight", expected=1, bundle=b)

    def test_cumulative_budget_not_reset(self):
        for key, val in (("task_seconds", 1001), ("attempts_started", 4), ("repair_attempts", 3)):
            b = copy.deepcopy(self.bundle)
            b["checkpoint"]["consumed"][key] = val
            self.cli(expected=1, bundle=b)

    def test_mode_mismatch_and_no_inference(self):
        self.bundle["checkpoint"]["mode"] = "github"
        self.cli("preflight", expected=1)
        del self.bundle["config"]["mode"]
        self.cli("preflight", expected=1)

    def test_numeric_and_duplicate_task_ids(self):
        b = copy.deepcopy(self.bundle)
        b["tasks"][0]["id"] = "123"
        self.cli("preflight", expected=1, bundle=b)
        self.bundle["tasks"].append(copy.deepcopy(self.bundle["tasks"][0]))
        self.cli("preflight", expected=1)

    def test_renamed_task_file_identity_is_not_issue_number(self):
        self.bundle["tasks"][0]["reports"]["note"] = "docs/issue#123.html"
        self.cli("preflight")

    def test_missing_dependency_and_cycles(self):
        self.bundle["tasks"][0]["dependencies"] = ["outside-page"]
        self.cli("preflight", expected=1)
        self.bundle["tasks"][0]["dependencies"] = ["task-login"]
        result = self.cli("preflight", expected=1)
        self.assertTrue(any("cycle" in item["message"] for item in result["errors"]))

    def test_valid_nontrivial_dependency_graph(self):
        second = {"id": "task-api", "acceptance_ids": ["AC-api"], "dependencies": ["task-login"],
                  "reports": {"note": "docs/api.html", "walkthrough": "tasks/api.md", "delivery": "docs/api-delivery.md"}}
        self.bundle["tasks"].append(second)
        self.cli("preflight")
        self.bundle["tasks"][0]["dependencies"] = ["task-api"]
        self.cli("preflight", expected=1)

    def test_unsafe_report_paths(self):
        for bad in ("../outside.md", "/tmp/out.md", "C:/out.md", "docs\\out.md", "docs//out.md",
                    "docs/./out.md", "docs/NUL.txt", "docs/file.md.", "docs/\x7f.md"):
            with self.subTest(bad=bad):
                b = copy.deepcopy(self.bundle)
                b["tasks"][0]["reports"]["note"] = bad
                self.cli("preflight", expected=1, bundle=b)

    def test_casefold_and_ancestor_report_collisions(self):
        for bad in ("DOCS/TASK-LOGIN.HTML", "docs/task-login.html/nested.md"):
            b = copy.deepcopy(self.bundle)
            b["tasks"][0]["reports"]["delivery"] = bad
            self.cli("preflight", expected=1, bundle=b)

    def test_report_symlink_rejected(self):
        (self.root / "linked").symlink_to(self.root / "reports", target_is_directory=True)
        self.bundle["tasks"][0]["reports"]["note"] = "linked/note.md"
        self.cli("preflight", expected=1)

    def test_every_binding_component_rejects_drift(self):
        for name in self.bundle["input"]["binding"]:
            for source in ("current", "result"):
                b = copy.deepcopy(self.bundle)
                b[source]["binding"][name] = "tree" if name == "C_kind" else "f" * len(b[source]["binding"][name])
                self.cli(expected=1, bundle=b)

    def test_configuration_fingerprint_cannot_be_stale(self):
        for which in ("environment", "checks", "limits", "task"):
            b = copy.deepcopy(self.bundle)
            if which == "environment":
                b["config"]["environment"]["git"] = "changed-git"
            elif which == "checks":
                b["config"]["checks"][0]["argv"].append("changed-test-scope")
            elif which == "limits":
                b["config"]["limits"]["task_seconds"] = 2000
            else:
                b["tasks"][0]["acceptance_ids"].append("AC-new")
            self.cli(expected=1, bundle=b)

    def test_stale_revision_run_and_attempt(self):
        for name, val in (("checkpoint_revision", 6), ("run_id", "run-old"), ("attempt_id", "attempt-old")):
            b = copy.deepcopy(self.bundle)
            b["result"][name] = val
            self.cli(expected=1, bundle=b)

    def test_stale_individual_check_and_review(self):
        for record in ("check", "review"):
            b = copy.deepcopy(self.bundle)
            target = b["result"]["checks"][0] if record == "check" else b["result"]["review"]
            target["attempt_id"] = "attempt-old"
            self.cli(expected=1, bundle=b)

    def test_failed_exit_code_cannot_be_green_status(self):
        for val in (1, -9, True, "0"):
            b = copy.deepcopy(self.bundle)
            b["result"]["checks"][0]["exit_code"] = val
            self.cli(expected=1, bundle=b)

    def test_skipped_pending_and_unknown_checks_block(self):
        for status in ("skipped", "pending", "unknown", None):
            b = copy.deepcopy(self.bundle)
            b["result"]["checks"][0]["status"] = status
            self.cli(expected=1, bundle=b)

    def test_zero_tests_skips_failed_and_inconsistent_counts(self):
        for counts in ({"executed": 0, "passed": 0, "failed": 0, "skipped": 0},
                       {"executed": 4, "passed": 4, "failed": 0, "skipped": 1},
                       {"executed": 4, "passed": 3, "failed": 1, "skipped": 0},
                       {"executed": 4, "passed": 5, "failed": 0, "skipped": 0},
                       {"executed": 4, "passed": 4, "skipped": 0}):
            b = copy.deepcopy(self.bundle)
            b["result"]["checks"][0]["counts"] = counts
            self.cli(expected=1, bundle=b)

    def test_tool_zero_evaluation_blocks(self):
        self.bundle["result"]["checks"][1]["counts"]["evaluated"] = 0
        self.cli(expected=1)

    def test_missing_and_duplicate_check_results(self):
        b = copy.deepcopy(self.bundle)
        b["result"]["checks"].pop()
        self.cli(expected=1, bundle=b)
        self.bundle["result"]["checks"].append(copy.deepcopy(self.bundle["result"]["checks"][0]))
        self.cli(expected=1)

    def test_missing_changed_empty_and_large_reports(self):
        file = self.root / "reports/unit.txt"
        for content in (None, b"changed", b"", b"x" * (8 * 1024 * 1024 + 1)):
            if content is None:
                file.unlink()
            else:
                file.write_bytes(content)
            self.cli(expected=1)

    def test_unresolved_blocking_finding(self):
        self.bundle["result"]["review"]["findings"] = [
            {"severity": "Blocking", "summary": "Authentication bypass remains", "resolved": False}]
        self.cli(expected=1)

    def test_pending_or_nonindependent_review(self):
        for name, value in (("status", "pending"), ("independent", False), ("unresolved_items", ["review not finished"])):
            b = copy.deepcopy(self.bundle)
            b["result"]["review"][name] = value
            self.cli(expected=1, bundle=b)

    def test_acceptance_missing_duplicate_or_unknown_evidence(self):
        b = copy.deepcopy(self.bundle)
        b["result"]["acceptance"].pop()
        self.cli(expected=1, bundle=b)
        b = copy.deepcopy(self.bundle)
        b["result"]["acceptance"].append(copy.deepcopy(b["result"]["acceptance"][0]))
        self.cli(expected=1, bundle=b)
        self.bundle["result"]["acceptance"][0]["evidence_ids"] = ["invented"]
        self.cli(expected=1)

    def test_input_cannot_drop_required_acceptance_or_checks(self):
        for name in ("required_acceptance_ids", "required_check_ids"):
            b = copy.deepcopy(self.bundle)
            b["input"][name].pop()
            self.cli(expected=1, bundle=b)

    def test_timeout_cancelled_budget_exhaustion_stop_reasons(self):
        for reason in ("timeout", "cancelled", "budget_exhausted", "unknown"):
            b = copy.deepcopy(self.bundle)
            b["result"]["stop_reason"] = reason
            self.cli(expected=1, bundle=b)

    def test_malformed_json_duplicates_nan_depth_size(self):
        for raw in ('{"version": 1, "version": 1}', '{"x": NaN}', '{"x": 1e9999}', '{', '[' * 40 + '0' + ']' * 40,
                    '{"padding": "' + 'x' * (2 * 1024 * 1024) + '"}'):
            self.cli("preflight", expected=1, raw=raw)

    def test_malformed_structure_fails_without_traceback(self):
        for raw in ('[]', 'null', '{"version":1,"config":null,"tasks":[3],"checkpoint":null}'):
            self.cli("preflight", expected=1, raw=raw)
        self.bundle["checkpoint"]["task_id"] = ["task-login"]
        self.cli("preflight", expected=1)

    def test_read_only_and_deterministic(self):
        self.bundle_path.write_text(json.dumps(self.bundle))
        before = {str(p): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        command = [sys.executable, str(SCRIPT), "evidence", "--bundle", str(self.bundle_path)]
        first = subprocess.run(command, capture_output=True, timeout=5)
        second = subprocess.run(command, capture_output=True, timeout=5)
        self.assertEqual(first.returncode, 0)
        self.assertEqual(first.stdout, second.stdout)
        after = {str(p): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
