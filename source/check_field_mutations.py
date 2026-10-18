#!/usr/bin/env python3
"""Reproducible structure/mutation audit. No clinical data or LLM calls."""
import copy, json, random, re, hashlib, importlib.util
from pathlib import Path
from collections import Counter
from datetime import date, timedelta
import claimslens_rule_candidate as core

AS_OF = date(2026,10,17)
SHUFFLE_SEED = 20261014
EMAIL_PATTERNS = [
 r'final.{0,50}report.{0,50}(?:received|obtained|available|signed|uploaded)',
 r'(?:received|obtained|available|signed|uploaded).{0,50}(?:the\s+)?final.{0,30}report',
 r'(?:radiology|imaging).{0,35}report.{0,35}(?:received|obtained|available)',
]

def verdict(case):
 return core.verify(case,case['orders'][0],as_of=AS_OF)['eligible_for_simulated_closure']

def main():
 cases=core.CASES
 reference=Path(__file__).parent.parent/'archived_reference'/'claimslens_verifier_historical.py'
 spec=importlib.util.spec_from_file_location('claimslens_original_snapshot',reference)
 original_core=importlib.util.module_from_spec(spec); spec.loader.exec_module(original_core)
 class FrozenDate(date):
  @classmethod
  def today(cls):return cls(2026,10,17)
 original_core.date=FrozenDate
 original_matches=sum(
  original_core.verify(c,c['orders'][0])['eligible_for_simulated_closure']==(c['scenario']=='complete')
  for c in original_core.CASES.values())
 original={cid:verdict(c) for cid,c in cases.items()}
 labels={cid:c['scenario']=='complete' for cid,c in cases.items()}
 assert len(cases)==240
 scenario_counts=dict(sorted(Counter(c['scenario'] for c in cases.values()).items()))
 # one seeded shuffle per case; not all permutations
 rng=random.Random(SHUFFLE_SEED)
 changed=0
 for cid,c in cases.items():
  t=copy.deepcopy(c);rng.shuffle(t['records']);changed+=verdict(t)!=original[cid]
 # One verified complete exemplar. Decoys retain obligation pointer by design.
 cid=next(k for k,v in labels.items() if v)
 c=copy.deepcopy(cases[cid]);order=c['orders'][0]
 good=next(r for r in c['records'] if r['event']=='COMPLETED' and r['authority']=='RADIOLOGY_FINAL')
 good_day=date.fromisoformat(good['date'])
 def with_record(*,event='CANCELLED',days=1,**overrides):
  x=copy.deepcopy(c);r=copy.deepcopy(good)
  r.update(id=cid+'-DEC'+str(days)+str(len(overrides)),event=event,date=(good_day+timedelta(days=days)).isoformat(),**overrides)
  x['records'].append(r);return x
 def run(x):return core.verify(x,order,as_of=AS_OF)
 tests={
  'unrelated_patient':run(with_record(patient_id='UNRELATED-PATIENT'))['eligible_for_simulated_closure'],
  'unrelated_claim':run(with_record(claim_id='UNRELATED-CLAIM'))['eligible_for_simulated_closure'],
  'unrelated_order':run(with_record(order_id='UNRELATED-ORDER'))['eligible_for_simulated_closure'],
  'earlier_cancellation':run(with_record(days=-1))['eligible_for_simulated_closure'],
  'later_matching_cancellation':not run(with_record(days=2))['eligible_for_simulated_closure'],
  'same_day_conflict':('SAME_DAY_OR_UNDATED_CANCELLATION_NEEDS_REVIEW' in run(with_record(days=0))['blockers'] and not run(with_record(days=0))['eligible_for_simulated_closure']),
 }
 reinstated=with_record(days=1)
 r=copy.deepcopy(good);r.update(id=cid+'-REINSTATEMENT',date=(good_day+timedelta(days=2)).isoformat())
 reinstated['records'].append(r)
 tests['newer_completion_after_cancellation']=run(reinstated)['eligible_for_simulated_closure']
 # Field-level mutation: start with a completed case; change one required field
 mutations={
  'patient_id':'OTHER','claim_id':'OTHER','order_id':'OTHER','authority':'SCHEDULING',
  'signed':False,'event':'SCHEDULED','superseded':True,
  'date':(date.fromisoformat(order['created'])-timedelta(days=1)).isoformat(),
  'anatomy':'left ankle' if c['anatomy']!='left ankle' else 'right ankle',
  'side':'LEFT' if good['side']!='LEFT' else 'RIGHT',
  'modality':'OTHER'}
 mutation_results={}
 for field,value in mutations.items():
  x=copy.deepcopy(c)
  rec=next(r for r in x['records'] if r['id']==good['id'])
  rec[field]=value
  mutation_results[field]=not verdict(x)
 # check order-position robust to added unrelated completed decoy
 x=copy.deepcopy(c);r=copy.deepcopy(good);r.update(id=cid+'-WRONG-PATIENT-COMPLETED',patient_id='OTHER')
 x['records'].append(r);rng.shuffle(x['records'])
 tests['wrong_patient_completed_decoy']=verdict(x)
 emails=[e['body'] for c in cases.values() for e in c['emails']]
 hits={f'pattern_{i+1}':sum(bool(re.search(p,b,re.I|re.S)) for b in emails) for i,p in enumerate(EMAIL_PATTERNS)}
 all_decisions=[d for c in cases.values() for d in core.evidence(c)]
 summary={
  'as_of':AS_OF.isoformat(),'shuffle_seed':SHUFFLE_SEED,
  'cases':len(cases),'emails':len(emails),'obligations':len(all_decisions),
  'open_obligations':sum(not d['eligible_for_simulated_closure'] for d in all_decisions),
  'supported_obligations':sum(d['eligible_for_simulated_closure'] for d in all_decisions),
  'initial_verifier_label_agreement':original_matches,
  'corrected_verifier_label_agreement':sum(original[cid]==labels[cid] for cid in cases),
  'scenario_counts':scenario_counts,
  'shuffled_imaging_changed':changed,
  'complete_source_02_count':sum(any(r['id'].endswith('SRC02') and r['event']=='COMPLETED' and r['authority']=='RADIOLOGY_FINAL' for r in c['records']) for c in cases.values() if c['scenario']=='complete'),
  'email_patterns':EMAIL_PATTERNS,'email_hits':hits,
  'mutation_checks':mutation_results,'regression_checks':tests,
  'case_CL_0038_scenario':cases['CL-0038']['scenario'],
  'qwen_rerun_performed':False,
 }
 assert all(tests.values()) and all(mutation_results.values()),(tests,mutation_results)
 assert summary['initial_verifier_label_agreement']==240
 assert summary['corrected_verifier_label_agreement']==240 and summary['shuffled_imaging_changed']==0
 assert summary['supported_obligations']==283 and summary['open_obligations']==917
 (Path(__file__).parent/'audit_v2_results.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
 print(json.dumps(summary,indent=2,sort_keys=True))
if __name__=='__main__':main()
