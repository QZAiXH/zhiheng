"""Evidence-producing serial validation, with explicit human delivery handoff."""
import json
from pathlib import Path
from .state import Blocked, atomic_json
from .local import prepare_candidate, run_checks, check_fresh, fingerprint, file_fingerprint, safe_id
from .runtime import git
from .contracts import schema_errors, check_fingerprint
from graphlib import TopologicalSorter, CycleError
from .knowledge import SerenaAdapter, verify_durable_evidence, _safe_local_path
from .capabilities import require_capabilities


def contract_identity(controller, config, task):
    return {"task_sha256": fingerprint(task), "checks_sha256": check_fingerprint(config),
            "spec_sha256": file_fingerprint(_safe_local_path(controller.root, task["spec"]))}


def approve_contract(controller, config, task, authorized=False):
    """Record an explicitly reviewed baseline; never invoked automatically by implementation."""
    if not authorized or not controller.entered:
        raise Blocked("contract baseline requires explicit review authorization and run lock")
    identity = contract_identity(controller, config, task)
    state = controller.state.read()
    entry = dict(identity, task_id=task["id"], target=git(controller.root, "rev-parse", task["target"]),
                 revision=state["revision"])
    state.setdefault("contract_approvals", []).append(entry)
    state.setdefault("contracts", {})[task["id"]] = identity
    controller.state.write(state, state["revision"])
    return {"contract_baseline_recorded": True, "task_id": task["id"], **identity}


def require_approved_contract(controller, config, task):
    observed = contract_identity(controller, config, task)
    expected = controller.state.read().get("contracts", {}).get(task["id"])
    if observed != expected:
        raise Blocked("task/spec/check/budget contract lacks matching reviewed baseline; explicit approve-contract required")


def render_argv(argv, values):
    if not isinstance(argv, list) or not argv or not all(isinstance(x, str) for x in argv):
        raise Blocked("host command must be a nonempty argv list")
    return [x.format_map(values) for x in argv]


def review(controller, candidate, task, config, run_dir, attempt_id, knowledge=None):
    output = Path(run_dir) / "review.json"
    if output.exists():
        raise Blocked("review output already exists")
    prompt = ("Independently review this exact candidate, its task and acceptance requirements. "
              "Do not modify files. Report findings with severity Blocking/Warning/Info, summary, "
              "location and evidence. For each acceptance ID provide passed/failed and evidence. "
              "Do not treat self-reported success as proof. Verify project knowledge and durable citations "
              "against actual source, and that project purpose, stack, commands, conventions and completion "
              "checks are usable. Read core and needed referenced topics, not every memory. Task JSON: "
              + json.dumps(task, ensure_ascii=False) + "\nNative knowledge observations:\n" + json.dumps(knowledge, ensure_ascii=False))
    host = config.get("host", {})
    values = {"worktree": candidate["candidate_path"], "output": str(output), "prompt": prompt,
              "schema": str(Path(__file__).with_name("review-response.schema.json")), "task_id": task["id"]}
    argv = render_argv(host.get("review_argv", []), values)
    record = controller.execute(argv, candidate["candidate_path"], attempt_id + "-review", Path(run_dir) / "review.log",
                                timeout=config["limits"]["review_seconds"], scope="review")
    if record["exit_code"] != 0 or record["reason"]:
        raise Blocked("independent review failed or timed out; preserve raw review log")
    try:
        result = json.loads(output.read_text())
        from jsonschema import validate
        validate(result, json.loads(Path(__file__).with_name("review-response.schema.json").read_text()))
    except Exception as exc:
        raise Blocked("independent review response missing or invalid") from exc
    required = set(task["acceptance_ids"])
    rows = result["acceptance"]
    if {row["id"] for row in rows} != required or len(rows) != len(required):
        raise Blocked("review did not cover every acceptance ID exactly once")
    if any(row["status"] != "passed" for row in rows) or any(f["severity"] == "Blocking" for f in result["findings"]):
        raise Blocked("review has unmet acceptance or Blocking findings")
    return dict(result, record=record, log_sha256=file_fingerprint(record["log"]), response_sha256=file_fingerprint(output), response=str(output))


