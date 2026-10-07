#!/usr/bin/env python3
"""独立行为验证；仅操作同目录登记的临时项目，Wiki 与模型均明确模拟。"""
from pathlib import Path
import datetime
import fcntl
import hashlib
import json
import os
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT / 'snapshot/dl-init/scripts/project_init.py'
BUNDLE = ROOT / 'snapshot'
INSTALLER = ROOT / 'external/installer/install-skill-from-github.py'
WIKI = ROOT / 'external/openwiki/SKILL.md'
BASE = ROOT / 'projects/已有项目'
SPEC = json.loads((BUNDLE / 'double-loop/assets/project-manifest.json').read_text())
ENV = dict(os.environ, TMPDIR=str(ROOT / 'runtime-temp'), PYTHONDONTWRITEBYTECODE='1')
RESULTS = []
CALLS = []
FINDINGS = []


def digest(data):
    return hashlib.sha256(data).hexdigest()


def json_digest(value):
    return digest(json.dumps(value, ensure_ascii=False, sort_keys=True).encode())


def check(name, condition, detail=None, kind='真实本地行为'):
    RESULTS.append({'场景': name, '通过': bool(condition), '证据类型': kind, '详情': detail})
    print(('通过：' if condition else '失败：') + name, flush=True)


def cli(project, verb, label, input_path=None, installer=INSTALLER, init_git=False):
    args = [sys.executable, str(SCRIPT), verb, '--root', str(project)]
    if verb == 'prepare':
        args += ['--bundle', str(BUNDLE), '--installer', str(installer), '--openwiki-skill', str(WIKI)]
        if init_git:
            args += ['--init-git']
    if input_path is not None:
        args += ['--input', str(input_path)]
    run = subprocess.run(args, cwd=ROOT, env=ENV, capture_output=True, text=True, timeout=600)
    try:
        output = json.loads(run.stdout)
    except ValueError:
        output = None
    receipt = {'label': label, 'command': args, 'exit_code': run.returncode,
               'output': output, 'stdout': run.stdout, 'stderr': run.stderr}
    path = ROOT / 'logs' / f'{len(CALLS)+3:02d}_{label}.json'
    path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
    CALLS.append(str(path))
    return run.returncode, output, run.stderr


def git(project, *args):
    return subprocess.check_output(['git', '-C', str(project), *args], env=ENV, text=True).strip()


def file_map(directory):
    return {p.relative_to(directory).as_posix(): digest(p.read_bytes())
            for p in directory.rglob('*')
            if p.is_file() and not any(x in {'.git', '__pycache__', '.DS_Store'} for x in p.relative_to(directory).parts)
            and p.suffix != '.pyc'}


def project_map(project):
    return {p.relative_to(project).as_posix(): (digest(p.read_bytes()), p.stat().st_mtime_ns)
            for p in project.rglob('*') if p.is_file() and '.git' not in p.relative_to(project).parts}


def payload(project, status='complete'):
    result = {'root': str(project.resolve()), 'status': status, 'simulated': True,
              'evidence': '[明确模拟，未调用真实模型或 Wiki]独立测试，仅验证助手结构校验。'}
    if status in {'complete', 'noop'}:
        result.update(operation='openwiki_finish' if status == 'complete' else 'openwiki_begin',
                      tool_response={'status': status, 'simulated': True},
                      host={'model': 'simulation-model-no-call', 'effort': 'simulation-effort',
                            'context': 'fresh', 'rationale': '明确模拟，行为验证需要。',
                            'capability_evidence': '无真实调用能力核验；仅模拟结构。',
                            'confirmed': True, 'confirmation': '临时测试夹具，非用户真实模型授权。'})
    return result


def write_input(name, value):
    path = ROOT / 'inputs' / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    return path


