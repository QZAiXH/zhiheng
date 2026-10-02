#!/usr/bin/env python3
"""Install the zh public entrypoints and their pinned, reversible harness dependencies."""
import argparse
import importlib.util
import json
from pathlib import Path
import tempfile

ROOT=Path(__file__).resolve().parents[1]
ZH=('zh','zh-context','zh-plan','zh-implement','zh-debug','zh-review','zh-finish')


def engine(root):
    source=root/'vendor/goal-workflow/scripts/install-codex-skills.py'
    spec=importlib.util.spec_from_file_location('zh_harness_installer',source)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def install(destination, action='install', selection='all', source=ROOT, dry_run=False):
    source=Path(source).resolve();module=engine(source)
    components=tuple(module.CHAIN)
    requested=selection.split(',') if selection!='all' else list(ZH+components)
    if len(requested)!=len(set(requested)) or any(n not in ZH+components for n in requested):
        raise ValueError('Unknown/duplicate skill selection')
    # zh skills mutually link their references and route the enhanced chain.
    names=list(ZH+components) if any(n in ZH for n in requested) else list(requested)
    if any(n!='harness-init' for n in names) and not any(n in ZH for n in names) and 'harness-init' not in names:
        names.insert(0,'harness-init')
    if dry_run:
        return {'status':'preview','destination':str(Path(destination).expanduser()/'.agents/skills'),
                'skills':names,'action':action,'notice':'No target changes; existing unmanaged same-name skills are preserved and require explicit migration'}
    if action=='rollback':
        return module.install(Path(destination).expanduser(),source,action=action)
    with tempfile.TemporaryDirectory(prefix='zh-harness-package-') as temp:
        stage=Path(temp);(stage/'skills').mkdir()
        own=[n for n in names if n in ZH]
        dependency=[n for n in names if n in components]
        if own:
            files=module.tree_files(source,own,packaged=True)
            module.copy_manifest_files(source,stage/'skills',files)
        if dependency:
            package=source/'vendor/goal-workflow/skills'
            files=module.tree_files(package,dependency,packaged=True)
            module.copy_manifest_files(package,stage/'skills',files)
        return module.install(Path(destination).expanduser(),stage,action=action,skills=names)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination',required=True,type=Path,help='Existing project directory, or your home for user-level installation')
    parser.add_argument('--action',choices=('install','upgrade','rollback'),default='install')
    parser.add_argument('--skills',default='all',help='all (17 components), harness-init, or a comma-separated subset; any zh entry includes the full chain')
    parser.add_argument('--dry-run',action='store_true')
    args=parser.parse_args()
    try:
        result=install(args.destination,args.action,args.skills,dry_run=args.dry_run)
    except (OSError,ValueError,RuntimeError) as exc:
        print(json.dumps({'status':'blocked','reason':str(exc)},ensure_ascii=False,indent=2));return 2
    print(json.dumps(result,ensure_ascii=False,indent=2));return 0

if __name__=='__main__':raise SystemExit(main())
