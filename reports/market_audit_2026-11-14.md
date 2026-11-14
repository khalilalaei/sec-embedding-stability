# Yahoo market-data audit — 2026-11-14

The frozen `yahoo_pilot_v2` upload passed numerical and lineage checks. This is the first real market-data ingestion milestone, not a financial forecast or evidence of incremental embedding value. The original dataset is unchanged and stays outside GitHub.

## Verified checks

- All 29 manifest-listed artifacts matched SHA-256 hashes. The separate input corpus hash matches the embedding evidence exactly, and the corpus snapshot matches its contents and document order.
- 12 securities, 712 price sessions each, and 711 daily return dates: 2024-01-03 through 2026-11-02. There are 8,532 security-date returns and no missing panel cells.
- Recomputed XNYS sessions using exchange-calendars 4.13.2 match all supplied daily histories and the saved return calendar. This is a separate execution of the same calendar source, not an independently maintained calendar.
- Every adjusted-close ratio reproduced every saved return exactly using round-trip CSV parsing; maximum absolute error was zero. No dividend was added twice.
- OHLC ordering, positive finite prices, and nonnegative finite volume/action fields passed. Saved metadata matched each requested symbol, USD equity type and New York timezone.

## Identity and action review

The 11 other provider issuer names are consistent with the supplied SEC issuer labels and ticker lists at a descriptive level. This is AI-assisted review of supplied records, not a historical security-master audit or proof of share-class continuity. Vendor aliases remain `YF:TICKER`; original pending review fields are preserved.

XOM requires an explicit successor relationship: the SEC corpus uses Exxon Mobil Corporation (CIK 34088), while current provider metadata names ExxonMobil Holdings Corporation. The issuer’s July 2026 Form 8-K documents a July 1 redomiciliation and one-for-one exchange into Holdings shares, with the XOM ticker retained for trading from July 2. This supports a documented economic-continuity assumption for this vendor-series pilot; it does not make the two legal registrants identical. Source: https://investor.exxonmobil.com/sec-filings/all-sec-filings/content/0001193125-26-291986/d70995d8k.htm

Walmart has a provider-recorded 3-for-1 split on 2024-02-26. Adjusted prices are used as supplied; no second split adjustment is applied. All 12 tables contain dividend events. These action records are screened for numerical validity, not independently reconstructed against issuer payment records.

| Company | Dividend events | Minimum daily proxy return | Maximum daily proxy return |
|---|---:|---:|---:|
| MSFT | 11 | -9.99% | 15.51% |
| ORCL | 12 | -13.79% | 35.95% |
| JPM | 12 | -7.48% | 11.54% |
| BAC | 11 | -11.06% | 8.43% |
| XOM | 11 | -7.20% | 4.99% |
| CVX | 11 | -8.22% | 6.65% |
| JNJ | 11 | -7.59% | 6.19% |
| MRK | 11 | -9.81% | 12.60% |
| CAT | 12 | -9.25% | 11.63% |
| DE | 11 | -6.76% | 11.58% |
| WMT | 11 | -9.15% | 9.55% |
| TGT | 11 | -21.41% | 12.02% |

Extrema are screening diagnostics, not identified data errors. Large moves (including Oracle and Target) are retained and require event/source review before an outcome-evaluation study. No winsorization, outlier deletion or zero filling was performed.

## Scope and next experiment

The return column is a Yahoo adjusted-price proxy, not independently reconstructed CRSP total returns. Parsed provider tables are retained, not raw HTTP responses. Current quote metadata is used only for identity checks. Revised adjusted histories and this selected-company universe are not point-in-time data.

No covariance/portfolio outcome evaluation has run in this audit. The next descriptive task is the fixed-weight covariance/risk sensitivity design in `docs/FINANCIAL_PILOT_PROTOCOL.md` (252 trailing observations, fixed lambda 0.25, equal weights). Any historical outcome evaluation still requires explicit filing-eligibility timestamps, logged issuer/successor assumptions and the unresolved model-training-cutoff limitation. Do not silently promote the pending collection to independently reviewed or historically implementable status.

## Reproduce locally

After pulling the repository, run:

```powershell
.\.venv\Scripts\python.exe scripts\audit_market_pilot.py --market data\market\yahoo_pilot_v2 --corpus data\corpus_extracted_v1.json --output market_audit_local.json
```

The output file must not already exist. This performs no downloads and leaves source files unchanged. `results/market_audit_2026-11-14/audit_receipt.json` records the audited input hashes and aggregate checks. The audit is self-consistency verification of the frozen upload; it does not independently authenticate Yahoo observations.
