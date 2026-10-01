#!/usr/bin/env python3
"""Read-only, stdlib-only consistency checks; never an execution/verification engine."""
import argparse
import hashlib
import json
import math
import re
import sys
import unicodedata
from graphlib import CycleError, TopologicalSorter
from pathlib import Path

VERSION = 1
MAX_BUNDLE_BYTES = 2 * 1024 * 1024
MAX_REPORT_BYTES = 8 * 1024 * 1024
MAX_TASKS = 500
MAX_CHECKS = 100
MAX_ACCEPTANCE = 500
MAX_DEPTH = 32
ID = re.compile(r"[A-Za-z][A-Za-z0-9._-]{0,127}\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
GIT_OID = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
ENV_FIELDS = ("host", "model", "os", "git", "runtime", "skills_revision",
              "skills_path", "dependency_lock_sha256", "stop_method", "lock_backend")
LOCAL_LIMITS = ("command_seconds", "stop_grace_seconds", "implementation_seconds",
                "review_seconds", "repair_attempts", "task_seconds", "task_attempts")
GITHUB_LIMITS = ("request_seconds", "query_attempts", "ci_wait_seconds", "merge_queue_wait_seconds")
IDENTITY = ("mode", "repository_id", "task_id", "run_id", "attempt_id", "checkpoint_revision")
BINDING = ("H", "T", "C", "C_kind", "spec_sha256", "checks_sha256",
           "environment_sha256", "task_sha256")
NOTICE = ("Caller-supplied snapshots are untrusted. This helper checks structure, consistency "
          "and local report bytes only; it does not independently verify Git, execution, "
          "review, environment, delivery, or completion and never authorizes those actions.")


def fingerprint(value):
    """Contract hash: UTF-8 canonical JSON, sorted keys, no spaces, literal Unicode."""
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                     allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def check_fingerprint(config):
    """Bind required checks, their resource limits, and mode-specific baseline policy."""
    policy = {"checks": config["checks"], "limits": config["limits"]}
    for name in ("host", "knowledge", "push"):
        if name in config:
            policy[name] = config[name]
    if config.get("mode") == "github":
        policy["github"] = config["github"]
    return fingerprint(policy)


def scaffold(mode):
    if mode not in ("local", "github"):
        raise ValueError("mode must be local or github")
    limits = LOCAL_LIMITS + (GITHUB_LIMITS if mode == "github" else ())
    config = {"mode": mode, "repository_id": "", "repository_root": "",
              "environment": {name: "" for name in ENV_FIELDS},
              "limits": {name: None for name in limits}, "checks": []}
    if mode == "github":
        config["github"] = {"server": "", "repository": "", "gh_version": "",
                            "baseline_policy": ""}
    return {"version": VERSION, "config": config, "tasks": [], "checkpoint": None}


class Validator:
    def __init__(self, bundle):
        self.bundle = bundle
        self.errors = []
        self.root = None
        self.checks = {}
        self.tasks = {}
        self.config = {}
        self.checkpoint = None
        self.report_paths = {}

    def fail(self, path, message):
        self.errors.append({"path": path, "message": message})

    def obj(self, value, path):
        if not isinstance(value, dict):
            self.fail(path, "must be an object")
            return {}
        return value

    def array(self, value, path, minimum=0, maximum=MAX_ACCEPTANCE):
        if not isinstance(value, list):
            self.fail(path, "must be an array")
            return []
        if not minimum <= len(value) <= maximum:
            self.fail(path, "must contain %d..%d entries" % (minimum, maximum))
        return value[:maximum]

    def string(self, value, path, pattern=None):
        if not isinstance(value, str) or not value.strip() or len(value) > 4096:
            self.fail(path, "must be a nonempty string of at most 4096 characters")
            return ""
        if value != value.strip() or any(ord(c) < 32 for c in value):
            self.fail(path, "must not contain outer whitespace or control characters")
        if pattern and not pattern.fullmatch(value):
            self.fail(path, "has an invalid identifier or fingerprint format")
        return value

    def number(self, value, path, minimum=0, positive=False, integer=False):
        valid = type(value) in (int, float)
        if integer:
            valid = type(value) is int
        if valid:
            try:
                valid = math.isfinite(value)
            except (OverflowError, TypeError):
                valid = False
        if not valid or value < minimum or (positive and value <= 0):
            self.fail(path, "must be a %sfinite %snumber" %
                      ("positive " if positive else "nonnegative ", "integer " if integer else ""))
            return None
        return value

    def ids(self, value, path, minimum=0, maximum=MAX_ACCEPTANCE):
        result = []
        seen = set()
        for i, item in enumerate(self.array(value, path, minimum, maximum)):
            item = self.string(item, "%s[%d]" % (path, i), ID)
            if item in seen:
                self.fail(path, "duplicate ID: " + item)
            seen.add(item)
            result.append(item)
        return result

    def safe_path(self, value, path, unique=False):
        value = self.string(value, path)
        if not value:
            return None
        parts = value.split("/")
        if (value.startswith("/") or "\\" in value or ":" in value or
                any(p in ("", ".", "..") or p.endswith((".", " ")) for p in parts) or
                any(ord(c) < 32 or ord(c) == 127 for c in value) or
                any(re.fullmatch(r"(?i)(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?", p) for p in parts)):
            self.fail(path, "must be a normalized, portable repository-relative file path")
            return None
        key = unicodedata.normalize("NFC", value).casefold()
        if unique:
            for previous, owner in self.report_paths.items():
                if key == previous or key.startswith(previous + "/") or previous.startswith(key + "/"):
                    self.fail(path, "report path collides with " + owner)
            self.report_paths[key] = path
        if self.root is None:
            return None
        target = self.root.joinpath(*parts)
        try:
            cursor = self.root
            for part in parts:
                cursor = cursor / part
                if cursor.is_symlink():
                    self.fail(path, "symlink components are not accepted")
                    return None
            if not target.resolve().is_relative_to(self.root):
                self.fail(path, "path escapes repository_root")
                return None
            if target.exists() and not target.is_file():
                self.fail(path, "existing report path must be a regular file")
                return None
        except (OSError, RuntimeError) as exc:
            self.fail(path, "cannot inspect path: " + str(exc))
            return None
        return target

    def preflight(self):
        self.errors = []
        self.root = None
        self.checks = {}
        self.tasks = {}
        self.report_paths = {}
        self.checkpoint = None
        b = self.obj(self.bundle, "bundle")
        if type(b.get("version")) is not int or b.get("version") != VERSION:
            self.fail("version", "must be integer 1")
        c = self.config = self.obj(b.get("config"), "config")
        mode = c.get("mode")
        if mode not in ("local", "github"):
            self.fail("config.mode", "must explicitly be local or github; no mode inference")
        self.string(c.get("repository_id"), "config.repository_id")
        root = self.string(c.get("repository_root"), "config.repository_root")
        if root:
            try:
                p = Path(root)
                if not p.is_absolute() or not p.is_dir():
                    self.fail("config.repository_root", "must be an existing absolute directory")
                else:
                    self.root = p.resolve()
            except (OSError, RuntimeError) as exc:
                self.fail("config.repository_root", "cannot inspect root: " + str(exc))
        env = self.obj(c.get("environment"), "config.environment")
        for name in ENV_FIELDS:
            self.string(env.get(name), "config.environment." + name,
                        SHA256 if name == "dependency_lock_sha256" else None)
        if mode == "github":
            gh = self.obj(c.get("github"), "config.github")
            for name in ("server", "repository", "gh_version"):
                self.string(gh.get(name), "config.github." + name)
            if gh.get("baseline_policy") not in ("strict", "merge_queue", "review_only"):
                self.fail("config.github.baseline_policy", "must be strict, merge_queue, or review_only")
        limits = self.obj(c.get("limits"), "config.limits")
        required = LOCAL_LIMITS + (GITHUB_LIMITS if mode == "github" else ())
        for name in required:
            self.number(limits.get(name), "config.limits." + name,
                        positive=True, integer=name.endswith("attempts"))
        # Optional limits also fail closed rather than silently accepting unlimited values.
        for name in sorted(set(limits) - set(required)):
            self.number(limits[name], "config.limits." + name,
                        positive=True, integer=name.endswith("attempts"))
        repair = limits.get("repair_attempts")
        if type(repair) in (int, float) and repair > 2:
            self.fail("config.limits.repair_attempts", "must not exceed the source plan's two repair rounds")
        for i, raw in enumerate(self.array(c.get("checks"), "config.checks", 1, MAX_CHECKS)):
            path = "config.checks[%d]" % i
            check = self.obj(raw, path)
            cid = self.string(check.get("id"), path + ".id", ID)
            if cid in self.checks:
                self.fail(path + ".id", "duplicate check ID")
            if cid == "review":
                self.fail(path + ".id", "review is reserved for independent review evidence")
            self.checks[cid] = check
            if check.get("kind") not in ("test", "tool"):
                self.fail(path + ".kind", "must be test or tool")
            for j, arg in enumerate(self.array(check.get("argv"), path + ".argv", 1, 100)):
                self.string(arg, "%s.argv[%d]" % (path, j))
            timeout = self.number(check.get("timeout_seconds"), path + ".timeout_seconds", positive=True)
            command_limit = limits.get("command_seconds")
            if timeout is not None and type(command_limit) in (int, float) and timeout > command_limit:
                self.fail(path + ".timeout_seconds", "exceeds command_seconds")
            if check.get("kind") == "test":
                self.number(check.get("min_executed"), path + ".min_executed", positive=True, integer=True)
        graph = {}
        for i, raw in enumerate(self.array(b.get("tasks"), "tasks", 1, MAX_TASKS)):
            path = "tasks[%d]" % i
            task = self.obj(raw, path)
            tid = self.string(task.get("id"), path + ".id", ID)
            if tid in self.tasks:
                self.fail(path + ".id", "duplicate task ID")
            self.tasks[tid] = task
            graph[tid] = self.ids(task.get("dependencies"), path + ".dependencies", maximum=MAX_TASKS)
            self.ids(task.get("acceptance_ids"), path + ".acceptance_ids", 1)
            reports = self.obj(task.get("reports"), path + ".reports")
            for name in ("note", "walkthrough", "delivery"):
                self.safe_path(reports.get(name), path + ".reports." + name, unique=True)
        for tid, dependencies in graph.items():
            for dep in dependencies:
                if dep not in graph:
                    self.fail("tasks." + tid + ".dependencies", "missing task: " + dep)
        try:
            tuple(TopologicalSorter(graph).static_order())
        except CycleError as exc:
            cycle = exc.args[1] if len(exc.args) > 1 else []
            self.fail("tasks.dependencies", "dependency cycle: " + " -> ".join(cycle))
        if "checkpoint" not in b:
            self.fail("checkpoint", "must explicitly be null for a new run or an object")
        elif b["checkpoint"] is not None:
            cp = self.checkpoint = self.obj(b["checkpoint"], "checkpoint")
            for name in ("run_id", "task_id", "attempt_id"):
                self.string(cp.get(name), "checkpoint." + name, ID)
            if cp.get("mode") != mode:
                self.fail("checkpoint.mode", "mode mismatch; use matching config or a separately initialized run")
            if cp.get("repository_id") != c.get("repository_id"):
                self.fail("checkpoint.repository_id", "repository mismatch")
            if not isinstance(cp.get("task_id"), str) or cp.get("task_id") not in self.tasks:
                self.fail("checkpoint.task_id", "unknown task")
            self.number(cp.get("revision"), "checkpoint.revision", integer=True)
            consumed = self.obj(cp.get("consumed"), "checkpoint.consumed")
            for name, limit_name in (("task_seconds", "task_seconds"), ("attempts_started", "task_attempts"),
                                     ("repair_attempts", "repair_attempts")):
                val = self.number(consumed.get(name), "checkpoint.consumed." + name,
                                  integer=name != "task_seconds")
                limit = limits.get(limit_name)
                if val is not None and type(limit) in (int, float) and val > limit:
                    self.fail("checkpoint.consumed." + name, "exceeds configured cumulative budget")
        return not self.errors

    def binding(self, value, path):
        data = self.obj(value, path)
        for name in BINDING:
            if name == "C_kind":
                if data.get(name) not in ("commit", "tree"):
                    self.fail(path + ".C_kind", "must be commit or tree")
            else:
                self.string(data.get(name), path + "." + name,
                            GIT_OID if name in ("H", "T", "C") else SHA256)
        return data

    def report(self, value, path):
        data = self.obj(value, path)
        target = self.safe_path(data.get("path"), path + ".path", unique=True)
        sha = self.string(data.get("sha256"), path + ".sha256", SHA256)
        if target is not None:
            try:
                # Bounded read also rejects empty and oversized evidence reports.
                with target.open("rb") as stream:
                    raw = stream.read(MAX_REPORT_BYTES + 1)
                if not raw or len(raw) > MAX_REPORT_BYTES:
                    self.fail(path, "report must contain 1..8388608 bytes")
                elif hashlib.sha256(raw).hexdigest() != sha:
                    self.fail(path + ".sha256", "does not match report bytes")
            except (OSError, ValueError) as exc:
                self.fail(path, "cannot read report: " + str(exc))

    def evidence(self):
        if not self.preflight():
            return False
        b = self.bundle
        if self.checkpoint is None:
            self.fail("checkpoint", "evidence requires an existing checkpoint snapshot")
            return False
        cp = self.checkpoint
        expected_identity = {name: cp.get("revision" if name == "checkpoint_revision" else name)
                             for name in IDENTITY}
        task = self.tasks[cp["task_id"]]
        snapshots = {}
        for name in ("input", "result", "current"):
            snap = snapshots[name] = self.obj(b.get(name), name)
            for field in IDENTITY:
                if snap.get(field) != expected_identity[field] or type(snap.get(field)) is not type(expected_identity[field]):
                    self.fail(name + "." + field, "does not match checkpoint; stale or foreign snapshot")
            self.binding(snap.get("binding"), name + ".binding")
        baseline = self.obj(snapshots["input"].get("binding"), "input.binding")
        for name in ("result", "current"):
            candidate = self.obj(snapshots[name].get("binding"), name + ".binding")
            for field in BINDING:
                if baseline.get(field) != candidate.get(field):
                    self.fail(name + ".binding." + field, "changed since input; evidence is stale")
        computed = {"checks_sha256": check_fingerprint(self.config),
                    "environment_sha256": fingerprint(self.config["environment"]),
                    "task_sha256": fingerprint(task)}
        for field, digest in computed.items():
            if baseline.get(field) != digest:
                self.fail("input.binding." + field, "does not match the supplied current configuration/task")
        required_acceptance = set(task["acceptance_ids"])
        actual = self.ids(snapshots["input"].get("required_acceptance_ids"), "input.required_acceptance_ids", 1)
        if set(actual) != required_acceptance:
            self.fail("input.required_acceptance_ids", "must exactly match task acceptance_ids")
        actual = self.ids(snapshots["input"].get("required_check_ids"), "input.required_check_ids", 1, MAX_CHECKS)
        if set(actual) != set(self.checks):
            self.fail("input.required_check_ids", "must exactly match configured checks")
        result = snapshots["result"]
        if result.get("stop_reason") != "completed":
            self.fail("result.stop_reason", "must be completed; cancellation, timeout and unknown outcomes block eligibility")
        if self.array(result.get("unresolved_items"), "result.unresolved_items"):
            self.fail("result.unresolved_items", "unresolved items block eligibility")
        seen = set()
        for i, raw in enumerate(self.array(result.get("checks"), "result.checks", 1, MAX_CHECKS)):
            path = "result.checks[%d]" % i
            check = self.obj(raw, path)
            cid = self.string(check.get("id"), path + ".id", ID)
            if cid in seen:
                self.fail(path + ".id", "duplicate result check ID")
            seen.add(cid)
            definition = self.checks.get(cid)
            if definition is None:
                self.fail(path + ".id", "unknown check ID")
                continue
            self.record_binding(check, path, baseline, cp)
            if check.get("status") != "passed":
                self.fail(path + ".status", "must be passed; missing, skipped and unknown are not success")
            if type(check.get("exit_code")) is not int or check.get("exit_code") != 0:
                self.fail(path + ".exit_code", "must be the recorded integer exit code 0")
            self.report(check.get("report"), path + ".report")
            counts = self.obj(check.get("counts"), path + ".counts")
            names = ("executed", "passed", "failed", "skipped") if definition["kind"] == "test" else ("evaluated", "failed")
            checked = {name: self.number(counts.get(name), path + ".counts." + name, integer=True) for name in names}
            if all(value is not None for value in checked.values()):
                if checked["failed"] != 0:
                    self.fail(path + ".counts.failed", "failures block eligibility")
                if definition["kind"] == "test":
                    if checked["executed"] < definition["min_executed"]:
                        self.fail(path + ".counts.executed", "fewer than the configured positive minimum tests executed")
                    if checked["skipped"] != 0:
                        self.fail(path + ".counts.skipped", "unexpected skips block eligibility")
                    if checked["executed"] != checked["passed"] + checked["failed"]:
                        self.fail(path + ".counts", "executed must equal passed plus failed; skipped is separate")
                elif checked["evaluated"] <= 0:
                    self.fail(path + ".counts.evaluated", "tool must evaluate at least one configured item")
        if seen != set(self.checks):
            self.fail("result.checks", "must contain exactly one result for every configured check")
        review = self.obj(result.get("review"), "result.review")
        self.record_binding(review, "result.review", baseline, cp)
        if review.get("status") != "completed" or review.get("independent") is not True:
            self.fail("result.review", "requires completed, independently performed review (claim still needs external verification)")
        self.report(review.get("report"), "result.review.report")
        if self.array(review.get("unresolved_items"), "result.review.unresolved_items"):
            self.fail("result.review.unresolved_items", "review remains unresolved")
        for i, raw in enumerate(self.array(review.get("findings"), "result.review.findings")):
            path = "result.review.findings[%d]" % i
            finding = self.obj(raw, path)
            if finding.get("severity") not in ("Blocking", "Warning", "Info"):
                self.fail(path + ".severity", "must be Blocking, Warning, or Info")
            self.string(finding.get("summary"), path + ".summary")
            if type(finding.get("resolved")) is not bool:
                self.fail(path + ".resolved", "must be a boolean")
            if finding.get("severity") == "Blocking" and finding.get("resolved") is not True:
                self.fail(path, "unresolved Blocking finding")
        seen = set()
        for i, raw in enumerate(self.array(result.get("acceptance"), "result.acceptance", 1)):
            path = "result.acceptance[%d]" % i
            entry = self.obj(raw, path)
            aid = self.string(entry.get("id"), path + ".id", ID)
            if aid in seen:
                self.fail(path + ".id", "duplicate acceptance ID")
            seen.add(aid)
            if entry.get("status") != "passed":
                self.fail(path + ".status", "required acceptance must be passed")
            refs = self.ids(entry.get("evidence_ids"), path + ".evidence_ids", 1)
            for ref in refs:
                if ref not in self.checks and ref != "review":
                    self.fail(path + ".evidence_ids", "unknown check or review reference: " + ref)
        if seen != required_acceptance:
            self.fail("result.acceptance", "must contain exactly one result for every required acceptance ID")
        return not self.errors

    def record_binding(self, record, path, baseline, checkpoint):
        bound = self.binding(record.get("binding"), path + ".binding")
        for field in BINDING:
            if bound.get(field) != baseline.get(field):
                self.fail(path + ".binding." + field, "does not match this attempt's input binding")
        for field in ("run_id", "attempt_id"):
            if record.get(field) != checkpoint[field]:
                self.fail(path + "." + field, "stale or foreign execution/review record")


def duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key: " + key)
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError("non-finite JSON number: " + value)


def check_depth(value, depth=0):
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("non-finite JSON number")
    if depth > MAX_DEPTH:
        raise ValueError("JSON nesting exceeds %d" % MAX_DEPTH)
    if isinstance(value, dict):
        for item in value.values():
            check_depth(item, depth + 1)
    elif isinstance(value, list):
        for item in value:
            check_depth(item, depth + 1)


def load_bundle(path):
    if not Path(path).is_file():
        raise ValueError("bundle must be a readable regular file")
    with Path(path).open("rb") as stream:
        raw = stream.read(MAX_BUNDLE_BYTES + 1)
    if len(raw) > MAX_BUNDLE_BYTES:
        raise ValueError("bundle exceeds %d bytes" % MAX_BUNDLE_BYTES)
    data = json.loads(raw.decode("utf-8"), object_pairs_hook=duplicate_keys, parse_constant=reject_constant)
    check_depth(data)
    return data


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    new = sub.add_parser("scaffold", help="print an intentionally incomplete draft; write no files")
    new.add_argument("--mode", choices=("local", "github"), required=True)
    for name in ("preflight", "evidence"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--bundle", required=True)
    args = parser.parse_args(argv)
    if args.command == "scaffold":
        print(json.dumps(scaffold(args.mode), ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    try:
        validator = Validator(load_bundle(args.bundle))
        okay = validator.preflight() if args.command == "preflight" else validator.evidence()
        errors = validator.errors
    except (OSError, UnicodeError, ValueError, RecursionError) as exc:
        okay = False
        errors = [{"path": "bundle", "message": str(exc)}]
    decision = ("configuration_consistent" if args.command == "preflight" else
                "eligible_for_independent_verification") if okay else "blocked"
    print(json.dumps({"version": VERSION, "command": args.command, "ok": okay,
                      "decision": decision, "errors": errors, "notice": NOTICE},
                     ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if okay else 1


if __name__ == "__main__":
    sys.exit(main())
