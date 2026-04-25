"""
analyzers/kotlin.py — Kotlin-native heuristic signals.

Key design decisions:
  - Kotlin data classes are IDIOMATIC, not AI-specific. Do NOT increase AI score.
  - Coroutine usage is modern Kotlin style, treat as contextual.
  - Null-safety operators are correct Kotlin idioms.
  - Android framework patterns are framework boilerplate, not AI-generated.
  - Only flag patterns that are truly unusual in Kotlin context.

All signals return float in [0.0, 1.0] where:
  - Values towards 1.0 indicate AI-like patterns (used consistently)
  - Values towards 0.0 indicate human-like or idiomatic Kotlin patterns
  - For most Kotlin signals the "AI-like" interpretation is very weak (0.25–0.55)
    because the language itself encourages the patterns AI models mimic.

IMPORTANT: These signals are supporting evidence only. Kotlin idiomatic code
will naturally score in the 0.25–0.55 range on most signals here.
"""
from __future__ import annotations

import re
from typing import Dict


# ── Kotlin syntax markers ──────────────────────────────────────────────────────

_KOTLIN_MARKERS_RE = re.compile(
    r"\bfun\s+\w+|val\s+\w+|var\s+\w+|data\s+class\s+\w+|"
    r"object\s+\w+|companion\s+object|import\s+kotlin\.|"
    r":\s*(?:String|Int|Long|Boolean|Double|Float|List|Map|Set)\??",
    re.MULTILINE,
)


def is_kotlin_file(text: str) -> bool:
    """
    Return True if the text looks like Kotlin source code.

    Uses a set of Kotlin syntax markers: function declarations, val/var,
    data classes, companion objects, and typed imports.

    Args:
        text: Raw source file text.

    Returns:
        True if at least 2 distinct Kotlin markers are found.
    """
    matches = _KOTLIN_MARKERS_RE.findall(text)
    return len(matches) >= 2


# ── Data class / sealed class signal ──────────────────────────────────────────

_DATA_CLASS_RE = re.compile(
    r"\b(?:data|sealed|value|enum)\s+class\s+\w+", re.MULTILINE
)
_OBJECT_RE = re.compile(r"\bobject\s+\w+|\bcompanion\s+object\b", re.MULTILINE)
_CLASS_BODY_LINES_RE = re.compile(r"^\s*(?:val|var)\s+\w+\s*:", re.MULTILINE)


def kotlin_data_class_signal(text: str) -> float:
    """
    Signal for Kotlin data class, sealed class, value class, enum class,
    object, and companion object usage.

    These constructs are IDIOMATIC Kotlin — their presence does NOT indicate
    AI generation. The signal deliberately returns LOW values (0.25–0.40)
    to avoid penalising idiomatic code.

    Only returns a slightly elevated value (up to 0.40) when data classes
    appear in unusually symmetric, high-density patterns suggesting a
    scaffolded data layer.

    Args:
        text: Raw source file text.

    Returns:
        Float in [0.25, 0.40] range. Never exceeds 0.40.
    """
    lines = text.splitlines()
    total_lines = max(len(lines), 1)

    data_class_count = len(_DATA_CLASS_RE.findall(text))
    object_count = len(_OBJECT_RE.findall(text))
    property_count = len(_CLASS_BODY_LINES_RE.findall(text))

    # Density of data classes relative to file size
    data_class_density = data_class_count / (total_lines / 20.0 + 1)

    # Base signal: idiomatic → low
    base = 0.25

    # Slightly elevated if very dense data-class file (scaffolded DTO layer)
    if data_class_count >= 3 and data_class_density > 1.5:
        base += 0.08

    # Symmetric property count per data class → slight elevation
    if data_class_count > 0 and property_count / max(data_class_count, 1) >= 5:
        base += 0.07

    return min(0.40, max(0.25, base))


# ── Coroutine usage signal ─────────────────────────────────────────────────────

