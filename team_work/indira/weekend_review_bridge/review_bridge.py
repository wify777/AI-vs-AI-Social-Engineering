#!/usr/bin/env python3
"""Offline bridge for preserved independent human review forms."""
import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

CATEGORIES = {'explicit_text_refusal', 'summary_only', 'action_intent_without_valid_decision', 'incomplete_output', 'other_ambiguous'}
FIELDS = ('case_id','config_hash','run_id','stage','source_record_sha256_excluding_newline','annotator_identity','annotated_at','policy_version','policy_sha256','secondary_category','evidence_note')
FIXED = ('case_id','config_hash','run_id','stage','source_record_sha256_excluding_newline','policy_version','policy_sha256')
HASHES = ('config_hash','source_record_sha256_excluding_newline','policy_sha256')
HEX = re.compile(r'[0-9a-fA-F]{64}\Z')
SECTION = re.compile(r'^## (R\d{3})\s*$',re.M)

class ReviewError(ValueError): pass

def check(cond, message):
    if not cond: raise ReviewError(message)

def read_json(path):
    try: return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, UnicodeError, json.JSONDecodeError) as e: raise ReviewError(f'Cannot read JSON {path}: {e}') from e

def digest(data): return hashlib.sha256(data).hexdigest()

def write_new(path, obj):
    p=Path(path)
    check(not p.exists(), f'Output exists: {p}')
    p.parent.mkdir(parents=True,exist_ok=True)
    try:
        with p.open('x',encoding='utf-8',newline='\n') as f: json.dump(obj,f,indent=2,ensure_ascii=False);f.write('\n')
    except OSError as e: raise ReviewError(str(e)) from e

def load_reference(path, expected_count=None):
    data=read_json(path)
    check(type(data) is list and bool(data),'Reference must be a nonempty JSON array')
    seen_ids=set();seen_keys=set()
    for i,r in enumerate(data):
        label=f'reference[{i}]'
        check(type(r) is dict and set(r)==set(FIELDS),f'{label}: incorrect fields')
        for k in FIXED:
            check(type(r[k]) is str and bool(r[k].strip()),f'{label}: {k} must be a nonempty string')
        for k in HASHES: check(bool(HEX.fullmatch(r[k])),f'{label}: {k} must be 64 hex digits')
        check(r['case_id'] not in seen_ids,f'{label}: duplicate case_id')
        seen_ids.add(r['case_id'])
        key=tuple(r[k] for k in ('config_hash','run_id','stage','source_record_sha256_excluding_newline'))
        check(key not in seen_keys,f'{label}: duplicate identity tuple')
        seen_keys.add(key)
        check(r['annotator_identity']=='' and r['annotated_at']=='' and r['secondary_category'] is None and r['evidence_note']=='',f'{label}: reference must be blank')
    if expected_count is not None:
        expected={f'R{i:03d}' for i in range(1,expected_count+1)}
        check(seen_ids==expected,f'Reference case IDs differ from R001–R{expected_count:03d}: missing={sorted(expected-seen_ids)}, extra={sorted(seen_ids-expected)}')
    return data

def validate_rows(reference, rows):
    check(type(rows) is list,'Form must be a JSON array')
    errors=[]; identities=set(); counts=Counter(); names=set(); completed=0; missing=0
    ref={r['case_id']:r for r in reference}
    for i,r in enumerate(rows):
        label=f'form[{i}]'
        if type(r) is not dict: errors.append(f'{label}: expected object');continue
        if set(r)!=set(FIELDS): errors.append(f'{label}: incorrect fields');continue
        case=r['case_id']
        if type(case) is not str: errors.append(f'{label}: case_id must be string');continue
        counts[case]+=1
        if case not in ref: errors.append(f'{label}: unknown case_id {case}');continue
        for k in FIXED:
            if type(r[k]) is not str or r[k]!=ref[case][k]: errors.append(f'{label}: changed/invalid {k}')
        values=[r[k] for k in ('annotator_identity','annotated_at','secondary_category','evidence_note')]
        if not (type(values[0]) is str and type(values[1]) is str and (values[2] is None or type(values[2]) is str) and type(values[3]) is str):
            errors.append(f'{label}: invalid annotation field types');continue
        blank=values==['','',None,'']
        if blank:
            missing+=1
            continue
        if not all(type(x) is str and x.strip() for x in values):
            errors.append(f'{label}: partially completed annotation');continue
        if r['secondary_category'] not in CATEGORIES:
            errors.append(f'{label}: unknown category')
            continue
        try:
            stamp=r['annotated_at']
            check('T' in stamp,'timestamp requires ISO 8601 date/time')
            parsed=datetime.fromisoformat(stamp)
            check(parsed.tzinfo is not None and parsed.utcoffset() is not None,'timestamp missing timezone')
        except (ValueError,TypeError,ReviewError):
            errors.append(f'{label}: invalid timestamp/timezone')
            continue
        completed+=1
        names.add(r['annotator_identity'].strip().casefold())
        identities.add(r['annotator_identity'].strip())
    for case in ref:
        if counts[case]==0: errors.append(f'missing case_id {case}')
        if counts[case]>1: errors.append(f'duplicate case_id {case}')
    if len(names)>1: errors.append('multiple annotator identities within one form')
    return {'valid':not errors,'total':len(reference),'completed':completed,'missing':missing,'identities':sorted(identities),'errors':errors}

