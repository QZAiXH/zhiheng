"""Deterministic Darwin zombie-group and genuine permission failure regressions."""
import importlib.util
from pathlib import Path
import signal
import subprocess
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[2] / 'skills/review-it/scripts/bounded-run.py'
spec = importlib.util.spec_from_file_location('review_bounded', SCRIPT)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class ZombieGroupTests(unittest.TestCase):
    def ps(self, text):
        return subprocess.CompletedProcess([], 0, text, '')
    def test_eperm_zombie_only_is_verified_stopped(self):
        with patch.object(runner.os, 'killpg', side_effect=PermissionError(1, 'Operation not permitted')), \
             patch.object(runner.subprocess, 'run', return_value=self.ps('101 101 Z\n202 202 S\n')):
            self.assertFalse(runner.group_alive(101))
            runner.signal_group(101, signal.SIGKILL)
    def test_eperm_with_live_child_is_not_suppressed(self):
        with patch.object(runner.os, 'killpg', side_effect=PermissionError(1, 'Operation not permitted')), \
             patch.object(runner.subprocess, 'run', return_value=self.ps('101 101 Z\n102 101 S\n')):
            with self.assertRaises(PermissionError): runner.group_alive(101)
            with self.assertRaises(PermissionError): runner.signal_group(101, signal.SIGKILL)
    def test_failed_process_query_is_not_absence(self):
        with patch.object(runner.os, 'killpg', side_effect=PermissionError(1, 'Operation not permitted')), \
             patch.object(runner.subprocess, 'run', side_effect=subprocess.TimeoutExpired('ps', 2)):
            with self.assertRaises(subprocess.TimeoutExpired): runner.group_alive(101)
    def test_malformed_process_query_fails_closed(self):
        for text in ['', 'not a process row\n']:
            with self.subTest(text=text), patch.object(runner.subprocess, 'run', return_value=self.ps(text)):
                with self.assertRaises(RuntimeError): runner.live_group_members(101)

if __name__ == '__main__': unittest.main()
