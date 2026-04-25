"""
analyzers/scaffold.py — Scaffold completeness, magic number discipline, name-body coherence.

Scaffold completeness: measures how uniformly complete a file's structure is.
High completeness = everything uniformly implemented = AI-like scaffold signal.

Magic number discipline: measures use of unnamed numeric literals.
Low discipline (many magic numbers) = human-like signal.
High discipline (few magic numbers, use of constants) = AI-like or senior-dev signal.

Name-body coherence: measures alignment between function names and their implementation.
High coherence (name matches body) = could be AI-generated descriptive naming.
Low coherence (generic name, complex body) = human legacy signal.

All signals are SUPPORTING evidence, not decisive. A senior developer who
follows clean-code principles will naturally score high on scaffold signals.
"""
from __future__ import annotations

import re
import statistics
from typing import Dict, List, Optional, Tuple


# ── Method extraction helpers ──────────────────────────────────────────────────

# Match Python / Java / Kotlin / TypeScript function definitions
_PY_FUNC_RE = re.compile(
    r"^(?P<indent>\s*)(?:async\s+)?def\s+(?P<name>\w+)\s*\(",
    re.MULTILINE,
)
_JAVA_FUNC_RE = re.compile(
    r"^(?P<indent>[ \t]*)(?:public|private|protected|static|final|override|"
    r"suspend|fun|open|internal|\s){0,6}\s*\w[\w<>\[\]?,\s]*\s+"
    r"(?P<name>[a-z_]\w*)\s*\(",
    re.MULTILINE,
)


def _extract_python_methods(text: str) -> List[Tuple[str, List[str]]]:
    """
    Extract (method_name, body_lines) tuples for Python functions.
    Body lines include the lines between this def and the next def at same indent.
    """
    lines = text.splitlines()
    results: List[Tuple[str, List[str]]] = []
    positions = list(_PY_FUNC_RE.finditer(text))

    for i, m in enumerate(positions):
        name = m.group("name")
        start_line = text[:m.start()].count("\n")
        # end at next function at same or lower indent, or EOF
        end_line = len(lines)
        if i + 1 < len(positions):
            end_line = text[:positions[i + 1].start()].count("\n")
        body = lines[start_line + 1: end_line]
        results.append((name, body))

    return results


def _extract_java_methods(text: str) -> List[Tuple[str, List[str]]]:
    """
    Extract (method_name, body_lines) tuples for Java/Kotlin/TS functions.
    Uses a simple brace-counting approach to locate the method body.
    """
    lines = text.splitlines()
    results: List[Tuple[str, List[str]]] = []
    positions = list(_JAVA_FUNC_RE.finditer(text))

    for m in positions:
        name = m.group("name")
        start_offset = m.end()
        # Find opening brace
        brace_pos = text.find("{", start_offset)
        if brace_pos == -1:
            continue

        # Count braces to find matching close
        depth = 0
        body_start = text[:brace_pos].count("\n")
        close_pos = brace_pos
        for idx in range(brace_pos, len(text)):
            if text[idx] == "{":
                depth += 1
            elif text[idx] == "}":
                depth -= 1
                if depth == 0:
                    close_pos = idx
                    break

        body_end = text[:close_pos].count("\n")
        body = lines[body_start + 1: body_end]
        if body:
            results.append((name, body))

    return results


# ── Scaffold completeness ──────────────────────────────────────────────────────

_CRUD_METHODS = frozenset({
    "findById", "findAll", "save", "update", "delete", "deleteById",
    "create", "get", "getById", "getAll", "list", "insert", "remove",
})

_UNIFORM_EXCEPTION_RE = re.compile(
    r"\bcatch\s*\(\s*\w+Exception\b|\bcatch\s*\(\s*Exception\b|"
    r"\bexcept\s+\w+Error:|"
    r"\bexcept\s+Exception:",
    re.MULTILINE,
)


