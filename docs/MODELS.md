# Model decisions and official sources

Selected on 2026-11-02 before running this project. These are research choices, not SEC-task performance claims.

| Model | Role | Input convention | Why selected |
| --- | --- | --- | --- |
| intfloat/e5-base-v2 | Primary | query: on both texts for symmetric similarity | Manageable English encoder with an explicit semantic similarity convention |
| BAAI/bge-base-en-v1.5 | Comparator | No prefix for symmetric document comparison | Another English embedding family at a manageable scale |
| Qwen/Qwen3-Embedding-0.6B | LLM-based comparator | Fixed symmetric Instruct/Query prefix on every passage | Adds an instruction-aware decoder-based embedding family without beginning at 4B/8B scale |
| TF-IDF cosine | Lexical control | Full reviewed section text | Tests whether neural representations add beyond shared vocabulary |

Sources, retrieved 2026-11-02:
- https://huggingface.co/intfloat/e5-base-v2 — documented 768-dimensional output and symmetric query-prefix guidance.
- https://huggingface.co/BAAI/bge-base-en-v1.5 — official BGE model card and SentenceTransformer usage. Instructions intended for asymmetric retrieval should not be applied blindly to one side of a symmetric company comparison.
- https://huggingface.co/Qwen/Qwen3-Embedding-0.6B — official Qwen model card; 0.6B parameters, up to 1024 dimensions, instruction support. Symmetric Risk Factors instruction is our study choice, not a vendor-validated SEC instruction.

Resolve revisions with lock-models; retain the same lock across all models and budgets. Embedding defaults and model cards may change. Record the precise checkpoint and actual runtime architecture. The starter does not download and snapshot model-card files; do that before a formal study and retain license/training-data evidence alongside the lock.

Initial training cutoffs: **unknown until independently documented**, including base pretraining, embedding training, fine-tuning and distillation. A release timestamp is not the cutoff. License terms should be saved with each exact revision.

Expansion candidates after pilot: intfloat/e5-large-v2 (size within family), BAAI/bge-m3 (another context/representation design), nomic-ai/nomic-embed-text-v1.5 (new family with explicit task prefixes), Qwen/Qwen3-Embedding-4B (size within family). Do not add candidates just to search for the best held-out return result. Freeze expansion rationale before evaluation. Adding a model to the shared-tokenizer configuration changes chunk definitions; create a new experiment series and rerun all matched arms.
