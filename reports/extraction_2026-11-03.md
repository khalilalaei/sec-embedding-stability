# Risk Factors extraction report — 2026-11-03

Status: **12/12 extracted; AI-assisted source/boundary checks passed for descriptive pilot use.** No model embeddings or financial experiments have run.

| Company | Words | Reporting period end | Item 1B boundary |
|---|---:|---|---|
| MSFT | 11,678 | 2026-06-30 | Checked |
| ORCL | 15,039 | 2026-05-31 | Checked |
| JPM | 15,467 | 2025-12-31 | Checked |
| BAC | 16,573 | 2025-12-31 | Checked |
| XOM | 5,079 | 2025-12-31 | Checked |
| CVX | 4,937 | 2025-12-31 | Checked |
| JNJ | 6,260 | 2025-12-28 | Checked |
| MRK | 11,300 | 2025-12-31 | Checked |
| CAT | 7,844 | 2025-12-31 | Checked |
| DE | 8,748 | 2025-11-02 | Checked |
| WMT | 13,545 | 2026-01-31 | Checked |
| TGT | 7,912 | 2026-01-31 | Checked |

Total: 124,382 whitespace-delimited words. Word counts are not model-token counts.

## Evidence

All 24 original filing/SEC submission-metadata hashes match the user's uploaded source manifest. Issuer CIK, accession, form and dates match saved SEC submissions. Each long Item 1A span ends immediately before the actual Item 1B heading; short table-of-contents candidates were excluded. Deere splits its item and title over separate lines and is handled explicitly.

Repeated page numbers, running headers, report footers and navigation labels were removed using logged rules. Standalone numeric removals were checked and form sequential page-number series for this batch; the numeric-line rule must be reviewed again on other filings. Substantive paragraphs, summaries, bullets and risk categories were preserved. There is no semantic rewriting or broad repeated-paragraph removal. Hidden inline XBRL, head/style/script content and explicit hidden DOM elements are excluded.

A separately implemented standard-library HTML parser matches the lxml extraction's complete non-whitespace character sequence for all 12 sections after the same boundary/cleanup rules. This is a cross-parser consistency check, not an independent policy or human audit. The assistant inspected the section openings, endings, next headings and all removal lists; it did not perform a sentence-by-sentence semantic or browser-rendered layout audit.

Each source map records selected/rejected boundaries, removed lines and reasons, retained output ranges, and original DOM XPath/source-line locations. Visible-text offsets are Unicode character offsets, NOT raw HTML byte offsets. Original source/text/map hashes tie outputs to inputs. The original HTML and submission metadata remain unchanged.

## Safe installation

The accompanying installer verifies the package and all 24 original local source-file hashes before writing. It refuses to replace any differing destination. It installs separate `data/text/extracted_v1/` and `data/corpus_extracted_v1.json`, preserving `data/corpus.json` and any manually copied Microsoft/Oracle files. Repeat installs with identical bytes are harmless.

## Limits

The corpus's `ai_assisted_passed` status is distinct from human review and is accepted only with `descriptive_pilot_only` scope and an intact source map. Source-map integrity is checked whenever this corpus is loaded. Formal financial work still requires the agreed temporal/market-data protocol and whatever human/independent source review the team requires. Reporting periods differ across issuers and current-company selection is not historical point-in-time index membership.

The raw HTML, extracted text and complete maps are delivered separately, not committed to GitHub. The GitHub report contains only a summary and provenance. Future extraction versions must retain new hashes and separate run IDs.

## Software and installation checks

21 offline tests passed, including parser boundaries, hidden content, source mapping, ambiguous-section rejection, review-scope gating and source-map tampering. On a test copy of the real 12-filing batch, installation and corpus loading passed; manually saved text and the original corpus were preserved; a second install made zero writes; a modified original source and a conflicting destination were rejected. Integration was exercised on the local Linux/Python runtime; Windows execution is the user's next step.
