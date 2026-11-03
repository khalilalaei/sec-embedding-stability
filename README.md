# SEC Embedding Stability

Independent research starter by Khalil Alaei. Built from an empty project: no external team repository, saved embeddings, or previous empirical results are inputs.

**Research question:** How much do SEC-filing company similarities and financial conclusions change across embedding models and processing choices, and does text add value beyond price and industry information?

**Current status:** runnable starter code with offline software tests. No SEC downloads, pretrained-model inference, measured embedding stability, or financial experiments have been executed in this package. Unit-test fixtures are synthetic and are never research evidence.

## Chosen starting design

- Text: **10-K Item 1A Risk Factors**. One manually reviewed section per company.
- Pilot: **12 companies / six industry pairs**, selected before inspecting results. Latest eligible original 10-K in SEC recent submissions, with filing date no later than 2026-11-02. This is a descriptive date-based pilot; not a historical point-in-time universe.
- Primary model: **intfloat/e5-base-v2**.
- Comparators: **BAAI/bge-base-en-v1.5**, **Qwen/Qwen3-Embedding-0.6B**.
- Non-neural baseline: TF-IDF cosine, fitted to this descriptive pilot only.
- First tests: model family, **192 versus 320 total-token budgets** (including prefixes and special tokens), and top-2 peers. Budgets bound every tokenizer; they are not body-token counts.
- Aggregation: equal mean of normalized chunk vectors, then normalize the document vector. Alternative weighting and sentence boundaries are future experiments.
- Main stability outcomes: off-diagonal similarity Spearman correlation, top-k overlap/Jaccard, per-company boundary margins.
- Financial follow-up: covariance and risk, then volatility and returns. None implemented or evaluated yet.

## Step 1: Get the project onto your computer

Repository: https://github.com/khalilalaei/sec-embedding-stability

This is a private, independent research repository. With Git for Windows installed, open PowerShell in the folder where you keep projects:

```powershell
git clone https://github.com/khalilalaei/sec-embedding-stability.git
cd sec-embedding-stability
```

Authenticate through the normal GitHub browser prompt if requested. Never put passwords or tokens in shell commands. Alternatively download and extract the repository ZIP from GitHub's Code menu, then open PowerShell in the extracted project folder. Git is recommended for tracking research changes.

## Step 2: Install and check the project

