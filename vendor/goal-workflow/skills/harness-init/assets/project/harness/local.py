"""Git-native isolated candidate validation and conservative fast-forward delivery."""
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from .runtime import git
from .state import Blocked, atomic_json


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def file_fingerprint(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def safe_id(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,100}", value) or ".." in value:
        raise Blocked("invalid stable identifier")
    return value


def observed_git(root, *args, controller=None):
    return controller.git(*args, cwd=root) if controller is not None else git(root, *args)


def bindings(root, source, target, spec, checks, environment, controller=None):
    return {"H": observed_git(root, "rev-parse", source + "^{commit}", controller=controller),
            "T": observed_git(root, "rev-parse", target + "^{commit}", controller=controller),
            "spec_fingerprint": file_fingerprint(spec),
            "checks_fingerprint": fingerprint(checks), "environment_fingerprint": fingerprint(environment)}


def prepare_candidate(controller, source, target, task_id, attempt_id, spec, checks, environment):
    if not controller.entered:
        raise Blocked("run lock required")
    safe_id(task_id); safe_id(attempt_id)
    root = controller.root
    bound = bindings(root, source, target, spec, checks, environment, controller)
    location = controller.common / "harness-worktrees" / (task_id + "-" + attempt_id)
    if location.exists():
        raise Blocked("candidate already exists; reconcile or use a new attempt, never overwrite")
    location.parent.mkdir(exist_ok=True)
    controller.git("worktree", "add", "--detach", str(location), bound["T"])
    try:
        controller.git("-c", "user.name=Harness", "-c", "user.email=harness@localhost", "merge", "--no-ff", "--no-edit", bound["H"], cwd=location)
    except Blocked:
        # Preserve conflict and worktree for diagnosis; never touch user's checkout.
        raise Blocked(f"candidate combination conflict; preserved at {location}")
    bound.update({"C": controller.git("rev-parse", "HEAD", cwd=location), "tree": controller.git("rev-parse", "HEAD^{tree}", cwd=location),
                  "candidate_path": str(location), "source_ref": source, "target_ref": target})
    return bound


def run_checks(controller, candidate, checks, attempt_prefix, run_dir):
    results = []
    for index, check in enumerate(checks):
        check_id = safe_id(check["id"])
        if check.get("required") is False:
            raise Blocked("remove explicitly non-applicable checks from approved contract before running")
        if check.get("kind") in ("tests", "test"):
            report_name = check.get("junit")
            if not report_name or Path(report_name).is_absolute() or ".." in Path(report_name).parts:
                raise Blocked("tests require a new repo-relative JUnit report path")
            report = Path(candidate["candidate_path"]) / report_name
            if report.exists() or report.is_symlink():
                raise Blocked("JUnit report already exists; use a fresh per-attempt report path")
            if not report.resolve().is_relative_to(Path(candidate["candidate_path"]).resolve()):
                raise Blocked("report path escapes candidate worktree")
        result = controller.execute(check["argv"], candidate["candidate_path"],
                                    f"{attempt_prefix}-{index}", Path(run_dir) / (check_id + ".log"),
                                    timeout=check.get("timeout_seconds"))
        result.update({"id": check_id, "status": "passed" if result["exit_code"] == 0 and not result["reason"] else "failed"})
        result["log_sha256"] = file_fingerprint(result["log"])
        if check.get("kind") in ("tests", "test"):
            report_name = check.get("junit")
            if not report_name or Path(report_name).is_absolute() or ".." in Path(report_name).parts:
                result.update(status="failed", problem="test checks require a repo-relative JUnit report")
            else:
                try:
                    report = Path(candidate["candidate_path"]) / report_name
                    tree = ET.parse(report)
                    cases = list(tree.iter("testcase"))
                    skipped = sum(c.find("skipped") is not None for c in cases)
                    failed = sum(c.find("failure") is not None or c.find("error") is not None for c in cases)
                    result.update(tests=len(cases), skipped=skipped, failed=failed, report=str(report), report_sha256=file_fingerprint(report))
                    if len(cases) - skipped < check.get("min_executed", 1) or skipped or failed:
                        result.update(status="failed", problem="tests missing, skipped or failed")
                except (OSError, ET.ParseError) as exc:
                    result.update(status="failed", problem=f"missing/invalid JUnit report: {exc}")
        results.append(result)
        if result["status"] != "passed":
            break
    return results


def check_fresh(root, evidence, spec, checks, environment, controller=None):
    now = bindings(root, evidence["source_ref"], evidence["target_ref"], spec, checks, environment, controller)
    for key, value in now.items():
        if evidence.get(key) != value:
            raise Blocked(f"stale evidence: {key} changed")
    if observed_git(evidence["candidate_path"], "rev-parse", "HEAD", controller=controller) != evidence["C"]:
        raise Blocked("candidate commit changed")
    if observed_git(evidence["candidate_path"], "diff", "HEAD", "--", controller=controller):
        raise Blocked("candidate tracked files changed after validation")


def deliver(controller, evidence, target_worktree, spec, checks, environment, authorized=False):
    if not authorized or not controller.entered:
        raise Blocked("explicit delivery authorization and run lock required")
    if evidence.get("status") != "verified":
        raise Blocked("candidate has not passed independent verification")
    check_fresh(controller.root, evidence, spec, checks, environment, controller)
    target_worktree = Path(target_worktree).resolve()
    if Path(controller.git("rev-parse", "--path-format=absolute", "--git-common-dir", cwd=target_worktree)) != controller.common:
        raise Blocked("target worktree belongs to another repository")
    if controller.git("symbolic-ref", "--short", "HEAD", cwd=target_worktree) != evidence["target_ref"]:
        raise Blocked("target worktree is not on requested target branch")
    if controller.git("status", "--porcelain", cwd=target_worktree):
        raise Blocked("target worktree dirty; preserve user changes")
    if controller.git("rev-parse", "HEAD", cwd=target_worktree) != evidence["T"]:
        raise Blocked("target changed before delivery")
    controller.git("merge", "--ff-only", "--no-overwrite-ignore", evidence["C"], cwd=target_worktree)
    delivered = controller.git("rev-parse", "HEAD", cwd=target_worktree)
    if delivered != evidence["C"] or controller.git("rev-parse", "HEAD^{tree}", cwd=target_worktree) != evidence["tree"]:
        raise Blocked("target updated but delivered content differs; block downstream")
    return {"status": "delivered", "D": delivered, "tree": evidence["tree"]}


def reconcile_delivery(root, evidence, target_ref, controller=None):
    """Read real target; never regenerate commits merely because checkpoint is old."""
    actual = observed_git(root, "rev-parse", target_ref + "^{commit}", controller=controller)
    if actual == evidence.get("C") and observed_git(root, "rev-parse", actual + "^{tree}", controller=controller) == evidence.get("tree"):
        return {"status": "delivered", "D": actual}
    return {"status": "blocked", "D": actual, "reason": "actual target is not the validated candidate; inspect/revalidate"}


def push_delivery(controller, task_id, remote, remote_ref, authorized=False):
    if not controller.entered or not authorized:
        raise Blocked("explicit push authorization and run lock required")
    if not remote or remote.startswith("-") or not remote_ref.startswith("refs/heads/"):
        raise Blocked("explicit named remote and refs/heads destination required")
    state = controller.state.read()
    task = state["tasks"].get(task_id, {})
    if task.get("status") not in ("delivered", "completed") or not task.get("D"):
        raise Blocked("only an actually delivered commit may be pushed")
    from .git_transport import remote_fingerprint, query_remote_ref, push_remote_ref
    destination = remote_fingerprint(controller, remote)
    before = query_remote_ref(controller, remote, remote_ref, destination=destination)
    state = controller.state.read()
    if before == task["D"]:
        matches = [op for op in state["remote_operations"] if op.get("action") == "git-push"
                   and op.get("remote") == remote and op.get("ref") == remote_ref and op.get("D") == task["D"]
                   and op.get("destination", destination) == destination
                   and op.get("status") in ("intent", "unknown")]
        if len(matches) > 1:
            raise Blocked("duplicate uncertain push identities require explicit reconciliation")
        if matches:
            matches[0].update(status="observed", observed_ref=task["D"])
            controller.state.write(state, state["revision"])
        return {"pushed": True, "reused": True, "D": task["D"], "remote": remote, "ref": remote_ref}
    if any(op.get("status") in ("intent", "unknown", "pending") for op in state["remote_operations"]):
        raise Blocked("previous remote result is unresolved; do not retry push before reconciliation")
    operation = {"action": "git-push", "remote": remote, "ref": remote_ref, "D": task["D"], "destination": destination, "status": "intent"}
    state["remote_operations"].append(operation)
    state = controller.state.write(state, state["revision"])
    try:
        push_remote_ref(controller, remote, remote_ref, task["D"], destination=destination, before=before)
    except Blocked:
        # A request error is not proof of remote failure; query before retrying.
        pass
    after = query_remote_ref(controller, remote, remote_ref, destination=destination)
    okay = after == task["D"]
    state = controller.state.read()
    state["remote_operations"][-1]["status"] = "observed" if okay else "unknown"
    controller.state.write(state, state["revision"])
    if not okay:
        raise Blocked("push result unknown or mismatched; reconcile remote ref before retry")
    return {"pushed": True, "D": task["D"], "remote": remote, "ref": remote_ref}
