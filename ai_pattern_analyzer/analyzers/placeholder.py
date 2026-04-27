"""
analyzers/placeholder.py — Placeholder, LLM residue, and generic literal detection.

Detects:
  - Placeholder code (TODO/FIXME without context, pass, NotImplementedError)
  - LLM prompt residue ("Here is", "You can use", "Example usage", etc.)
  - Generic test literals (John Doe, foo, bar, localhost, dummy, sample)
  - Generic log messages (start, end, processing, executing)
  - Comment-code mismatch patterns
  - Resilience theater (retry without backoff, catch-log-continue)

All signals return float [0.0, 1.0] where 1.0 = strong AI-like artifact pattern.

⚠ High placeholder_density alone is NOT an AI signal — it may indicate
  work in progress. Interpret alongside other signals and context.
"""
from __future__ import annotations

import re
from typing import List, Tuple


# ── LLM prompt residue ────────────────────────────────────────────────────────

_PROMPT_RESIDUE_PATTERNS = [
    # Instructional phrases that appear in LLM completions
    (r"(?://|#|\"\"\"|\*)\s*Here is (?:an? |the )?(?:example|implementation|updated|corrected|improved)", 0.8),
    (r"(?://|#|\"\"\"|\*)\s*You can (?:use|call|import|replace|customize|modify|extend)", 0.7),
    (r"(?://|#|\"\"\"|\*)\s*Example usage:", 0.7),
    (r"(?://|#|\"\"\"|\*)\s*[Rr]eplace (?:with|this) (?:your|actual|the real)", 0.8),
    (r"(?://|#|\"\"\"|\*)\s*[Aa]dd your (?:logic|implementation|code|business logic)", 0.8),
    (r"(?://|#|\"\"\"|\*)\s*[Ii]n a real (?:application|scenario|world|implementation)", 0.7),
    (r"(?://|#|\"\"\"|\*)\s*[Ff]or (?:simplicity|brevity|demonstration|illustration)", 0.6),
    (r"(?://|#|\"\"\"|\*)\s*[Nn]ote:?\s+[Tt]his is (?:a|an|just a) (?:placeholder|stub|example|simplified)", 0.8),
    (r"(?://|#)\s*TODO:\s+[Ii]mplement (?:this|the|actual|real|business)", 0.7),
    (r"(?://|#|\*)\s*[Ff]eel free to (?:customize|modify|extend|adjust|change)", 0.6),
    # String literals with LLM artifacts
    (r"['\"]your[-_]?\w+[-_]?(?:api[-_]?key|token|secret|password|endpoint)['\"]", 0.7),
    (r"['\"]change[-_]?me['\"]|['\"]replace[-_]?me['\"]|['\"]todo['\"]", 0.6),
    (r"['\"]your[-_]?\w+[-_]?(?:here|value|input)['\"]", 0.5),
]

_COMPILED_RESIDUE = [(re.compile(p, re.I | re.M), s) for p, s in _PROMPT_RESIDUE_PATTERNS]


def prompt_residue(text: str) -> float:
    """
    Detect LLM prompt residue: instructional comments, placeholder strings,
    and completion artifacts that LLMs often include in generated code.

    Returns AI-like signal [0.0, 1.0].
    """
    if len(text) < 50:
        return 0.30

    max_score = 0.0
    total_score = 0.0
    count = 0

    for pattern, strength in _COMPILED_RESIDUE:
        matches = pattern.findall(text)
        if matches:
            count += len(matches)
            total_score += strength * min(len(matches), 3)
            max_score = max(max_score, strength)

    if count == 0:
        return 0.10

    # Blend max and average to avoid single-pattern domination
    avg_score = min(total_score / max(count, 1), 0.90)
    return round(min(0.30 + max_score * 0.40 + avg_score * 0.30, 0.92), 4)


# ── Placeholder code ──────────────────────────────────────────────────────────

_PLACEHOLDER_CODE_PATTERNS = [
    # Python placeholders
    (r"^\s*pass\s*$", 2),                          # standalone pass
    (r"raise\s+NotImplementedError\s*\(", 2),
    (r"raise\s+NotImplementedError\s*$", 2, re.M),
    # Java placeholders
    (r"throw\s+new\s+UnsupportedOperationException\s*\(\s*\)", 2),
    (r"return\s+(?:null|None|Collections\.emptyList|Optional\.empty)\s*;?\s*//\s*TODO", 3),
    # Generic
    (r"//\s*TODO[:\s]|#\s*TODO[:\s]|\*\s*TODO[:\s]", 1),
    (r"//\s*FIXME[:\s]|#\s*FIXME[:\s]", 1),
    (r"//\s*HACK[:\s]|#\s*HACK[:\s]", 1),
    (r"//\s*PLACEHOLDER|#\s*PLACEHOLDER", 2),
]

