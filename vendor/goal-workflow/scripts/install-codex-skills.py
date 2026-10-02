#!/usr/bin/env python3
"""Install local Codex CLI skills, or upgrade/roll back hash-verified copies.

Only <destination>/.agents is changed. No project code, documents, checkpoints,
credentials, package installation, or skill code execution is performed.
Existing conflicting names and edited managed files are never overwritten.
Interrupted transactions fail closed and retain their staged/backup evidence.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import uuid


CHAIN = ("harness-init", "prd", "prd-to-spec", "to-design", "to-issues", "loop-it",
         "review-it", "note-it", "walkthrough", "ship-it")
EXCLUDE = {".git", ".venv", "__pycache__", ".pytest_cache", ".mypy_cache", ".DS_Store"}
MANIFEST = ".goal-workflow-install.json"
JOURNAL = ".goal-workflow-transaction.json"
BACKUPS = ".goal-workflow-backups"
NAME = re.compile(r"[a-z][a-z0-9-]*\Z")


class InstallBlocked(RuntimeError):
    pass


def safe_path(root, relative):
    if not isinstance(relative, str) or relative.startswith("/") or "\\" in relative:
        raise InstallBlocked("Unsafe manifest path")
    parts = relative.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise InstallBlocked("Unsafe manifest path")
    path = root
    for part in parts:
        path = path / part
        if path.is_symlink():
            raise InstallBlocked("Symlink refused: " + str(path))
    return path


def read_json(path):
    if path.is_symlink() or not path.is_file():
        raise InstallBlocked("Missing or unsafe installation metadata: " + str(path))
    try:
        return json.loads(path.read_text())
    except (ValueError, OSError) as exc:
        raise InstallBlocked("Damaged installation metadata; manual recovery required") from exc


def write_json_new(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def tree_files(root, names, *, packaged=False, installed=False):
    files = {}
    for name in names:
        if not NAME.fullmatch(name):
            raise InstallBlocked("Invalid skill name: " + name)
        directory = safe_path(root, name)
        if not directory.is_dir():
            raise InstallBlocked("Skill directory missing: " + name)
        if not safe_path(directory, "SKILL.md").is_file():
            raise InstallBlocked("Skill has no SKILL.md: " + name)
        for base, dirs, filenames in os.walk(directory, followlinks=False):
            base = Path(base)
            if packaged:
                dirs[:] = [item for item in dirs if item not in EXCLUDE or (base / item).is_symlink()]
            if installed:
                # These are produced by running the installed Python package.
                # Do not ignore arbitrary .venv directories or unknown user files.
                dirs[:] = [item for item in dirs if not (
                    not (base / item).is_symlink() and (
                        (base / item).relative_to(root).as_posix() == "harness-init/assets/project/.venv"
                        or item in {"__pycache__", ".pytest_cache", ".mypy_cache"}
                    ))]
            for item in dirs + filenames:
                path = base / item
                if path.is_symlink():
                    raise InstallBlocked("Symlink in skill package refused: " + str(path))
            for filename in filenames:
                if packaged and (filename in EXCLUDE or filename.endswith((".pyc", ".pyo"))):
                    continue
                path = base / filename
                if not path.is_file():
                    raise InstallBlocked("Non-regular skill asset refused: " + str(path))
                relative = path.relative_to(root).as_posix()
                mode = 0o755 if path.stat().st_mode & 0o111 else 0o644
                files[relative] = {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "mode": mode}
    return files


def verify_manifest(value):
    if (not isinstance(value, dict) or type(value.get("schema_version")) is not int or value.get("schema_version") != 1
            or not isinstance(value.get("skills"), list) or not value["skills"]
            or not all(isinstance(n, str) and NAME.fullmatch(n) for n in value["skills"])
            or len(value["skills"]) != len(set(value["skills"]))
            or not isinstance(value.get("files"), dict) or not value["files"]
            or not isinstance(value.get("generation"), str)
            or not re.fullmatch(r"[0-9a-f]{32}", value["generation"])):
        raise InstallBlocked("Invalid installation manifest")
    previous = value.get("previous_backup")
    if previous is not None and (not isinstance(previous, str) or not re.fullmatch(r"[0-9a-f]{32}", previous)):
        raise InstallBlocked("Invalid previous-backup identifier")
    for relative, record in value["files"].items():
        safe_path(Path("/"), relative)
        if relative.split("/", 1)[0] not in value["skills"]:
            raise InstallBlocked("Manifest file outside managed skills")
        if (not isinstance(record, dict) or not isinstance(record.get("sha256"), str)
                or not re.fullmatch(r"[0-9a-f]{64}", record["sha256"])
                or record.get("mode") not in (0o644, 0o755)):
            raise InstallBlocked("Invalid manifest file fingerprint")
    if any(name + "/SKILL.md" not in value["files"] for name in value["skills"]):
        raise InstallBlocked("Manifest is missing a managed SKILL.md")
    return value


def assert_managed_unchanged(skills_dir, manifest):
    expected = verify_manifest(manifest)
    actual = tree_files(skills_dir, expected["skills"], installed=True)
    if actual != expected["files"]:
        raise InstallBlocked("Managed skills contain user changes, additions, or deletions; preserve and review them before upgrading")


def copy_manifest_files(source, destination, files):
    for relative, record in files.items():
        src = safe_path(source, relative)
        data = src.read_bytes()
        if hashlib.sha256(data).hexdigest() != record["sha256"]:
            raise InstallBlocked("Source changed during installation: " + relative)
        target = safe_path(destination, relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(data)
        target.chmod(record["mode"])


@contextmanager
def install_lock(agents):
    if sys.platform not in {"linux", "darwin"}:
        raise InstallBlocked("Installer locking requires macOS or Linux/WSL; native Windows is unsupported")
    import fcntl
    path = safe_path(agents, ".goal-workflow-install.lock")
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise InstallBlocked("Unsafe installer lock")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise InstallBlocked("Another skill installation is active") from exc
        yield
    finally:
        os.close(fd)


def install(destination, source, action="install", skills=None):
    if action not in {"install", "upgrade", "rollback"}:
        raise InstallBlocked("Unknown installation action")
    if sys.platform not in {"linux", "darwin"}:
        raise InstallBlocked("Installer locking requires macOS or Linux/WSL; native Windows is unsupported")
    destination = Path(destination).resolve(strict=True)
    source = Path(source).resolve(strict=action != "rollback")
    if not destination.is_dir():
        raise InstallBlocked("Destination must be an existing repository/workspace root")
    if os.path.lexists(destination / ".loop-state.json"):
        raise InstallBlocked("Existing workflow checkpoint requires stop/recovery review before skill changes")
    agents = safe_path(destination, ".agents")
    agents.mkdir(exist_ok=True)
    skills_dir = safe_path(agents, "skills")
    skills_dir.mkdir(exist_ok=True)
    with install_lock(agents):
        manifest_path = safe_path(agents, MANIFEST)
        journal_path = safe_path(agents, JOURNAL)
        if journal_path.exists():
            raise InstallBlocked("An interrupted skill transaction exists; preserve its staging/backups and reconcile before retrying")
        old = verify_manifest(read_json(manifest_path)) if manifest_path.exists() else None
        if action == "install" and old is not None:
            raise InstallBlocked("Managed installation already exists; use upgrade after reviewing changes")
        if action != "install" and old is None:
            raise InstallBlocked("No managed installation to " + action)
        if old:
            assert_managed_unchanged(skills_dir, old)
        if action == "rollback":
            backup_id = old.get("previous_backup")
            if not isinstance(backup_id, str) or not re.fullmatch(r"[0-9a-f]{32}", backup_id):
                raise InstallBlocked("No recorded previous version is available for rollback")
            backup = safe_path(agents, BACKUPS + "/" + backup_id)
            new = verify_manifest(read_json(backup / "manifest.json"))
            source_skills = safe_path(backup, "skills")
            assert_managed_unchanged(source_skills, new)
            if new["skills"] != old["skills"]:
                raise InstallBlocked("Rollback skill set mismatch")
        else:
            names = list(old["skills"] if old and skills is None else (skills or CHAIN))
            if not names or not all(isinstance(n, str) and NAME.fullmatch(n) for n in names) or len(names) != len(set(names)):
                raise InstallBlocked("Skill selection must contain unique valid names")
            if old and names != old["skills"]:
                raise InstallBlocked("Upgrade cannot silently add/remove managed skill names")
            source_skills = safe_path(source, "skills")
            files = tree_files(source_skills, names, packaged=True)
            new = {"schema_version": 1, "generation": uuid.uuid4().hex,
                   "skills": names, "files": files, "previous_backup": None}
        verify_manifest(new)
        for name in new["skills"]:
            target = safe_path(skills_dir, name)
            if old is None and target.exists():
                raise InstallBlocked("Existing same-name skill is preserved: " + name)
        transaction = uuid.uuid4().hex
        stage = safe_path(agents, ".goal-workflow-stage-" + transaction)
        stage.mkdir()
        copy_manifest_files(source_skills, stage, new["files"])
        if tree_files(stage, new["skills"]) != new["files"]:
            raise InstallBlocked("Staged package failed byte verification")
        backup = None
        if old:
            # Save and verify a restorable previous version before replacing any skill.
            backup = safe_path(agents, BACKUPS + "/" + transaction)
            backup.mkdir(parents=True)
            copy_manifest_files(skills_dir, backup / "skills", old["files"])
            write_json_new(backup / "manifest.json", old)
            assert_managed_unchanged(backup / "skills", old)
            if action == "upgrade":
                new["previous_backup"] = transaction
            assert_managed_unchanged(skills_dir, old)
            if read_json(manifest_path) != old:
                raise InstallBlocked("Installation manifest changed during staging")
        write_json_new(journal_path, {"action": action, "transaction": transaction,
                                     "stage": stage.name, "backup": str(backup.relative_to(agents)) if backup else None,
                                     "old_manifest": old, "new_manifest": new})
        retired = stage / ".retired"
        retired.mkdir()
        moved_old = []
        moved_new = []
        moved_runtime = []
        try:
            for name in new["skills"]:
                target = safe_path(skills_dir, name)
                if old:
                    os.rename(target, retired / name)
                    moved_old.append(name)
                elif target.exists():
                    raise InstallBlocked("A skill appeared during installation; refusing conflict")
                os.rename(stage / name, target)
                moved_new.append(name)
            runtime_relative = "harness-init/assets/project/.venv"
            if old and "harness-init" in new["skills"]:
                previous_runtime = safe_path(retired, runtime_relative)
                if previous_runtime.exists():
                    current_runtime = safe_path(skills_dir, runtime_relative)
                    if current_runtime.exists():
                        raise InstallBlocked("New package unexpectedly contains a runtime environment")
                    os.rename(previous_runtime, current_runtime)
                    moved_runtime.append((previous_runtime, current_runtime))
            manifest_temp = stage / "new-manifest.json"
            write_json_new(manifest_temp, new)
            os.replace(manifest_temp, manifest_path)
        except BaseException:
            # Do not erase user data: move our new copies back and restore old directories.
            for previous_runtime, current_runtime in reversed(moved_runtime):
                os.rename(current_runtime, previous_runtime)
            for name in reversed(moved_new):
                os.rename(skills_dir / name, stage / name)
            for name in reversed(moved_old):
                os.rename(retired / name, skills_dir / name)
            # The journal remains so a later invocation must reconcile the failed attempt.
            raise
        assert_managed_unchanged(skills_dir, new)
        journal_path.unlink()
        shutil.rmtree(stage)
        return {"status": {"install": "installed", "upgrade": "upgraded", "rollback": "rolled_back"}[action],
                "skills": new["skills"], "destination": str(skills_dir),
                "generation": new["generation"], "manifest": str(manifest_path),
                "backup": str(backup) if backup else None,
                "notice": "Files installed for Codex CLI discovery; no skill code was executed and runtime readiness is not established"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", required=True, type=Path, help="Explicit repository/workspace root")
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--action", choices=("install", "upgrade", "rollback"), default="install")
    parser.add_argument("--skills", help="Comma-separated skill names, or all for the enhanced chain")
    args = parser.parse_args(argv)
    names = None if args.skills in (None, "all") else args.skills.split(",")
    try:
        result = install(args.destination, args.source, args.action, names)
    except (InstallBlocked, OSError, ValueError) as exc:
        print(json.dumps({"status": "blocked", "reason": str(exc)}, indent=2))
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
