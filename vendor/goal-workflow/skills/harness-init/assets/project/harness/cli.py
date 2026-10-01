"""Single serial CLI entrypoint. Local mode never calls a hosting API."""
import argparse
import json
import sys
from pathlib import Path
from .state import Blocked, atomic_json
from .runtime import Controller, git
from . import local
from .workflow import validate_task, verified_evidence, run_serial, closeout, approve_contract
from .capabilities import require_capabilities, record_capabilities


def load(path):
    from .harness_check import load_bundle
    return load_bundle(path)


def config_limits(config):
    result = dict(config["limits"])
    # Commands are separately bounded; task-level retry budget is checked by workflow.
    # Include bounded Git/native/tool bookkeeping as well as task/review calls.
    default = config["limits"]["task_attempts"] * (len(config["checks"]) + 32) * (config["limits"]["repair_attempts"] + 1)
    default += config["limits"].get("query_attempts", 0) * 16
    result["max_attempts"] = config["limits"].get("control_commands", default)
    if type(result["max_attempts"]) is not int or result["max_attempts"] <= 0:
        raise Blocked("control_commands must be a positive finite integer")
    return result


def preflight(bundle):
    from .contracts import Validator
    v = Validator(bundle)
    if not v.preflight():
        raise Blocked(json.dumps(v.errors, ensure_ascii=False))
    return bundle["config"]


def select_task(bundle, task_id):
    tasks = [t for t in bundle["tasks"] if t["id"] == task_id]
    if len(tasks) != 1:
        raise Blocked("task ID missing or duplicate")
    return tasks[0]


def github_destinations(config, task):
    base = task.get("github_base") or task.get("target", "").removeprefix("refs/heads/")
    head = task.get("github_head") or task.get("source", "").removeprefix("refs/heads/")
    repository = config.get("repository") or config.get("github", {}).get("repository")
    head_repository = task.get("github_head_repository", repository)
    if not base or not head or not repository or not head_repository:
        raise Blocked("explicit GitHub source/destination branch and repository identities required")
    if config.get("github", {}).get("target_branch") not in (None, base):
        raise Blocked("task GitHub target differs from P0 configured target branch")
    return base, head, head_repository


def require_pr_destination(config, task, pr):
    base, head, head_repository = github_destinations(config, task)
    if pr.get("base", {}).get("ref") != base:
        raise Blocked("PR targets a different named destination branch")
    if (pr.get("head", {}).get("ref") != head
            or pr.get("head", {}).get("repo", {}).get("full_name") != head_repository):
        raise Blocked("PR source branch/repository differs from the authorized task")


def github_verified_args(controller, config, bundle, action, args):
    """Build merge proof from stored execution and fresh platform/Git reads, not caller JSON."""
    from .github import GitHubAdapter, controlled_runner
    task = select_task(bundle, args.get("task_id"))
    evidence = verified_evidence(controller, task, config)
    adapter = GitHubAdapter(config, controlled_runner(controller))
    pr = adapter.read_pr(args["number"])
    require_pr_destination(config, task, pr)
    current_target = adapter.branch_head(pr["base"]["ref"])
    saved_task = controller.state.read()["tasks"].get(task["id"], {})
    receipt = saved_task.get("platform_evidence", {})
    checked_sha = pr.get("merge_commit_sha") if not pr.get("merged") else receipt.get("checked_sha", pr["head"]["sha"])
    if not checked_sha:
        checked_sha = pr["head"]["sha"]
    required = config.get("github", {}).get("required_checks", [])
    checks = adapter.checks(args["number"], checked_sha, required)
    proof = {"status": checks["status"], "source_sha": evidence["H"], "target_sha": evidence["T"],
             "checked_sha": checked_sha, "candidate_tree": evidence["tree"], "baseline_verified": True}
    if pr.get("merged") and config.get("github", {}).get("baseline_policy") in ("queue", "merge_queue"):
        group_sha = args.get("merge_group_sha") or receipt.get("merge_group_sha")
        if not group_sha:
            raise Blocked("actual queue group SHA is required for native merge_group association checks")
        group = adapter.merge_group_evidence(group_sha, args["number"], required)
        if adapter.commit_tree(group_sha) != evidence["tree"]:
            raise Blocked("merge_group tree differs from validated candidate; revalidate actual combination")
        proof.update(group)
    built = dict(args, evidence=proof, current_target_sha=current_target)
    if action == "merge":
        if current_target != evidence["T"]:
            raise Blocked("actual target branch advanced after local verification")
        local.check_fresh(controller.root, evidence, controller.root / task["spec"], config["checks"], config["environment"], controller)
        actual_commit = adapter._api(f"repos/{adapter.repository}/git/commits/{checked_sha}")
        if actual_commit.get("tree", {}).get("sha") != evidence["tree"]:
            raise Blocked("GitHub checked candidate tree differs from locally verified combination")
        if task.get("tests_depend_on_commit_metadata"):
            raise Blocked("commit-sensitive checks require validation of actual GitHub candidate commit")
    if action == "reconcile" and pr.get("merged"):
        remote = config.get("github", {}).get("remote")
        if not remote or remote.startswith("-"):
            raise Blocked("GitHub final delivery requires explicit configured Git remote for commit/tree proof")
        delivered = pr.get("merge_commit_sha")
        if not delivered:
            raise Blocked("merged PR missing delivered commit")
        controller.git("fetch", "--no-tags", remote, pr["base"]["ref"])
        actual_target = controller.git("rev-parse", "FETCH_HEAD")
        tree = controller.git("rev-parse", delivered + "^{tree}")
        controller.git("merge-base", "--is-ancestor", delivered, actual_target)
        built.update(current_target_sha=actual_target, delivered_tree=tree, delivered_reachable=True)
    return built


