# Research readiness and scale-up plan

Khalil Alaei | SEC filing embedding stability | Status: November 14, 2026

## Assessment

**Ready now for a faculty progress discussion; not yet a scaled empirical validation study.** The repository contains a reproducible 12-company pilot with meaningful descriptive and adverse/null financial findings. It does not yet support broad claims about S&P 500 forecasting or the general financial value of embeddings. No institutional UCLA readiness threshold or faculty approval is being claimed.

The next milestone is a stronger undergraduate empirical research package: a defined question, a justified sample, credible price/industry controls, dependence-aware uncertainty, an evaluation plan that acknowledges prior inspection, and a reproducible written result. Positive financial performance is not a requirement; a carefully supported negative result is a valid contribution.

## Evidence actually completed

| Component | Completed evidence | Limit |
|---|---|---|
| Filing text | 12 source-mapped Item 1A sections | AI-assisted checks; no independent human corpus audit |
| Representations | TF-IDF; pinned E5, BGE and Qwen at 192/320 total-token budgets | Three neural families, not independent retraining seeds |
| Stability | Family/chunk comparisons; peer sets, margins, k sensitivity; CPU/GPU environment diagnostic | 12 selected companies; 66 similarity pairs are dependent |
| Financial integration | Fixed-weight covariance and risk snapshot; raw, calibrated and score-level controls | Uncalibrated mappings and then exploratory method development |
| Risk-loss evaluation | 3 nonoverlapping 21-session blocks, 63 return dates, 12 companies | Previously inspected development data; three blocks do not establish statistical significance |
| Historical expansion | 143 original filing records; metadata and header identities audited | Expanded filing bodies, sections and embeddings have not run |
| Header evidence | 143 source hashes and 2 output hashes verified; all parsed records reproduce | Under an explicit ET interpretation, all 143 API/header clocks agree; public availability/execution remains unapproved |
| Software | 105 passing tests in the last tested release | Software checks are distinct from scientific validation |

## Findings worth showing now

1. **High similarity-rank agreement does not guarantee stable peers.** The three neural-family comparisons have Spearman correlations of about 0.968-0.984, but retain only 79.2%-87.5% of directed top-2 peer memberships in this sample.
2. **The raw text-to-risk mapping matters.** At a fixed 25% blend, the raw neural targets produce about 47-64 times the price-only portfolio variance squared error across the three inspected blocks. This concerns the chosen mapping and sample, not a general failure of embeddings.
3. **Stronger controls change the conclusion.** Past-only scale calibration lowers covariance-entry error about 2.09%-2.20% versus the original baseline. However, additional diagonal shrinkage with no text lowers that error about 2.27% and portfolio variance error about 40.29%; none of the calibrated text arms beats it on either aggregate metric.

Current conclusion: model/chunk choices affect peer and risk quantities, but incremental financial value from text has not been demonstrated. The evidence motivates testing whether any apparent gain survives calibration and strong text-free controls on a larger, separately evaluated panel.

## Proposed scale target, subject to faculty scope

These are planning targets, not universal statistical or university minimums.

- **First bridge milestone:** process the existing 143-filing inventory into a versioned historical text panel for the 12 firms. Record incorporated-by-reference sections, extraction failures and exclusions; do not force every filing into the corpus. Conduct independent human spot checks across issuer, year and layout, plus review every flagged extraction.
- **Main study target:** approximately 100-200 companies across industries and 8-10 years, roughly 800-2,000 annual sections before exclusions. Define inclusion and security-link rules before outcome inspection. Include inactive securities where the sampling design calls for them; a current-survivor cohort must be labeled as such.
- **Financial panel:** roughly 100 or more nonoverlapping 21-session evaluation blocks over that span, with trailing 252-session price estimation and the filing actually eligible at each decision. Count time dependence and repeated annual text explicitly; firm-month rows are not independent trials.
- **Original full-universe ambition:** a historical S&P 500-scale study is on the order of 5,000 constituent company-years over a decade. It needs historical membership/security data and may involve more than 500 distinct issuers. A current 500-name list is a different estimand.

## What must improve before a scaled empirical claim

