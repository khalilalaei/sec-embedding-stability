# Subsequent-window risk accuracy protocol — v1

This exploratory specification extends the mechanical snapshot to subsequent realized-risk losses. It is committed before computing these window-specific losses. It is not an untouched holdout or formal preregistration: the raw prices were uploaded and the November snapshot already summarized a period containing these dates. Models were encoded in November and training cutoffs are unknown. No historical implementability claim is permitted.

## Dates and timing

Use the same frozen 12-company Yahoo collection, corpus and seven primary representations, plus the separate CPU/GPU environment diagnostic. Use the XNYS close of the last session of July, August, September and October 2026 as candidate decision times. Roll weekend month-end backward to its last session. These are calendar rules, not dates chosen using losses. Require exactly 252 trailing return observations through the decision date and exactly 21 subsequent return observations. Log and exclude incomplete windows without shortening. Reject overlapping evaluation windows. The frozen collection ends November 2, so October's candidate will be logged as incomplete.

For this retrospective assumption-based diagnostic only, derive assumed eligibility as the close of the first XNYS session whose local date is strictly after the document's recorded SEC acceptance local date. Store every acceptance, assumed timestamp, source URL and review scope. Exclude any candidate before all 12 assumed timestamps. Original records remain unchanged; do not mark independently reviewed eligibility or permanent security links passed. This explicit assumption-based branch does not satisfy the stricter approved-execution gate for future historically implementable studies. The XOM economic successor assumption is retained from the market audit.

## Estimators and losses

Fit centered Ledoit-Wolf only to trailing returns. Preserve its marginal variances in every text blend: C_lambda=(1-lambda)B+lambda D K D. Keep equal weights 1/12. Primary text weight remains 0.25; supplementary grid remains 0, 0.10, 0.25, 0.50, 1. No fitting, model selection or outcome-driven changes to settings. Original document cosine matrices remain uncalibrated dependence targets, not estimated return correlations.

The realized proxy is the centered sample covariance of the next 21 daily proxy-return vectors with ddof=1. Its equal-weight quadratic form equals the sample variance of the fixed-weight daily return series. This is a noisy proxy for future daily covariance, not an oracle or guaranteed unbiased proxy for a time-varying conditional covariance. No annual-return or trading-profit target is tested.

Primary loss: squared difference between estimated and realized daily portfolio variance. Secondary losses: mean squared entry error over the whole covariance matrix and over off-diagonal entries. Aggregate each loss by an equal mean across the admitted dates; report improvement as 1-model_loss/baseline_loss, where positive means lower error and negative means higher error. Report each window, not just its mean. If baseline mean loss is zero, normalized improvement is undefined (null), not infinite. The all-entry loss includes diagonals shared by every augmented estimator, so also report off-diagonal loss.

At primary text weight only, include a supplementary score-level control for each encoder setting: c=mean off-diagonal K, K_level=(1-c)I+c11T. This retains the raw score level while removing company-specific structure and remains PSD for a valid Gram matrix. This control is motivated by the already-observed snapshot scale effect and is not an independent confirmatory test. Compare its losses with the corresponding structured kernel without choosing a winning model.

## Reporting and validity

Expect three complete nonoverlapping 21-session evaluation blocks. Trailing windows overlap, all arms share returns and documents, and these three blocks do not support reliable significance tests, confidence intervals, broad generalization or trading conclusions. Keep all arms, losses, failures/exclusions and frozen input/code/config hashes. No outlier deletion, missing-value imputation or additional provider download. No GPU or re-embedding is required. Publish aggregate outputs only; preserve provider observations locally.

An improvement would be a small exploratory observation under an uncalibrated mapping and timing assumptions. No improvement is a valid result. Future calibration, industry/factor controls, document permutations, expanded universes and genuinely prospective testing need separate protocols.
