# Resumable historical source and extraction batch

This is the first batch stage after the 143-record inventory/header audit. It downloads original primary filing documents, reuses matching source bytes already held by the pilot, and emits source-mapped Item 1A candidates plus an exception queue. It does not run embeddings, admit text or assign trading eligibility.

## Execute locally

Use the existing project Python environment with the extract extra and SEC_USER_AGENT set to the actual user/organization/contact. From the repository root:

```powershell
.\.venv\Scripts\python.exe -m secstab.history_corpus --limit 5
```

After inspecting the checkpoint, process the rest:

```powershell
.\.venv\Scripts\python.exe -m secstab.history_corpus --resume
```

Default inputs: data/history/inventory_v1, data/history/headers_v1 and optional data/corpus_extracted_v1.json source cache. Default output: data/history/corpus_v1. For a different cache location, use --cache-root; source paths are validated against that root. --cache-only performs no network requests and requires no request header. --limit counts newly processed records for the invocation.

The collector rechecks inventory and header hashes/record lineage, then confirms the primary filename in each header's 10-K document list before downloading. Each source is saved with a receipt before extraction. --resume verifies recorded source/text/map hashes, skips processed outcomes and continues missing work. Network/integrity failures preserve progress and stop; section-boundary failures are individually flagged and the batch continues. Existing completed text/maps are never silently overwritten. A code change to retry flagged extractions must use a documented new version/cached-source path, not erase flags.

Outcomes are keyed by CIK/accession so repeated company-years do not overwrite one another. Each successful extraction remains extracted_pending_review; ambiguous, short/incorporated or unsupported layouts remain extraction_flagged_pending_review. The existing conservative extractor was developed on the original 12-company pilot and must not be assumed universally reliable. Review new layouts, source maps and flags. Preserve all exclusions and stratified human QA evidence.

## Current validation

112 offline tests pass. Seven added tests cover synthetic source batching, genuine conservative extraction, cache-only behavior, changed cache/source/text detection, no overwrite, individual boundary flags, network resume, limited checkpoints and relative output paths.

A cache-only integration reused all 12 original pilot sources and reproduced every original extracted text hash exactly, with no network requests and no new admission. A separate live check downloaded one new BAC 2015 original primary document and extracted a 13,968-word candidate between Item 1A and Item 1B. This remains a candidate, not an independently reviewed section or an expanded financial result. Receipts are in results/batch_corpus_preflight_2026-11-14/.

Local agent execution context and deadline: docs/LOCAL_CODEX_HANDOFF.md and docs/THREE_WEEK_SPRINT.md.
