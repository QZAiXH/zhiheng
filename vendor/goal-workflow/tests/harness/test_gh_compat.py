import subprocess
import unittest
from harness.github import GitHubAdapter, AdapterError
class GhCompatibility(unittest.TestCase):
 def adapter(self, raw):
  calls=[]
  def run(argv, timeout):
   calls.append(argv)
   if '--slurp' in argv:return subprocess.CompletedProcess(argv,1,'','unknown flag: --slurp')
   return subprocess.CompletedProcess(argv,0,raw,'')
  return GitHubAdapter({'repository':'example/repo'},run),calls
 def test_old_cli_native_paginated_arrays(self):
  adapter,calls=self.adapter('[{"number":1}]\n[{"number":2}]\n')
  result=adapter._api('repos/example/repo/issues',True)
  self.assertEqual([x['number'] for x in result],[1,2]);self.assertEqual(len(calls),2)
  self.assertIn('--paginate',calls[-1]);self.assertNotIn('--slurp',calls[-1])
 def test_old_cli_native_paginated_objects(self):
  adapter,_=self.adapter('{"check_runs":[]}\n{"check_runs":[]}')
  self.assertEqual(len(adapter._command(['api','anything','--paginate','--slurp'])),2)
 def test_malformed_or_empty_pages_fail(self):
  for raw in ('','[{}]\nBROKEN'):
   adapter,_=self.adapter(raw)
   with self.assertRaises(AdapterError):adapter._api('endpoint',True)
 def test_other_errors_do_not_fallback(self):
  calls=[]
  def run(argv,t):calls.append(argv);return subprocess.CompletedProcess(argv,1,'','HTTP 403')
  adapter=GitHubAdapter({'repository':'example/repo'},run)
  with self.assertRaises(AdapterError):adapter._api('endpoint',True)
  self.assertEqual(len(calls),1)
if __name__=='__main__':unittest.main()
