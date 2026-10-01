"""Private-repository compatibility via simulated APIs; no private repo created."""
from pathlib import Path
import sys
import unittest
import subprocess
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_github_probe as probes
import test_capabilities_audit as receipts
import test_github as adapters
from harness.capabilities import record_capabilities, require_capabilities, REQUIRED_LIVE
from harness.runtime import Controller
from harness.github import GitHubAdapter, AdapterError


class PrivateProbeAudit(unittest.TestCase):
    behavior = probes.GitHubP0Tests.behavior
    run_probe = probes.GitHubP0Tests.run_probe

    def setUp(self):
        probes.GitHubP0Tests.setUp(self)
        source = self.executable.read_text().replace("'full_name':'example/project'", "'private':True,'full_name':'example/project'")
        source = source.replace("simulated rules inaccessible", "HTTP 403: rules endpoint unavailable to private fixture")
        self.executable.write_text(source)

    def test_private_rules_403_preserves_task_pr_ci_capabilities(self):
        self.behavior(rules_error=True)
        result = self.run_probe()
        self.assertEqual(result["status"], "verified")
        self.assertEqual(result["automatic_merge_rules"]["status"], "blocked")
        self.assertIn("403", result["automatic_merge_rules"]["detail"])
        self.assertNotIn("server_rules", result["observations"], "inaccessible rules must not become an empty verified ruleset")
        self.assertTrue(result["observations"]["pull_requests"]["read_sample_observed"])
        self.assertTrue(result["observations"]["target_checks"]["all_required_passed"])

    def test_private_missing_rules_keeps_handoff_without_claiming_enforcement(self):
        self.behavior(missing_rules=True)
        result = self.run_probe()
        self.assertEqual(result["status"], "verified")
        self.assertEqual(result["automatic_merge_rules"]["status"], "blocked")
        self.assertNotIn("403", result["automatic_merge_rules"]["detail"])

    def test_review_only_private_mode_never_queries_rule_settings(self):
        self.config["github"]["baseline_policy"] = "review_only"
        self.behavior(rules_error=True)
        result = self.run_probe()
        self.assertEqual(result["status"], "verified")
        self.assertEqual(result["automatic_merge_rules"]["status"], "not_applicable")
        self.assertNotIn("/rules/branches/", (self.executable.parent / "calls.jsonl").read_text())


class PrivateReceiptAudit(unittest.TestCase):
    setUp = receipts.CapabilitiesAudit.setUp
    commit = receipts.CapabilitiesAudit.commit
    tearDown = receipts.CapabilitiesAudit.tearDown

    def controller(self):
        return Controller(self.root, "github", "private-receipt", dict(self.config["limits"]))

    def test_missing_auto_merge_is_not_global_github_readiness_failure(self):
        self.config["mode"] = "github"
        self.config["github"] = {"repository": "fixture/private", "server": "https://github.com",
                                 "baseline_policy": "review_only", "required_checks": ["unit"]}
        (self.root / "semantic-review.md").write_text("# Explicit fixture operator review\nSources checked; mock P0 only.\n")
        self.commit("private capability fixture review")
        capabilities = {name: {"status": "verified", "fixture": "mocked P0"} for name in REQUIRED_LIVE}
        capabilities["github_authenticated_capabilities"] = {"status": "verified"}
        observed = {"capabilities": capabilities, "github_probe": {"status": "verified",
            "observations": {"repository": {"private": True}},
            "automatic_merge_rules": {"status": "blocked", "detail": "HTTP 403 private fixture"}}}
        with self.controller() as controller, patch("harness.p0.probe", return_value=observed):
            receipt = record_capabilities(controller, self.config, "live", "semantic-review.md", True)
            self.assertEqual(receipt["status"], "ready")
            self.assertEqual(require_capabilities(controller, self.config)["status"], "ready")
            self.assertEqual(receipt["observations"]["github_probe"]["automatic_merge_rules"]["status"], "blocked")


class NativeRuleAuthorityAudit(unittest.TestCase):
    def adapter(self, declaration, native_rules):
        routes = adapters.GitHubTests().checks_routes()
        routes["repos/o/r/rules/branches/main?per_page=100"] = native_rules
        routes["merge"] = subprocess.CompletedProcess([], 0, "", "")
        fixture = adapters.Fixture(routes)
        config = {"repository": "o/r", "github": {"merge_policy": "strict", "required_checks": ["test"]}}
        if declaration is not None:
            config["github"]["rules_verified"] = declaration
        return GitHubAdapter(config, fixture), fixture

    def evidence(self):
        return dict(status="pass", source_sha="source", target_sha="target",
                    checked_sha="source", baseline_verified=True)

    def test_actual_native_rules_work_without_a_true_declaration_flag(self):
        rules = [[{"type": "required_status_checks", "parameters": {
            "strict_required_status_checks_policy": True, "required_status_checks": [{"context": "test"}]}}]]
        for declaration in (None, False):
            with self.subTest(declaration=declaration):
                adapter, calls = self.adapter(declaration, rules)
                self.assertEqual(adapter.request_merge(8, self.evidence(), "target", True)["status"], "delivery_pending")
                self.assertTrue(any("merge" in argv for argv, _ in calls.calls))

    def test_true_declaration_cannot_bypass_native_rules_403(self):
        error = subprocess.CompletedProcess([], 1, "", "HTTP 403: private rule access unavailable")
        adapter, calls = self.adapter(True, error)
        with self.assertRaisesRegex(AdapterError, "403"):
            adapter.request_merge(8, self.evidence(), "target", True)
        self.assertFalse(any("merge" in argv for argv, _ in calls.calls))

    def test_true_declaration_cannot_bypass_absent_native_rules(self):
        adapter, calls = self.adapter(True, [[]])
        with self.assertRaises(AdapterError):
            adapter.request_merge(8, self.evidence(), "target", True)
        self.assertFalse(any("merge" in argv for argv, _ in calls.calls))


if __name__ == "__main__":
    unittest.main(verbosity=2)
