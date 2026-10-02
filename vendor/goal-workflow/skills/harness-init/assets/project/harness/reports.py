"""Stable report identity and conservative Chinese report generation.

Mapping is configuration, not a second task-progress store. Call mutations while
holding the repository controller lock; do not synthesize verification evidence.
"""
from html import escape
from contextlib import redirect_stdout
import io
from pathlib import Path, PurePosixPath
import os
import tempfile
from .state import Blocked
from .local import safe_id


KINDS = ('note', 'walkthrough', 'delivery')
BEGIN = '<!-- harness:generated:start -->'
END = '<!-- harness:generated:end -->'


def relative_path(value):
    if not isinstance(value, str) or not value or '\\' in value or any(ord(c) < 32 for c in value):
        raise Blocked('invalid report path')
    p = PurePosixPath(value)
    if p.is_absolute() or '..' in p.parts or ':' in value or str(p) != value or value.startswith('.harness/runs/'):
        raise Blocked('report path must be normalized, durable and repo-relative')
    return value


def build_mapping(tasks, mode, existing=None):
    if mode not in ('local', 'github'):
        raise Blocked('explicit report mode required')
    mapping = {key: dict(value) for key, value in (existing or {}).items()}
    ids = set()
    for task in tasks:
        tid = safe_id(task['task_id'])
        if tid in ids:
            raise Blocked('duplicate task ID: ' + tid)
        ids.add(tid)
        if mode == 'github' and (type(task.get('issue_number')) is not int or task['issue_number'] <= 0):
            raise Blocked('GitHub report needs a verified real issue_number, even for an existing mapping')
        if tid not in mapping:
            if mode == 'github':
                number = task.get('issue_number')
                if type(number) is not int or number <= 0:
                    raise Blocked('GitHub report needs a real issue number')
                note = f'docs/issue#{number}.html'
            else:
                note = f'docs/task-{tid}.html'
            mapping[tid] = {'note': note, 'walkthrough': f'tasks/walkthrough-{tid}.md',
                            'delivery': f'docs/delivery-{tid}.md'}
    occupied = {}
    for tid, paths in mapping.items():
        safe_id(tid)
        if set(paths) != set(KINDS):
            raise Blocked('report mapping requires note, walkthrough and delivery')
        if not paths['walkthrough'].endswith('.md') or not paths['delivery'].endswith('.md'):
            raise Blocked('walkthrough and delivery reports must use .md paths')
        outputs = dict(paths, rendered_html=str(PurePosixPath(paths['walkthrough']).with_suffix('.html')))
        for kind, path in outputs.items():
            relative_path(path)
            key = path.casefold()
            if key in occupied:
                raise Blocked(f'report path collision: {path} and {occupied[key]}')
            occupied[key] = tid + ':' + kind
    return mapping


def _text(value):
    value = str(value if value is not None else '未发生/未记录').replace('\r', ' ').replace('\n', ' ')
    # Values are plain text, not executable HTML or user-controlled Markdown links.
    value = value.replace('\\', '\\\\')
    for char in ('[', ']', '(', ')', '`', '*', '_', '#', '!'):
        value = value.replace(char, '\\' + char)
    return escape(value, quote=False)


def _safe_output(root, path):
    root = Path(root).resolve()
    target = root / relative_path(path)
    if target.is_symlink() or not target.resolve().is_relative_to(root):
        raise Blocked('report path escapes repository or is a symlink')
    return target


def _merge_generated(target, generated):
    """Keep user content; replace only our own previously generated region."""
    old = target.read_text() if target.exists() else ''
    if BEGIN in old or END in old:
        if old.count(BEGIN) != 1 or old.count(END) != 1 or old.index(END) < old.index(BEGIN):
            raise Blocked('ambiguous generated report markers; preserve file for manual repair')
        a = old.index(BEGIN); b = old.index(END) + len(END)
        return old[:a] + BEGIN + '\n' + generated + '\n' + END + old[b:]
    if old:
        raise Blocked('existing report has no managed section; preserve and migrate explicitly')
    return BEGIN + '\n' + generated + '\n' + END + '\n'


