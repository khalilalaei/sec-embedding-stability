# Company-specific similarity versus score level

This is a focused contrast of the already-run historical accuracy results. It uses the same fixed 25% text blend, the same three subsequent windows and the same 12 companies. No new fits, windows, embeddings or text weights were introduced. The score-level control was specified in the original accuracy protocol.

The full kernel and its matching score-level control share the same average off-diagonal cosine. Their difference captures the contribution of company-specific pair structure under this particular direct covariance mapping. It does not isolate or exhaust all possible uses of semantic information.

| Representation | Portfolio-error change vs level control | Covariance-error change vs level control |
|---|---:|---:|
| TF-IDF | +2.24% | -0.16% |
| E5 192 | +0.45% | +0.19% |
| E5 320 | +0.46% | +0.21% |
| BGE 192 | +1.33% | +0.53% |
| BGE 320 | +1.41% | +0.55% |
| Qwen 192 | +2.81% | +1.07% |
| Qwen 320 | +3.12% | +1.04% |

Positive changes mean the full kernel had higher error. These percentages compare aggregate mean squared losses, not volatility or investment returns.

For neural representations, adding the company-specific pair structure increased portfolio variance error by 0.45%–3.12% and covariance-entry error by 0.19%–1.07% relative to the matching level-only control. TF-IDF increased portfolio error by 2.24% while reducing covariance-entry error by 0.16%. The much larger deterioration versus the price-only baseline was already present in the level-only controls.

This supports investigating score calibration before treating raw cosine as a return-correlation target. It does not establish that text has no financial information. The experiment remains exploratory and retrospective: three evaluation blocks, selected companies, postdated embeddings, unknown training cutoffs and assumption-only eligibility. No significance test or model selection was performed.

Reproduce the frozen contrast with:

```powershell
.\.venv\Scripts\python.exe scripts\compare_score_level.py
```

Reference comparison and source/code hashes: results/score_level_comparison_2026-11-14/. The unchanged underlying experiment is documented in reports/risk_accuracy_2026-11-14.md.
