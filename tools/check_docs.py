#!/usr/bin/env python3
"""Check repository documentation links and source-table targets."""

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r"(?<!!)\[[^\]]+\]\(([^)#]+)(?:#[^)]*)?\)")
TABLE_TARGETS = {
    "upstream-adoption.tsv": "target",
    "upstream-dependencies.tsv": "actual_internal_target",
    "upstream-provenance.tsv": "target",
}


def main() -> int:
    errors = []
    documents = [ROOT / "README.md", ROOT / "AGENTS.md", *sorted((ROOT / "docs").glob("*.md"))]
    for document in documents:
        for target in LINK.findall(document.read_text(encoding="utf-8")):
            if target.startswith(("https://", "http://", "#", "/")):
                continue
            if not (document.parent / target).exists():
                errors.append(f"{document.relative_to(ROOT)}: missing {target}")

    for name, field in TABLE_TARGETS.items():
        table = ROOT / "docs" / name
        with table.open(encoding="utf-8", newline="") as source:
            reader = csv.DictReader(source, delimiter="\t")
            if reader.fieldnames is None or field not in reader.fieldnames:
                errors.append(f"docs/{name}: missing {field} column")
                continue
            for number, row in enumerate(reader, 2):
                if None in row or any(value is None for value in row.values()):
                    errors.append(f"docs/{name}:{number}: invalid column count")
                    continue
                for target in row[field].split(";"):
                    if not target or not (ROOT / target).is_file():
                        errors.append(f"docs/{name}:{number}: missing target {target}")
    print(json.dumps({"documents": len(documents), "tables": len(TABLE_TARGETS),
                      "errors": errors}, ensure_ascii=False))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
