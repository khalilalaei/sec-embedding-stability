# Financial pilot protocol draft — 2026-11-03

Status (2026-11-14): numerical foundations, an audited Yahoo proxy import and a retrospective mechanical covariance/risk sensitivity snapshot are implemented and run. Historical outcome evaluation, permanent security linking and portfolio optimization **not run**. WRDS account requested; source-specific CRSP query/export instructions will be finalized after the user's actual entitlements and dataset format are known. This draft is a research design, not a validated forecasting method.

## Alternative-data amendment — 2026-11-13

With WRDS still pending, the user requested a way to continue. A separately versioned Yahoo adjusted-price proxy path is now available: [collection instructions and limitations](YAHOO_PILOT.md). This changes the initial data-source option, not the financial estimand, frozen text contrasts or proposed primary text weight. It uses vendor-scoped YF:TICKER aliases, not permanent IDs, and requires identity/availability review. Yahoo-based financial results must remain labeled exploratory and retrospective. No alternative data or outcomes were inspected before this amendment; the collector was tested with synthetic fixtures only.

## First question

For the same 12 companies, return window and portfolio weights, does changing the text representation materially change estimated covariance and portfolio variance? Subsequently: does adding text reduce variance-estimation error against a price-only baseline? Keep sensitivity separate from incremental predictive value.

## Proposed primary design (freeze before inspecting return outcomes)

- Representations: TF-IDF and six model/budget settings already generated. The E5 GPU-192 arm is an environment diagnostic, not a seventh independent text model.
- Price baseline: centered Ledoit–Wolf shrinkage covariance, fitted only to trailing daily total returns. This is an established implemented comparator, not a claim that it is best for this sample. Official method/API: https://scikit-learn.org/stable/modules/generated/sklearn.covariance.LedoitWolf.html and https://scikit-learn.org/stable/modules/covariance.html
- Trailing window: candidate 252 observed trading days; evaluation: next 21 observed trading days. Use an explicit reviewed exchange calendar; missing dates/returns must not silently disappear through an inner join.
- Text kernel: the saved normalized-document cosine matrix K, required symmetric positive semidefinite with diagonal one.
- Dependence-only augmentation: let B be the price baseline and D=diag(sqrt(diag(B))). Define T=D K D, then C_lambda=(1-lambda)B+lambda T. This intentionally preserves every baseline marginal variance so the first contrast isolates dependence structure rather than conflating text choice with a change in individual-stock volatility. This refines the earlier trailing-volatility proposal; neither has been evaluated on real returns.
- Candidate primary text weight: lambda=0.25, chosen now before return outcomes. Supplementary fixed grid: 0, 0.10, 0.25, 0.50, 1.00. These are design choices, not optimized or proven values. If later tuning is introduced, use separate chronological training/validation and an untouched test period.
- Primary portfolio: equal weights in the same 12 admitted securities. Holding weights fixed lets us measure how estimated risk changes. Optimized allocations, turnover and costs are a later extension; no optimizer is implemented in this preparation milestone.
- Primary descriptive outcome: spread of estimated daily portfolio variance across representation settings at fixed lambda. Also report covariance entry changes and closest-peer changes.
- Subsequent outcome evaluation: covariance mean squared entry error against a clearly specified next-window realized covariance proxy, and squared error of portfolio variance forecasts. Short-horizon realized covariance is noisy; report that limitation. Annualization, if displayed, must use one explicitly specified trading-day convention consistently.
- A stability result can exist with no predictive benefit. Do not select a configuration or lambda by its eventual test-period performance.

## Chronology and validity

The current embeddings were generated in November 2026 from filings with different reporting periods. Training/fine-tuning cutoffs remain unknown. Historical performance using these modern models is a **retrospective diagnostic** unless model timing can be established; it is not a proven historically implementable forecast. Prospective testing can be frozen separately, but requires future observations and a fixed protocol.

