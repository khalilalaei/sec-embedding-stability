# Review original Risk Factors sections

The downloader preserves original filings. Version 0.2 adds source-mapped extraction in `secstab.extraction`; see the README and 2026-11-03 extraction report for the current 12-company batch. Its review is explicitly AI-assisted, not an independent human audit. The manual alternative below remains available. Candidate machine extraction is never automatically marked as human-approved.

1. Run `secstab fetch` from the project root. Open the source_url in data/filings.json and the corresponding saved filing.html. Confirm issuer, CIK, accession, original 10-K form, reporting period, and dates.
2. Locate the ACTUAL Item 1A Risk Factors section. The table of contents is not the section. Read the preceding and following headings.
3. Extract the full section into a UTF-8 plain-text file under data/text/. A browser/text editor can be used for the pilot. Preserve numbers, headings, paragraph order and meaning. Avoid running an LLM rewrite, summary, or paraphrase.
4. Remove duplicated page headers/footers only under a documented rule. Do not remove seemingly boilerplate risk paragraphs just because they repeat. Record table transformations, broken characters, cross-references, and any content outside the primary document. If Item 1A refers elsewhere instead of including a complete section, flag it for a separate admissibility decision.
5. Compare the beginning, middle, and end with the raw saved source; scan every subsection heading. Verify there is no Item 1B/1C/2 content at the end, missing continuation, hidden XBRL data, or contents-page-only extraction. Record first/last source anchors and the extraction method/version.
6. Copy docs/REVIEW_TEMPLATE.md for the company and complete it. If the source lacks usable text or contains unclear boundaries, exclude/flag it. Do not assert passed review to bypass the gate.
7. Run `secstab admit` using the actual accession, text path, your name, and accurate review notes. The code records your assertion and hashes; it cannot independently prove the manual check occurred.
8. Keep the files and review records backed up. Admission is append-only; create a versioned corpus when correcting admitted text, so earlier runs remain interpretable.

Do not infer a historical tradable timestamp from the download date or fiscal-year end. This pilot stores SEC acceptance metadata but does not certify historical first-public availability. SEC User-Agent guidance: https://www.sec.gov/search-filings/edgar-application-programming-interfaces
