"""Deterministic tests of developer-defined conservative research policy; NOT a clinical oracle."""
import copy, sys, random
from datetime import date, timedelta
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'source'))
import claimslens_verifier as conservative
import claimslens_rule_candidate as candidate
AS_OF = date(2026, 10, 17)

@pytest.fixture
def exemplar():
    c=copy.deepcopy(next(v for v in candidate.CASES.values() if v['scenario']=='complete'))
    return c, c['orders'][0]

def attach(c, o, **changes):
    report=next(r for r in c['records'] if r['event']=='COMPLETED' and r['kind']=='IMAGING')
    r=copy.deepcopy(report)
    r.update(id=f"PROBE-{len(c['records'])}", event='CANCELLED',date=(date.fromisoformat(report['date'])+timedelta(days=1)).isoformat())
    r.update(changes)
    c['records'].append(r)
    return r

@pytest.mark.parametrize('field,bad',[
    ('patient_id','FOREIGN-PATIENT'), ('claim_id','FOREIGN-CLAIM'), ('order_id','FOREIGN-ORDER'),
    ('kind','CONSULT'),('authority','SCHEDULING'),('signed',False),('modality','CT'),
    ('anatomy','wrong-site'),('side','LEFT'),('superseded',True),('date','2027-01-01'),
    ('date','bad-date'),('event','REVOKED'),('event','ENTERED_IN_ERROR'),
    ('event','AMENDED'),('event','CORRECTED')])
def test_notice_never_auto_affirms(exemplar,field,bad):
    c,o=exemplar;attach(c,o,**{field:bad})
    got=conservative.verify(c,o,as_of=AS_OF)
    assert got['state']=='REVIEW_CONFLICT'
    assert not got['documentary_eligible']
    assert got['conflicting_notice_ids']
    assert not got['support_source_ids']

@pytest.mark.parametrize('delta',[-2,-1,0,1,2,1000])
def test_dates_before_and_after_report_review(exemplar,delta):
    c,o=exemplar
    report=next(r for r in c['records'] if r['event']=='COMPLETED' and r['kind']=='IMAGING')
    attach(c,o,date=(date.fromisoformat(report['date'])+timedelta(days=delta)).isoformat())
    assert conservative.verify(c,o,as_of=AS_OF)['state']=='REVIEW_CONFLICT'

def test_completion_without_notice_is_found(exemplar):
    c,o=exemplar;out=conservative.verify(c,o,as_of=AS_OF)
    assert out['state']=='DOCUMENT_FOUND'
    assert out['documentary_eligible']
    assert len(out['support_source_ids'])==1

def test_missing_source_is_missing(exemplar):
    c,o=exemplar
    c['records']=[r for r in c['records'] if r.get('event')!='COMPLETED' or r.get('kind')!='IMAGING']
    assert conservative.verify(c,o,as_of=AS_OF)['state']=='REVIEW_MISSING'

def test_mismatched_completion_is_conflict(exemplar):
    c,o=exemplar
    next(r for r in c['records'] if r['event']=='COMPLETED' and r['kind']=='IMAGING')['patient_id']='WRONG'
    assert conservative.verify(c,o,as_of=AS_OF)['state']=='REVIEW_CONFLICT'

def test_malformed_source_not_affirmed(exemplar):
    c,o=exemplar;c['records'].append(None)
    assert conservative.verify(c,o,as_of=AS_OF)['state']=='REVIEW_CONFLICT'

def test_future_signed_completion_is_not_document_found(exemplar):
    c,o=exemplar
    next(r for r in c['records'] if r['event']=='COMPLETED' and r['kind']=='IMAGING')['date']='2027-01-01'
    assert conservative.verify(c,o,as_of=AS_OF)['state']=='REVIEW_CONFLICT'

@pytest.mark.parametrize('name', ['patient_id','claim_id','order_id','authority','signed','side','anatomy','modality','date'])
def test_missing_completion_fields_not_auto_accepted(exemplar,name):
    c,o=exemplar
    next(r for r in c['records'] if r['event']=='COMPLETED' and r['kind']=='IMAGING').pop(name)
    assert conservative.verify(c,o,as_of=AS_OF)['state']!='DOCUMENT_FOUND'

def test_multi_records_order_invariance(exemplar):
    c,o=exemplar
    attach(c,o,patient_id='WRONG');attach(c,o,signed=False)
    got=conservative.verify(c,o,as_of=AS_OF)['state']
    rng=random.Random(173)
    for _ in range(100):
        x=copy.deepcopy(c);rng.shuffle(x['records'])
        assert conservative.verify(x,o,as_of=AS_OF)['state']==got

def test_explicit_as_of_required(exemplar):
    c,o=exemplar
    with pytest.raises((TypeError,ValueError)):
        conservative.verify(c,o)
    assert conservative.verify(c,o,as_of='2026-10-17')['state']=='DOCUMENT_FOUND'

@pytest.mark.parametrize('scenario', ['complete','scheduled_only','wrong_patient','cancelled','revoked','superseded','email_claim'])
def test_generator_smoke_states(scenario):
    c=next(c for c in conservative.CASES.values() if c['scenario']==scenario)
    result=conservative.verify(c,c['orders'][0],as_of=AS_OF)
    assert result['state'] in {'DOCUMENT_FOUND','REVIEW_MISSING','REVIEW_CONFLICT'}
    assert result['as_of']=='2026-10-17'

@pytest.mark.parametrize('event', ['CANCELLED','REVOKED','ENTERED_IN_ERROR','AMENDED','CORRECTED','SUPERSEDED'])
def test_notices_even_with_wrong_identity_flagged(exemplar,event):
    c,o=exemplar; attach(c,o,event=event,patient_id='WRONG',signed=False)
    assert conservative.verify(c,o,as_of=AS_OF)['state']=='REVIEW_CONFLICT'
