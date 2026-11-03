# Independent pilot protocol v0.2 — proposed, updated 2026-11-03

Owner: Khalil Alaei. This protocol is newly specified for this project. It imports no previous team code, documents, embeddings, company results, or experiment outputs.

## Scope and hypotheses

Primary question: Do company-peer relationships from identical SEC Risk Factors text survive changes in embedding family and chunk budget?

Primary outcome: mean top-2 peer overlap for paired configurations. Secondary: top-2 Jaccard, pair-similarity Spearman correlation, per-company boundary margins, documented failures, compute cost.

Predeclared contrasts: E5 vs BGE at 192 total tokens; E5 vs Qwen at 192; BGE vs Qwen at 192; each model at 192 vs 320. TF-IDF comparisons are lexical controls. These are descriptive pilot comparisons; no hypothesis-test threshold or best-model claim is authorized from this sample.

## Sample

Twelve deliberately selected companies in six industry pairs, in configs/universe.json. Labels are selection aids, not a licensed or audited industry taxonomy. Match CIK/name/ticker to SEC data before analysis. One latest eligible original 10-K per company from SEC recent submission metadata, filing date <=2026-11-02. Exclude 10-K/A for this pilot, not by quietly substituting amendments.

This small current-company selection is not an unbiased historical universe. Reporting periods and filing dates differ across firms and must be reported. No cross-sectional economic interpretation may ignore these differences. Expand to historical point-in-time membership only after the pilot.

## Source gate

Download raw original SEC HTML and submission metadata; retain hashes. Extract the entire Item 1A and record the reviewer type and scope. For the current descriptive pilot, AI-assisted source/boundary review is permitted and labeled separately from manual human review. Reject missing, garbled, incomplete, or ambiguous sections and record reasons. No synthetic filler, hallucinated text, or inference results from unreviewed sources. Manual review is an author check, not an independent audit. AI-assisted review is also not an independent audit or a claim of sentence-by-sentence human review. It uses ai_assisted_passed only with descriptive_pilot_only scope and intact source-map hashes; ordinary pending extraction remains blocked. Four documents suffice for a software development check; all 12 are required for the intended pilot. Report failures/missingness, and do not silently change the universe.

## Representation

Pin exact Hugging Face model/tokenizer revisions before any neural run. Use E5 symmetric query prefix, no BGE prefix, and the fixed symmetric Qwen instruction in configs/models.json. Use each checkpoint's declared SentenceTransformer pooling. Record architecture and precision. Model family comparisons include training/objective/tokenizer/instruction differences; they cannot isolate architecture alone.

Shared source spans are greedily packed at whitespace boundaries against all tokenizers. Budgets are 192 or 320 TOTAL tokens, including model-specific prefix and special tokens. Split unusually long single units as needed; never drop source text. Offsets are Python Unicode characters, end exclusive. No overlap. Equal average of L2-normalized chunk vectors, then L2 normalize the document vector. All companies embedded with all chunks. Failed runs remain failed evidence; they do not become zero vectors.

## Analysis

Similarity S=ZZ^T. Exclude self from peers. Top-2 peers use deterministic stable sorting; disclose ties and zero margins. Compare off-diagonal upper triangles with Spearman; report undefined if constant. Do not directly compare unrelated embedding coordinates. For same-scale bounded score changes epsilon, a top-k boundary margin >2 epsilon is sufficient to retain membership. Do not apply this as a universal cross-model guarantee.

Report all contrasts, company-level outcomes and failures. No iid pair bootstrap or training-seed claim from fixed-weight repeats. Confirmatory uncertainty will require a larger sample and a company/time-aware inference plan.

## Financial boundary

No filing availability lag, historical security link, total-return feed, historical universe, model training cutoff, financial time split, forecast or portfolio has been approved or implemented here. See FINANCIAL_NEXT.md for proposals. TF-IDF fit to the complete pilot is descriptive and must be replaced with a past-only vocabulary/IDF fit in historical prediction.

## Change control

Before running, commit this protocol. Record any later edits with date, rationale, and whether outcomes were already seen. Freeze a separate version before main-study experiments. Every claim must point to exact run IDs, input hashes, code commit, metric definitions and result fields.

## Amendment log

2026-11-03, before neural or financial outcomes: user requested the assistant perform extraction rather than manual copying. Added versioned DOM extraction, same-assistant source/boundary review with a separate stdlib parser consistency check, logged page-artifact cleanup and visible-text/DOM source maps. Broadened the descriptive source gate to explicitly labeled AI-assisted review. No model, sample, primary metric or financial gate changed. Original manual files/corpus are preserved and the new corpus has its own version.
