#!/usr/bin/env python3
"""Research-only, fixed-as-of checks of conservative package policy and generator structure."""
from __future__ import annotations
import sys,json,collections,copy,itertools,hashlib
from pathlib import Path
from datetime import date
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P))
import claimslens_verifier as safe
import claimslens_rule_candidate as candidate
AS_OF=date(2026,10,17)
cs=list(safe.CASES.values())
count=collections.Counter(c['scenario'] for c in cs)
profile_matrix=collections.defaultdict(set)
for c in cs:profile_matrix[c['title']].add(c['scenario'])
intersection_total=len(cs)
unique_cells=sum(map(len,profile_matrix.values()))
missing_complete=[p for p,v in profile_matrix.items() if 'complete' not in v]
case_order_counts=collections.Counter()
comparisons=collections.Counter()
for c in cs:
 for o in c['orders']:
  old=candidate.verify(c,o,as_of=AS_OF)
  new=safe.verify(c,o,as_of=AS_OF)
  case_order_counts[(o['kind'],new['state'])]+=1
  comparisons[(o['kind'],int(old['eligible_for_simulated_closure']),int(new['documentary_eligible']))]+=1
assert len(cs)==240 and sum(count.values())==240 and len(profile_matrix)==24
# Characterize correlations, not independent endpoint truth.
modulo={}
for j,kind in enumerate(safe.KINDS[1:],1):
 done_indices=[i for i,c in enumerate(cs) if candidate.verify(c,c['orders'][j],as_of=AS_OF)['eligible_for_simulated_closure']]
 modulo[kind]={'count':len(done_indices),'profile_count':len({cs[i]['title'] for i in done_indices}),
               'sample_case_indices_0_based':done_indices[:10]}
# Only illustrative mutation of *existing records*: untrusted completion and notice hold.
policy_examples={}
case=copy.deepcopy(next(c for c in cs if c['scenario']=='complete'))
order=case['orders'][0]
report=next(r for r in case['records'] if r['event']=='COMPLETED' and r['kind']=='IMAGING')
for k,changed in [('no_notice',None),('untrusted_notice',{'event':'CANCELLED','signed':False}),
                  ('cross_patient_notice',{'event':'CANCELLED','patient_id':'OTHER'}),
                  ('matching_prior_notice',{'event':'CANCELLED','date':order['created']}),
                  ('entered_in_error_notice',{'event':'ENTERED_IN_ERROR'}),
                  ('mismatched_modality',{'event':'CANCELLED','modality':'UNRELATED'})]:
 x=copy.deepcopy(case)
 if changed is not None:
  r=copy.deepcopy(report);r.update(id='ADDITIONAL',date='2026-06-01');r.update(changed);x['records'].append(r)
 v=safe.verify(x,order,as_of=AS_OF)
 policy_examples[k]={'state':v['state'],'candidate_rule_eligible':v['candidate_rule_eligible'],
                    'source_warnings':v['conflicting_notice_ids']}
 assert (v['state']=='DOCUMENT_FOUND') == (changed is None)
result={'fixed_as_of':AS_OF.isoformat(),'generator_total':len(cs),'profile_templates':len(profile_matrix),
 'imaging_scenarios':dict(sorted(count.items())),
 'profile_scenario_cells_observed':unique_cells,'possible_profile_scenario_cells':24*16,
 'scenarios_per_profile':dict(collections.Counter(len(v) for v in profile_matrix.values())),
 'profiles_without_complete':missing_complete,
 'non_imaging_modulo_composition':modulo,
 'states_by_kind':{k:{st:n for (kk,st),n in case_order_counts.items() if kk==k} for k in safe.KINDS},
 'candidate_to_safe':{f'{kind}:{a}->{b}':n for (kind,a,b),n in comparisons.items()},
 'illustrative_policy_probes':policy_examples,
 'canonical_sha256':hashlib.sha256((P/'claimslens_verifier.py').read_bytes()).hexdigest(),
 'candidate_sha256':hashlib.sha256((P/'claimslens_rule_candidate.py').read_bytes()).hexdigest(),
 'warning':'This measures deterministic policy outputs and generator design, not clinical accuracy or beneficial safety impact.'}
D=P.parent/'results';D.mkdir(exist_ok=True)
(D/'policy_generator_results.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ('generator_total','profile_templates','profile_scenario_cells_observed','possible_profile_scenario_cells','scenarios_per_profile','profiles_without_complete','states_by_kind','candidate_to_safe','illustrative_policy_probes')},indent=2))
