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
        result = self.call()
        self.assertEqual(result.returncode, 124, result.stdout + '\nSTDERR:\n' + result.stderr)
    def test_tests_timeout_is_failure(self):
        self.env['REVIEW_IT_TIMEOUT'] = '1'
        result = self.call('--parallel-tests', 'sleep 30')
        self.assertEqual(result.returncode, 124, result.stdout + '\nSTDERR:\n' + result.stderr)
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


class PortableReviewHelperTests(ReviewHelperTests):
    """Run original regressions without GNU timeout/setsid anywhere on PATH."""
    def setUp(self):
        super().setUp()
        import shutil
        import sys
        self.tools = self.root / 'portable-bin'
        self.tools.mkdir()
        for command in ('bash', 'git', 'dirname', 'wc', 'tr', 'mktemp', 'cat', 'rm', 'cp', 'sleep'):
            source = shutil.which(command)
            self.assertIsNotNone(source, command)
            (self.tools / command).symlink_to(source)
        (self.tools / 'python3').symlink_to(sys.executable)
        self.env['PATH'] = str(self.bin) + os.pathsep + str(self.tools)
        self.assertIsNone(shutil.which('timeout', path=self.env['PATH']))
        self.assertIsNone(shutil.which('setsid', path=self.env['PATH']))

    def test_retained_branch_diff_without_gnu_utilities(self):
        def git(*args):
            subprocess.run(['git', *args], cwd=self.root, env=self.env, check=True, capture_output=True)
        (self.root / 'file.txt').write_text('base\n')
        git('add', 'file.txt')
        git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.test', 'commit', '-m', 'base')
        git('branch', '-M', 'main')
        git('checkout', '-b', 'feature')
        (self.root / 'file.txt').write_text('changed\n')
        git('add', 'file.txt')
        git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.test', 'commit', '-m', 'change')
        result = subprocess.run(['bash', str(HELPER), '--agent', 'claude', '--mode', 'branch', '--base', 'main'],
                                cwd=self.root, env=self.env, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 3, result.stderr)
        retained = next(line.split('retained review input: ')[1].split(' (remove')[0]
                        for line in result.stdout.splitlines() if 'retained review input:' in line)
        self.assertIn('+changed', (Path(retained) / 'review.diff').read_text())
        import shutil
        shutil.rmtree(retained)

    def test_timeout_stops_term_ignoring_descendant(self):
        import time
        child = self.root / 'child.py'
        heartbeat = self.root / 'heartbeat'
        pid_file = self.root / 'child.pid'
        child.write_text('import os,signal,time\nfrom pathlib import Path\n'
                         'signal.signal(signal.SIGTERM, signal.SIG_IGN)\n'
                         f'Path({str(pid_file)!r}).write_text(str(os.getpid()))\n'
                         'while True:\n'
                         f'    with open({str(heartbeat)!r}, "a") as f: f.write("tick\\n")\n'
                         '    time.sleep(0.02)\n')
        self.env['REVIEW_IT_TIMEOUT'] = '1'
        self.codex(f'python3 "{child}" &\nwait')
        result = self.call()
        self.assertEqual(result.returncode, 124, result.stdout + result.stderr)
        self.assertTrue(pid_file.exists())
        first = heartbeat.read_bytes()
        time.sleep(0.2)
        self.assertEqual(heartbeat.read_bytes(), first)
        pid = int(pid_file.read_text())
        state = subprocess.run(['ps', '-o', 'stat=', '-p', str(pid)], capture_output=True, text=True).stdout.strip()
        self.assertTrue(not state or state.startswith('Z'), state)

    def test_interrupt_stops_parallel_commands(self):
        import signal
        import time
        self.codex('sleep 30')
        process = subprocess.Popen(['bash', str(HELPER), '--agent', 'codex', '--mode', 'local',
                                    '--parallel-tests', 'sleep 30'], cwd=self.root, env=self.env,
                                   text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(0.2)
        process.send_signal(signal.SIGTERM)
        stdout, stderr = process.communicate(timeout=5)
        self.assertEqual(process.returncode, 143, stdout + stderr)

    def test_shell_kill_stops_owned_command(self):
        import signal
        import time
        heartbeat = self.root / 'parent-kill-heartbeat'
        child = self.root / 'parent-kill-child.py'
        child.write_text('import time\n'
                         'while True:\n'
                         f'    with open({str(heartbeat)!r}, "a") as f: f.write("tick\\n")\n'
                         '    time.sleep(0.02)\n')
        self.codex(f'python3 "{child}"')
        process = subprocess.Popen(['bash', str(HELPER), '--agent', 'codex', '--mode', 'local'],
                                   cwd=self.root, env=self.env, text=True,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        deadline = time.monotonic() + 3
        while not heartbeat.exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        self.assertTrue(heartbeat.exists())
        process.kill()
        process.communicate(timeout=3)
        time.sleep(0.5)
        first = heartbeat.read_bytes()
        time.sleep(0.2)
        self.assertEqual(heartbeat.read_bytes(), first)

if __name__ == '__main__': unittest.main()
