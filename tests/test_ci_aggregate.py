"""Run only isolated reporting snippets; never invoke the harness test suite."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / '.github/workflows/harness-verify.yml'


def snippets():
    text = WORKFLOW.read_text()
    aggregate = text.split('  all_platforms:\n', 1)[1]
    require = aggregate.split('        run: |\n', 1)[1].split('      - name:', 1)[0]
    require = textwrap.dedent(require)
    code = aggregate.split("          python3 - <<'PYCODE'\n", 1)[1].split('          PYCODE', 1)[0]
    return text, require, textwrap.dedent(code)


class AggregateReportingTests(unittest.TestCase):
    def report(self, paused, independent):
        _, _, code = snippets()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scope = root / 'vendor/goal-workflow/docs/evidence/controller-commit-test-scope.json'
            scope.parent.mkdir(parents=True)
            scope.write_text(json.dumps({'paused_test_ids': paused, 'independent_security_review': independent}))
            summary = root / 'summary.md'
            result = subprocess.run([sys.executable, '-c', code], cwd=root,
                                    env={**os.environ, 'GITHUB_STEP_SUMMARY': str(summary)},
                                    capture_output=True, text=True, timeout=10)
            return result, summary.read_text() if summary.exists() else ''

    def test_deferred_review_warns_without_claiming_full_acceptance(self):
        result, summary = self.report(['ordinary-placeholder'] * 28, 'incomplete')
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn('::warning::28 cases deferred', result.stdout)
        self.assertNotIn('::error::', result.stdout)
        self.assertIn('do not establish full acceptance', summary)
        self.assertIn('does not mark deferred tests passed', summary)
        self.assertIn('All 15 ordinary platform checks remain required', summary)

    def test_incomplete_review_warns_even_without_deferred_list(self):
        result, summary = self.report([], 'incomplete')
        self.assertEqual(0, result.returncode)
        self.assertIn('::warning::', result.stdout)
        self.assertTrue(summary)

    def test_functional_failures_cannot_be_cleared_by_successful_warning_step(self):
        _, require, _ = snippets()
        for runtime, review in [('failure', 'success'), ('success', 'failure'),
                                ('cancelled', 'success'), ('success', 'skipped')]:
            with self.subTest(runtime=runtime, review=review):
                script = require.replace('${{ needs.runtime.result }}', runtime).replace('${{ needs.review_portability.result }}', review)
                failed = subprocess.run(['bash', '-c', script], capture_output=True, timeout=10)
                reporting, _ = self.report(['placeholder'], 'incomplete')
                self.assertNotEqual(0, failed.returncode)
                self.assertEqual(0, reporting.returncode)

    def test_successful_dependencies_pass_and_15_check_definitions_remain(self):
        text, require, _ = snippets()
        script = require.replace('${{ needs.runtime.result }}', 'success').replace('${{ needs.review_portability.result }}', 'success')
        self.assertEqual(0, subprocess.run(['bash', '-c', script], timeout=10).returncode)
        self.assertEqual(2, text.count('os: [ubuntu-latest, macos-latest, macos-15-intel]'))
        self.assertIn('suite: [core, local, github, knowledge]', text)
        self.assertIn('name: harness-${{ matrix.os }}-${{ matrix.suite }}', text)
        self.assertIn('needs: [runtime, review_portability]', text)
        self.assertNotIn('continue-on-error:', text)
        scope = json.loads((ROOT / 'vendor/goal-workflow/docs/evidence/controller-commit-test-scope.json').read_text())
        self.assertEqual(28, len(scope['paused_test_ids']))
