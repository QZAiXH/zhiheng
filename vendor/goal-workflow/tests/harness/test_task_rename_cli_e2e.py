"""A23 ordinary rename continuation: real CLI/Git/Serena, simulated host/review.

This resumes validation of an already committed, verified source. It does not
exercise dirty implementation recovery or Controller commit recovery.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
import test_cli_e2e as fixture


@unittest.skipUnless(fixture.SERENA and fixture.SERENA_PYTHON and fixture.GIT,
                     'Explicit pinned Serena and Git required')
class TaskRenameCLI(unittest.TestCase):
    setUp = fixture.CliE2E.setUp
    git = fixture.CliE2E.git
    task = fixture.CliE2E.task
    save_bundle = fixture.CliE2E.save_bundle
    state = fixture.CliE2E.state
    deliver_and_close = fixture.CliE2E.deliver_and_close

    def cli(self, command, *args, okay=True):
        if command != 'tasks':
            return fixture.CliE2E.cli(self, command, *args, okay=okay)
        result = subprocess.run([sys.executable, '-m', 'harness.cli', 'tasks', '--bundle', str(self.bundle_path)],
                                env=self.env, capture_output=True, text=True, timeout=90)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def test_task_file_rename_revalidates_same_source_and_delivers(self):
        original = self.repo / 'work/01-tiny.md'
        original.parent.mkdir()
        original.write_text('''# Tiny addition

## Task ID
tiny

## Description
Implement addition of two numbers.

## Demo path
add(2, 3) returns 5.

## Acceptance Criteria
- [ ] [AC-tiny] Addition works for positive and negative numbers.

## Blocked by
None

## SPEC Reference
docs/spec.md
''')
        self.git('add', 'work/01-tiny.md')
        self.git('-c', 'maintenance.auto=false', '-c', 'gc.auto=0', 'commit', '--quiet', '-m', 'fixture task input')
        task = self.task('tiny')
        self.bundle['config']['task_directories'] = ['work']
        self.bundle['config']['report_mapping'] = {'tiny': task['reports']}
        self.bundle_path.write_text(json.dumps(self.bundle))
        parsed = self.cli('tasks')[0]
        task.update(parsed)
        self.save_bundle([task])
        self.assertEqual('handoff', self.cli('run', '--attempt', 'before-rename', '--implement')['status'])
        initial = self.state()
        old_evidence = json.loads(Path(initial['tasks']['tiny']['evidence']).read_text())
        self.assertEqual('verified', initial['tasks']['tiny']['status'])
        implementation_attempts = [row['attempt_id'] for row in initial['attempts']
                                   if row['attempt_id'].endswith('-implementation')]
        self.assertEqual(1, len(implementation_attempts))

        self.git('mv', 'work/01-tiny.md', 'work/renamed-tiny.md')
        self.git('-c', 'maintenance.auto=false', '-c', 'gc.auto=0', 'commit', '--quiet', '-m', 'rename task file only')
        target_after_rename = self.git('rev-parse', 'main')
        renamed = self.cli('tasks')[0]
        for key in ('id', 'source_sha256', 'content', 'reports', 'acceptance_ids'):
            self.assertEqual(parsed[key], renamed[key], key)
        self.assertNotEqual(parsed['source_file'], renamed['source_file'])
        task.update(renamed)
        self.bundle['tasks'] = [task]
        self.bundle_path.write_text(json.dumps(self.bundle))
        refused = self.cli('deliver', '--task', 'tiny', '--target-worktree', str(self.repo),
                           '--authorize', '--simulation', okay=False)
        self.assertEqual(target_after_rename, self.git('rev-parse', 'main'))
        self.assertIn("task requirements changed after verification", refused.stderr)
        self.assertTrue(self.cli('approve-contract', '--task', 'tiny', '--authorize'))
        self.cli('validate', '--task', 'tiny', '--attempt', 'after-rename')
        saved = self.state()
        new_evidence = json.loads(Path(saved['tasks']['tiny']['evidence']).read_text())
        self.assertEqual('verified', saved['tasks']['tiny']['status'])
        self.assertEqual(old_evidence['H'], new_evidence['H'])
        self.assertNotEqual(old_evidence['T'], new_evidence['T'])
        self.assertNotEqual(old_evidence['C'], new_evidence['C'])
        self.assertEqual(target_after_rename, new_evidence['T'])
        self.assertEqual(implementation_attempts, [row['attempt_id'] for row in saved['attempts']
                                                if row['attempt_id'].endswith('-implementation')])
        result = json.loads(Path(saved['tasks']['tiny']['evidence']).with_name('result.json').read_text())
        self.assertTrue(result['review']['independent'])
        self.assertTrue(all(row['status'] == 'passed' and row['tests'] > 0 for row in new_evidence['checks']))
        self.assertNotEqual(old_evidence['review']['record']['attempt_id'], new_evidence['review']['record']['attempt_id'])
        self.deliver_and_close('tiny')
        final = self.state()
        self.assertEqual(['tiny'], list(final['tasks']))
        self.assertEqual('completed', final['tasks']['tiny']['status'])
        self.assertFalse(original.exists())
        self.assertTrue((self.repo / renamed['source_file']).is_file())
        for report in task['reports'].values():
            self.assertTrue((self.repo / report).is_file())
        self.assertEqual('', self.git('remote'))
        self.assertEqual('completed', self.cli('run', '--attempt', 'after-closeout')['status'])
        directory = os.environ.get('HARNESS_RENAME_EVIDENCE_DIR')
        if directory:
            destination = Path(directory)
            destination.mkdir(parents=True, exist_ok=True)
            (destination / 'summary.json').write_text(json.dumps({
                'scenario': 'A23 committed-source task-file rename continuation',
                'tier': 'real CLI/Git/Serena; simulated host and independent review',
                'original_source_file': parsed['source_file'], 'renamed_source_file': renamed['source_file'],
                'stable_id': task['id'], 'reports': task['reports'],
                'old': {key: old_evidence[key] for key in ('H', 'T', 'C')},
                'new': {key: new_evidence[key] for key in ('H', 'T', 'C')},
                'D': final['tasks']['tiny']['D'], 'status': final['tasks']['tiny']['status'],
                'implementation_attempts': implementation_attempts,
                'old_evidence_refusal': refused.stderr.strip(),
                'actual_model_calls': 0, 'network_calls': 0,
            }, indent=2) + '\n')
