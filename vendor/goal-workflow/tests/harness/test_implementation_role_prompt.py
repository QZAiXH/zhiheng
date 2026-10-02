"""Pure prompt/routing checks; no host, Controller or subprocess execution."""
import ast
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / 'skills/harness-init/assets/project/harness/workflow.py'


class ImplementationRolePrompt(unittest.TestCase):
    def prompt(self, mode):
        function = next(node for node in ast.parse(WORKFLOW.read_text()).body
                        if isinstance(node, ast.FunctionDef) and node.name == 'implement_task')
        scope = {'mode': mode, 'task': {'id': 'fixture', 'allowed_paths': ['business.py']},
                 'json': json, 'spec': 'fixture spec', 'feedback': ''}
        for name in ('commit_instruction', 'prompt'):
            assignment = next(node for node in function.body if isinstance(node, ast.Assign)
                              and any(isinstance(target, ast.Name) and target.id == name for target in node.targets))
            scope[name] = eval(compile(ast.Expression(assignment.value), '<prompt-only>', 'eval'), scope)
        return scope['prompt']

    def test_controller_worker_edits_tests_and_returns_without_outer_dispatch(self):
        text = self.prompt('controller_commit')
        for required in ('already dispatched by the outer Controller', 'do not invoke run/probe',
                         'create another worktree', 'independent business review',
                         'finish promptly with a concise implementation report',
                         'walkthrough/knowledge candidates in that report',
                         'allowed_paths in controller_commit mode', 'Do not stage or commit'):
            self.assertIn(required, text)
        self.assertNotIn('Commit your changes on the current branch', text)
        self.assertIn('fixture spec', text)
        self.assertIn('business.py', text)

    def test_model_commit_keeps_explicit_existing_commit_responsibility(self):
        text = self.prompt('model_commit')
        self.assertIn('Commit your changes on the current branch when implementation is ready.', text)
        self.assertIn('do not invoke run/probe', text)
        self.assertNotIn('Do not stage or commit', text)

    def test_loop_worker_branch_precedes_outer_controller_route(self):
        text = (ROOT / 'skills/loop-it/SKILL.md').read_text()
        self.assertLess(text.index('先识别当前角色'), text.index('外层必须经已安装的 Harness 控制入口运行'))
        self.assertIn('此执行者分支到此返回', text)
        self.assertIn('`model_commit` 仍按外层明确的原有提交职责处理', text)

    def test_source_exists_message_does_not_offer_nonexistent_resume(self):
        text = WORKFLOW.read_text()
        self.assertNotIn('source branch exists; use explicit resume', text)
        self.assertIn('No automatic dirty-implementation resume entry exists', text)
        self.assertIn('recover only verifies stopped execution', text)
        self.assertIn('Do not delete the branch or reset budgets to retry', text)
        function = text[text.index('def implement_task('):text.index('def repair_task(')]
        self.assertLess(function.index('raise Blocked("implementation failed; worktree and raw logs preserved")'),
                        function.index('commit_receipt = _finish_controlled_commit'))