def validate_task(controller, config, task, attempt_id):
    safe_id(task["id"]); safe_id(attempt_id)
    if not config.get("ready"):
        raise Blocked("P0 capabilities not yet approved/ready")
    capability = require_capabilities(controller, config)
    if config.get("mode") not in ("local", "github"):
        raise Blocked("explicit mode required")
    for field in ("source", "target", "spec", "acceptance_ids"):
        if not task.get(field):
            raise Blocked(f"task missing {field}")
    _safe_local_path(controller.root, task["spec"])
    require_approved_contract(controller, config, task)
    data = controller.state.read()
    for dep in task.get("dependencies", []):
        prior = data["tasks"].get(dep, {})
        if prior.get("status") not in ("delivered", "completed") or not prior.get("D"):
            raise Blocked(f"dependency not delivered: {dep}")
        try:
            git(controller.root, "merge-base", "--is-ancestor", prior["D"], task["target"])
        except Blocked as exc:
            raise Blocked(f"dependency not in downstream baseline: {dep}") from exc
    old = data["tasks"].get(task["id"], {})
    rounds = old.get("validation_attempts", 0)
    if rounds >= config["limits"]["task_attempts"]:
        raise Blocked("task attempt budget exhausted; explicit budget amendment required")
    data["tasks"][task["id"]] = dict(old, status="validating", validation_attempts=rounds + 1)
    controller.state.write(data, data["revision"])
    run_dir = controller.common / "harness-runs" / controller.state.run_id / task["id"] / attempt_id
    run_dir.mkdir(parents=True, exist_ok=False)
    atomic_json(run_dir / "request.json", {"config": config, "task": task, "attempt_id": attempt_id})
    try:
        candidate = prepare_candidate(controller, task["source"], task["target"], task["id"], attempt_id,
                                      controller.root / task["spec"], config["checks"], config["environment"])
        knowledge_config = config.get("knowledge", {})
        if not knowledge_config.get("executable") or not knowledge_config.get("serena_home"):
            raise Blocked("pinned Serena executable and dedicated serena_home are required")
        native = SerenaAdapter(candidate["candidate_path"], knowledge_config["executable"], knowledge_config["serena_home"],
                               timeout_seconds=config["limits"]["command_seconds"],
                               python_executable=knowledge_config.get("python_executable"), controller=controller)
        native.register_existing()
        knowledge = native.readiness(task.get("durable_evidence", []))
        if knowledge.get("structural_ready") is not True:
            raise Blocked("native knowledge readiness is incomplete")
        binding = {"H": candidate["H"], "T": candidate["T"], "C": candidate["C"], "C_kind": "commit",
                   "spec_sha256": candidate["spec_fingerprint"], "checks_sha256": check_fingerprint(config),
                   "environment_sha256": fingerprint(config["environment"]), "task_sha256": fingerprint(task)}
        snapshot = {"mode": config["mode"], "repository_id": config["repository_id"], "task_id": task["id"],
                    "run_id": controller.state.run_id, "attempt_id": attempt_id,
                    "checkpoint_revision": controller.state.read()["revision"], "binding": binding}
        task_input = dict(snapshot, required_acceptance_ids=task["acceptance_ids"],
                          required_check_ids=[c["id"] for c in config["checks"]], task=task,
                          limits=config["limits"], context=task.get("context", []))
        errors = schema_errors(task_input, "input")
        if errors:
            raise Blocked("invalid task input schema: " + str(errors))
        atomic_json(run_dir / "input.json", task_input)
        results = run_checks(controller, candidate, config["checks"], attempt_id, run_dir)
        if len(results) != len(config["checks"]) or any(r["status"] != "passed" for r in results):
            raise Blocked("required checks failed or incomplete")
        assessment = review(controller, candidate, task, config, run_dir, attempt_id, knowledge)
        check_fresh(controller.root, candidate, controller.root / task["spec"], config["checks"], config["environment"])
        evidence = dict(candidate, mode=config["mode"], task_id=task["id"], run_id=controller.state.run_id,
                        attempt_id=attempt_id, checks=results, review=assessment,
                        task_fingerprint=fingerprint(task), policy_fingerprint=check_fingerprint(config),
                        knowledge=knowledge, verification_tier=capability["tier"],
                        status="verified" if config["mode"] == "local" else "validating")
        common = {"run_id": controller.state.run_id, "attempt_id": attempt_id, "binding": binding}
        def report(path):
            return {"path": str(Path(path).relative_to(controller.state.path.parent)), "sha256": file_fingerprint(path)}
        task_result = dict(snapshot, stop_reason="completed", unresolved_items=[], checks=[],
                           acceptance=[{"id": row["id"], "status": row["status"], "evidence_ids": ["review"]}
                                       for row in assessment["acceptance"]])
        for result in results:
            counts = ({"executed": result["tests"] - result["skipped"], "passed": result["tests"] - result["failed"] - result["skipped"],
                       "failed": result["failed"], "skipped": result["skipped"]} if "tests" in result
                      else {"evaluated": 1, "failed": 0})
            task_result["checks"].append(dict(common, id=result["id"], status=result["status"], exit_code=result["exit_code"],
                                               counts=counts, report=report(result["log"])))
        task_result["review"] = dict(common, status="completed", independent=True, report=report(assessment["response"]),
                                    findings=[dict(f, resolved=False) for f in assessment["findings"]], unresolved_items=[])
        errors = schema_errors(task_result, "result")
        if errors:
            raise Blocked("invalid task result schema: " + str(errors))
        atomic_json(run_dir / "result.json", task_result)
        atomic_json(run_dir / "evidence.json", evidence)
        data = controller.state.read()
        data["tasks"][task["id"]].update(status=evidence["status"], local_validation="passed",
                                        verification_tier=capability["tier"], evidence=str(run_dir / "evidence.json"),
                                        evidence_sha256=file_fingerprint(run_dir / "evidence.json"))
        controller.state.write(data, data["revision"])
        return evidence
    except Exception as exc:
        data = controller.state.read()
        data["tasks"][task["id"]].update(status="blocked", reason=str(exc), next_step="inspect preserved logs; repair under remaining budget")
        controller.state.write(data, data["revision"])
        raise


