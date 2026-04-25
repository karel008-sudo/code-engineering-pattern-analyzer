"""
analyzers/style_continuity.py — Style continuity break detection.

Splits a file into windows/segments and measures style consistency.
A file with uniform style throughout → continuous (could be AI-generated or well-maintained).
A file with a sudden style change → discontinuity → more likely AI-assisted or mixed-origin.

Key insight: style DISCONTINUITY (local AI-like block in human file)
is stronger evidence for AI-ASSISTED than for FULLY-AI-GENERATED.

Returns:
  - continuity_score: 1.0 = perfectly continuous, 0.0 = maximum discontinuity
  - style_breaks: list of (line_start, line_end, severity) for suspicious sections
"""
from __future__ import annotations

import re
import statistics
from typing import Dict, List, Tuple


# ── Style vector computation ───────────────────────────────────────────────────

def _compute_window_style(lines: List[str]) -> Dict[str, float]:
    """
    Compute a style feature vector for a window of source lines.

    Features:
      - avg_line_length:         Average non-empty line length.
      - comment_density:         Fraction of lines that are comments.
      - blank_line_ratio:        Fraction of lines that are blank.
      - avg_token_length:        Approximated average identifier token length.
      - indentation_consistency: Standard deviation of indent levels (higher = less consistent).

    Args:
        lines: A list of raw source lines for this window.

    Returns:
        Dict mapping feature name → float. All values are normalised
        to approximately [0, 1] for comparability.
    """
    if not lines:
        return {
            "avg_line_length": 0.0,
            "comment_density": 0.0,
            "blank_line_ratio": 0.0,
            "avg_token_length": 0.0,
            "indentation_consistency": 0.0,
        }

    total = len(lines)
    non_blank = [l for l in lines if l.strip()]
    blank_count = total - len(non_blank)
    blank_ratio = blank_count / total

    # Average line length (normalised to 0–1 range assuming max ~120 chars)
    if non_blank:
        avg_len = sum(len(l) for l in non_blank) / len(non_blank)
    else:
        avg_len = 0.0
    avg_len_norm = min(1.0, avg_len / 120.0)

    # Comment density
    comment_re = re.compile(r"^\s*(?://|#|/\*|\*|<!--|--|'''|\"\"\"|rem\s)", re.I)
    comment_count = sum(1 for l in lines if comment_re.match(l))
    comment_density = comment_count / total

    # Average token length (rough proxy: split on non-alphanumeric)
    all_tokens = re.findall(r"[a-zA-Z_]\w*", " ".join(non_blank))
    if all_tokens:
        avg_token_len = sum(len(t) for t in all_tokens) / len(all_tokens)
    else:
        avg_token_len = 0.0
    avg_token_len_norm = min(1.0, avg_token_len / 20.0)

    # Indentation consistency: std-dev of leading-space count
    indent_levels = []
    for l in non_blank:
        stripped = l.lstrip()
        indent = len(l) - len(stripped)
        indent_levels.append(indent)

    if len(indent_levels) >= 2:
        try:
            indent_std = statistics.stdev(indent_levels)
        except statistics.StatisticsError:
            indent_std = 0.0
    elif indent_levels:
        indent_std = 0.0
    else:
        indent_std = 0.0

    # Normalise indent std to 0–1 (assume max meaningful std ~16 spaces)
    indent_consistency_norm = min(1.0, indent_std / 16.0)

    return {
        "avg_line_length": avg_len_norm,
        "comment_density": comment_density,
        "blank_line_ratio": blank_ratio,
        "avg_token_length": avg_token_len_norm,
        "indentation_consistency": indent_consistency_norm,
    }


# ── Style distance ─────────────────────────────────────────────────────────────

# Weights for each feature in the Manhattan distance computation
_FEATURE_WEIGHTS: Dict[str, float] = {
    "avg_line_length": 0.25,
    "comment_density": 0.30,
    "blank_line_ratio": 0.15,
    "avg_token_length": 0.15,
    "indentation_consistency": 0.15,
}


def _style_distance(v1: Dict[str, float], v2: Dict[str, float]) -> float:
    """
    Compute weighted Manhattan distance between two style vectors.

    The result is in [0, 1] where 0 = identical style and 1 = maximally
    different style across all features.

    Args:
        v1: Style vector for window 1.
        v2: Style vector for window 2.

    Returns:
        Weighted Manhattan distance in [0, 1].
    """
    total_weight = sum(_FEATURE_WEIGHTS.values())
    distance = 0.0
    for feature, weight in _FEATURE_WEIGHTS.items():
        a = v1.get(feature, 0.0)
        b = v2.get(feature, 0.0)
        distance += abs(a - b) * weight
    # Normalise by total weight to keep in [0, 1]
    return min(1.0, distance / total_weight)


# ── Main continuity score ──────────────────────────────────────────────────────

