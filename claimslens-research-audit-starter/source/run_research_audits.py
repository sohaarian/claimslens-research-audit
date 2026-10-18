#!/usr/bin/env python3
"""Single user-facing command for reproducible deterministic research audits."""
import subprocess,sys,json,hashlib
from pathlib import Path
p=Path(__file__).resolve().parent
for filename in ('check_field_mutations.py','check_all_obligations.py','check_cancellation_behavior.py','check_renderer_sources.py','audit_factorial_grid.py','audit_conservative_policy.py'):
 r=subprocess.run([sys.executable,str(p/filename)],cwd=p,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=110)
 if r.returncode:raise RuntimeError(f'{filename} failed\n'+r.stdout[-900:]+r.stderr[-1300:])
f=json.loads((p.parent/'results'/'factorial_grid.json').read_text())
s=json.loads((p/'audit_v6_results.json').read_text())
c=json.loads((p/'audit_v7_comparison.json').read_text())
assert f['oracle_disagreements']==0 and f['factorial_total']==18432
assert f['multi_record_order_permutations']==360
assert s['original_vs_corrected_all_obligations']=={'total':1200,'changed':0}
assert c['cases']['future_matching_cancellation']['corrected'] is False
assert c['cases']['earlier_matching_cancellation']['corrected'] is True
out={'audit_date':'2026-10-17','verifier_sha256':hashlib.sha256((p/'claimslens_rule_candidate.py').read_bytes()).hexdigest(),
'factorial_design_test_cases':f['factorial_total'],'developer_oracle_disagreements':f['oracle_disagreements'],
'program_transitions_in_grid':f['outcomes_historical_to_current'],
'multi_source_permutations':f['multi_record_order_permutations'],
'generator_source_line_coverage':f['source_line_coverage'],
'generator_comparison':s['original_vs_corrected_all_obligations'],
'scenario_counts':f['scenario_counts'],
'limitations':['developer-authored rule specification','no clinical independent oracle','no fresh LLM test','no deployed route verification']}
(p.parent/'results'/'audit_summary.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
