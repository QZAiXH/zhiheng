"""Observe bounded P0 capabilities without enabling the workflow.

Version/help output is not host session, independent-review or resume proof.
Project mutations (including native Serena cache side effects) require a real,
entered matching Controller. Synthetic stop probes use only a temporary repo.
"""
import hashlib
import json
import math
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

from .harness_check import fingerprint
from .runtime import Controller, owned
from .state import Blocked

HOST_GAPS = {
    "host_session_start": "A real configured Codex execution session and its native identity have not been verified by this probe.",
    "host_independent_review": "A separate real review session must inspect actual requirements and evidence; self-reported JSON is insufficient.",
    "host_native_stop": "A local process-group stop does not prove the host's native session or remote execution stopped.",
    "host_session_resume": "A new host session must actually read the handoff and resume the same task safely.",
    "knowledge_semantic_readiness": "Core/reference reads do not prove completed onboarding, correct knowledge, or host activation."
}
MAX_CAPTURE = 64 * 1024


def _cap(status, detail, **evidence):
    return {"status": status, "detail": detail, **evidence}


def _positive(value, name, integer=False):
    if type(value) not in ((int,) if integer else (int, float)):
        raise Blocked("P0 positive finite limit required: " + name)
    try:
        valid = math.isfinite(value) and value > 0
    except OverflowError:
        valid = False
    if not valid:
        raise Blocked("P0 positive finite limit required: " + name)
    return value


def _entered_controller(controller, root):
    return (isinstance(controller, Controller) and controller.entered
            and controller.run_lock.is_locked and Path(controller.root).resolve() == root)


def _execute(controller, argv, name, timeout):
    if controller.journal.exists():
        prior = json.loads(controller.journal.read_text())
        if not prior.get("stopped"):
            raise Blocked("Previous probe execution stop is unconfirmed; no further dispatch")
    log = controller.root / ("p0-" + name + ".log")
    result = controller.execute(argv, controller.root, "probe-" + name, log, timeout=timeout)
    with log.open("rb") as stream:
        raw = stream.read(MAX_CAPTURE + 1)
    output = raw[:MAX_CAPTURE].decode("utf-8", errors="replace")
    # Fingerprint exactly the bounded bytes presented, and disclose truncation.
    return result, {"argv": argv, "exit_code": result["exit_code"], "reason": result["reason"],
                    "stopped": result["stopped"], "output": output,
                    "captured_sha256": hashlib.sha256(raw[:MAX_CAPTURE]).hexdigest(),
                    "output_truncated": len(raw) > MAX_CAPTURE,
                    "elapsed_seconds": result["elapsed_seconds"]}


def _successful(controller, argv, name, timeout):
    result, evidence = _execute(controller, argv, name, timeout)
    if result["exit_code"] != 0 or result["reason"] or not result["stopped"]:
        return _cap("blocked", "The bounded command did not finish successfully and stop.", **evidence)
    return _cap("verified", "This specific bounded command ran and exited successfully.", **evidence)


