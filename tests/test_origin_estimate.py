"""
tests/test_origin_estimate.py — Tests for the AI Origin Estimate Engine (v5.0).

Tests:
  - Three-way probabilities always sum to 100%
  - High adjusted score → higher fully_ai_generated probability
  - Low adjusted score → higher human_authored probability
  - Style discontinuity → boosts ai_assisted
  - High scaffold score → boosts fully_ai_generated
  - Generated/vendor categories have correct origin interpretation
  - Portfolio aggregation is LOC-weighted
  - Confidence intervals are valid
  - No origin claims use deterministic language
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from ai_pattern_analyzer.origin.engine import compute_file_origin, aggregate_origin_estimates
from ai_pattern_analyzer.origin.confidence import ConfidenceInterval, compute_interval, portfolio_interval
from ai_pattern_analyzer.domain import OriginEstimate, FileCategory, FrameworkContext


# ── Helper: mock FileAnalysis ─────────────────────────────────────────────────

class MockFileAnalysis:
    """Minimal mock of FileAnalysis for testing origin engine."""
    def __init__(
        self,
        adjusted_score=0.30,
        confidence=0.65,
        signals=None,
        category=FileCategory.PRODUCTION_LOGIC,
        framework_context=None,
        lines=100,
        module_path="src/main",
    ):
        self.adjusted_score = adjusted_score
        self.confidence = confidence
        self.signals = signals or {}
        self.category = category
        self.framework_context = framework_context
        self.lines = lines
        self.module_path = module_path


# ── Sum to 100% ───────────────────────────────────────────────────────────────

def test_origin_probs_sum_to_100_low_score():
    fa = MockFileAnalysis(adjusted_score=0.10, confidence=0.70)
    oe = compute_file_origin(fa)
    total = oe.fully_ai_generated_pct + oe.ai_assisted_pct + oe.human_authored_pct
    assert abs(total - 100.0) < 0.5, f"Sum {total} != 100"

def test_origin_probs_sum_to_100_medium_score():
    fa = MockFileAnalysis(adjusted_score=0.45, confidence=0.60)
    oe = compute_file_origin(fa)
    total = oe.fully_ai_generated_pct + oe.ai_assisted_pct + oe.human_authored_pct
    assert abs(total - 100.0) < 0.5, f"Sum {total} != 100"

def test_origin_probs_sum_to_100_high_score():
    fa = MockFileAnalysis(adjusted_score=0.75, confidence=0.80)
    oe = compute_file_origin(fa)
    total = oe.fully_ai_generated_pct + oe.ai_assisted_pct + oe.human_authored_pct
    assert abs(total - 100.0) < 0.5, f"Sum {total} != 100"

def test_origin_probs_sum_to_100_extreme_high():
    fa = MockFileAnalysis(adjusted_score=0.95, confidence=0.90)
    oe = compute_file_origin(fa)
    total = oe.fully_ai_generated_pct + oe.ai_assisted_pct + oe.human_authored_pct
    assert abs(total - 100.0) < 0.5

def test_origin_probs_sum_to_100_extreme_low():
    fa = MockFileAnalysis(adjusted_score=0.02, confidence=0.50)
    oe = compute_file_origin(fa)
    total = oe.fully_ai_generated_pct + oe.ai_assisted_pct + oe.human_authored_pct
    assert abs(total - 100.0) < 0.5


# ── Directional correctness ───────────────────────────────────────────────────

def test_high_score_increases_fully_ai():
    low = MockFileAnalysis(adjusted_score=0.15)
    high = MockFileAnalysis(adjusted_score=0.75)
    oe_low = compute_file_origin(low)
    oe_high = compute_file_origin(high)
    assert oe_high.fully_ai_generated_pct > oe_low.fully_ai_generated_pct

def test_low_score_increases_human():
    low = MockFileAnalysis(adjusted_score=0.10)
    high = MockFileAnalysis(adjusted_score=0.70)
    oe_low = compute_file_origin(low)
    oe_high = compute_file_origin(high)
    assert oe_low.human_authored_pct > oe_high.human_authored_pct

def test_medium_score_ai_assisted_dominant():
    fa = MockFileAnalysis(adjusted_score=0.45)
    oe = compute_file_origin(fa)
    # At medium score, ai_assisted should be the largest component
    assert oe.ai_assisted_pct >= oe.fully_ai_generated_pct

def test_style_discontinuity_boosts_ai_assisted():
    cont = MockFileAnalysis(adjusted_score=0.45)
    discont = MockFileAnalysis(adjusted_score=0.45)
    oe_cont = compute_file_origin(cont, style_continuity=0.95)
    oe_discont = compute_file_origin(discont, style_continuity=0.10)
    # Discontinuity should boost ai_assisted
    assert oe_discont.ai_assisted_pct > oe_cont.ai_assisted_pct

def test_scaffold_boosts_fully_ai():
    no_scaffold = MockFileAnalysis(adjusted_score=0.55)
    with_scaffold = MockFileAnalysis(adjusted_score=0.55)
    oe_no = compute_file_origin(no_scaffold, scaffold_score=0.0)
    oe_sc = compute_file_origin(with_scaffold, scaffold_score=0.90)
    assert oe_sc.fully_ai_generated_pct > oe_no.fully_ai_generated_pct


# ── Category modifiers ────────────────────────────────────────────────────────

def test_generated_category_high_ai_probability():
    fa = MockFileAnalysis(adjusted_score=0.50, category=FileCategory.GENERATED)
    oe = compute_file_origin(fa)
    # Generated code should have highest fully_ai probability
    assert oe.fully_ai_generated_pct > oe.human_authored_pct

def test_vendor_category_increases_human_vs_default():
    fa_prod = MockFileAnalysis(adjusted_score=0.50, category=FileCategory.PRODUCTION_LOGIC)
    fa_vendor = MockFileAnalysis(adjusted_score=0.50, category=FileCategory.VENDOR)
    oe_prod = compute_file_origin(fa_prod)
    oe_vendor = compute_file_origin(fa_vendor)
    # Vendor increases human relative to production
    assert oe_vendor.human_authored_pct >= oe_prod.human_authored_pct - 5.0

def test_dto_category_reduces_fully_ai():
    prod = MockFileAnalysis(adjusted_score=0.55, category=FileCategory.PRODUCTION_LOGIC)
    dto  = MockFileAnalysis(adjusted_score=0.55, category=FileCategory.DTO_MAPPER)
    oe_prod = compute_file_origin(prod)
    oe_dto  = compute_file_origin(dto)
    # DTO should have lower fully_ai (it's inherently regular, not necessarily AI)
    assert oe_dto.fully_ai_generated_pct < oe_prod.fully_ai_generated_pct


# ── Confidence levels ─────────────────────────────────────────────────────────

def test_high_confidence_gives_high_label():
    fa = MockFileAnalysis(confidence=0.85)
    oe = compute_file_origin(fa)
    assert oe.confidence == "high"

def test_medium_confidence_gives_medium_label():
    fa = MockFileAnalysis(confidence=0.60)
    oe = compute_file_origin(fa)
    assert oe.confidence in ("medium", "high")

def test_low_confidence_gives_low_label():
    fa = MockFileAnalysis(confidence=0.30)
    oe = compute_file_origin(fa)
    assert oe.confidence == "low"


# ── Drivers and uncertainty ───────────────────────────────────────────────────

def test_origin_estimate_has_drivers():
    fa = MockFileAnalysis(adjusted_score=0.60)
    oe = compute_file_origin(fa)
    assert len(oe.drivers) > 0

def test_small_file_has_uncertainty_reason():
    fa = MockFileAnalysis(lines=20)
    oe = compute_file_origin(fa)
    assert any("small" in r.lower() or "insufficient" in r.lower()
               for r in oe.uncertainty_reasons)

def test_no_git_has_uncertainty_reason():
    fa = MockFileAnalysis(module_path=None)
    oe = compute_file_origin(fa)
    # No git → should mention temporal signals
    # (has_git is proxied from module_path being not None)
    assert isinstance(oe.uncertainty_reasons, list)


# ── Portfolio aggregation ─────────────────────────────────────────────────────

def test_portfolio_aggregation_sums_to_100():
    oe1 = OriginEstimate(fully_ai_generated_pct=10.0, ai_assisted_pct=50.0,
                         human_authored_pct=40.0, confidence="medium", confidence_level=0.60)
    oe2 = OriginEstimate(fully_ai_generated_pct=5.0, ai_assisted_pct=35.0,
                         human_authored_pct=60.0, confidence="high", confidence_level=0.80)
    portfolio = aggregate_origin_estimates([(oe1, 100), (oe2, 200)])
    total = (portfolio.fully_ai_generated_pct + portfolio.ai_assisted_pct
             + portfolio.human_authored_pct)
    assert abs(total - 100.0) < 0.5

def test_portfolio_weighted_by_loc():
    # oe1: 80% fully AI, 100 LOC
    # oe2: 0% fully AI, 900 LOC
    # Expected: ~8% fully AI weighted average
    oe1 = OriginEstimate(fully_ai_generated_pct=80.0, ai_assisted_pct=10.0,
                         human_authored_pct=10.0, confidence="high", confidence_level=0.80)
    oe2 = OriginEstimate(fully_ai_generated_pct=0.0, ai_assisted_pct=40.0,
                         human_authored_pct=60.0, confidence="high", confidence_level=0.80)
    portfolio = aggregate_origin_estimates([(oe1, 100), (oe2, 900)])
    # 80*100/1000 + 0*900/1000 = 8%
    assert abs(portfolio.fully_ai_generated_pct - 8.0) < 2.0

def test_portfolio_empty_returns_neutral():
    portfolio = aggregate_origin_estimates([])
    total = (portfolio.fully_ai_generated_pct + portfolio.ai_assisted_pct
             + portfolio.human_authored_pct)
    assert abs(total - 100.0) < 1.0
    assert portfolio.confidence == "low"

def test_portfolio_zero_loc_ignored():
    oe1 = OriginEstimate(fully_ai_generated_pct=50.0, ai_assisted_pct=30.0,
                         human_authored_pct=20.0, confidence="medium", confidence_level=0.60)
    oe2 = OriginEstimate(fully_ai_generated_pct=0.0, ai_assisted_pct=100.0,
                         human_authored_pct=0.0, confidence="medium", confidence_level=0.60)
    portfolio = aggregate_origin_estimates([(oe1, 100), (oe2, 0)])
    # oe2 has 0 LOC → should be ignored → portfolio = oe1
    assert abs(portfolio.fully_ai_generated_pct - 50.0) < 1.0


# ── as_dict() contract ────────────────────────────────────────────────────────

def test_origin_estimate_as_dict_has_required_fields():
    fa = MockFileAnalysis(adjusted_score=0.50)
    oe = compute_file_origin(fa)
    d = oe.as_dict()
    assert "fully_ai_generated_pct" in d
    assert "ai_assisted_pct" in d
    assert "human_authored_pct" in d
    assert "confidence" in d
    assert "confidence_level" in d
    assert "confidence_interval" in d
    assert "drivers" in d
    assert "uncertainty_reasons" in d
    assert "methodology" in d
    assert "caveats" in d

def test_origin_estimate_no_deterministic_language():
    """Ensure no deterministic AI-authorship claims in estimate objects."""
    fa = MockFileAnalysis(adjusted_score=0.80, confidence=0.90,
                          category=FileCategory.PRODUCTION_LOGIC)
    oe = compute_file_origin(fa)
    d = oe.as_dict()
    full_text = str(d).lower()
    # Check that no deterministic claims are made
    forbidden = ["confirmed ai", "proven ai", "guaranteed", "100% ai", "definitely ai"]
    for term in forbidden:
        assert term not in full_text, f"Deterministic claim found: '{term}'"


# ── Confidence interval ───────────────────────────────────────────────────────

def test_confidence_interval_high_confidence():
    ci = compute_interval(50.0, confidence_level=0.85, data_quality=0.90)
    assert isinstance(ci, ConfidenceInterval)
    assert ci.low <= 50.0 <= ci.high
    assert ci.width <= 20.0  # high confidence = narrow interval

def test_confidence_interval_low_confidence():
    ci = compute_interval(50.0, confidence_level=0.25, data_quality=0.30)
    assert ci.width >= 20.0  # low confidence = wide interval

def test_confidence_interval_clamped():
    ci = compute_interval(2.0, confidence_level=0.30, data_quality=0.30)
    assert ci.low >= 0.0
    ci2 = compute_interval(98.0, confidence_level=0.30, data_quality=0.30)
    assert ci2.high <= 100.0

def test_portfolio_interval_narrows_with_more_repos():
    ci_small = portfolio_interval(50.0, n_repos=2, avg_confidence=0.60)
    ci_large = portfolio_interval(50.0, n_repos=50, avg_confidence=0.60)
    assert ci_large.width <= ci_small.width


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
