#!/usr/bin/env python3
"""项目接入的确定性操作；Wiki 内容与生命周期由原生 OpenWiki Host 负责。"""

import argparse
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "double-loop" / "scripts"))
import workflow_state as wf
from dependency_contract import manifest, tree_hash


START = b"<!-- DOUBLE-LOOP:START -->"
END = b"<!-- DOUBLE-LOOP:END -->"
IGNORE_START = b"# DOUBLE-LOOP:START"
IGNORE_END = b"# DOUBLE-LOOP:END"
WIKI_START = b"<!-- OPENWIKI:START -->"
WIKI_END = b"<!-- OPENWIKI:END -->"


def command(args, timeout=180):
    try:
        result = subprocess.run([str(arg) for arg in args], capture_output=True,
                                check=True, timeout=timeout)
        return result.stdout.decode("utf-8", errors="replace").strip()
    except (OSError, subprocess.SubprocessError) as exc:
        # 不输出环境、令牌或网络工具的原始 stderr。
        raise wf.WorkflowError(f"外部工具执行失败：{args[0]}；{type(exc).__name__}。保留检查点后重试。") from exc


def atomic_bytes(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".init-", dir=path.parent)
    try:
        if path.exists():
            os.fchmod(fd, path.stat().st_mode & 0o777)
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def block(data, start, end):
    if start not in data and end not in data:
        return None
    wf.require(data.count(start) == data.count(end) == 1 and data.index(start) < data.index(end),
               "托管标记不完整或重复；保留文件，先解决区块冲突。")
    begin = data.index(start)
    finish = data.index(end) + len(end)
    return begin, finish, data[begin:finish]


