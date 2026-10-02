"""Linux/local-FS serial controller primitives. No detached task is trusted."""
import os
import json
import math
import signal
import subprocess
import time
import tempfile
import hashlib
import uuid
from pathlib import Path
import psutil
from filelock import FileLock, Timeout
from .state import Blocked, State, atomic_json
from .init_project import require_local_linux, load_lock_backend, repository_lock, InitRefused


class GitFailure(Blocked):
    def __init__(self, message, record):
        super().__init__(message)
        self.returncode = record["exit_code"]
        self.reason = record["reason"]


class NativeRunLock:
    def __init__(self, common):
        self.common, self.context, self.is_locked = common, None, False

    def acquire(self):
        try:
            backend, timeout_error = load_lock_backend()
            self.context = repository_lock(self.common, backend, timeout_error)
            self.context.__enter__()
            self.is_locked = True
        except InitRefused as exc:
            raise Blocked(str(exc)) from exc
        return self

    def release(self):
        if self.is_locked:
            self.context.__exit__(None, None, None)
            self.is_locked = False

    def __enter__(self):
        return self.acquire()

    def __exit__(self, *exc):
        self.release()


def git(root, *args):
    p = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, timeout=30)
    if p.returncode:
        raise Blocked(p.stderr.strip() or "git failed")
    return p.stdout.strip()


def identity(proc):
    return {"pid": proc.pid, "created": proc.create_time()}


def owned(record):
    try:
        p = psutil.Process(record["pid"])
        return p if abs(p.create_time() - record["created"]) < 0.01 and p.status() != psutil.STATUS_ZOMBIE else None
    except psutil.NoSuchProcess:
        return None
    except (psutil.AccessDenied, KeyError) as exc:
        raise Blocked("cannot verify prior process ownership") from exc


