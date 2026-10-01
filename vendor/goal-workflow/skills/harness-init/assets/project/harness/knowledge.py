"""Pinned native Serena adapter and committed-evidence checks.

Keep Serena's environment separate from the harness environment. Sources:
https://github.com/oraios/serena/tree/v1.7.0 (949a27ef1e5fda1a6e7b561e777bcece345c6ffd)
Native CLI signatures come from src/serena/cli.py; reference verdict text comes
from src/serena/memories/memory_reference_analysis.py. No inference from exit 0.
"""
from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import signal
import subprocess
import uuid

from .init_project import (InitRefused, inspect_shared_checkpoints, load_lock_backend,
                           repository_lock, repository_paths, require_local_linux)
from .state import Blocked


SERENA_VERSION = "1.7.0"
SERENA_SOURCE_COMMIT = "949a27ef1e5fda1a6e7b561e777bcece345c6ffd"
VERSION_OUTPUT = re.compile(r"Serena 1\.7\.0(?:-([0-9a-f]{8,40}))?\Z")
MEMORY_NAME = re.compile(r"[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*\Z")
CLEAN_REFERENCES = "✓ No referential integrity issues found."


def parse_reference_report(stdout, returncode=0):
    """1.7.0 explicitly returns exit 0 even for stale mem: references."""
    if returncode != 0:
        raise Blocked("Serena reference check execution failed")
    report = stdout.strip()
    stale = re.search(r"^Stale references \((\d+)\):", report, re.MULTILINE)
    if stale:
        raise Blocked(f"Serena found {stale.group(1)} stale memory references: {report}")
    if report != CLEAN_REFERENCES:
        raise Blocked("Unknown or non-clean native reference report; manual review required: " + report)
    return {"clean": True, "native_report": report}


def _safe_local_path(root, relative, *, required=True):
    parts = PurePosixPath(relative).parts
    if (not parts or relative.startswith("/") or "\\" in relative or ":" in relative
            or any(p in ("", ".", "..") for p in relative.split("/"))):
        raise Blocked("Evidence and memory paths must be normalized repository-relative paths")
    path = root
    for part in parts:
        path = path / part
        if path.is_symlink():
            raise Blocked("Symlink component refused: " + relative)
    if required and not path.is_file():
        raise Blocked("Required file missing: " + relative)
    return path


def verify_durable_evidence(repo, references, commit="HEAD", controller=None):
    """Return actual committed blobs for references; temporary/external-only fails.

    This validates accessibility and byte identity, not whether a cited source
    supports a knowledge claim. That is an independent semantic review.
    """
    root = Path(repo).resolve(strict=True)
    if not isinstance(references, (list, tuple)) or not references:
        raise Blocked("At least one committed, durable source reference is required")
    if not isinstance(commit, str) or not re.fullmatch(r"HEAD|[0-9a-f]{40}|[0-9a-f]{64}", commit):
        raise Blocked("Evidence revision must be HEAD or a full immutable commit ID")
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env["GIT_OPTIONAL_LOCKS"] = "0"

    def git(*args):
        if controller is not None:
            return controller.git(*args, cwd=root, raw=True)
        try:
            result = subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                                    timeout=15, env=env)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise Blocked("Unable to inspect durable evidence") from exc
        if result.returncode:
            raise Blocked("Evidence is not accessible in the selected committed revision")
        return result.stdout

    oid = git("rev-parse", "--verify", commit + "^{commit}").decode().strip()
    result = []
    for ref in references:
        if not isinstance(ref, str):
            raise Blocked("Evidence references must be repository-relative strings")
        path_part = ref.split("#", 1)[0]
        parts = PurePosixPath(path_part).parts
        if (path_part == ".loop-state.json" or parts[:2] == (".harness", "runs")
                or any(p in {".git", "tmp", ".tmp", "logs", "cache", ".cache"} for p in parts)):
            raise Blocked("Temporary or mutable run evidence cannot back long-term knowledge: " + ref)
        path = _safe_local_path(root, path_part)
        blob = git("show", oid + ":" + path_part)
        if path.read_bytes() != blob:
            raise Blocked("Working-tree evidence differs from the committed source: " + ref)
        if not blob:
            raise Blocked("Empty source cannot establish durable evidence: " + ref)
        result.append({"reference": ref, "commit": oid, "sha256": hashlib.sha256(blob).hexdigest()})
    return result


