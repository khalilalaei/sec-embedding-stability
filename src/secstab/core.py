"""Numerical operations; no remote services and no fitted return models."""
import hashlib
import re
import numpy as np
from scipy.stats import spearmanr


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize(x):
    x = np.asarray(x, dtype=float)
    norms = np.linalg.norm(x, axis=-1, keepdims=True)
    if not np.isfinite(x).all() or np.any(norms <= 0):
        raise ValueError("Nonfinite or zero vector: inspect document/model coverage")
    return x / norms


def shared_chunks(text, fits):
    """Identical contiguous source spans, bounded by EVERY model's tokenizer.

    Greedy whitespace-unit packing; long units are split by characters.
    Offsets are Python Unicode character offsets, end exclusive.
    This intentionally tests a simple deterministic boundary rule, not sentences.
    """
    ends = [m.end() for m in re.finditer(r"\S+\s*", text)]
    if not ends:
        raise ValueError("Empty document")
    spans, start, stop = [], 0, 0
    for end in ends:
        if fits(text[start:end]):
            stop = end
            continue
        if stop > start:
            spans.append((start, stop))
            start = stop
        # Handle unusually long single units without dropping source characters.
        while not fits(text[start:end]):
            low, high, best = start + 1, end, None
            while low <= high:
                mid = (low + high) // 2
                if fits(text[start:mid]):
                    best, low = mid, mid + 1
                else:
                    high = mid - 1
            if best is None:
                raise ValueError("Budget too small even for one character plus prefix")
            spans.append((start, best))
            start = best
        stop = end
    if stop > start:
        spans.append((start, stop))
    if spans[-1][1] < len(text):
        raise AssertionError("Source coverage incomplete")
    return spans


def peers(similarity, k):
    s = np.asarray(similarity, dtype=float)
    if s.ndim != 2 or s.shape[0] != s.shape[1] or not np.isfinite(s).all():
        raise ValueError("Expected finite square similarity matrix")
    if not 1 <= k < len(s) - 1:
        raise ValueError("Need 1 <= k < n-1 to compute boundary margins")
    masked = s.copy()
    np.fill_diagonal(masked, -np.inf)
    ranks = np.argsort(-masked, axis=1, kind="stable")[:, :len(s)-1]
    chosen = ranks[:, :k]
    margins = np.array([s[i, r[k-1]] - s[i, r[k]] for i, r in enumerate(ranks)])
    return chosen, ranks, margins


def compare(a, b, ids, k):
    if a.shape != b.shape or a.shape != (len(ids), len(ids)):
        raise ValueError("Matrix/order mismatch")
    pa, ra, ma = peers(a, k)
    pb, rb, mb = peers(b, k)
    upper = np.triu_indices(len(ids), 1)
    rho = float(spearmanr(a[upper], b[upper]).statistic)
    if not np.isfinite(rho):
        rho = None  # Undefined for constant similarities; never convert to success.
    rows = []
    for i, doc in enumerate(ids):
        x, y = set(pa[i]), set(pb[i])
        rows.append({"document_id":doc, "overlap":len(x & y)/k,
                     "jaccard":len(x & y)/len(x | y),
                     "margin_a":float(ma[i]), "margin_b":float(mb[i]),
                     "peers_a":[ids[j] for j in pa[i]],
                     "peers_b":[ids[j] for j in pb[i]]})
    return {"spearman_pair_similarity":rho,
            "mean_top_k_overlap":float(np.mean([r["overlap"] for r in rows])),
            "mean_top_k_jaccard":float(np.mean([r["jaccard"] for r in rows])),
            "mean_absolute_similarity_change":float(np.mean(np.abs(a[upper]-b[upper]))),
            "note":"Cross-model score distances are descriptive; score scales differ. Pairs are dependent; no significance test is implied.",
            "companies":rows}
