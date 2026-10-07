"""隔离项目验证接入保护与恢复；上游安装器、Wiki 与模型明确使用测试替身。"""

import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch


entry = importlib.util.spec_from_file_location("project_init", Path(__file__).with_name("project_init.py"))
pi = importlib.util.module_from_spec(entry)
entry.loader.exec_module(pi)


class OnboardingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="dl-onboarding-test-")
        self.base = Path(self.temporary.name).resolve()
        self.root = self.base / "project"
        self.root.mkdir()
        (self.root / "src.txt").write_text("业务代码\n", encoding="utf-8")
        self.bundle = self.base / "bundle"
        self.upstream = self.base / "upstream"
        self.upstream.mkdir()
        self.spec = pi.manifest()
        (self.upstream / "LICENSE").write_text("隔离测试许可证\n")
        for name, group in self.spec["skills"].items():
            directory = self.upstream / "skills" / group / name
            directory.mkdir(parents=True)
            (directory / "SKILL.md").write_text(f"---\nname: {name}\n---\n中文测试方法。\n")
            (directory / "references.md").write_text("引用的测试内容\n")
        for name in self.spec["bundle"]:
            directory = self.bundle / name
            directory.mkdir(parents=True)
            (directory / "SKILL.md").write_text(f"---\nname: {name}\n---\n中文测试阶段。\n")
        self.git(self.upstream, "init")
        self.git(self.upstream, "add", ".")
        self.git(self.upstream, "-c", "user.name=接入测试", "-c", "user.email=test@example.invalid", "commit", "-m", "隔离测试源")
        self.spec["revision"] = self.git(self.upstream, "rev-parse", "HEAD").strip()
        self.wiki_skill = self.base / "OpenWiki-SKILL.md"
        self.wiki_skill.write_text("明确模拟的 OpenWiki 入口\n")
        self.installer = self.base / "simulated_installer.py"
        self.installer.write_text(
            "import argparse, pathlib, shutil\n"
            "p=argparse.ArgumentParser()\n"
            "p.add_argument('--repo'); p.add_argument('--ref'); p.add_argument('--path', nargs='+'); p.add_argument('--dest')\n"
            "a=p.parse_args()\n"
            f"source=pathlib.Path({str(self.upstream)!r})\n"
            "for rel in a.path:\n"
            " shutil.copytree(source/rel, pathlib.Path(a.dest)/pathlib.Path(rel).name)\n"
        )
        self.manifest_patch = patch.object(pi, "manifest", return_value=self.spec)
        self.manifest_patch.start()
        self.addCleanup(self.manifest_patch.stop)
        self.real_command = pi.command

        def local_command(args, timeout=180):
            args = list(args)
            if args[:2] == ["git", "clone"]:
                args[-2] = str(self.upstream)
            return self.real_command(args, timeout)

        self.command_patch = patch.object(pi, "command", side_effect=local_command)
        self.command_patch.start()
        self.addCleanup(self.command_patch.stop)
        self.addCleanup(self.temporary.cleanup)

    @staticmethod
    def git(root, *args):
        return subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                              check=True, text=True).stdout

    def prepare(self, root=None):
        project = pi.Project(root or self.root)
        result = project.prepare(self.bundle, self.installer, self.wiki_skill, init_git=True)
        return project, result

    def ready_local(self):
        project, _ = self.prepare()
        project.instructions("项目代码在 src.txt。使用中文，按实际测试配置验证。\n".encode())
        self.assertTrue(project.status()["local_ready"])
        return project

    def wiki_files(self):
        (self.root / "openwiki").mkdir(exist_ok=True)
        (self.root / "openwiki/quickstart.md").write_text("明确模拟的 Wiki 页面，只有测试用途。\n")
        path = self.root / "AGENTS.md"
        path.write_bytes(path.read_bytes() + b"\n" + pi.WIKI_START + b"\nSIMULATED\n" + pi.WIKI_END + b"\n")

    def receipt(self, status="complete"):
        return {"root": str(self.root), "status": status,
                "operation": "openwiki_finish" if status == "complete" else "openwiki_begin",
                "tool_response": {"status": status, "simulated": True},
                "evidence": "明确模拟的 Host 回执，未调用实际 Wiki 或模型",
                "host": {"model": "测试模型", "effort": "测试强度", "context": "fresh", "confirmed": True,
                         "rationale": "测试夹具，无推荐意义", "confirmation": "模拟确认",
                         "capability_evidence": "模拟能力来源"}}

    def baseline(self):
        self.git(self.root, "add", "src.txt")
        self.git(self.root, "-c", "user.name=接入测试", "-c", "user.email=test@example.invalid", "commit", "-m", "测试基线")

    def test_status_is_read_only_without_git(self):
        project = pi.Project(self.root)
        self.assertFalse(project.status()["initialized"])
        self.assertFalse((self.root / ".workflow").exists())
        self.assertFalse((self.root / ".git").exists())

    def test_damaged_state_returns_structured_error_without_modification(self):
        path = self.root / ".workflow/project.json"
        path.parent.mkdir()
        values = [[], {"schema": 1, "root": str(self.root), "bundle": [], "managed_files": {},
                       "wiki": {}, "conflicts": []}]
        for value in values:
            path.write_text(json.dumps(value))
            before = path.read_bytes()
            result = subprocess.run(["python3", "-B", str(Path(pi.__file__).resolve()), "status", "--root", str(self.root)],
                                    text=True, capture_output=True)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(result.stdout)["status"], "error")
            self.assertNotIn("Traceback", result.stderr)
            self.assertEqual(path.read_bytes(), before)

    def test_install_all_fixed_skills_and_preserve_license(self):
        project, result = self.prepare()
        self.assertEqual(len(project.state["installed_skills"]), 15)
        self.assertEqual(len(project.state["bundle"]), 9)
        self.assertTrue((self.root / ".agents/vendor/mattpocock-skills/LICENSE").is_file())
        self.assertTrue(result["needs_git_baseline"])
        self.assertFalse(result["ready_for_worktrees"])
        self.assertFalse(list((self.root / ".workflow/onboarding/tmp").iterdir()))
        self.assertFalse((self.base / ".codex").exists())

    def test_repeat_prepare_is_idempotent_and_does_not_reinstall(self):
        project = self.ready_local()
        before = (self.root / "AGENTS.md").read_bytes()
        self.installer.unlink()  # 没有缺项时不需要安装器再次运行。
        project, _ = self.prepare()
        self.assertTrue(project.status()["local_ready"])
        self.assertEqual((self.root / "AGENTS.md").read_bytes(), before)

    def test_compatible_existing_skills_are_reused(self):
        folder = self.root / ".agents/skills/tdd"
        shutil.copytree(self.upstream / "skills/engineering/tdd", folder)
        inode = folder.stat().st_ino
        project, _ = self.prepare()
        self.assertIn("tdd", project.state["installed_skills"])
        self.assertEqual(folder.stat().st_ino, inode)

    def test_conflicting_skill_is_preserved_and_missing_ones_installed(self):
        folder = self.root / ".agents/skills/tdd"
        folder.mkdir(parents=True)
        (folder / "SKILL.md").write_text("用户自己的 TDD\n")
        project, result = self.prepare()
        self.assertEqual((folder / "SKILL.md").read_text(), "用户自己的 TDD\n")
        self.assertEqual(len(project.state["installed_skills"]), 14)
        self.assertEqual(result["phase"], "conflict")
        self.assertFalse(result["local_ready"])

    def test_partial_install_resumes_and_failed_stage_is_removed(self):
        project, _ = self.prepare()
        shutil.rmtree(self.root / ".agents/skills/tdd")
        shutil.rmtree(self.root / ".agents/skills/research")
        original = self.installer.read_text()
        self.installer.write_text(original + "\nraise SystemExit(1)\n")
        with self.assertRaises(pi.wf.WorkflowError):
            self.prepare()
        self.assertFalse((self.root / ".agents/skills/tdd").exists())
        self.assertFalse(list((self.root / ".workflow/onboarding/tmp").iterdir()))
        self.installer.write_text(original)
        project, _ = self.prepare()
        project.instructions("恢复测试项目\n".encode())
        self.assertTrue(project.status()["local_ready"])

    def test_existing_agents_and_wiki_block_preserved_byte_for_byte(self):
        old = b"user text\r\n\r\n" + pi.WIKI_START + b"\nold Wiki\n" + pi.WIKI_END + b"\r\n"
        (self.root / "AGENTS.md").write_bytes(old)
        project, _ = self.prepare()
        project.instructions("中文项目规则\n".encode())
        current = (self.root / "AGENTS.md").read_bytes()
        self.assertTrue(current.startswith(old))
        project.instructions("更新中文项目规则\n".encode())
        self.assertTrue((self.root / "AGENTS.md").read_bytes().startswith(old))

    def test_user_modified_or_deleted_owned_block_is_not_overwritten(self):
        project = self.ready_local()
        path = self.root / "AGENTS.md"
        data = path.read_bytes().replace("项目代码".encode(), "用户改写".encode())
        path.write_bytes(data)
        with self.assertRaises(pi.wf.WorkflowError):
            project.instructions("新版规则".encode())
        self.assertEqual(path.read_bytes(), data)
        path.write_bytes(b"user removed block\n")
        with self.assertRaises(pi.wf.WorkflowError):
            project.instructions("新版规则".encode())
        self.assertEqual(path.read_bytes(), b"user removed block\n")

    def test_malformed_or_unowned_blocks_fail_safely(self):
        for value in (pi.START + b"\nunclosed", pi.START + b"\nunknown\n" + pi.END,
                      pi.START + pi.START + pi.END):
            path = self.root / "AGENTS.md"
            path.write_bytes(value)
            with self.assertRaises(pi.wf.WorkflowError):
                pi.Project(self.root).instructions("新正文".encode())
            self.assertEqual(path.read_bytes(), value)

    def test_first_block_write_interruption_recovers(self):
        project, _ = self.prepare()
        with patch.object(pi, "atomic_bytes", side_effect=OSError("模拟落盘中断")):
            with self.assertRaises(OSError):
                project.instructions("新项目正文".encode())
        recovered = pi.Project(self.root)
        recovered.instructions("新项目正文".encode())
        self.assertTrue(recovered.status()["local_ready"])

    def test_block_post_write_interruption_recovers(self):
        project = self.ready_local()
        original_save = project.save
        count = 0

        def save_once():
            nonlocal count
            count += 1
            if count == 2:
                raise OSError("模拟写完正文后中断")
            original_save()

        with patch.object(project, "save", side_effect=save_once):
            with self.assertRaises(OSError):
                project.instructions("新版项目正文".encode())
        recovered = pi.Project(self.root)
        recovered.instructions("新版项目正文".encode())
        self.assertTrue(recovered.status()["local_ready"])

    def test_user_dependency_config_conflict_is_preserved(self):
        path = self.root / ".workflow/dependencies.json"
        path.parent.mkdir()
        original = {"mattpocock_root": str(self.base / "user-source"), "user_setting": "必须保留"}
        path.write_text(json.dumps(original))
        with self.assertRaises(pi.wf.WorkflowError):
            self.prepare()
        self.assertEqual(json.loads(path.read_text()), original)

    def test_dependency_write_interruption_recovers(self):
        self.ready_local()
        project = pi.Project(self.root)
        # 单独拦截依赖文件，接入记录仍可持久化。
        original = pi.wf.atomic_json
        def interrupted(path, value):
            if path.name == "dependencies.json":
                raise OSError("模拟依赖替换中断")
            return original(path, value)
        with patch.object(pi.wf, "atomic_json", side_effect=interrupted):
            with self.assertRaises(OSError):
                project.dependencies(self.root / ".agents/vendor/mattpocock-skills", self.wiki_skill, self.spec)
        project, _ = self.prepare()
        self.assertTrue(project.status()["local_ready"])

    def test_ignore_rules_preserve_existing_content_and_sources(self):
        (self.root / ".gitignore").write_bytes(b"# user\nnode_modules/\n")
        (self.root / ".openwikiignore").write_bytes(b"# user wiki rule\nfixtures/\n")
        project, _ = self.prepare()
        self.assertTrue((self.root / ".gitignore").read_bytes().startswith(b"# user\nnode_modules/\n"))
        self.assertTrue((self.root / ".openwikiignore").read_bytes().startswith(b"# user wiki rule\nfixtures/\n"))
        self.assertEqual(self.git(self.root, "check-ignore", ".agents/skills/tdd/SKILL.md").strip(), ".agents/skills/tdd/SKILL.md")
        self.assertNotIn("/src.txt", (self.root / ".openwikiignore").read_text())

    def test_later_negation_of_installed_paths_is_detected(self):
        project = self.ready_local()
        path = self.root / ".gitignore"
        path.write_bytes(path.read_bytes() + b"!/.agents/skills/tdd/\n")
        self.assertFalse(project.status()["local_ready"])

    def test_ignored_workflow_specs_are_source_inputs(self):
        project = self.ready_local()
        self.wiki_files()
        file = self.root / ".workflow/runs/example/spec.md"
        file.parent.mkdir(parents=True)
        file.write_text("已确认中文规格\n")
        ignore = self.root / ".gitignore"
        ignore.write_bytes(ignore.read_bytes() + b"/.workflow/runs/\n")
        project.record_wiki(self.receipt())
        file.write_text("修改后规格\n")
        self.assertFalse(project.status()["wiki_ready"])

    def test_workflow_state_and_handoffs_do_not_invalidate_wiki(self):
        project = self.ready_local()
        self.wiki_files()
        project.record_wiki(self.receipt())
        run = self.root / ".workflow/runs/example"
        (run / "scratch").mkdir(parents=True)
        (run / "handoffs").mkdir()
        for path in (run / "state.json", run / "config.json", run / "scratch/debug.md", run / "handoffs/task.md"):
            path.write_text("运行中间状态\n")
        self.assertTrue(project.status()["wiki_ready"])

    def test_bundle_source_project_is_not_hidden(self):
        self.git(self.root, "init")
        local_bundle = self.root / ".agents/skills"
        shutil.copytree(self.bundle, local_bundle)
        project = pi.Project(self.root)
        project.prepare(local_bundle, self.installer, self.wiki_skill)
        ignored = (self.root / ".openwikiignore").read_text()
        self.assertNotIn("/.agents/skills/dl-init/", ignored)
        self.assertIn("/.agents/skills/tdd/", ignored)

    def test_local_openwiki_entry_is_reused_and_excluded(self):
        project = self.ready_local()
        path = self.root / ".agents/skills/openwiki/SKILL.md"
        path.parent.mkdir(parents=True)
        path.write_text("明确模拟的项目级 OpenWiki 集成\n")
        project.prepare(self.bundle, self.installer, path)
        deps = pi.wf.read_json(self.root / ".workflow/dependencies.json")
        self.assertEqual(deps["openwiki_skill"], str(path))
        self.assertIn("/.agents/skills/openwiki/", (self.root / ".openwikiignore").read_text())
        self.assertTrue(project.status()["local_ready"])

    def test_wiki_complete_and_unborn_readiness_are_distinct(self):
        project = self.ready_local()
        self.wiki_files()
        result = project.record_wiki(self.receipt())
        self.assertTrue(result["initialized"])
        self.assertTrue(result["needs_git_baseline"])
        self.assertFalse(result["ready_for_worktrees"])
        self.baseline()
        self.assertTrue(pi.Project(self.root).status()["ready_for_worktrees"])

    def test_wiki_noop_and_repeated_record_do_not_edit_wiki(self):
        project = self.ready_local()
        self.wiki_files()
        previous = (self.root / "openwiki/quickstart.md").read_bytes()
        self.assertTrue(project.record_wiki(self.receipt("noop"))["wiki_ready"])
        self.assertTrue(project.record_wiki(self.receipt("noop"))["wiki_ready"])
        self.assertEqual((self.root / "openwiki/quickstart.md").read_bytes(), previous)

    def test_wiki_reload_checkpoint_then_resume(self):
        project = self.ready_local()
        result = project.record_wiki({"root": str(self.root), "status": "awaiting_host_reload",
                                      "evidence": "模拟：项目集成已安装，需宿主重新加载"})
        self.assertEqual(result["phase"], "awaiting_host_reload")
        self.assertFalse(result["wiki_ready"])
        self.wiki_files()
        result = pi.Project(self.root).record_wiki(self.receipt())
        self.assertTrue(result["wiki_ready"])

    def test_fake_success_wrong_operation_or_missing_files_rejected(self):
        project = self.ready_local()
        with self.assertRaises(pi.wf.WorkflowError):
            project.record_wiki(self.receipt())
        self.wiki_files()
        receipt = self.receipt()
        receipt["operation"] = "openwiki_next_page"
        with self.assertRaises(pi.wf.WorkflowError):
            project.record_wiki(receipt)
        receipt = self.receipt()
        receipt["host"]["confirmed"] = False
        with self.assertRaises(pi.wf.WorkflowError):
            project.record_wiki(receipt)

    def test_source_and_user_instructions_change_make_wiki_stale(self):
        project = self.ready_local()
        self.wiki_files()
        project.record_wiki(self.receipt())
        path = self.root / "src.txt"
        path.write_text("业务代码已修改\n")
        self.assertFalse(project.status()["wiki_ready"])
        project.record_wiki(self.receipt())
        path = self.root / "AGENTS.md"
        path.write_bytes(b"user policy change\n" + path.read_bytes())
        self.assertFalse(project.status()["wiki_ready"])

    def test_edited_installed_reference_is_detected(self):
        project = self.ready_local()
        (self.root / ".agents/skills/tdd/references.md").write_text("用户修改的参考方法")
        self.assertFalse(project.status()["local_ready"])
        with self.assertRaises(ValueError):
            pi.wf.preflight(pi.wf.read_json(self.root / ".workflow/dependencies.json"))

    def test_missing_bundle_and_symlink_paths_rejected(self):
        shutil.rmtree(self.bundle / "dl-resume")
        with self.assertRaises(pi.wf.WorkflowError):
            self.prepare()
        outside = self.base / "outside"
        outside.mkdir()
        (self.root / ".workflow").rename(self.base / "previous-state")
        (self.root / ".workflow").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(pi.wf.WorkflowError):
            pi.Project(self.root)
        self.assertFalse(list(outside.iterdir()))

    def test_parent_repo_is_not_nested_initialized(self):
        self.git(self.root, "init")
        child = self.root / "child"
        child.mkdir()
        with self.assertRaises(pi.wf.WorkflowError):
            pi.Project(child).git_root(init=True)
        self.assertFalse((child / ".git").exists())

    def test_modified_checkout_is_not_reset(self):
        project, _ = self.prepare()
        source = self.root / ".agents/vendor/mattpocock-skills/skills/engineering/tdd/SKILL.md"
        source.write_text("用户在上游 checkout 做了修改\n")
        with self.assertRaises(pi.wf.WorkflowError):
            self.prepare()
        self.assertEqual(source.read_text(), "用户在上游 checkout 做了修改\n")


if __name__ == "__main__":
    unittest.main(verbosity=2)
