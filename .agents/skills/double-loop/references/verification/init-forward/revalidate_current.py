#!/usr/bin/env python3
"""独立复验当前快照，只用自身临时夹具和真实固定上游内容。"""
from pathlib import Path
import datetime
import hashlib
import importlib.util
import json
import os
import subprocess

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('own_validation', ROOT / 'validate_behavior.py')
test = importlib.util.module_from_spec(spec)
spec.loader.exec_module(test)
test.ROOT = ROOT / 'current_recheck'
test.ROOT.mkdir()
for name in ('projects', 'inputs', 'logs', 'runtime-temp'):
    (test.ROOT / name).mkdir()
test.SCRIPT = ROOT / 'snapshot_current/dl-init/scripts/project_init.py'
test.BUNDLE = ROOT / 'snapshot_current'
test.ENV = dict(os.environ, TMPDIR=str(test.ROOT / 'runtime-temp'), PYTHONDONTWRITEBYTECODE='1')
test.RESULTS.clear()
test.CALLS.clear()
test.FINDINGS.clear()


def save():
    manifest = json.loads((ROOT / 'snapshot_current_manifest.json').read_text())
    drift = []
    for entry in manifest['sources']:
        path = Path(entry['path'])
        current = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        if current != entry['sha256']:
            drift.append({'path': str(path), 'tested_sha256': entry['sha256'], 'current_sha256': current, '需复验': True})
    old = json.loads((ROOT / 'independent_receipt.json').read_text())
    report = {'验证者': '/root/init_forward_check', '完成时间UTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              '临时目录': str(ROOT), '初轮回执': str(ROOT / 'independent_receipt.json'),
              '初轮结果': {'场景数': len(old['结果']), '失败数': sum(not r['通过'] for r in old['结果'])},
              '复验结果': test.RESULTS, '复验日志': test.CALLS, '被测文件SHA256': manifest['sources'],
              '期间版本变化': drift, '初轮发现': old['发现'],
              '测试边界': ['初轮真实网络 clone 与官方 installer 已实测；当前复验复用真实固定内容与 Git clone，避免重复网络安装。',
                           '本回执 Wiki、模型全部是明确模拟；没有原生生命周期或模型调用。',
                           '所有变更均位于自己的登记临时目录，没有修改技能包、全局配置或当前业务目录。',
                           '没有读取生成者测试或回执，也未读取 harness-workflow。'],
              '结论': '初轮安装与文件保护行为通过；损坏 JSON 数组记录问题已在当前快照复验；完整 Wiki 与模型接入仍未实测。'}
    (ROOT / 'independent_current_receipt.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'复验场景数': len(test.RESULTS), '失败数': sum(not r['通过'] for r in test.RESULTS),
                      '版本变化数': len(drift), '回执': str(ROOT / 'independent_current_receipt.json')}, ensure_ascii=False))