1. **Corpus and timestamps:** source text plus section boundaries, exact original versions, report/filing/acceptance distinctions, public-availability evidence and an explicit execution lag. Header/API clock agreement alone is insufficient.
2. **Identity and outcomes:** historical security links, corporate-action/total-return conventions and documented missingness/delistings. The current YF aliases are useful for exploratory integration, not a substitute for permanent share identifiers.
3. **Controls:** price-only Ledoit-Wolf, diagonal and constant-correlation shrinkage, industry/factor controls, TF-IDF, and matched score-level or document-permutation controls. Fit any calibration using past returns only.
4. **Evaluation discipline:** current 2024-2026 observations and all three inspected blocks remain development data. Lock a separately uninspected evaluation panel before running it. Retrospective evaluation with modern models must retain its label; a prospective frozen arm or genuinely pre-period available checkpoint is needed for stronger timing claims.
5. **Look-ahead assessment:** investigate exact weight/checkpoint release history and training/fine-tuning evidence. Unknown cutoffs remain unknown. A before/after comparison or permutation diagnostic alone cannot prove absence of contamination.
6. **Inference and stability:** quantify both economic loss changes and their sensitivity to model/settings. Use date blocks and firm dependence as appropriate; do not use pair counts or settings as independent replications. Predeclare primary metrics and contrasts and retain all outcomes.
7. **Research delivery:** a faculty-reviewed report with data/sample flow, exclusions, methods, uncertainty, limitations and figures; a clean reproduction run from frozen inputs; and documented failed/null results.

## Conditional timeline

**Planning estimate: about 4-8 more weeks for a credible scoped undergraduate empirical package**, assuming approximately 10-15 focused hours per week, prompt faculty feedback, usable return/security data and adequate inference capacity. This is an estimate, not a delivery guarantee. The work budget is roughly 60-100 focused hours plus unattended computation and access/review delays; low availability or data problems can extend the calendar beyond eight weeks. GPU throughput has not been benchmarked at expanded scale, so no fixed inference runtime is promised.

| Stage | Approximate working calendar | Reviewable exit artifact |
|---|---|---|
| Show the pilot | Now | This brief, existing reports, figures and negative findings |
| Source and extraction bridge | Week 1, potentially into week 2 | 143-filing source/extraction ledger, exclusions, human spot-check record |
| Scope, access and compute benchmark | Weeks 1-2, in parallel | Frozen cohort rules; source/return plan; measured throughput on a representative document subset |
| Expanded corpus and embeddings | Weeks 2-4 | Audited 100-200-company panel, or a narrower agreed scope; frozen model/settings manifests |
| Locked comparisons and inference | Weeks 4-6 | Price/industry/text controls, dependence-aware evaluation and uncertainty, all prespecified contrasts |
| Independent review and write-up | Weeks 6-8 | Reproduction check, report/poster or working-paper draft, limitations and next evaluation plan |

A 12-company longitudinal update is a smaller bridge milestone and could be available in about 1-2 weeks. A full historical S&P 500 study should be budgeted separately; a rough 8-12+ week scope is plausible but cannot be reliable until data entitlements, corpus exception rates and GPU throughput are measured. There is no defensible publication-acceptance ETA.

## Resources and critical path

- Resolve WRDS entitlements and historical identifiers/return conventions while corpus processing continues. If access stays limited, choose and label a smaller conditional-cohort research question rather than imply market-wide coverage.
- Seek faculty-sponsored Hoffman2 access and benchmark the existing pinned models before requesting larger models. UCLA documentation requires faculty/researcher sponsorship and notes that pending sponsorship requests must be checked in SIM. Resource/queue availability is not assumed.
- Keep three model families and the fixed primary chunk contrasts initially; prioritize sample validity, controls and evaluation over adding configurations.
- Review the scope and scientific question with the professor now. Useful agreement items: primary estimand, cohort definition, evaluation reservation, industry/factor control, and whether the intended deliverable is a research note, poster or working-paper draft.

Official access/data references:

- https://www.hoffman2.idre.ucla.edu/Accounts/Requesting-an-account.html
- https://sim.idre.ucla.edu
- https://indexes.morningstar.com/research-data-products/crsp-us-stock-databases

Project evidence: reports/pilot_stability_2026-11-03.md; reports/risk_accuracy_2026-11-14.md; reports/risk_calibration_2026-11-14.md; results/history_headers_audit_2026-11-14/audit_receipt.json. These are pilot findings and a proposed plan, not a faculty-approved research certification or a preregistration of the expanded study.
