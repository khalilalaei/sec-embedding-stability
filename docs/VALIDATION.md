# Starter validation — 2026-11-02

13 offline unittest checks passed; Python compilation and CLI help passed. Tests cover exact source-span coverage including Unicode and long units; self-exclusion and ties; rotation invariance; peer changes; invalid/failed vectors; lexical pipeline/comparison; immutable run paths; source and output tampering; and pending-review rejection.

Synthetic fixtures exist only in temporary test directories. No real SEC filing acquisition, embedding-model download/inference, GPU execution, or financial experiment was run. Network/API behavior and model compatibility remain to be verified in the first live pilot. The tested host environment is recorded in starter-validation-environment.json; it is not an embedding environment lock.

## Update — 2026-11-03

21 tests now pass after adding source-mapped extraction, hidden-text and boundary cases, and AI-review scope/source-map integrity tests. Actual batch integration and second-parser checks are documented in reports/extraction_2026-11-03.md. This supersedes the earlier statement that no real SEC data had been processed; pretrained model inference and financial experiments remain unrun.