def github_platform_verify(controller, config, bundle, args):
    from .github import GitHubAdapter, controlled_runner
    task = select_task(bundle, args["task_id"])
    local_proof = verified_evidence(controller, task, config, allow_local_only=True)
    adapter = GitHubAdapter(config, controlled_runner(controller))
    pr = adapter.read_pr(args["number"])
    require_pr_destination(config, task, pr)
    current_target = adapter.branch_head(pr["base"]["ref"])
    if pr["head"]["sha"] != local_proof["H"] or current_target != local_proof["T"]:
        raise Blocked("PR head or target differs from locally validated combination")
    checked_sha = pr.get("merge_commit_sha") or pr["head"]["sha"]
    actual_tree = adapter.commit_tree(checked_sha)
    if actual_tree != local_proof["tree"]:
        raise Blocked("actual GitHub checked object differs from local validated tree")
    if task.get("tests_depend_on_commit_metadata") and checked_sha != local_proof["C"]:
        raise Blocked("commit-sensitive validation must target the actual GitHub candidate")
    checks = adapter.checks(args["number"], checked_sha, config.get("github", {}).get("required_checks", []))
    if checks["status"] != "pass":
        raise Blocked("current required GitHub CI incomplete or failed")
    after = adapter.read_pr(args["number"])
    require_pr_destination(config, task, after)
    after_target = adapter.branch_head(after["base"]["ref"])
    if after["head"]["sha"] != local_proof["H"] or after_target != local_proof["T"]:
        raise Blocked("PR changed during final platform gate")
    proof = {"status": "pass", "source_sha": local_proof["H"], "target_sha": local_proof["T"],
             "checked_sha": checked_sha, "candidate_tree": actual_tree, "baseline_verified": True,
             "checks": checks, "pr": args["number"]}
    state = controller.state.read()
    state["tasks"][task["id"]].update(status="verified", platform_evidence=proof, pr=args["number"])
    controller.state.write(state, state["revision"])
    return {"status": "verified", "task_id": task["id"], "verification_tier": local_proof["verification_tier"], "platform_evidence": proof}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="initialize draft config without overwriting existing content")
    init.add_argument("--repo", required=True)
    init.add_argument("--mode", choices=["local", "github"], required=True)
    init.add_argument("--dry-run", action="store_true")
    for name in ("preflight", "evidence", "validate", "deliver", "recover", "reconcile", "github", "run", "reports", "closeout", "push", "probe", "tasks", "approve-contract", "migrate", "knowledge", "record-capabilities"):
        p = sub.add_parser(name)
        p.add_argument("--bundle", required=True)
        if name in ("validate", "deliver", "recover", "reconcile", "run", "github", "reports", "closeout", "push", "approve-contract", "migrate", "knowledge", "record-capabilities"):
            p.add_argument("--run", required=True)
        if name in ("validate", "deliver", "reconcile", "reports", "closeout", "push", "approve-contract"):
            p.add_argument("--task", required=True)
        if name == "validate":
            p.add_argument("--attempt", required=True)
        if name == "run":
            p.add_argument("--attempt", required=True)
            p.add_argument("--implement", action="store_true", help="start configured implementation host in isolated worktree")
        if name == "reports":
            p.add_argument("--results", required=True, help="actual observed draft report results JSON")
        if name in ("push", "approve-contract", "migrate"):
            p.add_argument("--authorize", action="store_true")
        if name == "deliver":
            p.add_argument("--target-worktree", required=True)
            p.add_argument("--authorize", action="store_true")
            p.add_argument("--simulation", action="store_true", help="deliver only inside a capability-bound marked temporary fixture")
        if name == "record-capabilities":
            p.add_argument("--tier", choices=["live", "simulation"], required=True)
            p.add_argument("--semantic-review")
            p.add_argument("--authorize-semantic-review", action="store_true")
        if name == "github":
            p.add_argument("action", choices=["tasks", "graph", "read", "dependencies", "find-pr", "checks", "reconcile", "rules", "create-pr", "merge", "verify", "complete-issue", "reconcile-issue", "wait-checks", "cancel", "commit-tree", "merge-group", "remote-state"])
            p.add_argument("--args", default="{}", help="JSON action arguments; mutation requires authorized=true")
        if name == "knowledge":
            p.add_argument("action", choices=["create", "register", "maintenance", "onboarding", "read-core", "references", "readiness", "write", "edit", "rename"])
            p.add_argument("--args", default="{}", help="JSON native action parameters; edits use expected_sha256")
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            from .init_project import main as initialize
            values = ["--repo", args.repo, "--mode", args.mode]
            if args.dry_run:
                values.append("--dry-run")
            return initialize(values)
        bundle = load(args.bundle)
        config = bundle["config"] if args.command in ("probe", "tasks", "knowledge", "record-capabilities") else preflight(bundle)
        if args.command == "probe":
            from .p0 import probe
            result = probe(config)
        elif args.command == "tasks":
            if config["mode"] != "local":
                raise Blocked("use github tasks for GitHub task source; no implicit mode switching")
            from .tasks import load_tasks
            result = load_tasks(config["repository_root"], config["task_directories"], config.get("report_mapping"))
        elif args.command == "knowledge":
            from .knowledge import SerenaAdapter
            if config.get("mode") not in ("local", "github"):
                raise Blocked("knowledge operation needs explicit project mode")
            knowledge = config["knowledge"]
            params = json.loads(args.args)
            with Controller(config["repository_root"], config["mode"], args.run, config_limits(config)) as controller:
                native = SerenaAdapter(controller.root, knowledge["executable"], knowledge["serena_home"],
                                       timeout_seconds=config["limits"]["command_seconds"],
                                       python_executable=knowledge.get("python_executable"), controller=controller)
                if args.action == "create": result = native.create_project(params["languages"])
                elif args.action == "register": result = native.register_existing()
                elif args.action == "maintenance": result = native.initialize_maintenance()
                elif args.action == "onboarding": result = native.onboarding_instructions()
                elif args.action == "read-core": result = native.read_core()
                elif args.action == "references": result = native.check_references()
                elif args.action == "readiness": result = native.readiness(params["evidence"])
                elif args.action == "write": result = native.write_new_memory(params["name"], params["content"], params["evidence"])
                elif args.action == "edit": result = native.update_memory(params["name"], params["content"], params["evidence"], params["expected_sha256"])
                else: result = native.rename_memory(params["old_name"], params["new_name"], params["evidence"], params["expected_sha256"])
        elif args.command == "record-capabilities":
            with Controller(config["repository_root"], config["mode"], args.run, config_limits(config)) as controller:
                result = record_capabilities(controller, config, args.tier, args.semantic_review, args.authorize_semantic_review)
        elif args.command in ("preflight", "evidence"):
            from .contracts import evaluate_bundle
            result = evaluate_bundle(bundle, args.command)
        elif args.command == "github":
            from .github import github_action, AdapterError, controlled_runner
            action_args = json.loads(args.args)
            with Controller(config["repository_root"], config["mode"], args.run, config_limits(config)) as controller:
                if args.action == "verify":
                    try:
                        result = github_platform_verify(controller, config, bundle, action_args)
                    except AdapterError as exc:
                        raise Blocked(str(exc)) from exc
                    print(json.dumps(result, ensure_ascii=False, indent=2))
                    return 0
                if args.action == "create-pr":
                    task = select_task(bundle, action_args.get("task_id"))
                    local_proof = verified_evidence(controller, task, config, allow_local_only=True)
                    local.check_fresh(controller.root, local_proof, controller.root / task["spec"], config["checks"], config["environment"], controller)
                    base, head, head_repository = github_destinations(config, task)
                    label = head_repository.split("/", 1)[0] + ":" + head
                    if action_args.get("base", base) != base or action_args.get("head", label) not in (head, label):
                        raise Blocked("PR creation source/destination differs from approved task")
                    action_args.update(base=base, head=label)
                if args.action in ("merge", "reconcile"):
                    try:
                        action_args = github_verified_args(controller, config, bundle, args.action, action_args)
                    except AdapterError as exc:
                        raise Blocked(str(exc)) from exc
                state = controller.state.read()
                if args.action in ("complete-issue", "reconcile-issue"):
                    task = select_task(bundle, action_args.get("core_task_id"))
                    delivered = state["tasks"].get(task["id"], {})
                    if delivered.get("status") not in ("delivered", "completed"):
                        raise Blocked("Issue completion requires actual verified delivery")
                    verified_evidence(controller, task, config)
                    closeout(controller, config, task, check_only=True)
                    source_id = task.get("source_id") or task.get("issue_number")
                    if source_id is None:
                        raise Blocked("real Issue identity missing from task")
                    if "task_id" in action_args and str(action_args["task_id"]) != str(source_id):
                        raise Blocked("Issue identity differs from delivered task")
                    action_args.update(task_id=source_id, delivery=delivered["platform_delivery"])
                    if args.action == "reconcile-issue":
                        action_args["authorized"] = False
                    state = controller.state.read()
                operation = {"action": args.action, "args": action_args, "status": "intent"}
                mutating = args.action in ("create-pr", "merge", "cancel", "complete-issue")
                if mutating:
                    require_capabilities(controller, config, delivery=True)
                    state = controller.state.read()
                    if args.action != "cancel" and any(o.get("status") in ("intent", "unknown", "pending") for o in state["remote_operations"]):
                        raise Blocked("outstanding remote operation requires query/reconciliation before new mutation")
                    state["remote_operations"].append(operation)
                    state = controller.state.write(state, state["revision"])
                try:
                    if args.action == "wait-checks":
                        key = str(action_args["number"]) + ":" + action_args["expected_sha"]
                        action_args["budget"] = state.setdefault("platform_waits", {}).get(key, {})
                        def persist(budget):
                            nonlocal state
                            state = controller.state.read()
                            state["platform_waits"][key] = budget
                            state = controller.state.write(state, state["revision"])
                        result = github_action(config, args.action, action_args, run=controlled_runner(controller), persist=persist)
                    else:
                        result = github_action(config, "complete-issue" if args.action == "reconcile-issue" else args.action, action_args,
                                               run=controlled_runner(controller))
                except AdapterError as exc:
                    if mutating:
                        state = controller.state.read()
                        state["remote_operations"][-1].update(status="unknown", reason=str(exc))
                        controller.state.write(state, state["revision"])
                    raise Blocked(str(exc)) from exc
                state = controller.state.read()
                if mutating:
                    outcome = result.get("status") if isinstance(result, dict) else None
                    journal_status = "unknown" if outcome in ("delivery_unknown", "unknown") else "pending" if outcome in ("delivery_pending", "pending") else "observed"
                    state["remote_operations"][-1].update(status=journal_status, result=result)
                    if args.action == "merge" and action_args.get("task_id") in state["tasks"]:
                        state["tasks"][action_args["task_id"]]["platform_evidence"] = action_args["evidence"]
                    if args.action == "complete-issue" and outcome == "completed":
                        task_id = action_args.get("core_task_id")
                        state["tasks"][task_id]["issue_completion"] = result
                    if args.action == "cancel" and outcome in ("cancelled", "already_delivered"):
                        for prior in state["remote_operations"][:-1]:
                            if prior.get("args", {}).get("number") == action_args.get("number") and prior.get("status") in ("intent", "pending", "unknown"):
                                prior.update(status="observed", cancellation=result)
                    controller.state.write(state, state["revision"])
                elif args.action == "reconcile" and isinstance(result, dict) and result.get("status") == "delivered":
                    number = action_args.get("number")
                    matches = [o for o in state["remote_operations"] if o.get("action") == "merge"
                               and o.get("args", {}).get("number") == number and o.get("status") in ("intent", "unknown", "pending")]
                    if len(matches) == 1:
                        matches[0].update(status="observed", result=result)
                    task_id = action_args.get("task_id")
                    if task_id in state["tasks"]:
                        state["tasks"][task_id].update(status="delivered", D=result["delivered_sha"],
                                                       platform_delivery=result, pr=number)
                    controller.state.write(state, state["revision"])
                elif args.action == "find-pr" and isinstance(result, dict) and result.get("number"):
                    matches = [o for o in state["remote_operations"] if o.get("action") == "create-pr"
                               and o.get("args", {}).get("head") == action_args.get("head")
                               and o.get("args", {}).get("base") == action_args.get("base")
                               and o.get("status") in ("intent", "unknown")]
                    if len(matches) > 1:
                        raise Blocked("multiple unresolved PR-create intents require explicit reconciliation")
                    if matches:
                        matches[0].update(status="observed", result=result)
                        controller.state.write(state, state["revision"])
                elif args.action == "reconcile-issue" and isinstance(result, dict) and result.get("status") == "completed":
                    matches = [o for o in state["remote_operations"] if o.get("action") == "complete-issue"
                               and o.get("args", {}).get("task_id") == action_args.get("task_id")
                               and o.get("status") in ("intent", "unknown")]
                    if len(matches) > 1:
                        raise Blocked("multiple unresolved Issue completion intents")
                    for op in matches:
                        op.update(status="observed", result=result)
                    state["tasks"][action_args["core_task_id"]]["issue_completion"] = result
                    controller.state.write(state, state["revision"])
        elif args.command == "recover":
            result = Controller.reconcile_stopped(config["repository_root"], config["mode"], args.run, config_limits(config))
        elif args.command == "migrate":
            from .state import migrate_legacy
            result = migrate_legacy(config["repository_root"], config["mode"], args.run, config_limits(config), args.authorize)
        else:
            task = select_task(bundle, args.task) if args.command != "run" else None
            with Controller(config["repository_root"], config["mode"], args.run, config_limits(config)) as controller:
                if args.command == "run":
                    result = run_serial(controller, config, bundle["tasks"], args.attempt, args.implement)
                elif args.command == "approve-contract":
                    result = approve_contract(controller, config, task, args.authorize)
                elif args.command == "reports":
                    from .reports import build_mapping, write_reports
                    normalized = [dict(t, task_id=t["id"]) for t in bundle["tasks"]]
                    mapping = build_mapping(normalized, config["mode"], {t["id"]: t["reports"] for t in bundle["tasks"]})
                    result = write_reports(controller, config["mode"], dict(task, task_id=task["id"]), load(args.results), mapping)
                    state = controller.state.read()
                    if task["id"] in state["tasks"] and state["tasks"][task["id"]].get("status") == "verified":
                        state["tasks"][task["id"]].update(status="blocked", reason="reports changed after verification; commit and revalidate")
                        controller.state.write(state, state["revision"])
                elif args.command == "closeout":
                    result = closeout(controller, config, task)
                elif args.command == "push":
                    require_capabilities(controller, config, delivery=True)
                    if config["mode"] != "local" or not config.get("push", {}).get("enabled", False):
                        raise Blocked("local push is disabled by default")
                    result = local.push_delivery(controller, task["id"], config["push"]["remote"], config["push"]["ref"], args.authorize)
                elif args.command == "validate":
                    result = validate_task(controller, config, task, args.attempt)
                elif args.command == "reconcile":
                    saved = controller.state.read()["tasks"].get(task["id"], {})
                    evidence = json.loads(Path(saved["evidence"]).read_text())
                    result = local.reconcile_delivery(controller.root, evidence, task["target"], controller)
                    if result["status"] == "delivered":
                        try:
                            verified_evidence(controller, task, config)
                        except Blocked as exc:
                            result.update(status="blocked", reason="physically delivered but proof invalid: " + str(exc))
                        state = controller.state.read()
                        state["tasks"][task["id"]].update(result)
                        controller.state.write(state, state["revision"])
                else:
                    if config["mode"] != "local":
                        raise Blocked("GitHub delivery requires github checks/rules/merge/reconcile adapter path")
                    receipt = require_capabilities(controller, config, delivery=True, simulate_delivery=args.simulation)
                    evidence = verified_evidence(controller, task, config)
                    result = local.deliver(controller, evidence, args.target_worktree, controller.root / task["spec"],
                                           config["checks"], config["environment"], authorized=args.authorize)
                    result["verification_tier"] = receipt["tier"]
                    state = controller.state.read()
                    state["tasks"][task["id"]].update(result)
                    controller.state.write(state, state["revision"])
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if isinstance(result, dict) and (result.get("ok") is False or result.get("status") == "blocked") else 0
    except (Blocked, OSError, ValueError, KeyError) as exc:
        print(json.dumps({"status": "blocked", "reason": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
