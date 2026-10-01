#!/usr/bin/env python3
"""Create an unready harness draft, never initialize or operate a workflow.

Requires filelock==3.19.1 and verified local macOS or Linux/WSL storage.
macOS permits APFS/HFS with MNT_LOCAL; Linux/WSL uses the allowlist below.
NFS, SMB/CIFS, FUSE, WSL drvfs/9p and unknown types are refused. Native Windows
is unsupported. macOS code has simulated-platform coverage; real Mac testing
must be completed on that host before claiming its P0 capability.
The native UnixFileLock lock inode is the only metadata created before locking.
Dry-run never acquires that mutating lock and cannot promise lock availability.
Do not remove the persistent lock file, even when no process holds its lock.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import ctypes
import hashlib
from importlib.metadata import PackageNotFoundError, version
import json
import os
from pathlib import Path
import platform
import re
import stat
import subprocess
import sys
from typing import Iterator


FILELOCK_VERSION = "3.19.1"
SUPPORTED_FILESYSTEMS = frozenset({"ext2", "ext3", "ext4", "xfs", "btrfs", "tmpfs", "overlay"})
DARWIN_FILESYSTEMS = frozenset({"apfs", "hfs"})
DARWIN_MNT_LOCAL = 0x00001000
LOCK_NAME = "harness.run.lock"


class InitRefused(Exception):
    def __init__(self, reason: str, *, status: str = "blocked") -> None:
        self.reason = reason
        self.status = status
        super().__init__(reason)


def git(repo: Path, *args: str) -> str:
    """Only read Git metadata; inherited repository overrides must not redirect it."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env["GIT_OPTIONAL_LOCKS"] = "0"
    try:
        result = subprocess.run(
            ["git", "-C", os.fspath(repo), *args], capture_output=True,
            env=env, timeout=15, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise InitRefused(f"Cannot inspect Git repository: {exc}") from exc
    if result.returncode:
        raise InitRefused("Git repository inspection failed: " + os.fsdecode(result.stderr).strip())
    return os.fsdecode(result.stdout).removesuffix("\n")


def repository_paths(repo: Path) -> tuple[Path, Path]:
    if not repo.is_dir():
        raise InitRefused("--repo must identify an existing non-bare Git working tree")
    if git(repo, "rev-parse", "--is-bare-repository") != "false":
        raise InitRefused("Bare repositories are not supported")
    root = Path(git(repo, "rev-parse", "--path-format=absolute", "--show-toplevel")).resolve(strict=True)
    common = Path(git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir")).resolve(strict=True)
    return root, common


def _mount_unescape(value: str) -> str:
    return re.sub(r"\\([0-7]{3})", lambda m: chr(int(m.group(1), 8)), value)


class _DarwinStatfs64(ctypes.Structure):
    """Darwin's documented 64-bit statfs ABI, not a filesystem implementation.

    Layout/flags: Apple XNU bsd/sys/mount.h __DARWIN_STRUCT_STATFS64.
    https://github.com/apple-oss-distributions/xnu/blob/main/bsd/sys/mount.h
    """
    _fields_ = [
        ("f_bsize", ctypes.c_uint32), ("f_iosize", ctypes.c_int32),
        ("f_blocks", ctypes.c_uint64), ("f_bfree", ctypes.c_uint64),
        ("f_bavail", ctypes.c_uint64), ("f_files", ctypes.c_uint64),
        ("f_ffree", ctypes.c_uint64), ("f_fsid", ctypes.c_int32 * 2),
        ("f_owner", ctypes.c_uint32), ("f_type", ctypes.c_uint32),
        ("f_flags", ctypes.c_uint32), ("f_fssubtype", ctypes.c_uint32),
        ("f_fstypename", ctypes.c_char * 16), ("f_mntonname", ctypes.c_char * 1024),
        ("f_mntfromname", ctypes.c_char * 1024), ("f_flags_ext", ctypes.c_uint32),
        ("f_reserved", ctypes.c_uint32 * 7),
    ]


def _load_darwin_fstatfs():
    """Select an explicitly 64-bit ABI; never call the legacy Intel statfs ABI."""
    if sys.platform != "darwin" or ctypes.sizeof(ctypes.c_void_p) != 8:
        raise InitRefused("Native macOS filesystem inspection requires 64-bit Darwin")
    machine = platform.machine().lower()
    names = (("fstatfs",) if machine in {"arm64", "aarch64"}
             else ("fstatfs$INODE64", "fstatfs64") if machine == "x86_64" else ())
    if not names:
        raise InitRefused("Unverified macOS architecture; refusing filesystem assumptions")
    library = ctypes.CDLL(None, use_errno=True)
    for name in names:
        function = getattr(library, name, None)
        if function is not None:
            function.argtypes = [ctypes.c_int, ctypes.POINTER(_DarwinStatfs64)]
            function.restype = ctypes.c_int
            return function
    raise InitRefused("Native Darwin 64-bit fstatfs API unavailable")


def _darwin_filesystem(path: Path) -> tuple[str, bool]:
    if (ctypes.sizeof(_DarwinStatfs64) != 2168 or _DarwinStatfs64.f_flags.offset != 64
            or _DarwinStatfs64.f_fstypename.offset != 72):
        raise InitRefused("Unexpected Darwin filesystem ABI layout")
    function = _load_darwin_fstatfs()
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        result = _DarwinStatfs64()
        if function(descriptor, ctypes.byref(result)) != 0:
            error = ctypes.get_errno()
            raise InitRefused(f"Native Darwin fstatfs failed for {path}: {os.strerror(error)}")
        try:
            kind = bytes(result.f_fstypename).split(b"\0", 1)[0].decode("ascii", errors="strict")
        except UnicodeError as exc:
            raise InitRefused("Native Darwin returned an invalid filesystem type") from exc
        return kind, bool(result.f_flags & DARWIN_MNT_LOCAL)
    finally:
        os.close(descriptor)


def require_supported_local_filesystems(*paths: Path) -> dict[str, str]:
    if sys.platform == "darwin":
        found = {}
        for path in paths:
            kind, local = _darwin_filesystem(path)
            if kind not in DARWIN_FILESYSTEMS or not local:
                raise InitRefused(f"Unsupported or non-local macOS filesystem {kind!r} for {path}; only local APFS/HFS is supported")
            found[str(path)] = kind
        return found
    if sys.platform != "linux":
        raise InitRefused("Only macOS or Linux/WSL with a verified local filesystem is supported; native Windows is unsupported")
    try:
        lines = Path("/proc/self/mountinfo").read_text().splitlines()
        mounts = []
        for line in lines:
            left, right = line.split(" - ", 1)
            mounts.append((Path(_mount_unescape(left.split()[4])), right.split()[0]))
    except (OSError, IndexError, ValueError) as exc:
        raise InitRefused("Cannot verify local filesystem types from /proc/self/mountinfo") from exc
    found = {}
    for path in paths:
        matches = [(mount, kind) for mount, kind in mounts if path == mount or mount in path.parents]
        if not matches:
            raise InitRefused(f"Cannot identify filesystem for {path}")
        _, kind = max(matches, key=lambda pair: len(pair[0].parts))
        if kind not in SUPPORTED_FILESYSTEMS:
            raise InitRefused(f"Unsupported filesystem {kind!r} for {path}; network/shared filesystems are unsupported")
        found[str(path)] = kind
    return found


def require_local_linux(*paths: Path) -> dict[str, str]:
    """Compatibility API for callers; now verifies macOS and Linux/WSL."""
    return require_supported_local_filesystems(*paths)


def _descriptor_alias(descriptor: int) -> str:
    if sys.platform == "linux":
        return f"/proc/self/fd/{descriptor}"
    if sys.platform == "darwin":
        # macOS fd(4) opens the already-open descriptor; no repository path
        # lookup or symlink-following is delegated to filelock's O_TRUNC open.
        return f"/dev/fd/{descriptor}"
    raise InitRefused("Native UnixFileLock backend is supported only on macOS or Linux/WSL")


def load_lock_backend():
    try:
        installed = version("filelock")
        from filelock import Timeout, UnixFileLock
        from filelock._unix import has_fcntl
    except (ImportError, PackageNotFoundError) as exc:
        raise InitRefused(f"Install filelock=={FILELOCK_VERSION} in the dedicated tool environment") from exc
    if installed != FILELOCK_VERSION or not has_fcntl:
        raise InitRefused(f"Native UnixFileLock from filelock=={FILELOCK_VERSION} is required (found {installed})")
    return UnixFileLock, Timeout


def entry_stat(directory_fd: int, name: str):
    try:
        return os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    except FileNotFoundError:
        return None


def inspect_destination(root_fd: int) -> None:
    if entry_stat(root_fd, ".loop-state.json") is not None:
        raise InitRefused(
            "Existing .loop-state.json requires the recovery controller to verify old execution has stopped; "
            "acquiring the lock alone is insufficient"
        )
    existing = entry_stat(root_fd, ".harness")
    if existing is None:
        return
    if stat.S_ISLNK(existing.st_mode):
        raise InitRefused("Refusing symlink at .harness; no target was read or written")
    raise InitRefused(
        "Existing .harness preserved unchanged. Review its config/manifest and any interrupted draft manually; "
        "this initializer never repairs, merges, or overwrites existing files",
        status="needs_review",
    )


def inspect_shared_checkpoints(root: Path, common: Path) -> None:
    if os.path.lexists(common / "harness.execution.json"):
        raise InitRefused(
            "Shared harness.execution.json exists; use the recovery controller to reconcile previous "
            "execution before initializing another worktree"
        )
    # A linked worktree can outlive its controlling process. Its checkpoint is
    # still relevant even if this particular working tree has never been used.
    listing = git(root, "worktree", "list", "--porcelain", "-z")
    for item in listing.split("\0"):
        if item.startswith("worktree "):
            candidate = Path(item[len("worktree "):]) / ".loop-state.json"
            if os.path.lexists(candidate):
                raise InitRefused(
                    f"Checkpoint exists in a linked repository worktree ({candidate}); "
                    "the recovery controller must verify previous execution has stopped"
                )


@contextmanager
def repository_lock(common: Path, backend, timeout_error) -> Iterator[None]:
    """Use filelock's native flock on a no-follow, pinned inode.

    Version 3.19.1 opens with O_TRUNC; pinning an empty inode prevents following
    a substituted symlink or truncating user content. All participants must keep
    this inode in place. The lock file itself is deliberately never deleted.
    """
    common_fd = os.open(common, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    lock_fd = None
    try:
        try:
            lock_fd = os.open(LOCK_NAME, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                              0o600, dir_fd=common_fd)
        except FileExistsError:
            try:
                lock_fd = os.open(LOCK_NAME, os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK,
                                  dir_fd=common_fd)
            except OSError as exc:
                raise InitRefused("Run lock must be a regular, non-symlink local file") from exc
        info = os.fstat(lock_fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size != 0:
            raise InitRefused("Refusing a nonempty, non-regular, or hard-linked run lock; nothing was truncated")
        # Descriptor-backed aliases bind filelock's O_TRUNC open to the inspected
        # inode: Linux /proc/self/fd, Darwin's native /dev/fd descriptor device.
        lock = backend(_descriptor_alias(lock_fd), timeout=0, mode=stat.S_IMODE(info.st_mode))
        try:
            lock.acquire(blocking=False)
        except timeout_error as exc:
            raise InitRefused("Another process holds the shared repository run lock; initialization refused") from exc
        except (OSError, NotImplementedError) as exc:
            raise InitRefused(f"Native lock unavailable; no soft-lock fallback is allowed: {exc}") from exc
        try:
            actual_fd = lock._context.lock_file_fd  # Pinned filelock 3.19.1 native backend.
            locked = os.fstat(actual_fd)
            if (locked.st_dev, locked.st_ino) != (info.st_dev, info.st_ino):
                raise InitRefused("Native descriptor alias resolved to a different lock inode")
            current = entry_stat(common_fd, LOCK_NAME)
            if current is None or (current.st_dev, current.st_ino) != (info.st_dev, info.st_ino):
                raise InitRefused("Run lock path changed during acquisition; initialization refused")
            yield
        finally:
            lock.release()
    finally:
        if lock_fd is not None:
            os.close(lock_fd)
        os.close(common_fd)


def json_bytes(value: dict) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def draft_config(mode: str) -> tuple[dict, Path]:
    # This sibling is the shared draft contract; never import project code.
    if __package__:
        from . import harness_check
    else:
        import harness_check
    config = harness_check.scaffold(mode)["config"]
    config["ready"] = False
    config["missing_p0"] = (
        ["repository_id"]
        + ["environment." + name for name in harness_check.ENV_FIELDS]
        + ["limits." + name for name in config["limits"]]
        + ["checks", "host_execution_and_stop_drill", "independent_review_drill",
           "serena_native_onboarding_and_core_read", "durable_evidence_retention",
           "target_baseline_policy", "mode_end_to_end_pilot"]
        + (["github." + name for name in config["github"]] if mode == "github" else [])
    )
    return config, Path(harness_check.__file__).resolve(strict=True)


def exclusive_write(directory_fd: int, name: str, data: bytes) -> None:
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                 0o644, dir_fd=directory_fd)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def initialize(repo: Path, mode: str = "local", *, dry_run: bool = False) -> dict:
    if mode not in {"local", "github"}:
        raise InitRefused("mode must be local or github")
    if sys.platform not in {"linux", "darwin"}:
        raise InitRefused("Only macOS or Linux/WSL with a verified local filesystem is supported; native Windows is unsupported")
    root, common = repository_paths(repo)
    filesystems = require_local_linux(root, common)
    backend, timeout_error = load_lock_backend()
    root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        inspect_destination(root_fd)
        inspect_shared_checkpoints(root, common)
        config, helper_path = draft_config(mode)
        config["repository_root"] = str(root)
        config_data = json_bytes(config)
        result = {
            "status": "dry_run" if dry_run else "initialized_draft",
            "ready": False,
            "repo": str(root), "mode": mode,
            "lock_path": str(common / LOCK_NAME),
            "files": [".harness/config.json", ".harness/manifest.json"],
            "next_step": "Complete and verify every P0 requirement before using any workflow controller",
        }
        if dry_run:
            result["lock_acquired"] = False
            result["notice"] = "No files changed; run lock was not acquired or tested for availability"
            result["draft_config"] = config
            return result
        manifest = {
            "schema_version": 1, "status": "draft", "ready": False, "mode": mode,
            "generator": {
                "name": "init_project.py", "sha256": sha256(Path(__file__).read_bytes()),
                "scaffold_helper": {"name": helper_path.name, "sha256": sha256(helper_path.read_bytes())},
            },
            "dependencies": {"filelock": FILELOCK_VERSION, "lock_backend": "UnixFileLock"},
            "generated_files": {".harness/config.json": {"sha256": sha256(config_data)}},
            "filesystem_types": filesystems,
            "scope": "configuration scaffold only; P0 and workflow execution remain unverified",
        }
        with repository_lock(common, backend, timeout_error):
            inspect_destination(root_fd)
            inspect_shared_checkpoints(root, common)
            root_info = os.fstat(root_fd)
            current_root = os.stat(root, follow_symlinks=False)
            if (root_info.st_dev, root_info.st_ino) != (current_root.st_dev, current_root.st_ino):
                raise InitRefused("Repository root changed during initialization")
            os.mkdir(".harness", mode=0o755, dir_fd=root_fd)
            harness_fd = os.open(".harness", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=root_fd)
            try:
                exclusive_write(harness_fd, "config.json", config_data)
                exclusive_write(harness_fd, "manifest.json", json_bytes(manifest))
                os.fsync(harness_fd)
            finally:
                os.close(harness_fd)
            os.fsync(root_fd)
        result["notice"] = "Draft created; this does not establish project or workflow readiness"
        return result
    finally:
        os.close(root_fd)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True, help="Existing Git working tree")
    parser.add_argument("--mode", choices=("local", "github"), default="local")
    parser.add_argument("--dry-run", action="store_true", help="Inspect and show draft without writing or locking")
    args = parser.parse_args(argv)
    try:
        result = initialize(args.repo, args.mode, dry_run=args.dry_run)
    except InitRefused as exc:
        result = {"status": exc.status, "ready": False, "reason": exc.reason}
        code = 2
    except (OSError, ImportError, ValueError) as exc:
        result = {
            "status": "blocked", "ready": False,
            "reason": f"Initialization stopped: {exc}. Any partial draft is preserved for manual review",
        }
        code = 2
    else:
        code = 0
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