def main():
    project = test.seed('新版本复验项目')
    code, out, _ = test.cli(project, 'prepare', 'current_prepare', installer=ROOT / 'never-needed-installer.py')
    test.check('新版本在真实固定 checkout 与现有技能下完成 prepare', code == 0 and not out['conflicts'])
    agents_input = test.ROOT / 'inputs/instructions.md'
    agents_input.write_text('项目入口 src/app.py；当前没有测试配置。\n输出与新文稿使用中文，优先复用成熟开源工具。\n')
    code, out, _ = test.cli(project, 'instructions', 'current_instructions', agents_input)
    test.check('新版本中文指令增补后本地就绪', code == 0 and out['local_ready'] and not out['wiki_ready'])
    test.wiki_fixture(project)
    wiki_input = test.write_input('current-wiki-simulated.json', test.payload(project))
    code, out, _ = test.cli(project, 'wiki', 'current_simulated_wiki_structure', wiki_input)
    test.check('新版本结构有效的模拟回执可保存', code == 0 and out['initialized'], kind='明确模拟 Wiki')
    code, out, _ = test.cli(project, 'prepare', 'current_prepare_reuse', installer=ROOT / 'never-needed-installer.py')
    test.check('新版本重复 prepare 复用内容', code == 0 and out['local_ready'] and out['wiki_ready'], kind='真实本地重试 + 模拟既有 Wiki')
    before = test.project_map(project)
    code, out, _ = test.cli(project, 'status', 'current_readonly_status')
    test.check('新版本 status 无文件写入', code == 0 and out['initialized'] and before == test.project_map(project),
               kind='真实本地状态 + 模拟既有 Wiki')
    gitignore = project / '.gitignore'
    original_ignore = gitignore.read_bytes()
    gitignore.write_bytes(original_ignore + b'\n!/.agents/skills/tdd/\n')
    visible = subprocess.run(['git', '-C', str(project), 'check-ignore', '--no-index', '.agents/skills/tdd/'],
                             capture_output=True, text=True, env=test.ENV).returncode == 1
    code, out, _ = test.cli(project, 'status', 'current_negation_detected')
    test.check('安装后的用户否定规则使技能可见时 status 标记本地未就绪', visible and code == 0 and not out['local_ready']
               and any('ignore' in p for p in out['problems']))
    gitignore.write_bytes(original_ignore)
    durable = project / '.workflow/runs/fixture-run/spec.md'
    durable.parent.mkdir(parents=True)
    durable.write_text('# 已确认规格\n临时持久规格属于用户知识输入。\n')
    test.cli(project, 'wiki', 'wiki_before_durable_change', wiki_input)
    durable.write_text('# 已确认规格\n用户修改了持久规格。\n')
    code, out, _ = test.cli(project, 'status', 'current_durable_workflow_drift')
    test.check('持久运行规格变更使 Wiki 源指纹失效', code == 0 and out['local_ready'] and not out['wiki_ready'],
               kind='真实持久规格变更 + 模拟 Wiki')
    test.cli(project, 'wiki', 'wiki_after_durable_change', wiki_input)
    scratch = project / '.workflow/runs/fixture-run/scratch/tmp.md'
    scratch.parent.mkdir()
    scratch.write_text('临时草稿改动。\n')
    state = project / '.workflow/runs/fixture-run/state.json'
    state.write_text('{"phase":"planning"}\n')
    handoff = project / '.workflow/runs/fixture-run/handoffs/agent.json'
    handoff.parent.mkdir()
    handoff.write_text('{"simulated":true}\n')
    code, out, _ = test.cli(project, 'status', 'current_runtime_noise_excluded')
    test.check('scratch、handoff 与运行状态变更不反复失效 Wiki', code == 0 and out['wiki_ready'],
               kind='真实临时运行文件 + 模拟 Wiki')
    for value, suffix in [([], 'array'), ({'schema': 1, 'root': '', 'bundle': [], 'managed_files': {}, 'wiki': {}, 'conflicts': []}, 'bad-fields')]:
        damaged = test.ROOT / 'projects' / ('损坏记录-' + suffix)
        damaged.mkdir()
        (damaged / '.workflow').mkdir()
        if isinstance(value, dict):
            value['root'] = str(damaged.resolve())
        record = damaged / '.workflow/project.json'
        record.write_text(json.dumps(value, ensure_ascii=False) + '\n')
        initial = record.read_bytes()
        code, out, stderr = test.cli(damaged, 'status', 'current_record_' + suffix)
        test.check('损坏接入记录 ' + suffix + ' 返回中文结构化错误并保留字节', code == 2 and isinstance(out, dict)
                   and out.get('status') == 'error' and not stderr and record.read_bytes() == initial)
    original_dependencies = (project / '.workflow/dependencies.json').read_bytes()
    (project / '.workflow/dependencies.json').write_text('[]\n')
    code, out, stderr = test.cli(project, 'prepare', 'current_dependencies_array')
    test.check('数组依赖配置返回结构化错误并保留', code == 2 and isinstance(out, dict) and not stderr
               and (project / '.workflow/dependencies.json').read_bytes() == b'[]\n')
    (project / '.workflow/dependencies.json').write_bytes(original_dependencies)
    for field in ('host', 'tool_response'):
        bad = test.payload(project)
        bad[field] = []
        code, out, stderr = test.cli(project, 'wiki', 'current_receipt_' + field + '_array',
                                     test.write_input('bad-' + field + '-simulated.json', bad))
        test.check('Wiki 回执 ' + field + ' 数组返回结构化错误', code == 2 and isinstance(out, dict) and not stderr,
                   kind='明确模拟无效 Wiki 回执')
    code, out, stderr = test.cli(project, 'wiki', 'current_receipt_array', test.write_input('bad-array-simulated.json', []))
    test.check('数组 Wiki 回执返回结构化错误', code == 2 and isinstance(out, dict) and not stderr,
               kind='明确模拟无效 Wiki 回执')
    test.cli(project, 'prepare', 'current_restore_prepare')
    code, out, _ = test.cli(project, 'verify', 'current_final_verify')
    test.check('边界测试恢复后当前项目结构验收通过', code == 0 and out['ready_for_worktrees'], kind='真实本地状态 + 模拟 Wiki')
    save()


if __name__ == '__main__':
    try:
        main()
    except BaseException:
        save()
        raise
