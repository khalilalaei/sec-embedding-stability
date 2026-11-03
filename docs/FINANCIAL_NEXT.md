# Financial phase — roadmap

The first stability pilot is complete. Numerical financial foundations and schemas are now implemented; see [financial pilot protocol draft](FINANCIAL_PILOT_PROTOCOL.md). Real market data, historical links, financial evaluation and portfolio optimization remain unrun. The remaining sections are broader design proposals; the first draft preserves baseline marginal variances when adding text.

## 1. Data and timing gate

Obtain WRDS/CRSP access through the appropriate UCLA process and permitted use. Build historical company/security links using permanent identifiers and effective dates; tickers alone are insufficient. Define original filing versions, amendment handling, first-public evidence, exchange timezone, ingestion delay and execution rule. A conservative candidate is next trading-day close after verified public availability, with returns starting after that close; specify exchange calendar and this rule before measuring results. Use only the most recently eligible filing at each decision date.

Use historical index membership, delisted securities, dividend-aware total returns, documented delisting treatment, sector/industry information available at the time and point-in-time financial controls where used. Assess model pretraining/fine-tuning/distillation timing separately. Historical tests with later-trained/unknown-cutoff models are retrospective analyses, not proven historical forecasts. Freeze a prospective evaluation now as a cleaner complementary track.

## 2. Peer validation

Freeze text top-k peers at monthly formation. Compare future return correlation and company-minus-peer portfolio residual variance against industry peers, trailing-correlation peers, TF-IDF peers, and matched random peers. Use same eligible securities and k. Include within-sector comparisons. Evaluate multiple months/years and report missingness. Future returns are evaluation labels, never peer-selection inputs.

## 3. Primary financial task: covariance/risk

Use identical trailing windows and a shrinkage covariance baseline. For normalized embeddings Z, K=ZZ^T is positive semidefinite. Let D contain trailing daily volatility estimates; Sigma_text=D K D. Blend Sigma_lambda=(1-lambda) Sigma_baseline+lambda Sigma_text, lambda in [0,1]. This is a proposed estimator, not a demonstrated improvement. Select lambda with rolling training/validation only. Zero/negative fitted gains are valid findings. Check symmetry, PSD, ordering, missingness, and units. A constrained portfolio optimizer may still need numerical regularization.

Compare baseline, industry/factor augmentation, TF-IDF augmentation, and embedding augmentation under the same tuning budget. Monthly formation with a candidate 252-trading-day trailing estimation window and next-21-trading-day evaluation is a starting protocol choice, not an approved optimum. Short-horizon realized covariance is a noisy proxy: report that limitation.

Outcomes: out-of-sample covariance loss with specified normalization; portfolio variance forecast error; realized volatility under identical long-only fully invested constraints and a predeclared weight cap; turnover and concentration. Include costs where economic implementation is evaluated. Report kernel blend weights and failure rates.

## 4. Secondary tasks: volatility, then returns

Volatility target: next-21-day realized daily-return variance or its annualized square root; explicitly define which and its units. Compare lagged volatility/control baseline to the same model plus text-peer summaries or past-only text features. Use log-volatility error/QLIKE as appropriate to the chosen positive variance target.

Return target: next-21-day compounded total return less the specified benchmark. Compare a simple price/financial-control model with the same model plus text, using ridge as an initial implementation. Fit scaling, PCA, vocabulary/IDF and hyperparameters within each training fold. Evaluate out-of-sample R-squared relative to a declared baseline, date-level cross-sectional rank IC and costs-aware portfolio returns. No deep architecture needed initially.

## 5. Evaluation and stability of financial conclusions

Use rolling chronological train/validation/test splits; purge overlapping label windows at boundaries and define the test only once. Never random-split firm-date rows for the main forecasting claim. Cluster/resample by companies and time blocks as appropriate; pair observations and overlapping horizons are dependent. Account for multiple specifications and do not select the final model on the untouched test.

For each configuration, Delta=baseline loss - augmented loss. Report average Delta, uncertainty, fraction of configurations with positive Delta, worst/best cases, signal/weight changes and cross-regime behavior. Compare the size of financial improvement with variation attributable to configuration choice. Pre/post training-cutoff comparisons and structured permutation tests are diagnostics, not proofs of leakage or its absence.

## 6. Publication evidence

Before making any financial claim, link every table row to source versions, point-in-time records, security mapping, model revision, commit, config, fitted period, test period, prediction file, metric implementation, costs and exclusions. Preserve null results and failures. New code and numerical tests for financial tasks must be implemented and verified before this design becomes an empirical result.
