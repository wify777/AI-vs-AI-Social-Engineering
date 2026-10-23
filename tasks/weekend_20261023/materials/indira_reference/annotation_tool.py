#!/usr/bin/env python3
"""Offline, standard-library-only, independent secondary annotation utility."""
import argparse
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

POLICY_VERSION = 'response-review-v1'
CATEGORIES = frozenset({
    'explicit_text_refusal', 'summary_only', 'action_intent_without_valid_decision',
    'incomplete_output', 'other_ambiguous',
})
REQUIRED_CASE = ('config_hash', 'run_id', 'stage', 'trusted_request', 'external_text',
                 'parser', 'admin', 'finish_metadata', 'tool_evidence', 'truncation')
KEY = ('config_hash', 'run_id', 'stage', 'source_hash')

class ValidationError(ValueError):
    pass

def require_object(obj, fields, label):
    if not isinstance(obj, dict):
        raise ValidationError(f'{label}: expected object')
    missing = [k for k in fields if k not in obj]
    if missing:
        raise ValidationError(f'{label}: missing fields: {missing}')

def nonempty(value):
    return isinstance(value, str) and bool(value.strip())

def load_cases(path):
    """Hash exact JSONL line bytes excluding a terminal LF or CRLF only."""
    records, seen, run_configs = [], set(), {}
    with open(path, 'rb') as f:
        for line_no, raw in enumerate(f, 1):
            if not raw.strip():
                raise ValidationError(f'line {line_no}: empty JSONL line')
            raw_record = raw[:-2] if raw.endswith(b'\r\n') else raw[:-1] if raw.endswith(b'\n') else raw
            try:
                obj = json.loads(raw_record.decode('utf-8'))
            except (UnicodeDecodeError, json.JSONDecodeError) as e:
                raise ValidationError(f'line {line_no}: invalid UTF-8 JSON: {e}') from e
            require_object(obj, REQUIRED_CASE, f'line {line_no}')
            for field in ('config_hash', 'run_id', 'stage', 'trusted_request'):
                if not nonempty(obj[field]):
                    raise ValidationError(f'line {line_no}: empty {field}')
            for field in ('parser', 'admin', 'finish_metadata', 'tool_evidence', 'truncation'):
                if not isinstance(obj[field], dict):
                    raise ValidationError(f'line {line_no}: {field} must be an object')
            if not isinstance(obj['external_text'], (str, type(None))):
                raise ValidationError(f'line {line_no}: invalid external_text')
            if not (len(obj['config_hash']) == 64 and all(c in '0123456789abcdef' for c in obj['config_hash'])):
                raise ValidationError(f'line {line_no}: config_hash must be full lowercase SHA-256 hex')
            identity = (obj['config_hash'], obj['run_id'], obj['stage'])
            if identity in seen:
                raise ValidationError(f'line {line_no}: duplicate case {identity}')
            seen.add(identity)
            previous = run_configs.setdefault(obj['run_id'], obj['config_hash'])
            if previous != obj['config_hash']:
                raise ValidationError(f'line {line_no}: run_id occurs in different config_hash')
            obj['source_hash'] = hashlib.sha256(raw_record).hexdigest()
            records.append(obj)
    if not records:
        raise ValidationError('no cases')
    return records

