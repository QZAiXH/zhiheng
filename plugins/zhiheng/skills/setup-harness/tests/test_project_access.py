import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import project_access as access


class ProjectAccessTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        self.folder = Path(self.scratch.name)
        self.config = self.folder / 'ov.conf'
        self.config.write_text(json.dumps({'server': {'host': '127.0.0.1', 'port': 1933,
                                                      'root_api_key': 'admin-test', 'auth_mode': 'api_key'}}))
        self.key_file = self.folder / 'keys' / 'project.key'
        self.args = ['provision', '--config', str(self.config), '--account', 'orchard',
                     '--key-file', str(self.key_file)]
        self.health = {'account_id': 'orchard', 'user_id': 'codex', 'role': 'user', 'auth_mode': 'api_key'}

    def provision(self, *extra):
        with patch.object(sys, 'argv', ['project_access.py', *self.args, *extra]), contextlib.redirect_stdout(io.StringIO()):
            access.main()

    def mcp_headers(self):
        return subprocess.run([sys.executable, '-B', access.__file__, 'mcp-headers',
                               '--key-file', str(self.key_file)], capture_output=True, text=True)

    def test_mcp_headers_load_project_key_from_private_file(self):
        self.key_file.parent.mkdir()
        access.save_key(self.key_file, 'ordinary-test')

        result = self.mcp_headers()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {'Authorization': 'Bearer ordinary-test'})

    def test_mcp_headers_reject_invalid_key_file_without_echoing_secret(self):
        self.key_file.parent.mkdir()
        marker = 'PRIVATE-TEST-FRAGMENT'
        for mode, key, message in ((0o644, marker, 'private regular key file'),
                                   (0o600, f'first\n{marker}', 'single API key')):
            with self.subTest(mode=oct(mode)):
                access.save_key(self.key_file, key)
                self.key_file.chmod(mode)

                result = self.mcp_headers()

                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, '')
                self.assertIn(message, result.stderr)
                self.assertNotIn(marker, result.stderr)

    def test_existing_key_needs_only_the_ordinary_health_check(self):
        self.key_file.parent.mkdir()
        access.save_key(self.key_file, 'ordinary-test')
        inode = self.key_file.stat().st_ino
        with patch.object(access, 'request', return_value=self.health) as call:
            self.provision('--rotate-lost-key')
        call.assert_called_once_with('http://127.0.0.1:1933/health', 'ordinary-test')
        self.assertEqual(self.key_file.stat().st_ino, inode)

    def test_account_created_before_interruption_resumes_at_missing_user(self):
        missing = HTTPError('http://example.test', 404, 'Missing', {}, None)
        replies = [{'result': {'account_id': 'orchard'}}, missing, {'result': {'user_key': 'issued'}}, self.health]
        with patch.object(access, 'request', side_effect=replies) as call:
            self.provision()
        self.assertEqual([c.args[2] for c in call.call_args_list if len(c.args) == 3],
                         [{'user_id': 'codex', 'role': 'user'}])
        self.assertEqual(access.read_key(self.key_file), 'issued')
        self.assertEqual(self.key_file.stat().st_mode & 0o777, 0o600)

    def test_missing_receipt_preserves_existing_membership_and_credential(self):
        replies = [{'result': {}}, {'result': {'user_id': 'codex', 'role': 'user'}}]
        with patch.object(access, 'request', side_effect=replies) as call, self.assertRaisesRegex(ValueError, 'already exists'):
            self.provision()
        self.assertTrue(all(len(c.args) == 2 for c in call.call_args_list))
        self.assertFalse(self.key_file.exists())

    def test_wrong_identity_cannot_be_overwritten_by_recovery(self):
        self.key_file.parent.mkdir()
        access.save_key(self.key_file, 'from-another-account')
        with patch.object(access, 'request', return_value={**self.health, 'account_id': 'other'}) as call:
            with self.assertRaisesRegex(ValueError, 'ordinary user'):
                self.provision('--rotate-lost-key')
        self.assertEqual(call.call_count, 1)
        self.assertEqual(access.read_key(self.key_file), 'from-another-account')

    def test_malformed_credential_stays_out_of_diagnostics(self):
        marker = 'PRIVATE-TEST-FRAGMENT'
        env = {**os.environ, 'HARNESS_TEST_KEY': f'first\n{marker}'}
        run = subprocess.run([sys.executable, '-B', access.__file__, 'verify', '--url', 'http://127.0.0.1:1',
                              '--account', 'orchard', '--key-env', 'HARNESS_TEST_KEY'],
                             env=env, capture_output=True, text=True)
        self.assertNotEqual(run.returncode, 0)
        self.assertNotIn(marker, run.stdout + run.stderr)


if __name__ == '__main__':
    unittest.main()