class Controller:
    def __init__(self, root, mode, run_id, limits):
        self.root = Path(root).resolve()
        self.common = Path(git(root, "rev-parse", "--path-format=absolute", "--git-common-dir"))
        try:
            require_local_linux(self.root, self.common)
        except InitRefused as exc:
            raise Blocked(str(exc)) from exc
        self.run_lock = NativeRunLock(self.common)
        primary_line = git(root, "worktree", "list", "--porcelain").splitlines()[0]
        if not primary_line.startswith("worktree "):
            raise Blocked("cannot resolve primary repository worktree")
        self.state = State(Path(primary_line[9:]), mode, run_id, self.common / "harness.state.lock")
        self.journal = self.common / "harness.execution.json"
        self.limits = dict(limits)
        self.limits.setdefault("total_seconds", limits.get("task_seconds"))
        self.limits.setdefault("max_attempts", limits.get("task_attempts"))
        for name in ("command_seconds", "stop_grace_seconds", "total_seconds", "max_attempts"):
            value = self.limits.get(name)
            if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
                raise Blocked(f"positive finite limit required: {name}")
        self.entered = False

    def __enter__(self):
        if os.name != "posix":
            raise Blocked("process stop backend not validated for this OS")
        try:
            self.run_lock.acquire()
        except Timeout as exc:
            raise Blocked("repository already has an active controller") from exc
        self.entered = True
        try:
            if self.journal.is_symlink():
                raise Blocked("shared execution journal cannot be a symlink")
            if self.journal.exists():
                try:
                    prior = json.loads(self.journal.read_text())
                except (ValueError, OSError) as exc:
                    raise Blocked("shared execution journal damaged") from exc
                if not prior.get("stopped", False):
                    raise Blocked("shared prior execution requires stop reconciliation")
            data = self.state.read()
            active = data.get("active")
            if active:
                # Recovery never kills by PID alone or assumes an old lock means stopped.
                identities = active.get("processes", [])
                if active.get("host_handle") or active.get("remote_unknown"):
                    raise Blocked("reconcile outstanding host/remote execution before resuming")
                if any(owned(p) for p in identities):
                    raise Blocked("old execution still alive; operator must stop verified identities")
                if not active.get("stopped", False):
                    raise Blocked("previous execution stop unconfirmed; reconcile before resuming")
            return self
        except Exception:
            self.run_lock.release()
            self.entered = False
            raise

    def __exit__(self, *exc):
        self.entered = False
        self.run_lock.release()

    def git(self, *args, cwd=None, raw=False):
        """Execute all in-workflow Git work under the same identity/budget journal."""
        token = "git-" + uuid.uuid4().hex
        log = self.common / "harness-git" / (token + ".stdout")
        directory = Path(cwd) if cwd is not None else self.root
        record = self.execute(["git", "-C", str(directory), *args], directory, token, log,
                              separate_stderr=True)
        if record["exit_code"] != 0 or record["reason"]:
            raise GitFailure(Path(record["stderr_log"]).read_text().strip() or "controlled Git command failed", record)
        return log.read_bytes() if raw else log.read_text().strip()

    @classmethod
    def reconcile_stopped(cls, root, mode, run_id, limits):
        """Conservative recovery: prove every recorded identity stopped; never kill by stale PID."""
        obj = cls(root, mode, run_id, limits)
        with obj.run_lock:
            data = obj.state.read()
            journal = json.loads(obj.journal.read_text()) if obj.journal.exists() else None
            for active in (data.get("active"), journal):
                if not active:
                    continue
                if active.get("host_handle") or active.get("remote_unknown"):
                    raise Blocked("remote/host outcome requires native reconciliation")
                if not active.get("processes") and not active.get("stopped"):
                    raise Blocked("spawn identity missing; cannot prove old execution stopped")
                if any(owned(p) for p in active.get("processes", [])):
                    raise Blocked("prior owned execution still running; stop it before recovery")
                for record in active.get("processes", []):
                    for p in psutil.process_iter(["pid"]):
                        try:
                            if os.getsid(p.pid) == record["pid"] and p.status() != psutil.STATUS_ZOMBIE:
                                raise Blocked("prior process group still alive")
                        except (ProcessLookupError, psutil.NoSuchProcess):
                            pass
            if journal:
                journal["stopped"] = True
                atomic_json(obj.journal, journal)
            if data.get("active"):
                previous = data["active"]
                if not any(a["attempt_id"] == previous["attempt_id"] for a in data["attempts"]):
                    charged = max(previous.get("reserved_seconds", 0), time.time() - previous.get("started_at", time.time()))
                    data["spent_seconds"] += charged
                    data["attempts"].append({"attempt_id": previous["attempt_id"], "argv": previous.get("command"),
                                             "exit_code": None, "reason": "controller_interrupted", "stopped": True,
                                             "charged_seconds": charged,
                                             "elapsed_seconds": None})
                data["active"] = None
                data["recovery"] = "confirmed_recorded_execution_stopped; external Git/task facts still require reconciliation"
                obj.state.write(data, data["revision"])
            return {"execution_stopped": True, "external_reconciliation_required": True}

    def execute(self, argv, cwd, attempt_id, log_path, timeout=None, scope="command", env=None,
                input_text=None, separate_stderr=False):
        if not self.entered:
            raise Blocked("run lock not held")
        if not isinstance(argv, list) or not argv or not all(isinstance(x, str) for x in argv):
            raise Blocked("command must be an argv array")
        data = self.state.read()
        if scope not in ("command", "implementation", "review", "github"):
            raise Blocked("unknown bounded execution scope")
        cap = self.limits.get("request_seconds" if scope == "github" else scope + "_seconds", self.limits["command_seconds"])
        timeout = min(timeout or cap, cap,
                      self.limits["total_seconds"] - data["spent_seconds"])
        if timeout <= 0 or data.get("commands_started", len(data["attempts"])) >= self.limits["max_attempts"]:
            raise Blocked("budget_exhausted")
        log_path = Path(log_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        started = time.monotonic()
        proc = None
        reason = None
        tracked = {}
        with log_path.open("xb") as output:
            stdin_file = tempfile.TemporaryFile() if input_text is not None else None
            stderr_path = Path(str(log_path) + ".stderr") if separate_stderr else None
            stderr_file = stderr_path.open("xb") if stderr_path else None
            if stdin_file:
                stdin_file.write(input_text.encode("utf-8"))
                stdin_file.seek(0)
            # Save intent before spawn. A crash in the spawn/identity window blocks recovery.
            data["commands_started"] = data.get("commands_started", 0) + 1
            data["active"] = {"attempt_id": attempt_id, "processes": [], "stopped": False, "command": argv,
                              "started_at": time.time(), "reserved_seconds": timeout}
            data = self.state.write(data, data["revision"])
            atomic_json(self.journal, dict(data["active"], workspace=str(self.root)))
            try:
                proc = subprocess.Popen(argv, cwd=cwd, stdout=output,
                                        stderr=stderr_file if stderr_file else subprocess.STDOUT,
                                        stdin=stdin_file if stdin_file else subprocess.DEVNULL,
                                        env=env, start_new_session=True)
                root = psutil.Process(proc.pid)
                tracked[proc.pid] = identity(root)
                data["active"]["processes"] = list(tracked.values())
                data = self.state.write(data, data["revision"], attempt_id)
                atomic_json(self.journal, dict(data["active"], workspace=str(self.root)))
                while proc.poll() is None:
                    for child in root.children(recursive=True):
                        if child.pid not in tracked:
                            tracked[child.pid] = identity(child)
                            data["active"]["processes"] = list(tracked.values())
                            data = self.state.write(data, data["revision"], attempt_id)
                            atomic_json(self.journal, dict(data["active"], workspace=str(self.root)))
                    if time.monotonic() - started >= timeout:
                        reason = "timeout"
                        break
                    time.sleep(0.025)
            except (KeyboardInterrupt, SystemExit):
                reason = "cancelled"
            finally:
                # Stop same-group members and observed descendants; detached/remote work is unsupported.
                if proc is not None:
                    for candidate in psutil.process_iter(["pid", "create_time"]):
                        try:
                            if os.getsid(candidate.pid) == proc.pid:
                                tracked[candidate.pid] = identity(candidate)
                        except (ProcessLookupError, psutil.NoSuchProcess):
                            pass
                live = [p for r in tracked.values() if (p := owned(r)) is not None]
                if proc is not None and (proc.poll() is None or live):
                    try:
                        os.killpg(proc.pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                    for p in live:
                        try:
                            p.terminate()
                        except psutil.NoSuchProcess:
                            pass
                    children = [p for p in live if p.pid != proc.pid]
                    _, alive = psutil.wait_procs(children, timeout=self.limits["stop_grace_seconds"])
                    if proc.poll() is None:
                        try:
                            proc.wait(timeout=self.limits["stop_grace_seconds"])
                        except subprocess.TimeoutExpired:
                            alive.append(psutil.Process(proc.pid))
                    for p in alive:
                        if owned(tracked[p.pid]):
                            p.kill()
                    psutil.wait_procs([p for p in alive if p.pid != proc.pid], timeout=self.limits["stop_grace_seconds"])
                    proc.wait(timeout=self.limits["stop_grace_seconds"])
                stopped = not any(owned(r) for r in tracked.values())
                elapsed = time.monotonic() - started
                data["spent_seconds"] += elapsed
                code = proc.returncode if proc is not None else None
                result = {"attempt_id": attempt_id, "argv": argv, "exit_code": code,
                          "reason": reason, "stopped": stopped, "log": str(log_path),
                          "elapsed_seconds": elapsed, "charged_seconds": elapsed}
                if stderr_path:
                    result["stderr_log"] = str(stderr_path)
                if input_text is not None:
                    result["input_sha256"] = hashlib.sha256(input_text.encode("utf-8")).hexdigest()
                data["attempts"].append(result)
                data["active"]["stopped"] = stopped
                data["active"]["processes"] = list(tracked.values())
                atomic_json(self.journal, dict(data["active"], workspace=str(self.root)))
                data = self.state.write(data, data["revision"], attempt_id)
                if stopped:
                    data["active"] = None
                    self.state.write(data, data["revision"])
                if not stopped:
                    raise Blocked("execution stop unconfirmed")
                if stdin_file:
                    stdin_file.close()
                if stderr_file:
                    stderr_file.close()
        return result
