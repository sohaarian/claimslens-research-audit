#!/usr/bin/env python3
"""One-command deterministic reproduction. No clinical validation or LLM inference."""
import subprocess,sys,json,hashlib,datetime
from pathlib import Path
BASE=Path(__file__).resolve().parent
SCRIPTS=['check_field_mutations.py','check_all_obligations.py','check_cancellation_behavior.py','check_renderer_sources.py']
RESULTS={'check_field_mutations.py':'audit_v2_results.json','check_all_obligations.py':'audit_v6_results.json','check_cancellation_behavior.py':'audit_v7_comparison.json','check_renderer_sources.py':'audit_explanation_grounding_results.json'}
ran={}
for s in SCRIPTS:
 p=subprocess.run([sys.executable,str(BASE/s)],cwd=BASE,capture_output=True,text=True,timeout=90)
 if p.returncode: raise RuntimeError(f'{s} failed:\n{p.stdout[-1500:]}\n{p.stderr[-1500:]}')
 ran[s]=json.loads((BASE/RESULTS[s]).read_text())
comparison=ran['check_cancellation_behavior.py']['cases']
assert comparison['future_matching_cancellation']['corrected'] is False
assert comparison['unparseable_matching_cancellation']['corrected'] is False
assert comparison['unrelated_patient_cancellation']['historical'] is False
assert comparison['unrelated_patient_cancellation']['corrected'] is True
counts=ran['check_all_obligations.py']
assert counts['original_vs_corrected_all_obligations']=={'changed':0,'total':1200}
assert sum(counts['documentarily_met_by_kind'].values())==283
assert len(ran['check_field_mutations.py']['mutation_checks'])==11
assert all(ran['check_field_mutations.py']['mutation_checks'].values())
assert len(ran['check_field_mutations.py']['regression_checks'])==8
assert all(ran['check_field_mutations.py']['regression_checks'].values())
summary={'audit_date':'2026-10-17','type':'deterministic software behavior, developer-defined tests',
'corrected_verifier_sha256':hashlib.sha256((BASE/'claimslens_verifier.py').read_bytes()).hexdigest(),
'historical_verifier_sha256':hashlib.sha256((BASE/'claimslens_verifier_historical.py').read_bytes()).hexdigest(),
'generated_obligations':1200,'generator_rule_met':283,'generator_rule_open':917,
'original_to_corrected_changed_on_generated_set':0,'imaging_cases':240,
'field_mutations_M1_M11':len(ran['check_field_mutations.py']['mutation_checks']),
'original_regressions_R1_R8':len(ran['check_field_mutations.py']['regression_checks']),
'cancellation_comparison_rows_including_baseline_and_duplicate':len(comparison),
'future_matching_cancel_corrected_eligible':comparison['future_matching_cancellation']['corrected'],
'unparseable_matching_cancel_corrected_eligible':comparison['unparseable_matching_cancellation']['corrected'],
'cancellation_probes':comparison,
'deterministic_renderer':ran['check_renderer_sources.py']['counts'],
'limitations':['single constructed cancellation case','developer-derived labels','no model rerun','no clinical verification','no live-site verification']}
(BASE/'verified_audit_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
