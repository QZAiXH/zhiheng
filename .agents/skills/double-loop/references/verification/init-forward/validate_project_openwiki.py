#!/usr/bin/env python3
"""项目级 OpenWiki 集成补验，不调用 Wiki 生成或任何模型。"""
from pathlib import Path
import datetime
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('own_validation', ROOT / 'validate_behavior.py')
test = importlib.util.module_from_spec(spec)
spec.loader.exec_module(test)
test.ROOT = ROOT / 'project_openwiki_recheck'
test.ROOT.mkdir()
for name in ('projects', 'inputs', 'logs', 'runtime-temp'):
    (test.ROOT / name).mkdir()
test.SCRIPT = ROOT / 'snapshot_openwiki/dl-init/scripts/project_init.py'
test.BUNDLE = ROOT / 'snapshot_openwiki'
test.ENV = dict(os.environ, TMPDIR=str(test.ROOT / 'runtime-temp'), PYTHONDONTWRITEBYTECODE='1',
                OPENWIKI_TELEMETRY_DISABLED='1')
test.RESULTS.clear()
test.CALLS.clear()
test.FINDINGS.clear()
CLI = str(Path(shutil.which('openwiki')).resolve())
PACKAGE = Path(CLI).parents[2]
CLI_LOGS = []


def native(project, action, label):
    cmd = [CLI, 'integrations', action]
    if action == 'install':
        cmd.append('codex')
    cmd += ['--project', str(project)]
    run = subprocess.run(cmd, cwd=test.ROOT, env=test.ENV, capture_output=True, text=True, timeout=120)
    receipt = {'操作': '真实成熟 OpenWiki CLI 项目级集成；没有 Wiki 生成或模型调用',
               'command': cmd, 'exit_code': run.returncode, 'stdout': run.stdout, 'stderr': run.stderr}
    path = test.ROOT / 'logs' / (label + '.json')
    path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
    CLI_LOGS.append(str(path))
    return run.returncode, run.stdout, run.stderr


def instructions(project, label):
    path = test.ROOT / 'inputs' / (label + '.md')
    path.write_text('项目入口 src/app.py；尚无独立测试配置。\n输出及新文稿使用中文，有成熟开源方案时优先复用。\n')
    return test.cli(project, 'instructions', label, path)


def ignored(project, path):
    run = subprocess.run(['git', '-C', str(project), 'check-ignore', '--no-index', path],
                         env=test.ENV, capture_output=True, text=True)
    return run.returncode == 0


