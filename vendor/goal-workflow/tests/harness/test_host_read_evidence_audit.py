"""Offline public JSONL read-proof audit; never invokes a model or rewrites receipts."""
import json
import unittest
from harness.codex_probe import parse_events,validate_read_content,ProbeFailed

BODY='def apply_discount(subtotal, rate):\n    return subtotal * (1 + rate)\n'
AC='AC-discount: apply_discount(100, 0.1) must return 90. A discount must reduce the subtotal.\n'
NUMBERED='     1\tdef apply_discount(subtotal, rate):\n     2\t    return subtotal * (1 + rate)\n'
class HostReadEvidenceAudit(unittest.TestCase):
    def events(self,commands):
        rows=[{'type':'thread.started','thread_id':'00000000-0000-0000-0000-000000000001'}]
        for command,output,exit_code in commands:
            rows.append({'type':'item.completed','item':{'type':'command_execution','status':'completed','exit_code':exit_code,'command':command,'aggregated_output':output}})
        rows += [{'type':'item.completed','item':{'type':'agent_message','text':'Blocking: fixture.py:2 returns 110 instead of 90.'}},{'type':'turn.completed'}]
        return parse_events(('\n'.join(json.dumps(row) for row in rows)+'\n').encode())
    def check(self,commands,expected=None):
        return validate_read_content(self.events(commands),expected or {'fixture.py':BODY,'acceptance.md':AC})
    def test_exact_mac_trace_preserves_source_and_format(self):
        command="/bin/zsh -lc 'nl -ba fixture.py; cat acceptance.md'"
        result=self.check([('rg --files','fixture.py\nacceptance.md\n',0),(command,NUMBERED+AC,0)])
        self.assertEqual(result['fixture.py']['event_index'],3)
        self.assertEqual(result['fixture.py']['command'],command)
        self.assertEqual(result['fixture.py']['format'],'numbered')
        self.assertEqual(result['acceptance.md']['output_start_line'],3)
    def test_enumeration_cannot_prove_read_even_with_body_in_output(self):
        with self.assertRaises(ProbeFailed):self.check([('rg --files',BODY+AC,0)])
    def test_failed_or_boolean_exit_cannot_prove_read(self):
        for code in (1,False):
            with self.subTest(code=code),self.assertRaises(ProbeFailed):self.check([('cat fixture.py acceptance.md',BODY+AC,code)])
    def test_numbered_missing_changed_indent_skipped_duplicate_lines_refused(self):
        variants=[NUMBERED.splitlines(True)[0],NUMBERED.replace('1 + rate','1 - rate'),NUMBERED.replace('\t    return','\treturn'),NUMBERED.replace('     2\t','     3\t'),NUMBERED.replace('     2\t','     1\t')]
        for output in variants:
            with self.subTest(output=output),self.assertRaises(ProbeFailed):self.check([('nl -ba fixture.py; cat acceptance.md',output+AC,0)])
    def test_cross_event_partial_body_cannot_be_joined(self):
        with self.assertRaises(ProbeFailed):self.check([('cat fixture.py',BODY.splitlines(True)[0],0),('cat fixture.py',BODY.splitlines(True)[1],0),('cat acceptance.md',AC,0)])
    def test_unrelated_command_or_echo_cannot_lend_output(self):
        for cmd in ('echo fixture.py acceptance.md','cat fixture.py; echo acceptance.md','python -c "print(1)"','cat fixture.py | cat acceptance.md'):
            with self.subTest(cmd=cmd),self.assertRaises(ProbeFailed):self.check([(cmd,BODY+AC,0)])
    def test_separate_genuine_full_reads_are_allowed(self):
        result=self.check([('cat fixture.py',BODY,0),('cat acceptance.md',AC,0)])
        self.assertEqual(result['fixture.py']['event_index'],2);self.assertEqual(result['acceptance.md']['event_index'],3)
    def test_extra_raw_content_is_not_exact_fixture(self):
        with self.assertRaises(ProbeFailed):self.check([('cat fixture.py',BODY+'unexpected_extra_line\n',0)],{'fixture.py':BODY})
    def test_numbered_duplicate_extra_line_is_not_exact_fixture(self):
        with self.assertRaises(ProbeFailed):self.check([('nl -ba fixture.py',NUMBERED+'     2\tmalicious extra line\n',0)],{'fixture.py':BODY})
    def test_swapped_command_output_cannot_claim_named_file(self):
        with self.assertRaises(ProbeFailed):self.check([('cat acceptance.md fixture.py',BODY+AC,0)])
if __name__=='__main__':unittest.main()
