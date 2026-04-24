"""
analyzers/lexical.py — Token-level statistical analysis.

All functions return a float in [0.0, 1.0] where 1.0 = strong AI-like pattern.

Signals:
  token_entropy     — low Shannon entropy (repetitive vocabulary) = AI-like
  type_token_ratio  — low TTR (few unique tokens vs total) = AI-like
  repetition_index  — consecutive identical structural blocks = AI-like
"""
from __future__ import annotations
import math
import re
from collections import Counter
from typing import List


# Tokenizer: identifier tokens only (skip punctuation and literals)
_TOKEN_RE = re.compile(r"\b[a-zA-Z_]\w*\b")


def _tokenize(text: str) -> List[str]:
    return _TOKEN_RE.findall(text.lower())


def token_entropy(text: str) -> float:
    """
    Shannon entropy of the token distribution, normalized to [0,1].
    Low entropy = few token types used repeatedly = AI-like pattern.
    Returns AI signal: 1.0 when entropy is very low, 0.0 when very high.
    """
    tokens = _tokenize(text)
    if len(tokens) < 20:
        return 0.5  # too little data

    freq = Counter(tokens)
    total = sum(freq.values())
    # Raw Shannon entropy
    raw_h = -sum((c / total) * math.log2(c / total) for c in freq.values())
    # Normalize by theoretical max (all unique)
    max_h = math.log2(len(freq)) if len(freq) > 1 else 1.0
    normalized = raw_h / max_h  # 0 = completely repetitive, 1 = all unique

    # Invert: low normalized entropy → high AI signal
    # Apply a soft curve: most code sits around 0.7–0.9 normalized entropy
    ai_signal = max(0.0, min(1.0, 1.0 - normalized))
    return round(ai_signal, 4)


def type_token_ratio(text: str) -> float:
    """
    TTR = unique_tokens / total_tokens.
    Low TTR = repetitive vocabulary = AI-like.
    Returns AI signal (inverted TTR, smoothed).
    """
    tokens = _tokenize(text)
    if len(tokens) < 20:
        return 0.5

    # Use moving-window TTR to reduce length bias
    # Split into windows of 50 tokens, average their TTRs
    window = 50
    ttrs = []
    for i in range(0, len(tokens) - window + 1, window // 2):
        chunk = tokens[i:i + window]
        ttrs.append(len(set(chunk)) / len(chunk))

    avg_ttr = sum(ttrs) / len(ttrs) if ttrs else len(set(tokens)) / len(tokens)
    # TTR ~0.5 is typical for human code, AI tends toward ~0.35–0.45
    # Map to AI signal: lower TTR → higher signal
    ai_signal = max(0.0, min(1.0, (0.70 - avg_ttr) / 0.35))
    return round(ai_signal, 4)


def repetition_index(text: str) -> float:
    """
    Detects structurally repeated blocks — a pattern common in AI-generated code
    (e.g., nearly identical if-blocks, repeated exception handlers, similar methods).

    Splits text into overlapping n-gram shingles and measures repetition.
    Returns AI signal: 1.0 = high structural repetition.
    """
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if len(lines) < 10:
        return 0.3

    # Use 3-line shingles as structural fingerprints
    shingle_size = 3
    shingles = []
    for i in range(len(lines) - shingle_size + 1):
        # Normalize: strip leading digits/identifiers that vary between instances
        shingle = " | ".join(
            re.sub(r"\b\w+\b", "X", lines[i + j]) for j in range(shingle_size)
        )
        shingles.append(shingle)

    if not shingles:
        return 0.3

    total = len(shingles)
    unique = len(set(shingles))
    repetition = 1.0 - (unique / total)

    # Scale: 0–10% repetition is normal, >30% is AI-like
    ai_signal = max(0.0, min(1.0, (repetition - 0.05) / 0.25))
    return round(ai_signal, 4)
