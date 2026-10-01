"""One checkpoint writer, with CAS and immutable attempt history."""
import copy
import json
import os
import tempfile
import hashlib
import time
import math
from pathlib import Path
from filelock import FileLock


class Blocked(RuntimeError):
    pass


def strict_json(raw):
    def pairs(rows):
        result = {}
        for key, value in rows:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result
    def constant(value):
        raise ValueError("nonfinite JSON constant")
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)


def atomic_json(path, data):
    path = Path(path)
    if path.is_symlink():
        raise Blocked(f"refuse symlink: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
        dfd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    finally:
        if os.path.exists(name):
            os.unlink(name)


class State:
    """Caller must hold the common-Git-dir run lock for this entire lifetime."""
    def __init__(self, root, mode, run_id, lock_path):
        self.path = Path(root) / ".loop-state.json"
        self.mode, self.run_id = mode, run_id
        self.lock = FileLock(str(lock_path), timeout=0)

    def read(self):
        if not self.path.exists():
            return {"schema_version": 2, "revision": 0, "mode": self.mode,
                    "run_id": self.run_id, "spent_seconds": 0.0, "attempts": [],
                    "commands_started": 0, "active": None, "remote_operations": [], "tasks": {}}
        try:
            data = strict_json(self.path.read_text())
        except (ValueError, OSError) as exc:
            raise Blocked("checkpoint damaged; preserve file and reconcile facts") from exc
        if data.get("schema_version") != 2:
            raise Blocked("checkpoint migration required; back up before migration")
        if (type(data.get("revision")) is not int or data["revision"] < 0
                or type(data.get("spent_seconds")) not in (int, float) or not math.isfinite(data["spent_seconds"])
                or data["spent_seconds"] < 0 or not isinstance(data.get("attempts"), list)
                or not isinstance(data.get("tasks"), dict) or not isinstance(data.get("remote_operations"), list)
                or type(data.get("commands_started", 0)) is not int or data.get("commands_started", 0) < 0):
            raise Blocked("checkpoint structure damaged; preserve and reconcile")
        if data.get("mode") != self.mode or data.get("run_id") != self.run_id:
            raise Blocked("checkpoint mode/run mismatch; do not reset consumed budget")
        return data

    def write(self, data, expected_revision, attempt_id=None):
        lock_path = Path(self.lock.lock_file)
        if lock_path.is_symlink() or (lock_path.exists() and (not lock_path.is_file() or lock_path.stat().st_size)):
            raise Blocked("unsafe state lock path")
        with self.lock:
            old = self.read()
            if old["revision"] != expected_revision:
                raise Blocked("stale checkpoint revision")
            if attempt_id is not None and (old.get("active") or {}).get("attempt_id") != attempt_id:
                raise Blocked("late result from inactive attempt")
            if data.get("run_id") != old["run_id"] or data.get("mode") != old["mode"]:
                raise Blocked("state identity change rejected")
            if data.get("spent_seconds", -1) < old["spent_seconds"]:
                raise Blocked("budget cannot decrease")
            if data.get("commands_started", 0) < old.get("commands_started", 0):
                raise Blocked("started command budget cannot decrease")
            if data.get("attempts", [])[:len(old["attempts"])] != old["attempts"]:
                raise Blocked("attempt history cannot be rewritten")
            new = copy.deepcopy(data)
            new["revision"] = expected_revision + 1
            atomic_json(self.path, new)
            return new


def migrate_legacy(root, mode, run_id, limits, authorized=False):
    """Backup version-1 progress; never infer shipped means delivered or reset unknown budget."""
    from .runtime import Controller, owned
    if not authorized:
        raise Blocked("checkpoint migration requires explicit authorization")
    controller = Controller(root, mode, run_id, limits)
    with controller.run_lock:
        if controller.journal.exists():
            journal = json.loads(controller.journal.read_text())
            if not journal.get("stopped") or any(owned(p) for p in journal.get("processes", [])):
                raise Blocked("prior execution must be reconciled before migration")
        path = controller.state.path
        raw = path.read_bytes()
        try:
            old = json.loads(raw)
        except (ValueError, UnicodeError) as exc:
            raise Blocked("damaged checkpoint preserved; cannot infer missing legacy progress") from exc
        if old.get("schema_version") == 2:
            raise Blocked("already version 2; use normal recovery")
        if old.get("version") != 1 or not isinstance(old.get("issues"), dict):
            raise Blocked("unsupported legacy schema preserved")
        backup = path.with_name(path.name + ".v1-backup-" + str(time.time_ns()))
        with backup.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        migrated = {"schema_version": 2, "revision": 1, "mode": mode, "run_id": run_id,
                    "spent_seconds": controller.limits["total_seconds"], "commands_started": 0,
                    "active": None, "attempts": [], "remote_operations": [], "tasks": {},
                    "legacy": {"backup": str(backup), "sha256": hashlib.sha256(raw).hexdigest(),
                               "issues": old["issues"], "unresolved": "reconcile actual delivery and explicitly amend unknown historical budget"}}
        atomic_json(path, migrated)
        return {"status": "blocked", "migrated": True, "backup": str(backup),
                "reason": migrated["legacy"]["unresolved"]}