def wiki_fixture(project):
    directory = project / 'openwiki'
    directory.mkdir(exist_ok=True)
    (directory / 'quickstart.md').write_text('# 明确模拟 Wiki\n仅为助手文件校验夹具，不是原生 Wiki 生成结果。\n')
    path = project / 'AGENTS.md'
    if b'<!-- OPENWIKI:START -->' not in path.read_bytes():
        path.write_bytes(path.read_bytes() + b'\n<!-- OPENWIKI:START -->\n' +
                         '明确模拟的 OpenWiki 区块。'.encode() + b'\n<!-- OPENWIKI:END -->\n')


def seed(name, baseline=True):
    project = ROOT / 'projects' / name
    project.mkdir()
    (project / 'src').mkdir()
    (project / 'src/app.py').write_text('print("临时项目")\n')
    (project / 'TEST_ONLY.txt').write_text('隔离行为验证项目；Wiki、模型均未真实执行。\n')
    if baseline:
        subprocess.run(['git', 'init', str(project)], env=ENV, capture_output=True, check=True)
        subprocess.run(['git', '-C', str(project), 'add', '.'], env=ENV, check=True)
        subprocess.run(['git', '-C', str(project), '-c', 'user.name=Independent Test',
                        '-c', 'user.email=independent-test@example.invalid', 'commit', '-m', '独立临时项目基线'],
                       env=ENV, capture_output=True, check=True)
    vendor = project / '.agents/vendor/mattpocock-skills'
    vendor.parent.mkdir(parents=True)
    subprocess.run(['git', 'clone', '--no-hardlinks', str(BASE / '.agents/vendor/mattpocock-skills'), str(vendor)],
                   env=ENV, capture_output=True, check=True)
    git(vendor, 'checkout', '--detach', SPEC['revision'])
    skills = project / '.agents/skills'
    skills.mkdir(parents=True)
    for name, group in SPEC['skills'].items():
        shutil.copytree(vendor / 'skills' / group / name, skills / name)
    return project


