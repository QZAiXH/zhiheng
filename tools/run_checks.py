#!/usr/bin/env python3
"""Run package and tool checks from the repository root."""

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMMANDS = (
    [sys.executable, "tools/build_package.py"],
    [sys.executable, "tools/check_package.py"],
    [sys.executable, "tools/check_docs.py"],
    [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-v"],
    [sys.executable, "-m", "compileall", "-q", "skills/zh/scripts", "tools"],
)


def main() -> int:
    for command in COMMANDS:
        print("+", " ".join(command), flush=True)
        result = subprocess.run(command, cwd=ROOT, check=False)
        if result.returncode:
            return result.returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())
