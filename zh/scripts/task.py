#!/usr/bin/env python3
"""Small, conservative Git task lifecycle helper for the zh skills.

This program checks Git and evidence *identity*. It cannot perform a semantic
review or decide whether the user authorized a change.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone


class TaskError(Exception):
    pass


def git(repo: Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True
    )
    if check and result.returncode:
        raise TaskError(f"git {' '.join(args)}: {result.stderr.strip() or result.stdout.strip()}")
    return result.stdout.strip()


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def common_dir(repo: Path) -> Path:
    value = Path(git(repo, "rev-parse", "--git-common-dir"))
    return (value if value.is_absolute() else repo / value).resolve()


def task_dir(repo: Path, task_id: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}", task_id):
        raise TaskError("task id must contain only letters, numbers, dot, underscore or dash")
    return common_dir(repo) / "zh" / "tasks" / task_id


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".tmp-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def save(repo: Path, state: dict) -> None:
    directory = task_dir(repo, state["id"])
    atomic_write(directory / "state.json", json.dumps(state, ensure_ascii=False, indent=2) + "\n")
    note = directory / "task.md"
    begin, end = "<!-- zh-state-begin -->", "<!-- zh-state-end -->"
    summary = (
        f"{begin}\n"
        f"- Status: {state['phase']}\n"
        f"- Target: `{state['target']}` at `{state.get('target_sha', 'unknown')}`\n"
        f"- Task branch: `{state['branch']}` at `{state.get('candidate_sha', 'unknown')}`\n"
        f"- Worktree: `{state['worktree']}`\n"
        f"- Updated: {state['updated_at']}\n"
        f"{end}"
    )
    if note.exists():
        content = note.read_text(encoding="utf-8")
        if begin in content and end in content:
            content = content[: content.index(begin)] + summary + content[content.index(end) + len(end) :]
        else:
            content += "\n\n" + summary + "\n"
    else:
        content = (
            f"# Task {state['id']}\n\n"
            "## Goal and scope\n\n"
            "## Authorization and decisions\n\n"
            "## Acceptance criteria\n\n"
            "## Evidence and results\n\n"
            "## Open issues and next step\n\n"
            + summary + "\n"
        )
    atomic_write(note, content)


def load(repo: Path, task_id: str) -> dict:
    path = task_dir(repo, task_id) / "state.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise TaskError(f"task {task_id} is not registered") from error
    if data.get("id") != task_id:
        raise TaskError("task record id does not match its directory")
    return data


def worktrees(repo: Path) -> list[dict]:
    blocks = git(repo, "worktree", "list", "--porcelain").split("\n\n")
    result = []
    for block in blocks:
        item = {}
        for line in block.splitlines():
            key, _, value = line.partition(" ")
            item[key] = value
        if item.get("worktree"):
            result.append(item)
    return result


def checked_out(repo: Path, branch: str) -> Path:
    matches = [Path(item["worktree"]).resolve() for item in worktrees(repo)
               if item.get("branch") == f"refs/heads/{branch}"]
    if len(matches) != 1:
        raise TaskError(f"branch {branch} must be checked out in exactly one worktree")
    return matches[0]


def commit(repo: Path, ref: str = "HEAD") -> str:
    return git(repo, "rev-parse", "--verify", f"{ref}^{{commit}}")


def dirty(repo: Path, *, ignored: bool = False) -> str:
    args = ["status", "--porcelain=v1", "--untracked-files=all"]
    if ignored:
        args.append("--ignored=matching")
    return git(repo, *args)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def archive_evidence(repo: Path, task_id: str, source: Path, digest: str) -> Path:
    archive = task_dir(repo, task_id) / "review-evidence" / f"{digest}{source.suffix}"
    archive.parent.mkdir(parents=True, exist_ok=True)
    if archive.exists():
        if sha256(archive) != digest:
            raise TaskError("archived review evidence hash mismatch")
        return archive
    fd, name = tempfile.mkstemp(prefix=".tmp-", dir=archive.parent)
    try:
        with source.open("rb") as input_file, os.fdopen(fd, "wb") as output_file:
            shutil.copyfileobj(input_file, output_file)
            output_file.flush()
            os.fsync(output_file.fileno())
        if sha256(Path(name)) != digest:
            raise TaskError("review evidence changed while copying")
        os.replace(name, archive)
    finally:
        if os.path.exists(name):
            os.unlink(name)
    return archive


def ensure_branch(repo: Path, worktree: Path, branch: str) -> None:
    actual = checked_out(repo, branch)
    if actual != worktree:
        raise TaskError(f"branch {branch} is checked out at {actual}, not {worktree}")


def register(args: argparse.Namespace, *, adopt: bool) -> dict:
    repo = args.repo.resolve()
    directory = task_dir(repo, args.id)
    if directory.exists():
        raise TaskError(f"task {args.id} is already registered")
    if args.target == args.branch:
        raise TaskError("task branch must differ from target branch")
    target_worktree = checked_out(repo, args.target)
    target_sha = commit(target_worktree)
    path = (args.worktree or repo.parent / f"{repo.name}-{args.id}").resolve()
    if adopt:
        ensure_branch(repo, path, args.branch)
        candidate_sha = commit(path)
    else:
        if path.exists():
            raise TaskError(f"worktree path already exists: {path}")
        if git(repo, "branch", "--list", args.branch):
            raise TaskError(f"branch already exists: {args.branch}")
        candidate_sha = target_sha
        if not args.dry_run:
            git(repo, "worktree", "add", "-b", args.branch, str(path), args.target)
            candidate_sha = commit(path)
    state = {
        "id": args.id, "target": args.target, "target_worktree": str(target_worktree),
        "branch": args.branch, "worktree": str(path), "phase": "active",
        "created_at": now(), "updated_at": now(), "target_sha": target_sha,
        "candidate_sha": candidate_sha, "review": None, "check": None,
    }
    if not args.dry_run:
        save(repo, state)
    return state


def inspect(repo: Path, state: dict) -> dict:
    output = dict(state)
    for key, branch, path_key in (
        ("actual_target", state["target"], "target_worktree"),
        ("actual_candidate", state["branch"], "worktree"),
    ):
        path = Path(state[path_key])
        try:
            ensure_branch(repo, path, branch)
            output[key] = commit(path)
            output[key + "_status"] = dirty(path, ignored=True)
        except TaskError as error:
            output[key] = None
            output[key + "_error"] = str(error)
    return output


def review(args: argparse.Namespace) -> dict:
    repo = args.repo.resolve()
    state = load(repo, args.id)
    if state["phase"] not in ("active", "reviewed", "review_failed"):
        raise TaskError("review cannot be replaced after merge")
    worktree = Path(state["worktree"])
    target = Path(state["target_worktree"])
    ensure_branch(repo, worktree, state["branch"])
    ensure_branch(repo, target, state["target"])
    if dirty(worktree):
        raise TaskError("commit or remove task worktree changes before binding review")
    evidence = args.evidence.resolve()
    if not evidence.is_file():
        raise TaskError("review evidence must be an existing regular file")
    digest = sha256(evidence)
    archive = (task_dir(repo, args.id) / "review-evidence" /
               f"{digest}{evidence.suffix}")
    if not args.dry_run:
        archive = archive_evidence(repo, args.id, evidence, digest)
    entry = {
        "result": args.result, "candidate": commit(worktree),
        "target": commit(target), "evidence": str(archive),
        "source_evidence": str(evidence), "evidence_sha256": digest, "recorded_at": now(),
    }
    state.update(
        review=entry, candidate_sha=entry["candidate"], target_sha=entry["target"],
        phase="reviewed" if args.result == "pass" else "review_failed", updated_at=now(),
        check=None,
    )
    if not args.dry_run:
        save(repo, state)
    return state


def require_review(state: dict) -> dict:
    review_data = state.get("review")
    if not review_data or review_data.get("result") != "pass":
        raise TaskError("a passing independent review record is required")
    evidence = Path(review_data["evidence"])
    if not evidence.is_file() or sha256(evidence) != review_data["evidence_sha256"]:
        raise TaskError("review evidence is missing or changed")
    return review_data


def finish(args: argparse.Namespace) -> dict:
    repo = args.repo.resolve()
    state = load(repo, args.id)
    if state["phase"] == "done":
        return state
    review_data = require_review(state)
    target = Path(state["target_worktree"])
    source = Path(state["worktree"])
    ensure_branch(repo, target, state["target"])
    target_head = commit(target)
    candidate = review_data["candidate"]
    if state["phase"] == "cleanup_intent" and target_head == candidate:
        registered = any(Path(item["worktree"]).resolve() == source
                         for item in worktrees(repo))
        if source.exists() or registered:
            # A previous removal may have failed. Continue through the normal
            # clean-worktree guard below, then retry removal.
            pass
        elif commit(repo, state["branch"]) == candidate:
            if args.dry_run:
                return {**state, "would_recover": "done"}
            state["phase"] = "done"
            state["updated_at"] = now()
            save(repo, state)
            return state
        else:
            raise TaskError("task branch changed during cleanup; inspect it manually")
    if target_head != candidate:
        ensure_branch(repo, source, state["branch"])
        if commit(source) != candidate:
            raise TaskError("candidate changed after review; review the current commit")
        if dirty(source):
            raise TaskError("task worktree has uncommitted or untracked changes")
        if target_head != review_data["target"]:
            raise TaskError("target changed after review; integrate it and review again")
        if dirty(target):
            raise TaskError("target worktree is dirty; preserve its contents and retry later")
        ancestor = subprocess.run(
            ["git", "-C", str(repo), "merge-base", "--is-ancestor", target_head, candidate],
            capture_output=True,
        )
        if ancestor.returncode != 0:
            raise TaskError("candidate cannot fast-forward target; integrate target and review again")
        if args.dry_run:
            return {**state, "would_merge": candidate, "would_check": args.check,
                    "would_cleanup": str(source)}
        state["phase"] = "merge_intent"
        state["updated_at"] = now()
        save(repo, state)
        git(target, "merge", "--no-overwrite-ignore", "--ff-only", candidate)
        if commit(target) != candidate:
            raise TaskError("target did not reach reviewed candidate")
        state["phase"] = "merged"
        state["updated_at"] = now()
        save(repo, state)
    else:
        if state["phase"] not in ("merge_intent", "merged", "check_failed", "check_invalid",
                                  "checked", "cleanup_blocked", "cleanup_intent"):
            raise TaskError("target equals candidate without a recorded merge intent")
        if state["phase"] == "merge_intent":
            if args.dry_run:
                return {**state, "would_recover": "merged"}
            state["phase"] = "merged"
            state["updated_at"] = now()
            save(repo, state)
    if commit(target) != candidate or dirty(target):
        raise TaskError("target changed or became dirty after merge; preserve it and reassess checks")
    valid_check = state.get("check") or {}
    check_log = Path(valid_check.get("log", "/nonexistent"))
    reusable = (state["phase"] in ("checked", "cleanup_blocked", "cleanup_intent")
                and valid_check.get("exit_code") == 0 and valid_check.get("target") == candidate
                and check_log.is_file() and sha256(check_log) == valid_check.get("log_sha256"))
    if not reusable:
        if not args.check:
            raise TaskError("an actual post-merge --check command is required")
        if args.dry_run:
            return {**state, "would_check": args.check, "would_cleanup": str(source)}
        result = subprocess.run(args.check, cwd=target, shell=True, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        checks_dir = task_dir(repo, args.id) / "checks"
        checks_dir.mkdir(parents=True, exist_ok=True)
        log = checks_dir / f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}.log"
        atomic_write(log, result.stdout)
        state["check"] = {
            "command": args.check, "target": candidate, "exit_code": result.returncode,
            "log": str(log), "log_sha256": sha256(log), "ran_at": now(),
        }
        target_valid = commit(target) == candidate and not dirty(target)
        state["phase"] = ("checked" if result.returncode == 0 and target_valid else
                          "check_failed" if result.returncode else "check_invalid")
        state["updated_at"] = now()
        save(repo, state)
        if result.returncode:
            raise TaskError(f"integration check failed ({result.returncode}); see {log}")
        if not target_valid:
            raise TaskError("integration check changed target HEAD or worktree; evidence is invalid")
    if args.dry_run:
        return {**state, "would_cleanup": str(source)}
    if args.keep_worktree:
        return state
    # Worktree removal is conservative: even ignored files may contain user data.
    if commit(target) != candidate or dirty(target):
        raise TaskError("target changed or became dirty after check; preserve it and reassess checks")
    if source.exists():
        ensure_branch(repo, source, state["branch"])
        if commit(source) != candidate:
            raise TaskError("task branch changed after merge; preserve worktree")
        status = dirty(source, ignored=True)
        if status:
            state["phase"] = "cleanup_blocked"
            state["updated_at"] = now()
            save(repo, state)
            raise TaskError("task worktree contains tracked, untracked or ignored files; cleanup blocked")
        state["phase"] = "cleanup_intent"
        state["updated_at"] = now()
        save(repo, state)
        git(repo, "worktree", "remove", str(source))
    elif state["phase"] != "cleanup_intent":
        raise TaskError("task worktree is missing without a recorded cleanup intent")
    if any(Path(item["worktree"]).resolve() == source for item in worktrees(repo)):
        raise TaskError("task worktree remains registered after cleanup")
    if commit(repo, state["branch"]) != candidate:
        raise TaskError("task branch changed during cleanup")
    state["phase"] = "done"
    state["updated_at"] = now()
    save(repo, state)
    return state


def parser() -> argparse.ArgumentParser:
    top = argparse.ArgumentParser(description=__doc__)
    sub = top.add_subparsers(dest="command", required=True)
    for name in ("create", "adopt"):
        part = sub.add_parser(name)
        part.add_argument("--repo", type=Path, required=True)
        part.add_argument("--id", required=True)
        part.add_argument("--target", required=True)
        part.add_argument("--branch", required=True)
        part.add_argument("--worktree", type=Path)
        part.add_argument("--dry-run", action="store_true")
    part = sub.add_parser("status")
    part.add_argument("--repo", type=Path, required=True)
    part.add_argument("--id", required=True)
    part = sub.add_parser("review")
    part.add_argument("--repo", type=Path, required=True)
    part.add_argument("--id", required=True)
    part.add_argument("--result", choices=("pass", "fail"), required=True)
    part.add_argument("--evidence", type=Path, required=True)
    part.add_argument("--dry-run", action="store_true")
    part = sub.add_parser("finish")
    part.add_argument("--repo", type=Path, required=True)
    part.add_argument("--id", required=True)
    part.add_argument("--check", help="shell command run in target worktree after merge")
    part.add_argument("--keep-worktree", action="store_true",
                      help="stop after verified merge and integration check; finish later")
    part.add_argument("--dry-run", action="store_true")
    return top


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command in ("create", "adopt"):
            result = register(args, adopt=args.command == "adopt")
        elif args.command == "status":
            result = inspect(args.repo.resolve(), load(args.repo.resolve(), args.id))
        elif args.command == "review":
            result = review(args)
        else:
            result = finish(args)
    except TaskError as error:
        print(f"task: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
