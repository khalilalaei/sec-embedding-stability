# Local Codex handoff - start here

User: Khalil Alaei. Independent UCLA SEC embedding stability project. User deadline: December 5, 2026. User wants local terminal execution and batch progress with minimal command relay. The project is GitHub-backed at https://github.com/khalilalaei/sec-embedding-stability . Preserve original work; do not import another student's repository or results.

## First local session

Read AGENTS.md and docs/THREE_WEEK_SPRINT.md. Inspect git status. Create a dedicated branch for the local sprint, preserving user modifications. Read the actual config/model locks and relevant source files rather than assuming the scaffold already supports large longitudinal experiments.

Verify the local machine, Python, GPU, VRAM, torch/CUDA, disk and input directories. Use nvidia-smi and the actual Python environment. The older computer had a 4 GB RTX 3050 and 64 GB RAM; the user now offers a desktop i9/RTX 3070. Do not assume exact desktop VRAM or CUDA setup. Recreate environments on a new PC. Prefer a compute checkout/model cache outside OneDrive for heavy I/O while retaining the original source/data copy.

A new clone contains code and curated result evidence, but not ignored source data or environments. Copy the existing data directory safely to the compute computer or retrieve the user's preserved archives; never assume git pull transfers it. Keep both original copies until hash verification.

## Current ignored data expected on the user's original project computer

- data/corpus_extracted_v1.json, data/raw/CIK/filing.html, data/text/extracted_v1/: original source-matched 12-section pilot.
- data/history/inventory_v1/: 143 original 10-K metadata records, 12 CIKs, 2015-01-01 through 2026-11-02. All 99 metadata file hashes and four output hashes audited. Deere has 11 filings because the cutoff precedes its observed December filing pattern.
- data/history/headers_v1/: 143 matching source header responses. All source/output hashes and records audited. Every response contains agreeing tag and labeled header copies. API clocks match source clocks under an explicit ET interpretation; availability approval remains pending.
- data/market/yahoo_pilot_v2/: 12-company adjusted-price proxy, 711 daily return dates through 2026-11-02, vendor aliases only. Not CRSP permanent-security data.
- .venv: Python 3.11.9 CPU project environment; .venv-gpu: CUDA environment used for E5/Qwen. Both need verification on this machine.
- SEC_USER_AGENT must identify the actual user/organization/contact for requests. Use the existing user-provided header; do not put credentials in Git. SEC requests stay sequential under the project delay.

## Evidence and conventions

Pinned models: configs/models.pilot_2026-11-03.lock.json. E5/BGE/Qwen; 192/320 are total-token budgets including prefixes and special tokens. Equal mean of normalized chunks, then document normalization. Full-corpus TF-IDF exists only as a descriptive pilot fit; historical financial evaluation needs past-only fitting.

Pilot reports are reports/pilot_stability_2026-11-03.md, reports/risk_accuracy_2026-11-14.md, reports/risk_calibration_2026-11-14.md and reports/score_level_comparison_2026-11-14.md. There are 12 embedded sections, three inspected financial windows, and no demonstrated incremental text value. Current weight/calibration choices were developed on those windows. They are not new holdouts. Modern model training cutoffs remain unknown.

The source/header repair supports hidden tag-style plus visible labeled copies and rejects conflicts. Resume the existing collection rather than deleting it if needed. The source batch in secstab.history_corpus is newly added: its conservative extractor can flag incorporated-by-reference/old layouts. Preserve those flags; machine candidates are not admitted text. Existing source maps must remain traceable to exact bytes. Latest tested count is 112 offline tests; verify after changes.

## Immediate execution task (do the work, not just a plan)

1. Confirm source inputs and environments, run focused required checks, inspect hardware and log them in docs/LOCAL_EXECUTION_LOG.md.
2. Run a small source/extraction checkpoint, then the complete 143-record batch with the existing Python environment and SEC contact header:
   python -m secstab.history_corpus --limit 5
   python -m secstab.history_corpus --resume
   Use the explicit environment executable in PowerShell. If a prior batch exists, inspect its status and use --resume; do not overwrite evidence.
3. Review the candidate/flag ledger, stratified section boundary samples and source maps. Preserve exclusions. Generalize parser behavior only from observed source evidence and tests; version changed extraction outputs. Provide a compact human QA queue to the user and distinguish sampled human checks from AI-assisted checks.
4. Cache shared chunks and benchmark a representative document set on the actual GPU. Preserve prefixes, exact tokenizer revisions, total budgets and chunk coverage. Record chunks/sec, words/tokens, batch size, dtype, peak VRAM and wall time. Do not start redundant full inference before checking caches/outputs.
5. Write the expanded protocol and deterministic cohort rules/splits/controls before examining new financial losses. Preferred scoped target: 100 companies, with 50 as a justified fallback, about 8 years. Establish identity/industry/source feasibility. Do not cherry-pick companies or decide exclusions using model performance.
6. Implement the time-varying panel and fair controls, then execute according to docs/THREE_WEEK_SPRINT.md. Save all results, including negative ones. Ask only for missing access, genuinely necessary scientific choices or user-authorized paid actions.

## Progress reporting

Report actual counts (downloaded, extracted, flagged, reviewed, embedded, evaluated), elapsed/runtime estimates from measurements, current blockers and the next gate. Commit focused code/docs changes to the sprint branch with concise evidence. End substantive sessions with a saved execution log so context survives a new session. Avoid simultaneous agents writing the same branch; this chat and the local session coordinate via Git and the execution log.

## Official local Codex setup reference

https://learn.chatgpt.com/docs/codex/cli . Install on the chosen Windows PC, sign in with ChatGPT, open the repository folder and have Codex read this handoff. Running a separate local session does not automatically import this conversation.