_COROUTINE_KEYWORDS_RE = re.compile(
    r"\bsuspend\s+fun\b|"
    r"\bFlow\s*<|"
    r"\bStateFlow\s*<|"
    r"\bSharedFlow\s*<|"
    r"\bviewModelScope\b|"
    r"\blifecycleScope\b|"
    r"\bCoroutineScope\b|"
    r"\blaunch\s*\{|"
    r"\basync\s*\{|"
    r"\bwithContext\s*\(|"
    r"\bDispatchers\.\w+|"
    r"\bcollect\s*\{|"
    r"\bawait\(\)",
    re.MULTILINE,
)


def kotlin_coroutine_usage(text: str) -> float:
    """
    Signal for Kotlin coroutine and Flow usage.

    Modern coroutine usage is idiomatic Kotlin — not AI-specific. Returns
    a contextual signal in [0.35, 0.55] regardless of usage density.

    High coroutine density may slightly elevate the signal toward 0.55 if the
    file looks like a scaffolded coroutine-heavy service, but the signal is
    deliberately capped to remain non-decisive.

    Args:
        text: Raw source file text.

    Returns:
        Float in [0.35, 0.55]. Returns 0.40 (baseline) if no coroutines found.
    """
    matches = _COROUTINE_KEYWORDS_RE.findall(text)
    if not matches:
        return 0.40  # baseline neutral — no coroutines present

    lines = text.splitlines()
    total_lines = max(len(lines), 1)

    coroutine_density = len(matches) / (total_lines / 10.0 + 1)

    # Map density to [0.35, 0.55]
    if coroutine_density >= 2.0:
        return 0.55   # very dense coroutine file — slightly AI-like scaffold
    if coroutine_density >= 1.0:
        return 0.50
    if coroutine_density >= 0.5:
        return 0.45
    return 0.35       # sparse coroutine usage — idiomatic, low signal


# ── Null-safety signal ─────────────────────────────────────────────────────────

_NULLABLE_TYPE_RE = re.compile(r"\w+\?(?:\s|,|\)|\])", re.MULTILINE)
_FORCE_NONNULL_RE = re.compile(r"!!")
_ELVIS_RE = re.compile(r"\?:")
_SAFE_CALL_RE = re.compile(r"\?\.")
_REQUIRE_NOT_NULL_RE = re.compile(r"\b(?:requireNotNull|checkNotNull)\s*\(")


def kotlin_nullability(text: str) -> float:
    """
    Signal for Kotlin null-safety usage patterns.

    Correct nullability usage is idiomatic Kotlin. The signal is in [0.30, 0.50]:
    - Very few null-safety constructs → slightly elevated (missing idioms)
    - Uniform null-safety usage → neutral (idiomatic)
    - Overuse of !! (force non-null) → slightly lowered (human workaround pattern)

    Args:
        text: Raw source file text.

    Returns:
        Float in [0.30, 0.50].
    """
    lines = text.splitlines()
    total_lines = max(len(lines), 1)

    nullable_types = len(_NULLABLE_TYPE_RE.findall(text))
    force_nonnull = len(_FORCE_NONNULL_RE.findall(text))
    elvis = len(_ELVIS_RE.findall(text))
    safe_calls = len(_SAFE_CALL_RE.findall(text))
    require_not_null = len(_REQUIRE_NOT_NULL_RE.findall(text))

    null_safety_total = nullable_types + elvis + safe_calls + require_not_null

    # Force non-null (!!) is a human workaround — lowers the signal
    force_ratio = force_nonnull / max(null_safety_total, 1)

    # Base signal: idiomatic null safety → 0.40
    base = 0.40

    # Adjust down for !! overuse (human pattern)
    if force_ratio >= 0.40:
        base -= 0.10
    elif force_ratio >= 0.20:
        base -= 0.05

    # Very uniform null-safety (many ?. and ?: with no !!) → slightly AI-like
    if null_safety_total > 5 and force_nonnull == 0:
        base += 0.05

    # Very sparse null-safety in a kotlin file → slightly elevated (inconsistent)
    if null_safety_total < 2 and total_lines > 30:
        base += 0.05

    return min(0.50, max(0.30, base))


# ── Android framework patterns signal ─────────────────────────────────────────