def main():
    fixture = json.loads((ROOT / 'fixtures.json').read_text())
    actual = json.loads((ROOT / 'logs/02_actual_prepare.json').read_text())
    out = json.loads(actual['stdout'])
    check('固定上游真实 clone 与官方 installer 整批安装', actual['exit_code'] == 0 and not out['conflicts'],
          {'revision': git(BASE / '.agents/vendor/mattpocock-skills', 'rev-parse', 'HEAD'),
           'log': str(ROOT / 'logs/02_actual_prepare.json')}, '真实 Git + 官方网络安装')
    check('助手没有提交已有业务文件', git(BASE, 'rev-parse', 'HEAD') == fixture['baseline_head'])
    immutable = ['src/app.py', 'README.md', 'CLAUDE.md', 'AGENTS.md',
                 'docs/agents/issue-tracker.md', '.agents/skills/user-owned/SKILL.md', 'TEST_ONLY.txt']
    check('首次 prepare 保留全部用户源文件和指令字节',
          all(digest((BASE / name).read_bytes()) == fixture['initial_files'][name] for name in immutable))
    deps = json.loads((BASE / '.workflow/dependencies.json').read_text())
    check('已有依赖配置的用户字段保留', deps['user_metadata'] == {'tracker': 'tasks/', 'retained': True})
    all_matching = all(file_map(BASE / '.agents/skills' / name) ==
                       file_map(BASE / '.agents/vendor/mattpocock-skills/skills' / group / name)
                       for name, group in SPEC['skills'].items())
    check('15 个上游技能全目录内容与固定 checkout 一致', all_matching)
    check('九个本包技能完整安装', all(file_map(BASE / '.agents/skills' / name) == file_map(BUNDLE / name)
                                      for name in SPEC['bundle']))
    check('固定 checkout 许可证保留', any((BASE / '.agents/vendor/mattpocock-skills' / name).is_file()
                                         for name in ('LICENSE', 'LICENSE.md', 'LICENSE.txt')))
    before_agents = (BASE / 'AGENTS.md').read_bytes()
    prose = ROOT / 'inputs/instructions-zh.md'
    prose.parent.mkdir(exist_ok=True)
    prose.write_text('本项目入口是 src/app.py；运行入口为 python3 src/app.py，尚无独立测试命令。\n'
                     '输出和新文稿使用中文；有成熟开源方案时优先复用。\n'
                     '任务跟踪沿用 docs/agents/issue-tracker.md，源码变更时阅读现有规则。\n'
                     '首次接入和恢复分别阅读 .agents/skills/dl-init/SKILL.md 与 .agents/skills/dl-resume/SKILL.md；'
                     '研发由 .agents/skills/double-loop/SKILL.md 按本次能力推荐模型。\n')
    code, out, _ = cli(BASE, 'instructions', 'instructions_chinese', prose)
    check('增补中文正文保留既有 AGENTS 与 OpenWiki 区块',
          code == 0 and (BASE / 'AGENTS.md').read_bytes().startswith(before_agents) and out['local_ready'])
    data, mtime = (BASE / 'AGENTS.md').read_bytes(), (BASE / 'AGENTS.md').stat().st_mtime_ns
    code, out, _ = cli(BASE, 'instructions', 'instructions_idempotent', prose)
    check('相同指令再次调用无重复区块、不重写文件', code == 0 and (BASE / 'AGENTS.md').read_bytes() == data
          and (BASE / 'AGENTS.md').stat().st_mtime_ns == mtime)
    immutable_before = {name: file_map(BASE / '.agents/skills' / name) for name in [*SPEC['skills'], *SPEC['bundle']]}
    code, out, _ = cli(BASE, 'prepare', 'prepare_reuse_no_installer', installer=ROOT / 'not-an-installer.py')
    check('完整已有安装复用，不依赖再次可用的安装器', code == 0 and out['local_ready'] and not out['wiki_ready']
          and all(file_map(BASE / '.agents/skills' / name) == value for name, value in immutable_before.items()))
    check('prepare 正常退出清理自己的 staging', not list((BASE / '.workflow/onboarding/tmp').glob('dl-init-*')))
    before = project_map(BASE)
    code, out, _ = cli(BASE, 'status', 'status_read_only')
    check('已有项目 status 只读，字节与修改时间均稳定', code == 0 and project_map(BASE) == before)
    code, out, _ = cli(BASE, 'verify', 'verify_before_wiki')
    check('本地安装就绪但 Wiki 未完成时 verify 非零', code == 2 and out['local_ready'] and not out['initialized'])
    reload_input = write_input('reload-simulated.json', payload(BASE, 'awaiting_host_reload'))
    code, out, _ = cli(BASE, 'wiki', 'wiki_reload_simulated', reload_input)
    check('明确模拟 reload 状态可以保存，不能当完成', code == 0 and out['phase'] == 'awaiting_host_reload'
          and not out['wiki_ready'], kind='明确模拟 Wiki 状态')
    missing = write_input('complete-missing-files-simulated.json', payload(BASE))
    code, out, _ = cli(BASE, 'wiki', 'wiki_missing_quickstart', missing)
    check('成功形状的模拟回执不能越过缺少 quickstart 的检查', code == 2 and out['status'] == 'error',
          kind='明确模拟 Wiki 回执')
    wiki_fixture(BASE)
    bad = payload(BASE)
    bad['operation'] = 'openwiki_next_page'
    code, out, _ = cli(BASE, 'wiki', 'wiki_wrong_operation', write_input('wrong-operation-simulated.json', bad))
    check('next_page complete 不能替代 finish complete', code == 2 and out['status'] == 'error',
          kind='明确模拟 Wiki 回执')
    code, out, _ = cli(BASE, 'wiki', 'wiki_complete_structure_only', missing)
    check('合格模拟回执通过结构校验（不证明真实 Wiki 完成）', code == 0 and out['initialized']
          and out['ready_for_worktrees'], kind='明确模拟 Wiki 回执与文件')
    code, out, _ = cli(BASE, 'verify', 'verify_simulated_wiki_structure')
    check('结构就绪模拟项目 verify 为零（仅助手行为）', code == 0, kind='明确模拟 Wiki 回执与文件')
    source = BASE / 'src/app.py'
    original_source = source.read_bytes()
    source.write_bytes(original_source + '# 新增业务行为\n'.encode())
    code, out, _ = cli(BASE, 'status', 'source_drift')
    check('业务源码变化使既有 Wiki 结构回执失效', code == 0 and out['local_ready'] and not out['wiki_ready'],
          kind='真实源码变更 + 模拟既有 Wiki')
    source.write_bytes(original_source)
    agents = BASE / 'AGENTS.md'
    original_agents = agents.read_bytes()
    agents.write_bytes(original_agents + '用户添加的周边说明。\n'.encode())
    code, out, _ = cli(BASE, 'status', 'user_surrounding_edit')
    check('用户编辑 AGENTS 周边内容仍本地有效但要求 Wiki 再核查', code == 0 and out['local_ready']
          and not out['wiki_ready'], kind='真实用户指令变更 + 模拟既有 Wiki')
    code, out, _ = cli(BASE, 'instructions', 'preserve_surrounding_edit', prose)
    check('instructions 重试保留用户新增周边内容', code == 0 and agents.read_bytes().endswith('用户添加的周边说明。\n'.encode()))
    agents.write_bytes(original_agents.replace('本项目入口'.encode(), '用户已修改入口'.encode()))
    edited = agents.read_bytes()
    code, out, _ = cli(BASE, 'instructions', 'protect_modified_managed_block', prose)
    check('用户修改托管区块后拒绝覆盖并保留全部字节', code == 2 and agents.read_bytes() == edited)
    agents.write_bytes(original_agents)
    target = BASE / '.agents/skills/tdd/SKILL.md'
    old_tdd = target.read_bytes()
    target.write_bytes(old_tdd + '\n用户的自定义方法。\n'.encode())
    changed = target.read_bytes()
    code, out, _ = cli(BASE, 'prepare', 'upstream_user_conflict')
    check('上游同名技能用户变更被保留并报告冲突', code == 0 and out['phase'] == 'conflict'
          and out['conflicts'] and target.read_bytes() == changed)
    target.write_bytes(old_tdd)
    cli(BASE, 'prepare', 'clear_repaired_conflict')
    dependencies = BASE / '.workflow/dependencies.json'
    old_dependencies = dependencies.read_bytes()
    conflicting = json.loads(old_dependencies)
    conflicting['openwiki_skill'] = str(ROOT / 'external/other-openwiki/SKILL.md')
    dependencies.write_text(json.dumps(conflicting, ensure_ascii=False, indent=2) + '\n')
    changed_dependencies = dependencies.read_bytes()
    code, out, _ = cli(BASE, 'prepare', 'protect_dependency_conflict')
    check('已有关键依赖字段冲突拒绝覆盖用户配置', code == 2 and dependencies.read_bytes() == changed_dependencies)
    dependencies.write_bytes(old_dependencies)
    cli(BASE, 'prepare', 'restore_after_dependency_conflict')
    lock = BASE / '.workflow/.project-init.lock'
    with lock.open('a+b') as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        before_agents = agents.read_bytes()
        code, out, _ = cli(BASE, 'instructions', 'concurrent_writer_rejected', prose)
        check('存活初始化写入者持锁时拒绝另一个写入者', code == 2 and agents.read_bytes() == before_agents)
    unborn = seed('尚无Git基线', baseline=False)
    code, out, _ = cli(unborn, 'prepare', 'non_git_requires_explicit_init')
    check('非 Git 项目无 init-git 时不隐式建立仓库', code == 2 and not (unborn / '.git').exists())
    code, out, _ = cli(unborn, 'prepare', 'non_git_explicit_init', init_git=True)
    check('显式 init-git 建立仓库但不提交已有内容', code == 0 and out['needs_git_baseline'])
    cli(unborn, 'instructions', 'unborn_instructions', prose)
    wiki_fixture(unborn)
    code, out, _ = cli(unborn, 'wiki', 'unborn_simulated_wiki', write_input('unborn-wiki-simulated.json', payload(unborn)))
    check('无首个提交项目可结构接入但 worktree 不就绪', code == 0 and out['initialized'] and out['needs_git_baseline']
          and not out['ready_for_worktrees'], kind='真实 unborn Git + 明确模拟 Wiki')
    code, out, _ = cli(unborn, 'verify', 'unborn_verify')
    check('无 Git 基线时 verify 非零', code == 2 and not out['ready_for_worktrees'], kind='真实 unborn Git + 明确模拟 Wiki')
    nested = BASE / 'src'
    before = project_map(BASE)
    code, out, _ = cli(nested, 'status', 'nested_root_rejected')
    check('父仓库子目录不会被当作独立项目或创建嵌套仓库', code == 0 and not out['initialized']
          and project_map(BASE) == before and any('Git 顶层' in p for p in out['problems']))
    malformed = ROOT / 'projects/用户已有其他workflow记录'
    malformed.mkdir()
    (malformed / '.workflow').mkdir()
    malformed_file = malformed / '.workflow/project.json'
    malformed_file.write_text('[]\n')
    code, out, stderr = cli(malformed, 'status', 'valid_json_wrong_record_type')
    if out is None and 'AttributeError' in stderr:
        FINDINGS.append({'编号': 'INIT-JSON-01', '严重性': '低',
                         '问题': '已有 project.json 是合法 JSON 数组时，status 以 AttributeError 回溯崩溃，未返回约定的中文结构化错误。',
                         '文件': 'dl-init/scripts/project_init.py', '位置': 'Project.__init__；state.get 调用前未核对记录类型',
                         '复现': ['mkdir -p <隔离目录>/.workflow', '写入 [] 到 .workflow/project.json',
                                  'python3 <dl-init>/scripts/project_init.py status --root <隔离目录>'],
                         '实际': {'exit_code': code, 'stderr': stderr},
                         '影响': '用户已有其他工作流记录或损坏记录时，保护了原文件但恢复诊断不可消费；不属于数据覆盖。'})
    check('错误记录仍保留原用户字节', malformed_file.read_text() == '[]\n')
    save()


