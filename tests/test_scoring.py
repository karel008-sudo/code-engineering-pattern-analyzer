"""
tests/test_scoring.py — Tests for the scoring model: raw vs adjusted scores,
confidence, risk, classification, and FileAnalysis integrity.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pathlib import Path
from ai_pattern_analyzer.scoring.model import score_file, THRESH_AI_HIGH, MIN_CONFIDENCE
from ai_pattern_analyzer.domain import FileCategory, FrameworkContext
from ai_pattern_analyzer.scoring.adjusted import (
    apply_category_adjustment,
    compute_risk_score,
    build_score_breakdown,
)


# ── score_file integration ────────────────────────────────────────────────────

def test_score_file_returns_file_analysis():
    result = score_file(
        path=Path("test.py"),
        language="Python",
        kind="production",
        lines=50,
        signals={"type_annotations": 0.85, "comment_density": 0.80},
        category=FileCategory.PRODUCTION_LOGIC,
    )
    assert result is not None
    assert 0.0 <= result.ai_likelihood <= 1.0
    assert 0.0 <= result.adjusted_score <= 1.0
    assert 0.0 <= result.risk_score <= 1.0
    assert 0.0 <= result.confidence <= 1.0
    assert result.classification in ("AI-like", "human-like", "mixed", "uncertain")

def test_score_file_high_signals_gives_ai_like():
    """All signals at 0.9 should yield AI-like classification."""
    signals = {k: 0.90 for k in ["type_annotations", "comment_density", "docstring_quality",
                                   "exception_style", "log_quality"]}
    result = score_file(
        path=Path("service.py"),
        language="Python",
        kind="production",
        lines=100,
        signals=signals,
        category=FileCategory.PRODUCTION_LOGIC,
    )
    assert result.ai_likelihood >= 0.60
    assert result.adjusted_score >= 0.40

def test_score_file_low_signals_gives_human_like():
    """All signals at 0.10 should yield human-like or uncertain classification."""
    signals = {k: 0.10 for k in ["type_annotations", "comment_density", "docstring_quality",
                                   "exception_style", "stream_usage"]}
    result = score_file(
        path=Path("service.py"),
        language="Python",
        kind="production",
        lines=100,
        signals=signals,
        category=FileCategory.PRODUCTION_LOGIC,
    )
    assert result.ai_likelihood <= 0.45

def test_dto_category_reduces_adjusted_score():
    """DTO category should reduce adjusted score vs production logic."""
    signals = {"type_annotations": 0.85, "docstring_quality": 0.70, "comment_density": 0.60}

    prod = score_file(
        path=Path("service.py"), language="Python", kind="production", lines=60,
        signals=signals, category=FileCategory.PRODUCTION_LOGIC,
    )
    dto = score_file(
        path=Path("dto.py"), language="Python", kind="production", lines=60,
        signals=signals, category=FileCategory.DTO_MAPPER,
    )
    assert dto.adjusted_score < prod.adjusted_score

def test_generated_category_zero_risk():
    """Generated files should have near-zero risk score."""
    result = score_file(
        path=Path("Generated.java"), language="Java", kind="production", lines=200,
        signals={"type_annotations": 0.9, "comment_density": 0.9},
        category=FileCategory.GENERATED,
    )
    assert result.risk_score == 0.0

def test_framework_context_reduces_adjusted():
    """MapStruct mapper context should reduce adjusted score."""
    signals = {"type_annotations": 0.80, "comment_density": 0.70, "docstring_quality": 0.75}
    ctx = FrameworkContext(
        detected_frameworks=["mapstruct"],
        is_mapstruct_mapper=True,
        boilerplate_score=0.80,
    )
    result = score_file(
        path=Path("OrderMapper.java"), language="Java", kind="production", lines=50,
        signals=signals, category=FileCategory.DTO_MAPPER,
        framework_ctx=ctx,
    )
    # adjusted should be substantially less than ai_likelihood (raw)
    assert result.adjusted_score < result.ai_likelihood

def test_score_file_has_findings():
    """Score should produce findings for high signals."""
    signals = {"type_annotations": 0.90, "comment_density": 0.85, "docstring_quality": 0.80}
    result = score_file(
        path=Path("service.py"), language="Python", kind="production", lines=100,
        signals=signals, category=FileCategory.PRODUCTION_LOGIC,
    )
    assert len(result.findings) > 0

def test_score_file_findings_have_evidence():
    signals = {"docstring_quality": 0.85, "stream_usage": 0.80}
    result = score_file(
        path=Path("service.java"), language="Java", kind="production", lines=100,
        signals=signals, category=FileCategory.PRODUCTION_LOGIC,
    )
    for finding in result.findings:
        assert finding.rule_id
        assert finding.description
        assert 0.0 <= finding.confidence <= 1.0
        assert finding.severity in ("info", "low", "moderate", "high")

def test_score_breakdown_sum():
    """adjusted_score = raw_score * adjustments (not sum)."""
    signals = {"type_annotations": 0.80, "comment_density": 0.75}
    result = score_file(
        path=Path("x.py"), language="Python", kind="production", lines=100,
        signals=signals, category=FileCategory.DTO_MAPPER,
    )
    assert result.score_breakdown is not None
    assert result.score_breakdown.adjusted_score == result.adjusted_score


# ── apply_category_adjustment ─────────────────────────────────────────────────

def test_category_adjustment_production_no_change():
    adjusted = apply_category_adjustment(0.50, FileCategory.PRODUCTION_LOGIC)
    assert adjusted == 0.50  # factor = 1.0

def test_category_adjustment_dto_reduced():
    adjusted = apply_category_adjustment(0.60, FileCategory.DTO_MAPPER)
    assert adjusted < 0.60  # factor < 1.0

def test_category_adjustment_generated_minimal():
    adjusted = apply_category_adjustment(0.80, FileCategory.GENERATED)
    assert adjusted <= 0.20  # factor = 0.20

def test_category_adjustment_bounded():
    for cat in FileCategory:
        val = apply_category_adjustment(0.70, cat)
        assert 0.0 <= val <= 1.0


# ── compute_risk_score ────────────────────────────────────────────────────────

def test_risk_score_generated_zero():
    risk = compute_risk_score(0.80, 0.90, FileCategory.GENERATED)
    assert risk == 0.0

def test_risk_score_vendor_zero():
    risk = compute_risk_score(0.80, 0.90, FileCategory.VENDOR)
    assert risk == 0.0

def test_risk_score_critical_path_higher():
    normal = compute_risk_score(0.60, 0.80, FileCategory.PRODUCTION_LOGIC)
    critical = compute_risk_score(0.60, 0.80, FileCategory.PRODUCTION_LOGIC, is_critical_path=True)
    assert critical > normal

def test_risk_score_bounded():
    risk = compute_risk_score(1.0, 1.0, FileCategory.PRODUCTION_LOGIC, is_critical_path=True)
    assert 0.0 <= risk <= 1.0

def test_risk_dto_lower_than_production():
    dto_risk  = compute_risk_score(0.60, 0.80, FileCategory.DTO_MAPPER)
    prod_risk = compute_risk_score(0.60, 0.80, FileCategory.PRODUCTION_LOGIC)
    assert dto_risk < prod_risk


# ── deterministic output ──────────────────────────────────────────────────────

def test_same_input_same_output():
    """Score must be deterministic."""
    signals = {"type_annotations": 0.75, "comment_density": 0.60, "docstring_quality": 0.70}
    r1 = score_file(Path("f.py"), "Python", "production", 80, signals,
                    FileCategory.PRODUCTION_LOGIC)
    r2 = score_file(Path("f.py"), "Python", "production", 80, signals,
                    FileCategory.PRODUCTION_LOGIC)
    assert r1.ai_likelihood == r2.ai_likelihood
    assert r1.adjusted_score == r2.adjusted_score
    assert r1.risk_score == r2.risk_score


if __name__ == "__main__":
    import traceback
    tests = [v for k, v in globals().items() if k.startswith("test_") and callable(v)]
    passed = failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"FAIL {t.__name__}: {e}")
            traceback.print_exc()
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