_COMPILED_PLACEHOLDER = []
for item in _PLACEHOLDER_CODE_PATTERNS:
    if len(item) == 3:
        pat, weight, flags = item
        _COMPILED_PLACEHOLDER.append((re.compile(pat, flags), weight))
    else:
        pat, weight = item
        _COMPILED_PLACEHOLDER.append((re.compile(pat, re.M), weight))


def placeholder_density(text: str) -> float:
    """
    Detect placeholder code patterns: standalone pass, NotImplementedError,
    UnsupportedOperationException, and TODO/FIXME annotations.

    ⚠ High score means the file may be incomplete or scaffolded.
    It is NOT a reliable standalone AI signal — always check context.
    """
    if len(text) < 30:
        return 0.20

    lines = max(text.count("\n") + 1, 1)
    total_weight = 0

    for pattern, weight in _COMPILED_PLACEHOLDER:
        matches = pattern.findall(text)
        total_weight += len(matches) * weight

    # Normalize by file size
    density = total_weight / (lines / 20.0)
    if density >= 4:
        return 0.85
    if density >= 2:
        return 0.65
    if density >= 1:
        return 0.45
    if total_weight > 0:
        return 0.30
    return 0.10


# ── Generic literal detection ─────────────────────────────────────────────────

_GENERIC_LITERALS = re.compile(
    r"""(?x)
    ['"](
        foo|bar|baz|qux|
        test|example|sample|dummy|placeholder|mock|fake|
        john\.?doe|jane\.?doe|
        test@example\.com|user@example\.com|
        admin@test\.com|
        localhost|127\.0\.0\.1|
        my-service|my-app|my-app-name|
        your-?(?:api-?key|token|secret|endpoint|value)|
        password|changeme|change_me|
        (?:test|sample|dummy|example)[\-_](?:data|value|input|output)|
        (?:some|any)[\-_](?:value|string|data)
    )['"]
    """,
    re.I,
)

_GENERIC_FUNC_NAMES = re.compile(
    r"\b(?:def|function|func)\s+(process|handle|execute|perform|do_stuff|"
    r"helper|utility|util|do_something|run|start|init|setup|teardown)\s*\(",
    re.I,
)


def generic_literal_density(text: str) -> float:
    """
    Detect generic placeholder literals associated with generated or tutorial-style examples.
    Returns AI-like signal [0.0, 1.0].
    """
    lines = max(text.count("\n") + 1, 1)
    literal_count = len(_GENERIC_LITERALS.findall(text))
    func_count    = len(_GENERIC_FUNC_NAMES.findall(text))

    total = literal_count + func_count * 2
    density = total / (lines / 15.0)

    if density >= 3:
        return 0.80
    if density >= 1.5:
        return 0.60
    if density >= 0.5:
        return 0.40
    if total > 0:
        return 0.25
    return 0.10


# ── Generic log messages ──────────────────────────────────────────────────────

_GENERIC_LOG_PATTERNS = re.compile(
    r"""(?x)
    log(?:ger)?\.(?:debug|info|warn|warning|error|critical)\s*\(
    \s*[f]?['"](?:
        [Ss]tarting|[Ss]tart(?:ing)?\s|
        [Ss]topped|[Ss]topping|
        [Cc]ompleted|[Cc]ompletion|
        [Pp]rocessing\s+\w+\.\.\.|
        [Ee]xecuting\s+\w+\.\.\.|
        [Ee]ntering\s+(?:method|function)|
        [Ll]eaving\s+(?:method|function)|
        [Mm]ethod\s+called|
        [Oo]peration\s+(?:started|completed|failed)|
        [Ss]uccess(?:fully)?|
        [Ff]ailed\s+to|
        [Ee]rror\s+occurred|
        [Aa]n\s+error\s+(?:occurred|happened)
    )
    """,
    re.I,
)


