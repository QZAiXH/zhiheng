#!/usr/bin/env python3
"""双层循环的确定性状态助手；不执行模型、验收、Wiki 或远端交付。"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from graphlib import CycleError, TopologicalSorter
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit
import sys

# 允许通过绝对入口或 importlib 在任意目录使用，仍只加载本包相邻模块。
sys.path.insert(0, str(Path(__file__).resolve().parent))
from dependency_contract import check_installed, manifest


class WorkflowError(Exception):
    pass


PHASES = {"planning", "design-review", "executing", "integrating", "verifying",
          "knowledge", "delivering", "cleaning", "complete", "blocked"}
STATUSES = {"pending", "running", "reviewing", "done", "blocked"}
ROLES = {"design", "implementation", "review"}
UPSTREAM = manifest()["skills"]


def require(condition, message):
    if not condition:
        raise WorkflowError(message)


def now():
    return datetime.now(timezone.utc).isoformat()


def read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise WorkflowError(f"无法读取 JSON：{path}：{exc}") from exc


def digest(data):
    return hashlib.sha256(data).hexdigest()


def json_digest(value):
    return digest(json.dumps(value, ensure_ascii=False, sort_keys=True).encode())


def git(root, *args):
    try:
        result = subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                                check=True, timeout=30)
        return result.stdout.decode("utf-8", errors="surrogateescape").strip()
    except (OSError, subprocess.SubprocessError) as exc:
        raise WorkflowError(f"Git 操作失败：{' '.join(args)}：{exc}") from exc


def repo_root(path):
    root = Path(path).resolve()
    require(Path(git(root, "rev-parse", "--show-toplevel")).resolve() == root,
            "--root 必须是目标 Git 顶层目录。")
    git(root, "rev-parse", "HEAD")
    return root


def safe_path(root, relative):
    require(isinstance(relative, str) and relative and "\\" not in relative,
            "必须使用非空的仓库相对 POSIX 路径。")
    rel = PurePosixPath(relative)
    require(not rel.is_absolute() and all(p not in {"..", ".git"} for p in rel.parts)
            and str(rel) == relative and relative != ".", "拒绝路径越界或非规范路径。")
    current = root
    for part in rel.parts:
        current = current / part
        require(not current.is_symlink(), f"拒绝符号链接：{relative}")
    require(current.resolve().is_relative_to(root), "路径必须位于目标仓库内。")
    return current


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".state-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def validate_config(config):
    require(isinstance(config, dict), "配置必须是对象。")
    require(config.get("confirmed") is True and isinstance(config.get("confirmation"), str)
            and config["confirmation"].strip(), "缺少用户集中确认记录。")
    require(config.get("endpoint") == "pr", "本包默认交付终点为 pr。")
    caps = config.get("capabilities", {})
    require(isinstance(caps, dict), "capabilities 必须是对象。")
    require(all(caps.get(k) is True for k in
                ("explicit_model", "explicit_effort", "fresh_context")),
            "宿主必须支持显式模型、强度和新上下文。")
    require(isinstance(caps.get("evidence"), str) and caps["evidence"].strip(),
            "缺少实际宿主能力的来源记录。")
    available = caps.get("models", {})
    require(isinstance(available, dict) and len(available) >= 3,
            "宿主实际可用模型必须至少三种。")
    limit, concurrency = caps.get("max_children"), config.get("concurrency")
    require(type(limit) is int and type(concurrency) is int and 1 <= concurrency <= limit,
            "并发数必须是正整数且不超过宿主上限。")
    roles = config.get("roles", {})
    require(isinstance(roles, dict) and set(roles) == ROLES, "必须配置设计、实现、审查三个角色。")
    chosen = []
    for name, role in roles.items():
        require(isinstance(role, dict), f"{name} 配置必须是对象。")
        model, effort = role.get("model"), role.get("effort")
        require(isinstance(model, str) and model in available, f"{name} 模型不在实际可用清单中。")
        require(isinstance(available[model], list) and effort in available[model],
                f"{name} 推理强度不受该模型支持。")
        require(role.get("context") == "fresh", f"{name} 必须使用新上下文。")
        require(isinstance(role.get("rationale"), str) and role["rationale"].strip(),
                f"{name} 缺少动态推荐理由。")
        chosen.append(model)
    require(len(set(chosen)) == 3, "设计、实现、审查必须使用三个不同的规范模型 ID。")
    routes = config.get("stage_roles", {})
    require(isinstance(routes, dict) and set(routes) == {"knowledge", "delivery"}
            and all(role in ROLES for role in routes.values()), "必须配置知识和交付阶段角色路由。")
    if "initialization" in config:
        initialization = config["initialization"]
        require(isinstance(initialization, dict) and set(initialization) == {"wiki_host"},
                "首次接入配置只能包含 wiki_host。")
        host = initialization["wiki_host"]
        require(isinstance(host, dict) and host.get("model") in available and
                host.get("effort") in available[host["model"]] and host.get("context") == "fresh" and
                isinstance(host.get("rationale"), str) and host["rationale"].strip(),
                "Wiki Host 必须按当前能力动态配置模型、强度、新上下文和理由。")
    return config


def validate_tasks(tasks):
    require(isinstance(tasks, list), "tasks 必须是列表。")
    ids = []
    for task in tasks:
        require(isinstance(task, dict) and isinstance(task.get("id"), str)
                and task["id"].strip(), "任务需要非空 ID。")
        require(task.get("status") in STATUSES, "未知任务状态。")
        deps = task.get("blocked_by")
        require(isinstance(deps, list) and all(isinstance(d, str) for d in deps)
                and len(deps) == len(set(deps)), "任务依赖必须是无重复的 ID 列表。")
        ids.append(task["id"])
    require(len(set(ids)) == len(ids), "任务 ID 重复。")
    mapping = {t["id"]: t for t in tasks}
    require(all(dep in mapping for t in tasks for dep in t["blocked_by"]), "任务引用了不存在的依赖。")
    try:
        tuple(TopologicalSorter({t["id"]: t["blocked_by"] for t in tasks}).static_order())
    except CycleError as exc:
        raise WorkflowError("任务图存在循环依赖。") from exc
    for task in tasks:
        if task["status"] in {"running", "reviewing", "done"}:
            require(all(mapping[d]["status"] == "done" for d in task["blocked_by"]),
                    f"任务 {task['id']} 的前置任务尚未完成。")
    return [t["id"] for t in tasks if t["status"] == "pending"
            and all(mapping[d]["status"] == "done" for d in t["blocked_by"])]


def repo_files(root):
    raw = git(root, "ls-files", "-z", "--cached", "--others", "--exclude-standard")
    return sorted(set(p for p in raw.split("\0") if p))


def workflow_inputs(root):
    """运行输入可能被 Git 忽略，仍需检测规格与任务的变更。"""
    folder = root / ".workflow"
    if not folder.exists():
        return []
    require(not folder.is_symlink(), "拒绝符号链接形式的 .workflow 目录。")
    result = []
    for path in folder.rglob("*"):
        if not path.is_file() and not path.is_symlink():
            continue
        relative = path.relative_to(root).as_posix()
        parts = PurePosixPath(relative).parts
        if len(parts) >= 4 and parts[:2] == (".workflow", "runs"):
            tail = parts[3:]
            if tail[0] in {"scratch", "handoffs"} or (len(tail) == 1 and
                    (tail[0] in {"state.json", "config.json"} or tail[0].startswith(".state-"))):
                continue
        result.append(relative)
    return result


def snapshot(root):
    entries = []
    files = {p for p in repo_files(root) if not p.startswith(".workflow/")}
    files.update(workflow_inputs(root))
    for relative in sorted(files):
        path = root / relative
        if path.is_symlink():
            value = "链接:" + os.readlink(path)
        elif path.is_file():
            value = digest(path.read_bytes())
        elif path.is_dir():
            value = "目录"
        else:
            value = "不存在"
        entries.append((relative, value))
    return {"head": git(root, "rev-parse", "HEAD"), "content": json_digest(entries)}


class Run:
    def __init__(self, root, run_id, create=False, allow_config_mismatch=False):
        require(re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}", run_id) is not None,
                "运行名仅允许字母、数字、下划线和连字符，最多 64 字符。")
        self.root = repo_root(root)
        self.id = run_id
        self.relative = f".workflow/runs/{run_id}"
        self.folder = safe_path(self.root, self.relative)
        self.state_path = safe_path(self.root, self.relative + "/state.json")
        self.config_path = safe_path(self.root, self.relative + "/config.json")
        if create:
            require(not self.folder.exists(), "同名运行已存在，不能覆盖；请恢复或使用新运行名。")
            return
        self.state = read_json(self.state_path)
        config = validate_config(read_json(self.config_path))
        require(self.state.get("schema_version") == 1 and self.state.get("root") == str(self.root)
                and self.state.get("run_id") == run_id, "运行身份或版本不匹配。")
        require(json_digest(config) == self.state.get("config_hash") or allow_config_mismatch,
                "配置已被修改或上次替换中断，请用确认后的配置重新执行 reconfigure。")
        require(self.state.get("phase") in PHASES, "运行阶段无效。")
        validate_tasks(self.state.get("tasks"))

    def save(self):
        self.state["updated_at"] = now()
        safe_path(self.root, self.relative + "/state.json")
        atomic_json(self.state_path, self.state)

    def evidence_paths(self, record, name):
        require(isinstance(record, dict) and isinstance(record.get("evidence"), list)
                and record["evidence"], f"{name} 缺少持久证据。")
        return record["evidence"]

    def cleanup_gate(self):
        state = self.state
        require(state["phase"] in {"cleaning", "complete"}, "清理只在 cleaning 或 complete 阶段执行。")
        require(state["tasks"] and all(t["status"] == "done" for t in state["tasks"]),
                "任务图为空或尚有未完成任务。")
        verification, knowledge, delivery = (state.get(k, {}) for k in
                                            ("verification", "knowledge", "delivery"))
        require(verification.get("status") == "passed", "验收尚未通过。")
        require(knowledge.get("status") in {"complete", "noop"}, "知识维护尚未完成。")
        require(delivery.get("status") == "pr_created", "PR 尚未创建。")
        link = urlsplit(delivery.get("pr_url", ""))
        require(link.scheme == "https" and link.netloc and link.path, "缺少有效 PR 链接。")
        require(delivery.get("commit") == git(self.root, "rev-parse", "HEAD"),
                "当前 HEAD 与已交付提交不一致。")
        require(state.get("snapshot") == snapshot(self.root), "代码在检查点后变化，必须重新核验。")
        paths = set(state.get("retained_paths", []))
        paths.update(self.evidence_paths(verification, "验收"))
        paths.update(self.evidence_paths(knowledge, "知识维护"))
        require(paths, "缺少保留资料。")
        for relative in paths:
            path = safe_path(self.root, relative)
            require(path.is_file(), f"保留资料不存在：{relative}")
            require(not relative.startswith(self.relative + "/scratch/"),
                    "验收、知识回执和保留原件必须位于 scratch 之外。")
        if state["phase"] == "complete":
            recorded = {entry["path"]: entry for entry in state["cleanup"]}
            require(all(a["path"] in recorded and recorded[a["path"]].get("status")
                        in {"deleted", "retained", "missing"} for a in state["artifacts"]
                        if a["kind"] == "temporary"), "还有未记录结果的临时文件，先完成清理。")
        return paths


def init_run(root, run_id, config):
    validate_config(config)
    run = Run(root, run_id, create=True)
    run.state = {"schema_version": 1, "root": str(run.root), "run_id": run_id,
                 "phase": "planning", "created_at": now(), "config_hash": json_digest(config),
                 "config_revisions": [], "snapshot": snapshot(run.root), "tasks": [],
                 "artifacts": [], "retained_paths": [], "dispatches": [], "notes": [],
                 "verification": {}, "knowledge": {}, "delivery": {}, "cleanup": []}
    run.state["updated_at"] = now()
    # 两份记录全部完成后才发布运行目录；中断不会占住最终 run-id。
    run.folder.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f".init-{run_id}-", dir=run.folder.parent) as name:
        staging = Path(name)
        atomic_json(staging / "config.json", config)
        atomic_json(staging / "state.json", run.state)
        require(not run.folder.exists(), "同名运行已被创建，不能覆盖。")
        staging.rename(run.folder)
    return {"run": run.relative, "phase": run.state["phase"]}


def checkpoint(run, update):
    allowed = {"phase", "tasks", "retained_paths", "verification", "knowledge", "delivery",
               "dispatches", "notes", "blocker"}
    require(isinstance(update, dict) and set(update) <= allowed, "检查点含未知或不可覆盖字段。")
    proposed = dict(run.state)
    proposed.update(update)
    require(proposed["phase"] in PHASES, "未知运行阶段。")
    ready = validate_tasks(proposed["tasks"])
    for key in ("retained_paths", "dispatches", "notes"):
        require(isinstance(proposed[key], list), f"{key} 必须是列表。")
    for relative in proposed["retained_paths"]:
        safe_path(run.root, relative)
    for key in ("verification", "knowledge", "delivery"):
        require(isinstance(proposed[key], dict), f"{key} 必须是对象。")
    proposed["snapshot"] = snapshot(run.root)
    if proposed["snapshot"]["content"] != run.state["snapshot"]["content"]:
        # 不让一次普通检查点更新把旧成功结论绑定到新代码。
        for key in ("verification", "knowledge"):
            if key not in update:
                proposed[key] = {}
    previous = run.state
    run.state = proposed
    try:
        if proposed["phase"] in {"cleaning", "complete"}:
            run.cleanup_gate()
    except WorkflowError:
        run.state = previous
        raise
    run.save()
    return {"phase": proposed["phase"], "ready_tasks": ready}


def register(run, relative, kind, reason, targets):
    path = safe_path(run.root, relative)
    require(not path.exists(), "已存在文件不能补登记为本次新建产物。")
    require(kind in {"temporary", "durable"} and reason.strip(), "需要有效分类与用途。")
    if kind == "temporary":
        require(relative.startswith(run.relative + "/scratch/"), "临时文件仅登记在本次 scratch 下。")
    else:
        require(not relative.startswith("openwiki/"), "OpenWiki 文件所有权由引擎管理。")
    require(not any(a["path"] == relative for a in run.state["artifacts"]), "文件已经登记。")
    require(relative not in {run.relative + "/state.json", run.relative + "/config.json"},
            "不能认领状态控制文件。")
    for target in targets:
        safe_path(run.root, target)
    run.state["artifacts"].append({"path": relative, "kind": kind, "reason": reason,
                                   "sha256": None, "extract_to": targets, "created_at": now()})
    run.save()
    return {"registered": relative}


def seal(run, relative, targets):
    item = next((a for a in run.state["artifacts"] if a["path"] == relative), None)
    require(item is not None, "文件尚未登记。")
    path = safe_path(run.root, relative)
    require(path.is_file(), "只能封存存在的普通文件。")
    if targets is not None:
        for target in targets:
            safe_path(run.root, target)
        item["extract_to"] = targets
    item["sha256"] = digest(path.read_bytes())
    item["sealed_at"] = now()
    run.save()
    return {"sealed": relative, "sha256": item["sha256"]}


def references(root, documents):
    """复用 CommonMark 解析器，处理引用式、图片、括号和 HTML 链接。"""
    try:
        from markdown_it import MarkdownIt
    except ImportError as exc:
        raise WorkflowError("清理引用检查需要 markdown-it-py；请按 requirements.txt 在隔离环境运行。") from exc
    parser = MarkdownIt("commonmark")
    refs, problems = set(), []

    def add_link(link, base):
        parts = urlsplit(link)
        if parts.scheme == "repo":
            refs.add(unquote((parts.netloc + parts.path).lstrip("/")))
            return
        if parts.scheme not in {"", "file"} or not parts.path:
            return
        if parts.scheme == "file" and parts.netloc not in {"", "localhost"}:
            return
        decoded = unquote(parts.path)
        targets = [base / decoded]
        if decoded.startswith("/"):
            # 同时保护实际绝对路径和网站常用的仓库根相对路径。
            targets = [Path(decoded), root / decoded.lstrip("/")]
        for target in targets:
            resolved = target.resolve()
            if resolved.is_relative_to(root):
                refs.add(resolved.relative_to(root).as_posix())
                if target.is_relative_to(root):
                    refs.add(target.relative_to(root).as_posix())

    class HTMLLinks(HTMLParser):
        def handle_starttag(self, tag, attrs):
            for key, value in attrs:
                if key in {"href", "src"} and value:
                    add_link(value, self.base)

    def json_resources(value, base):
        if isinstance(value, dict):
            for child in value.values():
                json_resources(child, base)
        elif isinstance(value, list):
            for child in value:
                json_resources(child, base)
        elif isinstance(value, str) and value.startswith("repo://"):
            add_link(value, base)

    for relative in sorted(documents):
        if Path(relative).suffix.lower() not in {".md", ".json"}:
            continue
        path = root / relative
        try:
            resolved = path.resolve()
            require(resolved.is_relative_to(root), "保留文档链接指向仓库之外，无法自动核对引用。")
            if not resolved.is_file():
                continue
            text = resolved.read_text(encoding="utf-8")
            if path.suffix.lower() == ".json":
                if "repo://" in text:
                    json_resources(json.loads(text), path.parent)
                continue
            tokens = list(parser.parse(text))
            while tokens:
                token = tokens.pop()
                if token.type in {"link_open", "image"}:
                    add_link(token.attrGet("href") or token.attrGet("src") or "", path.parent)
                if token.children:
                    tokens.extend(token.children)
                if token.type in {"html_inline", "html_block"}:
                    html = HTMLLinks()
                    html.base = path.parent
                    html.feed(token.content)
            # repo:// 可能在行内代码或 Wiki 正文中，Claims JSON 是正式依据。
            for link in re.findall(r"repo://[^\s\"'<>`]+", text):
                add_link(link.rstrip("，。;"), path.parent)
        except (OSError, ValueError, WorkflowError) as exc:
            problems.append(f"{relative}：{exc}")
    return refs, problems


def cleanup(run, apply=False):
    retained = run.cleanup_gate()
    candidates = {a["path"] for a in run.state["artifacts"] if a["kind"] == "temporary"}
    documents = set(repo_files(run.root)) | retained
    for base in (run.folder, run.root / "openwiki"):
        if base.exists():
            require(not base.is_symlink(), "拒绝通过符号链接遍历资料目录。")
            documents.update(p.relative_to(run.root).as_posix() for p in base.rglob("*")
                             if p.is_file() and p.suffix.lower() in {".md", ".json"})
    # 未登记的临时文档也是保留项，防止删除它仍引用的资料。
    # 保守地检查所有文档，包括可能因其他门槛被暂缓删除的草稿。
    linked, reference_problems = references(run.root, documents)
    linked_files = set()
    for relative in linked:
        path = run.root / relative
        if path.exists() and path.is_file():
            stat = path.stat()
            linked_files.add((stat.st_dev, stat.st_ino))
    prior = {entry["path"]: entry for entry in run.state["cleanup"]}
    result = []
    for item in run.state["artifacts"]:
        relative = item["path"]
        if item["kind"] != "temporary":
            continue
        reason = None
        try:
            require(not reference_problems, "存在无法核对的文档引用，暂缓自动清理。")
            path = safe_path(run.root, relative)
            require(relative.startswith(run.relative + "/scratch/"), "超出本次临时目录。")
            require(relative not in retained, "文件属于保留资料。")
            require(relative not in linked, "保留文档仍引用该文件。")
            if path.is_file():
                stat = path.stat()
                require((stat.st_dev, stat.st_ino) not in linked_files,
                        "保留文档仍引用该文件的实际文件身份。")
            require(item["sha256"], "文件尚未封存。")
            for target in item["extract_to"]:
                destination = safe_path(run.root, target)
                require(not target.startswith(".workflow/") and target not in candidates,
                        "知识替代位置必须是持久项目资料。")
                require(destination.is_file(), f"知识替代资料不存在：{target}")
            if not path.exists():
                status = "deleted" if prior.get(relative, {}).get("status") in {"deleting", "deleted"} else "missing"
                result.append({"path": relative, "status": status, "reason": "文件已不存在。"})
                continue
            require(path.is_file(), "拒绝删除目录或特殊文件。")
            require(digest(path.read_bytes()) == item["sha256"], "内容在封存后变化。")
        except WorkflowError as exc:
            reason = str(exc)
        if reason:
            result.append({"path": relative, "status": "retained", "reason": reason})
            continue
        entry = {"path": relative, "status": "eligible", "reason": "所有权、内容与静态引用检查通过。"}
        if apply:
            entry["status"] = "deleting"
            prior[relative] = entry
            run.state["cleanup"] = list(prior.values())
            run.save()
            path.unlink()
            entry["status"] = "deleted"
        result.append(entry)
    if apply:
        run.state["cleanup"] = result
        run.save()
    return {"mode": "apply" if apply else "preview", "files": result,
            "reference_problems": reference_problems}


def preflight(config):
    require(isinstance(config, dict), "依赖配置必须是 JSON 对象。")
    location = config.get("mattpocock_root")
    require(isinstance(location, str) and Path(location).is_absolute(), "尚未配置上游 checkout 绝对路径。")
    root = repo_root(location)
    expected = config.get("mattpocock_revision")
    require(isinstance(expected, str) and re.fullmatch(r"[0-9a-f]{40}", expected), "需要固定上游提交 SHA。")
    require(git(root, "rev-parse", "HEAD") == expected, "上游版本与已核验配置不同。")
    require(not git(root, "status", "--porcelain", "--untracked-files=no"), "上游 checkout 存在未核验修改。")
    missing = [name for name, group in UPSTREAM.items()
               if not (root / "skills" / group / name / "SKILL.md").is_file()]
    require(not missing, "上游缺少阶段入口：" + ", ".join(missing))
    wiki = config.get("openwiki_skill")
    require(isinstance(wiki, str) and Path(wiki).is_absolute() and Path(wiki).is_file(),
            "尚未配置可读取的 OpenWiki 技能。")
    check_installed(config)
    return {"status": "ready", "revision": expected, "skills": list(UPSTREAM),
            "host_check_required": "仍需检查原生调度、模型权限、Wiki 写入和 GitHub 能力。"}


def main():
    parser = argparse.ArgumentParser(description="双层循环状态、恢复与受限清理助手")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("preflight", "validate-config"):
        p = sub.add_parser(name)
        p.add_argument("--dependencies" if name == "preflight" else "--input", required=True)
    for name in ("init", "checkpoint", "reconfigure", "register", "seal", "resume", "cleanup"):
        p = sub.add_parser(name)
        p.add_argument("--root", required=True)
        p.add_argument("--run-id", required=True)
        if name in {"init", "reconfigure"}:
            p.add_argument("--config", required=True)
        elif name == "checkpoint":
            p.add_argument("--input", required=True)
        elif name in {"register", "seal"}:
            p.add_argument("--path", required=True)
            p.add_argument("--extract-to", action="append", default=[] if name == "register" else None)
            if name == "register":
                p.add_argument("--kind", choices=("temporary", "durable"), required=True)
                p.add_argument("--reason", required=True)
        elif name == "cleanup":
            p.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "preflight":
            output = preflight(read_json(args.dependencies))
        elif args.command == "validate-config":
            validate_config(read_json(args.input))
            output = {"status": "valid"}
        elif args.command == "init":
            output = init_run(args.root, args.run_id, read_json(args.config))
        else:
            run = Run(args.root, args.run_id, allow_config_mismatch=args.command == "reconfigure")
            if args.command == "checkpoint":
                output = checkpoint(run, read_json(args.input))
            elif args.command == "register":
                output = register(run, args.path, args.kind, args.reason, args.extract_to)
            elif args.command == "seal":
                output = seal(run, args.path, args.extract_to)
            elif args.command == "cleanup":
                output = cleanup(run, args.apply)
            elif args.command == "reconfigure":
                config = validate_config(read_json(args.config))
                previous = read_json(run.config_path)
                revision = {"hash": run.state["config_hash"], "changed_at": now(),
                            "configuration": previous if json_digest(previous) == run.state["config_hash"] else None,
                            "interrupted_change": json_digest(previous) != run.state["config_hash"]}
                run.state["config_revisions"].append(revision)
                run.state["config_hash"] = json_digest(config)
                run.state["verification"] = {}
                run.state["phase"] = "verifying"
                # 两文件替换若中断将显式产生指纹不一致，而不是带旧矩阵继续。
                atomic_json(run.config_path, config)
                run.save()
                output = {"status": "reconfigured", "phase": "verifying"}
            else:
                current = snapshot(run.root)
                output = {"phase": run.state["phase"], "snapshot_changed": current != run.state["snapshot"],
                          "verification_stale": current != run.state["snapshot"],
                          "ready_tasks": validate_tasks(run.state["tasks"]), "current_snapshot": current}
        print(json.dumps(output, ensure_ascii=False, indent=2))
    except (WorkflowError, OSError, TypeError, KeyError, ValueError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
