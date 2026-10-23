import copy
import hashlib
import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from annotation_tool import ValidationError, load_cases, prepare, merge, validate_form

ROOT = Path(__file__).parent
FIX = ROOT / 'fixtures'

class AnnotationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.cases = load_cases(FIX / 'cases.jsonl')

    def make_cases(self, objects):
        path = self.dir / 'cases.jsonl'
        with path.open('wb') as f:
            for obj in objects:
                obj = {k: v for k, v in obj.items() if k != 'source_hash'}
                f.write(json.dumps(obj, separators=(',', ':')).encode() + b'\n')
        return path

    def make_form(self, reviewer):
        return json.loads((FIX / f'test_review_{reviewer}.json').read_text())

    def save_form(self, form, name):
        p = self.dir / name
        p.write_text(json.dumps(form), encoding='utf-8')
        return p

    def test_five_scenarios_and_source_hash(self):
        self.assertEqual(len(self.cases), 5)
        line = (FIX / 'cases.jsonl').read_bytes().splitlines()[0]
        self.assertEqual(self.cases[0]['source_hash'], hashlib.sha256(line).hexdigest())

    def test_prepare_blanks_and_no_overwrite(self):
        out = self.dir / 'out'
        prepare(Namespace(cases=str(FIX / 'cases.jsonl'), output=str(out)))
        a = json.loads((out / 'reviewer_A.json').read_text())
        b = json.loads((out / 'reviewer_B.json').read_text())
        self.assertEqual(len(a['annotations']), 5)
        self.assertEqual(a['annotations'][0]['context'], b['annotations'][0]['context'])
        self.assertIsNone(a['annotations'][0]['category'])
        self.assertIsNone(a['annotations'][0]['annotator_identity'])
        with self.assertRaises(ValidationError):
            prepare(Namespace(cases=str(FIX / 'cases.jsonl'), output=str(out)))

    def test_duplicate_case(self):
        with self.assertRaisesRegex(ValidationError, 'duplicate'):
            load_cases(self.make_cases([self.cases[0], self.cases[0]]))

    def test_run_id_cross_config(self):
        second = copy.deepcopy(self.cases[1])
        second['run_id'] = self.cases[0]['run_id']
        second['config_hash'] = 'b' * 64
        with self.assertRaisesRegex(ValidationError, 'different config_hash'):
            load_cases(self.make_cases([self.cases[0], second]))

    def test_unknown_category(self):
        f = self.make_form('A')
        f['annotations'][0]['category'] = 'not_a_category'
        with self.assertRaisesRegex(ValidationError, 'unknown category'):
            validate_form(self.save_form(f, 'a.json'), self.cases, 'A')

    def test_invalid_run_id_type_gives_validation_error(self):
        f = self.make_form('A')
        f['annotations'][0]['run_id'] = ['invalid', 'list']
        with self.assertRaisesRegex(ValidationError, 'run_id must be a nonempty string'):
            validate_form(self.save_form(f, 'invalid_run_id.json'), self.cases, 'A')

    def test_missing_required_field(self):
        f = self.make_form('A')
        del f['annotations'][0]['explanation']
        with self.assertRaisesRegex(ValidationError, 'missing fields'):
            validate_form(self.save_form(f, 'a.json'), self.cases, 'A')

    def test_partial_annotation(self):
        f = self.make_form('A')
        f['annotations'][0]['explanation'] = ''
        with self.assertRaisesRegex(ValidationError, 'partially completed'):
            validate_form(self.save_form(f, 'a.json'), self.cases, 'A')

    def test_wrong_hash(self):
        f = self.make_form('A')
        f['annotations'][0]['source_hash'] = '0' * 64
        with self.assertRaisesRegex(ValidationError, 'incorrect source hash'):
            validate_form(self.save_form(f, 'a.json'), self.cases, 'A')

    def test_duplicate_annotation(self):
        f = self.make_form('A')
        f['annotations'].append(copy.deepcopy(f['annotations'][0]))
        with self.assertRaisesRegex(ValidationError, 'duplicate annotation'):
            validate_form(self.save_form(f, 'a.json'), self.cases, 'A')

    def test_tampered_context(self):
        f = self.make_form('A')
        f['annotations'][0]['context']['admin']['text'] = 'changed'
        with self.assertRaisesRegex(ValidationError, 'context modified'):
            validate_form(self.save_form(f, 'a.json'), self.cases, 'A')

    def test_timestamp_requires_timezone(self):
        f = self.make_form('A')
        f['annotations'][0]['timestamp'] = '2026-10-21T12:00:00'
        with self.assertRaisesRegex(ValidationError, 'timezone'):
            validate_form(self.save_form(f, 'a.json'), self.cases, 'A')

    def test_same_person_not_independent(self):
        a, b = self.make_form('A'), self.make_form('B')
        for item in b['annotations']:
            item['annotator_identity'] = 'FICTIONAL_TEST_REVIEWER_A'
        with self.assertRaisesRegex(ValidationError, 'not independent'):
            merge(Namespace(cases=str(FIX / 'cases.jsonl'), a=self.save_form(a, 'a.json'),
                            b=self.save_form(b, 'b.json'), output=self.dir / 'report.json'))

    def test_merge_agreement_disagreement_missing(self):
        a, b = self.make_form('A'), self.make_form('B')
        b['annotations'][1]['category'] = 'other_ambiguous'
        for field in ('annotator_identity', 'timestamp', 'category', 'explanation'):
            b['annotations'][2][field] = None
        target = self.dir / 'report.json'
        merge(Namespace(cases=str(FIX / 'cases.jsonl'), a=self.save_form(a, 'a.json'),
                        b=self.save_form(b, 'b.json'), output=target))
        report = json.loads(target.read_text())
        self.assertEqual(report['counts'], {'agreement': 3, 'disagreement': 1, 'missing': 1})
        self.assertEqual(report['items'][1]['review_A']['category'], 'summary_only')
        self.assertEqual(report['items'][1]['review_B']['category'], 'other_ambiguous')
        with self.assertRaises(FileExistsError):
            merge(Namespace(cases=str(FIX / 'cases.jsonl'), a=self.dir / 'a.json',
                            b=self.dir / 'b.json', output=target))

    def test_source_hash_changes_on_byte_edit(self):
        original = (FIX / 'cases.jsonl').read_bytes()
        changed = original.replace(b'Summarize this note.', b'Summarize this NOTE.', 1)
        p = self.dir / 'changed.jsonl'
        p.write_bytes(changed)
        self.assertNotEqual(load_cases(p)[0]['source_hash'], self.cases[0]['source_hash'])
        with self.assertRaisesRegex(ValidationError, 'incorrect source hash'):
            validate_form(self.save_form(self.make_form('A'), 'a.json'), load_cases(p), 'A')

if __name__ == '__main__':
    unittest.main()
