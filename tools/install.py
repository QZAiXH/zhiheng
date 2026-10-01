#!/usr/bin/env python3
"""Install the zh skill suite with an explicit, reversible backup."""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import shutil
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote


SKILLS = ("zh", "zh-context", "zh-plan", "zh-implement", "zh-debug", "zh-review", "zh-finish")
LEGACY = "zhiheng"
AFFECTED = (*SKILLS, LEGACY)
DEFAULT_TARGET = Path("/root/.codex/skills")
DEFAULT_BACKUPS = Path("/root/.codex/skill-backups")
FINISHED = {"installed", "restored"}


class InstallError(Exception):
    pass


def _path(value: Path | str) -> Path:
    return Path(value).expanduser().absolute()


def _check_root(path: Path, label: str) -> None:
    if path.is_symlink() or (path.exists() and not path.is_dir()):
        raise InstallError(f"{label} must be a real directory: {path}")


def _check_entry(path: Path) -> None:
    if path.is_symlink() or (path.exists() and not path.is_dir()):
        raise InstallError(f"affected skill must be a real directory: {path}")


def _validate_source(source: Path) -> None:
    _check_root(source, "source")
    if not source.is_dir():
        raise InstallError(f"source directory does not exist: {source}")
    for name in SKILLS:
        directory = source / name
        _check_entry(directory)
        skill_file = directory / "SKILL.md"
        if not skill_file.is_file() or skill_file.is_symlink():
            raise InstallError(f"missing regular SKILL.md: {skill_file}")
        for required in (directory / "LICENSE", directory / "agents" / "openai.yaml"):
            if not required.is_file() or required.is_symlink():
                raise InstallError(f"missing regular skill resource: {required}")
            if not required.read_text(encoding="utf-8").strip():
                raise InstallError(f"empty skill resource: {required}")
        if not (directory / "agents" / "openai.yaml").read_text(encoding="utf-8").startswith("interface:\n"):
            raise InstallError(f"invalid skill interface metadata: {directory / 'agents' / 'openai.yaml'}")
        for root, dirs, files in os.walk(directory, followlinks=False):
            for child in (*dirs, *files):
                if (Path(root) / child).is_symlink():
                    raise InstallError(f"source skill contains a symlink: {Path(root) / child}")
        content = skill_file.read_text(encoding="utf-8")
        match = re.match(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", content, re.DOTALL)
        if not match:
            raise InstallError(f"invalid frontmatter in {skill_file}")
        names = re.findall(r"^name:\s*(.*?)\s*$", match.group(1), re.MULTILINE)
        if len(names) != 1 or names[0].strip("'\"") != name:
            raise InstallError(f"SKILL.md name must be {name}: {skill_file}")
        descriptions = re.findall(r"^description:\s*(.*?)\s*$", match.group(1), re.MULTILINE)
        if len(descriptions) != 1 or not descriptions[0].strip("'\" "):
            raise InstallError(f"SKILL.md needs a description: {skill_file}")
    task_script = source / "zh" / "scripts" / "task.py"
    if not task_script.is_file() or task_script.is_symlink():
        raise InstallError(f"missing regular task helper: {task_script}")
    try:
        ast.parse(task_script.read_text(encoding="utf-8"), filename=str(task_script))
    except SyntaxError as exc:
        raise InstallError(f"invalid task helper: {task_script}: {exc}") from exc
    # Relative Markdown links are the suite's runtime references. Check them in
    # the sibling layout actually used after installation.
    for name in SKILLS:
        for markdown in (source / name).rglob("*.md"):
            content = markdown.read_text(encoding="utf-8")
            for raw in re.findall(r"(?<!!)\[[^\]]*\]\(([^)]+)\)", content):
                link = unquote(raw.split("#", 1)[0].strip().split(" ", 1)[0])
                if not link or re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", link) or link.startswith("/"):
                    continue
                destination = (markdown.parent / link).resolve()
                if not destination.is_relative_to(source.resolve()) or not destination.is_file():
                    raise InstallError(f"unresolved local reference {raw!r} in {markdown}")


def _save_manifest(folder: Path, manifest: dict) -> None:
    temp = folder / "manifest.json.tmp"
    with temp.open("w", encoding="utf-8") as stream:
        json.dump(manifest, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    temp.replace(folder / "manifest.json")


def _load_manifest(folder: Path) -> dict:
    if folder.is_symlink() or not folder.is_dir():
        raise InstallError(f"backup directory missing or unsafe: {folder}")
    path = folder / "manifest.json"
    if path.is_symlink():
        raise InstallError(f"unsafe manifest: {path}")
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise InstallError(f"cannot read backup manifest: {path}") from exc
    if manifest.get("tool") != "zh-skill-installer" or manifest.get("version") != 1 or manifest.get("affected") != list(AFFECTED):
        raise InstallError(f"unsupported backup manifest: {path}")
    if not isinstance(manifest.get("original"), dict) or set(manifest["original"]) != set(AFFECTED):
        raise InstallError(f"invalid original entries in {path}")
    return manifest


def _check_incomplete(backups: Path, target: Path) -> None:
    if not backups.exists():
        return
    for folder in backups.iterdir():
        if not folder.is_dir() or folder.is_symlink():
            continue
        manifest_path = folder / "manifest.json"
        if not manifest_path.exists():
            continue
        try:
            marker = json.loads(manifest_path.read_text(encoding="utf-8")).get("tool")
        except (OSError, ValueError, AttributeError):
            continue  # A backup from another tool is not ours to interpret.
        if marker != "zh-skill-installer":
            continue
        manifest = _load_manifest(folder)
        if manifest.get("target") == str(target) and manifest.get("phase") not in FINISHED:
            raise InstallError(
                f"unfinished migration {folder.name} ({manifest['phase']}); "
                f"restore it before installing again"
            )


def _layout(source: Path, target: Path, backups: Path) -> None:
    for path, label in ((target, "target"), (backups, "backup root")):
        _check_root(path, label)
    resolved = (source.resolve(), target.resolve(), backups.resolve())
    if any(a == b or a.is_relative_to(b) or b.is_relative_to(a)
           for a, b in ((resolved[0], resolved[1]), (resolved[0], resolved[2]), (resolved[1], resolved[2]))):
        raise InstallError("source, target and backup root must be separate directories")
    for name in AFFECTED:
        _check_entry(target / name)


def install(source: Path | str, target: Path | str = DEFAULT_TARGET,
            backups: Path | str = DEFAULT_BACKUPS, dry_run: bool = False) -> dict:
    source, target, backups = map(_path, (source, target, backups))
    _validate_source(source)
    _layout(source, target, backups)
    _check_incomplete(backups, target)
    original = {name: (target / name).exists() for name in AFFECTED}
    preview = {"action": "install", "source": str(source), "target": str(target),
               "backup_root": str(backups), "replace": [name for name in SKILLS if original[name]],
               "retire": [LEGACY] if original[LEGACY] else [], "dry_run": dry_run}
    if dry_run:
        return preview

    backup_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:12]
    folder = backups / backup_id
    stage = target / f".zh-install-{backup_id}"
    manifest = {"tool": "zh-skill-installer", "version": 1, "affected": list(AFFECTED), "target": str(target),
                "source": str(source), "original": original, "phase": "backed_up",
                "installed": [], "legacy_retired": False, "restore_archives": []}
    try:
        backups.mkdir(parents=True, exist_ok=True)
        folder.mkdir()
        snapshot = folder / "original"
        snapshot.mkdir()
        for name in AFFECTED:
            if original[name]:
                shutil.copytree(target / name, snapshot / name, symlinks=True)
        _save_manifest(folder, manifest)

        target.mkdir(parents=True, exist_ok=True)
        (stage / "new").mkdir(parents=True)
        (stage / "removed").mkdir()
        for name in SKILLS:
            shutil.copytree(source / name, stage / "new" / name)
        _validate_source(stage / "new")
        manifest["phase"] = "installing"
        _save_manifest(folder, manifest)
        for name in SKILLS:
            current = target / name
            if current.exists():
                current.rename(stage / "removed" / name)
            (stage / "new" / name).rename(current)
            manifest["installed"].append(name)
            _save_manifest(folder, manifest)
        manifest["phase"] = "new_installed"
        _save_manifest(folder, manifest)
        _validate_source(target)
        if (target / LEGACY).exists():
            (target / LEGACY).rename(stage / "removed" / LEGACY)
        manifest["legacy_retired"] = True
        manifest["phase"] = "installed"
        _save_manifest(folder, manifest)
        shutil.rmtree(stage)
    except Exception as exc:
        if (folder / "manifest.json").exists():
            manifest["phase"] = "failed"
            manifest["error"] = str(exc)
            _save_manifest(folder, manifest)
            raise InstallError(f"installation interrupted; backup {folder}; restore with `restore {backup_id}`: {exc}") from exc
        # No installed file was touched before the first manifest was saved.
        if folder.exists():
            shutil.rmtree(folder)
        raise InstallError(f"backup could not be created; installed skills are unchanged: {exc}") from exc
    return {**preview, "dry_run": False, "backup_id": backup_id, "backup": str(folder)}


def restore(backup_id: str, backups: Path | str = DEFAULT_BACKUPS,
            target: Path | str | None = None, dry_run: bool = False) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", backup_id):
        raise InstallError("backup ID must be a simple directory name")
    backups = _path(backups)
    _check_root(backups, "backup root")
    folder = backups / backup_id
    manifest = _load_manifest(folder)
    saved_target = _path(manifest["target"])
    target = _path(target) if target is not None else saved_target
    if target != saved_target:
        raise InstallError(f"backup belongs to {saved_target}, not {target}")
    _check_root(target, "target")
    if manifest["phase"] == "restored":
        return {"action": "restore", "backup": str(folder), "target": str(target),
                "status": "already_restored", "dry_run": dry_run}
    snapshot = folder / "original"
    if snapshot.is_symlink() or not snapshot.is_dir():
        raise InstallError(f"missing original snapshot: {snapshot}")
    for name in AFFECTED:
        _check_entry(target / name)
        if manifest["original"][name]:
            entry = snapshot / name
            _check_entry(entry)
            if not entry.is_dir():
                raise InstallError(f"missing original skill in backup: {entry}")
    preview = {"action": "restore", "backup": str(folder), "target": str(target),
               "restore": [name for name in AFFECTED if manifest["original"][name]],
               "remove": [name for name in AFFECTED if not manifest["original"][name]],
               "preserve_current_under": str(folder / "restore-archives"), "dry_run": dry_run}
    if dry_run:
        return preview

    archive_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:12]
    archive = folder / "restore-archives" / archive_id
    try:
        archive.mkdir(parents=True)
        for name in AFFECTED:
            if (target / name).exists():
                shutil.copytree(target / name, archive / name, symlinks=True)
        install_stage = target / f".zh-install-{backup_id}"
        if install_stage.exists():
            _check_entry(install_stage)
            shutil.copytree(install_stage, archive / "install-stage", symlinks=True)
        manifest["restore_archives"].append(str(archive))
        manifest["phase"] = "restoring"
        manifest["restored"] = []
        _save_manifest(folder, manifest)
        for name in AFFECTED:
            current = target / name
            if current.exists():
                shutil.rmtree(current)
            if manifest["original"][name]:
                shutil.copytree(snapshot / name, current, symlinks=True)
            manifest["restored"].append(name)
            _save_manifest(folder, manifest)
        if install_stage.exists():
            shutil.rmtree(install_stage)
        manifest["phase"] = "restored"
        _save_manifest(folder, manifest)
    except Exception as exc:
        if (folder / "manifest.json").exists():
            manifest["phase"] = "failed_restore"
            manifest["error"] = str(exc)
            _save_manifest(folder, manifest)
        raise InstallError(f"restore interrupted; retry `restore {backup_id}`: {exc}") from exc
    return {**preview, "dry_run": False, "archive": str(archive)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    put = actions.add_parser("install", help="install seven skills and retire zhiheng")
    put.add_argument("--source", type=Path, default=Path(__file__).resolve().parent.parent)
    put.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    put.add_argument("--backups", type=Path, default=DEFAULT_BACKUPS)
    put.add_argument("--dry-run", action="store_true")
    undo = actions.add_parser("restore", help="restore an install backup")
    undo.add_argument("backup_id")
    undo.add_argument("--target", type=Path)
    undo.add_argument("--backups", type=Path, default=DEFAULT_BACKUPS)
    undo.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.action == "install":
            if (args.source / "zh/references/harness-integration.md").exists():
                raise InstallError("This source requires harness dependencies; use tools/install-harness.py --destination <project-or-home>. Legacy restore remains supported.")
            result = install(args.source, args.target, args.backups, args.dry_run)
        else:
            result = restore(args.backup_id, args.backups, args.target, args.dry_run)
    except InstallError as exc:
        parser.exit(2, f"install.py: {exc}\n")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
