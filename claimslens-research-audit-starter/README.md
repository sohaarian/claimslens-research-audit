# ClaimsLens Research Audit

**Status: source audit package pending — not yet reproducible from this repository.**

This repository is intended to accompany *ClaimsLens: Testing Medical-Document Evidence Rules and a Conservative Review Policy* (17 October 2026), an independent software-verification case study using fictional records.

The research contrasts (1) a historical cancellation veto, (2) an identity-aware but permissive candidate, and (3) a conservative, human-review-oriented research policy. It studies software predicates and generated records; it does **not** establish clinical accuracy, medical effectiveness, nursing productivity gains, or deployment of the research policy to a hosted demo.

## Paper

- [`paper/ClaimsLens_Technical_Report.pdf`](paper/ClaimsLens_Technical_Report.pdf) — the uploaded 32-page case study.

## What must be added before publishing this as a reproducible audit

The attached PDF documents, but does not supply, the executable audit files. Add the exact original files (not reconstructed approximations) to these locations:

```text
source/claimslens_verifier.py
source/claimslens_rule_candidate.py
source/claimslens_verifier_historical.py
source/run_research_audits.py
source/audit_factorial_grid.py
source/audit_conservative_policy.py
source/audit_policy_generator.py
source/audit_seeded_faults.py
source/experimental_triage.py
source/check_field_mutations.py
source/check_all_obligations.py
source/check_cancellation_behavior.py
source/check_renderer_sources.py
source/benchmark_extraction_scaffold.py
tests/test_conservative_policy.py
requirements-research.txt
results/audit_summary.json
results/factorial_grid.json
results/experimental_triage.json
results/policy_generator_results.json
results/seeded_fault_detection.json
results/policy_branch_coverage.json
SHA256SUMS.txt
```

These paths reproduce the research report's **Technical Appendix A** inventory. Supplementary application modules needed by the original audits may also be required and must be carried over from the actual archived audit package.

## Commands described by the report

Run these only **after** populating and verifying the research package, installing dependencies in a fresh environment, and checking that referenced files are present.

```bash
python -m pip install -r requirements-research.txt
python source/run_research_audits.py
python source/audit_policy_generator.py
python source/audit_seeded_faults.py
python -m pytest -q tests/
python -m coverage run --branch --source=claimslens_verifier -m pytest -q tests/
python -m coverage report -m
sha256sum source/claimslens_verifier.py
```

The reported results are historical findings from an archived controlled run; none of the commands above has been run on the starter repository.

## Evidence and risk boundaries

- The study used 240 fictional cases, 1,200 tracked items, and a constructed 18,432-cell cancellation predicate grid.
- The developer-authored policy suite reported 51 passing parameterized cases across 12 test functions, 90% combined line/branch coverage of the small conservative policy module, and detection of five deliberately seeded faults.
- These are software-testing results, not independently adjudicated clinical outcomes.
- The archived research verifier is **not** assumed to be installed in the hosted public app.

Related demonstration source: [claimslens-public-demo](https://github.com/sohaarian/claimslens-public-demo). Keep the public demonstration and controlled research package distinct.

## Before changing visibility to public

Verify exact file contents and SHA-256 checksums; ensure all required scripts run in a clean environment; add accurate dependencies, a dataset/source-provenance statement, and a license decision. Do not commit secrets, private claims files, credentials, or employer records. Do not claim external reproduction until an independent party actually reproduces the run.
