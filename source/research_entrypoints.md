Run `python source/run_research_audits.py` for the R10 historical/candidate comparator tests.
Run `python source/audit_policy_generator.py` for the new conservative default generator composition.
Run `python source/audit_seeded_faults.py` for five intentionally seeded source errors.
Run `python -m coverage run --branch --source=claimslens_verifier -m pytest -q tests/test_conservative_policy.py` for the conservative default tests.
The only default import for newly authored research is `import claimslens_verifier`.
