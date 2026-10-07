"""用隔离 Git 仓库验证状态与删除边界，不运行真实模型或远端发布。"""

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("workflow_state", Path(__file__).with_name("workflow_state.py"))
wf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wf)


def configuration():
    # 仅测试符号，不是可用模型或推荐配置。
    names = {"design": "测试设计模型", "implementation": "测试实现模型", "review": "测试审查模型"}
    return {
        "confirmed": True, "confirmation": "测试夹具模拟的集中确认", "endpoint": "pr",
        "roles": {role: {"model": name, "effort": "测试强度", "context": "fresh",
                         "rationale": "测试夹具按角色分配"} for role, name in names.items()},
        "stage_roles": {"knowledge": "design", "delivery": "implementation"},
        "capabilities": {"explicit_model": True, "explicit_effort": True,
                         "fresh_context": True, "models": {n: ["测试强度"] for n in names.values()},
                         "max_children": 3, "evidence": "模拟宿主接口，仅供单元测试"},
        "concurrency": 2,
    }


class ConfigTests(unittest.TestCase):
    def test_roles_are_distinct_and_available(self):
        config = configuration()
        wf.validate_config(config)
        config["roles"]["review"]["model"] = config["roles"]["implementation"]["model"]
        with self.assertRaises(wf.WorkflowError):
            wf.validate_config(config)

    def test_capability_and_context_constraints(self):
        for change in ("fresh_context", "explicit_model", "explicit_effort"):
            config = configuration()
            config["capabilities"][change] = False
            with self.assertRaises(wf.WorkflowError):
                wf.validate_config(config)
        config = configuration()
        config["roles"]["review"]["context"] = "inherit"
        with self.assertRaises(wf.WorkflowError):
            wf.validate_config(config)

    def test_unsupported_effort_and_confirmation(self):
        config = configuration()
        config["roles"]["design"]["effort"] = "未支持强度"
        with self.assertRaises(wf.WorkflowError):
            wf.validate_config(config)
        config = configuration()
        config["confirmed"] = False
        with self.assertRaises(wf.WorkflowError):
            wf.validate_config(config)

    def test_initialization_host_uses_dynamic_available_configuration(self):
        config = configuration()
        config["initialization"] = {"wiki_host": dict(config["roles"]["design"])}
        wf.validate_config(config)
        config["initialization"]["wiki_host"]["context"] = "inherit"
        with self.assertRaises(wf.WorkflowError):
            wf.validate_config(config)
        config["initialization"]["wiki_host"] = dict(config["roles"]["design"], model="不可用测试模型")
        with self.assertRaises(wf.WorkflowError):
            wf.validate_config(config)
    def test_dependency_frontier_and_cycle(self):
        tasks = [{"id": "A", "blocked_by": [], "status": "done"},
                 {"id": "B", "blocked_by": ["A"], "status": "pending"}]
        self.assertEqual(wf.validate_tasks(tasks), ["B"])
        tasks[0]["blocked_by"] = ["B"]
        with self.assertRaises(wf.WorkflowError):
            wf.validate_tasks(tasks)

    def test_missing_duplicate_and_unfinished_dependencies(self):
        invalid = [
            [{"id": "A", "blocked_by": ["missing"], "status": "pending"}],
            [{"id": "A", "blocked_by": [], "status": "pending"}] * 2,
            [{"id": "A", "blocked_by": [], "status": "pending"},
             {"id": "B", "blocked_by": ["A"], "status": "running"}],
        ]
        for tasks in invalid:
            with self.assertRaises(wf.WorkflowError):
                wf.validate_tasks(tasks)


class RunTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        self.write("app.py", "value = 1\n")
        wf.git(self.root, "add", "app.py")
        wf.git(self.root, "-c", "user.name=测试", "-c", "user.email=test@example.invalid",
               "commit", "-qm", "初始测试提交")
        wf.init_run(self.root, "demo", configuration())
        self.run = wf.Run(self.root, "demo")

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, path, text):
        file = self.root / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(text, encoding="utf-8")
        return file

    def temporary(self, name, targets=None, text="临时草稿"):
        relative = self.run.relative + "/scratch/" + name
        wf.register(self.run, relative, "temporary", "本次测试临时材料", targets or [])
        self.write(relative, text)
        wf.seal(self.run, relative, None)
        return relative

    def ready_for_cleanup(self, knowledge="complete"):
        evidence = self.run.relative + "/verification.md"
        receipt = self.run.relative + "/wiki-receipt.json"
        summary = self.run.relative + "/summary.md"
        self.write(evidence, "模拟验收证据；没有真实业务检查")
        self.write(receipt, json.dumps({"status": knowledge}))
        self.write(summary, "测试交付摘要")
        wf.checkpoint(self.run, {
            "phase": "cleaning", "tasks": [{"id": "A", "blocked_by": [], "status": "done"}],
            "retained_paths": [evidence, receipt, summary],
            "verification": {"status": "passed", "evidence": [evidence]},
            "knowledge": {"status": knowledge, "evidence": [receipt]},
            "delivery": {"status": "pr_created", "pr_url": "https://example.invalid/pr/1",
                         "commit": wf.git(self.root, "rev-parse", "HEAD")},
        })

    def test_resume_fingerprint_observes_dirty_and_new_files(self):
        before = wf.snapshot(self.root)
        self.write("app.py", "value = 2\n")
        self.assertNotEqual(before, wf.snapshot(self.root))
        self.write("app.py", "value = 1\n")
        self.write("new.py", "pass\n")
        self.assertNotEqual(before, wf.snapshot(self.root))

    def test_workflow_scratch_is_not_source_drift(self):
        before = wf.snapshot(self.root)
        self.temporary("draft.md")
        self.assertEqual(before, wf.snapshot(self.root))

    def test_ignored_spec_and_tasks_are_still_versioned_inputs(self):
        self.write(".gitignore", ".workflow/\n")
        spec = self.run.relative + "/spec.md"
        task = self.run.relative + "/tasks/01.md"
        self.write(spec, "已确认规格")
        self.write(task, "原任务")
        before = wf.snapshot(self.root)
        self.write(spec, "新规格")
        self.assertNotEqual(before, wf.snapshot(self.root))
        self.write(spec, "已确认规格")
        self.write(task, "更新后的任务")
        self.assertNotEqual(before, wf.snapshot(self.root))
        self.write(task, "原任务")
        self.write(self.run.relative + "/handoffs/temporary.md", "临时交接")
        self.assertEqual(before, wf.snapshot(self.root))

    def test_checkpoint_invalidates_old_success_after_source_change(self):
        self.ready_for_cleanup()
        self.write("app.py", "value = 2\n")
        wf.checkpoint(self.run, {"phase": "verifying"})
        self.assertEqual(self.run.state["verification"], {})
        self.assertEqual(self.run.state["knowledge"], {})

    def test_cleanup_preview_apply_and_retry(self):
        path = self.temporary("draft.md", ["openwiki/runtime.md"])
        self.write("openwiki/runtime.md", "已落盘的测试知识")
        self.ready_for_cleanup()
        result = wf.cleanup(self.run)
        self.assertEqual(result["files"][0]["status"], "eligible")
        self.assertTrue((self.root / path).exists())
        self.assertEqual(wf.cleanup(self.run, True)["files"][0]["status"], "deleted")
        reloaded = wf.Run(self.root, "demo")
        self.assertEqual(wf.cleanup(reloaded, True)["files"][0]["status"], "deleted")
        self.assertTrue((self.root / reloaded.relative / "state.json").exists())

    def test_cleanup_keeps_user_file_and_changed_draft(self):
        user = self.write(self.run.relative + "/scratch/user.md", "用户已有文件")
        with self.assertRaises(wf.WorkflowError):
            wf.register(self.run, user.relative_to(self.root).as_posix(), "temporary", "不能认领", [])
        path = self.temporary("draft.md")
        self.write(path, "封存后出现的新成果")
        self.ready_for_cleanup()
        self.assertEqual(wf.cleanup(self.run, True)["files"][0]["status"], "retained")
        self.assertTrue(user.exists())
        self.assertTrue((self.root / path).exists())

    def test_references_and_claims_prevent_deletion(self):
        for reference in ("markdown", "reference", "claim"):
            path = self.temporary(reference + ".md")
            if reference == "markdown":
                self.write("docs/kept.md", f"[证据](../{path})")
            elif reference == "reference":
                self.write("docs/reference.md", f"[证据][proof]\n\n[proof]: ../{path}")
            else:
                self.write("openwiki/.claims/evidence.json", json.dumps({"resource": "repo://" + path}))
        self.ready_for_cleanup()
        self.assertTrue(all(x["status"] == "retained" for x in wf.cleanup(self.run, True)["files"]))

    def test_absolute_parenthesized_image_and_html_links_are_preserved(self):
        absolute = self.temporary("absolute.md")
        parentheses = self.temporary("draft(v1).md")
        image = self.temporary("image.png")
        html = self.temporary("html.txt")
        text = (f"[绝对引用]({self.root / absolute})\n"
                f"[括号路径](../{parentheses})\n"
                f"![图片](../{image})\n"
                f'<a href="../{html}">HTML 引用</a>')
        self.write("docs/kept.md", text)
        self.ready_for_cleanup()
        self.assertTrue(all(x["status"] == "retained" for x in wf.cleanup(self.run, True)["files"]))

    def test_document_symlink_is_read_without_blocking_unrelated_cleanup(self):
        path = self.temporary("draft.md")
        self.write("README.md", "没有临时文件引用")
        (self.root / "guide.md").symlink_to("README.md")
        self.ready_for_cleanup()
        self.assertEqual(wf.cleanup(self.run, True)["files"][0]["status"], "deleted")
        self.assertFalse((self.root / path).exists())
        self.assertTrue((self.root / "guide.md").is_symlink())

    def test_reference_matches_actual_identity_on_case_insensitive_filesystem(self):
        path = self.temporary("MixedCase.md")
        if not (self.root / path.lower()).exists():
            self.skipTest("当前文件系统大小写敏感，等价名称场景不适用")
        self.write("docs/kept.md", f"[有效引用](../{path.lower()})")
        self.ready_for_cleanup()
        self.assertEqual(wf.cleanup(self.run, True)["files"][0]["status"], "retained")
        self.assertTrue((self.root / path).exists())

    def test_retained_draft_does_not_lose_its_reference(self):
        child = self.temporary("child.md")
        parent = self.temporary("parent.md", text="[后续材料](child.md)")
        self.write(parent, "[后续材料](child.md)\n新增未提炼内容")
        self.ready_for_cleanup()
        statuses = {x["path"]: x["status"] for x in wf.cleanup(self.run, True)["files"]}
        self.assertEqual(statuses[child], "retained")
        self.assertEqual(statuses[parent], "retained")

    def test_knowledge_failure_blocks_cleanup(self):
        self.temporary("draft.md")
        self.ready_for_cleanup()
        self.run.state["knowledge"]["status"] = "pending"
        with self.assertRaises(wf.WorkflowError):
            wf.cleanup(self.run, True)

    def test_missing_stable_target_retains_draft(self):
        path = self.temporary("draft.md", ["openwiki/missing.md"])
        self.ready_for_cleanup()
        self.assertEqual(wf.cleanup(self.run, True)["files"][0]["status"], "retained")
        self.assertTrue((self.root / path).exists())

    def test_new_source_changes_block_cleanup(self):
        self.temporary("draft.md")
        self.ready_for_cleanup()
        self.write("app.py", "value = 3\n")
        with self.assertRaises(wf.WorkflowError):
            wf.cleanup(self.run, True)

    def test_path_escape_and_symlink_are_rejected(self):
        for path in ("../outside.md", "/tmp/outside.md", ".git/config", "a/../b"):
            with self.assertRaises(wf.WorkflowError):
                wf.safe_path(self.root, path)
        (self.root / "linked").symlink_to(self.root / "app.py")
        with self.assertRaises(wf.WorkflowError):
            wf.safe_path(self.root, "linked")
        (self.root / "linked-dir").symlink_to(self.root / ".workflow", target_is_directory=True)
        with self.assertRaises(wf.WorkflowError):
            wf.safe_path(self.root, "linked-dir/runs/demo/state.json")

    def test_interrupted_delete_is_recoverable(self):
        path = self.temporary("draft.md")
        self.ready_for_cleanup()
        real_unlink = Path.unlink
        def fail_after_delete(file, *args, **kwargs):
            real_unlink(file, *args, **kwargs)
            if file == self.root / path:
                raise OSError("模拟 unlink 后中断")
        with patch.object(Path, "unlink", fail_after_delete):
            with self.assertRaises(OSError):
                wf.cleanup(self.run, True)
        loaded = wf.Run(self.root, "demo")
        self.assertEqual(wf.cleanup(loaded, True)["files"][0]["status"], "deleted")

    def test_config_tamper_and_duplicate_init_are_rejected(self):
        with self.assertRaises(wf.WorkflowError):
            wf.init_run(self.root, "demo", configuration())
        config = configuration()
        config["concurrency"] = 1
        wf.atomic_json(self.run.config_path, config)
        with self.assertRaises(wf.WorkflowError):
            wf.Run(self.root, "demo")

    def test_cli_reconfigure_recovers_interrupted_config_replacement(self):
        config = configuration()
        config["concurrency"] = 1
        wf.atomic_json(self.run.config_path, config)
        # 模拟配置替换完成、状态替换尚未完成；重复应用已确认矩阵应可恢复。
        script = Path(__file__).with_name("workflow_state.py")
        result = subprocess.run(["python3", "-B", str(script), "reconfigure", "--root", str(self.root),
                                 "--run-id", "demo", "--config", str(self.run.config_path)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        loaded = wf.Run(self.root, "demo")
        self.assertEqual(loaded.state["phase"], "verifying")
        self.assertEqual(loaded.state["verification"], {})
        self.assertTrue(loaded.state["config_revisions"][-1]["interrupted_change"])

    def test_complete_requires_cleanup_results(self):
        self.temporary("draft.md")
        self.ready_for_cleanup()
        with self.assertRaises(wf.WorkflowError):
            wf.checkpoint(self.run, {"phase": "complete"})
        self.assertEqual(self.run.state["phase"], "cleaning")
        wf.cleanup(self.run, True)
        wf.checkpoint(self.run, {"phase": "complete"})
        self.assertEqual(wf.Run(self.root, "demo").state["phase"], "complete")

    def test_cli_resume_reports_changes(self):
        self.write("app.py", "value = 4\n")
        result = subprocess.run(["python3", "-B", str(Path(__file__).with_name("workflow_state.py")),
                                 "resume", "--root", str(self.root), "--run-id", "demo"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(json.loads(result.stdout)["verification_stale"])

    def test_interrupted_init_can_retry_same_run_id(self):
        original = wf.atomic_json
        def interrupt_before_state(path, value):
            if path.name == "state.json":
                raise KeyboardInterrupt("模拟 init 发布前中断")
            return original(path, value)
        with patch.object(wf, "atomic_json", interrupt_before_state):
            with self.assertRaises(KeyboardInterrupt):
                wf.init_run(self.root, "second", configuration())
        self.assertFalse((self.root / ".workflow/runs/second").exists())
        wf.init_run(self.root, "second", configuration())
        self.assertEqual(wf.Run(self.root, "second").state["phase"], "planning")


if __name__ == "__main__":
    unittest.main(verbosity=2)
