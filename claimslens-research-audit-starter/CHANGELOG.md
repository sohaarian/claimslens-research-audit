# Research software change record

## Targeted editorial and reproducibility corrections, 17 October 2026

- Kept the conservative verifier, permissive candidate and historical verifier algorithms unchanged.
- Corrected the verifier-hash provenance, default-versus-candidate language, generator-profile interpretation, safety control and R1--R4/R7 test links.
- Clarified the 51 collected pytest cases across 12 functions; reported statement and branch coverage separately and named all unexecuted paths.
- Relabeled the default facade outcome table, placed the requirement table immediately under Appendix B.1, and removed duplicate prototype discussion.
- Renamed `source/audit_revision11.py` to `source/audit_policy_generator.py` and `results/revision11_policy_and_generator.json` to `results/policy_generator_results.json`; updated commands and CI. The outputs are from the unchanged algorithms.
- Verified the FDA guidance document explicitly identifies January 29, 2026, as its date and supersedes the January 6 edition. No citation date change needed.
- Re-ran the prescribed coverage command from a fresh copy; 51 cases passed, statement coverage 40/43, branch coverage 4/6, combined 90%.

## Research policy release, 17 October 2026

- Retained original broad-veto historical verifier as `claimslens_verifier_historical.py`.
- Renamed the identity-aware but permissive comparison rule to `claimslens_rule_candidate.py`; comparison data are unchanged.
- Added `claimslens_verifier.py` as **conservative, review-first research default** with explicit date, three statuses, separate support and inspection source IDs, attached-notice review and basic malformed structured-record handling.
- Added 51 pytest cases with branch coverage, five transparent seeded source-fault probes, and a structural generator audit reporting 240/384 profile/scenario cells and modulo confounds.
- Documented that the 283/917 generator split was unchanged, whereas the research-default states are 283 Document Found, 782 Review Missing and 135 Review Conflict.
- Made method sections explicitly distinguish software predicate compatibility from validated patient care. Expanded future independent clinical labeling and report extraction methods.
- Added Singh et al. (2009) imaging follow-up citation, verified FDA issue/reissue dates through FDA town hall, and completed Gebru et al. DOI.
- Public demo code/deployment was **not** modified or verified.

## Historic comparison artifacts

The case-generation, identity-aware candidate correction and all-algorithm predicate grid are preserved to explain the cancellation-defect discovery. The permissive candidate is not designated the safe default.

## Seven targeted editorial clarifications (17 October 2026)
No verifier, generator, evaluation script, or test code changed. The report now clarifies profile/modulo coupling; earlier cancellation policy; grid direction; AST vs Coverage.py measurement; archived Qwen baseline; public demo versus research archive; and ISO-8601 UTC time-of-day event logs.

## Three final targeted typesetting edits (18 October 2026)
- Removed the duplicate generator interaction sentence, retaining the labeled Interaction limit paragraph.
- Corrected column-break placement in the profile confounding section without changing its conclusion.
- Standardized the predicate-grid equation in explicit display math mode; the numeric result remains unchanged.
- No verifier, model, test, audit or research result code changed.

## Report 4 targeted code and typesetting corrections (October 2026)
- Kept historical `for r in linked` and explicit `review = True` assignments in readable code listings; prevented the examples from splitting awkwardly across columns.
- Preserved the correct 2^10 × 6 × 3 = 18,432 math expression and added a sentence boundary to the coverage explanation.
- Removed awkward hyphenation in the line-and-branch coverage phrase and standardized Table 2 scenario Count, Table 5 transitions, and Table 6 row wrapping.
- Enlarged the Figure 3 diamond label and regenerated the diagram from its correct source text.
- Python, audit scripts, test fixtures, and quantitative findings are unchanged.

