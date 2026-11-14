# SEC embedding stability research

Independent project owned by Khalil Alaei. Read docs/LOCAL_CODEX_HANDOFF.md and docs/THREE_WEEK_SPRINT.md before changing the research workflow. Current primary deadline: December 5, 2026; aim for a scoped empirical research draft, not guaranteed publication or positive performance.

## Work autonomously within the requested task

Use local code and terminal tools to implement, test and execute authorized reversible research work in batches. Keep a concise progress log. Do not require the user to relay every intermediate command or output. Ask for genuinely missing decisions or access; do not invent results or silently weaken source/review gates to get a green run.

## Scientific and data invariants

- Preserve all original pilot runs, source bytes, manifests and results. New experiments/configs get new versioned outputs; only documented --resume paths may append to incomplete work.
- Raw/provider data, credentials, virtual environments and model caches remain outside Git. data/history and data/market are ignored.
- Extraction candidates are not admitted text. Record flags/exclusions and review scope truthfully. Source provenance and original public availability are distinct from fiscal/report dates.
- Historic identifiers, corporate actions and any XOM predecessor/successor assumptions require explicit treatment. Do not claim the selected cohort is representative or point-in-time S&P 500 membership.
- All currently inspected 2024-2026 observations and three pilot evaluation blocks are development evidence. Freeze the expanded design before inspecting new financial losses.
- Unknown model training cutoffs remain unknown. November embeddings on old outcomes are retrospective; timing-clock agreement is not proof against look-ahead.
- Fit TF-IDF vocabulary, calibration, scaling, PCA and all learned transforms using permitted past data only for financial evaluation. For each decision use the exact eligible filing for that company; never apply the latest filing to earlier dates.
- Controls include price-only, extra diagonal shrinkage, past-price constant correlation, industry/sector controls and suitable text-free/score-level controls. Preserve adverse and null results.
- Pair counts, settings and firm-month rows are not independent statistical replications. Use a predeclared dependence-aware inference plan.

## Environment and execution

Windows project currently uses .venv (CPU Python 3.11.9) and .venv-gpu (CUDA). Recreate environments on a new computer; do not assume copied environments are portable. Confirm actual GPU/VRAM with nvidia-smi and torch. Run SEC requests sequentially under the existing delay/contact policy. Do not bypass a provider block.

Run meaningful tests for changed behavior: python -m unittest discover -s tests -q. Use the explicit environment python executable in PowerShell. Do not repeatedly rerun expensive inference unless changes or failures justify it. Use checkpoints/caches and log runtime/chunks/peak VRAM so scale estimates are measured.

## Git workflow

Inspect git status and preserve user changes. Use a dedicated sprint branch for local-agent implementation. Avoid concurrent edits to the same branch from separate sessions. Commit focused changes and maintain docs/LOCAL_EXECUTION_LOG.md. Existing files include private ignored data not present in a new Git clone; verify input folders before executing jobs.
