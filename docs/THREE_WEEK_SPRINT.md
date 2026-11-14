# Three-week research sprint

Revised November 14, 2026 after the user set a three-week deadline. Target date: **December 5, 2026**. This replaces the earlier broad 4-8 week scheduling assumption for the immediate deliverable; it does not retrospectively turn planning targets into completed evidence.

## Deliverable and scope

Aim for a defensible, reproducible undergraduate empirical research draft with a precise question, an expanded panel, strong controls, uncertainty, a separately locked evaluation and an honest limitations section. Publication acceptance and positive financial results are not guaranteed.

Primary question: how do model/chunk choices change SEC-text peer groups and the financial conclusions of a fixed covariance/risk task, after controlling for price information, industry and similarity-score level?

Keep the existing three pinned neural families, 192/320 chunk contrasts and TF-IDF. Prioritize executing the pipeline and expanding valid observations over adding more models or tasks. Expected hardware is a desktop i9/RTX 3070; confirm its actual VRAM and benchmark before estimating inference wall time.

**Operational target:** 50-100 companies over roughly 8 years, about 400-800 annual sections before exclusions. A 100-company panel is the preferred target; 50 is a scope fallback if a measured data/compute constraint demands it, not a universal research threshold. A larger 100-200 company / ten-year study remains an extension. Do not claim S&P 500 coverage without historical membership evidence. If WRDS remains unavailable, a precisely defined surviving-company cohort can support a narrower conditional retrospective question; label that limitation.

## Calendar and measurable gates

| Days | Work | Exit evidence |
|---|---|---|
| 1-3 | Run the 143-filing source/extraction batch; review flags; benchmark representative documents; write and commit expanded protocol | Source hashes, candidate/exclusion counts, stratified human QA list, measured GPU chunks/sec and VRAM; exact cohort/split/metrics frozen before new loss evaluation |
| 4-9 | Expand to the prespecified 50-100 company cohort; obtain return/identity/industry data; cache common chunks; execute embedding batches | Complete sample-flow ledger, missingness/identifier policy, time-eligible document panel, versioned checkpointed model outputs |
| 10-15 | Evaluate fixed peer/risk contrasts and controls; dependence-aware uncertainty; investigate data exceptions without selecting favorable outcomes | All prespecified results and failures, covariance/portfolio loss panels, industry and text-free controls, date/firm dependence treatment |
| 16-21 | Run the locked evaluation once; reproduce; faculty/independent review; write research draft and figures | Reproduction receipt, report/poster or working-paper draft, limitations and negative findings, appendix and source/experiment references |

Daily progress is measured by source and section counts, reviewed exceptions, successful model jobs, evaluated decision dates and finished figures--not number of chat messages or tests alone. If a gate slips, reduce breadth/secondary tasks transparently and keep scientific validity. Do not rush a full-universe claim.

## Scientific deadline constraints

The current three financial windows and all inspected 2024-2026 data are development evidence. No improvement found by further adapting to those windows is fresh validation. Before running expanded outcomes, define a separately uninspected evaluation panel and lock its methodology. Historic experiments with postdated or unknown-cutoff models remain retrospective. A newly frozen 21-session prospective test cannot be assumed complete inside three calendar weeks; it may be registered as a continuation, not fabricated into the deadline report.

Current results already show important adverse/null evidence: high rank agreement can coexist with peer changes; raw cosine risk targets fail against price-only in three blocks; calibrated covariance gains do not survive the stronger diagonal control. The expanded study can establish how robust that conclusion is; a positive text signal is not required.

## Execution changes now

1. A local Codex session owns terminal execution on the computer containing the data/GPU. This chat can continue research review through the repository; it does not automatically gain the local terminal or inherit local sessions.
2. Source/extraction is one resumable batch: python -m secstab.history_corpus. It reuses verified pilot source bytes, downloads remaining primary documents, writes candidates/maps, and queues extraction flags without stopping the whole batch for a boundary failure. Network/integrity failures stop safely; --resume preserves progress. Candidates are not automatically admitted.
3. Cache shared chunks once per corpus/tokenizer revision/budget before large inference. Existing cli.embed recomputes chunk boundaries per run; that is an explicit scaling task, not already optimized behavior.
4. Batch GPU inputs efficiently, preserve document aggregation/order, checkpoint each document/job, and benchmark on the actual device. Do not infer runtime from peak GPU specifications.
5. Implement the expanded time-varying financial panel: correct security order and latest permitted filing at each decision, with past-only TF-IDF/calibration. Current 12-company financial scripts use a static pilot corpus and must not be reused blindly as a longitudinal backtest.
6. Reserve time for stratified independent human boundary review and all flagged/excluded cases. Machine success is not human audit.

## Resource dependencies

GPU throughput helps inference; historical return/security/industry data, QA and scientific design remain critical. Work on source processing and software while access requests are pending. Do not purchase cloud compute or change external accounts without a specific user instruction. Package jobs so they can move to faculty-sponsored computing if benchmarked local capacity is inadequate.
