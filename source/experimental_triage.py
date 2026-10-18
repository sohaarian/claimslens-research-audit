"""UNVALIDATED research-only conservative documentary triage overlay.
Does NOT change canonical verifier or public demo; needs stakeholder requirements before deployment.
"""
from datetime import date
import claimslens_rule_candidate as core

def triage(case, order, *, as_of):
    base=core.verify(case,order,as_of=as_of)
    accepted=bool(base['eligible_for_simulated_closure'])
    if not accepted:
        blockers=base.get('blockers',[])
        has_conflict=any('CANCEL' in b or 'UNDATED' in b for b in blockers)
        if any(t.get('failed') and (t['checks'].get('completed_event') or t['checks'].get('source_authority')) for t in base['traces']):
            has_conflict=True
        return {'state':'REVIEW_CONFLICT' if has_conflict else 'REVIEW_MISSING', 'reasons':blockers,'base_eligible':False,'policy':'experimental'}
    linked=[r for r in case['records'] if r['obligation_id']==order['id']]
    cands=[r for r in linked if r.get('event') in ('CANCELLED','REVOKED')]
    if cands:
        # Explicitly conservative policy: any attached cancel/revoke is a conflict to resolve,
        # regardless of provenance, until workflow-specific authority and reinstatement rules exist.
        return {'state':'REVIEW_CONFLICT','reasons':['CANCEL_OR_REVOKE_ATTACHED_REQUIRES_MANUAL_RECONCILIATION'],
                'base_eligible':True,'policy':'experimental'}
    return {'state':'DOCUMENT_FOUND','reasons':[],'base_eligible':True,'policy':'experimental'}
