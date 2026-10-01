"""Capability receipts bind directly executed P0 observations; ready is never proof."""
import hashlib
import json
import shutil
import tempfile
import sys
import platform
from importlib.metadata import version
from pathlib import Path
from .state import Blocked, atomic_json
from .runtime import git
from .contracts import fingerprint, check_fingerprint

REQUIRED_LIVE = ("local_process_group_stop", "repository_write", "serena_version", "serena_core_read",
                 "serena_references", "host_session_start", "host_independent_review", "host_session_resume",
                 "host_native_stop")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def binding(controller, config):
    package = Path(__file__).resolve().parent
    files = sorted([*package.rglob("*.py"), *package.rglob("*.json")])
    code = {str(p.relative_to(package)): sha(p) for p in files if "__pycache__" not in p.parts}
    skill_root = Path(config.get("environment", {}).get("skills_path", ""))
    if not skill_root.is_absolute():
        skill_root = controller.root / skill_root
    if not skill_root.is_dir():
        raise Blocked("actual loaded skills_path must exist to bind instructions")
    excluded = {".git", ".venv", "__pycache__", "node_modules", "dist"}
    skill_files = {}
    for path in sorted(skill_root.rglob("*")):
        relative = path.relative_to(skill_root)
        if any(part in excluded for part in relative.parts):
            continue
        if path.is_symlink():
            raise Blocked("loaded skill files must be concrete files, not unverified symlinks")
        if path.is_file():
            skill_files[str(relative)] = sha(path)
    if not any(name == "SKILL.md" or name.endswith("/SKILL.md") for name in skill_files):
        raise Blocked("skills_path contains no actual SKILL.md")
    if config.get("environment", {}).get("entry_skill") == "zh" and "zh/SKILL.md" not in skill_files:
        raise Blocked("$zh entry receipt must include actual zh/SKILL.md and installed dependencies")
    lock = package.parent / "uv.lock"
    if not lock.is_file():
        raise Blocked("installed tool lockfile is missing; cannot bind environment")
    host_files = {}
    for field in ("implementation_argv", "review_argv"):
        argv = config.get("host", {}).get(field, [])
        if not argv:
            raise Blocked("configured implementation and review host commands are required")
        executable = shutil.which(argv[0])
        if not executable:
            raise Blocked("host executable unavailable: " + argv[0])
        host_files[str(Path(executable).resolve())] = sha(Path(executable).resolve())
        for arg in argv[1:]:
            if isinstance(arg, str) and "{" not in arg and Path(arg).is_absolute() and Path(arg).is_file():
                host_files[str(Path(arg).resolve())] = sha(Path(arg).resolve())
    return {"mode": config["mode"], "repository_id": config["repository_id"],
            "repository_root": str(controller.root), "git_common_dir": str(controller.common),
            "config_sha256": fingerprint(config), "checks_sha256": check_fingerprint(config),
            "environment_sha256": fingerprint(config.get("environment", {})),
            "runtime_sha256": fingerprint(code), "skill_sha256": fingerprint(skill_files),
            "skills_root": str(skill_root.resolve()), "skill_files": skill_files,
            "lock_sha256": sha(lock), "host_files": host_files,
            "observed_runtime": {"python": sys.version, "os": platform.platform(),
                                 "python_executable_sha256": sha(Path(sys.executable).resolve()),
                                 "git_executable_sha256": sha(Path(shutil.which("git")).resolve()),
                                 "packages": {name: version(name) for name in ("filelock", "psutil", "jsonschema", "Markdown")}}}


def simulation_scope(controller):
    root = controller.root
    temporary = Path(tempfile.gettempdir()).resolve()
    if not root.is_relative_to(temporary):
        raise Blocked("simulation is restricted to an explicitly marked temporary fixture repository")
    if git(root, "remote"):
        raise Blocked("simulation fixture must not have a remote")
    marker = root / ".harness-simulation"
    if not marker.is_file() or marker.read_text().strip() != "isolated-harness-fixture":
        raise Blocked("simulation fixture marker missing")
    if git(root, "show", "HEAD:.harness-simulation").strip() != "isolated-harness-fixture":
        raise Blocked("simulation marker must be committed")


