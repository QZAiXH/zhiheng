"""Bounded optional Codex CLI drills with an explicitly selected model and call budget."""
import hashlib
import json
import math
import os
import signal
import sys
import threading
import time
import re
import secrets
import shutil
import uuid
from pathlib import Path

from .runtime import Controller, owned
from .state import Blocked

MAX_LOG_BYTES = 8 * 1024 * 1024


class ProbeFailed(ValueError):
    pass


def parse_events(raw):
    """Read public --json events only; never inspect Codex's private session files."""
    if not isinstance(raw, bytes) or not raw or len(raw) > MAX_LOG_BYTES:
        raise ProbeFailed("JSONL log must contain 1..8388608 bytes")
    try:
        text = raw.decode("utf-8")
    except UnicodeError as exc:
        raise ProbeFailed("Host log is not UTF-8") from exc
    thread_ids, messages, reads, command_outputs = [], [], set(), []
    completed = False
    diagnostics = []
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except ValueError:
            # Runtime merges stderr with stdout. Retain version/auth warnings in raw log.
            diagnostics.append(line[:1000])
            continue
        if not isinstance(event, dict):
            raise ProbeFailed("Unexpected non-object JSON event")
        kind = event.get("type")
        if kind in ("error", "turn.failed"):
            raise ProbeFailed("Host emitted an error/failed turn; see preserved raw log")
        if kind == "thread.started":
            thread_id = event.get("thread_id")
            try:
                uuid.UUID(thread_id)
            except (ValueError, TypeError, AttributeError) as exc:
                raise ProbeFailed("Host did not return a usable native session UUID") from exc
            thread_ids.append(thread_id)
        elif kind == "turn.completed":
            completed = True
        elif kind == "item.completed":
            item = event.get("item")
            if not isinstance(item, dict):
                raise ProbeFailed("Malformed completed host item")
            if item.get("type") == "agent_message" and isinstance(item.get("text"), str):
                messages.append(item["text"])
            if (item.get("type") == "command_execution" and item.get("exit_code") == 0
                    and type(item.get("exit_code")) is int and item.get("status") == "completed"):
                emitted = item.get("aggregated_output", item.get("output", ""))
                if isinstance(emitted, str):
                    command_outputs.append(emitted)
                command = item.get("command", "")
                if isinstance(command, str):
                    for filename in ("fixture.py", "acceptance.md"):
                        if filename in command:
                            reads.add(filename)
    if not thread_ids or len(set(thread_ids)) != 1 or not completed or not messages:
        raise ProbeFailed("Missing unique native session ID, completed turn, or final agent message")
    return {"thread_id": thread_ids[0], "final": messages[-1].strip(),
            "read_files": sorted(reads), "command_output": "\n".join(command_outputs), "diagnostics": diagnostics[:10]}


def _canonical_artifact_path(value):
    """Accept only verified macOS system aliases; keep arbitrary symlink refusal.

    Do not call resolve() on the supplied path before inspecting components:
    that would erase evidence of an inner user-controlled symlink or escape.
    """
    if not isinstance(value, str) or not value or not Path(value).is_absolute():
        raise Blocked("p0.output_dir must explicitly name an absolute artifact directory")
    path = Path(value)
    if ".." in path.parts:
        raise Blocked("p0.output_dir must be normalized")
    if sys.platform == "darwin" and len(path.parts) >= 2 and path.parts[0] == "/":
        expected = {"var": Path("/private/var"), "tmp": Path("/private/tmp")}.get(path.parts[1])
        if expected is not None:
            alias = Path("/") / path.parts[1]
            if alias.is_symlink():
                try:
                    target = Path(os.readlink(alias))
                except OSError as exc:
                    raise Blocked("Cannot verify macOS system path alias") from exc
                if not target.is_absolute():
                    target = alias.parent / target
                # normpath is lexical: never follow an unexpected link chain.
                if Path(os.path.normpath(str(target))) != expected or not expected.is_dir():
                    raise Blocked("Unexpected macOS system path alias target")
                path = expected.joinpath(*path.parts[2:])
    for candidate in (path, *path.parents):
        if candidate.is_symlink():
            raise Blocked("Symlink artifact paths are refused")
    return path


