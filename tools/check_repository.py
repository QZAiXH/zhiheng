#!/usr/bin/env python3
"""检查本包跨文件契约，复用 PyYAML 和 markdown-it-py 解析。"""

import ast
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

from markdown_it import MarkdownIt
import yaml


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / ".agents/skills"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    manifest = json.loads((SKILLS / "double-loop/assets/project-manifest.json").read_text())
    found = {p.name for p in SKILLS.iterdir() if (p / "SKILL.md").is_file()}
    require(found == set(manifest["bundle"]), "技能目录与安装清单不同。")
    root_license = (ROOT / "LICENSE").read_bytes()
    for name in sorted(found):
        folder = SKILLS / name
        text = (folder / "SKILL.md").read_text()
        require(text.startswith("---\n"), f"{name} 缺少 frontmatter。")
        frontmatter = yaml.safe_load(text.split("---\n", 2)[1])
        require(isinstance(frontmatter, dict) and frontmatter.get("name") == name
                and isinstance(frontmatter.get("description"), str) and frontmatter["description"].strip(),
                f"{name} 入口元数据不完整。")
        metadata = yaml.safe_load((folder / "agents/openai.yaml").read_text())["interface"]
        require(25 <= len(metadata["short_description"]) <= 64 and "$" + name in metadata["default_prompt"],
                f"{name} 界面元数据不完整。")
        require((folder / "LICENSE").read_bytes() == root_license, f"{name} 缺少完整项目许可证。")

    parser = MarkdownIt("commonmark")
    markdown = list(SKILLS.rglob("*.md")) + list((ROOT / "docs").rglob("*.md")) + list(ROOT.glob("*.md"))
    evidence_json = list(SKILLS.rglob("*.json")) + list((ROOT / "docs").rglob("*.json"))
    checked_links = 0
    for path in markdown:
        for token in parser.parse(path.read_text()):
            for child in token.children or []:
                link = child.attrGet("href") if child.type == "link_open" else child.attrGet("src") if child.type == "image" else None
                if not link:
                    continue
                parsed = urlsplit(link)
                if parsed.scheme or parsed.netloc or not parsed.path:
                    continue
                require(not parsed.path.startswith("/"), f"公开文档使用了本机绝对链接：{path}")
                destination = (path.parent / unquote(parsed.path)).resolve()
                require(destination.is_relative_to(ROOT) and destination.exists(), f"引用缺失或越界：{path}: {link}")
                if path.is_relative_to(SKILLS):
                    require(destination.is_relative_to(SKILLS), f"安装后的技能引用依赖仓库外壳：{path}: {link}")
                checked_links += 1

    for path in list(SKILLS.rglob("*.py")) + list((ROOT / "tools").rglob("*.py")):
        ast.parse(path.read_text(), filename=str(path))
    for path in evidence_json:
        json.loads(path.read_text())
    yaml.safe_load((ROOT / ".github/workflows/verify.yml").read_text())

    redaction = SKILLS / "double-loop/references/verification/publication-redaction.json"
    for record in json.loads(redaction.read_text())["文件"]:
        path = ROOT / record["path"]
        require(hashlib.sha256(path.read_bytes()).hexdigest() == record["public_sha256"],
                f"公开历史证据在脱敏记录之后变化：{path}")

    # 只报告文件名，保护扫描结果中的实际值。
    forbidden = re.compile(r"/Users/[^/\s\"']+/|/opt/homebrew/|\b(?:gh[pousr]_|github_pat_)[A-Za-z0-9_]{20,}")
    for path in markdown + evidence_json + list(SKILLS.rglob("*.py")):
        require(not forbidden.search(path.read_text()), f"公开材料仍含本机定位或疑似凭证：{path.relative_to(ROOT)}")
    print(f"{len(found)} 个技能、项目许可证、{checked_links} 个相对引用、语法、JSON 与公开证据契约通过。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