class Project:
    def __init__(self, root):
        self.root = Path(root).resolve()
        wf.require(self.root.is_dir(), "目标项目目录不存在。")
        self.path = wf.safe_path(self.root, ".workflow/project.json")
        self.state = wf.read_json(self.path) if self.path.exists() else {
            "schema": 1, "root": str(self.root), "created_at": wf.now(),
            "bundle": {}, "managed_files": {}, "wiki": {}, "conflicts": [],
        }
        self.validate_state()

    def validate_state(self):
        wf.require(isinstance(self.state, dict), "接入记录必须是 JSON 对象；保留原记录。")
        wf.require(self.state.get("schema") == 1 and self.state.get("root") == str(self.root),
                   "接入记录的版本或项目身份不匹配；保留原记录。")
        wf.require(all(isinstance(self.state.get(key), dict) for key in ("bundle", "managed_files", "wiki")) and
                   isinstance(self.state.get("conflicts"), list), "接入记录的字段类型损坏；保留原记录。")
        wf.require(all(isinstance(value, dict) for key in ("bundle", "managed_files")
                       for value in self.state[key].values()), "接入记录的安装或区块字段损坏；保留原记录。")

    def save(self):
        self.state["updated_at"] = wf.now()
        wf.atomic_json(self.path, self.state)

    @contextmanager
    def locked(self):
        path = wf.safe_path(self.root, ".workflow/.project-init.lock")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a+b") as stream:
            try:
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise wf.WorkflowError("已有项目初始化进程；先恢复该执行者。") from exc
            # 加锁后重新读取，避免用锁前的记录覆盖另一个执行者。
            if self.path.exists():
                self.state = wf.read_json(self.path)
                self.validate_state()
            yield

    def git_root(self, init=False):
        result = subprocess.run(["git", "-C", str(self.root), "rev-parse", "--show-toplevel"],
                                capture_output=True, timeout=30)
        if result.returncode:
            wf.require(init, "项目尚未接入 Git；调用初始化时可显式传入 --init-git。")
            command(["git", "-C", self.root, "init"])
        else:
            wf.require(Path(os.fsdecode(result.stdout).strip()).resolve() == self.root,
                       "目标必须是 Git 顶层；不会在已有父仓库内创建嵌套仓库。")
        return self.root

    def checkout(self, spec):
        location = wf.safe_path(self.root, ".agents/vendor/mattpocock-skills")
        if not location.exists():
            location.parent.mkdir(parents=True, exist_ok=True)
            with self.staging() as stage:
                source = stage / "checkout"
                command(["git", "clone", "--filter=blob:none", "--no-checkout",
                         "https://github.com/" + spec["repo"] + ".git", source], timeout=300)
                command(["git", "-C", source, "checkout", "--detach", spec["revision"]], timeout=180)
                self.verify_checkout(source, spec)
                wf.require(not location.exists(), "上游目标目录已出现；保留它并重新核对。")
                source.rename(location)
        self.verify_checkout(location, spec)
        self.state["checkout"] = {"path": str(location), "revision": spec["revision"]}
        self.save()
        return location

    @staticmethod
    def verify_checkout(path, spec):
        wf.require(Path(wf.git(path, "rev-parse", "--show-toplevel")).resolve() == path.resolve(),
                   "上游目录不是独立 Git checkout。")
        wf.require(wf.git(path, "rev-parse", "HEAD") == spec["revision"], "上游版本冲突；不切换或覆盖已有目录。")
        wf.require(not wf.git(path, "status", "--porcelain"), "上游目录含本地改动；保留并报告。")
        wf.require(any((path / name).is_file() for name in ("LICENSE", "LICENSE.md", "LICENSE.txt")),
                   "上游缺少许可证。")
        for name, group in spec["skills"].items():
            tree_hash(path / "skills" / group / name)

    @contextmanager
    def staging(self):
        parent = wf.safe_path(self.root, ".workflow/onboarding/tmp")
        parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="dl-init-", dir=parent) as temporary:
            yield Path(temporary)

    def merge(self, relative, content, start=START, end=END):
        path = wf.safe_path(self.root, relative)
        data = path.read_bytes() if path.exists() else b""
        found = block(data, start, end)
        desired = start + b"\n" + content.strip(b"\r\n") + b"\n" + end
        record = self.state["managed_files"].get(relative, {})
        if found:
            current = wf.digest(found[2])
            wf.require(found[2] == desired or current in {record.get("sha256"), record.get("pending_sha256")},
                       f"{relative} 托管区块被用户修改或所有权未知；保留内容。")
            updated = data[:found[0]] + desired + data[found[1]:]
        else:
            wf.require(not record or (not record.get("sha256") and
                       record.get("base_file_sha256") == wf.digest(data)),
                       f"{relative} 的托管区块已被删除或文件已变化；保留原文件。")
            updated = data + (b"\n" if data and not data.endswith(b"\n") else b"") + desired + b"\n"
        # 先保存写入意图，中断后可识别旧区块或已写入的新区块。
        record["pending_sha256"] = wf.digest(desired)
        record["base_file_sha256"] = wf.digest(data)
        self.state["managed_files"][relative] = record
        self.save()
        if data != updated:
            atomic_bytes(path, updated)
        self.state["managed_files"][relative] = {"sha256": wf.digest(desired)}
        self.save()

    def install_bundle(self, bundle, spec):
        bundle = Path(bundle).resolve()
        wf.require(set(spec["bundle"]) <= {p.name for p in bundle.iterdir() if p.is_dir()},
                   "源技能包不完整；必须包含全部九个目录。")
        for name in spec["bundle"]:
            source = bundle / name
            expected = tree_hash(source)
            target = wf.safe_path(self.root, ".agents/skills/" + name)
            if target.exists() and tree_hash(target) != expected:
                self.state["conflicts"].append({"path": str(target), "reason": "本包同名技能内容不同"})
                continue
            if not target.exists():
                with self.staging() as stage:
                    copied = stage / name
                    shutil.copytree(source, copied, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"))
                    target.parent.mkdir(parents=True, exist_ok=True)
                    wf.require(tree_hash(copied) == expected and not target.exists(), "技能发布前内容或目标发生变化。")
                    copied.rename(target)
            self.state["bundle"][name] = {"path": str(target), "sha256": expected,
                                           "source_is_target": source == target}
            self.save()

    def install_upstream(self, source, installer, spec):
        missing, installed = [], {}
        for name, group in spec["skills"].items():
            target = wf.safe_path(self.root, ".agents/skills/" + name)
            expected = tree_hash(source / "skills" / group / name)
            if target.exists():
                if tree_hash(target) != expected:
                    self.state["conflicts"].append({"path": str(target), "reason": "上游同名技能版本或内容不同"})
                    continue
                installed[name] = {"path": str(target), "sha256": expected}
            else:
                missing.append(name)
        if missing:
            installer = Path(installer).resolve()
            wf.require(installer.is_file(), "未找到成熟 skill-installer 的安装脚本。")
            with self.staging() as stage:
                destination = stage / "skills"
                paths = [f"skills/{spec['skills'][name]}/{name}" for name in missing]
                command([sys.executable, installer, "--repo", spec["repo"], "--ref", spec["revision"],
                         "--path", *paths, "--dest", destination], timeout=300)
                # 验证整批后再逐目录发布；进程中断后按内容复用已发布部分。
                for name in missing:
                    wf.require(tree_hash(destination / name) == tree_hash(source / "skills" / spec["skills"][name] / name),
                               f"安装器输出与固定 checkout 不一致：{name}")
                for name in missing:
                    target = wf.safe_path(self.root, ".agents/skills/" + name)
                    wf.require(not target.exists(), f"安装目标已出现：{name}；保留并重试。")
                    (destination / name).rename(target)
                    installed[name] = {"path": str(target), "sha256": tree_hash(target)}
                    self.state["installed_skills"] = installed.copy()
                    self.save()
        self.state["installed_skills"] = installed
        self.save()

    def dependencies(self, source, wiki_skill, spec):
        wiki_skill = Path(wiki_skill).resolve()
        wf.require(wiki_skill.is_file(), "OpenWiki 技能入口不可读；先接入现有技能。")
        path = wf.safe_path(self.root, ".workflow/dependencies.json")
        current = wf.read_json(path) if path.exists() else {}
        wf.require(isinstance(current, dict), "已有依赖配置必须是 JSON 对象；保留原文件。")
        fields = {"mattpocock_root": str(source), "mattpocock_revision": spec["revision"],
                  "openwiki_skill": str(wiki_skill), "installed_skills": self.state["installed_skills"]}
        old = self.state.get("dependencies_sha256")
        pending = self.state.get("dependencies_pending", {})
        if current and wf.json_digest(current) not in {old, pending.get("before"), pending.get("after")}:
            wf.require(all(key not in current or current[key] is None or current[key] == value for key, value in fields.items()),
                       "已有依赖配置与项目接入冲突；保留用户配置。")
        current.update(fields)
        self.state["dependencies_pending"] = {"before": old, "after": wf.json_digest(current)}
        self.save()
        wf.atomic_json(path, current)
        self.state["dependencies_sha256"] = wf.json_digest(current)
        self.state.pop("dependencies_pending", None)
        self.save()

    def ignore(self, spec):
        paths = ["/.agents/vendor/mattpocock-skills/"]
        records = {**self.state["installed_skills"], **self.state["bundle"]}
        deps = wf.read_json(wf.safe_path(self.root, ".workflow/dependencies.json"))
        wiki_directory = Path(deps["openwiki_skill"]).parent
        if wiki_directory == self.root / ".agents/skills/openwiki":
            records["openwiki"] = {"path": str(wiki_directory)}
        for record in records.values():
            path = Path(record["path"])
            rel = path.relative_to(self.root).as_posix()
            # 技能仓库自身的源文件以及已跟踪目录继续作为业务知识来源。
            if record.get("source_is_target") or wf.git(self.root, "ls-files", "--", rel):
                continue
            paths.append("/" + rel + "/")
        local = ["/.workflow/project.json", "/.workflow/dependencies.json", "/.workflow/.project-init.lock",
                 "/.workflow/onboarding/", "/.workflow/runs/*/scratch/", "/.workflow/runs/*/handoffs/",
                 "/.workflow/runs/*/state.json", "/.workflow/runs/*/config.json"]
        content = ("\n".join(sorted(set(paths + local))) + "\n").encode()
        for filename in (".gitignore", ".openwikiignore"):
            self.merge(filename, content, IGNORE_START, IGNORE_END)
        self.state["excluded_sources"] = paths
        self.save()
        # .gitignore 的用户否定规则可能使安装目录仍进入 Git，必须显式暴露。
        self.check_git_ignore()

    def check_git_ignore(self):
        paths = [p[1:] for p in self.state.get("excluded_sources", [])]
        wf.require(paths, "安装目录排除记录缺失。")
        ignored = subprocess.run(["git", "-C", str(self.root), "check-ignore", "--no-index", "--stdin"],
                                 input="\n".join(paths).encode(), capture_output=True, timeout=30)
        wf.require(ignored.returncode in {0, 1}, "无法核查项目 Git ignore 规则。")
        visible = set(paths) - set(os.fsdecode(ignored.stdout).splitlines())
        wf.require(not visible, "用户 ignore 规则覆盖安装排除项；保留规则并解决：" + ", ".join(sorted(visible)))

    def prepare(self, bundle, installer, wiki_skill, init_git=False):
        self.git_root(init_git)
        spec = manifest()
        self.state["manifest_sha256"] = wf.json_digest(spec)
        self.state["conflicts"] = []
        self.state["phase"] = "preparing"
        self.save()
        source = self.checkout(spec)
        self.install_bundle(bundle, spec)
        self.install_upstream(source, installer, spec)
        self.save()
        if self.state["conflicts"]:
            self.state["phase"] = "conflict"
            self.save()
            return self.status()
        self.dependencies(source, wiki_skill, spec)
        self.ignore(spec)
        self.state["phase"] = "local_prepared"
        self.save()
        return self.status()

    def instructions(self, content):
        wf.require(content.strip(), "项目指令内容不能为空。")
        wf.require(not any(marker in content for marker in (START, END, WIKI_START, WIKI_END)),
                   "正文只包含项目接入指令；托管标记由各自所有者生成。")
        self.merge("AGENTS.md", content)
        return self.status()

    def source_fingerprint(self):
        result = subprocess.run(["git", "-C", str(self.root), "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                                capture_output=True, check=True, timeout=30)
        skipped = [name[1:] for name in self.state.get("excluded_sources", [])]
        hashes = {}
        names = set(os.fsdecode(result.stdout).split("\0")) | set(wf.workflow_inputs(self.root))
        for name in sorted(names):
            if not name or name.startswith(
                    ("openwiki/", ".workflow/onboarding/", ".agents/vendor/", *skipped)) or name in {
                    ".workflow/project.json", ".workflow/dependencies.json", ".workflow/.project-init.lock"} or re.match(
                    r"^\.workflow/runs/[^/]+/(scratch/|handoffs/|(?:state|config)\.json$|\.state-)", name):
                continue
            path = self.root / name
            if path.is_symlink():
                hashes[name] = wf.digest(os.readlink(path).encode())
            elif path.is_file():
                data = path.read_bytes()
                if name in {"AGENTS.md", "CLAUDE.md"}:
                    found = block(data, WIKI_START, WIKI_END)
                    if found:
                        data = (data[:found[0]] + data[found[1]:]).strip()
                hashes[name] = wf.digest(data)
            else:
                hashes[name] = "missing"
        return wf.json_digest(hashes)

    def record_wiki(self, receipt):
        wf.require(isinstance(receipt, dict), "Wiki 回执必须是 JSON 对象。")
        wf.require(receipt.get("root") == str(self.root), "Wiki 回执属于其他项目。")
        status = receipt.get("status")
        wf.require(status in {"complete", "noop", "awaiting_host_reload", "blocked"}, "不支持的 Wiki 接入状态。")
        wf.require(isinstance(receipt.get("evidence"), str) and receipt["evidence"].strip(), "缺少实际工具回执或阻塞依据。")
        if status in {"complete", "noop"}:
            host = receipt.get("host", {})
            wf.require(isinstance(host, dict), "Wiki Host 配置必须是对象。")
            wf.require(host.get("context") == "fresh" and host.get("confirmed") is True,
                       "Wiki Host 必须有已确认的新上下文配置。")
            wf.require(all(isinstance(host.get(k), str) and host[k].strip()
                           for k in ("model", "effort", "rationale", "confirmation", "capability_evidence")),
                       "Wiki Host 配置或动态推荐依据不完整。")
            response = receipt.get("tool_response", {})
            wf.require(isinstance(response, dict), "Wiki 工具响应必须是对象。")
            operation = receipt.get("operation")
            wf.require(response.get("status") == status and
                       ((status == "complete" and operation == "openwiki_finish") or
                        (status == "noop" and operation == "openwiki_begin")),
                       "完成只能来自 finish complete 或 begin noop。")
            self.check_wiki_files()
        receipt = dict(receipt, recorded_at=wf.now(), source_sha256=self.source_fingerprint())
        path = wf.safe_path(self.root, ".workflow/onboarding/wiki-receipt.json")
        wf.atomic_json(path, receipt)
        self.state["wiki"] = {"status": status, "receipt": str(path.relative_to(self.root)),
                              "sha256": wf.json_digest(receipt), "source_sha256": receipt["source_sha256"]}
        self.state["phase"] = status if status not in {"complete", "noop"} else "wiki_recorded"
        self.save()
        return self.status()

    def check_wiki_files(self):
        quickstart = wf.safe_path(self.root, "openwiki/quickstart.md")
        wf.require(quickstart.is_file() and quickstart.stat().st_size > 0, "Wiki quickstart 未生成。")
        agents = wf.safe_path(self.root, "AGENTS.md")
        wf.require(agents.is_file() and block(agents.read_bytes(), WIKI_START, WIKI_END),
                   "缺少 OpenWiki 生成的 AGENTS.md 区块。")

    def status(self):
        problems, git_root, baseline = [], None, False
        try:
            git_root = str(self.git_root())
            probe = subprocess.run(["git", "-C", str(self.root), "rev-parse", "--verify", "HEAD"],
                                   capture_output=True, timeout=30)
            baseline = probe.returncode == 0
        except wf.WorkflowError as exc:
            problems.append(str(exc))
        spec = manifest()
        local_ready = True
        try:
            wf.require(self.state.get("manifest_sha256") == wf.json_digest(spec), "项目接入清单缺失或已变化。")
            wf.require(not self.state.get("conflicts"), "存在已记录的同名技能冲突。")
            for name in spec["bundle"]:
                record = self.state["bundle"].get(name, {})
                target = wf.safe_path(self.root, ".agents/skills/" + name)
                wf.require(record.get("path") == str(target) and tree_hash(target) == record.get("sha256"),
                           f"本包技能缺失或内容已变化：{name}")
            deps = wf.read_json(wf.safe_path(self.root, ".workflow/dependencies.json"))
            wf.require(wf.json_digest(deps) == self.state.get("dependencies_sha256"), "依赖配置缺失或已被修改。")
            wf.preflight(deps)
            for relative, start, end in (("AGENTS.md", START, END), (".gitignore", IGNORE_START, IGNORE_END),
                                          (".openwikiignore", IGNORE_START, IGNORE_END)):
                path = wf.safe_path(self.root, relative)
                found = block(path.read_bytes(), start, end)
                wf.require(found and wf.digest(found[2]) == self.state["managed_files"].get(relative, {}).get("sha256"),
                           f"{relative} 托管区块缺失或被修改。")
            self.check_git_ignore()
        except (wf.WorkflowError, OSError, ValueError, KeyError, TypeError) as exc:
            local_ready = False
            problems.append(str(exc))
        wiki_ready = False
        try:
            wiki = self.state["wiki"]
            wf.require(wiki.get("status") in {"complete", "noop"}, "Wiki 尚未完成或需重新加载宿主。")
            receipt = wf.read_json(wf.safe_path(self.root, wiki["receipt"]))
            wf.require(wf.json_digest(receipt) == wiki["sha256"] and receipt.get("status") == wiki["status"], "Wiki 回执已变化。")
            self.check_wiki_files()
            wf.require(wiki.get("source_sha256") == self.source_fingerprint(), "项目源文件已变化；由 Wiki Host 核查更新。")
            wiki_ready = True
        except (wf.WorkflowError, OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
            problems.append(str(exc))
        initialized = bool(git_root) and local_ready and wiki_ready
        return {"root": str(self.root), "phase": self.state.get("phase", "not_initialized"),
                "initialized": initialized, "local_ready": local_ready, "wiki_ready": wiki_ready,
                "needs_git_baseline": bool(git_root) and not baseline,
                "ready_for_worktrees": initialized and baseline,
                "conflicts": self.state.get("conflicts", []), "problems": problems,
                "host_check_required": "仍需从当前工具清单核查模型、MCP 在线状态与 GitHub 权限；回执不独立证明模型生效。"}


def main():
    parser = argparse.ArgumentParser(description="双层循环项目接入、保护与恢复助手")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("status", "prepare", "instructions", "wiki", "verify"):
        child = commands.add_parser(name)
        child.add_argument("--root", required=True)
        if name == "prepare":
            child.add_argument("--bundle", required=True)
            child.add_argument("--installer", required=True)
            child.add_argument("--openwiki-skill", required=True)
            child.add_argument("--init-git", action="store_true")
        elif name in {"instructions", "wiki"}:
            child.add_argument("--input", required=True)
    args = parser.parse_args()
    try:
        project = Project(args.root)
        if args.command in {"status", "verify"}:
            result = project.status()
        else:
            with project.locked():
                if args.command == "prepare":
                    result = project.prepare(args.bundle, args.installer, args.openwiki_skill, args.init_git)
                elif args.command == "instructions":
                    result = project.instructions(Path(args.input).read_bytes())
                else:
                    result = project.record_wiki(wf.read_json(args.input))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2 if args.command == "verify" and not result["ready_for_worktrees"] else 0
    except (wf.WorkflowError, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
