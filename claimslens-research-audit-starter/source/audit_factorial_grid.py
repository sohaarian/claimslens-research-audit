#!/usr/bin/env python3
"""Executable developer-specified cancellation predicate grid. NOT independent clinical labels.
No network/model calls; deterministic. Outputs coverage and 100% enumerated matching combinations.
"""
from __future__ import annotations
import copy, json, itertools, sys, importlib.util, hashlib, inspect, ast
from pathlib import Path
from datetime import date, timedelta
from collections import Counter
BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE))
import claimslens_rule_candidate as new
spec=importlib.util.spec_from_file_location('cl_historical', BASE/'claimslens_verifier_historical.py')
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
AS_OF=date(2026,10,17)
class FrozenDate(date):
 @classmethod
 def today(cls):return cls(2026,10,17)
old.date=FrozenDate
base=copy.deepcopy(next(c for c in new.CASES.values() if c['scenario']=='complete'))
order=base['orders'][0]
report=next(r for r in base['records'] if r['event']=='COMPLETED' and r['authority']=='RADIOLOGY_FINAL')
rd=date.fromisoformat(report['date']); cr=date.fromisoformat(order['created'])
status={'earlier_preorder':(cr-timedelta(days=1)).isoformat(),'earlier_valid':(rd-timedelta(days=1)).isoformat(),
 'same_day':rd.isoformat(),'later_valid':(rd+timedelta(days=1)).isoformat(),
 'future':'2027-01-01','unparseable':'not-a-date'}
assert cr < rd < AS_OF
field_keys=['patient_id','claim_id','order_id','kind','authority','signed','modality','anatomy','side','superseded']
other={'patient_id':'PAT-WRONG','claim_id':'CL-WRONG','order_id':'ORD-WRONG',
 'kind':'CONSULT','authority':'SCHEDULING','signed':False,'modality':'CT','anatomy':'left foot','side':'LEFT','superseded':True}
assert all(report[k]!=v for k,v in other.items())

# Developer-defined documentary oracle, independently written but NOT expert-adjudicated.
def expected(bits, age, event):
 signed=bits[field_keys.index('signed')]==0
 authority=bits[field_keys.index('authority')]==0
 matching=all(z==0 for z in bits)
 historical=not ((event in ('CANCELLED','REVOKED')) and signed and authority)
 revised=not ((event in ('CANCELLED','REVOKED')) and matching and age in ('same_day','later_valid','future','unparseable'))
 return historical,revised

observed=Counter(); mismatch=[]; samples={}; total=0
for bits in itertools.product((0,1),repeat=len(field_keys)):
 for age,when in status.items():
  for event in ('CANCELLED','REVOKED','OTHER'):
   case=copy.deepcopy(base);c=copy.deepcopy(report)
   c.update(id='GRID-CANCEL',event=event,date=when)
   for flag,k in zip(bits,field_keys):
    if flag:c[k]=other[k]
   case['records'].append(c)
   got0=bool(old.verify(case,order)['eligible_for_simulated_closure'])
   got1=bool(new.verify(case,order,as_of=AS_OF)['eligible_for_simulated_closure'])
   exp0,exp1=expected(bits,age,event)
   total+=1;observed[f'{int(got0)}->{int(got1)}']+=1
   if (got0,got1)!=(exp0,exp1):
    if len(mismatch)<15:mismatch.append({'bits':bits,'age':age,'event':event,'expected':[exp0,exp1],'observed':[got0,got1]})
   if all(v==0 for v in bits):samples[f'{event}_{age}']={'prior':got0,'current':got1}
assert not mismatch,(total,mismatch)

# Explicit multi-source permutations: expected program invariance (not clinical correctness).
import random
rng=random.Random(20261017)
patterns=[]
def candidate(age,mut=None,event='CANCELLED',idx=0):
 r=copy.deepcopy(report);r.update(id=f'MULTI-{idx}',event=event,date=status[age]);
 if mut:r.update(mut)
 return r
