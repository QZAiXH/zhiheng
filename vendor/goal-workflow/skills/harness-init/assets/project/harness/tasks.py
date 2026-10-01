"""Read explicitly selected upstream-style local Markdown tasks; never write progress."""
import hashlib
import os
import re
from graphlib import CycleError, TopologicalSorter
from pathlib import Path

from .harness_check import ID, MAX_TASKS, Validator

MAX_TASK_BYTES = 1024 * 1024
CHECKBOX = re.compile(r"^\s*[-*]\s+\[[ xX]\]\s+\[(AC-[A-Za-z0-9._-]+)\]\s+(.+)$")
ANY_CHECKBOX = re.compile(r"^\s*[-*]\s+\[[^]]*\]")


class TaskParseError(ValueError):
    def __init__(self, errors):
        self.errors = errors
        super().__init__("; ".join(str(item["path"]) + ": " + item["message"] for item in errors))


def _fail(path, message):
    raise TaskParseError([{"path": str(path), "message": message}])


def _relative_path(value, root, kind):
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        _fail(value, "must be an explicit repository-relative " + kind)
    parts = value.split("/")
    if any(part in ("", ".", "..") for part in parts) or any(ord(c) < 32 for c in value):
        _fail(value, "unsafe relative path")
    target = root
    for part in parts:
        target = target / part
        if target.is_symlink():
            _fail(value, "symlink paths are not supported")
    try:
        if not target.resolve().is_relative_to(root):
            _fail(value, "path leaves the repository")
    except (OSError, RuntimeError) as exc:
        _fail(value, "cannot resolve path: " + str(exc))
    return target


def _sections(content, source):
    title = None
    result = {}
    current = None
    fence = None
    for line in content.splitlines():
        stripped = line.lstrip()
        match = re.match(r"(`{3,}|~{3,})", stripped)
        if match:
            marker = match.group(1)
            if fence is None:
                fence = marker[0]
            elif marker[0] == fence:
                fence = None
            if current is not None:
                result[current].append(line)
            continue
        if fence is None:
            if line.startswith("# "):
                if title is not None:
                    _fail(source, "duplicate top-level title")
                title = line[2:].strip()
                continue
            if line.startswith("## "):
                current = line[3:].strip().casefold()
                if not current or current in result:
                    _fail(source, "empty or duplicate section: " + current)
                result[current] = []
                continue
        if current is not None:
            result[current].append(line)
    if fence is not None:
        _fail(source, "unclosed code fence")
    if not title:
        _fail(source, "missing # task title")
    return title, {key: "\n".join(lines).strip() for key, lines in result.items()}


def _acceptance(text, source):
    criteria = []
    seen = set()
    for line in text.splitlines():
        if not line.strip():
            if criteria:
                criteria[-1]["text"] += "\n"
            continue
        match = CHECKBOX.match(line)
        if match:
            aid, requirement = match.groups()
            if not ID.fullmatch(aid) or aid in seen:
                _fail(source, "invalid or duplicate acceptance ID: " + aid)
            seen.add(aid)
            criteria.append({"id": aid, "text": requirement})
        elif ANY_CHECKBOX.match(line) or not criteria:
            _fail(source, "each acceptance checkbox must have a stable [AC-id] and nonempty requirement")
        else:
            # Preserve continuation text and boundary conditions, rather than silently dropping them.
            criteria[-1]["text"] += "\n" + line
    if not criteria:
        _fail(source, "Acceptance Criteria must contain at least one [AC-id] checkbox")
    for criterion in criteria:
        criterion["text"] = criterion["text"].rstrip()
    return criteria


def _dependencies(text, source):
    if text.casefold() == "none":
        return []
    if not text:
        _fail(source, "Blocked by must explicitly say None or list stable task IDs")
    result = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith(("- ", "* ")):
            line = line[2:].strip()
        for token in line.split(","):
            token = token.strip()
            if not ID.fullmatch(token) or token.casefold() == "none":
                _fail(source, "malformed dependency; use stable task IDs, never numeric #NN: " + token)
            if token in result:
                _fail(source, "duplicate dependency: " + token)
            result.append(token)
    if not result:
        _fail(source, "empty dependency list; write None explicitly")
    return result


