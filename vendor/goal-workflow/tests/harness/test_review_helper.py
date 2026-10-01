"""Execute the upstream helper with deterministic CLI subprocess fixtures."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

HELPER = Path(__file__).resolve().parents[2] / 'skills/review-it/scripts/review-it'

class ReviewHelperTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        self.env = dict(os.environ, PATH=str(self.bin) + ':' + os.environ['PATH'])
        self.codex('exit 0')
    def tearDown(self): self.tmp.cleanup()
    def codex(self, body):
        path = self.bin / 'codex'
        path.write_text('#!/bin/bash\n' + body + '\n')
        path.chmod(0o755)
    def call(self, *args):
        return subprocess.run(['bash', str(HELPER), '--agent', 'codex', '--mode', 'local', *args], cwd=self.root,
                              env=self.env, text=True, capture_output=True, timeout=12)
    def test_nonzero_tests_preserved(self):
        r = self.call('--parallel-tests', 'echo failed-original; exit 17')
        self.assertEqual(r.returncode, 17, r.stdout + r.stderr)
        self.assertIn('failed-original', r.stdout)
    def test_review_failure_preserved(self):
        self.codex('exit 19')
        self.assertEqual(self.call().returncode, 19)
    def test_codex_actual_flags_and_output(self):
        output = self.root / 'review.txt'
        self.env['CC_REVIEW_OUTPUT'] = str(output)
        self.codex('printf "%s\\n" "$*"')
        r = self.call()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(output.read_text().strip(), 'review --uncommitted')
        self.assertNotIn('review clean', r.stdout)
    def test_review_timeout_is_failure(self):
        self.env['REVIEW_IT_TIMEOUT'] = '1'
        self.codex('sleep 30')
        self.assertEqual(self.call().returncode, 124)
    def test_tests_timeout_is_failure(self):
        self.env['REVIEW_IT_TIMEOUT'] = '1'
        self.assertEqual(self.call('--parallel-tests', 'sleep 30').returncode, 124)
    def test_slash_host_explicit_pending_not_success(self):
        r = subprocess.run(['bash', str(HELPER), '--agent', 'claude', '--mode', 'local'], cwd=self.root,
                           env=self.env, text=True, capture_output=True)
        self.assertEqual(r.returncode, 3)
        self.assertIn('external review pending', r.stdout)
        # This handoff has no diff; dispose the retained test artifact.
        for line in r.stdout.splitlines():
            if 'retained review input:' in line:
                import shutil
                shutil.rmtree(line.split('retained review input: ')[1].split(' (remove')[0])

if __name__ == '__main__': unittest.main()
