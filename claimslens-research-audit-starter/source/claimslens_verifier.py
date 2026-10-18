#!/usr/bin/env python3
"""Conservative RESEARCH DEFAULT for structured fictional documentary tracking.

Runs a prior deterministic rule as a comparator, then holds any attached
cancellation/revocation/entered-in-error or amendment notice for reconciliation.
Does not infer clinical appropriateness or order reinstatement. NOT the hosted demo.
"""
from __future__ import annotations
from datetime import date
from enum import Enum
from typing import Any
import claimslens_rule_candidate as candidate

CASES = candidate.CASES
PROFILES = candidate.PROFILES
SCENARIOS = candidate.SCENARIOS
KINDS = candidate.KINDS
generate_cases = candidate.generate_cases

class DecisionState(str, Enum):
    DOCUMENT_FOUND = "DOCUMENT_FOUND"
    REVIEW_MISSING = "REVIEW_MISSING"
    REVIEW_CONFLICT = "REVIEW_CONFLICT"

ATTENTION_EVENTS = frozenset({"CANCELLED", "REVOKED", "ENTERED_IN_ERROR", "AMENDED", "CORRECTED", "SUPERSEDED"})
EVIDENCE_EVENTS = frozenset({"COMPLETED", "DOCUMENTED"})

def verify(case: dict[str, Any], order: dict[str, Any], *, as_of: date | str) -> dict[str, Any]:
    """Fail closed (for documentary auto-affirmation) on attached notices.

    A notice shares the tracking-item ID, even if its patient or order data do
    not match. This prioritizes surfacing data-integrity warnings over workload.
    It is a developer-defined triage choice, not a validated clinical policy.
    A reproducible as_of date is mandatory for this research API.
    """
    if as_of is None:
        raise ValueError("explicit as_of date is required")
    if isinstance(as_of,str):
        as_of=date.fromisoformat(as_of)
    if not isinstance(as_of,date):
        raise TypeError("as_of must be a date or ISO date string")
    linked=[r for r in case.get('records', []) if isinstance(r,dict) and r.get('obligation_id')==order.get('id')]
    malformed=[i for i,r in enumerate(case.get('records', [])) if not isinstance(r,dict)]
    # Potential contradictory notices are *warnings* even when their signature,
    # identity, date or authority is invalid. They are not deemed authentic vetoes.
    notices=[r for r in linked if str(r.get('event','')).upper() in ATTENTION_EVENTS]
    notice_ids=[str(r.get('id','<missing-id>')) for r in notices]
    try:
        raw=candidate.verify(case,order,as_of=as_of)
    except (KeyError,TypeError,ValueError) as exc:
        raw={'id':order.get('id'), 'kind':order.get('kind'), 'blockers':['MALFORMED_STRUCTURED_SOURCE'],
             'traces':[], 'citations':[], 'eligible_for_simulated_closure':False,
             'input_error_type':type(exc).__name__}
    candidate_eligible=bool(raw.get('eligible_for_simulated_closure',False))
    contested=bool(notices or malformed or 'MALFORMED_STRUCTURED_SOURCE' in raw.get('blockers',[]))
    other_evidence=[r for r in linked if str(r.get('event','')).upper() in EVIDENCE_EVENTS]
    # Non-authoritative completion-like records generate a conflict to investigate,
    # not a positive status. This is not an independent truth judgment.
    state=(DecisionState.REVIEW_CONFLICT if contested or (not candidate_eligible and other_evidence)
           else DecisionState.DOCUMENT_FOUND if candidate_eligible
           else DecisionState.REVIEW_MISSING)
    reasons=list(raw.get('blockers', []))
    if notices:reasons.append('ATTACHED_STATUS_NOTICE_REQUIRES_RECONCILIATION')
    if malformed:reasons.append('MALFORMED_RECORD_REQUIRES_RECONCILIATION')
    if state==DecisionState.REVIEW_CONFLICT and not reasons:reasons.append('CONFLICTING_OR_NONQUALIFYING_EVIDENCE')
    if state==DecisionState.REVIEW_MISSING and not reasons:reasons.append('NO_QUALIFYING_SOURCE')
    return {
        'tracking_item_id':order.get('id'), 'state':state.value,
        'status':{'DOCUMENT_FOUND':'Document found — unreviewed evidence',
                  'REVIEW_MISSING':'Review required — evidence missing',
                  'REVIEW_CONFLICT':'Review required — evidence conflict'}[state.value],
        'documentary_eligible':state==DecisionState.DOCUMENT_FOUND,
        'candidate_rule_eligible':candidate_eligible,
        'source_ids_considered':[str(r.get('id','<missing-id>')) for r in linked],
        'conflicting_notice_ids':notice_ids,
        'support_source_ids':list(raw.get('citations',[])) if state==DecisionState.DOCUMENT_FOUND else [],
        'inspection_source_ids':list(dict.fromkeys(str(r.get('id','<missing-id>')) for r in linked)),
        'blockers':list(dict.fromkeys(reasons)),
        'as_of':as_of.isoformat(), 'policy':'CONSERVATIVE_RESEARCH_DEFAULT_V1',
        'real_claim_updated':False,
        'legacy_candidate_result':raw,
    }

def evidence(case: dict[str,Any], *, as_of: date | str) -> list[dict[str,Any]]:
    return [verify(case,o,as_of=as_of) for o in case['orders']]
