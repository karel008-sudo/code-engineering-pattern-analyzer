"""
analyzers/test_quality.py — Test quality and semantic usefulness signals.

Analyzes test files for patterns associated with AI-generated or low-quality tests:
  - Shallow assertions (assertNotNull, assertTrue(x != null))
  - Excessive mocking (more mocks than assertions)
  - Generic test fixtures (John Doe, test@example.com, dummy data)
  - Repetitive test structure (all tests follow identical arrange-act-assert without variation)
  - Missing edge cases (only happy-path tests)
  - Mock abuse (verifying interactions without state assertions)

Also provides:
  - assertion_quality: how specific are the assertions?
  - mock_abuse: are mocks overused?
  - fixture_realism: how realistic are test data values?

All signals return float [0.0, 1.0] where 1.0 = AI-like/low-quality test pattern.

⚠ Lower test quality scores indicate test files that may warrant review,
  but do NOT prove AI generation. Senior developers also write shallow tests.
"""
from __future__ import annotations

import re
from collections import Counter
from typing import List


# ── Assertion quality ─────────────────────────────────────────────────────────

_SHALLOW_ASSERTIONS = re.compile(
    r"""(?x)
    (?:
        assert(?:NotNull|IsNotNone|IsNone|IsTrue|IsFalse|IsNotEmpty)\s*\(|
        assert\s+\w+\s+is\s+not\s+None\s*$|          # assert x is not None (trivial)
        assert\s+\w+\s*!=\s*None\s*$|                 # assert x != None
        assert\s+(?:True|False)\s*\(|
        assert\s+len\s*\(\w+\)\s*>[=]\s*0\s*$|       # assert len(x) > 0
        assertTrue\s*\(\s*\w+\s*!=\s*null\s*\)|      # JUnit
        assertNotNull\s*\(\s*(?:result|response|actual|output|data)\s*\)|
        assertFalse\s*\(\s*\w+\.isEmpty\s*\(\s*\)\s*\)  # assertFalse(list.isEmpty())
    )
    """,
    re.M,
)

_STRONG_ASSERTIONS = re.compile(
    r"""(?x)
    (?:
        assertEquals\s*\(\s*(?!null|true|false)\w|   # assertEquals with actual value
        assertThat\s*\([^)]+\)\s*\.(?:isEqual|contains|matches|satisfies)|
        assert\s+\w+\s*==\s*(?!''.|\"\")[\w.]+\s*$| # assert x == specific_value (Python)
        assert\s+\w+\s+==\s+\{|                       # dict comparison
        assert\s+\w+\s+==\s+\[|                       # list comparison
        assertRaises\s*\(|                              # checking exception type
        pytest\.raises\s*\(|
        with\s+self\.assertRaises\s*\(|
        assertThrows\s*\(|
        \.isEqualTo\s*\(|
        \.containsExactly\s*\(|
        \.hasSize\s*\(|
        \.isInstanceOf\s*\(
    )
    """,
    re.M,
)


def test_assertion_quality(text: str, lang: str) -> float:
    """
    Measure assertion quality in test files.
    Low quality (many shallow assertions) = AI-like test pattern.
    Returns 0.0 (strong assertions) to 1.0 (shallow/trivial assertions).
    """
    shallow = len(_SHALLOW_ASSERTIONS.findall(text))
    strong  = len(_STRONG_ASSERTIONS.findall(text))
    total   = shallow + strong

    if total == 0:
        return 0.40  # no assertions found — uncertain

    shallow_ratio = shallow / total
    if shallow_ratio > 0.75:
        return 0.80
    if shallow_ratio > 0.50:
        return 0.60
    if shallow_ratio > 0.30:
        return 0.40
    return 0.15


# ── Mock abuse detection ──────────────────────────────────────────────────────

# Java/Mockito
_MOCK_SETUP_JAVA = re.compile(
    r"Mockito\.mock\s*\(|@Mock\b|when\s*\([^)]+\)\.thenReturn|"
    r"doReturn\s*\(|\.mock\s*\(|mock\s*\([A-Z]\w+\.class\)",
)
_VERIFY_JAVA = re.compile(r"verify\s*\([^)]+\)")
_ASSERT_JAVA = re.compile(r"assert(?:Equals|That|True|False|NotNull|Null|Same|Throws)\s*\(")

# Python/pytest
_MOCK_SETUP_PY = re.compile(
    r"MagicMock\s*\(|Mock\s*\(|patch\s*\(|mocker\.(?:patch|Mock)|"
    r"mock\.patch\s*\(|@patch\s*\(",
)
_ASSERT_PY = re.compile(r"assert\s+|assert_(?:called|any_call|has_calls)")


def test_mock_abuse(text: str, lang: str) -> float:
    """
    Detect excessive mocking relative to assertions.
    High mock-to-assertion ratio with heavy verify usage = AI-like test pattern.
    """
    if lang in ("Java", "Kotlin"):
        mock_count   = len(_MOCK_SETUP_JAVA.findall(text))
        verify_count = len(_VERIFY_JAVA.findall(text))
        assert_count = len(_ASSERT_JAVA.findall(text))
    else:
        mock_count   = len(_MOCK_SETUP_PY.findall(text))
        verify_count = len(re.findall(r"assert_called|assert_any_call|assert_has_calls", text))
        assert_count = len(_ASSERT_PY.findall(text))

    total = mock_count + assert_count
    if total == 0:
        return 0.30

    mock_ratio = mock_count / max(total, 1)
    verify_ratio = verify_count / max(mock_count + 1, 1)

    score = 0.0
    if mock_ratio > 0.6:
        score += 0.40
    elif mock_ratio > 0.4:
        score += 0.25
    if verify_ratio > 0.5:
        score += 0.20   # many verify calls = interaction testing, not state
    if mock_count > 5 and assert_count < mock_count:
        score += 0.20

    return round(min(score, 0.85), 4)