class SerenaAdapter:
    """Invoke only pinned native operations; no silent global-memory dependency.

    Native startup can create cache/config files, even for read commands. An
    explicit SERENA_HOME is therefore required. Mutations require a shared
    repository lock (or an already-entered controller from this harness).
    """
    def __init__(self, repo, executable, serena_home, *, timeout_seconds=30,
                 python_executable=None, controller=None):
        self.root, self.common = repository_paths(Path(repo))
        self.executable = str(Path(executable).absolute())
        self.python_executable = str(Path(python_executable).absolute()) if python_executable else None
        self.home = Path(serena_home).absolute()
        if type(timeout_seconds) not in (int, float) or not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise Blocked("Native Serena calls need a positive bounded timeout")
        self.timeout = timeout_seconds
        self.controller = controller
        self._version_checked = False

    def _call(self, argv, *, input_text=None):
        if self.controller is None and (self.root / ".harness/config.json").exists():
            raise Blocked("Managed project native calls require the supervised Controller; standalone calls are component probes only")
        env = os.environ.copy()
        # An inherited harness PYTHONPATH must not override Serena's pinned env.
        env.pop("PYTHONPATH", None)
        env["SERENA_HOME"] = str(self.home)
        if self.controller is not None:
            token = "serena-" + uuid.uuid4().hex
            log = self.controller.common / "harness-native" / (token + ".stdout")
            record = self.controller.execute(argv, self.root, token, log, timeout=self.timeout,
                                             env=env, input_text=input_text, separate_stderr=True)
            stdout = log.read_text()
            stderr = Path(record["stderr_log"]).read_text()
            if record["exit_code"] != 0 or record["reason"] or not record["stopped"]:
                raise Blocked("Controlled native Serena call failed: " + stderr.strip()[:2000])
            return stdout
        try:
            proc = subprocess.Popen(argv, cwd=self.root, env=env, text=True,
                                    stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, start_new_session=True)
        except OSError as exc:
            raise Blocked("Cannot start pinned Serena executable: " + str(exc)) from exc
        try:
            stdout, stderr = proc.communicate(input_text, timeout=self.timeout)
        except BaseException as exc:
            # Native CLI is synchronous: stop this owned process group on timeout/cancel.
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            try:
                proc.communicate(timeout=5)
            except subprocess.TimeoutExpired as cleanup_exc:
                raise Blocked("Native Serena stop could not be confirmed; reconcile before continuing") from cleanup_exc
            if isinstance(exc, subprocess.TimeoutExpired):
                raise Blocked("Native Serena call timed out and its owned process group was stopped") from exc
            raise
        if proc.returncode != 0:
            raise Blocked("Native Serena call failed: " + stderr.strip()[:2000])
        return stdout

    def probe_version(self):
        output = self._call([self.executable, "--version"]).strip()
        match = VERSION_OUTPUT.fullmatch(output)
        if not match or (match.group(1) and not SERENA_SOURCE_COMMIT.startswith(match.group(1))):
            raise Blocked("Expected Serena 1.7.0, found: " + output)
        self._version_checked = True
        return {"version_output": output, "required_version": SERENA_VERSION}

    def _native(self, *args, input_text=None):
        if not self._version_checked:
            self.probe_version()
        return self._call([self.executable, *args], input_text=input_text)

    def _project_file(self):
        return _safe_local_path(self.root, ".serena/project.yml")

    def _snapshots(self):
        _safe_local_path(self.root, ".serena", required=False)
        memories = self.root / ".serena/memories"
        result = {}
        config = _safe_local_path(self.root, ".serena/project.yml", required=False)
        if config.is_file():
            result[config] = config.read_bytes()
        if memories.is_symlink():
            raise Blocked("Symlink at .serena/memories refused")
        if memories.exists():
            for path in memories.rglob("*"):
                if path.is_symlink():
                    raise Blocked("Symlink in Serena memories refused")
                if path.is_file():
                    result[path] = path.read_bytes()
        return result

    @contextmanager
    def _mutation(self, expected_changes=None):
        require_local_linux(self.root, self.common)
        before = self._snapshots()
        if self.controller is not None:
            from .runtime import Controller
            controller = self.controller
            if (not isinstance(controller, Controller) or not controller.entered
                    or not controller.run_lock.is_locked
                    or Path(controller.common).resolve() != self.common):
                raise Blocked("Caller must hold this repository's actual controller lock")
            yield
        else:
            if os.path.lexists(self.root / ".loop-state.json"):
                raise Blocked("Existing checkpoint requires the recovery controller before knowledge mutations")
            backend, timeout_error = load_lock_backend()
            try:
                with repository_lock(self.common, backend, timeout_error):
                    if os.path.lexists(self.root / ".loop-state.json"):
                        raise Blocked("Checkpoint appeared during lock acquisition; recover first")
                    inspect_shared_checkpoints(self.root, self.common)
                    yield
            except InitRefused as exc:
                raise Blocked(str(exc)) from exc
        after = self._snapshots()
        for path, data in before.items():
            if expected_changes is not None and path in expected_changes:
                continue
            if path not in after or after[path] != data:
                raise Blocked("Native operation unexpectedly changed an existing memory: " + str(path))
        if expected_changes is not None:
            for path in set(before) | set(after) | set(expected_changes):
                expected = expected_changes.get(path, before.get(path))
                if after.get(path) != expected:
                    raise Blocked("Native mutation differs from the reviewed exact change: " + str(path))

    def create_project(self, languages):
        if not languages or not all(re.fullmatch(r"[a-z][a-z0-9_-]*", x) for x in languages):
            raise Blocked("Explicit native language-server names are required for project creation")
        with self._mutation():
            if os.path.lexists(self.root / ".serena/project.yml"):
                raise Blocked("Existing project.yml is preserved; register the existing project instead")
            args = ["project", "create", str(self.root)]
            for language in languages:
                args.extend(["--language", language])
            output = self._native(*args)
            self._project_file()
        return {"project_created": True, "registered": True, "onboarding_completed": False,
                "host_activated": False, "native_output": output}

    def _bridge(self, action, payload=None):
        if not self.python_executable:
            raise Blocked("Register/onboarding requires the Python executable from the pinned Serena environment")
        if not self._version_checked:
            self.probe_version()
        output = self._call([self.python_executable, str(Path(__file__).with_name("serena_bridge.py")),
                             action, str(self.root)],
                            input_text=json.dumps(payload) if payload is not None else None)
        try:
            return json.loads(output)
        except ValueError as exc:
            raise Blocked("Unexpected native Serena bridge output") from exc

    def register_existing(self):
        with self._mutation():
            self._project_file()
            result = self._bridge("register")
        if result.get("registered") is not True or Path(result.get("project_root", "")).resolve() != self.root:
            raise Blocked("Native registration did not confirm the requested project")
        return result

    def initialize_maintenance(self):
        with self._mutation():
            self._project_file()
            output = self._native("memories", "initialize", str(self.root))
        if "mem:global/" in output:
            raise Blocked("Global maintenance overrides project conventions; resolve explicitly for team portability")
        return {"maintenance_initialized": True, "onboarding_completed": False, "native_output": output}

    def onboarding_instructions(self):
        with self._mutation():
            self._project_file()
            result = self._bridge("onboarding")
        if result.get("maintenance_memory", "").startswith("global/"):
            raise Blocked("Global maintenance dependency requires explicit project review")
        return result

    def read_core(self):
        core = _safe_local_path(self.root, ".serena/memories/core.md")
        actual = core.read_text()
        if not actual.strip() or re.search(r"\bTODO\b|\[PLACEHOLDER\]", actual):
            raise Blocked("A substantive project core memory is required; maintenance/template only is insufficient")
        output = self._native("memories", "read", "core", str(self.root))
        if output.rstrip("\n") != actual.rstrip("\n"):
            raise Blocked("Native core read differs from project-local core memory")
        if re.search(r"mem:global/", output):
            raise Blocked("Core depends on personal global memories; team portability needs explicit resolution")
        return {"name": "core", "content": output, "sha256": hashlib.sha256(core.read_bytes()).hexdigest()}

    def check_references(self):
        return parse_reference_report(self._native("memories", "check", str(self.root)))

    def readiness(self, evidence):
        self._project_file()
        core = self.read_core()
        refs = self.check_references()
        durable = verify_durable_evidence(self.root, evidence, controller=self.controller)
        return {"structural_ready": True, "onboarding_completed": False,
                "semantic_review_required": True, "host_activation_required": True,
                "core": core, "references": refs, "durable_evidence": durable}

    def write_new_memory(self, name, content, evidence):
        if not MEMORY_NAME.fullmatch(name) or name == "global" or name.startswith("global/"):
            raise Blocked("Only normalized project-local native memory names are accepted")
        if not isinstance(content, str) or not content.strip():
            raise Blocked("Empty memory content refused")
        durable = verify_durable_evidence(self.root, evidence, controller=self.controller)
        with self._mutation():
            target = _safe_local_path(self.root, f".serena/memories/{name}.md", required=False)
            if os.path.lexists(target):
                raise Blocked("Existing memory preserved; use an explicitly reviewed native edit")
            self._project_file()
            output = self._native("memories", "write", name, str(self.root), input_text=content)
            if not target.is_file() or target.read_text() != content:
                raise Blocked("Native memory write was not verified")
        return {"memory": name, "native_output": output, "durable_evidence": durable,
                "semantic_review_required": True}


    def update_memory(self, name, content, evidence, expected_sha256):
        """Apply one explicitly reviewed native edit; never merge guessed knowledge.

        Preimage and unchanged neighbors are verified. Native read-only patterns
        are enforced through the pinned package's tool-context write boundary.
        Evidence accessibility is checked; semantic truth still needs review.
        """
        if not MEMORY_NAME.fullmatch(name) or name.startswith("global/"):
            raise Blocked("Only project-local memory edits are supported")
        if not isinstance(content, str) or not content.strip():
            raise Blocked("Empty replacement is not a reviewed knowledge edit")
        path = _safe_local_path(self.root, f".serena/memories/{name}.md")
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha256:
            raise Blocked("Memory changed since review; re-read instead of overwriting")
        with self._mutation({path: content.encode("utf-8")}):
            durable = verify_durable_evidence(self.root, evidence, controller=self.controller)
            result = self._bridge("update", {"name": name, "content": content,
                                            "expected_sha256": expected_sha256})
        return dict(result, durable_evidence=durable, semantic_review_required=True)

    def rename_memory(self, old_name, new_name, evidence, expected_sha256):
        """Rename via native reference propagation, preserving unrelated memory.

        Global or native read-only affected items require separate user work;
        this project-scoped adapter refuses them before any mutation.
        """
        for name in (old_name, new_name):
            if not MEMORY_NAME.fullmatch(name) or name.startswith("global/"):
                raise Blocked("Only project-local memory names are supported")
        if old_name == new_name:
            raise Blocked("Rename must change the memory name")
        payload = {"old_name": old_name, "new_name": new_name,
                   "expected_sha256": expected_sha256}
        # Planning is read-only. The native mutation rechecks the full preimage.
        planned = self._bridge("rename-plan", payload)
        expected = {}
        for name, content in planned["changes"].items():
            if not MEMORY_NAME.fullmatch(name) or name.startswith("global/"):
                raise Blocked("Native rename plan escaped project scope")
            path = _safe_local_path(self.root, f".serena/memories/{name}.md", required=False)
            expected[path] = content.encode("utf-8") if content is not None else None
        with self._mutation(expected):
            durable = verify_durable_evidence(self.root, evidence, controller=self.controller)
            result = self._bridge("rename", dict(payload, snapshot_sha256=planned["snapshot_sha256"]))
        return dict(result, durable_evidence=durable, semantic_review_required=True)
