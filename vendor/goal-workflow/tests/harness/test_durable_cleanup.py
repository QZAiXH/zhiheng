"""Real native/Git boundary tests. These do not claim Codex semantic onboarding."""
import os
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from harness.knowledge import SerenaAdapter, verify_durable_evidence
from harness.state import Blocked

SERENA=os.environ.get('HARNESS_TEST_SERENA')
PYTHON=os.environ.get('HARNESS_TEST_SERENA_PYTHON')

@unittest.skipUnless(SERENA and PYTHON, 'native pinned Serena environment required')
class DurableCleanupTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='durable-cleanup-');self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/'repo';self.root.mkdir()
        self.git('init','-q')
        (self.root/'README.md').write_text('# Sample\nRun python -m unittest.\n')
        for name,content in [('docs/decisions/0001-format.md','# MADR decision\nStatus: accepted\nUse text because this fixture is text-only.\n'),('tasks/walkthrough-cleanup.md','# Evidence\nInput: README. Result: text-only fixture.\n')]:
            p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(content)
        self.git('add','.');self.commit('durable task evidence')
        self.adapter=SerenaAdapter(self.root,SERENA,Path(self.tmp.name)/'home',python_executable=PYTHON)
        self.adapter.create_project(['python']);self.adapter.initialize_maintenance()
    def git(self,*args):
        return subprocess.run(['git','-C',str(self.root),*args],check=True,capture_output=True,text=True).stdout.strip()
    def commit(self,msg):
        self.git('-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm',msg)
    def test_cleanup_then_clean_clone_keeps_native_knowledge_and_sources(self):
        evidence=['README.md','docs/decisions/0001-format.md','tasks/walkthrough-cleanup.md']
        core='# Core\nCommands: python -m unittest.\nSources: [README](README.md), [decision](docs/decisions/0001-format.md), [walkthrough](tasks/walkthrough-cleanup.md).\n'
        self.adapter.write_new_memory('core',core,evidence)
        self.git('add','.serena/project.yml','.serena/memories');self.commit('knowledge and sources')
        expected={name:(self.root/name).read_bytes() for name in evidence+['.serena/memories/core.md','.serena/project.yml']}
        for d in ['.harness/runs/one','expired-ci-artifacts']:
            path=self.root/d;path.mkdir(parents=True);(path/'log.txt').write_text('temporary evidence to expire')
        shutil.rmtree(self.root/'.harness/runs');shutil.rmtree(self.root/'expired-ci-artifacts')
        copied=Path(self.tmp.name)/'clean-copy'
        subprocess.run(['git','clone','--quiet','--no-local',str(self.root),str(copied)],check=True,capture_output=True)
        self.assertFalse((copied/'.harness/runs').exists())
        fresh=SerenaAdapter(copied,SERENA,Path(self.tmp.name)/'fresh-home',python_executable=PYTHON)
        registered=fresh.register_existing();self.assertTrue(registered['registered'])
        self.assertEqual(core.rstrip('\n'),fresh.read_core()['content'].rstrip('\n'))
        self.assertTrue(fresh.check_references()['clean'])
        for name,content in expected.items():self.assertEqual(content,(copied/name).read_bytes())
        self.assertEqual(len(evidence),len(verify_durable_evidence(copied,evidence)))
        self.assertFalse(registered['onboarding_completed'])
        (copied/'docs/decisions/0001-format.md').unlink()
        with self.assertRaises(Blocked):verify_durable_evidence(copied,evidence)
    def test_native_rename_propagates_mem_reference(self):
        self.adapter.write_new_memory('module','# Module\nSee README.md.\n',['README.md'])
        self.adapter.write_new_memory('core','# Core\nRead `mem:module` for context.\n',['README.md'])
        # Exercise the pinned upstream CLI itself in this isolated disposable repo.
        # Does not claim automatic semantic approval or adapter edit support.
        output=self.adapter._native('memories','rename','module','renamed',str(self.root))
        self.assertIn('reference',output)
        self.assertFalse((self.root/'.serena/memories/module.md').exists())
        self.assertTrue((self.root/'.serena/memories/renamed.md').exists())
        self.assertIn('mem:renamed',self.adapter.read_core()['content'])
        self.assertTrue(self.adapter.check_references()['clean'])

    def test_guarded_native_edit_and_rename_preserve_neighbors(self):
        original='# Module\nSee README.\n'
        self.adapter.write_new_memory('module',original,['README.md'])
        self.adapter.write_new_memory('core','# Core\nRead `mem:module`.\n',['README.md'])
        self.adapter.write_new_memory('unrelated','# Unrelated\nMust stay byte-identical.\n',['README.md'])
        untouched=(self.root/'.serena/memories/unrelated.md').read_bytes()
        replacement='# Module\nRevised using README evidence.\n'
        digest=lambda data:hashlib.sha256(data).hexdigest()
        updated=self.adapter.update_memory('module',replacement,['README.md'],digest(original.encode()))
        self.assertTrue(updated['updated'])
        with self.assertRaises(Blocked):
            self.adapter.update_memory('module','stale write',['README.md'],digest(original.encode()))
        moved=self.adapter.rename_memory('module','updated-module',['README.md'],digest(replacement.encode()))
        self.assertTrue(moved['renamed']);self.assertEqual(1,moved['updated_references'])
        self.assertIn('mem:updated-module',self.adapter.read_core()['content'])
        self.assertEqual(untouched,(self.root/'.serena/memories/unrelated.md').read_bytes())
        self.assertTrue(self.adapter.check_references()['clean'])
    def test_native_tool_readonly_boundary_is_respected(self):
        content='# Protected core\n'
        self.adapter.write_new_memory('core',content,['README.md'])
        config=self.root/'.serena/project.yml'
        text=config.read_text()
        self.assertIn('read_only_memory_patterns: []',text)
        config.write_text(text.replace('read_only_memory_patterns: []', 'read_only_memory_patterns: ["core"]'))
        before=(self.root/'.serena/memories/core.md').read_bytes()
        sha=hashlib.sha256(before).hexdigest()
        with self.assertRaisesRegex(Blocked,'read-only'):
            self.adapter.update_memory('core','attempted replacement',['README.md'],sha)
        with self.assertRaisesRegex(Blocked,'read-only'):
            self.adapter.rename_memory('core','renamed-core',['README.md'],sha)
        self.assertEqual(before,(self.root/'.serena/memories/core.md').read_bytes())
        self.assertFalse((self.root/'.serena/memories/renamed-core.md').exists())

    def test_managed_project_refuses_unsupervised_native_call(self):
        config=self.root/'.harness/config.json';config.parent.mkdir();config.write_text('{}')
        with self.assertRaisesRegex(Blocked,'supervised Controller'):
            self.adapter.probe_version()

if __name__=='__main__':unittest.main()