def _output_directory(value, project_root, project_controller, label="host-drills"):
    path = _canonical_artifact_path(value)
    root = Path(project_root).resolve()
    if path.resolve().is_relative_to(root):
        if (not isinstance(project_controller, Controller) or not project_controller.entered
                or not project_controller.run_lock.is_locked or Path(project_controller.root).resolve() != root):
            raise Blocked("Saving P0 artifacts inside the target project requires its matching entered Controller")
    path.mkdir(parents=True, exist_ok=True)
    output = path / (label + "-" + uuid.uuid4().hex)
    output.mkdir(exist_ok=False)
    return output


def explicit_model_args(model, max_model_calls):
    """Validate opt-in cost choices and return invocation-only native CLI overrides."""
    if not isinstance(model, str) or not model or any(c.isspace() for c in model):
        raise Blocked("Host probes require an explicit nonempty model identifier")
    if type(max_model_calls) is not int or not 1 <= max_model_calls <= 4:
        raise Blocked("Host probes require an explicit max_model_calls integer in 1..4")
    return ["--model", model, "-c", "review_model=" + json.dumps(model),
            "-c", 'model_reasoning_effort="low"', "-c", 'service_tier="default"']


def run_host_drills(controller, executable, output_dir, *, project_root,
                    project_controller=None, timeout_seconds, config_sha256,
                    declared_environment_sha256, model=None, max_model_calls=None,
                    cancel_options=None):
    """Run three read-only calls, plus an explicitly requested fourth cancellation drill.

    Start -> fresh independent review -> exact-session resume. Output JSON is a
    report of direct observations, never a configuration readiness grant.
    """
    if not isinstance(controller, Controller) or not controller.entered or not controller.run_lock.is_locked:
        raise Blocked("Host drills require the actual entered temporary Controller")
    if not isinstance(executable, str) or not Path(executable).is_absolute():
        raise Blocked("Host executable must be the resolved configured Codex path")
    policy_args = explicit_model_args(model, max_model_calls)
    if cancel_options is not None:
        if not isinstance(cancel_options, dict):
            raise Blocked("Cancellation drill limits must be an object")
        for field in ("startup_seconds", "sleep_seconds", "total_seconds"):
            value = cancel_options.get(field)
            if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
                raise Blocked("Cancellation drill requires positive finite " + field)
        if not cancel_options["startup_seconds"] < cancel_options["total_seconds"] <= timeout_seconds:
            raise Blocked("Cancellation startup must be less than total, and total no greater than command timeout")
        if cancel_options["sleep_seconds"] <= cancel_options["total_seconds"]:
            raise Blocked("Bounded sleep must outlast the cancellation window to establish interruption")
        if cancel_options["sleep_seconds"] > controller.limits["total_seconds"]:
            raise Blocked("Synthetic sleep backup bound cannot exceed the P0 total budget")
    output = _output_directory(output_dir, project_root, project_controller)
    nonce = secrets.token_hex(16)
    capabilities = {name: {"status": "blocked", "detail": "This real host drill has not completed."}
                    for name in ("host_session_start", "host_independent_review", "host_session_resume")}
    result = {"version": 1, "kind": "codex_host_drills", "config_sha256": config_sha256,
              "declared_environment_sha256": declared_environment_sha256,
              "executable": executable, "artifact_directory": str(output),
              "capabilities": capabilities, "calls_started": 0, "call_limit": max_model_calls,
              "model_policy": {"model": model, "review_model": model,
                               "reasoning_effort": "low", "service_tier": "default",
                               "script_retries": 0,
                               "budget_unit": "Codex invocation; not API requests or currency"},
              "host_native_stop": {"status": "blocked", "detail": "Successful CLI exits do not exercise cancellation; a real owned host cancellation drill remains required."},
              "notice": "Bounded scoped read-only session drills, with explicit model/low reasoning/standard tier and optional owned-process cancellation; no model substitution, credential copy, security bypass or automatic readiness change."}

    def save():
        raw = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n"
        path = output / "report.json"
        # Only this invocation owns its new unique output directory.
        path.write_bytes(raw)
        return {**result, "report_path": str(path), "report_sha256": hashlib.sha256(raw).hexdigest()}

    def run(name, argv, cancellation=False):
        if result["calls_started"] >= result["call_limit"]:
            raise ProbeFailed("Explicit host drill call bound reached")
        if controller.journal.exists():
            previous = json.loads(controller.journal.read_text())
            if not previous.get("stopped"):
                raise ProbeFailed("Prior execution stop is unknown; no further host calls")
        result["calls_started"] += 1
        save()  # Charge before launching, including failed or uncertain starts.
        log = controller.root / ("host-drill-" + name + ".jsonl")
        try:
            record = controller.execute(argv, controller.root, "host-drill-" + name, log,
                                        timeout=cancel_options["total_seconds"] if cancellation else timeout_seconds)
        except (Blocked, OSError, ValueError) as exc:
            if log.is_file():
                failed_copy = output / log.name
                shutil.copyfile(log, failed_copy)
                digest = hashlib.sha256()
                with failed_copy.open("rb") as stream:
                    for chunk in iter(lambda: stream.read(65536), b""):
                        digest.update(chunk)
                result.setdefault("logs", {})[name] = {"path": str(failed_copy), "sha256": digest.hexdigest(),
                                                      "bytes": failed_copy.stat().st_size, "argv": argv, "error": str(exc)}
            raise
        destination = output / log.name
        shutil.copyfile(log, destination)
        with destination.open("rb") as stream:
            raw = stream.read(MAX_LOG_BYTES + 1)
        digest = hashlib.sha256()
        with destination.open("rb") as stream:
            for chunk in iter(lambda: stream.read(65536), b""):
                digest.update(chunk)
        descriptor = {"path": str(destination), "sha256": digest.hexdigest(),
                      "model_policy": dict(result["model_policy"]),
                      "bytes": destination.stat().st_size, "argv": argv, "execution": record}
        result.setdefault("logs", {})[name] = descriptor
        if len(raw) > MAX_LOG_BYTES:
            raise ProbeFailed("Preserved raw log is too large for this bounded parser")
        if cancellation:
            return raw, descriptor, record
        if record["exit_code"] != 0 or record["reason"] or not record["stopped"]:
            raise ProbeFailed("Codex invocation failed, timed out, or did not stop; authentication/availability errors are not success")
        return parse_events(raw), descriptor

    # Actual exec/resume --help support --model/-c; official schema documents
    # review_model, model_reasoning_effort and service_tier="default".
    prefix = [executable, "exec", "--sandbox", "read-only", "--json", "--cd", str(controller.root)] + policy_args
    start_prompt = ("This is a bounded P0 host-session drill. Remember the nonce " + nonce +
                    " in this session for a later resume. Do not read files, use tools, modify anything or access the network. "
                    "Your entire final response must be exactly HARNESS_P0_START:" + nonce)
    try:
        events, log = run("start", prefix + [start_prompt])
        if events["final"] != "HARNESS_P0_START:" + nonce:
            raise ProbeFailed("Initial session did not return the exact random final marker")
        session_id = events["thread_id"]
        capabilities["host_session_start"] = {"status": "verified", "detail": "Actual configured read-only CLI session returned a native UUID and completed the nonce turn.",
                                              "session_id": session_id, "log": log}
    except (Blocked, OSError, ValueError, KeyError) as exc:
        capabilities["host_session_start"]["detail"] = str(exc)
        return save()

    fixture = "def apply_discount(subtotal, rate):\n    return subtotal * (1 + rate)\n"
    acceptance = "AC-discount: apply_discount(100, 0.1) must return 90. A discount must reduce the subtotal.\n"
    (controller.root / "fixture.py").write_text(fixture, encoding="utf-8")
    (controller.root / "acceptance.md").write_text(acceptance, encoding="utf-8")
    (output / "fixture.py").write_text(fixture, encoding="utf-8")
    (output / "acceptance.md").write_text(acceptance, encoding="utf-8")
    result["fixture_sha256"] = hashlib.sha256(fixture.encode()).hexdigest()
    result["acceptance_sha256"] = hashlib.sha256(acceptance.encode()).hexdigest()
    review_prompt = ("This is a separate independent review session for a synthetic P0 fixture. "
                     "Use a read-only shell command to read fixture.py and acceptance.md from this worktree; do not modify files. "
                     "Decide whether the actual implementation satisfies AC-discount. Return exactly one JSON object with keys "
                     "acceptance_id, status (passed or failed), actual (number for the specified call), expected (number), "
                     "finding (specific explanation), and location (file and line). No Markdown or other text.")
    try:
        events, log = run("review", prefix + [review_prompt])
        if events["thread_id"] == session_id:
            raise ProbeFailed("Review reused the implementation session rather than starting an independent process/session")
        if set(events["read_files"]) != {"fixture.py", "acceptance.md"}:
            raise ProbeFailed("The public execution events do not establish successful reads of both fixture and acceptance files")
        if fixture.strip() not in events["command_output"] or acceptance.strip() not in events["command_output"]:
            raise ProbeFailed("Successful command events did not preserve the actual fixture and acceptance content")
        assessment = json.loads(events["final"])
        if not isinstance(assessment, dict):
            raise ProbeFailed("Review final response was not a JSON object")
        actual, expected = assessment.get("actual"), assessment.get("expected")
        if (assessment.get("acceptance_id") != "AC-discount" or assessment.get("status") != "failed"
                or type(actual) not in (int, float) or not math.isclose(actual, 110.0, rel_tol=1e-9)
                or type(expected) not in (int, float) or expected != 90
                or not isinstance(assessment.get("finding"), str) or len(assessment["finding"].strip()) < 10
                or not re.search(r"fixture\.py.*(?:line\s*)?2\b", str(assessment.get("location", "")))):
            raise ProbeFailed("Fresh review did not correctly identify the known failed acceptance and line-2 defect")
        capabilities["host_independent_review"] = {"status": "verified", "detail": "A fresh real read-only session read both files and detected the known synthetic failing acceptance.",
                                                   "session_id": events["thread_id"], "assessment": assessment, "log": log}
    except (Blocked, OSError, ValueError, KeyError, TypeError) as exc:
        capabilities["host_independent_review"]["detail"] = str(exc)

    # Do not reveal the nonce again: successful output must come from native session continuity.
    resume_prompt = ("Resume the P0 session. Without reading files, using tools or modifying anything, recall the nonce "
                     "given in this session's initial turn. Return exactly HARNESS_P0_RESUME: followed by that original nonce. "
                     "If it is unavailable, return MISSING rather than inventing it.")
    resume_argv = [executable, "exec", "--sandbox", "read-only", "--cd", str(controller.root),
                   "resume", "--json", *policy_args, session_id, resume_prompt]
    try:
        events, log = run("resume", resume_argv)
        if events["thread_id"] != session_id or events["final"] != "HARNESS_P0_RESUME:" + nonce:
            raise ProbeFailed("Exact returned session ID or original nonce continuity was not confirmed")
        capabilities["host_session_resume"] = {"status": "verified", "detail": "The exact native session UUID resumed in another CLI process and recovered the original nonce absent from its new prompt.",
                                               "session_id": session_id, "log": log}
    except (Blocked, OSError, ValueError, KeyError) as exc:
        capabilities["host_session_resume"]["detail"] = str(exc)
    if cancel_options is not None:
        try:
            cancellation = _cancel_host(controller, executable, prefix, run, output, cancel_options)
            result["host_native_stop"] = cancellation
            capabilities["host_native_stop"] = cancellation
        except (Blocked, OSError, ValueError, KeyError) as exc:
            result["host_native_stop"] = {"status": "blocked", "detail": str(exc),
                                           "scope": "configured_local_cli_and_owned_descendants"}
            capabilities["host_native_stop"] = result["host_native_stop"]
    return save()