def prepare(args):
    reference=load_reference(args.identities,58)
    evidence=Path(args.evidence).read_bytes()
    try: sections=SECTION.findall(evidence.decode('utf-8'))
    except UnicodeError as e: raise ReviewError(f'Evidence is not UTF-8: {e}') from e
    expected=[f'R{i:03d}' for i in range(1,59)]
    check(sections==expected,f'Evidence sections must occur exactly once in R001–R058 order (found {len(sections)})')
    out=Path(args.output)
    check(not out.exists(),f'Output directory exists: {out}')
    out.mkdir(parents=True)
    paths=[]
    for name in ('reviewer_A.json','reviewer_B.json'):
        p=out/name;write_new(p,reference);paths.append(p)
    manifest={'reference_sha256':digest(Path(args.identities).read_bytes()),'evidence_sha256':digest(evidence),'source_hash_definition':'SHA-256 of original JSONL record bytes excluding final LF/CRLF; copied from identity manifest, never derived from EVIDENCE.md','case_count':58,'form_sha256':{p.name:digest(p.read_bytes()) for p in paths}}
    write_new(out/'manifest.json',manifest)
    return {'ok':True,'cases':58,'output':str(out),'manifest':manifest}

def validate(args):
    reference=load_reference(args.reference)
    result=validate_rows(reference,read_json(args.form))
    result['form']=str(args.form)
    return result

def compare(args):
    reference=load_reference(args.reference)
    a=read_json(args.a);b=read_json(args.b)
    va=validate_rows(reference,a);vb=validate_rows(reference,b)
    check(va['valid'] and vb['valid'],f'Invalid forms: A={va["errors"]}; B={vb["errors"]}')
    na={x.strip().casefold() for x in va['identities']};nb={x.strip().casefold() for x in vb['identities']}
    check(bool(na) and bool(nb),'Both forms require at least one completed human annotation before comparison')
    check(na.isdisjoint(nb),'Same normalized reviewer identity in A and B')
    ma={r['case_id']:r for r in a};mb={r['case_id']:r for r in b}
    rows=[];totals=Counter()
    for ref in reference:
        key=ref['case_id'];ra=ma[key];rb=mb[key]
        ca=ra['secondary_category'];cb=rb['secondary_category']
        status='missing' if ca is None or cb is None else 'agreement' if ca==cb else 'disagreement'
        totals[status]+=1
        rows.append({'case_id':key,'identity':{k:ref[k] for k in FIXED},'status':status,'a':{k:ra[k] for k in ('annotator_identity','annotated_at','secondary_category','evidence_note')},'b':{k:rb[k] for k in ('annotator_identity','annotated_at','secondary_category','evidence_note')}})
    report={'counts':{k:totals[k] for k in ('agreement','disagreement','missing')},'rows':rows,'disagreements':[r for r in rows if r['status']=='disagreement'],'note':'No consensus or ASR calculated. Different names do not prove independence.','inputs_sha256':{k:digest(Path(v).read_bytes()) for k,v in [('reference',args.reference),('a',args.a),('b',args.b)]}}
    write_new(args.output,report)
    return {'ok':True,'counts':report['counts'],'output':str(args.output)}

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    q=sub.add_parser('prepare');q.add_argument('--identities',required=True);q.add_argument('--evidence',required=True);q.add_argument('--output',required=True)
    q=sub.add_parser('validate');q.add_argument('--reference',required=True);q.add_argument('--form',required=True)
    q=sub.add_parser('compare');q.add_argument('--reference',required=True);q.add_argument('--a',required=True);q.add_argument('--b',required=True);q.add_argument('--output',required=True)
    args=p.parse_args(argv)
    try:
        result={'prepare':prepare,'validate':validate,'compare':compare}[args.command](args)
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return 0 if result.get('valid',True) else 1
    except (ReviewError,OSError) as e:
        print(json.dumps({'ok':False,'error':str(e)},ensure_ascii=False),file=sys.stderr);return 1
if __name__=='__main__':sys.exit(main())
