import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from harness.runtime import Controller
from harness.state import Blocked

class ControlledNativeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);subprocess.run(['git','init','-q',str(self.root)],check=True)
        self.limits={'command_seconds':3,'stop_grace_seconds':0.2,'total_seconds':10,'max_attempts':3}
    def test_stdin_env_and_separate_raw_streams(self):
        with Controller(self.root,'local','native-run',self.limits) as controller:
            env=dict(os.environ,HARNESS_NATIVE_PROBE='known-fixture')
            record=controller.execute([sys.executable,'-c','import os,sys; print(os.environ["HARNESS_NATIVE_PROBE"]); print(sys.stdin.read()); print("native-stderr",file=sys.stderr)'],self.root,'native-1',self.root/'native.out',env=env,input_text='正文输入',separate_stderr=True)
            self.assertEqual(record['exit_code'],0)
            self.assertIn('正文输入',Path(record['log']).read_text())
            self.assertNotIn('native-stderr',Path(record['log']).read_text())
            self.assertEqual(Path(record['stderr_log']).read_text(),'native-stderr\n')
            self.assertEqual(len(record['input_sha256']),64)
            state=controller.state.read();self.assertEqual(state['commands_started'],1);self.assertGreater(state['spent_seconds'],0)
    def test_unknown_scope_refused(self):
        with Controller(self.root,'local','native-run',self.limits) as controller:
            with self.assertRaises(Blocked):controller.execute([sys.executable,'-c','pass'],self.root,'native-1',self.root/'native.out',scope='unlimited')
    def test_corrupt_nonfinite_checkpoint_preserved(self):
        path=self.root/'.loop-state.json';raw='{"schema_version":2,"spent_seconds":NaN}'
        path.write_text(raw)
        with self.assertRaises(Blocked):
            with Controller(self.root,'local','native-run',self.limits):pass
        self.assertEqual(path.read_text(),raw)
if __name__=='__main__':unittest.main()