def verified_evidence(controller, task, config=None, allow_local_only=False):
    data = controller.state.read()
    saved = data["tasks"].get(task["id"], {})
    allowed = ("verified", "delivered", "completed")
    if saved.get("status") not in allowed and not (allow_local_only and saved.get("status") == "validating" and saved.get("local_validation") == "passed"):
        raise Blocked("task not verified by this controller")
    if file_fingerprint(saved["evidence"]) != saved.get("evidence_sha256"):
        raise Blocked("stored evidence altered")
    evidence = json.loads(Path(saved["evidence"]).read_text())
    if evidence["task_fingerprint"] != fingerprint(task):
        raise Blocked("task requirements changed after verification")
    if config is not None and evidence["policy_fingerprint"] != check_fingerprint(config):
        raise Blocked("check, budget or platform policy changed after verification")
    for check in evidence["checks"]:
        record = next((r for r in data["attempts"] if r["attempt_id"] == check["attempt_id"]), None)
        if not record or record["exit_code"] != 0 or record["reason"] or not record["stopped"]:
            raise Blocked("check lacks matching real execution record")
        if file_fingerprint(check["log"]) != check["log_sha256"]:
            raise Blocked("check raw log altered")
        if check.get("report") and file_fingerprint(check["report"]) != check["report_sha256"]:
            raise Blocked("check report altered")
    review_record = evidence["review"]["record"]
    if not any(r == review_record for r in data["attempts"]):
        raise Blocked("review lacks matching independent execution record")
    if file_fingerprint(review_record["log"]) != evidence["review"]["log_sha256"]:
        raise Blocked("review raw log altered")
    if file_fingerprint(evidence["review"]["response"]) != evidence["review"]["response_sha256"]:
        raise Blocked("review output changed")
    return evidence


