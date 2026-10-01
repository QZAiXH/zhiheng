#!/usr/bin/env python3
"""Check the installed sibling layout without network or optional dependencies."""
from pathlib import Path
import argparse
import ast
import re
import sys

NAMES = ('zh', 'zh-context', 'zh-plan', 'zh-implement', 'zh-debug', 'zh-review', 'zh-finish')


def validate(root):
    errors = []
    if not (root / 'zh/scripts/task.py').is_file():
        errors.append('Missing zh/scripts/task.py entrypoint')
    for name in NAMES:
        folder = root / name
        entry = folder / 'SKILL.md'
        if not entry.is_file():
            errors.append(f'{entry}: missing skill')
            continue
        content = entry.read_text()
        if not content.startswith('---\n') or '\n---\n' not in content[4:]:
            errors.append(f'{entry}: missing frontmatter')
            continue
        front = content.split('---\n', 2)[1]
        fields = dict(re.findall(r'^(name|description):\s*(.+)$', front, re.M))
        if fields.get('name') != name or not fields.get('description'):
            errors.append(f'{entry}: invalid name/description')
        if not (folder / 'LICENSE').is_file():
            errors.append(f'{folder}: missing redistributed license')
        if not (folder / 'agents/openai.yaml').is_file():
            errors.append(f'{folder}: missing interface metadata')
        for doc in folder.rglob('*.md'):
            for link in re.findall(r'\[[^\]]*\]\(([^)]+)\)', doc.read_text()):
                if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', link) or link.startswith('#'):
                    continue
                target = (doc.parent / link.split('#')[0]).resolve()
                if not target.is_relative_to(root.resolve()) or not target.exists():
                    errors.append(f'{doc}: unresolved local link {link}')
        for script in folder.rglob('*.py'):
            try:
                ast.parse(script.read_text(), filename=str(script))
            except SyntaxError as exc:
                errors.append(str(exc))
    if (root / 'zh/references/harness-integration.md').is_file():
        dependency_root = root / 'vendor/goal-workflow/skills' if (root / 'vendor/goal-workflow/skills').is_dir() else root
        components = ('harness-init', 'prd', 'prd-to-spec', 'to-design', 'to-issues', 'loop-it', 'review-it', 'note-it', 'walkthrough', 'ship-it')
        for name in components:
            entry = dependency_root / name / 'SKILL.md'
            if not entry.is_file():
                errors.append(f'{entry}: missing enhanced dependency')
                continue
            content = entry.read_text()
            if not re.search(r'^name: ' + re.escape(name) + r'$', content, re.M):
                errors.append(f'{entry}: incorrect enhanced skill name')
        assets = dependency_root / 'harness-init/assets/project'
        for required in ('pyproject.toml', 'uv.lock', 'harness/cli.py', 'harness/runtime.py', 'harness/state.py'):
            if not (assets / required).is_file():
                errors.append(f'{assets / required}: missing packaged runtime asset')
        for script in assets.rglob('*.py'):
            if any(part in ('.venv', '__pycache__') for part in script.parts):
                continue
            try:
                ast.parse(script.read_text(), filename=str(script))
            except (SyntaxError, UnicodeError) as exc:
                errors.append(str(exc))
    return errors


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', nargs='?', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    problems = validate(args.root)
    for problem in problems:
        print(problem, file=sys.stderr)
    if problems:
        raise SystemExit(1)
    print('Validated zh entries, licenses, local references and Python syntax; enhanced dependencies checked when present.')
