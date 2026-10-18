#!/usr/bin/env python3
"""Small, transparent mutation experiment on the research-policy module.
Only 5 hand-selected source edits. This is NOT a full mutmut campaign, clinical
validation, or percentage estimate for the overall codebase.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
import subprocess,sys,json,shutil
BASE=Path(__file__).resolve().parents[1]
original=(BASE/'source'/'claimslens_verifier.py').read_text()
pattern="notices=[r for r in linked if str(r.get('event','')).upper() in ATTENTION_EVENTS]"
state_pattern="state=(DecisionState.REVIEW_CONFLICT if contested or (not candidate_eligible and other_evidence)"
assert original.count(pattern)==1 and original.count(state_pattern)==1
mutants={
 'M01_remove_all_notices':("ATTENTION_EVENTS = frozenset({", "ATTENTION_EVENTS = frozenset({"),
 'M02_require_notice_signature':(pattern,pattern[:-1]+" and bool(r.get('signed'))]"),
 'M03_trust_identity_mismatch':(pattern,pattern[:-1]+" and r.get('patient_id')==case.get('patient_id')]"),
 'M04_ignore_future_notice':(pattern,pattern[:-1]+" and str(r.get('date','')) <= as_of.isoformat()]"),
 'M05_ignore_all_notice_conflicts':(state_pattern,"state=(DecisionState.REVIEW_CONFLICT if (not candidate_eligible and other_evidence)"),
}
results={}
with TemporaryDirectory(prefix='claims_mutant_') as td:
 root=Path(td);(root/'source').mkdir();(root/'tests').mkdir()
 shutil.copy2(BASE/'source'/'claimslens_rule_candidate.py',root/'source'/'claimslens_rule_candidate.py')
 shutil.copy2(BASE/'tests'/'test_conservative_policy.py',root/'tests'/'test_conservative_policy.py')
 for name,(old,new) in mutants.items():
  if name=='M01_remove_all_notices':
   altered=original.replace("ATTENTION_EVENTS = frozenset({\"CANCELLED\", \"REVOKED\", \"ENTERED_IN_ERROR\", \"AMENDED\", \"CORRECTED\", \"SUPERSEDED\"})", "ATTENTION_EVENTS = frozenset()")
  else:
   assert old in original, name
   altered=original.replace(old,new)
  assert altered!=original, name
  (root/'source'/'claimslens_verifier.py').write_text(altered)
  res=subprocess.run([sys.executable,'-m','pytest','-q',str(root/'tests'/'test_conservative_policy.py')],
                     cwd=root,capture_output=True,text=True,timeout=40)
  results[name]={'detected_by_failing_test':res.returncode!=0,
                 'exit_status':res.returncode,'tail':(res.stdout+res.stderr)[-330:]}
  if res.returncode==0:print('SURVIVED',name)
score={'seeded_mutants':len(results),'detected':sum(r['detected_by_failing_test'] for r in results.values()),
       'mutants':results,'interpretation':'Hand-selected edit detection; not a standard tool mutation score.'}
(BASE/'results'/'seeded_fault_detection.json').write_text(json.dumps(score,indent=2)+'\n')
print(json.dumps(score,indent=2))
