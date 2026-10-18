#!/usr/bin/env python3
"""Recompute ClaimsLens synthetic structural outcomes and test a corrected cancellation rule.
No model calls, patient data, or external services are used.
"""
import argparse, datetime as dt, hashlib, json, random, re, copy
from collections import Counter
from pathlib import Path
import claimslens_final as core
FIXED_AUDIT_SEED=20261014
RECEIPT_REGEX=r"final.{0,40}report.{0,30}(received|obtained|available|signed|uploaded)"

def run():
    ids=sorted(core.CASES)
    baseline={cid:core.evidence(core.CASES[cid])[0]['eligible_for_simulated_closure'] for cid in ids}
    truth={cid:core.CASES[cid]['scenario']=='complete' for cid in ids}
    decisions=[d for cid in ids for d in core.evidence(core.CASES[cid])]
    assert len(ids)==240 and len(decisions)==1200
    rng=random.Random(FIXED_AUDIT_SEED)
    shuffled_changed=0
    for cid in ids:
        case=copy.deepcopy(core.CASES[cid]); rng.shuffle(case['records'])
        shuffled_changed+=core.evidence(case)[0]['eligible_for_simulated_closure']!=baseline[cid]
    completed_src2=sum(1 for cid in ids if truth[cid] and any(r['id'].endswith('SRC02') and r['event']=='COMPLETED' and r['authority']=='RADIOLOGY_FINAL' for r in core.CASES[cid]['records']))
    all_emails=[e for cid in ids for e in core.CASES[cid]['emails']]
    email_hits=sum(bool(re.search(RECEIPT_REGEX,str(e['body']), re.I)) for e in all_emails)
    # independent probe: a complete case with unrelated cancellation must not flip
    exemplar=next(copy.deepcopy(core.CASES[cid]) for cid in ids if truth[cid]); claim=exemplar['id']; order=exemplar['orders'][0]
    candidate=next(r for r in exemplar['records'] if r['authority']=='RADIOLOGY_FINAL' and r['event']=='COMPLETED')
    unrelated=copy.deepcopy(candidate); unrelated.update(id=claim+'-TEST-OTHER',event='CANCELLED',patient_id='OTHER-PAT',claim_id='OTHER-CLAIM',order_id='OTHER-ORDER',date=(dt.date.fromisoformat(candidate['date'])+dt.timedelta(days=1)).isoformat())
    wrong=copy.deepcopy(exemplar); wrong['records'].append(unrelated)
    earlier=copy.deepcopy(exemplar); same=copy.deepcopy(unrelated);same.update(id=claim+'-TEST-EARLIER',patient_id=exemplar['patient_id'],claim_id=claim,order_id=order['order_id'],date=(dt.date.fromisoformat(candidate['date'])-dt.timedelta(days=1)).isoformat());earlier['records'].append(same)
    later=copy.deepcopy(exemplar);same2=copy.deepcopy(same);same2.update(id=claim+'-TEST-LATER',date=(dt.date.fromisoformat(candidate['date'])+dt.timedelta(days=2)).isoformat());later['records'].append(same2)
    probe={'unrelated_cancellation_does_not_flip':core.verify(wrong,order)['eligible_for_simulated_closure'],'earlier_cancellation_does_not_flip':core.verify(earlier,order)['eligible_for_simulated_closure'],'later_matching_cancellation_blocks':not core.verify(later,order)['eligible_for_simulated_closure']}
    summary={
      'as_of_date':dt.date.today().isoformat(), 'audit_seed':FIXED_AUDIT_SEED,
      'case_count':len(ids),'email_count':len(all_emails),'obligation_count':len(decisions),
      'supported_obligations':sum(d['eligible_for_simulated_closure'] for d in decisions),
      'rejected_obligations':sum(not d['eligible_for_simulated_closure'] for d in decisions),
      'supported_by_kind':dict(Counter(d['kind'] for d in decisions if d['eligible_for_simulated_closure'])),
      'generator_label_verifier_agreement':sum(baseline[cid]==truth[cid] for cid in ids),
      'shuffled_imaging_changed':shuffled_changed, 'complete_fixture_count':sum(truth.values()),
      'complete_with_src02':completed_src2,
      'email_search_regex':RECEIPT_REGEX, 'email_regex_hits':email_hits,
      'cancellation_regression':probe,
      'model_inference_repeated':False,
    }
    assert summary['generator_label_verifier_agreement']==240 and all(probe.values()) and shuffled_changed==0
    return summary

if __name__=='__main__':
    result=run(); print(json.dumps(result,indent=2,sort_keys=True))
    p=Path(__file__).with_name('audit_results_fresh.json');p.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
