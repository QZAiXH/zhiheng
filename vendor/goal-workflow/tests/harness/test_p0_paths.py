"""Portable path-guard tests; virtual Darwin aliases do not alter system paths."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[2] / "skills/harness-init/assets/project"
sys.path.insert(0, str(PROJECT))
from harness.codex_probe import _canonical_artifact_path, _output_directory
from harness.state import Blocked


class P0ArtifactPathTests(unittest.TestCase):
    def virtual_alias(self, alias, target, *, inner_link=None, platform="darwin", target_exists=True):
        # A tiny virtual filesystem lets Linux test exact Darwin prefix behavior.
        links={Path(alias)}
        if inner_link is not None:links.add(Path(inner_link))
        expected={"/var":Path("/private/var"),"/tmp":Path("/private/tmp")}[alias]
        return (patch("harness.codex_probe.sys.platform",platform),
                patch.object(Path,"is_symlink",autospec=True,side_effect=lambda path:path in links),
                patch("harness.codex_probe.os.readlink",return_value=target),
                patch.object(Path,"is_dir",autospec=True,side_effect=lambda path:target_exists and path==expected))

    def test_verified_darwin_var_relative_target_is_canonicalized(self):
        contexts=self.virtual_alias('/var','private/var')
        with contexts[0],contexts[1],contexts[2],contexts[3]:
            self.assertEqual(_canonical_artifact_path('/var/folders/session/artifacts'),Path('/private/var/folders/session/artifacts'))

    def test_verified_darwin_tmp_absolute_target_is_canonicalized(self):
        contexts=self.virtual_alias('/tmp','/private/tmp')
        with contexts[0],contexts[1],contexts[2],contexts[3]:
            self.assertEqual(_canonical_artifact_path('/tmp/session/artifacts'),Path('/private/tmp/session/artifacts'))

    def test_darwin_inner_hostile_symlink_is_still_refused(self):
        contexts=self.virtual_alias('/var','private/var',inner_link='/private/var/folders/hostile')
        with contexts[0],contexts[1],contexts[2],contexts[3]:
            with self.assertRaisesRegex(Blocked,'Symlink'):
                _canonical_artifact_path('/var/folders/hostile/artifacts')

    def test_unexpected_system_alias_target_is_refused(self):
        for target in ('/attacker/var','private/tmp','/private/var/elsewhere'):
            with self.subTest(target=target):
                contexts=self.virtual_alias('/var',target)
                with contexts[0],contexts[1],contexts[2],contexts[3]:
                    with self.assertRaisesRegex(Blocked,'Unexpected'):
                        _canonical_artifact_path('/var/folders/artifacts')

    def test_expected_target_must_exist(self):
        contexts=self.virtual_alias('/tmp','private/tmp',target_exists=False)
        with contexts[0],contexts[1],contexts[2],contexts[3]:
            with self.assertRaises(Blocked):_canonical_artifact_path('/tmp/session/artifacts')

    def test_linux_does_not_whitelist_darwin_like_symlink(self):
        contexts=self.virtual_alias('/var','private/var',platform='linux')
        with contexts[0],contexts[1],contexts[2] as readlink,contexts[3]:
            with self.assertRaisesRegex(Blocked,'Symlink'):_canonical_artifact_path('/var/folders/artifacts')
            readlink.assert_not_called()

    def test_dotdot_rejected_before_system_alias_normalization(self):
        contexts=self.virtual_alias('/var','private/var')
        with contexts[0],contexts[1],contexts[2] as readlink,contexts[3]:
            with self.assertRaisesRegex(Blocked,'normalized'):_canonical_artifact_path('/var/folders/../artifacts')
            readlink.assert_not_called()

    def test_private_target_itself_cannot_be_a_symlink_chain(self):
        contexts=self.virtual_alias('/var','private/var',inner_link='/private/var')
        with contexts[0],contexts[1],contexts[2],contexts[3]:
            with self.assertRaisesRegex(Blocked,'Symlink'):_canonical_artifact_path('/var/folders/artifacts')

    def test_real_inner_symlink_and_escape_are_refused_without_creation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary).resolve()
            project=root/'project';project.mkdir()
            outside=root/'outside';outside.mkdir()
            link=root/'link';link.symlink_to(outside,target_is_directory=True)
            with self.assertRaises(Blocked):_output_directory(str(link/'artifacts'),project,None)
            self.assertFalse((outside/'artifacts').exists())

    def test_real_canonical_temp_output_stays_outside_user_project(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary).resolve()
            project=root/'project';project.mkdir()
            output=_output_directory(str(root/'artifacts'),project,None)
            self.assertTrue(output.is_dir())
            self.assertEqual(list(project.iterdir()),[])


if __name__=='__main__':unittest.main()
