"""Actual read-only GitHub P0 capability observations, never a merge approval."""
import base64
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from urllib.parse import quote

from .codex_probe import _output_directory
from .github import GitHubAdapter, AdapterError
from .harness_check import fingerprint
from .runtime import Controller
from .state import Blocked

MAX_RESPONSE_BYTES = 8 * 1024 * 1024
OID = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")


def _positive(value, field):
    if type(value) not in (int, float):
        raise Blocked("Positive finite GitHub P0 limit required: " + field)
    try:
        okay = math.isfinite(value) and value > 0
    except OverflowError:
        okay = False
    if not okay:
        raise Blocked("Positive finite GitHub P0 limit required: " + field)
    return value


def _object_pages(adapter, endpoint, key):
    pages = adapter._command(["api", "--hostname", adapter.hostname, endpoint, "--paginate", "--slurp"])
    if (not isinstance(pages, list) or not pages
            or any(not isinstance(page, dict) or not isinstance(page.get(key), list) for page in pages)):
        raise AdapterError("Malformed paginated " + key + " response")
    rows = [row for page in pages for row in page[key]]
    if any(not isinstance(row, dict) for row in rows):
        raise AdapterError("Malformed entry in " + key)
    return rows


def _check_observations(adapter, sha, required, require_success=True):
    if not isinstance(sha, str) or not OID.fullmatch(sha) or (require_success and not required):
        raise AdapterError("An actual immutable commit and nonempty server-required checks are needed")
    rows = _object_pages(adapter, f"repos/{adapter.repository}/commits/{sha}/check-runs?per_page=100", "check_runs")
    verdicts = {}
    for row in sorted(rows, key=lambda row: row.get("id", 0)):
        if row.get("head_sha") != sha or not isinstance(row.get("name"), str):
            raise AdapterError("Check-run identity does not match the queried immutable commit")
        verdicts[row["name"]] = {"passed": row.get("status") == "completed" and row.get("conclusion") == "success",
                                  "url": row.get("html_url"), "id": row.get("id"), "head_sha": sha}
    statuses = adapter._api(f"repos/{adapter.repository}/commits/{sha}/statuses?per_page=100", True)
    for status in statuses:
        if not isinstance(status, dict) or not isinstance(status.get("context"), str):
            raise AdapterError("Malformed commit status")
        if status["context"] not in verdicts:  # statuses endpoint is newest-first
            verdicts[status["context"]] = {"passed": status.get("state") == "success", "url": status.get("target_url"), "head_sha": sha}
    selected = {name: verdicts.get(name, {"passed": False, "reason": "missing", "head_sha": sha}) for name in required}
    if require_success and not all(item["passed"] for item in selected.values()):
        raise AdapterError("Required checks are absent or not successful on observed commit " + sha + ": " + json.dumps(selected))
    return {"head_sha": sha, "checks": selected, "query_succeeded": True,
            "check_run_count": len(rows), "status_count": len(statuses), "observed_names": sorted(verdicts),
            "all_required_passed": bool(required) and all(item["passed"] for item in selected.values())}


