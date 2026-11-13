#!/usr/bin/env python3
"""Check packaged skill entrypoints and local references without installing them."""

import json
import hashlib
import re
import sys
from pathlib import Path

import yaml
from build_package import DEST, SINGLE_FILES

ROOT = Path(__file__).resolve().parents[1]
NAMES = (
    "zh", "zh-init", "zh-discuss", "zh-research", "zh-domain",
    "zh-arch", "zh-prototype", "zh-spec", "zh-plan", "zh-implement",
    "zh-tdd", "zh-debug", "zh-review", "zh-verify", "zh-deliver",
    "zh-release", "zh-resume",
)
LINK = re.compile(r"(?<!!)\[[^\]]+\]\(([^)#]+)(?:#[^)]*)?\)")


def main() -> int:
    errors = []
    manifest = json.loads((ROOT / ".codex-plugin/plugin.json").read_text())
    if manifest.get("skills") != "./skills/":
        errors.append("plugin.json: skills 必须指向 ./skills/")
    marketplace = json.loads((ROOT / ".agents/plugins/marketplace.json").read_text())
    entries = marketplace.get("plugins", [])
    if marketplace.get("name") != "zhiheng-local" or len(entries) != 1 or (
        entries[0].get("name") != "zhiheng"
        or entries[0].get("source") != {"source": "local", "path": "./dist/zhiheng"}
    ):
        errors.append("marketplace.json: 本地安装入口与插件根目录不一致")
    actual = {p.name for p in (ROOT / "skills").iterdir() if (p / "SKILL.md").exists()}
    if actual != set(NAMES):
        errors.append(f"技能入口差异: 缺少 {sorted(set(NAMES) - actual)}；多出 {sorted(actual - set(NAMES))}")
    checked = 0
    for name in NAMES:
        path = ROOT / "skills" / name / "SKILL.md"
        if not path.is_file():
            continue
        text = path.read_text()
        if not text.startswith("---\n") or "\n---\n" not in text[4:]:
            errors.append(f"{path}: 缺少 YAML frontmatter")
            continue
        meta = yaml.safe_load(text.split("\n---\n", 1)[0][4:])
        if not isinstance(meta, dict) or meta.get("name") != name or not meta.get("description"):
            errors.append(f"{path}: name/description 缺失或不一致")
        if "disable-model-invocation" in meta:
            errors.append(f"{path}: 入口不支持自动发现")
        if len(str(meta.get("description", ""))) > 400:
            errors.append(f"{path}: description 超长")
        checked += 1
    for path in (ROOT / "skills").rglob("*.md"):
        text = path.read_text()
        for relative in LINK.findall(text):
            if "://" in relative or relative.startswith(("/", "#", "$", "<")):
                continue
            target = (path.parent / relative).resolve()
            if not target.is_relative_to(ROOT) or not target.is_file():
                errors.append(f"{path.relative_to(ROOT)}: 断链 {relative}")
    expected = set(SINGLE_FILES) | {
        path.relative_to(ROOT).as_posix() for path in (ROOT / "skills").rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    }
    manifest_path = DEST / "package-manifest.json"
    if not manifest_path.is_file():
        errors.append("dist/zhiheng: 未构建安装包")
    else:
        manifest = json.loads(manifest_path.read_text())
        listed = manifest.get("files", {})
        actual = {path.relative_to(DEST).as_posix() for path in DEST.rglob("*")
                  if path.is_file() and path != manifest_path}
        if manifest.get("schema_version") != 1 or set(listed) != expected or actual != expected:
            errors.append("dist/zhiheng: 安装包文件清单与源码不一致")
        for name in sorted(expected & actual & set(listed)):
            source_sha = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            installed_sha = hashlib.sha256((DEST / name).read_bytes()).hexdigest()
            if source_sha != installed_sha or installed_sha != listed[name]:
                errors.append(f"dist/zhiheng/{name}: 内容指纹与源码不一致")
        packaged = json.loads((DEST / ".codex-plugin/plugin.json").read_text())
        if packaged.get("skills") != "./skills/":
            errors.append("dist/zhiheng: 安装包技能路径错误")
    output = {"status": "passed" if not errors else "failed", "skills_checked": checked,
              "package_files_checked": len(expected), "errors": errors}
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
