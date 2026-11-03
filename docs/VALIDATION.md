# Starter validation — 2026-11-02

13 offline unittest checks passed; Python compilation and CLI help passed. Tests cover exact source-span coverage including Unicode and long units; self-exclusion and ties; rotation invariance; peer changes; invalid/failed vectors; lexical pipeline/comparison; immutable run paths; source and output tampering; and pending-review rejection.

Synthetic fixtures exist only in temporary test directories. No real SEC filing acquisition, embedding-model download/inference, GPU execution, or financial experiment was run. Network/API behavior and model compatibility remain to be verified in the first live pilot. The tested host environment is recorded in starter-validation-environment.json; it is not an embedding environment lock.

## Update — 2026-11-03

21 tests now pass after adding source-mapped extraction, hidden-text and boundary cases, and AI-review scope/source-map integrity tests. Actual batch integration and second-parser checks are documented in reports/extraction_2026-11-03.md. This supersedes the earlier statement that no real SEC data had been processed; pretrained model inference and financial experiments remain unrun.

## Pilot evidence update — 2026-11-03

Actual user-run neural inference and six completed comparisons are now audited in reports/pilot_stability_2026-11-03.md. The audit checks 39 output hashes, 49 distinct source/text/extraction-evidence artifacts, all 72 company comparison rows, model-register consistency, final vector normalization and Gram matrices, exact chunk source spans/coverage, and a TF-IDF reconstruction from source. Inference and tokenizer counts were not independently rerun. The separate audit script adds four regression tests for unsafe archives, Windows path handling and corrupted summary/order evidence. This supersedes prior current-status statements that neural inference had not run; financial experiments remain unrun.

Pilot release verification: 25 offline tests passed on 2026-11-03, including all four new evidence-audit checks. The audited full user archive reproduced all six comparison summaries, all 72 company rows and the TF-IDF matrix from source text. The generated SVG was rendered and visually checked. No additional neural inference or financial experiment was run during this audit.