def record_capabilities(controller, config, tier, semantic_review=None, authorized_semantic=False):
    if not controller.entered or tier not in ("live", "simulation"):
        raise Blocked("capability receipt needs held run lock and explicit tier")
    if tier == "simulation":
        simulation_scope(controller)
    from .p0 import probe
    # Execute observations here. Never import caller-written 'success' JSON as P0 proof.
    observed = probe(config, controller=controller)
    capabilities = observed.get("capabilities", {})
    unverified = [name for name in REQUIRED_LIVE if capabilities.get(name, {}).get("status") != "verified"]
    if config["mode"] == "github" and capabilities.get("github_authenticated_capabilities", {}).get("status") != "verified":
        unverified.append("github_authenticated_capabilities")
    semantic = None
    if semantic_review is not None and authorized_semantic:
        from .knowledge import verify_durable_evidence
        semantic = verify_durable_evidence(controller.root, [semantic_review])
    else:
        unverified.append("operator_semantic_knowledge_review")
    receipt = {"version": 1, "tier": tier, "binding": binding(controller, config),
               "observations": observed, "unverified": unverified, "semantic_review": semantic,
               "status": "simulation_only" if tier == "simulation" else "ready" if not unverified else "blocked"}
    # Bind retained native and host logs in addition to structured observations.
    raw_logs = {}
    for item in controller.state.read()["attempts"]:
        for field in ("log", "stderr_log"):
            if item.get(field) and Path(item[field]).is_file():
                raw_logs[item[field]] = sha(item[field])
    drills = observed.get("host_drills", {})
    for item in drills.get("logs", {}).values():
        if isinstance(item, dict) and item.get("path") and Path(item["path"]).is_file():
            raw_logs[item["path"]] = sha(item["path"])
    if drills.get("report_path") and Path(drills["report_path"]).is_file():
        raw_logs[drills["report_path"]] = sha(drills["report_path"])
    github_probe = observed.get("github_probe", {})
    for item in github_probe.get("logs", []):
        if not isinstance(item, dict):
            continue
        for stream in ("stdout", "stderr"):
            descriptor = item.get(stream, {})
            if isinstance(descriptor, dict) and descriptor.get("path") and Path(descriptor["path"]).is_file():
                raw_logs[descriptor["path"]] = sha(descriptor["path"])
    if github_probe.get("report_path") and Path(github_probe["report_path"]).is_file():
        raw_logs[github_probe["report_path"]] = sha(github_probe["report_path"])
    receipt["raw_logs"] = raw_logs
    path = controller.common / "harness.capabilities.json"
    atomic_json(path, receipt)
    state = controller.state.read()
    state["capability_receipt"] = {"path": str(path), "sha256": sha(path), "tier": tier, "status": receipt["status"]}
    controller.state.write(state, state["revision"])
    return receipt


def require_capabilities(controller, config, *, delivery=False, simulate_delivery=False):
    pointer = controller.state.read().get("capability_receipt")
    if not pointer or not Path(pointer["path"]).is_file() or sha(pointer["path"]) != pointer.get("sha256"):
        raise Blocked("valid P0 capability receipt missing or altered; ready=true is insufficient")
    receipt = json.loads(Path(pointer["path"]).read_text())
    if receipt["binding"] != binding(controller, config):
        raise Blocked("P0 capability receipt stale: repository, mode, config, host, skill or dependency lock changed")
    if any(not Path(path).is_file() or sha(path) != digest for path, digest in receipt.get("raw_logs", {}).items()):
        raise Blocked("P0 raw capability evidence missing or changed")
    if receipt["tier"] == "simulation":
        simulation_scope(controller)
        if delivery and not simulate_delivery:
            raise Blocked("simulation receipt cannot authorize real delivery; explicit isolated simulation delivery required")
    elif receipt.get("status") != "ready" or receipt.get("unverified"):
        raise Blocked("real P0 capability gaps remain: " + ", ".join(receipt.get("unverified", [])))
    return receipt