def scaffold_completeness(text: str, lang: str) -> float:
    """
    Measure how uniformly complete a file's structure is.

    Indicators of high scaffold completeness (AI-like):
      - Very similar method lengths (low coefficient of variation)
      - Complete CRUD pattern (all five operations present)
      - Uniform exception handling across methods
      - Consistent public/private structure

    Args:
        text: Raw source file text.
        lang: Language string (e.g. "Python", "Java", "Kotlin").

    Returns:
        Float in [0.0, 1.0]. 0.8+ only for very strong symmetry.
        Returns 0.30 (neutral) when there are fewer than 3 methods.
    """
    # Extract methods
    if lang == "Python":
        methods = _extract_python_methods(text)
    else:
        methods = _extract_java_methods(text)

    if len(methods) < 3:
        return 0.30  # insufficient data

    method_lengths = [len(body) for _, body in methods]

    # Coefficient of variation (CV) of method lengths
    mean_len = statistics.mean(method_lengths)
    if mean_len < 1:
        return 0.30

    try:
        std_len = statistics.stdev(method_lengths)
    except statistics.StatisticsError:
        std_len = 0.0

    cv = std_len / mean_len

    # CV < 0.3 → high symmetry → AI-like
    if cv < 0.15:
        symmetry_score = 0.90
    elif cv < 0.30:
        symmetry_score = 0.75
    elif cv < 0.50:
        symmetry_score = 0.55
    elif cv < 0.80:
        symmetry_score = 0.40
    else:
        symmetry_score = 0.25

    # Check for complete CRUD pattern
    method_names_lower = {name.lower() for name, _ in methods}
    crud_hits = sum(
        1 for m in _CRUD_METHODS
        if any(m.lower() in name for name in method_names_lower)
    )
    crud_bonus = min(0.10, crud_hits * 0.02)

    # Uniform exception handling
    exception_matches = len(_UNIFORM_EXCEPTION_RE.findall(text))
    exception_uniformity = min(0.08, exception_matches / max(len(methods), 1) * 0.04)

    score = symmetry_score + crud_bonus + exception_uniformity
    return min(1.0, max(0.0, score))


# ── Magic number discipline ────────────────────────────────────────────────────

# Numbers that are NOT magic (safe / conventional values)
_SAFE_NUMBERS = frozenset({
    -1, 0, 1, 2, 3, 4, 5, 8, 10, 16, 32, 64, 100, 200, 201, 204,
    400, 401, 403, 404, 422, 500, 502, 503, 1000, 1024,
})

_PORT_MIN, _PORT_MAX = 1024, 65535
_YEAR_MIN, _YEAR_MAX = 1900, 2100

# Regex for numeric literals appearing in code expressions (not in comments/strings ideally)
_NUMERIC_LITERAL_RE = re.compile(
    r"(?<!['\"])"           # not immediately after a quote char
    r"\b(-?\d+(?:\.\d+)?)\b"
    r"(?!['\"])",           # not immediately before a quote char
    re.MULTILINE,
)

# Comment lines to skip
_COMMENT_LINE_RE = re.compile(r"^\s*(?://|#|/\*|\*)", re.MULTILINE)


def magic_number_discipline(text: str, lang: str) -> float:
    """
    Measure the use of unnamed numeric literals (magic numbers).

    High discipline (few magic numbers) suggests AI-generated or senior-authored
    code where constants are extracted. Low discipline (many magic numbers)
    is a human-like signal.

    The returned value represents how AI-like the file looks on this signal:
      - Return value closer to 1.0 = disciplined (AI-like or senior dev)
      - Return value closer to 0.0 = many magic numbers (human-like)

    Safe values (-1, 0, 1, 2, HTTP codes, port numbers, years) are excluded.

    Args:
        text: Raw source file text.
        lang: Language string (unused, reserved for future language-specific rules).

    Returns:
        Float in [0.0, 1.0].
    """
    lines = text.splitlines()
    total_lines = max(len(lines), 1)

    # Strip comment lines to reduce false positives
    non_comment_text = "\n".join(
        line for line in lines
        if not _COMMENT_LINE_RE.match(line)
    )

    all_literals = _NUMERIC_LITERAL_RE.findall(non_comment_text)

    unsafe_count = 0
    for lit in all_literals:
        try:
            val = float(lit)
        except ValueError:
            continue
        int_val = int(val) if val == int(val) else None

        if int_val is not None and int_val in _SAFE_NUMBERS:
            continue
        if int_val is not None and _PORT_MIN <= int_val <= _PORT_MAX:
            continue
        if int_val is not None and _YEAR_MIN <= int_val <= _YEAR_MAX:
            continue
        unsafe_count += 1

    # Normalise to lines (roughly 1 magic number per 10 lines is neutral)
    magic_ratio = unsafe_count / max(total_lines / 10, 1)

    if magic_ratio == 0:
        return 0.65   # no magic numbers at all — very clean (slightly AI-like)
    if magic_ratio < 0.5:
        return 0.70   # few magic numbers — disciplined
    if magic_ratio < 1.0:
        return 0.50   # moderate — borderline
    if magic_ratio < 3.0:
        return 0.30   # many magic numbers — human-like
    return 0.10       # very many magic numbers — strongly human-like