def _workflow_source(adapter, path, sha):
    if (not isinstance(path, str) or not path.startswith(".github/workflows/") or
            any(part in ("", ".", "..") for part in path.split("/")) or "\\" in path):
        raise AdapterError("Unsupported workflow source path")
    data = adapter._api(f"repos/{adapter.repository}/contents/{quote(path, safe='/')}?ref={quote(sha, safe='')}")
    if (not isinstance(data, dict) or data.get("type") != "file" or data.get("encoding") != "base64"
            or not isinstance(data.get("content"), str) or not OID.fullmatch(str(data.get("sha", "")))):
        raise AdapterError("Workflow source content is missing/inaccessible")
    try:
        raw = base64.b64decode("".join(data["content"].splitlines()), validate=True)
    except (ValueError, TypeError) as exc:
        raise AdapterError("Workflow source encoding is invalid") from exc
    if not raw or len(raw) > MAX_RESPONSE_BYTES:
        raise AdapterError("Workflow source is empty or exceeds the inspection limit")
    return {"path": path, "git_blob": data["sha"], "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw), "at_commit": sha}


def probe_github(config, controller, output_dir, *, project_controller=None, executable=None):
    """Observe authenticated APIs, permissions, tasks, checks, workflows and real rules.

    All commands are GET-style reads through the provided held temporary
    Controller. Empty/missing/inaccessible required evidence blocks readiness.
    No config 'rules_verified' boolean is accepted as proof.
    """
    result = {"version": 1, "kind": "github_p0_observations", "status": "blocked",
              "detail": "GitHub capabilities have not been fully observed", "observations": {}, "logs": {},
              "config_sha256": fingerprint(config), "read_only": True,
              "automatic_merge_rules": {"status": "blocked", "detail": "Automatic merge capability has not been observed"},
              "notice": "Scoped API and existing-CI observations; no writes, PR creation, rule changes, or delivery authorization."}
    if config.get("mode") != "github":
        return {**result, "status": "not_applicable", "detail": "Local mode never invokes GitHub"}
    if not isinstance(controller, Controller) or not controller.entered or not controller.run_lock.is_locked:
        raise Blocked("GitHub P0 requires an actual entered bounded controller")
    github = config.get("github", {})
    options = config.get("p0", {})
    limits = config.get("limits", {})
    if not isinstance(github, dict) or not isinstance(options, dict) or not isinstance(limits, dict):
        raise Blocked("GitHub P0 requires github/p0/limits objects")
    branch = github.get("target_branch")
    if not isinstance(branch, str) or not branch.strip() or any(ord(c) < 32 for c in branch):
        raise Blocked("github.target_branch must explicitly identify the actual protected target branch")
    request_timeout = _positive(limits.get("request_seconds"), "limits.request_seconds")
    total = _positive(options.get("github_total_seconds", limits.get("ci_wait_seconds")), "p0.github_total_seconds")
    maximum = options.get("github_max_requests", 50)
    if type(maximum) is not int or not 1 <= maximum <= 100:
        raise Blocked("p0.github_max_requests must be an integer in 1..100")
    command = executable or shutil.which("gh")
    if not command or not Path(command).is_absolute():
        raise Blocked("An actual resolved gh executable is required")
    output = _output_directory(output_dir, config["repository_root"], project_controller, "github-p0")
    result["artifact_directory"] = str(output)
    deadline = time.monotonic() + total
    calls = 0

    def observed_run(argv, timeout):
        nonlocal calls
        if not argv or argv[0] != "gh" or (argv[1:3] != ["auth", "status"] and argv[1:2] != ["api"]):
            raise AdapterError("P0 runner accepts only gh auth status and API reads")
        if any(arg in argv for arg in ("--method", "-X", "--field", "-f", "--raw-field", "-F", "--input", "--show-token")):
            raise AdapterError("Mutating or credential-revealing GitHub flags are refused")
        calls += 1
        if calls > maximum:
            raise AdapterError("GitHub P0 request bound exhausted")
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise AdapterError("GitHub P0 total deadline exhausted")
        name = "github-p0-%03d" % calls
        stdout = output / (name + ".stdout")
        env = os.environ.copy()
        env["GH_PROMPT_DISABLED"] = "1"
        actual = [command, *argv[1:]]
        try:
            execution = controller.execute(actual, controller.root, name, stdout,
                                           timeout=min(timeout, request_timeout, remaining), env=env,
                                           separate_stderr=True)
        except (Blocked, OSError, ValueError) as exc:
            result["logs"][name] = {"argv": actual, "error": str(exc)}
            raise AdapterError("Bounded GitHub read failed: " + str(exc)) from exc
        record = {"argv": actual, "execution": execution}
        for label, path in (("stdout", stdout), ("stderr", Path(execution["stderr_log"]))):
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(65536), b""):
                    digest.update(chunk)
            record[label] = {"path": str(path), "sha256": digest.hexdigest(), "bytes": path.stat().st_size}
        result["logs"][name] = record
        if execution["reason"] or not execution["stopped"]:
            raise AdapterError("GitHub read timed out/cancelled or stop is unknown; no capability inferred")
        if record["stdout"]["bytes"] > MAX_RESPONSE_BYTES or record["stderr"]["bytes"] > MAX_RESPONSE_BYTES:
            raise AdapterError("GitHub response exceeds bounded parser size")
        return subprocess.CompletedProcess(actual, execution["exit_code"], stdout.read_text(), Path(execution["stderr_log"]).read_text())

    try:
        adapter = GitHubAdapter(config, run=observed_run)
        adapter._deadline = deadline
        auth = adapter._command(["auth", "status", "--hostname", adapter.hostname], json_output=False)
        user = adapter._api("user")
        if not isinstance(user, dict) or not user.get("login") or type(user.get("id")) is not int:
            raise AdapterError("Authenticated user identity is not observable")
        result["observations"]["authentication"] = {"hostname": adapter.hostname, "login": user["login"], "id": user["id"], "status_output": auth}
        repository = adapter._api("repos/" + adapter.repository)
        permissions = repository.get("permissions") if isinstance(repository, dict) else None
        if (not isinstance(permissions, dict) or permissions.get("pull") is not True or permissions.get("push") is not True
                or repository.get("archived") is True or repository.get("disabled") is True
                or str(repository.get("full_name", "")).casefold() != adapter.repository.casefold()):
            raise AdapterError("Actual repository permissions do not support the configured collaboration path")
        result["observations"]["repository"] = {"full_name": repository.get("full_name"), "permissions": permissions,
                                                   "archived": repository.get("archived"), "disabled": repository.get("disabled")}
        actual_branch = adapter._api(f"repos/{adapter.repository}/branches/{quote(branch, safe='')}")
        target_sha = actual_branch.get("commit", {}).get("sha") if isinstance(actual_branch, dict) else None
        if not isinstance(target_sha, str) or not OID.fullmatch(target_sha) or actual_branch.get("name") != branch:
            raise AdapterError("Target branch identity/commit is missing or mismatched")
        result["observations"]["target"] = {"branch": branch, "sha": target_sha}
        tasks = adapter.list_tasks()
        result["observations"]["task_listing"] = {"count": len(tasks), "ids": [task["id"] for task in tasks]}
        issue = github.get("probe_issue_number")
        if issue is None and tasks:
            issue = tasks[0]["number"]
        if type(issue) is not int or issue <= 0:
            raise AdapterError("An existing task is required to observe actual task read/dependency behavior; set github.probe_issue_number or prepare a pilot issue")
        native_dependency_query = github.get("native_dependencies", True)
        if type(native_dependency_query) is not bool:
            raise AdapterError("github.native_dependencies must explicitly be boolean when present")
        task = adapter.read_task(issue)
        dependencies = adapter.dependencies(issue)
        result["observations"]["task_read"] = {"id": task["id"], "dependencies": [item["id"] for item in dependencies],
                                                  "native_dependency_query": native_dependency_query}
        prs = adapter._api(f"repos/{adapter.repository}/pulls?state=open&per_page=100", True)
        if any(not isinstance(pr, dict) or type(pr.get("number")) is not int for pr in prs):
            raise AdapterError("Malformed pull-request listing")
        pr_number = github.get("probe_pr_number") or (prs[0]["number"] if prs else None)
        pr_sample = adapter.read_pr(pr_number) if pr_number is not None else None
        result["observations"]["pull_requests"] = {"open_count": len(prs), "sample_number": pr_sample.get("number") if pr_sample else None,
                                                       "read_sample_observed": pr_sample is not None}
        declared = github.get("required_checks", [])
        if not isinstance(declared, list) or any(not isinstance(name, str) or not name for name in declared):
            raise AdapterError("github.required_checks must contain check names")
        result["observations"]["target_checks"] = _check_observations(adapter, target_sha, declared, require_success=False)
        workflows = _object_pages(adapter, f"repos/{adapter.repository}/actions/workflows?per_page=100", "workflows")
        active = [workflow for workflow in workflows if workflow.get("state") == "active"]
        requested = github.get("probe_workflow_paths")
        if requested is not None:
            if not isinstance(requested, list) or not requested or any(not isinstance(path, str) for path in requested):
                raise AdapterError("github.probe_workflow_paths must explicitly list source paths")
            active = [workflow for workflow in active if workflow.get("path") in requested]
            if {workflow.get("path") for workflow in active} != set(requested):
                raise AdapterError("Required probe workflow is absent or inactive")
        if len(active) > 25:
            raise AdapterError("More than 25 active workflows; explicitly narrow github.probe_workflow_paths for bounded source inspection")
        sources = {workflow["path"]: _workflow_source(adapter, workflow["path"], target_sha) for workflow in active}
        result["observations"]["workflows"] = {"active": [{key: workflow.get(key) for key in ("id", "name", "path", "state")} for workflow in active],
                                                   "current_sources": list(sources.values())}
        policy = github.get("baseline_policy")
        if policy == "review_only":
            result["automatic_merge_rules"] = {"status": "not_applicable", "detail": "Manual review/handoff mode; no automatic enforcing-rule capability is claimed."}
        else:
            try:
                rules = adapter.inspect_rules(branch, github.get("rules_mechanism", "rulesets"))
                desired = {"strict": "strict", "merge_queue": "queue", "queue": "queue"}.get(policy)
                if not rules.get("rules_verified") or rules.get("policy") != desired or desired is None:
                    raise AdapterError("Actual server target rules do not enforce the configured strict/queue policy")
                if not set(declared).issubset(set(rules["required_checks"])):
                    raise AdapterError("Configured required checks are not all enforced by the actual server rules")
                result["observations"]["server_rules"] = rules
                result["observations"]["automatic_required_checks"] = _check_observations(adapter, target_sha, rules["required_checks"])
                if not active:
                    raise AdapterError("No active workflow source was observable for automatic CI capability")
                if desired == "queue":
                    runs = _object_pages(adapter, f"repos/{adapter.repository}/actions/runs?event=merge_group&per_page=100", "workflow_runs")
                    allowed_ids = {workflow.get("id") for workflow in active}
                    candidates = [run for run in runs if run.get("event") == "merge_group" and run.get("status") == "completed"
                                  and run.get("conclusion") == "success" and run.get("workflow_id") in allowed_ids
                                  and (str(run.get("head_branch", "")).startswith("gh-readonly-queue/" + branch + "/")
                                       or any(item.get("base", {}).get("ref") == branch for item in run.get("pull_requests", []) if isinstance(item, dict)))]
                    requested_sha = github.get("probe_merge_group_sha")
                    if requested_sha:
                        candidates = [run for run in candidates if run.get("head_sha") == requested_sha]
                    if not candidates:
                        raise AdapterError("No actual successful merge_group run for this target/workflow scope was observable")
                    sample = candidates[0]
                    queue_sha = sample.get("head_sha")
                    queue_checks = _check_observations(adapter, queue_sha, rules["required_checks"])
                    workflow = next(item for item in active if item.get("id") == sample["workflow_id"])
                    prior_source = _workflow_source(adapter, workflow["path"], queue_sha)
                    if prior_source["sha256"] != sources[workflow["path"]]["sha256"]:
                        raise AdapterError("Current workflow source differs from the observed merge_group run; current queue behavior remains unproven")
                    result["observations"]["merge_group"] = {"run_id": sample.get("id"), "event": "merge_group",
                                                                 "checks": queue_checks, "workflow_source": prior_source}
                result["automatic_merge_rules"] = {"status": "verified", "detail": "Actual strict/queue target rules, required checks and applicable queue workflow observations were verified.", "policy": desired}
            except (AdapterError, Blocked, OSError, ValueError, KeyError, TypeError) as exc:
                result["automatic_merge_rules"] = {"status": "blocked", "detail": str(exc)}
        # Read target again: a capability sample spanning different targets must be repeated.
        after = adapter._api(f"repos/{adapter.repository}/branches/{quote(branch, safe='')}")
        if after.get("commit", {}).get("sha") != target_sha:
            result["automatic_merge_rules"] = {"status": "blocked", "detail": "Target advanced during the GitHub P0 observation window; refresh before automatic merge."}
            result["observations"]["target_snapshot_stale"] = True
        result.update(status="verified", detail="Actual authenticated task/PR/check/workflow read APIs and repository permissions were observed. Write APIs were not exercised; automatic enforcing rules and current check success are separate observations.")
    except (AdapterError, Blocked, OSError, ValueError, KeyError, TypeError) as exc:
        result.update(status="blocked", detail=str(exc))
    result["requests_started"] = calls
    path = output / "report.json"
    raw = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n"
    path.write_bytes(raw)
    return {**result, "report_path": str(path), "report_sha256": hashlib.sha256(raw).hexdigest()}