def implement_task(controller, config, task, attempt_id, feedback=""):
    """Run the configured host in an isolated source worktree, retaining failures."""
    safe_id(task["id"]); safe_id(attempt_id)
    if not config.get("ready"):
        raise Blocked("P0 not ready; no implementation executor started")
    require_capabilities(controller, config)
    require_approved_contract(controller, config, task)
    branch = task["source"]
    try:
        git(controller.root, "rev-parse", "--verify", branch)
        raise Blocked("source branch exists; use explicit resume after inspecting its worktree")
    except Blocked as exc:
        if "source branch exists" in str(exc):
            raise
    path = controller.common / "harness-worktrees" / (task["id"] + "-implementation-" + attempt_id)
    path.parent.mkdir(exist_ok=True)
    git(controller.root, "worktree", "add", "-b", branch, str(path), task["target"])
    run_dir = controller.common / "harness-runs" / controller.state.run_id / task["id"] / (attempt_id + "-implementation")
    run_dir.mkdir(parents=True, exist_ok=False)
    spec = _safe_local_path(controller.root, task["spec"]).read_text()
    prompt = ("Implement only this task in the current isolated worktree. Read applicable project rules, "
              "then project core knowledge and needed topic references. Preserve complete acceptance criteria. "
              "Prepare required walkthrough and stable evidence/knowledge changes before your final commit. "
              "Do not push, open PR, merge, deploy, or claim independent verification. Commit your changes "
              "on the current branch when implementation is ready; report missing knowledge/requirements.\n"
              + json.dumps(task, ensure_ascii=False) + "\nSPEC:\n" + spec + "\nPrior feedback:\n" + feedback)
    prompt_path = run_dir / "prompt.txt"
    prompt_path.write_text(prompt)
    values = {"worktree": str(path), "task_id": task["id"], "prompt": prompt,
              "input": str(prompt_path), "output": str(run_dir / "host-result.txt")}
    argv = render_argv(config.get("host", {}).get("implementation_argv", []), values)
    result = controller.execute(argv, path, attempt_id + "-implementation", run_dir / "host.log",
                                timeout=config["limits"]["implementation_seconds"], scope="implementation")
    if result["exit_code"] != 0 or result["reason"]:
        raise Blocked("implementation failed; worktree and raw logs preserved")
    if git(path, "status", "--porcelain"):
        raise Blocked("implementation left uncommitted/untracked files; inspect and commit explicitly")
    if git(path, "rev-parse", "HEAD") == git(controller.root, "rev-parse", task["target"]):
        raise Blocked("implementation produced no committed change")
    return {"source": branch, "worktree": str(path), "H": git(path, "rev-parse", "HEAD"), "execution": result}


def repair_task(controller, config, task, worktree, attempt_id, feedback):
    path = Path(worktree).resolve()
    if Path(git(path, "rev-parse", "--path-format=absolute", "--git-common-dir")) != controller.common:
        raise Blocked("repair worktree belongs to another repository")
    if git(path, "symbolic-ref", "--short", "HEAD") != task["source"]:
        raise Blocked("repair worktree branch changed")
    state = controller.state.read()
    entry = state["tasks"].setdefault(task["id"], {})
    count = entry.get("repair_attempts", 0)
    if count >= min(2, config["limits"]["repair_attempts"]):
        raise Blocked("repair rounds exhausted; retain Blocking findings")
    entry["repair_attempts"] = count + 1
    state = controller.state.write(state, state["revision"])
    directory = controller.common / "harness-runs" / controller.state.run_id / task["id"] / (attempt_id + "-repair")
    directory.mkdir(parents=True, exist_ok=False)
    prompt = ("Repair only the current task's observed failures. Do not weaken acceptance/check configuration, "
              "push, merge or deploy. Inspect the original logs cited below, update code/knowledge/reports as needed "
              "and commit the final correction on this source branch.\nTask:\n" + json.dumps(task, ensure_ascii=False)
              + "\nObserved failure:\n" + feedback)
    values = {"worktree": str(path), "task_id": task["id"], "prompt": prompt,
              "input": str(directory / "prompt.txt"), "output": str(directory / "host-result.txt")}
    (directory / "prompt.txt").write_text(prompt)
    result = controller.execute(render_argv(config["host"]["implementation_argv"], values), path,
                                attempt_id + "-repair", directory / "host.log",
                                timeout=config["limits"]["implementation_seconds"], scope="implementation")
    if result["exit_code"] != 0 or result["reason"] or git(path, "status", "--porcelain"):
        raise Blocked("repair failed or left uncommitted files; preserve worktree")
    return result