def parse_task(path, repository_root, report_mapping=None):
    """Read one task. `path` can be absolute under root or normalized repo-relative."""
    root = Path(repository_root).resolve()
    if not root.is_dir():
        _fail(repository_root, "repository_root must exist")
    source = Path(path)
    if source.is_absolute():
        try:
            relative = str(source.relative_to(root)).replace(os.sep, "/")
        except ValueError:
            _fail(source, "task file is outside repository_root")
    else:
        relative = str(source).replace(os.sep, "/")
    source = _relative_path(relative, root, "task file")
    if source.suffix.casefold() != ".md" or not source.is_file():
        _fail(relative, "task must be a regular .md file")
    try:
        with source.open("rb") as stream:
            raw = stream.read(MAX_TASK_BYTES + 1)
        if not raw or len(raw) > MAX_TASK_BYTES:
            _fail(relative, "task must contain 1..1048576 bytes")
        content = raw.decode("utf-8")
    except (OSError, UnicodeError) as exc:
        _fail(relative, "cannot read UTF-8 task: " + str(exc))
    title, sections = _sections(content, relative)
    for heading in ("task id", "description", "demo path", "acceptance criteria", "blocked by"):
        if not sections.get(heading):
            _fail(relative, "missing or empty ## " + heading)
    tid = sections["task id"]
    if not ID.fullmatch(tid):
        _fail(relative, "Task ID must be one stable nonnumeric identifier")
    acceptance = _acceptance(sections["acceptance criteria"], relative)
    dependencies = _dependencies(sections["blocked by"], relative)
    priority = sections.get("priority")
    if priority is not None and priority not in ("high", "medium", "low"):
        _fail(relative, "Priority must be high, medium, or low")
    if report_mapping is not None and not isinstance(report_mapping, dict):
        _fail("report_mapping", "must be an object keyed by stable task ID")
    reports = (report_mapping or {}).get(tid, {
        "note": "docs/task-" + tid + ".html",
        "walkthrough": "tasks/walkthrough-" + tid + ".md",
        "delivery": "docs/delivery-" + tid + ".md"})
    task = {"id": tid, "title": title, "description": sections["description"],
            "demo_path": sections["demo path"], "source_file": relative,
            "source_sha256": hashlib.sha256(raw).hexdigest(), "content": content,
            "dependencies": dependencies, "acceptance_ids": [entry["id"] for entry in acceptance],
            "acceptance_criteria": acceptance, "reports": reports}
    if priority is not None:
        task["priority"] = priority
    if "spec reference" in sections:
        task["spec_reference"] = sections["spec reference"]
    # Preserve all unknown sections in content; no Markdown checkbox becomes runtime progress.
    checker = Validator({})
    checker.root = root
    reports = checker.obj(reports, relative + ".reports")
    for name in ("note", "walkthrough", "delivery"):
        checker.safe_path(reports.get(name), relative + ".reports." + name, unique=True)
    if checker.errors:
        raise TaskParseError(checker.errors)
    return task


def load_tasks(repository_root, task_directories, report_mapping=None):
    """Load exactly the configured directories, then reject missing edges and cycles.

    Every .md file under those directories is a task, including malformed ones.
    Select feature task directories rather than broad documentation directories.
    Returns tasks sorted by stable ID; this is not a runnable-frontier decision.
    """
    root = Path(repository_root).resolve()
    if not root.is_dir():
        _fail(repository_root, "repository_root must exist")
    if not isinstance(task_directories, list) or not task_directories:
        _fail("task_directories", "must explicitly list one or more task directories")
    directories = []
    for relative in task_directories:
        directory = _relative_path(relative, root, "task directory")
        if not directory.is_dir():
            _fail(relative, "configured task directory is missing")
        for other in directories:
            if directory == other or directory.is_relative_to(other) or other.is_relative_to(directory):
                _fail(relative, "duplicate or overlapping configured task directory")
        directories.append(directory)
    files = []
    errors = []
    for directory in sorted(directories):
        def walk_error(exc):
            errors.append({"path": str(exc.filename), "message": "cannot enumerate task directory: " + str(exc)})
        for current, dirnames, filenames in os.walk(directory, followlinks=False, onerror=walk_error):
            dirnames.sort()
            for name in dirnames:
                candidate = Path(current) / name
                if candidate.is_symlink():
                    errors.append({"path": str(candidate), "message": "symlink task directory is not supported"})
            for name in sorted(filenames):
                if Path(name).suffix.casefold() == ".md":
                    files.append(Path(current) / name)
                    if len(files) > MAX_TASKS:
                        _fail("task_directories", "more than 500 task files")
    if errors:
        raise TaskParseError(errors)
    if not files:
        _fail("task_directories", "no Markdown tasks found in configured directories")
    tasks = []
    by_id = {}
    checker = Validator({})
    checker.root = root
    for path in sorted(files):
        try:
            task = parse_task(path, root, report_mapping)
            if task["id"] in by_id:
                errors.append({"path": task["source_file"], "message": "duplicate Task ID also in " + by_id[task["id"]]["source_file"]})
            by_id[task["id"]] = task
            tasks.append(task)
            for name, report in task["reports"].items():
                checker.safe_path(report, task["source_file"] + ".reports." + name, unique=True)
        except TaskParseError as exc:
            errors.extend(exc.errors)
    errors.extend(checker.errors)
    graph = {task["id"]: task["dependencies"] for task in tasks}
    for task in tasks:
        for dependency in task["dependencies"]:
            if dependency not in by_id:
                errors.append({"path": task["source_file"], "message": "missing dependency task: " + dependency})
    try:
        tuple(TopologicalSorter(graph).static_order())
    except CycleError as exc:
        errors.append({"path": "task_directories", "message": "dependency cycle: " + " -> ".join(exc.args[1])})
    if errors:
        raise TaskParseError(errors)
    return sorted(tasks, key=lambda task: task["id"])
