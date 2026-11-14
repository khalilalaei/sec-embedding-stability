# Starter validation — 2026-11-02

13 offline unittest checks passed; Python compilation and CLI help passed. Tests cover exact source-span coverage including Unicode and long units; self-exclusion and ties; rotation invariance; peer changes; invalid/failed vectors; lexical pipeline/comparison; immutable run paths; source and output tampering; and pending-review rejection.

Synthetic fixtures exist only in temporary test directories. No real SEC filing acquisition, embedding-model download/inference, GPU execution, or financial experiment was run. Network/API behavior and model compatibility remain to be verified in the first live pilot. The tested host environment is recorded in starter-validation-environment.json; it is not an embedding environment lock.

## Update — 2026-11-03

21 tests now pass after adding source-mapped extraction, hidden-text and boundary cases, and AI-review scope/source-map integrity tests. Actual batch integration and second-parser checks are documented in reports/extraction_2026-11-03.md. This supersedes the earlier statement that no real SEC data had been processed; pretrained model inference and financial experiments remain unrun.

## Pilot evidence update — 2026-11-03

Actual user-run neural inference and six completed comparisons are now audited in reports/pilot_stability_2026-11-03.md. The audit checks 39 output hashes, 49 distinct source/text/extraction-evidence artifacts, all 72 company comparison rows, model-register consistency, final vector normalization and Gram matrices, exact chunk source spans/coverage, and a TF-IDF reconstruction from source. Inference and tokenizer counts were not independently rerun. The separate audit script adds four regression tests for unsafe archives, Windows path handling and corrupted summary/order evidence. This supersedes prior current-status statements that neural inference had not run; financial experiments remain unrun.

Pilot release verification: 25 offline tests passed on 2026-11-03, including all four new evidence-audit checks. The audited full user archive reproduced all six comparison summaries, all 72 company rows and the TF-IDF matrix from source text. The generated SVG was rendered and visually checked. No additional neural inference or financial experiment was run during this audit.

## Complete initial chunk grid — 2026-11-03

The complete eight-run/eight-comparison upload preserves all 53 files in the initial upload byte-for-byte. Audit checks now cover 53 run-output hashes, 49 original/text/extraction source artifacts, all 96 company-level comparison rows, shared source chunks at both budgets and within-model inference settings/third-party runtime consistency. BGE's project-distribution metadata changes 0.1.0 to 0.2.0; inference CLI and numerical-core Git blob hashes match across the two recorded commits. This metadata exception is logged rather than silently treated as a fully identical environment.

A new regression check accepts the intended budget change, rejects changes in device/precision/Python and logs project-distribution metadata changes. Neural inference and tokenizer counts were not rerun during the audit.

Complete-grid release: 26 offline tests passed. The upgraded auditor also reproduces the original six-run/six-comparison archive. The latest SVG was rendered and inspected, and report links/counts were checked. Exact audit receipts and source-code identity checks are in results/pilot_2026-11-03_complete/audit_receipt.json.

## Financial preparation — 2026-11-03

35 offline tests pass, including nine new financial-foundation tests. Tests use synthetic observations only and check duplicate/missing/sentinel returns, explicit security ordering and calendar coverage, disjoint past/future windows, no influence of future returns on the fitted baseline, timezone-aware filing eligibility, PSD rejection, marginal-variance preservation under text blending, hand-calculated portfolio variance and covariance error. Real WRDS/CRSP data, financial evaluation and portfolio optimization remain unrun. Input templates are empty schemas. See FINANCIAL_PILOT_PROTOCOL.md.

## Exploratory peer-count supplement — 2026-11-03

38 tests pass, including three exact combinatorial-reference checks. The frozen complete-pilot matrices reproduce all user-reported E5–Qwen summaries at k=1,2,3,5. A documented post hoc extension covers all three model-family and three chunk contrasts at those k values (24 summary rows, 288 company rows). Source evidence was checked against its existing hash receipt. No new embeddings, market data, significance test or financial outcome is involved; k=2 remains primary. See reports/peer_count_2026-11-03.md.

## Alternative price-data preparation — 2026-11-13

45 offline tests pass, including seven synthetic Yahoo-proxy tests for split-adjusted returns, avoiding dividend double-counting, required adjusted-close fields, missing/nonpositive prices, exact calendar coverage, currency/symbol validation and ordered multi-security assembly. No live Yahoo request was made in the test runtime, and no real alternative-provider financial outcome was evaluated. Partial failure and no-overwrite behavior are implemented; live network/provider schema behavior is the user's next integration check. See docs/YAHOO_PILOT.md.

## Yahoo lazy-metadata repair — 2026-11-13

50 tests pass. The observed live AttributeError arose when the collector serialized yfinance's lazy Mapping as a string. The repair handles mappings recursively while skipping lazy intraday tradingPeriods, rejects malformed metadata explicitly, uses the current exception-policy configuration with restoration, and preserves an older-version fallback. Five new regression tests include an end-to-end mocked 12-security collection and no-overwrite check. Symbol/currency/type/timezone validation is retained. The live retry remains to be verified on the user's computer, using a new versioned collection directory.

## Uploaded Yahoo collection audit — 2026-11-14

