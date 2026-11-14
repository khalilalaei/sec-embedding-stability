# Uploaded historical-header audit

All 143 saved SEC header responses match their recorded SHA-256 hashes. Both generated output hashes match, the header collection links to the exact previously audited inventory, and all 143 parsed records reproduce from the raw source bytes with accession/form/CIK/filing-date/report-period checks intact. Every response contains two agreeing header representations.

As a diagnostic only, interpreting each raw header clock as America/New_York produces the same instant as its API acceptance value for all 143 records. This does not establish first public dissemination, ingestion, execution eligibility or absence of model look-ahead. No timestamps were promoted to approved availability.

The original parser failure and subsequent resume attempt remain in the receipt. The expanded corpus still has zero source bodies processed into admitted sections or embeddings. The original 12-section pilot is a separate completed dataset.

Evidence: results/history_headers_audit_2026-11-14/audit_receipt.json. Reproduce offline with:

```powershell
.\.venv\Scripts\python.exe scripts\audit_history_headers.py
```

This audit is an offline same-assistant consistency check, not an independent human source audit. The receipt stores exact source-manifest, inventory and code hashes. No raw SEC responses are committed by this report.
