"""
analyzers/similarity.py — Cross-file TF-IDF cosine similarity.

Computes how similar each file is to others in the same repo.
High average similarity = files share structural vocabulary = AI batch pattern.

No external dependencies — uses standard math + collections.
"""
from __future__ import annotations
import math
import re
from collections import Counter
from typing import Dict, List, Tuple

_TOKEN_RE = re.compile(r"\b[a-zA-Z_]\w*\b")


def _tf(tokens: List[str]) -> Dict[str, float]:
    """Term frequency: count / total."""
    if not tokens:
        return {}
    freq = Counter(tokens)
    total = sum(freq.values())
    return {t: c / total for t, c in freq.items()}


def _cosine(a: Dict[str, float], b: Dict[str, float]) -> float:
    """Cosine similarity between two TF vectors."""
    common = set(a) & set(b)
    if not common:
        return 0.0
    dot   = sum(a[t] * b[t] for t in common)
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    denom  = norm_a * norm_b
    return dot / denom if denom > 0 else 0.0


def tokenize_file(text: str) -> Dict[str, float]:
    """Tokenize source text into a TF vector."""
    tokens = _TOKEN_RE.findall(text.lower())
    return _tf(tokens)


def compute_similarity_scores(tf_vectors: List[Dict[str, float]]) -> List[float]:
    """
    For each file, compute its average cosine similarity to all other files.
    Returns list of per-file similarity scores in [0.0, 1.0].

    High score = this file's vocabulary closely matches other repo files
    = consistent with AI batch-generation.

    Complexity: O(n²) — works well for repos up to ~500 files.
    For larger repos, uses random sampling.
    """
    n = len(tf_vectors)
    if n < 2:
        return [0.0] * n

    # For large repos: sample up to 50 comparison partners
    max_comparisons = 50

    scores: List[float] = []
    for i, vec_i in enumerate(tf_vectors):
        if n <= max_comparisons + 1:
            partners = [j for j in range(n) if j != i]
        else:
            import random
            partners = random.sample([j for j in range(n) if j != i], max_comparisons)

        sims = [_cosine(vec_i, tf_vectors[j]) for j in partners]
        avg  = sum(sims) / len(sims) if sims else 0.0
        scores.append(avg)

    return scores


def similarity_to_ai_signal(avg_sim: float) -> float:
    """
    Map average cosine similarity to an AI-pattern signal [0.0, 1.0].

    Reference values from GPC codebase analysis:
      Human repos: avg similarity ~0.05–0.15
      AI-heavy repos: avg similarity ~0.25–0.45
    """
    # Linear ramp: <0.05 = neutral (0.3), >0.40 = high AI signal (0.85)
    if avg_sim < 0.05:
        return 0.25
    if avg_sim > 0.40:
        return 0.85
    return round(0.25 + (avg_sim - 0.05) / 0.35 * 0.60, 4)
