"""Independent ready reconciliation wiring checks: real state, simulated API/proof."""
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import test_github_ready_cli as fixtures
class ReadyWiringAudit(unittest.TestCase):
    setUp=fixtures.ReadyCli.setUp
    tearDown=fixtures.ReadyCli.tearDown
    commit=fixtures.ReadyCli.commit
    invoke=fixtures.ReadyCli.invoke
    state=fixtures.ReadyCli.state
    def pending(self):
        params={'task_id':'feature','number':1,'authorized':True}
        code,_=self.invoke('ready',params,lambda *_a,**_k:{'status':'unknown','pr':1})
        self.assertEqual(code,0)
        return params
    def test_still_draft_observation_never_clears_unknown(self):
        params=self.pending()
        code,_=self.invoke('reconcile-ready',params,lambda *_a,**_k:{'status':'draft','pr':1})
        self.assertEqual(code,0)
        self.assertEqual(self.state()['remote_operations'][0]['status'],'unknown')
        self.assertEqual(self.state()['tasks'],{})
    def test_other_pr_observation_cannot_clear_original_intent(self):
        params=self.pending();params['number']=2
        self.adapter.read_pr.return_value.update(number=2,draft=False)
        code,_=self.invoke('reconcile-ready',params,lambda *_a,**_k:{'status':'ready','pr':2})
        self.assertEqual(code,0)
        self.assertEqual(self.state()['remote_operations'][0]['status'],'unknown')
    def test_changed_named_destination_blocks_read_reconciliation(self):
        params=self.pending()
        self.adapter.read_pr.return_value['base']['ref']='other-target'
        code,called=self.invoke('reconcile-ready',params,lambda *_a,**_k:{'status':'ready','pr':1})
        self.assertEqual(code,1);called.assert_not_called()
        self.assertEqual(self.state()['remote_operations'][0]['status'],'unknown')
    def test_unknown_draft_type_cannot_mutate(self):
        for value in (None,'false',0):
            with self.subTest(value=value):
                self.adapter.read_pr.return_value['draft']=value
                code,called=self.invoke('ready',{'task_id':'feature','number':1,'authorized':True},lambda *_a,**_k:{})
                self.assertEqual(code,1);called.assert_not_called()
                self.assertEqual(self.state()['remote_operations'],[])
if __name__=='__main__':unittest.main()