def _atomic_text(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix='.' + path.name + '.', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as f:
            f.write(text); f.flush(); os.fsync(f.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def write_reports(controller, mode, task, result, mapping):
    if not getattr(controller, 'entered', False):
        raise Blocked('run lock required to write reports')
    mapping = build_mapping([task], mode, mapping)
    tid = task['task_id']; paths = mapping[tid]
    title = _text(task.get('title', tid))
    evidence = result.get('evidence', result)
    lines = [f'# 任务走查：{tid}', '', title, '',
             f'- 模式：{mode}', f'- 状态：{_text(result.get("status", "未验证"))}',
             f'- 验证类型：{_text(result.get("verification_tier", "未注明，不能按真实验收计"))}',
             '', '## 提交与基线']
    for key in ('H', 'T', 'C', 'D'):
        lines.append(f'- {key}：{_text(evidence.get(key))}')
    lines += ['', '## 逐项验收']
    for item in result.get('acceptance', []):
        lines.append(f'- {_text(item.get("id"))}：{_text(item.get("status"))}；{_text(item.get("evidence"))}')
    if not result.get('acceptance'):
        lines.append('- 未提供逐项记录，不能据此判定验收通过')
    lines += ['', '## 检查证据']
    for check in result.get('checks', []):
        lines.append(f'- {_text(check.get("id"))}：{_text(check.get("status"))}；exit={_text(check.get("exit_code"))}；tests={_text(check.get("tests"))}；skipped={_text(check.get("skipped"))}；failed={_text(check.get("failed"))}')
        if check.get('argv'):
            lines.append('  命令：' + _text(check['argv']))
    lines += ['', '## 审查及限制', _text(result.get('review', '未提供独立审查记录')),
              '', _text(result.get('limitations', '未注明；需结合原始工具证据复核')),
              '', '## 持久依据']
    for ref in result.get('durable_evidence', []):
        lines.append('- ' + _text(ref))
    if not result.get('durable_evidence'):
        lines.append('- 未提供持久依据，知识继续保留候选状态')
    md = '\n'.join(lines) + '\n'
    # Reuse the upstream renderer bundled for selective harness-init installs.
    from . import walkthrough_renderer
    with tempfile.TemporaryDirectory(prefix='harness-report-') as tempdir:
        source = Path(tempdir) / 'walkthrough.md'
        output = Path(tempdir) / 'walkthrough.html'
        source.write_text(md)
        with redirect_stdout(io.StringIO()):
            walkthrough_renderer.main([str(source), str(output)])
        html = output.read_text().replace('lang="en"', 'lang="zh-CN"')
    label = f'Issue #{task["issue_number"]}' if mode == 'github' else f'任务 {tid}'
    notes = ['<!doctype html>', '<html lang="zh-CN"><meta charset="utf-8"><title>实现笔记</title><body>',
             '<h1>' + escape(label + '：' + str(task.get('title', tid))) + '</h1>']
    for key, heading in [('decisions','设计决策'),('deviations','规范偏离'),('tradeoffs','取舍'),('questions','未决问题')]:
        notes += ['<h2>' + heading + '</h2>', '<p>' + escape(_text(task.get('notes', {}).get(key, '暂无已核实记录'))) + '</p>']
    notes += ['<p>重要决策链接 MADR 正文；未经核实的发现仍为候选。</p></body></html>']
    delivery = '\n'.join([f'# 交付说明：{tid}', '', f'- 模式：{mode}',
        f'- 状态：{_text(result.get("status", "未验证"))}',
        *[f'- {key}：{_text(evidence.get(key))}' for key in ('H', 'T', 'C', 'D')],
        '', '逐项验证见关联 walkthrough；未发生的交付不预填提交。',
        '本报告在最终提交验收前准备；实际最终提交关联从外部执行记录核实，报告存在不代表交付完成。',
        '', '未覆盖项：' + _text(result.get('limitations', '需查验收记录'))]) + '\n'
    generated = {'note': '\n'.join(notes), 'walkthrough': md, 'delivery': delivery, 'rendered_html': html}
    output_paths = dict(paths, rendered_html=str(PurePosixPath(paths['walkthrough']).with_suffix('.html')))
    prepared = []
    for kind, output_path in output_paths.items():
        target = _safe_output(controller.root, output_path)
        prepared.append((target, _merge_generated(target, generated[kind])))
    # Check all collisions/legacy files before any write; caller checkpoints after return.
    for target, text in prepared:
        _atomic_text(target, text)
    return paths
