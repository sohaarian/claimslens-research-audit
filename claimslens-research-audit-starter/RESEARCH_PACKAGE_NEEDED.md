# Missing research artifacts

The starter archive contains the report and GitHub documentation, **not** the actual audit source or outputs. Do not represent it as reproducible yet.

Refer to Appendix A (pages 30–31) of `paper/ClaimsLens_Technical_Report.pdf` for the file inventory and the one-command audit procedure. Copy files from the original audited archive rather than recreating them from short excerpts in the PDF. Verify the manifest and hashes after copying.

The report identifies these exact SHA-256 digests for two code files:

- Conservative research default `source/claimslens_verifier.py`: `f9fe07e192a64fc08d1cc3ce5923385495a53cf6180c07494e5fa1e7b697fc34`
- Permissive comparator `source/claimslens_rule_candidate.py`: `cd14284919dba346e03b6657a96ff7ce571ddce1bc6c5483e50478f0caf3463b`

These values are reported by the paper; this starter archive does not contain these code files for fresh hash verification.