def save():
    snapshot = json.loads((ROOT / 'snapshot_manifest.json').read_text())
    drift = []
    for entry in snapshot['sources']:
        path = Path(entry['path'])
        current = digest(path.read_bytes()) if path.is_file() else None
        if current != entry['sha256']:
            drift.append({'path': entry['path'], 'tested_sha256': entry['sha256'],
                          'current_sha256': current, '需复验': True})
    receipt = {'验证者': '/root/init_forward_check', '完成时间UTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               '临时目录': str(ROOT), '结果': RESULTS, '发现': FINDINGS, '调用日志': CALLS,
               '测试快照清单': snapshot['sources'], '期间版本变化': drift,
               '测试边界': ['只在登记的隔离临时目录中执行；没有修改本包源码或当前业务目录。',
                            '真实 Git clone 和官方 skill-installer 项目级安装已经实测，固定 upstream SHA 为 ' + SPEC['revision'] + '。',
                            '后续项目使用来自真实固定 checkout 的本地 Git clone 与完整技能内容，未再造安装器。',
                            'Wiki 页、回执、Host 模型字段全部明确标记模拟；没有调用真实 OpenWiki、模型或 PR。',
                            '仅结构校验通过不能报告真实 Wiki 或模型完成。',
                            '没有读取生成者 test_*.py、验证回执或 harness-workflow；没有改全局配置。'],
               '结论': '真实项目级依赖安装、用户文件保护、重试与 Git 基线边界均已验证；完整 Wiki/模型接入未实测。'}
    (ROOT / 'independent_receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'结果数': len(RESULTS), '失败数': sum(not r['通过'] for r in RESULTS),
                      '发现数': len(FINDINGS), '版本变化数': len(drift), '回执': str(ROOT / 'independent_receipt.json')},
                     ensure_ascii=False), flush=True)


if __name__ == '__main__':
    try:
        main()
    except BaseException:
        save()
        raise