def generic_log_quality(text: str) -> float:
    """
    Detect generic, context-free log messages that indicate AI generation.
    "Starting process..." / "Operation completed" patterns provide no debugging value.
    """
    lines = max(text.count("\n") + 1, 1)
    generic_count = len(_GENERIC_LOG_PATTERNS.findall(text))
    density = generic_count / (lines / 20.0)

    if density >= 2:
        return 0.70
    if density >= 1:
        return 0.50
    if generic_count > 0:
        return 0.35
    return 0.15


# ── Comment-code mismatch ─────────────────────────────────────────────────────

_OBVIOUS_COMMENT_PATTERNS = re.compile(
    r"(?://|#|\*)\s*(?:"
    r"[Cc]heck(?:s)?\s+(?:if|whether|that)|"
    r"[Rr]eturn(?:s)?\s+(?:the|a|an)\s+\w+|"
    r"[Ss]et(?:s)?\s+(?:the|a|an)\s+\w+\s+to|"
    r"[Gg]et(?:s)?\s+(?:the|a|an)\s+\w+|"
    r"[Cc]reate(?:s)?\s+(?:a|an|the|new)\s+\w+|"
    r"[Ll]oop(?:s)?\s+(?:over|through)|"
    r"[Ii]terate(?:s)?\s+(?:over|through)|"
    r"[Vv]alidate(?:s)?\s+(?:the|input|that)|"
    r"[Ii]nitialize(?:s)?\s+(?:the|a)\s+\w+|"
    r"[Pp]arse(?:s)?\s+(?:the|a)\s+\w+|"
    r"[Ff]ilter(?:s)?\s+(?:the|a)\s+\w+|"
    r"[Mm]ap(?:s)?\s+(?:the|a|each)\s+\w+"
    r")",
    re.M,
)


def obvious_comment_density(text: str) -> float:
    """
    Detect comments that merely restate what the code obviously does.
    Such over-obvious comments are associated with generated, scaffolded, or
    template-expanded code patterns.
    """
    lines = max(text.count("\n") + 1, 1)
    obvious = len(_OBVIOUS_COMMENT_PATTERNS.findall(text))
    density = obvious / (lines / 15.0)

    if density >= 3:
        return 0.80
    if density >= 1.5:
        return 0.60
    if density >= 0.5:
        return 0.40
    if obvious > 0:
        return 0.25
    return 0.10


# ── Resilience theater ────────────────────────────────────────────────────────

_RESILIENCE_THEATER_PATTERNS = [
    # Catch + log + return empty (swallowing exception with logging)
    (r"catch\s*\([^)]+\)\s*\{[^}]{0,200}log[^}]{0,100}return\s+(?:null|None|Collections\.empty|Optional\.empty|new Array)", 0.7),
    # Python: except + log + return None
    (r"except\s+\w+(?:\s+as\s+\w+)?:\s*\n\s+(?:logger?|logging)\.\w+[^\n]*\n\s+return\s+(?:None|\[\]|\{\}|''|\"\")", 0.7),
    # Retry without backoff (Java)
    (r"for\s*\(\s*int\s+\w+\s*=\s*0\s*;\s*\w+\s*<\s*(?:MAX_RETRIES|maxRetries|retries|3)\s*;\s*\w+\+\+\s*\)\s*\{[^}]{0,300}catch", 0.5),
    # Python retry without sleep
    (r"for\s+\w+\s+in\s+range\s*\(\s*(?:MAX_RETRIES|max_retries|retries|3)\s*\)[^:]*:\s*\n(?!\s*time\.sleep)", 0.4),
    # Empty catch with comment
    (r"catch\s*\([^)]+\)\s*\{\s*//[^\n]*\n\s*\}", 0.6),
]

_COMPILED_RESILIENCE = [(re.compile(p, re.S | re.I), s) for p, s in _RESILIENCE_THEATER_PATTERNS]


def resilience_theater_score(text: str) -> float:
    """
    Detect 'resilience theater': code that appears to handle errors/retries
    but provides no real recovery. Common in AI-generated service code.
    """
    max_score = 0.0
    for pattern, score in _COMPILED_RESILIENCE:
        if pattern.search(text):
            max_score = max(max_score, score)

    return round(max_score, 4) if max_score > 0 else 0.10


# ── Combined placeholder dispatcher ──────────────────────────────────────────

def compute_placeholder_signals(text: str, lang: str) -> dict:
    """
    Compute all placeholder and LLM-residue signals.
    Returns a dict of signal_key → float [0.0, 1.0].
    """
    return {
        "placeholder_density": placeholder_density(text),
        "prompt_residue":      prompt_residue(text),
    }
