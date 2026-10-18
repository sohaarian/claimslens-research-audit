#!/usr/bin/env python3
"""Demonstrate policy trade-offs, not clinical harm reduction."""
import copy, json, sys
from pathlib import Path
from datetime import date,timedelta
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P))
import claimslens_rule_candidate as v
from experimental_triage import triage
ex=copy.deepcopy(next(c for c in v.CASES.values() if c['scenario']=='complete'))
o=ex['orders'][0];report=next(r for r in ex['records'] if r['event']=='COMPLETED' and r['authority']=='RADIOLOGY_FINAL')
base=date.fromisoformat(report['date']);asof=date(2026,10,17)
rows={}
for label,mod in [('no_notice',{}),('prior_matching',{'date':(base-timedelta(days=1)).isoformat()}),
 ('later_matching',{'date':(base+timedelta(days=1)).isoformat()}),
 ('future_matching',{'date':'2027-01-01'}),('unsigned_matching',{'signed':False}),
 ('wrong_authority',{'authority':'SCHEDULING'}),('wrong_patient',{'patient_id':'DIFFERENT'}),
 ('wrong_service',{'kind':'CONSULT'}),('revocation',{'event':'REVOKED'})]:
  case=copy.deepcopy(ex)
  if label!='no_notice':
   r=copy.deepcopy(report);r.update(id='EXTRA-CANCEL',event='CANCELLED',date=(base+timedelta(days=1)).isoformat());r.update(mod);case['records'].append(r)
  ref=v.verify(case,o,as_of=asof)
  t=triage(case,o,as_of=asof)
  rows[label]={'canonical_eligible':ref['eligible_for_simulated_closure'],'experimental_state':t['state'],'reason':t['reasons']}
assert rows['prior_matching']['canonical_eligible'] is True
assert rows['prior_matching']['experimental_state']=='REVIEW_CONFLICT'
assert rows['wrong_patient']['canonical_eligible'] is True
assert rows['wrong_patient']['experimental_state']=='REVIEW_CONFLICT'
assert rows['no_notice']['experimental_state']=='DOCUMENT_FOUND'
q={'as_of':str(asof),'author_defined_policy_only':True,'clinical_validity':'unknown','rows':rows}
(P.parent/'results'/'experimental_triage.json').write_text(json.dumps(q,indent=2)+'\n')
print(json.dumps(rows,indent=2))
