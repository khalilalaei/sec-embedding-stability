# SEC header parser compatibility repair

The first live BAC 2015 source response exposed a parser error. Its HTML contains two SEC-HEADER copies: a hidden comment with tagged fields such as ACCESSION-NUMBER and TYPE, followed by an escaped visible header with labeled fields such as ACCESSION NUMBER and CONFORMED SUBMISSION TYPE. The original regular expression selected only the first block but expected labeled fields, so it stopped despite a valid response.

The repair parses both field conventions and every header copy. Each copy must match the expected accession, form, requested CIK, filing date and report period. All copies must also agree on the acceptance clock and filer CIK set. Missing, ambiguous or conflicting data still fail closed. The result records source_header_block_count, header_field_formats and header_copies_consistent. Raw responses remain unchanged and source clocks remain unzoned, with public-availability review pending.

## Verification

- Replayed the exact BAC source URL and reproduced its old-parser failure; the repaired parser matches both copies, the 2015-02-25 filing date and 2014-12-31 period.
- 105 offline tests pass. Five new regressions cover tagged fields, the hidden-tag/visible-label layout, conflicting clocks, conflicting CIKs and recovery from a parser failure using the already-recorded raw response.
- A deliberately limited live probe downloaded and replayed 47 headers across BAC, CAT, CVX and DE without parser errors. This is not a complete 143-header collection or approval of availability. Source hashes and checks are recorded in results/header_parser_repair_2026-11-14/verification.json. The partial raw probe and ledger were preserved.

Source response: https://www.sec.gov/Archives/edgar/data/70858/000007085815000008/0000070858-15-000008-index-headers.html

Source SHA-256: 6cffe4959c73ee14e0d65cd9de5e593c03d557b2ca11a152c8b1041bf4b15976

## Resume the user's saved collection

Run separately from the project root:

```powershell
git pull
```

```powershell
.\.venv\Scripts\python.exe -m secstab.history_headers --resume
```

The failed first response was saved and hashed before parsing. Resume verifies and reuses it, retaining the failure history and recording the repaired code version. Earlier inventory/corpus files and financial evidence are untouched. No new dependency or GPU is needed.
