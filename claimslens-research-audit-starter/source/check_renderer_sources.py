#!/usr/bin/env python3
"""Synthetic-only check of deterministic source-linked explanations, NOT LLM fidelity."""
import json, re, copy, random
from collections import Counter
from pathlib import Path
import claimslens_one_paste_studio as studio
import claimslens_rule_candidate as core

SOURCE_RE = re.compile(r'CL-\d{4}-SRC\d{2}')
rng=random.Random(20261014)
counts=Counter(); failures=[]
for cid,case in core.CASES.items():
    response=studio.sourced_summary(cid,'imaging status')
    known={r['id'] for r in case['records']}
    decisions=[d for d in core.evidence(case) if d['kind']=='IMAGING']
    assert len(decisions)==1
    d=decisions[0]
    cited=set(SOURCE_RE.findall(response))
    counts['evaluated_cases']+=1
    counts['unique_cited_ids_across_cases']+=len(cited)
    # all mentioned citation locators must correspond to an existing source
    if not cited.issubset(known): failures.append([cid,'unknown source ID',list(cited-known)])
    else:counts['valid_locator_cases']+=1
    expected=set(d['citations']) if d['eligible_for_simulated_closure'] else set()
    # Source adapter stores proof separately, so each proof cited must be a qualifying source.
    proof_line=next((line for line in response.splitlines() if line.startswith('Supporting completion citations:')),None)
    if proof_line is None: failures.append([cid,'missing proof field'])
    else:
        proof=set(SOURCE_RE.findall(proof_line))
        if proof != expected:
            failures.append([cid,'proof mismatch',sorted(proof),sorted(expected)])
        else:counts['proof_set_matches_core']+=1
    # Proof and inspection identifiers are semantically different; count separately.
    inspection_line=next((line for line in response.splitlines() if line.startswith('Rejection/inspection citations')),None)
    if inspection_line is not None:
        counts['unique_inspection_ids_across_cases'] += len(set(SOURCE_RE.findall(inspection_line)))
    counts['unique_proof_ids_across_cases'] += len(expected)
    # Explicit smoke assertions for rejected-document links and safe status labels.
    if not d['eligible_for_simulated_closure'] and d.get('traces'):
        counts['open_imaging_with_inspected_records'] += 1
        inspected = set(SOURCE_RE.findall(inspection_line or ''))
        if inspected:
            counts['open_imaging_with_nonempty_inspection_ids'] += 1
        else:
            failures.append([cid, 'open imaging lacks inspection citations'])
    if d['eligible_for_simulated_closure']:
        if d['status'] == 'REPORT DOCUMENTED - SYNTHETIC':
            counts['accepted_imaging_safe_label'] += 1
        else:
            failures.append([cid, 'unexpected positive status label', d['status']])

    # A misleading but nonqualifying structured source must not change completion.
    misleading=copy.deepcopy(case)
    fake=copy.deepcopy(misleading['records'][0])
    fake['id']=f'{cid}-SRC99'
    fake['event']='COMPLETED'
    fake['patient_id']='WRONG-PATIENT-DECOY'
    fake['claim_id']='WRONG-CLAIM-DECOY'
    fake['signed']=True
    misleading['records'].append(fake)
    md=[x for x in core.evidence(misleading) if x['kind']=='IMAGING'][0]
    if md['eligible_for_simulated_closure'] != d['eligible_for_simulated_closure']:
        failures.append([cid,'misleading record changed verdict'])
    else:counts['misleading_wrong_patient_record_invariant_cases']+=1
    # Invariance controls: unrelated changes must not change the documentary verdict.
    shuffled=copy.deepcopy(case);rng.shuffle(shuffled['records'])
    if core.evidence(shuffled)[0]['eligible_for_simulated_closure'] != d['eligible_for_simulated_closure']:
        failures.append([cid,'shuffled verdict changed'])
    else: counts['shuffle_invariant_cases']+=1
    extra=copy.deepcopy(case)
    if extra['emails']:
        extra['emails'][0]['body'] += '\nIrrelevant clerical greeting, no imaging evidence.'
    if core.evidence(extra)[0]['eligible_for_simulated_closure'] != d['eligible_for_simulated_closure']:
        failures.append([cid,'email-only text edit changed verdict'])
    else: counts['irrelevant_email_invariant_cases']+=1
out={'scope':'Deterministic source-linked studio summary and structured-source perturbation; no Qwen inference',
     'seed':20261014,'counts':dict(counts),'failures':failures,
     'clinical_faithfulness_measured':False,'llm_faithfulness_measured':False}
path=Path(__file__).with_name('audit_explanation_grounding_results.json')
path.write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
assert not failures, failures[:5]
