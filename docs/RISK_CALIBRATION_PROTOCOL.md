# Training-only shrinkage calibration — exploratory v1

This extension is designed after inspecting the raw-blend and score-level-control results. It is committed before computing calibrated window losses, but reuses the same three already-observed evaluation blocks. It is exploratory method development, not a fresh holdout, formal preregistration or confirmatory validation. Unknown model-training cutoffs and November embeddings continue to prevent historical implementability claims.

## Fixed method

Use the exact original corpus, matrices, Yahoo panel, assumed eligibility, 252/21-session windows, exclusion rule, loss definitions, equal portfolio weights and primary blend weight lambda=0.25. No new downloads or embedding inference. For each decision, fit the centered Ledoit-Wolf price covariance B to trailing returns only, and convert it to correlation R_B with D=diag(sqrt(diag(B))).

For each raw cosine Gram matrix K, fit one coefficient by least squares on the upper-triangle off-diagonal entries of R_B:

alpha=clip(sum(K_ij*R_B_ij)/sum(K_ij^2),0,1). A zero denominator gives alpha=0. Define K_cal=(1-alpha)I+alpha K and C_cal=(1-lambda)B+lambda D K_cal D.

This is restricted shrinkage calibration, not general correlation calibration. It can attenuate raw off-diagonal scores but cannot amplify them beyond their raw values or change their relative pattern. Alpha is fitted independently at each decision; no future covariance or portfolio-error label enters its fitting API. The fit targets trailing price correlation, not subsequent portfolio loss. The 66 pair entries are not independent samples; no coefficient standard errors are reported.

K_cal is a convex combination of PSD unit-diagonal matrices, so the covariance stays PSD and baseline marginal variances stay fixed. For identical K and alpha it decomposes into price covariance plus a diagonal shrinkage term plus a scaled raw-text target: any gain may arise from extra shrinkage, not semantic structure.

## Required controls

1. The original price-only Ledoit-Wolf baseline.
2. A fixed 25% diagonal-target blend, C_diag=0.75B+0.25diag(B). This is alpha=0, with no text.
3. A fixed 25% constant-correlation target estimated entirely from trailing price correlation: rho=mean off-diagonal R_B; K_const=(1-rho)I+rho11T. Clip rho to its PSD interval [-1/(n-1),1] for numerical bounds.
4. For each model, the old score-level kernel using its mean raw off-diagonal cosine, with its own alpha fitted by the same past-only rule. This retains only score level and receives the same calibration procedure.
5. The original raw-cosine blend at 0.25 for each representation, retained as an unchanged adverse-result reference.

Seven primary representations plus the separate E5 GPU environment diagnostic yield 27 arms per window, 81 window rows, 27 aggregate rows and 48 coefficient records (full and level-only, eight settings, three decisions). The environment diagnostic is excluded from primary representation counts. No estimator or parameter is chosen using the observed losses.

## Evaluation and provenance

Reuse centered next-21-session sample covariance (ddof=1), squared error of equal-weight daily portfolio variance, whole-matrix and off-diagonal covariance-entry MSE. Compare aggregate mean losses with price-only, diagonal, price-constant-correlation, raw and paired calibrated level-only controls; show all results and per-window values. Undefined relative changes for zero reference loss are null. Retain every coefficient, trailing fitting interval, target-fit MSE, input/config/code hash, exclusion and assumption record.

The chosen same-corpus/same-date pairwise target is a statistical construction, not a claim that document cosine equals return correlation. Coefficient fitting shares information with the price baseline. No optimizer, trading-return forecast, transaction-cost conclusion, model selection, significance test or independence claim is introduced. A favorable observation on these already-seen blocks requires independently reserved or prospective data before a validation claim.