Before evaluating any formation date, assign each exact document an independently reviewed `eligible_from` timestamp in a named exchange timezone/UTC, accounting for original public availability and an explicit ingestion/execution lag. A candidate decision rule is the close of the next trading day after verified availability; it is not automatically established by an SEC date. No document with eligible_from after the formation timestamp may enter. Do not replace old filings with later amendments or use fiscal year-end as the availability date.

The return baseline may use prices before the filing date; text eligibility applies at decision time. The evaluation return window begins strictly after the decision close. This removes one obvious timing error but does not resolve pretrained-model contamination. Monthly windows and overlapping horizons require a dependent-data inference plan; do not treat daily rows, 66 firm pairs or multiple configurations as independent trials.

The current chosen-company universe is not historical point-in-time S&P 500 membership. No financial conclusion from 12 companies/one filing each should be generalized to that larger target without expansion and an appropriate sample design.

## Input contract

Canonical formats are templates in `templates/financial/`. They are empty schemas, not downloaded or synthetic research observations.

1. `returns.csv`: `date,security_id,total_return`. Date is the exchange trading-day label YYYY-MM-DD; security_id is a permanent share/security identifier stored as text; return is a decimal total return (0.01 means 1%). Preserve source-specific original fields separately. Missing/source sentinel values are rejected; no zero imputation. The module cannot determine from a numeric column alone whether dividends/delistings were included correctly.
2. `security_links.csv`: `document_id,cik,security_id,link_start,link_end,review_status,notes`. Review company/share-class identity and effective dates. Tickers are labels, not the permanent join key. Historical changes may require multiple reviewed links; the first static panel should exclude/flag unsupported transitions explicitly. The numerical foundations do not yet parse/approve these links.
3. `filing_availability.csv`: `document_id,eligible_from,review_status,evidence_note`. eligible_from is an explicit timezone-aware decision-eligibility timestamp for exact document bytes; this is separately reviewed, not generated as a fact by the extractor.
4. `trading_calendar.csv`: `date`. Supply the reviewed evaluation exchange calendar. `align_returns` requires its expected dates and securities explicitly; it rejects missing panel cells, including a day absent for all securities.
5. `data_receipt.json`: source/database/release, extraction time, entitlement/use constraints, raw file hashes, return construction, dividend/delisting treatment, identifier-link source, calendar, timing rule and exclusions. Never put passwords, API keys or WRDS credentials in the repository.

Do not infer CRSP field meanings or combine delisting fields until the actual selected CRSP dataset's documentation is checked. Different exports/releases may have different return conventions; blindly adding a delisting adjustment could double-count it.

## Implemented now

`src/secstab/financial.py` provides return-format validation, explicit-calendar/security ordering, disjoint past/future windows, reviewed timezone-aware document-eligibility checks, centered price covariance, PSD kernel validation, dependence-only blending, fixed-weight portfolio variance and covariance MSE. These are numerical building blocks. The separate mechanical snapshot runner now integrates them with the audited proxy panel; future-outcome evaluation is not implemented by this module.

Run software tests without WRDS or a GPU:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_financial.py -v
```

After real data is mapped into the canonical schema, check its format:

```powershell
.\.venv\Scripts\python.exe -m secstab.financial --check-returns data/market/returns.csv
```

A passing format check does not approve the return definition, security links, trading calendar, document/model timing or financial claims. The original foundations milestone reported no financial results; the subsequent mechanical snapshot reports only estimated-risk sensitivity, as described below.

## Mechanical snapshot scope amendment — 2026-11-14

The first integration experiment is a retrospective descriptive snapshot at the frozen price-collection endpoint, 2026-11-02, rather than a historical trade or forecast formation date. It uses the prior specified 252-return window, equal weights, raw cosine dependence target and primary text weight 0.25; the complete config is configs/risk_snapshot_v1.json. The saved embeddings were generated after the price snapshot, which is stated explicitly in the receipt/report. The runner checks that source acceptance predates the snapshot close but does not mark trading eligibility or security links independently approved. No subsequent return/covariance labels are used. This narrower scope does not waive the chronology, linking or calibration requirements above for future outcome evaluation. See reports/risk_snapshot_2026-11-14.md.
