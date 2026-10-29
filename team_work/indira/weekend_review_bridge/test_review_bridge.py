import copy
import json
import tempfile
import unittest
from pathlib import Path
from review_bridge import FIELDS, ReviewError, load_reference, validate_rows, compare, prepare, write_new
from argparse import Namespace

class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.ref=[]
        for i in range(2):
            self.ref.append(dict(zip(FIELDS,[f'R{i+1:03d}','a'*64,f'run{i}','initial',f'{i+1:064x}','','','REVIEW_POLICY.md v1','b'*64,None,''])))
    def save(self,obj,name):
        p=self.root/name;p.write_text(json.dumps(obj));return p
    def filled(self,who,cat='summary_only'):
        f=copy.deepcopy(self.ref)
        for r in f:r.update(annotator_identity=who,annotated_at='2026-10-26T12:00:00+05:00',secondary_category=cat,evidence_note='Synthetic example only')
        return f
    def assert_invalid(self,rows):self.assertFalse(validate_rows(self.ref,rows)['valid'])
    def test_blank(self):
        r=validate_rows(self.ref,self.ref);self.assertTrue(r['valid']);self.assertEqual(r['missing'],2)
    def test_full(self):self.assertTrue(validate_rows(self.ref,self.filled('Alice'))['valid'])
    def test_unknown_id(self):
        x=self.filled('Alice');x[0]['case_id']='R999';self.assert_invalid(x)
    def test_missing_id(self):self.assert_invalid(self.ref[:1])
    def test_duplicate_id(self):self.assert_invalid(self.ref+[self.ref[0]])
    def test_config(self):
        x=self.filled('Alice');x[0]['config_hash']='c'*64;self.assert_invalid(x)
    def test_stage(self):
        x=self.filled('Alice');x[0]['stage']='other';self.assert_invalid(x)
    def test_hash(self):
        x=self.filled('Alice');x[0]['source_record_sha256_excluding_newline']='c'*64;self.assert_invalid(x)
    def test_policy(self):
        x=self.filled('Alice');x[0]['policy_version']='v2';self.assert_invalid(x)
    def test_wrong_type(self):
        x=self.filled('Alice');x[0]['run_id']=['bad'];self.assert_invalid(x)
    def test_timezone(self):
        x=self.filled('Alice');x[0]['annotated_at']='2026-10-26T12:00:00';self.assert_invalid(x)
    def test_partial(self):
        x=self.filled('Alice');x[0]['evidence_note']='';self.assert_invalid(x)
    def test_category(self):
        x=self.filled('Alice');x[0]['secondary_category']='invented';self.assert_invalid(x)
    def test_multiple_identities(self):
        x=self.filled('Alice');x[1]['annotator_identity']='Bob';self.assert_invalid(x)
    def test_no_overwrite(self):
        p=self.save({},'exists.json')
        with self.assertRaises(ReviewError):write_new(p,{'x':1})
        self.assertEqual(json.loads(p.read_text()),{})
    def test_agreement_and_preservation(self):
        a=self.filled('Alice');b=self.filled('Bob')
        rp=self.save(self.ref,'reference.json');ap=self.save(a,'a.json');bp=self.save(b,'b.json')
        before=[p.read_bytes() for p in (rp,ap,bp)]
        result=compare(Namespace(reference=rp,a=ap,b=bp,output=self.root/'result.json'))
        self.assertEqual(result['counts']['agreement'],2)
        self.assertEqual([p.read_bytes() for p in (rp,ap,bp)],before)
        report=json.loads((self.root/'result.json').read_text())
        self.assertEqual(report['rows'][0]['a']['evidence_note'],'Synthetic example only')
    def test_disagreement(self):
        a=self.filled('Alice');b=self.filled('Bob','other_ambiguous')
        result=compare(Namespace(reference=self.save(self.ref,'r.json'),a=self.save(a,'a.json'),b=self.save(b,'b.json'),output=self.root/'out.json'))
        self.assertEqual(result['counts']['disagreement'],2)
    def test_unread(self):
        a=self.filled('Alice');b=self.filled('Bob');b[1]=copy.deepcopy(self.ref[1])
        result=compare(Namespace(reference=self.save(self.ref,'r.json'),a=self.save(a,'a.json'),b=self.save(b,'b.json'),output=self.root/'out.json'))
        self.assertEqual(result['counts']['missing'],1)
    def test_same_reviewer(self):
        with self.assertRaisesRegex(ReviewError,'Same normalized'):
            compare(Namespace(reference=self.save(self.ref,'r.json'),a=self.save(self.filled('Alice'),'a.json'),b=self.save(self.filled(' ALICE '),'b.json'),output=self.root/'out.json'))
    def test_reference_duplicate(self):
        p=self.save(self.ref+[self.ref[0]],'ref.json')
        with self.assertRaises(ReviewError):load_reference(p)

    def test_category_list_validate(self):
        x=self.filled('Alice');x[0]['secondary_category']=['summary_only']
        result=validate_rows(self.ref,x)
        self.assertFalse(result['valid'])
        self.assertEqual(result['completed'],1)
        self.assertEqual(result['missing'],0)
        self.assertTrue(any('types' in error for error in result['errors']))

    def test_category_object_validate(self):
        x=self.filled('Alice');x[0]['secondary_category']={'category':'summary_only'}
        result=validate_rows(self.ref,x)
        self.assertFalse(result['valid'])
        self.assertEqual(result['completed'],1)
        self.assertEqual(result['missing'],0)

    def test_category_list_compare(self):
        a=self.filled('Alice');a[0]['secondary_category']=['summary_only']
        with self.assertRaisesRegex(ReviewError,'Invalid forms'):
            compare(Namespace(reference=self.save(self.ref,'r.json'),a=self.save(a,'a.json'),b=self.save(self.filled('Bob'),'b.json'),output=self.root/'out.json'))
        self.assertFalse((self.root/'out.json').exists())

    def test_category_object_compare(self):
        b=self.filled('Bob');b[0]['secondary_category']={'category':'summary_only'}
        with self.assertRaisesRegex(ReviewError,'Invalid forms'):
            compare(Namespace(reference=self.save(self.ref,'r.json'),a=self.save(self.filled('Alice'),'a.json'),b=self.save(b,'b.json'),output=self.root/'out.json'))
        self.assertFalse((self.root/'out.json').exists())

    def test_category_without_evidence_not_completed(self):
        x=self.filled('Alice');x[0]['evidence_note']=''
        result=validate_rows(self.ref,x)
        self.assertFalse(result['valid'])
        self.assertEqual(result['completed'],1)
        self.assertEqual(result['missing'],0)

    def test_partial_without_category_not_missing(self):
        x=self.filled('Alice');x[0]['secondary_category']=None
        result=validate_rows(self.ref,x)
        self.assertFalse(result['valid'])
        self.assertEqual(result['completed'],1)
        self.assertEqual(result['missing'],0)

    def test_mixed_counters(self):
        x=self.filled('Alice');x[0]=copy.deepcopy(self.ref[0])
        result=validate_rows(self.ref,x)
        self.assertTrue(result['valid'])
        self.assertEqual(result['completed'],1)
        self.assertEqual(result['missing'],1)

    def test_prepare_missing_evidence_section(self):
        reference=[copy.deepcopy(self.ref[0]) for _ in range(58)]
        for i,r in enumerate(reference):
            r['case_id']=f'R{i+1:03d}'
            r['run_id']=f'run{i}'
            r['source_record_sha256_excluding_newline']=f'{i+1:064x}'
        evidence=''.join(f'## R{i:03d}\n\nEvidence\n' for i in range(1,58))
        evidence_path=self.root/'evidence.md'
        evidence_path.write_text(evidence,encoding='utf-8')
        output=self.root/'prepared'
        with self.assertRaisesRegex(ReviewError,'Evidence sections'):
            prepare(Namespace(identities=self.save(reference,'identities.json'),evidence=evidence_path,output=output))
        self.assertFalse(output.exists())

    def test_prepare_refuses_existing_directory(self):
        reference=[copy.deepcopy(self.ref[0]) for _ in range(58)]
        for i,r in enumerate(reference):
            r['case_id']=f'R{i+1:03d}'
            r['run_id']=f'run{i}'
            r['source_record_sha256_excluding_newline']=f'{i+1:064x}'
        evidence_path=self.root/'evidence.md'
        evidence_path.write_text(''.join(f'## R{i:03d}\n' for i in range(1,59)),encoding='utf-8')
        output=self.root/'prepared';output.mkdir()
        sentinel=output/'keep.txt';sentinel.write_text('untouched')
        with self.assertRaisesRegex(ReviewError,'exists'):
            prepare(Namespace(identities=self.save(reference,'identities.json'),evidence=evidence_path,output=output))
        self.assertEqual(sentinel.read_text(),'untouched')

    def test_compare_refuses_overwrite(self):
        output=self.save({'old':True},'out.json')
        with self.assertRaisesRegex(ReviewError,'exists'):
            compare(Namespace(reference=self.save(self.ref,'r.json'),a=self.save(self.filled('Alice'),'a.json'),b=self.save(self.filled('Bob'),'b.json'),output=output))
        self.assertEqual(json.loads(output.read_text()),{'old':True})

if __name__=='__main__':unittest.main()
