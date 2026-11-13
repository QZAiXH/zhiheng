#!/usr/bin/env python3
"""Validate local tasks, capture content-bound evidence, and compare applicability."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from urllib.parse import unquote, urlsplit

try:
    import yaml
    from markdown_it import MarkdownIt
except ImportError as exc:
    print(json.dumps({"command": None, "task": None, "status": "error", "findings": [
        {"file": None, "field": "dependency", "code": "missing_dependency",
         "message": f"缺少解析依赖 {exc.name}；请在隔离环境安装 scripts/requirements.txt 中声明的依赖。"}],
        "applicability": "尚未执行核对。"}, ensure_ascii=False))
    sys.exit(2)


STATES = {"待处理", "执行中", "待验收", "已完成", "阻塞", "已暂停", "已取消", "已取代"}
RESULTS = {"通过", "失败", "未执行", "不适用"}
TASK_ID = re.compile(r"T-\d{8}-\d{3}\Z")
SLICE_ID = re.compile(r"S\d{2,}\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
APPLICABILITY = ("仅核对声明的本地记录、范围、来源、检查标识和证据内容；"
                 "conditions 是调用者声明的检查条件，未声明的外部环境变化须另行核对。"
                 "工具不执行检查命令、不接受业务成果、不改写任务状态。")
PROTOCOL = """Protocol v1 (literal local paths; no glob expansion or remote URL requests):
  Records use Markdown with --- YAML front matter --- (design section 7.10).
  A task may declare sources: [{id, path, revision}], relative to its own file.
  A task may link verification: verification.md, with the following metadata:
    schema_version: 1
    kind: verification
    task_ref: README.md
    task_revision: 1
    manifest: ../../../manifest.json
    checks: [{id: C01, result: 通过, evidence: [evidence/test.log]}]
    acceptance: [{id: A01, revision: 1, result: 通过, check_ids: [C01]}]
  A slice acceptance adds slice_id: S01 and uses that slice's revision.
  Completed units require a passing acceptance for the current revision.
  Passing acceptance requires a reachable manifest for the same task/revision,
  associated checks and content-matching evidence. Commands are never executed.
  Pending verification/checkpoint templates may omit results and use manifest: null.
  A task may declare records: [return.md], with kind: dispatch/return/checkpoint.
  All records bind task_ref/task_revision; slice records also bind slice_revision.
  Dispatch/return records require dispatch_id, workspace, write_scope (a path list),
  and current source_versions: {SPEC: r2} or sources: [{id, path, revision}].
  Optional artifacts/evidence are path lists relative to the record. A slice's
  current status/revision live only in the plan. Stale bindings are rejected.
  Local Markdown links/images/reference definitions use CommonMark parsing;
  remote URLs and anchors are not fetched.
  If a task directory is named after its ID, sibling */README.md files form its ID registry.

  --scope is a standalone YAML/JSON file, for example:
    schema_version: 1
    root: .
    paths: [src, tests]
    sources: [{id: SPEC, path: spec.md, revision: 1}]
    checks: [{id: C01, command: 'python -m unittest', evidence: [test.log]}]
    conditions: {python: '3.14', environment: local}
  root is relative to the scope file; paths/sources/checks.evidence are relative
  to root and must remain inside it without symlinks. All values must be JSON-compatible.
  sources/checks/conditions default to empty lists/a mapping. A source revision
  is a positive integer or a nonempty version string, declared by the caller;
  source contents are independently bound with SHA-256.
  Directories include all files, including untracked/ignored files, except .git
  and this output manifest. Sources, evidence, and records are included automatically.
  Existing business files cannot be overwritten; repeated output to a valid manifest
  is supported. An explicit paths file cannot simultaneously be the output.
  Snapshots capture scope definitions, SHA-256, task/slice status and revisions,
  Git HEAD, index blobs, staged/worktree status, and untracked paths. Compare
  rereads the original scope and detects directory additions/deletions.
  Conditions are caller declarations, not measurements of the external environment.
  Compare emits unchanged/changed/missing/unverifiable per item; progress and
  requirement revisions are reported separately. Relocated manifests/scopes need a new snapshot.
  Exit codes: 0=complete/no issues; 1=structural errors/differences/gaps;
  2=argument/dependency/runtime failures. Snapshot writes only --output on success;
  incomplete captures are not written. Task status is never modified.