def run_serial(controller, config, tasks, attempt_prefix, implement=False):
    mapping = {t["id"]: t for t in tasks}
    if len(mapping) != len(tasks):
        raise Blocked("duplicate task IDs")
    graph = {t["id"]: t.get("dependencies", []) for t in tasks}
    if any(d not in mapping for deps in graph.values() for d in deps):
        raise Blocked("missing dependency task")
    try:
        order = list(TopologicalSorter(graph).static_order())
    except CycleError as exc:
        raise Blocked("dependency cycle") from exc
    results = []
    for index, task_id in enumerate(order):
        task = mapping[task_id]
        existing = controller.state.read()["tasks"].get(task_id, {})
        if existing.get("status") in ("delivered", "completed"):
            # Even previously completed work must still be in current downstream baseline.
            git(controller.root, "merge-base", "--is-ancestor", existing["D"], task["target"])
            continue
        if existing.get("status") == "verified":
            results.append({"task_id": task_id, "status": "verified", "next_step": "explicit delivery and reconciliation required"})
            break
        attempt = f"{safe_id(attempt_prefix)}-{index}"
        if implement:
            # Dependencies checked before launching a host with side effects.
            for dep in task.get("dependencies", []):
                prior = controller.state.read()["tasks"].get(dep, {})
                if prior.get("status") not in ("delivered", "completed") or not prior.get("D"):
                    raise Blocked(f"dependency not delivered: {dep}")
                git(controller.root, "merge-base", "--is-ancestor", prior["D"], task["target"])
            implementation = implement_task(controller, config, task, attempt)
        for repair in range(min(2, config["limits"]["repair_attempts"]) + 1):
            validation_attempt = attempt if repair == 0 else attempt + "-fix" + str(repair)
            try:
                results.append(validate_task(controller, config, task, validation_attempt))
                break
            except Blocked as exc:
                if not implement or repair >= min(2, config["limits"]["repair_attempts"]):
                    raise
                # Structural/auth/stop failures must not be handed to an implementation model as code repair.
                if not any(marker in str(exc) for marker in ("required checks failed", "Blocking findings", "unmet acceptance")):
                    raise
                feedback = str(exc) + "\nInspect evidence directory: " + str(controller.common / "harness-runs" / controller.state.run_id / task["id"] / validation_attempt)
                repair_task(controller, config, task, implementation["worktree"], validation_attempt, feedback)
        # Default handoff is verified; never silently merge to unlock dependencies.
        break
    all_completed = all(controller.state.read()["tasks"].get(tid, {}).get("status") == "completed" for tid in order)
    return {"status": "handoff" if results else "completed" if all_completed else "delivered_pending_closeout", "tasks": results}


def closeout(controller, config, task, check_only=False):
    require_capabilities(controller, config)
    state = controller.state.read()
    saved = state["tasks"].get(task["id"], {})
    if saved.get("status") not in ("delivered", "completed") or not saved.get("D"):
        raise Blocked("closeout requires verified actual delivery")
    verified_evidence(controller, task, config)
    target = saved.get("platform_delivery", {}).get("target_sha") if config["mode"] == "github" else task["target"]
    if not target:
        raise Blocked("actual target delivery reference missing")
    git(controller.root, "merge-base", "--is-ancestor", saved["D"], target)
    evidence = json.loads(Path(saved["evidence"]).read_text())
    if file_fingerprint(saved["evidence"]) != saved["evidence_sha256"] or evidence["task_fingerprint"] != fingerprint(task):
        raise Blocked("closeout proof changed")
    evidence_root = controller.root
    if config["mode"] == "github":
        if not saved.get("platform_delivery", {}).get("verified_delivery"):
            raise Blocked("GitHub delivery has not been independently reconciled")
        evidence_root = controller.common / "harness-delivered" / (safe_id(task["id"]) + "-" + saved["D"])
        if not evidence_root.exists():
            evidence_root.parent.mkdir(exist_ok=True)
            git(controller.root, "worktree", "add", "--detach", str(evidence_root), saved["D"])
        elif git(evidence_root, "rev-parse", "HEAD") != saved["D"]:
            raise Blocked("delivered evidence worktree changed")
    refs = task.get("durable_evidence", []) + list(task.get("reports", {}).values())
    durable = verify_durable_evidence(evidence_root, refs, commit=saved["D"])
    if check_only:
        return {"durable_evidence": durable, "D": saved["D"], "status": "delivery_handoff_verified"}
    if config["mode"] == "github" and saved.get("issue_completion", {}).get("status") != "completed":
        raise Blocked("native Issue completion still requires authorized completion/reconciliation")
    state["tasks"][task["id"]].update(status="completed", durable_evidence=durable,
                                     handoff="task record and committed knowledge/report references verified")
    controller.state.write(state, state["revision"])
    return state["tasks"][task["id"]]
