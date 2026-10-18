"""Comparison of historical and corrected documentary verifier on specified synthetic mutations. Not clinical validation."""
import copy, json, importlib.util
from pathlib import Path
from datetime import date,timedelta
import claimslens_rule_candidate as corrected
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('archived_prior',HERE/'claimslens_verifier_historical.py')
prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
class FrozenDate(date):
 @classmethod
 def today(cls):return cls(2026,10,17)
prior.date=FrozenDate
AS_OF=date(2026,10,17)
case=copy.deepcopy(next(x for x in corrected.CASES.values() if x['scenario']=='complete'))
order=case['orders'][0]
proof=next(x for x in case['records'] if x['event']=='COMPLETED' and x['authority']=='RADIOLOGY_FINAL')
proof_date=date.fromisoformat(proof['date'])

def run(x):
 a=prior.verify(x,order)
 b=corrected.verify(x,order,as_of=AS_OF)
 return {'historical':bool(a['eligible_for_simulated_closure']),'corrected':bool(b['eligible_for_simulated_closure']),'corrected_blockers':b.get('blockers',[])}
def extra(delta,**overrides):
 x=copy.deepcopy(case);r=copy.deepcopy(proof)
 r.update(id='NEW-TEST-SOURCE',event='CANCELLED',date=(proof_date+timedelta(days=delta)).isoformat());r.update(overrides);x['records'].append(r)
 return x
v={
 'baseline_complete':run(case),
 'unrelated_patient_cancellation':run(extra(2,patient_id='DIFFERENT-PATIENT')),
 'unrelated_claim_cancellation':run(extra(2,claim_id='DIFFERENT-CLAIM')),
 'unrelated_order_cancellation':run(extra(2,order_id='DIFFERENT-ORDER')),
 'earlier_matching_cancellation':run(extra(-1)),
 'later_matching_cancellation':run(extra(2)),
 'same_day_matching_cancellation':run(extra(0)),
 'future_matching_cancellation':run(extra(2,date='2027-01-01')),
 'unparseable_matching_cancellation':run(extra(2,date='not-a-date')),
 'unsigned_matching_cancellation':run(extra(2,signed=False)),
 'wrong_authority_cancellation':run(extra(2,authority='SCHEDULING')),
 'future_cancellation_requires_review':run(extra(2,date='2027-01-01')),
}
result={'as_of':'2026-10-17','exemplar_case':case['id'],'unit':'single constructed imaging case with one added cancellation record','cases':v,'note':'The comparison checks program behavior; the expected outcome is developer-defined, and a clinician did not adjudicate it.'}
(HERE/'audit_v7_comparison.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
