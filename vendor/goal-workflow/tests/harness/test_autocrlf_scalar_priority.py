"""Pure data tests for one scalar selector; never execute the inspection script."""
import ast
from pathlib import Path
import unittest

SOURCE = (Path(__file__).resolve().parents[2] /
          'skills/harness-init/assets/project/harness/controller_commit.py')


def selector():
    outer = ast.parse(SOURCE.read_text())
    inspection = next(ast.literal_eval(node.value) for node in outer.body
                      if isinstance(node, ast.Assign)
                      and any(isinstance(target, ast.Name) and target.id == '_INSPECT'
                              for target in node.targets))
    body = ast.parse(inspection)
    function = next(node for node in body.body
                    if isinstance(node, ast.FunctionDef) and node.name == 'autocrlf_disabled')
    # Compile only this data selector. Imports, subprocesses, policy_check and
    # the inspection's outer try block are not included or executed.
    module = ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[]))
    namespace = {'__builtins__': {'next': next, 'reversed': reversed}}
    exec(compile(module, '<isolated-autocrlf-selector>', 'exec'), namespace)
    return namespace['autocrlf_disabled']


class AutocrlfScalarPriority(unittest.TestCase):
    def setUp(self):
        self.disabled = selector()

    def test_global_input_then_local_false(self):
        rows = [('core.autocrlf', 'input'), ('user.name', 'Fixture'), ('core.autocrlf', 'false')]
        original = list(rows)
        self.assertTrue(self.disabled(rows))
        self.assertEqual(original, rows, 'all source rows remain intact for fingerprinting')

    def test_final_input_overrides_earlier_false(self):
        self.assertFalse(self.disabled([('core.autocrlf', 'false'), ('core.autocrlf', 'input')]))

    def test_same_source_duplicates_use_last_value(self):
        self.assertTrue(self.disabled([('core.autocrlf', 'true'), ('core.autocrlf', 'false')]))
        self.assertFalse(self.disabled([('core.autocrlf', 'false'), ('core.autocrlf', 'true')]))

    def test_absent_key_defaults_to_disabled(self):
        self.assertTrue(self.disabled([]))
        self.assertTrue(self.disabled([('user.name', 'Fixture')]))

    def test_four_false_spellings_and_case(self):
        for value in ('false', 'no', 'off', '0', 'FALSE', 'No', 'oFf'):
            with self.subTest(value=value):
                self.assertTrue(self.disabled([('core.autocrlf', value)]))

    def test_effective_conversion_empty_unknown_values_refused(self):
        for value in ('input', 'INPUT', 'true', 'TRUE', 'yes', 'on', '1', '', 'unknown', ' false '):
            with self.subTest(value=value):
                self.assertFalse(self.disabled([('core.autocrlf', value)]))
