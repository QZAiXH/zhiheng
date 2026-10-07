#!/usr/bin/env python3
"""在本地与 CI 运行同一套回归；四组互不重复并覆盖全部案例。"""

import argparse
import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
GROUPS = ("core", "local", "github", "knowledge")


def load(relative, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def partition():
    state = load(".agents/skills/double-loop/scripts/test_workflow_state.py", "state_regression")
    onboarding = load(".agents/skills/dl-init/scripts/test_project_init.py", "onboarding_regression")
    loader = unittest.TestLoader()
    groups = {name: [] for name in GROUPS}
    for cls, fixed in ((state.ConfigTests, "core"), (onboarding.OnboardingTests, "local"), (state.RunTests, None)):
        for name in loader.getTestCaseNames(cls):
            case = cls(name)
            # 知识与删除边界独立成组，其余研发状态与交付记录归 github。
            group = fixed or ("knowledge" if any(word in name for word in (
                "cleanup", "knowledge", "draft", "stable_target", "reference", "document_symlink", "interrupted_delete"
            )) else "github")
            groups[group].append(case)
    ids = [case.id() for cases in groups.values() for case in cases]
    expected = sum(loader.loadTestsFromTestCase(cls).countTestCases()
                   for cls in (state.ConfigTests, onboarding.OnboardingTests, state.RunTests))
    if len(set(ids)) != len(ids) or len(ids) != expected or any(not group for group in groups.values()):
        raise ValueError("回归分组未完整覆盖测试，或存在重复/空组。")
    return groups


def main():
    parser = argparse.ArgumentParser(description="执衡回归入口")
    parser.add_argument("--group", choices=(*GROUPS, "all"), default="all")
    parser.add_argument("--list", action="store_true", help="只列出各组案例数量")
    args = parser.parse_args()
    groups = partition()
    if args.list:
        for name, cases in groups.items():
            print(f"{name}: {len(cases)}")
        print(f"all: {sum(map(len, groups.values()))}")
        return 0
    cases = [case for name, group in groups.items() if args.group in {name, "all"} for case in group]
    result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(cases))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