# ── Fixture realism ───────────────────────────────────────────────────────────

_GENERIC_TEST_DATA = re.compile(
    r"""(?x)
    ['"](
        [Jj]ohn\s*[Dd]oe|[Jj]ane\s*[Dd]oe|
        test@(?:example|test|domain)\.(?:com|org|net)|
        user@(?:example|test)\.com|
        admin@test\.com|
        [Ss]ample\s*(?:[Uu]ser|[Dd]ata|[Nn]ame|[Vv]alue)|
        [Dd]ummy\s*(?:[Uu]ser|[Dd]ata|[Nn]ame|[Vv]alue)|
        [Ff]ake\s*(?:[Uu]ser|[Dd]ata|[Nn]ame)|
        (?:first|last|full)[-_]?name|
        (?:test|sample|dummy|mock|fake)[-_]?\d+|
        123456(?:789|78)|
        0{6,}1|
        \+1[-\s]?\(?555\)?[-\s]?\d{4}
    )['"]
    """,
    re.I,
)


def test_fixture_realism(text: str, lang: str) -> float:
    """
    Detect generic, unrealistic test fixtures.
    AI-generated tests often use placeholder values (John Doe, test@example.com)
    rather than domain-relevant realistic test data.
    """
    lines = max(text.count("\n") + 1, 1)
    generic_count = len(_GENERIC_TEST_DATA.findall(text))

    if generic_count == 0:
        return 0.10

    density = generic_count / (lines / 20.0)
    if density >= 3:
        return 0.80
    if density >= 1.5:
        return 0.60
    if density >= 0.5:
        return 0.40
    return 0.25


# ── Structural uniformity in test methods ─────────────────────────────────────

_TEST_METHOD_JAVA = re.compile(r"@Test\b[^{]*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}", re.S)
_TEST_METHOD_PY   = re.compile(r"def\s+test_\w+\s*\([^)]*\):\s*\n((?:[ \t]+[^\n]*\n)*)", re.M)


def _extract_test_bodies(text: str, lang: str) -> List[str]:
    if lang in ("Java", "Kotlin"):
        return _TEST_METHOD_JAVA.findall(text)
    return _TEST_METHOD_PY.findall(text)


def test_structural_uniformity(text: str, lang: str) -> float:
    """
    Detect structural uniformity across test methods.
    AI-generated tests often follow identical patterns with low variation.
    """
    bodies = _extract_test_bodies(text, lang)
    if len(bodies) < 3:
        return 0.30

    # Measure line count variance across test bodies
    lengths = [len(b.splitlines()) for b in bodies]
    if not lengths:
        return 0.30

    mean = sum(lengths) / len(lengths)
    if mean == 0:
        return 0.30

    variance = sum((l - mean) ** 2 for l in lengths) / len(lengths)
    cv = (variance ** 0.5) / max(mean, 1)

    # Low CV = very uniform test structure = AI-like
    if cv < 0.15:
        return 0.75
    if cv < 0.30:
        return 0.55
    if cv < 0.50:
        return 0.35
    return 0.15


# ── Happy-path only detection ─────────────────────────────────────────────────

_EDGE_CASE_INDICATORS = re.compile(
    r"""(?x)
    (?:
        (?:empty|null|none|zero|negative|invalid|illegal|boundary|
           overflow|underflow|missing|duplicate|special|unicode|
           concurrent|race|timeout|large|max|min|edge)\w*\s+(?:case|input|value|test)|
        assertThrows\s*\(|pytest\.raises\s*\(|self\.assertRaises\s*\(|
        @Test\s*\(\s*expected\s*=|
        \bwith\s+self\.assertRaises\s*\(|
        null(?:able|Pointer|Argument)\w*|
        boundary|
        corner\s*case|
        negative\s*(?:case|test|path|scenario)
    )
    """,
    re.I,
)


def test_edge_case_coverage(text: str, lang: str) -> float:
    """
    Estimate edge case coverage. Absence of edge case indicators in a
    test file with multiple tests is an AI-like pattern (happy-path only).
    Returns 0.0 = good coverage, 1.0 = likely happy-path only.
    """
    test_count = len(re.findall(r"@Test\b|def\s+test_\w+\s*\(", text))
    if test_count < 3:
        return 0.30  # not enough tests to judge

    edge_indicators = len(_EDGE_CASE_INDICATORS.findall(text))
    ratio = edge_indicators / test_count

    if ratio >= 0.30:
        return 0.10  # good edge case coverage
    if ratio >= 0.15:
        return 0.30
    if ratio >= 0.05:
        return 0.55
    return 0.75  # no edge cases = high AI-like signal


# ── Main dispatcher ───────────────────────────────────────────────────────────

def compute_test_quality_signals(text: str, lang: str) -> dict:
    """
    Compute all test quality signals for a test file.
    Returns dict of signal_key → float [0.0, 1.0].
    """
    return {
        "test_assertion_quality": test_assertion_quality(text, lang),
        "test_mock_abuse":        test_mock_abuse(text, lang),
        "test_fixture_realism":   test_fixture_realism(text, lang),
    }
