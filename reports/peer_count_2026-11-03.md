# Exploratory peer-count sensitivity — 2026-11-03

**Finding:** E5–Qwen agreement is not monotonic in the number of peers. The original k=2 specification remains primary; these checks were added after inspecting the initial pilot results.

This supplement recomputes k=1,2,3,5 from the frozen matrices for all three original model-family contrasts and all three model-specific chunk contrasts. It adds no embeddings, market observations or financial evaluation. All four E5–Qwen values match the summaries supplied by the user. The other contrasts are supplemental matrix recomputations performed by the assistant.

## E5 versus Qwen at 192 tokens

| Peers k | Retained / total | Overlap | Uniform-independent reference | Normalized excess overlap |
|---|---:|---:|---:|---:|
| 1 | 11/12 | 91.67% | 9.09% | 0.908333 |
| 2 | 19/24 | 79.17% | 18.18% | 0.745370 |
| 3 | 26/36 | 72.22% | 27.27% | 0.618056 |
| 5 | 52/60 | 86.67% | 45.45% | 0.755556 |

With 12 companies, each focal company has 11 possible peers. Under two independent uniformly chosen k-element peer sets, expected intersection size is k²/11 and expected overlap fraction is k/11. Thus the combinatorial reference rises from 9.09% for k=1 to 45.45% for k=5. This is a reference calculation, not a significance test or a realistic model of industry structure.

Normalized excess overlap is (observed − k/11)/(1 − k/11). It is provided to make the mechanical baseline visible; it is not predictive accuracy. Raw overlap alone cannot establish that choosing five peers is more robust than choosing two. Larger sets can also admit peers that were ranked just outside a smaller set, so agreement need not increase or decrease monotonically.

The rank correlation remains 0.9682705354347146 and mean absolute similarity difference remains 0.12232404830167228 for every E5–Qwen row, because the underlying matrices do not change with k.

## Raw overlap across all six supplemental contrasts

| Contrast | k=1 | k=2 (primary) | k=3 | k=5 |
|---|---:|---:|---:|---:|
| e5_vs_bge_192 | 83.33% | 87.50% | 86.11% | 86.67% |
| e5_vs_qwen_192_gpu | 91.67% | 79.17% | 72.22% | 86.67% |
| bge_vs_qwen_192 | 83.33% | 79.17% | 83.33% | 88.33% |
| e5_192_vs_320 | 91.67% | 87.50% | 94.44% | 96.67% |
| bge_192_vs_320 | 91.67% | 91.67% | 91.67% | 96.67% |
| qwen_192_vs_320_gpu | 100.00% | 95.83% | 91.67% | 91.67% |

## Evidence and scope

- [All 24 summary rows and 288 company-level rows](../results/peer_count_2026-11-03/verified_sensitivity.json)
- [Summary CSV](../results/peer_count_2026-11-03/summary.csv)
- [Frozen source matrices and original pilot](../results/pilot_2026-11-03_complete/verified_evidence.json)
- [Reproduction script](../scripts/peer_count_sensitivity.py)

Run `python scripts/peer_count_sensitivity.py --output results/peer_count_new_check` from the project root. The source evidence hash is recorded in the result. The source JSON was checked against its existing audit receipt. Exact uniform-reference logic was checked by exhaustive enumeration on a small synthetic universe.

These are exploratory descriptive results for 12 deliberately selected firms. Pair observations and configurations are dependent. Keep k=2 as the primary specification rather than selecting k to maximize agreement. No uncertainty estimate, financial benefit or absence of look-ahead bias follows from these counts.
