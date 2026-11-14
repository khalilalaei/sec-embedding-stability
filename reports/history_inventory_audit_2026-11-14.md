# Historical inventory audit

The uploaded inventory passes offline hash, linked-page coverage, record-replay and row-lineage checks. It contains **143 unique original 10-K records for 12 requested CIKs**, selected by filing date from 2015-01-01 through 2026-11-02. This is metadata coverage, not an admitted text corpus, approved historical security mapping or financial result.

## Verified evidence

- All 99 SEC source JSON hashes and four generated-output hashes match the uploaded manifest.
- The source set includes 12 main pages and all 87 linked historical pages whose advertised ranges overlap the request. The 24 out-of-range archive skips reproduce from the saved parent pages.
- Replaying the saved pages reproduces the full inventory exactly, including metadata paths, hashes and row indexes. Direct accession/form/filing-date checks against the referenced rows also pass.
- 80 records come from recent main-page data and 63 from historical pages. All 143 CIK/accession pairs are unique.
- The filing-calendar coverage CSV, company counts and missing/conflict counters reproduce. There are no missing primary filenames or API acceptance values and no conflicting API timestamps.
- The config/universe JSON choices match the repository references. Snapshot hashes are checked against their own output receipts. Original input hashes are preserved separately: a reserialized JSON snapshot need not have identical bytes to the input file. The actual Windows collector code hashes match the reference source with CRLF line endings; those bytes differ from Linux LF bytes without changing the source text.

These are same-assistant consistency checks on the supplied archive, not independent authentication of every SEC document or an independent human audit. The original inventory statuses remain unchanged.

## Deere's single zero cell

The only empty company/filing-calendar-year cell is **DE, 2026**. The eleven observed Deere records are one each from 2015 through 2025, all filed in December. The most recent is accession 0001104659-25-122321, filed December 18, 2025 for the period ended November 2, 2025. Its official source header independently displays the same filing date, period, accession and Deere CIK:

https://www.sec.gov/Archives/edgar/data/315189/000110465925122321/0001104659-25-122321-index-headers.html

Because the inventory stops on November 2, 2026, the zero is consistent with the observed annual filing pattern and cutoff. No relevant linked metadata page was omitted, and there is no evidence here that the collector missed a 2026 filing. This is not a guarantee that all fiscal obligations were met or a claim about when a future filing will occur. Do not add a synthetic 144th record or use fiscal year-end as its availability date. The original zero-cell review flag is preserved, with this explanation recorded separately.

## Next source check

Before extracting 143 sections, collect and check each filing's SEC header. The new header collector preserves exact response bytes, verifies accession/form/requested CIK/filing date/report period, and saves the raw acceptance clock alongside the unverified API value. It does not silently assign a timezone, public availability timestamp or trading eligibility. See [header collection instructions](../docs/HISTORICAL_HEADERS.md).

The header collector's network behavior has been exercised with synthetic fixtures; bulk live header collection has not run in this environment. One official Deere header was inspected separately through web retrieval as source context. This does not replace the user's forthcoming saved bulk source bytes.

## Reproduction and evidence

```powershell
.\.venv\Scripts\python.exe -m secstab.history_audit
```

Default input: data/history/inventory_v1. Default audit output: runs/history_inventory_audit_v1.json, which must not already exist. This command is offline. The audit receipt, unchanged coverage table and Deere cutoff review are in results/history_inventory_audit_2026-11-14/. Full metadata remains in the preserved uploaded archive/local collection.

100 offline tests pass. Added tests cover changed source bytes, rehashed forged records/coverage, missing archive receipts, reference JSON formatting/line endings, raw and escaped header clocks, identity/date/period mismatches, non-header block pages, complete cached collection, source tampering and partial-download resume. All original financial findings remain unchanged.