_ANDROID_RE = re.compile(
    r"\b(?:Activity|Fragment|ViewModel|LiveData|MutableLiveData|"
    r"Composable|HiltViewModel|Inject|AndroidEntryPoint|"
    r"Room|RoomDatabase|Dao|Entity|Query|Database|"
    r"Retrofit|OkHttp|Interceptor|ApiService|"
    r"RecyclerView|ViewHolder|Adapter|"
    r"Bundle|Intent|Context|Application|"
    r"setContentView|onCreate|onStart|onResume|onPause|onStop|onDestroy|"
    r"NavController|NavGraph|NavArgument)\b",
    re.MULTILINE,
)


def kotlin_android_patterns(text: str) -> float:
    """
    Signal for Android framework patterns (Activity, Fragment, ViewModel, etc.).

    Android framework code is boilerplate — the patterns are driven by the
    framework contract, not AI generation. Returns LOW values [0.20, 0.35]
    to reduce the AI score for Android code.

    Args:
        text: Raw source file text.

    Returns:
        Float in [0.20, 0.35]. Higher density → lower score (more boilerplate).
    """
    lines = text.splitlines()
    total_lines = max(len(lines), 1)

    android_matches = len(_ANDROID_RE.findall(text))
    if android_matches == 0:
        return 0.40  # no Android patterns → neutral (not Android-specific)

    android_density = android_matches / (total_lines / 10.0 + 1)

    # More Android framework patterns → lower AI signal (it's boilerplate)
    if android_density >= 2.0:
        return 0.20   # very dense Android boilerplate
    if android_density >= 1.0:
        return 0.25
    if android_density >= 0.5:
        return 0.30
    return 0.35       # sparse Android patterns


# ── Test patterns signal ───────────────────────────────────────────────────────

_KOTLIN_TEST_RE = re.compile(
    r"\b(?:MockK|mockk|every|coEvery|verify|coVerify|"
    r"slot|capture|relaxed|spyk|"
    r"Turbine|test\s*\{|runTest|runBlocking|"
    r"@Test|@BeforeTest|@AfterTest|@ParameterizedTest|"
    r"shouldBe|shouldNotBe|shouldContain|"
    r"assertEquals|assertNotNull|assertThrows|assertTrue)\b",
    re.MULTILINE,
)


def kotlin_test_patterns(text: str) -> float:
    """
    Signal for Kotlin-specific test patterns (MockK, Turbine, runTest, etc.).

    Kotlin test code often follows a prescribed style (given/when/then)
    which can look AI-like or be AI-assisted. Returns moderate signal [0.30, 0.50].

    Args:
        text: Raw source file text.

    Returns:
        Float in [0.30, 0.50].
    """
    lines = text.splitlines()
    total_lines = max(len(lines), 1)

    test_matches = len(_KOTLIN_TEST_RE.findall(text))
    if test_matches == 0:
        return 0.35  # no test patterns → slight default signal

    test_density = test_matches / (total_lines / 10.0 + 1)

    if test_density >= 2.0:
        return 0.50   # very dense test boilerplate — could be AI-scaffolded
    if test_density >= 1.0:
        return 0.45
    if test_density >= 0.5:
        return 0.40
    return 0.30       # sparse test patterns


# ── Aggregate signal computation ───────────────────────────────────────────────

def compute_kotlin_signals(text: str) -> Dict[str, float]:
    """
    Compute all Kotlin-native heuristic signals for a source file.

    All signals are in [0.0, 1.0]. Values around 0.35–0.45 are idiomatic
    Kotlin and should NOT be interpreted as strong AI indicators.

    Args:
        text: Raw Kotlin source file text.

    Returns:
        Dict with keys:
          - ``kotlin_data_class``:   data class / sealed class density signal
          - ``kotlin_coroutines``:   coroutine / Flow usage signal
          - ``kotlin_nullability``:  null-safety usage signal
          - ``kotlin_android``:      Android framework boilerplate signal
          - ``kotlin_tests``:        Kotlin-specific test pattern signal
    """
    return {
        "kotlin_data_class": kotlin_data_class_signal(text),
        "kotlin_coroutines": kotlin_coroutine_usage(text),
        "kotlin_nullability": kotlin_nullability(text),
        "kotlin_android": kotlin_android_patterns(text),
        "kotlin_tests": kotlin_test_patterns(text),
    }
