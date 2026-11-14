# Historical SEC filing-header collection

The 143-record inventory has passed the [offline audit](../reports/history_inventory_audit_2026-11-14.md). This stage downloads the small SEC filing-header/index response for each inventoried accession. It does not download the full filing bodies or run extraction, embeddings or financial evaluation.

## Run

From the project folder in the same PowerShell window used for the inventory:

```powershell
git pull
```

```powershell
.\.venv\Scripts\python.exe -m secstab.history_headers
```

The existing SEC_USER_AGENT contact header is required. If this is a newly opened window, set it first:

```powershell
$env:SEC_USER_AGENT = "Khalil Alaei UCLA khalilalaei@g.ucla.edu"
```

Default source inventory: data/history/inventory_v1. Default output: data/history/headers_v1. The collector first re-audits the source inventory and checks config/universe choices, then makes sequential requests using the existing SEC delay. It prints progress and a final summary. No new dependency or GPU is needed.

After completion, share the printed summary. Preserve the source folder; the next review will use these exact bytes.

## What the collector verifies

Each response must contain a SEC-HEADER block. The parsed accession, conformed submission form, requested filer CIK, filing date and report period must agree with the inventory. A block page or conflicting identity stops the run, preserving downloaded evidence and the failure receipt. Source URL, raw-byte SHA-256 and retrieval timestamp are recorded for every response.

The acceptance_clock_unzoned field is the raw fourteen-digit source clock. It is not automatically treated as UTC or converted into eligible_from. Both API and source-header clock values are preserved for explicit timezone/dissemination review. Matching identity fields is not approval of public availability, trading eligibility, historical share-class continuity or text boundaries.

Outputs:

- headers/CIK/accession.html: original header/index response bytes.
- headers_inventory.json: matched identity fields, raw source clock and pending timing-review status.
- inventory_audit.json: source inventory audit performed before requests.
- manifest.json: input/source/output hashes, code versions, progress, failures and resume history.

## Resume a partial network failure

Keep the folder and run:

```powershell
.\.venv\Scripts\python.exe -m secstab.history_headers --resume
```

Resume requires the same audited inventory. It verifies recorded file hashes before reuse and does not redownload successful headers. A completed valid collection is left unchanged. Changed bytes, different inputs or unreceipted completed files stop the run for inspection. Failure history is retained. Do not delete data or evade a provider restriction to force progress.

The header collector has synthetic network/failure tests; its bulk live SEC integration is the user's next check. It preserves all earlier corpuses, model locks and financial outputs. Header completion does not admit any expanded Risk Factors text or approve any evaluation period.

## Dual-format parser repair

The first live BAC 2015 header exposed a format assumption: the HTML response contains a hidden SGML-style header in a comment and a visible, escaped labeled header. The original parser chose the first SEC-HEADER block but expected only labeled fields. The repaired parser supports tagged and labeled fields, parses every header copy, and requires matching identities, dates, clocks and filer CIK sets. Conflicting or incomplete copies fail rather than being silently discarded. Raw bytes and timing-review statuses are preserved.

After pulling the repair, resume the existing failed collection:

```powershell
.\.venv\Scripts\python.exe -m secstab.history_headers --resume
```

This reuses the already-recorded first response and retains the original failure history. Do not delete headers_v1 or change the inventory to get past the parser. The regression suite covers tag-only fields, the actual hidden-tag/visible-label layout, conflicting clocks, conflicting CIKs and parser-failure recovery without redownloading successful source bytes.

## Uploaded full collection audit

All 143 uploaded header source hashes, two output hashes and parsed records now reproduce. All responses contain two agreeing header copies. API values agree with source clocks when the latter are interpreted as Eastern time; that is an explicit diagnostic interpretation, not approved public availability. See reports/history_headers_audit_2026-11-14.md and scripts/audit_history_headers.py. Expanded section extraction/embedding is still pending.
