import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from harness.reports import build_mapping, write_reports
from harness.state import Blocked

class ReportsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.ctl=SimpleNamespace(root=self.root,entered=True)
        self.task={'task_id':'login-v2','title':'登录 <script>alert(1)</script>'}
    def tearDown(self):self.tmp.cleanup()
    def test_local_nonnumeric_rename_stable(self):
        m=build_mapping([self.task],'local'); t=dict(self.task,title='新标题',path='renamed.md')
        self.assertEqual(m,build_mapping([t],'local',m))
        p=write_reports(self.ctl,'local',self.task,{'status':'blocked'},m)
        text=(self.root/p['note']).read_text();self.assertNotIn('<script>',text)
        self.assertIn('lang="zh-CN"',text);self.assertNotIn('Issue #',text)
    def test_github_legacy(self):
        t=dict(self.task,issue_number=42);m=build_mapping([t],'github')
        self.assertEqual(m['login-v2']['note'],'docs/issue#42.html')
    def test_duplicate_and_path_collision(self):
        with self.assertRaises(Blocked):build_mapping([self.task,self.task],'local')
        m=build_mapping([self.task],'local');m['other']=dict(m['login-v2'])
        with self.assertRaises(Blocked):build_mapping([self.task],'local',m)
    def test_path_escape(self):
        for bad in ('../x','/tmp/x','docs/../x','docs\\x','.harness/runs/a','docs//x'):
            m=build_mapping([self.task],'local');m['login-v2']['note']=bad
            with self.assertRaises(Blocked):build_mapping([self.task],'local',m)
    def test_symlink_escape(self):
        with tempfile.TemporaryDirectory() as outer:
            (self.root/'docs').symlink_to(outer,target_is_directory=True)
            with self.assertRaises(Blocked):write_reports(self.ctl,'local',self.task,{},build_mapping([self.task],'local'))
    def test_preserves_user_text(self):
        m=build_mapping([self.task],'local');p=write_reports(self.ctl,'local',self.task,{},m)
        path=self.root/p['walkthrough'];path.write_text('用户前言\n'+path.read_text()+'用户后记\n')
        write_reports(self.ctl,'local',dict(self.task,title='changed'),{},m)
        text=path.read_text();self.assertTrue(text.startswith('用户前言'));self.assertTrue(text.endswith('用户后记\n'));self.assertIn('changed',text)
    def test_existing_unmanaged_preserved(self):
        m=build_mapping([self.task],'local');p=self.root/m['login-v2']['note'];p.parent.mkdir();p.write_text('user notes')
        with self.assertRaises(Blocked):write_reports(self.ctl,'local',self.task,{},m)
        self.assertEqual(p.read_text(),'user notes');self.assertFalse((self.root/'tasks').exists())
    def test_requires_lock(self):
        self.ctl.entered=False
        with self.assertRaises(Blocked):write_reports(self.ctl,'local',self.task,{},build_mapping([self.task],'local'))

if __name__=='__main__':unittest.main()