# ── Name-body coherence ────────────────────────────────────────────────────────

_GENERIC_NAMES = frozenset({
    "process", "handle", "execute", "doStuff", "run", "compute",
    "doIt", "doWork", "go", "start", "perform", "call", "invoke",
    "logic", "stuff", "action", "operation", "task",
})

# Split camelCase and snake_case names into tokens
_SPLIT_CAMEL_RE = re.compile(r"[A-Z][a-z]+|[a-z]+|[A-Z]+(?=[A-Z]|$)")
_SPLIT_SNAKE_RE = re.compile(r"[a-z_][a-z_]*")


def _tokenize_name(name: str) -> frozenset:
    """Split a function name into lowercase tokens."""
    camel_tokens = {t.lower() for t in _SPLIT_CAMEL_RE.findall(name)}
    snake_tokens = {t.strip("_").lower() for t in name.split("_") if t.strip("_")}
    return frozenset(camel_tokens | snake_tokens) - {"", "get", "set", "is", "has", "do"}


def _tokenize_body(body_lines: List[str], max_lines: int = 10) -> frozenset:
    """Extract word tokens from the first N lines of a method body."""
    text = " ".join(body_lines[:max_lines])
    tokens = re.findall(r"\b[a-z][a-zA-Z_]{2,}\b", text)
    return frozenset(t.lower() for t in tokens)


def _jaccard(a: frozenset, b: frozenset) -> float:
    """Jaccard similarity between two sets."""
    if not a and not b:
        return 0.5
    intersection = len(a & b)
    union = len(a | b)
    return intersection / union if union > 0 else 0.0


def name_body_coherence(text: str, lang: str) -> float:
    """
    Measure the alignment between function/method names and their implementations.

    High coherence (name tokens appear in body) is associated with descriptive,
    AI-like naming where names accurately document what the code does.
    Low coherence (generic names, mismatched bodies) is a human legacy signal.

    Args:
        text: Raw source file text.
        lang: Language string.

    Returns:
        Float in [0.0, 1.0].
        Returns 0.40 (neutral) if fewer than 2 methods are found.
    """
    if lang == "Python":
        methods = _extract_python_methods(text)
    else:
        methods = _extract_java_methods(text)

    if len(methods) < 2:
        return 0.40  # insufficient data

    coherence_scores: List[float] = []
    generic_count = 0

    for name, body in methods:
        name_tokens = _tokenize_name(name)

        # Check for generic names
        name_lower = name.lower()
        if name_lower in _GENERIC_NAMES or any(g in name_lower for g in _GENERIC_NAMES):
            generic_count += 1
            coherence_scores.append(0.20)  # generic name → low coherence
            continue

        if not body:
            coherence_scores.append(0.35)
            continue

        body_tokens = _tokenize_body(body)
        jac = _jaccard(name_tokens, body_tokens)
        coherence_scores.append(jac)

    if not coherence_scores:
        return 0.40

    mean_coherence = sum(coherence_scores) / len(coherence_scores)
    generic_penalty = generic_count / max(len(methods), 1) * 0.10

    # Scale to [0.0, 1.0]
    # Jaccard around 0.2–0.3 = normal, 0.5+ = high coherence
    scaled = min(1.0, mean_coherence * 1.8) - generic_penalty
    return min(1.0, max(0.0, scaled))


# ── Aggregate signal computation ───────────────────────────────────────────────

def compute_scaffold_signals(text: str, lang: str) -> Dict[str, float]:
    """
    Compute all scaffold-related signals for a source file.

    Args:
        text: Raw source file text.
        lang: Language string (e.g. "Python", "Java", "Kotlin").

    Returns:
        Dict with keys:
          - ``scaffold_completeness``:   uniform scaffold structure signal [0, 1]
          - ``magic_number_discipline``: low magic numbers = AI-like [0, 1]
          - ``name_body_coherence``:     names match body = AI-like [0, 1]
    """
    return {
        "scaffold_completeness": scaffold_completeness(text, lang),
        "magic_number_discipline": magic_number_discipline(text, lang),
        "name_body_coherence": name_body_coherence(text, lang),
    }
