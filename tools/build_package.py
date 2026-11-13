#!/usr/bin/env python3
"""Build the small installable plugin from the authoritative source tree."""

import hashlib
import json
from pathlib import Path
import shutil
import sys


ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "dist/zhiheng"
SINGLE_FILES = (
    ".codex-plugin/plugin.json", "LICENSE",
)


def main():
    if DEST.exists():
        shutil.rmtree(DEST)
    for name in SINGLE_FILES:
        source, target = ROOT / name, DEST / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    for source in sorted((ROOT / "skills").rglob("*")):
        if not source.is_file() or "__pycache__" in source.parts or source.suffix == ".pyc":
            continue
        target = DEST / source.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    files = {
        path.relative_to(DEST).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(DEST.rglob("*")) if path.is_file()
    }
    (DEST / "package-manifest.json").write_text(
        json.dumps({"schema_version": 1, "files": files}, indent=2, ensure_ascii=False) + "\n"
    )
    print(json.dumps({"output": str(DEST), "files": len(files), "skills": sum(
        path.endswith("/SKILL.md") for path in files)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
