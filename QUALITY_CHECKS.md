# Final five-point PDF preflight

This release removes a marked-content accessibility wrapper that caused some extractors to suppress the equation. The source retains `2^{10} \times 6 \times 3 = 18{,}432` in LaTeX mathematical display mode. For PDF readers that flatten superscripts, the immediately following explanation includes the unambiguous copyable text form `2^10 x 6 x 3 = 18,432`. The other four requested strings were already correct in the LaTeX and visible PDF.

Checks passed:
- historical loop source exact: **PASS**
- historical loop Poppler: **PASS**
- historical loop MuPDF: **PASS**
- candidate assignments source: **PASS**
- candidate assignments Poppler: **PASS**
- candidate assignments MuPDF: **PASS**
- equation math mode source: **PASS**
- equation Poppler ASCII exponent and comma: **PASS**
- equation MuPDF math not 210: **PASS**
- Table 2 header Poppler: **PASS**
- Table 2 header MuPDF: **PASS**
- final name Poppler: **PASS**
- final name MuPDF: **PASS**
- 32 pages: **PASS**

At 72 dpi, altered render pages: [10]. All executable files, experiment outputs, source tests and diagrams match the baseline by SHA-256. The report remains 32 pages.
