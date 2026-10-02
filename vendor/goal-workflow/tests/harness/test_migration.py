import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from harness.state import migrate_legacy, Blocked

class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        subprocess.run(['git','init','-q',str(self.root)],check=True)
        self.limits={'command_seconds':2,'stop_grace_seconds':1,'total_seconds':10,'max_attempts':4}
        self.path=self.root/'.loop-state.json'
    def test_backup_unknown_delivery_and_budget(self):
        old={'version':1,'issues':{'4':{'status':'shipped','attempts':2}}}
        raw=json.dumps(old).encode(); self.path.write_bytes(raw)
        result=migrate_legacy(self.root,'local','run-one',self.limits,True)
        self.assertEqual(result['status'],'blocked')
        self.assertEqual(Path(result['backup']).read_bytes(),raw)
        new=json.loads(self.path.read_text())
        self.assertEqual(new['tasks'],{})
        self.assertEqual(new['spent_seconds'],10)
        self.assertEqual(new['legacy']['issues'],old['issues'])
    def test_no_authorization_no_change(self):
        self.path.write_text('{"version":1,"issues":{}}'); before=self.path.read_bytes()
        with self.assertRaises(Blocked): migrate_legacy(self.root,'local','r',self.limits)
        self.assertEqual(self.path.read_bytes(),before)
    def test_corruption_preserved(self):
        self.path.write_bytes(b'{broken')
        with self.assertRaises(Blocked): migrate_legacy(self.root,'local','r',self.limits,True)
        self.assertEqual(self.path.read_bytes(),b'{broken')
if __name__=='__main__': unittest.main()