def _cancel_host(controller, executable, prefix, run, output, limits):
    """Observe a real host-created uniquely marked child before a graceful SIGINT.

    Does not infer cancellation of any remote/model server, CI or queued action.
    Signals only the controller's verified process group, with PID start-time
    checks immediately before signalling and independent rechecks after exit.
    """
    token = "HARNESS_CANCEL_" + secrets.token_hex(16)
    script = controller.root / ("p0_cancel_" + token + ".py")
    body = ("import sys,time\n" + "assert sys.argv[1] == " + repr(token) + "\n" +
            "print(" + repr(token) + ", flush=True)\n" +
            "time.sleep(" + repr(limits["sleep_seconds"]) + ")\n")
    script.write_text(body, encoding="utf-8")
    retained_script = output / script.name
    retained_script.write_text(body, encoding="utf-8")
    log_path = controller.root / "host-drill-cancel.jsonl"
    command = [sys.executable, str(script), token]
    prompt = ("This is an explicitly authorized bounded local cancellation drill. In this read-only worktree, "
              "execute exactly this argv with your shell/tool, then wait for it; do not spawn any other job, "
              "modify files, access the network, or detach processes. The controller will interrupt this "
              "owned session after it observes the sleep child. Exact argv: " + json.dumps(command) +
              ". Do not simulate the command or merely describe it.")
    stop_watch = threading.Event()
    observation = {"signal_sent": False, "token": token}
    deadline = time.monotonic() + limits["startup_seconds"]

    def watch():
        while not stop_watch.wait(0.025):
            if time.monotonic() >= deadline:
                observation["blocker"] = "The actual uniquely marked sleep child was not observed before startup deadline"
                return
            try:
                if not log_path.exists() or not controller.journal.exists():
                    continue
                if log_path.stat().st_size > MAX_LOG_BYTES:
                    observation["blocker"] = "Cancellation log exceeded parser bound before stop proof"
                    return
                raw = log_path.read_text(encoding="utf-8", errors="replace")
                command_seen = False
                session_id = None
                for line in raw.splitlines():
                    try:
                        event = json.loads(line)
                    except ValueError:
                        continue
                    if not isinstance(event, dict):
                        continue
                    if event.get("type") == "thread.started":
                        candidate = event.get("thread_id")
                        try:
                            uuid.UUID(candidate)
                            session_id = candidate
                        except (ValueError, TypeError, AttributeError):
                            pass
                    item = event.get("item", {})
                    if (event.get("type") in ("item.started", "item.updated", "item.completed")
                            and isinstance(item, dict) and item.get("type") == "command_execution"
                            and token in str(item.get("command", "")) and script.name in str(item.get("command", ""))):
                        command_seen = True
                if not command_seen or not session_id:
                    continue
                journal = json.loads(controller.journal.read_text())
                if journal.get("attempt_id") != "host-drill-cancel" or journal.get("stopped"):
                    continue
                identities = journal.get("processes", [])
                if not identities:
                    continue
                root_record = identities[0]
                root_process = owned(root_record)
                if root_process is None or os.getpgid(root_process.pid) != root_process.pid:
                    continue
                child_record = None
                for identity in identities[1:]:
                    process = owned(identity)
                    if process is None:
                        continue
                    argv = process.cmdline()
                    if str(script) in argv and token in argv:
                        child_record = identity
                        break
                if child_record is None or owned(child_record) is None or owned(root_record) is None:
                    continue
                # Observation comes from live process identity + actual public command trace,
                # never from a returned 'stopped' boolean or a PID supplied by the model.
                observation.update(session_id=session_id, root_identity=root_record,
                                   sleep_identity=child_record, command_trace_observed=True)
                os.killpg(root_record["pid"], signal.SIGINT)
                observation["signal_sent"] = True
                observation["signal"] = "SIGINT"
                return
            except (OSError, ValueError, KeyError, Blocked) as exc:
                observation["last_observation_error"] = str(exc)
                continue
            except Exception as exc:
                observation["blocker"] = "Cannot verify owned process identity: " + str(exc)
                return

    watcher = threading.Thread(target=watch, name="harness-owned-codex-cancel", daemon=True)
    watcher.start()
    try:
        raw, descriptor, execution = run("cancel", prefix + [prompt], cancellation=True)
    finally:
        stop_watch.set()
        watcher.join(timeout=limits["total_seconds"])
    if watcher.is_alive():
        raise ProbeFailed("Cancellation observer did not stop; reconcile before continuing")
    final = json.loads(controller.journal.read_text())
    identities = final.get("processes", [])
    all_stopped = bool(identities) and all(owned(identity) is None for identity in identities)
    matched_child = observation.get("sleep_identity") in identities
    okay = (observation["signal_sent"] and observation.get("command_trace_observed")
            and matched_child and all_stopped and execution["stopped"]
            and execution["reason"] != "timeout")
    observation.update(all_recorded_processes_stopped=all_stopped,
                       recorded_processes=identities, child_identity_retained=matched_child)
    return {"status": "verified" if okay else "blocked",
            "scope": "configured_local_cli_and_owned_descendants",
            "detail": ("Actual configured local Codex process and its observed marked sleep child were interrupted with SIGINT and independently confirmed stopped. "
                       "This does not attest cancellation of remote model services, GitHub CI, queued merges or detached jobs." if okay else
                       observation.get("blocker", "Actual host cancellation proof was incomplete; no stop capability granted")),
            "observation": observation, "log": descriptor,
            "fixture": {"path": str(retained_script), "sha256": hashlib.sha256(body.encode()).hexdigest()},
            "remote_cancellation_verified": False}
