# ClaimsLens: Research evidence-integrity report (17 October 2026)

This is a **research artifact**, not a clinical decision-support deployment or a clinical safety certification. All cases are fictional. The hosted demonstration is a separate codebase and has **not** been confirmed to use the research default below.

## Which verifier is which?

- `source/claimslens_verifier_historical.py`: archived historical implementation with the broad cancellation veto.
- `source/claimslens_rule_candidate.py`: identity-aware, chronology-sensitive but **permissive** candidate from the earlier comparison. A later completion can override an earlier cancellation without proof of reinstatement. Retained to reproduce the original 18,432-cell software grid, *not* designated as a clinical policy.
- `source/claimslens_verifier.py`: **research default**. Requires explicit `as_of` and returns `DOCUMENT_FOUND`, `REVIEW_MISSING`, or `REVIEW_CONFLICT`. An attached cancellation/revocation/status notice causes `REVIEW_CONFLICT` even when identity or authority differs; this may create extra reviews. It is an unvalidated developer decision, not an accepted medical standard.
- `source/claimslens_final.py` and older demo modules: legacy compatibility code required by historical UI/renderer scripts; not the default research policy, and not evidence of a fixed live deployment.

## Reproduce the software tests

Python 3.12 or 3.13 recommended. The research wrapper uses only the standard library; `pytest` and `coverage` are pinned in `requirements-research.txt` for the tests. **No Ollama instance is required** for these audits.

```bash
python -m pip install -r requirements-research.txt
python source/run_research_audits.py
python source/audit_policy_generator.py
python source/audit_seeded_faults.py
python -m coverage run --branch --source=claimslens_verifier -m pytest -q tests/test_conservative_policy.py
python -m coverage report -m
```

Expected from the executed Oct 17 research set:
- Historic/candidate rule enumeration: 18,432 developer-defined combinations, 3,064 ineligible-to-eligible transitions, no eligible-to-ineligible transitions, 360 multi-record permutations without Boolean change.
- Generated set: 240 cases, five tracking items each; 283 documentary states programmed positive in the candidate and research default, 917 other states. Research default splits non-document states into 782 missing and 135 conflict.
- Generator: 24 profiles, 16 scenario names, only 240 of 384 potential profile/scenario combinations exercised; nine profiles never appear in a complete imaging example.
- Default module: 51 passing pytest parameterized cases across 12 test functions; 90% combined line/branch coverage (not the whole application); five **hand-selected** seeded source faults detected.

## Model-extraction research is not complete

`source/benchmark_extraction_scaffold.py` only checks two supplied JSONL files. This release does not contain independently reviewed medical report labels, model prompts, an Ollama rerun, field-level extraction metrics, nurse usability studies or a clinically approved cancellation/reinstatement policy. Do not rephrase the synthetic tests as medical accuracy.

## Public link and reproducibility

The public demonstration repository is https://github.com/sohaarian/claimslens-public-demo . It is not a published, tagged research audit release and must not be cited as containing the three research-policy modules above until they are actually uploaded and verified. No DOI has been assigned. SHA-256 values in `SHA256SUMS.txt` identify the exact local research package.

## Limits and assistance

ChatGPT assisted with manuscript drafting and code/test development; user-supplied critical reviews attributed to Claude informed editorial priorities but provided no independent clinical adjudication. Funding and financial interests beyond what appears in the artifact were not independently established. Clinical and organizational requirements, patient security, and regulations must be assessed by relevant professionals before any live use.

## Verified page-layout corrections
This edition keeps the original research code and numerical findings unchanged. It improves typeset listings, the Section 4.4/Table 3 flow, and Figure 3. The figure's PDF is a vector drawing and can be regenerated with `python figures/render_conservative_policy.py` (requires ReportLab and DejaVuSans installed locally). This diagram-generation dependency is separate from the pinned research test requirements.

`QUALITY_CHECKS.md` records source checks, tested extracted PDF strings, and rendered-page inspection. The final PDF is 32 pages. The bibliography begins immediately after the conclusion, and the closing research-integrity and funding statements fit on page 32. The two-column layout and substantive report content are preserved. This report is not a clinical validation.

## Final five-issue PDF check
See `QUALITY_CHECKS.md` and `qa_evidence/` for proof of the exact five requested text and layout cases. Code and numerical findings are unchanged from the prior 32-page release.

## Five-point preflight
`QUALITY_CHECKS.md` records source, MuPDF, Poppler and rendered-page checks for five repeatedly misreported artifacts.