patterns=[
 [candidate('earlier_valid',idx=1),candidate('later_valid',idx=2)],
 [candidate('same_day',idx=1),candidate('later_valid',idx=2)],
 [candidate('future',idx=1),candidate('earlier_valid',idx=2)],
 [candidate('later_valid',{'patient_id':'OTHER'},idx=1),candidate('earlier_valid',idx=2)],
 [candidate('later_valid',{'signed':False},idx=1),candidate('same_day',idx=2)],
 [candidate('later_valid',{'authority':'SCHEDULING'},idx=1),candidate('later_valid',idx=2)],
]
multiple_permutations=0
for pattern in patterns:
 x=copy.deepcopy(base);x['records']+=pattern
 initial=new.verify(x,order,as_of=AS_OF)['eligible_for_simulated_closure']
 for _ in range(60):
  xx=copy.deepcopy(x);rng.shuffle(xx['records'])
  now=new.verify(xx,order,as_of=AS_OF)['eligible_for_simulated_closure']
  assert initial==now
  multiple_permutations+=1

# Source-line coverage in the targeted verifier, not whole-program branch or condition coverage.
def verify_linenos(fn):
 src,first=inspect.getsourcelines(fn);tree=ast.parse(''.join(src))
 return {first+n.lineno-1 for n in ast.walk(tree) if isinstance(n,ast.stmt) and hasattr(n,'lineno')}
relevant=verify_linenos(new.verify)
seen=set()
def tracer(frame,event,arg):
 if frame.f_code.co_filename==new.verify.__code__.co_filename and frame.f_code.co_name=='verify':
  if event=='line':seen.add(frame.f_lineno)
  return tracer
 return None
sys.settrace(tracer)
for c in new.CASES.values():
 for o in c['orders']:new.verify(c,o,as_of=AS_OF)
sys.settrace(None)
lines_fixture=seen.copy()
sys.settrace(tracer)
for age in status:
 for event in ('CANCELLED','REVOKED','OTHER'):
  for mut in ({}, {'patient_id':'WRONG'},{'claim_id':'WRONG'},{'order_id':'WRONG'},
              {'kind':'CONSULT'},{'authority':'SCHEDULING'},{'signed':False},
              {'modality':'CT'},{'anatomy':'left foot'},{'side':'LEFT'},{'superseded':True}):
   x=copy.deepcopy(base);r=candidate(age,mut,event=event);x['records'].append(r)
   new.verify(x,order,as_of=AS_OF)
sys.settrace(None)
lines_added=seen.copy()

scenarios=Counter(c['scenario'] for c in new.CASES.values())
result={'audit_date':AS_OF.isoformat(),'model_oracle':'developer-written reference rule, NOT independent clinical oracle',
 'factorial_dimensions':{k:['matching','changed'] for k in field_keys},
 'date_classes':status,'event_classes':['CANCELLED','REVOKED','OTHER'],
 'factorial_total':total,'oracle_disagreements':len(mismatch),'example_disagreements':mismatch,
 'outcomes_historical_to_current':dict(observed),'matching_cancel_samples':samples,
 'multi_record_patterns':len(patterns),'multi_record_order_permutations':multiple_permutations,
 'permutation_disagreements':0,
 'source_line_coverage':{'denominator_ast_statement_lines':len(relevant),
  'generator_executed_statement_lines':len(relevant & lines_fixture),
  'generator_plus_probes_executed_statement_lines':len(relevant & (lines_fixture | lines_added)),
  'generator_executed_line_numbers':sorted(relevant & lines_fixture),
  'newly_executed_line_numbers':sorted((relevant & lines_added)-lines_fixture),
  'disclaimer':'Source-line coverage within verify(); not MC/DC, branch coverage, clinical validity or test adequacy.'},
 'scenario_counts':dict(sorted(scenarios.items())),
 'counterexamples':'Same-author oracle, designed predicate grid; same-date ordering unresolved; clinical cancellation reinstatement unvalidated.'}
(BASE.parent/'results'/'factorial_grid.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ('factorial_total','oracle_disagreements','outcomes_historical_to_current','multi_record_order_permutations','source_line_coverage','scenario_counts')},indent=2))