## Report 5 final rendering checks (October 2026)
- Preserved historical veto Boolean and complete code listing while making its `for r in linked` tokens visually distinct.
- Set candidate `review = True` and `veto = True` as separate statement lines, avoiding false extraction of inline assignments.
- Split developer-defined header at the intended phrase boundary; vertically centered Table 6 values in their cells.
- Kept the 18,432 finite-grid formula in LaTeX math mode with the correct comma grouping.
- Replaced ambiguous single-word `No` edge label in Figure 3 with `No notice`, retaining the separate `No evidence` edge.
- Reduced the source SHA-256 cross-reference to its standard eight-character prefix; full hash remains in Appendix A.1 and SHA256SUMS.
- No Python, test, result, or research conclusion modifications.

- Improved the grid equation's neighboring prose so PDF text extraction cannot disguise the 1,024 input patterns.
- Prevented the historical veto listing from breaking across columns after changing fixed-width code formatting.

## Strict presentation corrections (October 2026)
- Verified and enlarged spacing in the intact historical predicate (`for r in linked`; closing parenthesis; `complete = bool(...)`).
- Verified both `review = True` assignments and `veto = True` in candidate listing; preserved source-code meaning.
- Added PDF accessible text semantics to the mathematically typeset 2^10 × 6 × 3 = 18,432 identity.
- Protected the compound Table 2 header and DOCUMENTED status word from misleading auto-hyphenation.
- Kept the Section 4.4 heading with its opening text and changed Table 6's narrow right header to Count.
- No Python verifier, dataset, generated result, finding, or experimental claim changed.

- Final pre-release visual check caught and corrected a full-listing wrap and a Section 4.4 one-line continuation.
- Restored complete single-line historical assignment by retaining compact fixed-column code layout.
- Confirmed proper LaTeX superscript and math punctuation with a redundant plain-language arithmetic equivalent.

## Render-verified layout correction
- Rechecked historical and candidate listings in source; valid Python syntax already present.
- Preserved fully typeset 2^10 x 6 x 3 formula and explicitly labeled scenario table.
- Anchored Table 3 in the source narrative instead of allowing a leading-column float.
- Replaced the tiny, wide Figure 3 with a readable vector decision diagram; added its regeneration script.
- Kept Section 9 header with introductory paragraph to avoid a heading orphan.
- Did not alter any verifier code, test outcomes, or research findings.

## Final Report 8 targeted layout correction
- Verified historical/pseudocode syntax, mathematical equation and Table 2 label are already correct in the LaTeX and visually rendered PDF (reported broken forms were flattened text-extraction artifacts).
- Set Table 3 as a `[!t]` float anchored in its own generator subsection; retained all substantive text.
- Replaced the forced page break before references with a keep-together requirement; reduced appendix B.2 onward paragraph leading slightly, keeping the final disclosures on the same final page.
- Result: 32 pages, no near-empty terminal page, no bibliography gap, no changed Python/test/result files.

## Report 9 narrow five-issue check
- Verified historical `for r in linked`, candidate `review = True` and `veto = True`, and Table 2 `Developer-defined` are already correct in the editable LaTeX and rendered PDF. No edits to these already-correct strings.
- Retained the correct LaTeX mathematical formula. A supplementary accessibility experiment was rejected because it made PDF text extraction worse; the delivered PDF has the original, accurate visual math.
- Protected final `ClaimsLens` product name from accidental line splitting; spelling was already correct.
- Maintained 32-page count and unchanged scientific narrative, code, and experimental results.

## PDF extraction and equation accessibility (targeted, 17 October 2026)
- Added `accsupp` alternate text for the displayed grid formula so text extraction preserves the exponent, multiplication operators, and thousands separator. No other paper wording or research code was modified.

## Final extractor compatibility
- Removed a marked-content wrapper that some PDF extractors dropped, kept the correct displayed mathematical formula, and placed a plain-text `2^10 x 6 x 3 = 18,432` rendering in its adjoining explanatory parenthesis to survive copy-and-paste. No research data or code changed.