def main():
    project = test.seed('项目OpenWiki入口切换')
    user_config = project / '.codex/config.toml'
    user_config.parent.mkdir()
    original_config = '# 用户已有项目配置\nmodel = "fixture-model-only"\n\n[mcp_servers.fixture_user_server]\ncommand = "echo"\nargs = ["fixture-only"]\n'.encode()
    user_config.write_bytes(original_config)
    original_head = test.git(project, 'rev-parse', 'HEAD')
    code, out, _ = test.cli(project, 'prepare', 'external_openwiki_prepare', installer=ROOT / 'missing-installer.py')
    test.check('使用外部已有 OpenWiki 入口能准备本地项目', code == 0 and not out['conflicts'])
    code, out, _ = instructions(project, 'external_openwiki_instructions')
    test.check('外部入口本地就绪与真实 Wiki 未完成分开报告', code == 0 and out['local_ready'] and not out['wiki_ready'])
    code, stdout, _ = native(project, 'list', 'native_before_install')
    test.check('成熟 CLI 项目级状态显示 Codex 尚未接入', code == 0 and 'codex\tnot-installed\tCodex' in stdout,
               kind='真实成熟 CLI 只读查询')
    installed_before = {name: test.file_map(project / '.agents/skills' / name) for name in test.SPEC['skills']}
    code, stdout, stderr = native(project, 'install', 'native_project_codex_install')
    local_skill = project / '.agents/skills/openwiki/SKILL.md'
    test.check('成熟 CLI 真实安装项目级 Codex 集成并提供本地技能入口', code == 0 and not stderr
               and local_skill.is_file() and (project / '.codex/config.toml').is_file(), kind='真实成熟 CLI 项目级安装')
    test.check('项目级集成保留用户已有 Codex 配置与其他 MCP', user_config.read_bytes().startswith(original_config)
               and b'[mcp_servers.fixture_user_server]' in user_config.read_bytes(), kind='真实成熟 CLI 项目级安装')
    test.WIKI = local_skill
    code, out, _ = test.cli(project, 'prepare', 'switch_to_project_openwiki', installer=ROOT / 'missing-installer.py')
    dependencies = json.loads((project / '.workflow/dependencies.json').read_text())
    expected = '/.agents/skills/openwiki/'
    test.check('重复 prepare 将依赖入口由外部路径切换到项目入口', code == 0 and out['local_ready']
               and dependencies['openwiki_skill'] == str(local_skill.resolve()))
    test.check('切换入口不重新安装固定上游技能', all(test.file_map(project / '.agents/skills' / name) == value
               for name, value in installed_before.items()))
    project_state = json.loads((project / '.workflow/project.json').read_text())
    test.check('未跟踪的项目 OpenWiki 技能被精确加入两类排除区块', expected in project_state['excluded_sources']
               and expected.encode() in (project / '.gitignore').read_bytes()
               and expected.encode() in (project / '.openwikiignore').read_bytes() and ignored(project, '.agents/skills/openwiki/SKILL.md'))
    config_bytes = user_config.read_bytes()
    skill_before = test.file_map(local_skill.parent)
    code, stdout, stderr = native(project, 'install', 'native_project_codex_repeat')
    test.check('成熟 CLI 重复集成返回 unchanged，配置与技能内容不变', code == 0 and stdout.startswith('unchanged Codex')
               and not stderr and user_config.read_bytes() == config_bytes and test.file_map(local_skill.parent) == skill_before,
               kind='真实成熟 CLI 重复安装')
    ignore_before = {(project / name).name: (project / name).read_bytes() for name in ('.gitignore', '.openwikiignore')}
    code, out, _ = test.cli(project, 'prepare', 'repeat_project_openwiki_prepare', installer=ROOT / 'missing-installer.py')
    test.check('项目入口重复 prepare 不重复排除区块也不改变用户配置', code == 0 and out['local_ready']
               and all((project / name).read_bytes() == value for name, value in ignore_before.items())
               and user_config.read_bytes() == config_bytes)
    code, stdout, _ = native(project, 'list', 'native_after_install')
    test.check('成熟 CLI 项目级 Codex 状态为 installed', code == 0 and 'codex\tinstalled\tCodex' in stdout,
               kind='真实成熟 CLI 只读查询')
    code, out, _ = test.cli(project, 'verify', 'no_real_wiki_verify')
    test.check('安装集成没有伪造 Wiki 完成，verify 仍非零', code == 2 and out['local_ready'] and not out['wiki_ready']
               and not out['initialized'] and not (project / 'openwiki').exists())
    test.check('集成与准备不提交已有业务文件', test.git(project, 'rev-parse', 'HEAD') == original_head)
    first = test.seed('缺少OpenWiki入口首次接入')
    code, stdout, stderr = native(first, 'install', 'native_first_before_prepare')
    test.WIKI = first / '.agents/skills/openwiki/SKILL.md'
    test.check('入口缺失时先接入成熟项目集成再取得 prepare 路径', code == 0 and not stderr and test.WIKI.is_file(),
               kind='真实成熟 CLI 项目级安装 + 流程验证')
    code, out, _ = test.cli(first, 'prepare', 'first_prepare_local_openwiki', installer=ROOT / 'missing-installer.py')
    instructions(first, 'first_local_openwiki_instructions')
    code, out, _ = test.cli(first, 'status', 'first_local_openwiki_status')
    test.check('先集成后 prepare 可形成有效本地接入且仍等待 Wiki', code == 0 and out['local_ready'] and not out['wiki_ready'])
    subprocess.run(['git', '-C', str(first), 'add', '-f', '.agents/skills/openwiki'], env=test.ENV, check=True)
    code, out, _ = test.cli(first, 'prepare', 'tracked_project_openwiki_prepare', installer=ROOT / 'missing-installer.py')
    tracked_state = json.loads((first / '.workflow/project.json').read_text())
    test.check('已跟踪的项目 OpenWiki 技能源码继续可见', code == 0 and out['local_ready']
               and expected not in tracked_state['excluded_sources']
               and not ignored(first, '.agents/skills/openwiki/SKILL.md'))
    before = test.project_map(first)
    code, out, _ = test.cli(first, 'status', 'local_openwiki_status_readonly')
    test.check('项目入口状态检查只读', code == 0 and before == test.project_map(first))
    global_records = json.loads((ROOT / 'global_readonly_baseline.json').read_text())
    unchanged = all(Path(e['path']).is_file() and hashlib.sha256(Path(e['path']).read_bytes()).hexdigest() == e['sha256']
                    and Path(e['path']).stat().st_mtime_ns == e['mtime_ns'] for e in global_records)
    test.check('全局 Codex 配置与全局 OpenWiki 入口 hash、mtime 均未变化', unchanged,
               {'核对范围': [e['path'] for e in global_records]}, kind='全局只读指纹核对')
    save()