def write_new(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation: never overwrite an existing file.
    with path.open('x', encoding='utf-8', newline='\n') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')

def prepare(args):
    cases = load_cases(args.cases)
    out = Path(args.output)
    targets = [out / 'reviewer_A.json', out / 'reviewer_B.json']
    if any(p.exists() for p in targets):
        raise ValidationError('output already exists; no files were overwritten')
    for reviewer, path in zip(('A', 'B'), targets):
        form = {'format_version': 1, 'policy_version': POLICY_VERSION,
                'reviewer': reviewer, 'annotations': []}
        for case in cases:
            form['annotations'].append({
                'config_hash': case['config_hash'], 'run_id': case['run_id'],
                'stage': case['stage'], 'source_hash': case['source_hash'],
                'context': {k: case[k] for k in REQUIRED_CASE if k not in ('config_hash', 'run_id', 'stage')},
                'annotator_identity': None, 'policy_version': POLICY_VERSION,
                'timestamp': None, 'category': None, 'explanation': None,
            })
        write_new(path, form)
    print(f'Prepared {len(cases)} cases for each reviewer in {out}')

def timestamp_valid(value):
    if not nonempty(value):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return parsed.tzinfo is not None and parsed.utcoffset() is not None
    except ValueError:
        return False

def validate_form(path, cases, expected_reviewer):
    with open(path, encoding='utf-8') as f:
        form = json.load(f)
    require_object(form, ('format_version', 'policy_version', 'reviewer', 'annotations'), str(path))
    if type(form['format_version']) is not int or not isinstance(form['policy_version'], str) or not isinstance(form['reviewer'], str):
        raise ValidationError(f'{path}: invalid form header field types')
    if form['format_version'] != 1 or form['policy_version'] != POLICY_VERSION or form['reviewer'] != expected_reviewer:
        raise ValidationError(f'{path}: invalid form header')
    if not isinstance(form['annotations'], list):
        raise ValidationError(f'{path}: annotations must be list')
    expected = {tuple(c[k] for k in KEY): c for c in cases}
    seen = set()
    output = {}
    identities = set()
    for i, item in enumerate(form['annotations'], 1):
        require_object(item, (*KEY, 'context', 'annotator_identity', 'policy_version',
                              'timestamp', 'category', 'explanation'), f'{path} entry {i}')
        for field in KEY:
            if not nonempty(item[field]):
                raise ValidationError(f'{path} entry {i}: {field} must be a nonempty string')
        if not isinstance(item['context'], dict):
            raise ValidationError(f'{path} entry {i}: context must be an object')
        if not isinstance(item['policy_version'], str):
            raise ValidationError(f'{path} entry {i}: policy_version must be a string')
        for field in ('annotator_identity', 'timestamp', 'category', 'explanation'):
            if item[field] is not None and not isinstance(item[field], str):
                raise ValidationError(f'{path} entry {i}: {field} must be a string or null')
        key = tuple(item[k] for k in KEY)
        if key in seen:
            raise ValidationError(f'{path}: duplicate annotation {key}')
        seen.add(key)
        if key not in expected:
            raise ValidationError(f'{path}: unknown case or incorrect source hash: {key}')
        source = expected[key]
        context = {k: source[k] for k in REQUIRED_CASE if k not in ('config_hash', 'run_id', 'stage')}
        if item['context'] != context:
            raise ValidationError(f'{path}: source context modified for {key}')
        if item['policy_version'] != POLICY_VERSION:
            raise ValidationError(f'{path}: incorrect policy version')
        fields = ('annotator_identity', 'timestamp', 'category', 'explanation')
        values = [item[k] for k in fields]
        if all(v is None or v == '' for v in values):
            output[key] = None  # completely blank form is a missing annotation
            continue
        if not all(nonempty(v) for v in values):
            raise ValidationError(f'{path}: partially completed annotation {key}')
        if item['category'] not in CATEGORIES:
            raise ValidationError(f'{path}: unknown category {item["category"]}')
        if not timestamp_valid(item['timestamp']):
            raise ValidationError(f'{path}: timestamp needs timezone')
        identities.add(item['annotator_identity'].strip())
        output[key] = item
    if len(identities) > 1:
        raise ValidationError(f'{path}: multiple annotator identities in one form')
    return output, identities

def merge(args):
    cases = load_cases(args.cases)
    a, ids_a = validate_form(args.a, cases, 'A')
    b, ids_b = validate_form(args.b, cases, 'B')
    if ids_a & ids_b:
        raise ValidationError('same annotator identity in both forms; not independent reviews')
    report = {'policy_version': POLICY_VERSION, 'source_cases': str(args.cases),
              'counts': {}, 'items': []}
    counts = Counter()
    for case in cases:
        key = tuple(case[k] for k in KEY)
        left, right = a.get(key), b.get(key)
        if left is None or right is None:
            status = 'missing'
        elif left['category'] == right['category']:
            status = 'agreement'
        else:
            status = 'disagreement'
        counts[status] += 1
        report['items'].append({**{k: case[k] for k in KEY}, 'status': status,
                                'review_A': left, 'review_B': right})
    report['counts'] = {k: counts[k] for k in ('agreement', 'disagreement', 'missing')}
    write_new(args.output, report)
    print(json.dumps(report['counts'], ensure_ascii=False))
    print(f'Report: {args.output}')

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    pp = sub.add_parser('prepare', help='generate independent blank review forms')
    pp.add_argument('--cases', default='fixtures/cases.jsonl')
    pp.add_argument('--output', default='out')
    pp.set_defaults(func=prepare)
    mp = sub.add_parser('merge', help='validate and compare completed forms')
    mp.add_argument('--cases', default='fixtures/cases.jsonl')
    mp.add_argument('--a', default='out/reviewer_A.json')
    mp.add_argument('--b', default='out/reviewer_B.json')
    mp.add_argument('--output', default='out/merge_report.json')
    mp.set_defaults(func=merge)
    args = p.parse_args(argv)
    try:
        args.func(args)
        return 0
    except (ValidationError, FileNotFoundError, FileExistsError, json.JSONDecodeError, OSError) as e:
        print(f'ERROR: {e}', file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())