def probe(config, controller=None):
    """Return observed per-capability results; never set config.ready or write a report.

    Uses config.limits.command_seconds/stop_grace_seconds/task_seconds. Optional
    config.p0.max_commands (default 8) is a probe-only bound, never a task retry
    override. p0.smoke_argv is an explicit actual invocation in the temp repo;
    {worktree} expands to that directory, with no shell. Even success is only a
    command smoke result, not independent review/start/stop/resume attestation.
    p0.register_existing=true requires a matching entered project controller.
    """
    capabilities = {
        name: _cap("blocked", "This required capability has not been observed.")
        for name in ("git_version", "codex_version", "temporary_filesystem_io",
                     "local_process_group_stop", "host_command_smoke", "serena_native_probe")
    }
    report = {"version": 1, "kind": "p0_observations", "capabilities": capabilities,
              "changes_ready": False, "automation_readiness": {"status": "blocked", "gaps": []},
              "notice": "Observed capability results are scoped to their actual probes; no summary enables execution."}
    if not isinstance(config, dict):
        capabilities["configuration"] = _cap("blocked", "Config must be an object.")
        return report
    try:
        report["config_sha256"] = fingerprint(config)
        report["declared_environment_sha256"] = fingerprint(config.get("environment", {}))
        limits = config.get("limits", {})
        options = config.get("p0", {})
        if not isinstance(limits, dict) or not isinstance(options, dict):
            raise Blocked("limits and p0 must be objects")
        command_seconds = _positive(limits.get("command_seconds"), "command_seconds")
        grace = _positive(limits.get("stop_grace_seconds"), "stop_grace_seconds")
        total = _positive(limits.get("task_seconds"), "task_seconds")
        maximum = _positive(options.get("max_commands", 8), "p0.max_commands", integer=True)
        mode = config.get("mode")
        if mode not in ("local", "github"):
            raise Blocked("P0 requires an explicit local/github mode")
        value = config.get("repository_root")
        if not isinstance(value, str) or not Path(value).is_absolute() or not Path(value).is_dir():
            raise Blocked("P0 repository_root must be an existing absolute directory")
        root = Path(value).resolve()
        if not isinstance(config.get("host", {}), dict):
            raise Blocked("host must be an object")
    except (Blocked, ValueError, TypeError, OSError) as exc:
        capabilities["configuration"] = _cap("blocked", str(exc))
        report["automation_readiness"]["gaps"] = ["configuration"]
        return report
    observed = {"os": platform.platform(), "python": sys.version, "python_executable": sys.executable}
    report["observed_environment"] = observed
    for name, message in HOST_GAPS.items():
        capabilities[name] = _cap("blocked", message)
    try:
        # This verifies enumeration/read access only, not write permissions or Git health.
        with os.scandir(root) as entries:
            count = sum(1 for _ in entries)
        capabilities["repository_read"] = _cap("verified", "Enumerated the actual repository directory.", entry_count=count)
    except OSError as exc:
        capabilities["repository_read"] = _cap("blocked", str(exc))
    capabilities["repository_write"] = _cap("blocked", "A project write probe requires its entered Controller.")
    executables = options.get("executables", {})
    if not isinstance(executables, dict):
        capabilities["configuration"] = _cap("blocked", "p0.executables must be an object")
        executables = {}
    git_command = executables.get("git", "git")
    git_path = shutil.which(git_command) if isinstance(git_command, str) else None
    temporary = None
    safe_cleanup = True
    if not git_path:
        capabilities["git_executable"] = _cap("blocked", "Git executable was not found; temporary controller probes cannot start.")
    else:
        temporary = Path(tempfile.mkdtemp(prefix="harness-p0-"))
        try:
            # Trusted Git init is constrained to a new temporary directory; no user's repo mutation.
            env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
            initialized = subprocess.run([git_path, "-c", "init.defaultBranch=main", "init", "--template=", str(temporary)],
                                         capture_output=True, timeout=command_seconds, env=env)
            if initialized.returncode:
                raise Blocked("Temporary Git initialization failed")
            probe_limits = {"command_seconds": command_seconds, "stop_grace_seconds": grace,
                            "total_seconds": total, "max_attempts": maximum}
            with Controller(temporary, "local", "p0-probe", probe_limits) as temp_controller:
                probes = [("git_version", git_path, ["--version"])]
                host_command = executables.get("codex", config.get("host", {}).get("executable", "codex"))
                codex_path = shutil.which(host_command) if isinstance(host_command, str) else None
                if codex_path:
                    probes.extend([("codex_version", codex_path, ["--version"]), ("codex_help", codex_path, ["--help"])])
                else:
                    capabilities["codex_version"] = _cap("blocked", "Configured Codex executable was not found.")
                if mode == "github":
                    gh_command = executables.get("gh", "gh")
                    gh_path = shutil.which(gh_command) if isinstance(gh_command, str) else None
                    if gh_path:
                        probes.append(("gh_version", gh_path, ["--version"]))
                    else:
                        capabilities["gh_version"] = _cap("blocked", "GitHub mode requires a gh executable.")
                    capabilities["github_authenticated_capabilities"] = _cap("blocked", "Version output does not prove repository access, CI, review, strict checks or merge-group behavior.")
                else:
                    capabilities["github_authenticated_capabilities"] = _cap("not_applicable", "Local mode does not invoke gh or GitHub APIs.")
                for name, executable, arguments in probes:
                    try:
                        cap = _successful(temp_controller, [executable, *arguments], name, command_seconds)
                        cap["executable"] = executable
                        capabilities[name] = cap
                        if cap["status"] == "verified":
                            observed[name] = cap["output"].strip()
                    except (Blocked, OSError, ValueError) as exc:
                        capabilities[name] = _cap("blocked", str(exc))
                try:
                    code = ("from pathlib import Path; p=Path('p0-file-probe'); "
                            "p.write_bytes(b'harness-p0'); assert p.read_bytes()==b'harness-p0'; p.unlink(); print('read-write-delete-confirmed')")
                    capabilities["temporary_filesystem_io"] = _successful(temp_controller, [sys.executable, "-c", code], "filesystem", command_seconds)
                except (Blocked, OSError, ValueError) as exc:
                    capabilities["temporary_filesystem_io"] = _cap("blocked", str(exc))
                try:
                    # Both owned processes are synthetic and sleep until the runtime cancels them.
                    code = ("import subprocess,sys,time,json; "
                            "p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)']); "
                            "print(json.dumps({'child_pid':p.pid}),flush=True); time.sleep(60)")
                    result, evidence = _execute(temp_controller, [sys.executable, "-c", code], "stop", min(command_seconds, 0.5))
                    journal = json.loads(temp_controller.journal.read_text())
                    identities = journal.get("processes", [])
                    actual_stopped = bool(identities) and all(owned(identity) is None for identity in identities)
                    child_reported = '"child_pid"' in evidence["output"]
                    okay = (result["reason"] == "timeout" and result["stopped"] and actual_stopped
                            and len(identities) >= 2 and child_reported)
                    capabilities["local_process_group_stop"] = _cap("verified" if okay else "blocked",
                        "Synthetic parent and child stop independently rechecked by process identity; does not prove host-native/remote cancellation.",
                        observed_processes=identities, actual_stop_confirmed=actual_stopped, **evidence)
                    safe_cleanup = actual_stopped
                except (Blocked, OSError, ValueError, KeyError) as exc:
                    capabilities["local_process_group_stop"] = _cap("blocked", str(exc))
                    if temp_controller.journal.exists():
                        try:
                            journal = json.loads(temp_controller.journal.read_text())
                            safe_cleanup = bool(journal.get("stopped")) and all(owned(item) is None for item in journal.get("processes", []))
                        except Exception:
                            safe_cleanup = False
                if options.get("run_host_drills") is True:
                    try:
                        from .codex_probe import run_host_drills
                        if not codex_path:
                            raise Blocked("Configured Codex executable was not found for actual host drills")
                        drills = run_host_drills(temp_controller, codex_path, options.get("output_dir"),
                                                 project_root=root, project_controller=controller,
                                                 timeout_seconds=command_seconds,
                                                 config_sha256=report["config_sha256"],
                                                 declared_environment_sha256=report["declared_environment_sha256"],
                                                 cancel_options=({"startup_seconds": options.get("cancel_startup_seconds"),
                                                                  "sleep_seconds": options.get("cancel_sleep_seconds"),
                                                                  "total_seconds": options.get("cancel_total_seconds")}
                                                                 if options.get("run_host_cancel_drill") is True else None))
                        report["host_drills"] = drills
                        capabilities.update(drills["capabilities"])
                        capabilities["host_native_stop"] = drills["host_native_stop"]
                        capabilities["host_command_smoke"] = capabilities["host_session_start"]
                    except (Blocked, OSError, ValueError) as exc:
                        capabilities["host_command_smoke"] = _cap("blocked", str(exc))
                smoke = options.get("smoke_argv")
                if options.get("run_host_drills") is True:
                    pass  # At most the three explicit drill calls; never a fourth optional smoke.
                elif smoke is not None:
                    if not isinstance(smoke, list) or not smoke or not all(isinstance(arg, str) for arg in smoke):
                        capabilities["host_command_smoke"] = _cap("blocked", "p0.smoke_argv must be an explicit nonempty argv list.")
                    else:
                        try:
                            argv = [arg.replace("{worktree}", str(temporary)) for arg in smoke]
                            if (not codex_path or argv[:7] != [codex_path, "exec", "--sandbox", "read-only", "--json", "--cd", str(temporary)]
                                    or len(argv) != 8 or not argv[-1].strip() or argv[-1].startswith("-")):
                                raise Blocked("Only exact Codex read-only smoke argv is supported: [resolved_codex, exec, --sandbox, read-only, --json, --cd, {worktree}, prompt]; arbitrary commands/config overrides are refused")
                            capabilities["host_command_smoke"] = _successful(temp_controller, argv, "host-smoke", command_seconds)
                        except (Blocked, OSError, ValueError) as exc:
                            capabilities["host_command_smoke"] = _cap("blocked", str(exc))
                else:
                    capabilities["host_command_smoke"] = _cap("blocked", "No explicit host smoke invocation was supplied.")
                if mode == "github":
                    try:
                        from .github_probe import probe_github
                        if not gh_path:
                            raise Blocked("Configured gh executable was not found")
                        github_report = probe_github(config, temp_controller, options.get("output_dir"),
                                                     project_controller=controller, executable=gh_path)
                        report["github_probe"] = github_report
                        capabilities["github_automatic_merge_rules"] = github_report["automatic_merge_rules"]
                        capabilities["github_authenticated_capabilities"] = {
                            "status": github_report["status"], "detail": github_report["detail"],
                            "report_path": github_report["report_path"], "report_sha256": github_report["report_sha256"]}
                    except (Blocked, OSError, ValueError) as exc:
                        capabilities["github_authenticated_capabilities"] = _cap("blocked", str(exc))
        except (Blocked, OSError, subprocess.TimeoutExpired, ValueError, KeyError) as exc:
            capabilities["temporary_controller"] = _cap("blocked", str(exc))
        finally:
            if temporary is not None:
                journal_path = temporary / ".git/harness.execution.json"
                if journal_path.exists():
                    try:
                        last = json.loads(journal_path.read_text())
                        safe_cleanup = safe_cleanup and bool(last.get("stopped")) and all(owned(item) is None for item in last.get("processes", []))
                    except Exception:
                        safe_cleanup = False
                if safe_cleanup:
                    shutil.rmtree(temporary)
                else:
                    report["preserved_probe_directory"] = str(temporary)
                    capabilities["temporary_controller_cleanup"] = _cap("blocked", "Execution stop is unconfirmed; probe files were preserved for reconciliation.")
    if _entered_controller(controller, root):
        try:
            token = uuid.uuid4().hex
            log = controller.common / "harness-p0" / (token + ".log")
            file = controller.common / ("harness-p0-write-" + token)
            code = ("from pathlib import Path; p=Path(" + repr(str(file)) + "); "
                    "p.write_bytes(b'harness-p0'); assert p.read_bytes()==b'harness-p0'; p.unlink(); print('project-common-dir-write-confirmed')")
            result = controller.execute([sys.executable, "-c", code], root, "p0-write-" + token, log, timeout=command_seconds)
            okay = result["exit_code"] == 0 and not result["reason"] and result["stopped"] and not file.exists()
            capabilities["repository_write"] = _cap("verified" if okay else "blocked",
                "Actual locked repository common-directory write/read/delete probe; does not assert every working-tree path is writable.", record=result)
        except (Blocked, OSError, ValueError) as exc:
            capabilities["repository_write"] = _cap("blocked", str(exc))
        knowledge = config.get("knowledge", {})
        if isinstance(knowledge, dict) and knowledge.get("executable") and knowledge.get("serena_home"):
            try:
                from .knowledge import SerenaAdapter
                adapter = SerenaAdapter(root, knowledge["executable"], knowledge["serena_home"],
                                        timeout_seconds=command_seconds, python_executable=knowledge.get("python_executable"),
                                        controller=controller)
                capabilities["serena_version"] = _cap("verified", "Native pinned version command observed.", result=adapter.probe_version())
                if options.get("register_existing") is True:
                    capabilities["serena_registration"] = _cap("verified", "Explicit native registration executed under the project controller.", result=adapter.register_existing())
                else:
                    capabilities["serena_registration"] = _cap("blocked", "Native registration was not explicitly requested; project-file existence is insufficient.")
                capabilities["serena_core_read"] = _cap("verified", "Read actual substantive project-local core through native Serena.", result=adapter.read_core())
                capabilities["serena_references"] = _cap("verified", "Native reference verdict parsed; this is not semantic correctness.", result=adapter.check_references())
                capabilities["serena_native_probe"] = _cap("verified", "Pinned native version, core read and parsed reference check actually completed; see separate registration/semantic gaps.")
            except (Blocked, OSError, ValueError) as exc:
                capabilities["serena_native_probe"] = _cap("blocked", str(exc))
        else:
            capabilities["serena_native_probe"] = _cap("blocked", "Pinned executable and dedicated serena_home were not configured.")
    else:
        capabilities["serena_native_probe"] = _cap("blocked", "Native Serena calls may write cache/config; provide the actual entered matching project controller.")
    report["observed_environment_sha256"] = fingerprint(observed)
    report["automation_readiness"]["gaps"] = sorted(name for name, capability in capabilities.items() if capability["status"] == "blocked")
    # This implementation intentionally cannot erase HOST_GAPS via caller-supplied readiness JSON.
    return report
