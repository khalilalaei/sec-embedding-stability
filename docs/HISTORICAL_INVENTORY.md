# Expanded historical filing inventory

This phase expands the time dimension for the same deliberately selected 12-company sample. It is not a historical S&P 500 universe and does not resolve selection/survivorship bias. Existing 2024–2026 prices, text results and financial evaluation windows remain development evidence. No new validation period is designated by this collection step; define and lock one before inspecting new return-label results. Reusing historical text with unknown-cutoff models remains retrospective.

## Scope and method

The frozen config selects original Form 10-K records by SEC filing-calendar date from **2015-01-01 through 2026-11-02**, inclusive. This is not a fiscal-year filter. Form 10-K/A is excluded; no amendment silently replaces the original. No current prices, security identifiers or industry classifications are imported.

For each configured CIK, the collector saves the exact current SEC submissions JSON, then follows relevant historical files listed in its filings.files array. It downloads pages whose advertised date intervals overlap the request. Pages with missing interval bounds are fetched rather than silently skipped. Out-of-range links and their bounds are logged. Current recent-only responses are insufficient for historical coverage.

Only metadata is downloaded at this stage. No filing HTML/text, model inference, text admission, automatic availability approval or new financial evaluation occurs. The current CIK and ticker labels come from the original selected sample. They are not historical security links or point-in-time industry labels. XOM's predecessor CIK is retained explicitly; its successor relationship still requires review and must not be treated as an identical legal registrant.

Every selected record preserves accession, filing date, report date where available, primary-document URL where available, filing-index/header links, and each source-page hash/path/row index. Duplicate CIK/accession records merge evidence; conflicting identity fields fail closed. Conflicting API timestamps are retained as a conflict, not chosen arbitrarily. Missing optional timestamps/documents are flagged rather than invented.

The field accepted_at_api is an unverified API value. It is deliberately not named accepted_at or eligible_from. All rows remain inventory_only_not_admitted, with historical security links pending. Source filing/header checks, public availability/dissemination evidence and an explicit execution lag must precede approved timing assumptions. Do not infer availability from fiscal year-end or silently convert an ambiguous clock.

The coverage CSV reports counts per requested company and filing-calendar year. Zero and multiple-original cells require review; neither alone proves a missing or erroneous fiscal filing. Partial first/final years and changes in filing patterns can explain them. The observed inventory count must not be replaced by an assumed twelve-filings-per-company target.

## Run locally

After pulling the repository, run each line separately from the project folder:

```powershell
git pull
```

```powershell
$env:SEC_USER_AGENT = "Khalil Alaei UCLA khalilalaei@g.ucla.edu"
```

```powershell
.\.venv\Scripts\python.exe -m secstab.history_inventory
```

Use your real contact information for the SEC request header. No new dependency or GPU is needed. Requests are sequential with the existing 0.25-second delay. A network/provider failure stops collection and preserves a failed partial receipt and downloaded bytes. It does not silently count the collection as complete. If SEC denies access, do not evade the restriction; retain the failure receipt for diagnosis.

The output data/history/inventory_v1 must not already exist. Earlier pilot data/corpuses and model locks are untouched. Keep failed collections and use an explicitly different --output for a later attempt; do not delete evidence to bypass the no-overwrite check.

Expected outputs:

- raw/CIK/...: exact SEC main and linked historical JSON bytes, with URL/hash/download-time receipts.
- filings_inventory.json: selected metadata records and row-level lineage.
- coverage.csv: filing-calendar-year counts and review flags.
- config_snapshot.json and universe_snapshot.json: exact collection choices.
- manifest.json: status, config/universe/code hashes, source hashes, skips, counts, missing-field flags and next review gate.

The data/history tree and historical-inventory ZIPs are gitignored. The User-Agent string is not saved in the receipt.

After collection, share the printed summary first. The next step is to audit the full inventory and source coverage, then download/extract versioned Item 1A text and check boundaries before computing any expanded embeddings. No expanded corpus, reserved-period evaluation, new financial finding or GPU run has been completed by this release.

## Validation and sources

89 offline tests pass. Twelve new synthetic cases cover column alignment, original/amendment filtering, safe and CIK-matched archive paths, overlap/unknown-range handling, optional missing fields, duplicate provenance, conflicting metadata, complete mocked collection, artifact hashes, partial network failure, no overwrite, required contact header and calendar-year coverage flags. Offline parsing of the 12 previously uploaded main/recent SEC metadata pages also succeeds (80 original 10-K metadata rows within the interval). This checks real main-page schema compatibility only, not historical archive completeness or live network access. The preflight receipt is results/history_inventory_preflight_2026-11-14/parser_check.json.

Official SEC references checked for this collector:

- Submissions API and linked historical file structure: https://www.sec.gov/search-filings/edgar-application-programming-interfaces
- Access rules, declared User-Agent, request rates, CIKs, archival paths and public dissemination limits: https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data