Use Python 3.11 or 3.12. From the project root:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[embed]"
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\secstab.exe --help
```

For a lighter first install without embedding dependencies, use `pip install -e .` inside the environment; tfidf, source download, review, comparisons, and numerical tests do not require model weights. On macOS/Linux use `python3.11 -m venv .venv`, `.venv/bin/python`, and `.venv/bin/secstab`.

Dependency ranges are compatibility bounds, not a frozen environment. Every run records the installed package versions. Before formal experiments freeze an exact tested environment, including platform and CUDA details; do not silently upgrade between configurations.

## Step 3: Download original SEC filings

Read `configs/universe.json` and `docs/PROTOCOL.md` first. Set a real SEC user-agent identity:

```powershell
$env:SEC_USER_AGENT = "Khalil Alaei UCLA your-real-email@example.com"
.\.venv\Scripts\secstab.exe fetch
```

Replace the example email with your actual contact. The command saves original filing HTML, SEC submission metadata, hashes, timestamps, company names, and SEC tickers. It does **not** automatically extract or approve Risk Factors text. Confirm each company/CIK identity in the saved metadata.

Requests are sequential with a pause. Respect SEC fair-access instructions; stop and inspect access errors rather than aggressively retrying. A partial collection is preserved; the command refuses to overwrite an existing `data/filings.json`. To restart, archive the entire current data directory first. Large older histories may require SEC historical submission files; this starter fails clearly rather than substituting another form.

## Step 4: Review and admit the text

Follow `docs/DATA_REVIEW.md`. Save one complete, reviewed UTF-8 Risk Factors section per company in `data/text/`. Use the accession number printed by `fetch` as the document ID.

```powershell
.\.venv\Scripts\secstab.exe admit --document-id "ACTUAL-ACCESSION-NUMBER" --text data/text/MSFT_item1a.txt --reviewer "Khalil Alaei" --notes "Verified full Item 1A against saved SEC source; excluded table of contents and next item; extraction method and limitations recorded in review log."
```

Repeat for every company. Do not paste the example assertion unless you actually performed those checks. The first complete pilot uses all 12; >=4 documents are allowed for development checks only. Source bytes and admitted text hashes are checked before every analysis.

## Step 5: Run the lexical baseline

```powershell
.\.venv\Scripts\secstab.exe tfidf --run-id pilot_tfidf --k 2
```

Read `runs/pilot_tfidf/peers.json`. This checks the corpus/analysis workflow without downloading a neural model. It is not evidence that a neural embedding helps.

## Step 6: Lock the models

```powershell
.\.venv\Scripts\secstab.exe lock-models
```

This queries each official Hugging Face model repository and records its exact current commit SHA. Run this **once**, before experiments. Keep the lock file unchanged across the pilot. Training-cutoff entries start as unknown; investigate documentation rather than inferring cutoffs from release dates.

## Step 7: Embed identical spans with each model

```powershell
.\.venv\Scripts\secstab.exe embed --model e5 --budget 192 --run-id pilot_e5_192
.\.venv\Scripts\secstab.exe embed --model bge --budget 192 --run-id pilot_bge_192
.\.venv\Scripts\secstab.exe embed --model qwen --budget 192 --run-id pilot_qwen_192 --device cuda --batch-size 8
```

The first two default to CPU. Qwen's example requires a CUDA-capable PyTorch installation and available GPU; use `--device cpu --batch-size 1` if necessary, with a potentially much longer runtime. The code does not assume a GPU is available. No timing or memory benchmark is claimed.

All three runs load all locked tokenizers to create the same contiguous source spans for a given budget. Model-specific prefixes are included in the fit check. No silent truncation is allowed. Source-span hashes can be compared across model runs. The selected Qwen symmetric instruction is a researcher choice; test alternatives later. Model-specific pooling comes from the pinned SentenceTransformer checkpoint and is recorded in run settings.

Then repeat E5 with 320 tokens:

```powershell
.\.venv\Scripts\secstab.exe embed --model e5 --budget 320 --run-id pilot_e5_320
```

For all three models' budget sensitivity, repeat BGE and Qwen at 320 too. Change only the declared budget. A larger budget reduces chunk count, not source coverage. All chunks are embedded; the document is not limited to its opening passage.

## Step 8: Compare configurations

```powershell
.\.venv\Scripts\secstab.exe compare --a runs/pilot_e5_192 --b runs/pilot_bge_192 --output runs/e5_vs_bge_192.json
.\.venv\Scripts\secstab.exe compare --a runs/pilot_e5_192 --b runs/pilot_e5_320 --output runs/e5_budget_comparison.json
.\.venv\Scripts\secstab.exe compare --a runs/pilot_tfidf --b runs/pilot_e5_192 --output runs/tfidf_vs_e5.json
```

Identical corpus hashes/order and complete intact runs are required. Run IDs and comparison files are never overwritten. Similarity-score scales differ across families: prioritize rankings/peer agreement; absolute score changes are descriptive. Exact ties use document-order tie-breaking, with zero margins signaling ambiguity. Pairwise similarities are statistically dependent; no significance claim follows from their count.

## Step 9: Financial study

Use `docs/FINANCIAL_NEXT.md`. Obtain properly licensed returns, define actual historical availability and model timing, freeze chronology and baselines, then implement the approved task. A current model applied to old documents is not automatically a historical forecast.

## What to commit

Commit source, configs, protocol, review templates, and curated evidence summaries. Raw filings, extracted text, model lock, and run directories are ignored by default to prevent accidental bulk or sensitive-data uploads. Preserve complete run evidence locally with backups. Once validated, intentionally add the exact model lock and a sanitized results/provenance summary to the research branch. Never commit credentials or licensed market data without checking terms.

See `docs/MODELS.md` for primary sources. No research performance is claimed by this starter.
