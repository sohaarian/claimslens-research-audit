#!/usr/bin/env python3
"""Offline scoring of independently labeled extraction outputs. No benchmark is bundled or claimed.
Usage: python benchmark_extraction_scaffold.py labels.jsonl predictions.jsonl
The file uses the same id in both. Labels must be independently adjudicated.
"""
import sys,json,re,collections
from pathlib import Path
FIELDS=('patient_id','order_id','modality','anatomy','laterality','report_date','report_status','signed')
def read(path):
 rows={}
 for line in Path(path).read_text().splitlines():
  if not line.strip():continue
  d=json.loads(line)
  if d['id'] in rows:raise ValueError('duplicate id '+d['id'])
  rows[d['id']]=d
 return rows
def score(ref,pred):
 assert ref.keys()==pred.keys(), 'ID mismatch: missing or extra predictions'
 good=collections.Counter();allfields=collections.Counter();invalid=collections.Counter();abstain=collections.Counter()
 for k,label in ref.items():
  model=pred[k]
  report=label['text'];fs=label['fields'];ps=model.get('fields',{})
  for field in FIELDS:
   if field not in fs:raise ValueError(f'{k} missing label: {field}')
   allfields[field]+=1
   val=ps.get(field)
   if val in ('',None):abstain[field]+=1;continue
   if str(val).strip().lower()==str(fs[field]).strip().lower():good[field]+=1
   if field in ('patient_id','order_id','modality','anatomy','laterality','report_date','report_status'):
    span=(model.get('spans') or {}).get(field,'')
    if not span or span not in report: invalid[field]+=1
 return {'cases':len(ref),'metric':'field exact match on independently supplied labels; not clinical validation',
         'field_counts':{f:{'correct':good[f],'total':allfields[f],
                            'accuracy':good[f]/allfields[f] if allfields[f] else None,
                            'abstain':abstain[f],'missing_or_invalid_source_spans':invalid[f]} for f in FIELDS}}
if __name__=='__main__':
 if len(sys.argv)!=3:raise SystemExit('Usage: python benchmark_extraction_scaffold.py independently_labeled.jsonl predictions.jsonl')
 print(json.dumps(score(read(sys.argv[1]),read(sys.argv[2])),indent=2))
