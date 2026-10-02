#!/usr/bin/env python3
"""Portable standalone POSIX command supervisor (macOS, Linux and WSL).

Uses Python's start_new_session/killpg rather than GNU timeout or the setsid
executable. Harness execution uses Controller.execute directly, not this helper.
The process group is owned from spawn through cleanup, including when its leader
exits before background children. Deliberately detached sessions are unsupported.
"""
import argparse
import math
import os
import signal
import subprocess
import sys
import time


def live_group_members(pgid):
    """Read native POSIX process state; zombies cannot run or receive signals.

    Darwin can return EPERM from killpg for a group containing only zombies.
    A permission error is *not* absence: inspect every group member and fail
    closed if ps fails or reports a live member. /bin/ps is native on both
    supported OSes and is not a GNU utility requirement.
    """
    result = subprocess.run(['/bin/ps', '-axo', 'pid=,pgid=,stat='],
                            capture_output=True, text=True, timeout=2, check=True)
    rows = result.stdout.splitlines()
    if not rows:
        raise RuntimeError('Cannot confirm process cleanup: empty native process listing')
    members = []
    for line in rows:
        fields = line.split()
        if len(fields) != 3 or not fields[0].isdigit() or not fields[1].isdigit():
            raise RuntimeError('Cannot confirm process cleanup: malformed native process listing')
        if int(fields[1]) == pgid and not fields[2].startswith('Z'):
            members.append(int(fields[0]))
    return members


def group_alive(pgid):
    try:
        os.killpg(pgid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        if not live_group_members(pgid):
            return False
        raise


def signal_group(pgid, sig):
    try:
        os.killpg(pgid, sig)
    except ProcessLookupError:
        pass
    except PermissionError:
        if live_group_members(pgid):
            raise


def stop_group(process, grace=0.3):
    """Always stop the owned group, not just a possibly exited group leader."""
    pgid = process.pid
    process.poll()  # Reap the direct child before probing zombie-group liveness.
    if group_alive(pgid):
        signal_group(pgid, signal.SIGTERM)
        until = time.monotonic() + grace
        while time.monotonic() < until:
            process.poll()
            if not group_alive(pgid):
                break
            time.sleep(0.02)
        if group_alive(pgid):
            signal_group(pgid, signal.SIGKILL)
    try:
        process.wait(timeout=1)
    except subprocess.TimeoutExpired:
        raise RuntimeError('Owned command did not stop after SIGKILL')
    # SIGKILL delivery is asynchronous. Verify live descendants have stopped;
    # a zombie-only group is stopped even when Darwin killpg returns EPERM.
    until = time.monotonic() + 1
    while group_alive(pgid) and live_group_members(pgid):
        if time.monotonic() >= until:
            raise RuntimeError('Owned process group still has live members after cleanup')
        time.sleep(0.02)


def run(argv, timeout, parent_pid=None):
    if os.name != 'posix':
        print('review-it: standalone bounded runner requires POSIX process groups', file=sys.stderr)
        return 2
    parent_pid = os.getppid() if parent_pid is None else parent_pid
    received = [None]
    def interrupted(signum, frame):
        received[0] = signum
    old = {sig: signal.signal(sig, interrupted) for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP)}
    process = None
    try:
        # Signal handlers are installed before spawn, covering the spawn/cancel race.
        process = subprocess.Popen(argv, start_new_session=True)
        deadline = time.monotonic() + timeout
        while True:
            if os.getppid() != parent_pid:
                # A killed standalone shell must not leave its command running.
                return 143
            if received[0] is not None:
                return 128 + received[0]
            code = process.poll()
            if code is not None:
                return code if code >= 0 else 128 - code
            if time.monotonic() >= deadline:
                print(f'review-it: command exceeded {timeout:g}s timeout', file=sys.stderr)
                return 124
            time.sleep(min(0.02, max(0, deadline - time.monotonic())))
    except FileNotFoundError as exc:
        print(f'review-it: command unavailable: {exc.filename}', file=sys.stderr)
        return 127
    finally:
        try:
            if process is not None:
                stop_group(process)
        finally:
            for sig, handler in old.items():
                signal.signal(sig, handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--timeout', type=float, required=True)
    parser.add_argument('--parent-pid', type=int)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not math.isfinite(args.timeout) or args.timeout <= 0 or not command:
        parser.error('positive timeout and command required')
    return run(command, args.timeout, args.parent_pid)


if __name__ == '__main__':
    sys.exit(main())
