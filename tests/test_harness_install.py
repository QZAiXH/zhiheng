import importlib.util
from pathlib import Path
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('install_harness',ROOT/'tools/install-harness.py')
installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)

class IntegratedInstallTests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.target=Path(self.temp.name)
    def test_all_17_with_zh_public_entry(self):
        result=installer.install(self.target)
        self.assertEqual(17,len(result['skills']))
        root=self.target/'.agents/skills'
        for name in ('zh','zh-context','harness-init','loop-it','ship-it'):
            self.assertTrue((root/name/'SKILL.md').is_file())
        self.assertTrue((root/'zh/references/harness-integration.md').is_file())
        self.assertTrue((root/'harness-init/assets/project/uv.lock').is_file())
    def test_validator_rejects_missing_harness_dependency(self):
        installer.install(self.target)
        import shutil
        spec=importlib.util.spec_from_file_location('validate_zh',ROOT/'tools/validate.py')
        validator=importlib.util.module_from_spec(spec);spec.loader.exec_module(validator)
        installed=self.target/'.agents/skills'
        self.assertEqual([],validator.validate(installed))
        shutil.rmtree(installed/'harness-init')
        self.assertTrue(any('missing enhanced dependency' in error for error in validator.validate(installed)))

    def test_selective_init_is_self_contained(self):
        result=installer.install(self.target,selection='harness-init')
        self.assertEqual(['harness-init'],result['skills'])
        self.assertFalse((self.target/'.agents/skills/zh').exists())
    def test_existing_zh_is_preserved(self):
        skill=self.target/'.agents/skills/zh';skill.mkdir(parents=True);(skill/'SKILL.md').write_text('user version')
        with self.assertRaises(RuntimeError):installer.install(self.target)
        self.assertEqual('user version',(skill/'SKILL.md').read_text())
    def test_preview_does_not_write(self):
        result=installer.install(self.target,dry_run=True)
        self.assertEqual('preview',result['status']);self.assertFalse((self.target/'.agents').exists())
    def test_upgrade_rollback(self):
        first=installer.install(self.target)
        second=installer.install(self.target,action='upgrade')
        restored=installer.install(self.target,action='rollback')
        self.assertNotEqual(first['generation'],second['generation'])
        self.assertEqual(first['generation'],restored['generation'])

if __name__=='__main__':unittest.main()