"""


class InputError(Exception):
    def __init__(self, code, message, file=None, field=""):
        self.finding = {"file": str(file) if file is not None else None,
                        "field": field, "code": code, "message": message}
        super().__init__(message)


class UniqueLoader(yaml.SafeLoader):
    pass


def unique_mapping(loader, node, deep=False):
    loader.flatten_mapping(node)
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str):
            raise InputError("invalid_key", "YAML 字段名必须是字符串。", field=str(key_node.start_mark))
        if key in result:
            raise InputError("duplicate_key", f"YAML 重复键：{key}。", field=f"{key} (line {key_node.start_mark.line + 1})")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load_yaml(path, markdown=False):
    try:
        data = path.read_bytes()
    except FileNotFoundError:
        raise InputError("missing_file", "文件不存在。", path)
    except OSError as exc:
        raise InputError("unreadable_file", str(exc), path)
    try:
        text = data.decode("utf-8-sig")
    except UnicodeError as exc:
        raise InputError("invalid_encoding", str(exc), path)
    body = ""
    if markdown:
        lines = text.splitlines(keepends=True)
        if not lines or lines[0].strip() != "---":
            raise InputError("missing_frontmatter", "记录必须以 --- YAML 元数据区开头。", path)
        end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
        if end is None:
            raise InputError("missing_frontmatter", "YAML 元数据区缺少结束 ---。", path)
        text, body = "".join(lines[1:end]), "".join(lines[end + 1:])
    try:
        obj = yaml.load(text, Loader=UniqueLoader)
    except InputError as exc:
        exc.finding["file"] = str(path)
        raise
    except (yaml.YAMLError, RecursionError, ValueError) as exc:
        raise InputError("invalid_yaml", str(exc), path)
    if not isinstance(obj, dict):
        raise InputError("invalid_mapping", "顶层必须是字段映射。", path)
    try:
        json.dumps(obj, allow_nan=False)
    except (TypeError, ValueError, RecursionError) as exc:
        raise InputError("invalid_value", f"YAML 值必须可表示为有限 JSON 数据：{exc}", path)
    return obj, body, sha(data)


def positive(value):
    return type(value) is int and value > 0


def version(value):
    return positive(value) or (isinstance(value, str) and bool(value.strip()))


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def markdown_targets(body):
    """Read links and images from CommonMark tokens, including nested containers."""
    env = {}
    pending = list(reversed(MarkdownIt("commonmark").parse(body, env)))
    seen = set()
    while pending:
        token = pending.pop()
        target = token.attrGet("href") if token.type == "link_open" else (
            token.attrGet("src") if token.type == "image" else None)
        if isinstance(target, str) and target not in seen:
            seen.add(target)
            yield target
        # Image children render as plain alt text; they are not separate links.
        if token.children and token.type != "image":
            pending.extend(reversed(token.children))
    # Preserve checks of actual reference definitions, including unused ones.
    for reference in env.get("references", {}).values():
        target = reference["href"]
        if target not in seen:
            seen.add(target)
            yield target


class Validator:
    def __init__(self, task):
        self.task = task
        self.findings = []
        self.documents = {}
        self.failed_documents = set()
        self.items = {}
        self.verification = None

    def issue(self, file, field, code, message):
        self.findings.append({"file": str(file), "field": field, "code": code, "message": message})

    def require(self, obj, field, predicate, file, message):
        if not predicate(obj.get(field)):
            self.issue(file, field, "invalid_field", message)
            return False
        return True

    def read(self, path, expected=None):
        if path in self.documents:
            obj = self.documents[path][0]
            if expected and obj.get("kind") != expected:
                self.issue(path, "kind", "invalid_kind", f"此引用要求 kind: {expected}。")
            return obj
        try:
            obj, body, fingerprint = load_yaml(path, markdown=True)
        except InputError as exc:
            self.findings.append(exc.finding)
            self.failed_documents.add(path)
            return None
        self.documents[path] = (obj, body, fingerprint)
        if type(obj.get("schema_version")) is not int or obj["schema_version"] != 1:
            self.issue(path, "schema_version", "unsupported_version", "只支持 schema_version: 1。")
        if not isinstance(obj.get("kind"), str) or obj["kind"] not in {"task", "plan", "slice", "verification", "dispatch", "return", "checkpoint"}:
            self.issue(path, "kind", "invalid_kind", "未知的记录 kind。")
        if expected and obj.get("kind") != expected:
            self.issue(path, "kind", "invalid_kind", f"此引用要求 kind: {expected}。")
        self.links(path, body)
        return obj

    def links(self, path, body):
        # Check inline links, images, and reference definitions, not prose semantics.
        for target in markdown_targets(body):
            try:
                parsed = urlsplit(target)
                if parsed.netloc:
                    # The parser normalizes URLs; also validate the decoded authority.
                    urlsplit("//" + unquote(parsed.netloc))
            except ValueError as exc:
                self.issue(path, "body.link", "invalid_reference", str(exc))
                continue
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            self.local_file(path, unquote(parsed.path), "body.link")

    def reference(self, base, value, field):
        if not nonempty(value):
            self.issue(base, field, "invalid_reference", "引用必须是非空本地文件路径。")
            return None
        try:
            parsed = urlsplit(value)
        except ValueError as exc:
            self.issue(base, field, "invalid_reference", str(exc))
            return None
        if parsed.scheme:
            self.issue(base, field, "invalid_reference", "机器字段要求本地文件路径。")
            return None
        return self.local_file(base, value, field)

    def local_file(self, base, value, field):
        # A decoded Markdown path has already passed URI classification.
        path = Path(os.path.abspath(base.parent / value))
        if not path.is_file():
            self.issue(base, field, "broken_reference", f"引用文件不可达：{path}。")
            return None
        return path

    def identity(self, obj, path, slice_item=False):
        pattern = SLICE_ID if slice_item else TASK_ID
        self.require(obj, "id", lambda v: isinstance(v, str) and bool(pattern.fullmatch(v)), path, "ID 格式无效。")
        self.require(obj, "revision", positive, path, "revision 必须是正整数。")
        self.require(obj, "status", lambda v: isinstance(v, str) and v in STATES, path, "未知状态；仅接受八种中文状态。")

    def sources(self, obj, path):
        entries = self.entries(obj.get("sources", []), path, "sources")
        for entry in entries:
            self.require(entry, "revision", version, path, "来源 revision 必须是正整数或非空字符串。")
            self.reference(path, entry.get("path"), f"sources.{entry.get('id')}.path")
        return entries

    def entries(self, values, path, field):
        if not isinstance(values, list):
            self.issue(path, field, "invalid_field", "必须是列表。")
            return []
        entries, ids = [], set()
        for index, item in enumerate(values):
            if not isinstance(item, dict):
                self.issue(path, f"{field}[{index}]", "invalid_field", "条目必须是映射。")
                continue
            identity = item.get("id")
            if not nonempty(identity):
                self.issue(path, f"{field}[{index}].id", "invalid_field", "ID 必须是非空字符串。")
                continue
            if identity in ids:
                self.issue(path, f"{field}[{index}].id", "duplicate_id", f"重复 ID：{identity}。")
                continue
            ids.add(identity)
            entries.append(item)
        return entries

    def run(self):
        task = self.read(self.task, "task")
        if task is None:
            return self
        self.identity(task, self.task)
        for field in ("phase", "delivery_target"):
            self.require(task, field, nonempty, self.task, f"{field} 必须是非空字符串。")
        self.sources(task, self.task)
        if "plan" not in task:
            self.issue(self.task, "plan", "invalid_field", "plan 必须是计划路径或 null。")
        if task.get("plan") is not None:
            plan_path = self.reference(self.task, task.get("plan"), "plan")
            if plan_path:
                self.plan(plan_path)
        if task.get("verification") is not None:
            path = self.reference(self.task, task["verification"], "verification")
            if path:
                self.verify(path, task)
        records = task.get("records", [])
        if not isinstance(records, list):
            self.issue(self.task, "records", "invalid_field", "records 必须是路径列表。")
        else:
            for i, value in enumerate(records):
                path = self.reference(self.task, value, f"records[{i}]")
                if path:
                    self.execution_record(path, task)
        completed = [(None, task)] + list(self.items.items())
        accepted = self.verification or []
        for identity, item in completed:
            if item.get("status") == "已完成" and not any(
                    a.get("slice_id") == identity and a.get("revision") == item.get("revision")
                    and a.get("result") == "通过" for a in accepted):
                self.issue(self.task, f"acceptance.{identity or 'task'}", "missing_acceptance", "已完成单元缺少当前修订的通过接受记录。")
        # Derive the registry from the prescribed task layout, not arbitrary parents.
        if self.task.parent.name == task.get("id"):
            for sibling in sorted(self.task.parent.parent.glob("*/README.md")):
                if sibling.resolve() == self.task:
                    continue
                try:
                    other, _, _ = load_yaml(sibling, markdown=True)
                except InputError:
                    continue
                if other.get("kind") == "task" and other.get("id") == task.get("id"):
                    self.issue(sibling, "id", "duplicate_id", "同一任务登记位置存在重复任务 ID。")
        return self

    def plan(self, path):
        plan = self.read(path, "plan")
        if plan is None:
            return
        back = self.reference(path, plan.get("task_ref"), "task_ref")
        if back is not None and back != self.task:
            self.issue(path, "task_ref", "wrong_reference", "计划未指回当前任务。")
        entries = self.entries(plan.get("items"), path, "items")
        self.items = {item["id"]: item for item in entries}
        for item in entries:
            self.identity(item, path, slice_item=True)
            if "assignee" not in item or not (item["assignee"] is None or nonempty(item["assignee"])):
                self.issue(path, f"items.{item['id']}.assignee", "invalid_field", "assignee 必须是非空字符串或 null。")
            deps = item.get("depends_on")
            if not isinstance(deps, list) or not all(nonempty(x) for x in deps):
                self.issue(path, f"items.{item['id']}.depends_on", "invalid_field", "依赖必须是 ID 列表。")
                continue
            if len(deps) != len(set(deps)):
                self.issue(path, f"items.{item['id']}.depends_on", "duplicate_id", "依赖 ID 重复。")
            for dependency in deps:
                if dependency not in self.items:
                    self.issue(path, f"items.{item['id']}.depends_on", "missing_dependency", f"缺失依赖：{dependency}。")
            detail = self.reference(path, item.get("detail"), f"items.{item['id']}.detail")
            if detail:
                obj = self.read(detail, "slice")
                if obj is not None:
                    if self.reference(detail, obj.get("plan_ref"), "plan_ref") != path or obj.get("slice_id") != item["id"]:
                        self.issue(detail, "plan_ref/slice_id", "wrong_reference", "切片必须指回所在计划及相应 ID。")
                    if "status" in obj or "revision" in obj:
                        self.issue(detail, "status/revision", "duplicate_authority", "切片当前状态和修订只在计划中维护。")
        # Kahn's algorithm avoids depending on Python recursion depth.
        pending = {i: set(x for x in item.get("depends_on", []) if isinstance(x, str) and x in self.items)
                   for i, item in self.items.items() if isinstance(item.get("depends_on"), list)}
        ready = [i for i, deps in pending.items() if not deps]
        while ready:
            done = ready.pop()
            pending.pop(done, None)
            for identity, deps in pending.items():
                if done in deps:
                    deps.remove(done)
                    if not deps:
                        ready.append(identity)
        if pending:
            self.issue(path, "items.depends_on", "dependency_cycle", "依赖图存在循环：" + ", ".join(sorted(pending)))

    def binding(self, obj, path, task):
        if self.reference(path, obj.get("task_ref"), "task_ref") != self.task:
            self.issue(path, "task_ref", "wrong_reference", "记录未关联当前任务。")
        if not positive(obj.get("task_revision")) or obj["task_revision"] != task.get("revision"):
            self.issue(path, "task_revision", "stale_revision", "记录所用任务修订与当前有效修订不同。")

    def verify(self, path, task):
        obj = self.read(path, "verification")
        if obj is None:
            return
        self.binding(obj, path, task)
        checks = self.entries(obj.get("checks", []), path, "checks")
        by_id = {item["id"]: item for item in checks}
        for item in checks:
            self.require(item, "result", lambda v: isinstance(v, str) and v in RESULTS, path, "未知检查结果。")
            evidence = item.get("evidence")
            if not isinstance(evidence, list) or (item.get("result") == "通过" and not evidence):
                self.issue(path, f"checks.{item['id']}.evidence", "missing_evidence", "检查需声明证据列表；通过检查至少有一个证据文件。")
            else:
                for value in evidence:
                    self.reference(path, value, f"checks.{item['id']}.evidence")
        self.verification = self.entries(obj.get("acceptance", []), path, "acceptance")
        manifest = self.manifest_binding(obj, path, task, any(item.get("result") == "通过" for item in self.verification))
        for item in self.verification:
            identity = item.get("slice_id")
            target = self.items.get(identity) if isinstance(identity, str) else task if identity is None else None
            if target is None:
                self.issue(path, f"acceptance.{item['id']}.slice_id", "unknown_slice", "接受记录引用了未知切片。")
            elif not positive(item.get("revision")) or item["revision"] != target.get("revision"):
                self.issue(path, f"acceptance.{item['id']}.revision", "stale_revision", "接受记录未绑定当前要求修订。")
            if isinstance(identity, str) and item.get("result") == "通过" and manifest is not None:
                bound = manifest["slices"].get(identity)
                if not isinstance(bound, dict) or not positive(bound.get("revision")) or bound["revision"] != item.get("revision"):
                    self.issue(path, f"manifest.slices.{identity}.revision", "stale_manifest", "成果清单未绑定接受项的切片身份与要求修订。")
            self.require(item, "result", lambda v: isinstance(v, str) and v in RESULTS, path, "未知接受结果。")
            ids = item.get("check_ids")
            if not isinstance(ids, list) or not ids or not all(nonempty(x) for x in ids):
                self.issue(path, f"acceptance.{item['id']}.check_ids", "missing_check", "接受记录必须关联非空检查 ID 列表。")
                continue
            if len(ids) != len(set(ids)):
                self.issue(path, f"acceptance.{item['id']}.check_ids", "duplicate_id", "接受记录的检查 ID 重复。")
            for identity in ids:
                check = by_id.get(identity)
                if check is None:
                    self.issue(path, f"acceptance.{item['id']}.check_ids", "missing_check", f"检查 ID 不存在：{identity}。")
                elif item.get("result") == "通过" and check.get("result") != "通过":
                    self.issue(path, f"acceptance.{item['id']}.result", "unmet_check", f"通过接受记录关联了未通过检查：{identity}。")
                elif item.get("result") == "通过" and manifest is not None:
                    if identity not in manifest["checks"]:
                        self.issue(path, f"checks.{identity}", "unbound_check", "通过接受项的检查 ID 未绑定到成果清单。")
                    for evidence in check.get("evidence", []) if isinstance(check.get("evidence"), list) else []:
                        if not nonempty(evidence):
                            continue
                        evidence_path = Path(os.path.abspath(path.parent / evidence))
                        root = Path(manifest["scope"]["root"])
                        bound = manifest["files"].get(str(evidence_path.relative_to(root))) if evidence_path.is_relative_to(root) else None
                        check_paths = {Path(os.path.abspath(root / value)) for value in manifest["checks"].get(identity, {}).get("evidence", [])}
                        if bound is None or evidence_path not in check_paths:
                            self.issue(path, f"checks.{identity}.evidence", "unbound_evidence", "接受证据未列入成果清单。")
                        elif evidence_path.is_file():
                            try:
                                if sha(evidence_path.read_bytes()) != bound["sha256"]:
                                    self.issue(path, f"checks.{identity}.evidence", "stale_evidence", "接受证据内容已变化，需重新核对。")
                            except OSError as exc:
                                self.issue(evidence_path, "evidence", "unreadable_file", str(exc))

    def manifest_binding(self, obj, path, task, required=False):
        value = obj.get("manifest")
        if value is None:
            if required:
                self.issue(path, "manifest", "missing_manifest", "已通过验收或完成记录必须绑定成果清单。")
            return None
        manifest_path = self.reference(path, value, "manifest")
        if manifest_path is None:
            return None
        try:
            manifest = load_manifest(manifest_path)
        except InputError as exc:
            self.findings.append(exc.finding)
            return None
        if manifest["task"].get("id") != task.get("id") or manifest["task"].get("revision") != task.get("revision"):
            self.issue(path, "manifest.task", "stale_manifest", "成果清单未绑定当前任务与要求修订。")
        return manifest

    def execution_record(self, path, task):
        obj = self.read(path)
        if obj is None:
            return
        if not isinstance(obj.get("kind"), str) or obj["kind"] not in {"dispatch", "return", "checkpoint"}:
            self.issue(path, "kind", "invalid_kind", "records 只接受 dispatch/return/checkpoint。")
        self.binding(obj, path, task)
        if obj.get("kind") in ("dispatch", "return"):
            self.require(obj, "dispatch_id", nonempty, path, "派发与返回必须声明 dispatch_id。")
            if self.require(obj, "workspace", nonempty, path, "派发与返回必须声明 workspace。"):
                if not (path.parent / obj["workspace"]).is_dir():
                    self.issue(path, "workspace", "missing_workspace", "工作区目录不可达。")
            self.require(obj, "write_scope", lambda value: isinstance(value, list) and all(nonempty(x) for x in value), path,
                         "派发与返回必须声明 write_scope 路径列表；只读任务用 []。")
        else:
            self.manifest_binding(obj, path, task, task.get("status") == "已完成")
        if obj.get("slice_id") is not None:
            item = self.items.get(obj["slice_id"]) if isinstance(obj["slice_id"], str) else None
            if item is None or not positive(obj.get("slice_revision")) or obj["slice_revision"] != item.get("revision"):
                self.issue(path, "slice_revision", "stale_revision", "切片身份或修订不匹配。")
        returned = self.sources(obj, path)
        current = {source["id"]: source for source in self.sources(task, self.task)}
        declared = obj.get("source_versions", {})
        if not isinstance(declared, dict) or not all(version(x) for x in declared.values()):
            self.issue(path, "source_versions", "invalid_field", "source_versions 必须是来源 ID 到版本的映射。")
            declared = {}
        returned_versions = {**declared, **{source["id"]: source.get("revision") for source in returned}}
        for identity, effective in current.items():
            if identity not in returned_versions:
                self.issue(path, f"source_versions.{identity}", "missing_source", "执行记录缺少当前有效来源修订。")
            elif returned_versions[identity] != effective.get("revision"):
                self.issue(path, f"source_versions.{identity}", "stale_source", "执行记录的来源修订已失效。")
        for identity in declared:
            if identity not in current or declared[identity] != current[identity].get("revision"):
                self.issue(path, f"source_versions.{identity}", "stale_source", "声明来源不存在或修订不匹配。")
        for source in returned:
            effective = current.get(source["id"])
            if effective is None or source.get("revision") != effective.get("revision") or (
                    Path(os.path.abspath(path.parent / str(source.get("path")))) !=
                    Path(os.path.abspath(self.task.parent / str(effective.get("path"))))):
                self.issue(path, f"sources.{source['id']}", "stale_source", "执行记录使用的来源与当前有效来源不匹配。")
        for field in ("artifacts", "evidence"):
            values = obj.get(field, [])
            if not isinstance(values, list):
                self.issue(path, field, "invalid_field", "必须是路径列表。")
            else:
                for value in values:
                    self.reference(path, value, field)


def under_root(root, value, file, field):
    if not nonempty(value):
        raise InputError("invalid_path", "路径必须是非空字符串。", file, field)
    path = Path(os.path.abspath(root / value))
    try:
        relative = path.relative_to(root)
    except ValueError:
        raise InputError("outside_scope", "路径不得超出声明的 root。", file, field)
    if ".git" in relative.parts:
        raise InputError("excluded_path", "不采集 .git 内部文件。", file, field)
    cursor = root
    for part in relative.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise InputError("symlink", "声明路径不得包含符号链接。", file, field)
    return path


def scope_input(path):
    obj, _, fingerprint = load_yaml(path)
    if type(obj.get("schema_version")) is not int or obj["schema_version"] != 1:
        raise InputError("unsupported_version", "范围清单只支持 schema_version: 1。", path, "schema_version")
    if not nonempty(obj.get("root")):
        raise InputError("invalid_field", "root 必须明确声明。", path, "root")
    root = (path.parent / obj["root"]).resolve()
    if not root.is_dir():
        raise InputError("missing_root", "范围根目录不可达。", path, "root")
    if not isinstance(obj.get("paths"), list) or not obj["paths"] or not all(nonempty(x) for x in obj["paths"]):
        raise InputError("invalid_field", "paths 必须是非空文件/目录路径列表。", path, "paths")
    v = Validator(path)
    sources = v.entries(obj.get("sources", []), path, "sources")
    checks = v.entries(obj.get("checks", []), path, "checks")
    for source in sources:
        v.require(source, "revision", version, path, "来源必须声明 revision。")
        v.require(source, "path", nonempty, path, "来源必须声明 path。")
    for check in checks:
        v.require(check, "command", nonempty, path, "检查必须声明实际 command/方法标识。")
        values = check.get("evidence")
        if not isinstance(values, list) or not values or not all(nonempty(x) for x in values):
            v.issue(path, f"checks.{check['id']}.evidence", "missing_evidence", "检查必须声明非空证据路径列表。")
    if not isinstance(obj.get("conditions", {}), dict):
        v.issue(path, "conditions", "invalid_field", "conditions 必须是映射。")
    return obj, root, fingerprint, v.findings


def git_run(root, *args, allowed=(0,)):
    proc = subprocess.run(["git", "-C", str(root), *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          env={**os.environ, "GIT_OPTIONAL_LOCKS": "0", "LC_ALL": "C"}, timeout=30)
    if proc.returncode not in allowed:
        raise RuntimeError("Git 核对失败：" + proc.stderr.decode("utf-8", "replace").strip())
    return proc


def git_state(root, selectors, excluded):
    if shutil.which("git") is None:
        raise RuntimeError("找不到 Git；无法确定工作区版本，请安装 Git 后重试。")
    probe = git_run(root, "rev-parse", "--show-toplevel", allowed=(0, 128))
    if probe.returncode:
        # A non-Git project is valid; broken repositories must not silently degrade.
        error = probe.stderr.decode("utf-8", "replace")
        marker_present = any((directory / ".git").exists() or (directory / ".git").is_symlink()
                             for directory in (root, *root.parents))
        explicit_git_location = any(key in os.environ for key in
                                    ("GIT_DIR", "GIT_COMMON_DIR", "GIT_WORK_TREE"))
        if "not a git repository" not in error.lower() or marker_present or explicit_git_location:
            raise RuntimeError(error.strip())
        return {"available": False, "reason": "not_git_repository"}
    git_root = Path(os.fsdecode(probe.stdout.rstrip(b"\n"))).resolve()
    specs = [":(top,literal)" + str(p.relative_to(git_root)) for p in selectors]
    def relative(raw):
        path = git_root / os.fsdecode(raw)
        try:
            value = str(path.relative_to(root))
        except ValueError:
            return None
        return None if path in excluded or ".git" in Path(value).parts else value
    head_proc = git_run(root, "rev-parse", "--verify", "HEAD", allowed=(0, 128))
    head = head_proc.stdout.decode().strip() if head_proc.returncode == 0 else None
    index = {}
    for record in git_run(root, "ls-files", "--stage", "-z", "--", *specs).stdout.split(b"\0"):
        if not record:
            continue
        meta, name = record.split(b"\t", 1)
        value = relative(name)
        if value is not None:
            mode, blob, stage = meta.decode().split()
            index.setdefault(value, []).append({"mode": mode, "blob": blob, "stage": int(stage)})
    status, chunks = {}, git_run(root, "status", "--porcelain=v1", "-z", "--untracked-files=all", "--", *specs).stdout.split(b"\0")
    i = 0
    while i < len(chunks):
        record = chunks[i]
        i += 1
        if not record:
            continue
        xy, name = record[:2].decode(), record[3:]
        value = relative(name)
        old = None
        if "R" in xy or "C" in xy:
            old = relative(chunks[i])
            i += 1
        if value is not None:
            status[value] = {"index": xy[0], "worktree": xy[1], "original_path": old}
    return {"available": True, "root": str(git_root), "head": head, "index": index, "status": status,
            "untracked": sorted(k for k, value in status.items() if value["index"] == "?")}


def collect(task_path, scope_path, excluded):
    validator = Validator(task_path).run()
    findings = list(validator.findings)
    obj, root, scope_sha, scope_findings = scope_input(scope_path)
    findings.extend(scope_findings)
    manifest = {"schema_version": 1, "kind": "manifest", "complete": False,
                "scope": {"file": str(scope_path), "root": str(root), "sha256": scope_sha,
                          "definition": obj}, "task": {}, "slices": {}, "records": {},
                "files": {}, "selectors": {}, "sources": {}, "checks": {},
                "conditions": obj.get("conditions", {}) if isinstance(obj.get("conditions", {}), dict) else {}, "git": {},
                "excluded_paths": [str(p.relative_to(root)) for p in excluded if p.is_relative_to(root)]}
    task = validator.documents.get(task_path, ({}, "", ""))[0]
    manifest["task"] = {k: task[k] for k in ("id", "revision", "status", "phase", "delivery_target") if k in task}
    manifest["slices"] = {i: {k: item[k] for k in ("revision", "status", "depends_on", "assignee") if k in item}
                          for i, item in validator.items.items()}
    selected = set()
    def add_issue(exc):
        findings.append(exc.finding)
    def resolve(value, field):
        try:
            return under_root(root, value, scope_path, field)
        except InputError as exc:
            add_issue(exc)
            return None
    def add_file(path, role):
        if path in excluded:
            if role != "scope":
                findings.append({"file": str(path), "field": role, "code": "self_reference",
                                 "message": "输出清单不能同时充当来源、任务记录或证据。"})
            return
        try:
            under_root(root, str(path.relative_to(root)), path, role)
            if not path.is_file():
                raise InputError("missing_file", "受测文件或证据不可达。", path, role)
            data = path.read_bytes()
            value = manifest["files"].setdefault(str(path.relative_to(root)),
                                                {"sha256": sha(data), "bytes": len(data), "roles": []})
            if role not in value["roles"]:
                value["roles"].append(role)
        except ValueError:
            findings.append({"file": str(path), "field": role, "code": "outside_scope", "message": "被引用资料超出 root；请明确扩大 root。"})
        except InputError as exc:
            add_issue(exc)
        except OSError as exc:
            findings.append({"file": str(path), "field": role, "code": "unreadable_file", "message": str(exc)})
    for value in obj["paths"]:
        path = resolve(value, "paths")
        if path is None:
            continue
        selected.add(path)
        if path in excluded:
            findings.append({"file": str(path), "field": "paths", "code": "self_reference",
                             "message": "显式受测文件不能同时作为输出清单。"})
            continue
        key = str(path.relative_to(root))
        if not path.exists():
            findings.append({"file": str(path), "field": "paths", "code": "missing_file", "message": "声明范围不存在。"})
            continue
        manifest["selectors"][key] = "directory" if path.is_dir() else "file"
        if path.is_dir():
            def walk_error(exc):
                findings.append({"file": str(exc.filename), "field": "paths", "code": "unreadable_file", "message": str(exc)})
            for directory, dirs, files in os.walk(path, onerror=walk_error, followlinks=False):
                dirs[:] = sorted(d for d in dirs if d != ".git")
                for name in list(dirs):
                    link = Path(directory) / name
                    if link.is_symlink():
                        dirs.remove(name)
                        findings.append({"file": str(link), "field": "paths", "code": "symlink", "message": "不采集符号链接目录。"})
                for name in sorted(files):
                    if name != ".git":
                        add_file(Path(directory) / name, "scope")
        else:
            add_file(path, "scope")
    # Failed parsing does not erase an observable file or its actual fingerprint.
    for path in sorted(validator.failed_documents):
        add_file(path, "record")
        selected.add(path)
    for path, (record, _, fingerprint) in validator.documents.items():
        add_file(path, "record")
        selected.add(path)
        key = str(path.relative_to(root)) if path.is_relative_to(root) else str(path)
        manifest["records"][key] = {"kind": record.get("kind"), "sha256": fingerprint}
        for source in record.get("sources", []) if isinstance(record.get("sources", []), list) else []:
            if isinstance(source, dict) and nonempty(source.get("id")) and nonempty(source.get("path")):
                source_path = Path(os.path.abspath(path.parent / source["path"]))
                add_file(source_path, "source")
                selected.add(source_path)
                manifest["sources"][key + ":" + source["id"]] = {
                    "path": str(source_path), "revision": source.get("revision")}
        if record.get("kind") == "verification" and isinstance(record.get("checks"), list):
            for check in record["checks"]:
                if isinstance(check, dict) and isinstance(check.get("evidence"), list):
                    for evidence in check["evidence"]:
                        if nonempty(evidence):
                            evidence_path = Path(os.path.abspath(path.parent / evidence))
                            add_file(evidence_path, "evidence")
                            selected.add(evidence_path)
        for field in ("artifacts", "evidence"):
            if isinstance(record.get(field), list):
                for value in record[field]:
                    if nonempty(value):
                        record_path = Path(os.path.abspath(path.parent / value))
                        add_file(record_path, field)
                        selected.add(record_path)
    for source in obj.get("sources", []) if isinstance(obj.get("sources", []), list) else []:
        if not isinstance(source, dict) or not nonempty(source.get("id")):
            continue
        path = resolve(source.get("path"), f"sources.{source['id']}.path")
        if path:
            add_file(path, "source")
            selected.add(path)
            manifest["sources"]["scope:" + source["id"]] = {"path": str(path), "revision": source.get("revision")}
    for check in obj.get("checks", []) if isinstance(obj.get("checks", []), list) else []:
        if not isinstance(check, dict) or not nonempty(check.get("id")):
            continue
        manifest["checks"][check["id"]] = check
        if isinstance(check.get("evidence"), list):
            for evidence in check["evidence"]:
                path = resolve(evidence, f"checks.{check['id']}.evidence")
                if path:
                    add_file(path, "evidence")
                    selected.add(path)
    for value in manifest["files"].values():
        value["roles"].sort()
    git_selectors = sorted(p for p in selected if p.is_relative_to(root))
    manifest["git"] = git_state(root, git_selectors, excluded)
    manifest["complete"] = not findings
    return manifest, findings


def observed(manifest):
    values = {}
    for group in ("task", "slices", "records", "sources", "checks", "conditions", "selectors"):
        for key, value in manifest[group].items():
            if isinstance(value, dict) and group in {"task", "slices", "sources"}:
                for field, item in value.items():
                    values[(group, f"{key}.{field}")] = item
            else:
                values[(group, key)] = value
    for key, value in manifest["files"].items():
        values[("files", key)] = value
    values[("scope", "definition")] = manifest["scope"]["definition"]
    values[("scope", "sha256")] = manifest["scope"]["sha256"]
    for key, value in manifest["git"].items():
        if key in {"index", "status"}:
            for path, entry in value.items():
                values[("git_" + key, path)] = entry
        else:
            values[("git", key)] = value
    return values


def load_manifest(path):
    obj, _, _ = load_yaml(path)
    if type(obj.get("schema_version")) is not int or obj["schema_version"] != 1:
        raise InputError("unsupported_version", "成果清单只支持 schema_version: 1。", path, "schema_version")
    if obj.get("kind") != "manifest" or obj.get("complete") is not True:
        raise InputError("invalid_manifest", "必须提供完整的 kind: manifest 清单。", path)
    for field in ("task", "slices", "records", "files", "selectors", "sources", "checks", "conditions", "git", "scope"):
        if not isinstance(obj.get(field), dict):
            raise InputError("invalid_manifest", f"缺少有效 {field} 映射。", path, field)
    if not nonempty(obj["task"].get("id")) or not positive(obj["task"].get("revision")):
        raise InputError("invalid_manifest", "清单必须绑定任务身份与正整数要求修订。", path, "task")
    for field in ("root", "file", "sha256"):
        if not nonempty(obj["scope"].get(field)):
            raise InputError("invalid_manifest", f"scope.{field} 无效。", path, field)
    if not isinstance(obj["scope"].get("definition"), dict):
        raise InputError("invalid_manifest", "缺少范围定义。", path, "scope.definition")
    for key, value in obj["files"].items():
        if not isinstance(value, dict) or not isinstance(value.get("sha256"), str) or not SHA256.fullmatch(value["sha256"]):
            raise InputError("invalid_manifest", "文件条目缺少 SHA-256。", path, f"files.{key}")
    for identity, check in obj["checks"].items():
        if (not isinstance(check, dict) or check.get("id") != identity or not nonempty(check.get("command")) or
                not isinstance(check.get("evidence"), list) or not check["evidence"] or
                not all(nonempty(value) for value in check["evidence"])):
            raise InputError("invalid_manifest", "检查条目缺少 ID、方法标识或证据路径列表。", path, f"checks.{identity}")
    if type(obj["git"].get("available")) is not bool:
        raise InputError("invalid_manifest", "Git 可用性必须是布尔值。", path, "git.available")
    for field in ("index", "status"):
        if field in obj["git"] and not isinstance(obj["git"][field], dict):
            raise InputError("invalid_manifest", "Git 条目必须是按路径索引的映射。", path, f"git.{field}")
    excluded = obj.get("excluded_paths")
    if not isinstance(excluded, list) or not all(nonempty(x) for x in excluded):
        raise InputError("invalid_manifest", "excluded_paths 必须是路径列表。", path)
    root = Path(obj["scope"]["root"])
    # Do not let edited exclusions conceal changes in deliverables.
    if excluded != ([str(path.relative_to(root))] if path.is_relative_to(root) else []):
        raise InputError("invalid_manifest", "排除范围必须恰好是当前清单本身；移动清单后请重新快照。", path, "excluded_paths")
    return obj


def compare(task, path):
    before = load_manifest(path)
    current_findings = []
    try:
        after, current_findings = collect(task, Path(before["scope"]["file"]), {path})
        actual = observed(after)
    except InputError as exc:
        current_findings.append(exc.finding)
        after, actual = None, {}
    previous = observed(before)
    entries = []
    missing = object()
    for group, key in sorted(previous.keys() | actual.keys()):
        old, new = previous.get((group, key), missing), actual.get((group, key), missing)
        state = "unverifiable" if after is None else "unchanged" if old == new else "missing" if new is missing else "changed"
        if group == "conditions" and any(f["code"] == "invalid_field" and f["field"] == "conditions"
                                        for f in current_findings):
            state = "unverifiable"
        if group in {"files", "records"} and new is missing and (Path(before["scope"]["root"]) / key).is_file():
            state = "unverifiable"
        if group == "files" and any(f["code"] in {"unreadable_file", "symlink"} and
                f.get("file") == str(Path(before["scope"]["root"]) / key) for f in current_findings):
            state = "unverifiable"
        category = "task_status" if group == "task" and key == "status" else (
            "requirement_revision" if (group == "task" and key == "revision") or
            (group == "slices" and key.endswith(".revision")) else group)
        entries.append({"category": category, "field": key, "state": state,
                        "before": None if old is missing else old, "after": None if new is missing else new,
                        "reusable": state == "unchanged"})
    summary = {state: sum(x["state"] == state for x in entries)
               for state in ("unchanged", "changed", "missing", "unverifiable")}
    findings = list(current_findings)
    findings.extend({"file": str(path), "field": f"{entry['category']}.{entry['field']}",
                     "code": entry["state"], "message": "当前输入与既有证据绑定内容存在差异或缺口。"}
                    for entry in entries if entry["state"] != "unchanged")
    return {"comparisons": entries, "summary": summary, "findings": findings,
            "task_identity": after["task"] if after else None}


def emit(command, task, findings, code, **extra):
    payload = {"command": command, "task": str(task) if task else None,
               "status": "ok" if code == 0 else "error" if code == 2 else "issues",
               "findings": findings, "applicability": APPLICABILITY, **extra}
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return code


class Parser(argparse.ArgumentParser):
    def error(self, message):
        emit(None, None, [{"file": None, "field": "arguments", "code": "invalid_arguments", "message": message}], 2)
        raise SystemExit(2)


def main(argv=None):
    parser = Parser(description=__doc__, epilog=PROTOCOL, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("validate", "snapshot", "compare"):
        child = commands.add_parser(name, epilog=PROTOCOL, formatter_class=argparse.RawDescriptionHelpFormatter)
        child.add_argument("--task", required=True, help="Local task README.md")
        child.add_argument("--format", choices=["json"], default="json")
        if name == "snapshot":
            child.add_argument("--scope", required=True, help="YAML/JSON file declaring the capture scope")
            child.add_argument("--output", required=True, help="Destination JSON manifest")
        elif name == "compare":
            child.add_argument("--manifest", required=True, help="Previously captured manifest")
    args = parser.parse_args(argv)
    task = Path(args.task).resolve()
    try:
        if args.command == "validate":
            validation = Validator(task).run()
            return emit(args.command, task, validation.findings, 1 if validation.findings else 0,
                        records=[str(path) for path in validation.documents])
        if args.command == "snapshot":
            output, scope = Path(args.output).resolve(), Path(args.scope).resolve()
            if output in {task, scope}:
                raise InputError("self_reference", "输出路径不能覆盖任务入口或范围定义。", output)
            if output.exists():
                try:
                    load_manifest(output)
                except InputError:
                    raise InputError("unsafe_output", "已有输出文件不是本工具的有效清单；请另选输出路径。", output)
            manifest, findings = collect(task, scope, {output})
            if findings:
                return emit(args.command, task, findings, 1, output=str(output), written=False)
            output.parent.mkdir(parents=True, exist_ok=True)
            # Write only after all inputs have been collected successfully.
            output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            return emit(args.command, task, [], 0, output=str(output), written=True,
                        files=len(manifest["files"]), task_identity=manifest["task"])
        result = compare(task, Path(args.manifest).resolve())
        findings = result.pop("findings")
        return emit(args.command, task, findings, 1 if findings else 0, **result)
    except InputError as exc:
        return emit(args.command, task, [exc.finding], 1)
    except (OSError, RuntimeError, subprocess.SubprocessError, RecursionError) as exc:
        return emit(args.command, task, [{"file": str(task), "field": "runtime", "code": "runtime_error", "message": str(exc)}], 2)


if __name__ == "__main__":
    sys.exit(main())
