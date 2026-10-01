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


def group_alive(pgid):
    try:
        os.killpg(pgid, 0)
        return True
    except ProcessLookupError:
        return False


def stop_group(process, grace=0.3):
    """Always stop the owned group, not just a possibly exited group leader."""
    pgid = process.pid
    if group_alive(pgid):
        try:
            os.killpg(pgid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        until = time.monotonic() + grace
        while time.monotonic() < until and group_alive(pgid):
            process.poll()  # reap our direct child; descendants are reaped by init
            time.sleep(0.02)
        if group_alive(pgid):
            try:
                os.killpg(pgid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    try:
        process.wait(timeout=1)
    except subprocess.TimeoutExpired:
        raise RuntimeError('Owned command did not stop after SIGKILL')


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