53 offline tests pass. Three additional synthetic audit cases cover a valid 12-security panel, changed source bytes, rehashed incorrect returns and a rehashed omitted calendar date. The actual frozen upload also passed its artifact hashes, corpus lineage, exact session coverage, OHLC/action sanity checks and adjusted-price return reconstruction. See reports/market_audit_2026-11-14.md for the receipt, issuer-successor exception and limitations. This milestone does not run covariance/portfolio outcome evaluation or approve forecast eligibility.

## Mechanical risk snapshot — 2026-11-14

58 offline tests pass. Five new synthetic risk checks cover zero-weight equivalence to the price baseline, fixed marginal variances, immunity to changes strictly after the snapshot, joint security/kernel permutation invariance, an independently derived all-ones versus identity target contrast, and invalid inputs. The frozen real-data integration produced 40 setting/grid rows, eight contrasts, baseline/primary covariance matrices and receipts, without reading future outcome labels or re-embedding text. Every primary covariance passed PSD checks. Estimated-risk sensitivity is reported separately from untested future accuracy.

## Subsequent-window risk accuracy — 2026-11-14

68 offline tests pass. Ten additional synthetic cases cover timezone-aware assumption-only filing lag, weekend/month-end handling, incomplete horizon exclusion, late-source exclusion, disjoint windows, realized covariance/scalar variance agreement, zero-weight baseline equivalence, no target-window contamination of the corresponding fitted baseline, score-level control mean/PSD/permutation invariance, independently checked loss formulas, aggregation across all dates and overlapping-window rejection. The real integration produced 147 window-loss rows, 49 aggregate rows, three complete 21-session blocks and one logged incomplete candidate. After a receipt-only enhancement, all analysis outputs reproduced byte-for-byte; code hashes match the final receipt. No model/weight was selected by these losses. See reports/risk_accuracy_2026-11-14.md for the adverse/null findings and limitations.

## Past-only calibration — 2026-11-14

77 offline tests pass. Nine new synthetic cases cover known-scale recovery, bounds and zero denominators, marginal/PSD preservation, unit/permutation invariance, least-squares objective bounds, calibrated-level/price-control equivalence, independent covariance decomposition, target-window immunity of coefficients and estimates, unchanged legacy raw losses and invalid inputs. The real integration produced 81 window rows, 27 aggregate rows, 48 fit records and 40 matched-control comparisons. Original raw/reference losses match the prior study within floating-point tolerance; all level controls equal the price-constant target here and all alpha estimates lie inside their constraints. After enhancing summary counters, unchanged numerical outputs reproduced byte-for-byte. All computation hashes match the receipt.

## Historical metadata inventory — 2026-11-14

89 offline tests pass. Twelve new synthetic pagination/provenance cases cover original-only filtering, missing optional fields, aligned columns, archive bounds and CIK/path restrictions, deduplication, contradictory metadata/timestamps, complete mocked collection with hashes and no-overwrite preservation, partial network failure, contact-header requirement and filing-calendar coverage flags. The parser also accepts all 12 previously uploaded main/recent SEC pages, yielding 80 metadata rows in the requested date interval. This is main-page schema compatibility evidence, not a live historical API run or expanded-corpus/financial result. See docs/HISTORICAL_INVENTORY.md and the preflight receipt.

## Uploaded historical inventory and header collector — 2026-11-14

100 offline tests pass. Eleven new audit/header cases cover exact source/output hash checks and source-row replay; rehashed forged metadata/coverage; missing linked-page receipts; semantic JSON reference checks across formatting and LF/CRLF differences; raw and escaped clocks without invented eligibility; header identity/date/period mismatches; non-header responses; complete cached/no-overwrite behavior; recorded-source tampering; and partial-network-failure resume. The actual upload reproduces 143 unique records from 12 main and 87 historical pages, with 24 out-of-range skips checked and four output receipts verified. Deere 2026 is the only zero cell and is separately documented as cutoff-consistent, without changing the original flag. Bulk live header collection has not run here; synthetic fixtures and one separately viewed official Deere source header are distinguished from that future integration check.

## Dual-format SEC-header repair — 2026-11-14

105 offline tests pass. Five new regressions cover tagged SGML fields, hidden-comment plus visible labeled copies, cross-copy clock conflicts, tagged identity mismatches and parser-failure resume using unchanged cached bytes. The exact first BAC response was replayed, and a deliberately limited live probe verified 47 source headers across BAC/CAT/CVX/DE. Multiple header copies must agree; identity/date/period checks remain mandatory. This is live parser compatibility evidence, not bulk collection completion or timing approval. See reports/header_parser_repair_2026-11-14.md and its source-hash verification receipt.

## Full uploaded header audit and faculty brief — 2026-11-14

The full uploaded collection passes 143 raw-source hashes, two output hashes, exact inventory linkage and replay of all 143 parsed records. All duplicate header blocks agree; API/source clocks agree under an explicit America/New_York interpretation. The original failure/resume history is preserved. Availability approval remains pending. No new expanded text or financial outcome was generated by this audit. The faculty brief distinguishes pilot evidence from proposed scope and estimates; its PDF is rendered and visually reviewed before delivery. The numerical test suite remains 105 tests.