def save():
    manifest = json.loads((ROOT / 'snapshot_openwiki_manifest.json').read_text())
    drift = []
    for e in manifest['sources']:
        path = Path(e['path'])
        current = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        if current != e['sha256']:
            drift.append({'path': str(path), 'tested_sha256': e['sha256'], 'current_sha256': current, '需复验': True})
    package_info = json.loads((PACKAGE / 'package.json').read_text())
    external = []
    for rel in ('package.json', 'dist/cli/cli.js', 'dist/integrations/install/installer.js',
                'dist/integrations/install/registry.js', 'dist/integrations/install/install-paths.js'):
        path = PACKAGE / rel
        external.append({'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    report = {'验证者': '/root/init_forward_check', '完成时间UTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              '临时目录': str(ROOT), '本轮结果': test.RESULTS, '本轮发现': test.FINDINGS,
              '调用日志': test.CALLS, '真实项目级CLI日志': CLI_LOGS, '被测文件SHA256': manifest['sources'],
              '成熟CLI': {'name': package_info['name'], 'version': package_info['version'], 'entry': CLI,
                           '来源': package_info['repository']['url'], '关键文件SHA256': external},
              '版本覆盖': {'初版': {'回执': str(ROOT / 'independent_receipt.json'), '场景数': 31,
                                    '说明': '包括真实 upstream 与官方 installer 网络安装；数组接入记录问题当时存在。'},
                           '对象与指纹修复版': {'回执': str(ROOT / 'independent_current_receipt.json'), '场景数': 15,
                                               '说明': '数组记录诊断、否定 ignore、持久规格与运行噪声已经复验。'},
                           '项目级OpenWiki新版': {'场景数': len(test.RESULTS), '说明': '本轮只复验实际项目入口切换、精确排除与重复准备。'}},
              '期间版本变化': drift,
              '测试边界': ['真实执行成熟 OpenWiki 0.7.0 CLI 项目级 Codex 集成的 list/install；没有调用 Wiki 生成生命周期、任何模型或 PR。',
                           'CLI 的命令参数始终显式 --project，且进程内关闭遥测；未修改全局配置。',
                           '固定上游技能通过首轮真实下载的 checkout 本地 Git clone 复用，没有再次网络安装。',
                           '只在原登记临时目录中产生或修改夹具；没有修改本技能包或当前业务目录。',
                           '没有读取生成者 test_*.py、验证回执或 harness-workflow。',
                           'CLI 安装成功不证明当前宿主 MCP 已加载；Wiki-ready 明确为 false。',
                           '临时目录全部保留，等待主 Agent 归档核对后清理。'],
              '结论': '项目级 OpenWiki 新流程独立补验完成；真实安装集成、入口切换、排除及重复调用已经验证，真实 Wiki 与模型仍未实测。'}
    (ROOT / 'independent_final_receipt.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'本轮场景数': len(test.RESULTS), '失败数': sum(not e['通过'] for e in test.RESULTS),
                      '版本变化数': len(drift), '回执': str(ROOT / 'independent_final_receipt.json')}, ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except BaseException:
        save()
        raise
