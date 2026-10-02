"""Independent local/bare transport checks; no external service calls."""
import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_source_push as fixtures
from harness.state import Blocked


class SourceTransportAudit(unittest.TestCase):
    setUp = fixtures.SourcePushTests.setUp
    commit = fixtures.SourcePushTests.commit
    controller = fixtures.SourcePushTests.controller
    push = fixtures.SourcePushTests.push
    actual = fixtures.SourcePushTests.actual

    def test_named_remote_policy_in_original_hook_is_not_bypassed(self):
        hook = self.root / ".git/hooks/pre-push"
        hook.write_text('#!/bin/sh\nprintf "%s" "$1" > hook-remote-name\n'
                        'if [ "$1" = "origin" ]; then exit 1; fi\nexit 0\n')
        hook.chmod(0o700)
        with self.controller() as controller:
            refusal = None
            try:
                self.push(controller)
            except Blocked as exc:
                refusal = exc
        self.assertTrue((self.root / "hook-remote-name").is_file(), "transport stopped before original hook: " + str(refusal))
        self.assertEqual((self.root / "hook-remote-name").read_text(), "origin")
        self.assertIsNotNone(refusal)
        self.assertIsNone(self.actual(), "original named-remote hook policy was bypassed")


if __name__ == "__main__":
    unittest.main(verbosity=2)