def style_continuity_score(
    text: str,
    window_size: int = 40,
) -> Tuple[float, List[Tuple[int, int, float]]]:
    """
    Compute a style continuity score for a source file.

    Splits the file into consecutive windows of ``window_size`` lines,
    computes a style vector per window, and measures the distance between
    consecutive windows.

    Args:
        text:        Raw source file text.
        window_size: Number of lines per window. Default 40.

    Returns:
        A tuple (continuity_score, style_breaks) where:
          - continuity_score: Float in [0, 1]. 1.0 = perfectly uniform style.
            0.0 = maximum detected discontinuity.
          - style_breaks: List of (start_line, end_line, distance) tuples for
            windows where consecutive distance exceeds 0.30.

    Notes:
        - Files with fewer than 30 lines return (0.70, []) — insufficient data.
        - Files with a single window (< 2 × window_size lines) return (0.75, []).
    """
    lines = text.splitlines()
    total_lines = len(lines)

    # Not enough lines for meaningful analysis
    if total_lines < 30:
        return 0.70, []

    # Split into windows
    windows: List[List[str]] = []
    for start in range(0, total_lines, window_size):
        window = lines[start: start + window_size]
        if len(window) >= 5:  # skip tiny trailing windows
            windows.append(window)

    if len(windows) < 2:
        return 0.75, []

    # Compute style vector per window
    style_vectors = [_compute_window_style(w) for w in windows]

    # Compute distances between consecutive windows
    distances: List[float] = []
    for i in range(len(style_vectors) - 1):
        d = _style_distance(style_vectors[i], style_vectors[i + 1])
        distances.append(d)

    mean_distance = sum(distances) / len(distances)
    continuity = max(0.0, min(1.0, 1.0 - mean_distance))

    # Identify style breaks (windows with distance > 0.30)
    style_breaks: List[Tuple[int, int, float]] = []
    for i, d in enumerate(distances):
        if d > 0.30:
            start_line = i * window_size
            end_line = min((i + 2) * window_size, total_lines)
            style_breaks.append((start_line, end_line, round(d, 4)))

    return round(continuity, 4), style_breaks


# ── Human irregularity score ───────────────────────────────────────────────────

_PRINT_STMT_RE = re.compile(r"\bprint\s*\(", re.MULTILINE)
_PRINT_STACK_RE = re.compile(r"\.printStackTrace\(\)", re.MULTILINE)
_BARE_EXCEPT_RE = re.compile(r"^\s*except\s*:", re.MULTILINE)
_TODO_FIXME_RE = re.compile(r"\b(?:TODO|FIXME|HACK|XXX|BUG)\b", re.MULTILINE)
_COMMENTED_CODE_RE = re.compile(
    r"^\s*(?://|#)\s*(?:\w+\s*[=({]|return\s+\w+|if\s+\w+|for\s+\w+)",
    re.MULTILINE,
)
_MAGIC_NUMBER_RE = re.compile(r"\b(?:[3-9]\d{2,}|\d{4,})\b")
# Detect mixed naming conventions (camelCase variable followed by snake_case in same file)
_CAMEL_VAR_RE = re.compile(r"\b[a-z][a-zA-Z]{2,}\b")
_SNAKE_VAR_RE = re.compile(r"\b[a-z][a-z_]{2,}[a-z]\b")


def human_irregularity_score(text: str, lang: str) -> float:
    """
    Detect human coding patterns that AI rarely produces consistently.

    Signals:
      - ``print()`` / ``println`` instead of a logger
      - ``e.printStackTrace()`` in Java/Kotlin
      - Bare ``except:`` in Python
      - Magic numbers in high quantity
      - Inconsistent naming (mix of camelCase and snake_case variables)
      - TODO/FIXME/HACK without context (bare markers)
      - Commented-out code blocks

    Args:
        text:  Raw source file text.
        lang:  Language string (e.g. "Python", "Java", "Kotlin").

    Returns:
        Float in [0.0, 1.0] where 1.0 = very human-like irregularity.
        Returns 0.0 when no irregular patterns are detected.
    """
    lines = text.splitlines()
    total_lines = max(len(lines), 1)

    signal_score = 0.0

    # 1. print() / println instead of logger
    print_count = len(_PRINT_STMT_RE.findall(text))
    if print_count > 0:
        signal_score += min(0.20, print_count / total_lines * 20)

    # 2. printStackTrace() — Java/Kotlin diagnostic anti-pattern
    if lang in ("Java", "Kotlin"):
        stack_count = len(_PRINT_STACK_RE.findall(text))
        if stack_count > 0:
            signal_score += min(0.15, stack_count * 0.05)

    # 3. Bare except — Python
    if lang == "Python":
        bare_except_count = len(_BARE_EXCEPT_RE.findall(text))
        if bare_except_count > 0:
            signal_score += min(0.15, bare_except_count * 0.07)

    # 4. Magic numbers (high count → human-like)
    magic_count = len(_MAGIC_NUMBER_RE.findall(text))
    magic_density = magic_count / (total_lines / 10.0 + 1)
    if magic_density > 2.0:
        signal_score += min(0.15, (magic_density - 2.0) / 3.0 * 0.15)

    # 5. Inconsistent naming conventions
    if lang in ("Python",):
        camel_count = len(_CAMEL_VAR_RE.findall(text))
        snake_count = len(_SNAKE_VAR_RE.findall(text))
        total_vars = camel_count + snake_count
        if total_vars > 10:
            minority = min(camel_count, snake_count)
            mixing_ratio = minority / total_vars
            if mixing_ratio > 0.15:  # significant mixing
                signal_score += min(0.12, mixing_ratio * 0.20)

    # 6. TODO/FIXME/HACK without context
    todo_count = len(_TODO_FIXME_RE.findall(text))
    if todo_count > 0:
        signal_score += min(0.10, todo_count * 0.02)

    # 7. Commented-out code
    commented_code_count = len(_COMMENTED_CODE_RE.findall(text))
    if commented_code_count > 0:
        signal_score += min(0.12, commented_code_count * 0.03)

    return min(1.0, max(0.0, signal_score))
