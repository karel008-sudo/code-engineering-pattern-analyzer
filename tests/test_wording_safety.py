"""
tests/test_wording_safety.py — Critical wording and contamination safety tests (v5.0).

These tests verify:
  1. GENERATED/VENDOR files have NO origin_estimate (no misleading AI-authorship claims)
  2. Origin estimate always carries non-deterministic caveats
  3. Origin estimate JSON includes pct_note disclaimer
  4. Summary labels use "pattern signal" language, not authorship language
  5. Origin estimate three-way sum always equals 100%
  6. JSON schema does not overclaim AI authorship
  7. Forbidden phrases are absent from key output strings
  8. Classification labels are pattern-based, not proof claims
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pathlib import Path
from ai_pattern_analyzer.scoring.model import score_file
from ai_pattern_analyzer.scoring.calibration import calibrate_repo
from ai_pattern_analyzer.domain import FileCategory, OriginEstimate
from ai_pattern_analyzer.origin.engine import compute_file_origin, aggregate_origin_estimates


# ── Contamination: GENERATED/VENDOR must not have origin_estimate ─────────────

def test_generated_file_has_no_origin_estimate():
    """GENERATED files (protobuf, OpenAPI, jOOQ) must NOT get an origin estimate.
    A protobuf stub is tool-generated, not LLM-generated — different concept."""
    result = score_file(
        path=Path("fake_pb2.py"), language="Python", kind="generated",
        lines=100, signals={}, category=FileCategory.GENERATED,
    )
    assert result.origin_estimate is None, (
        "GENERATED files must not have origin_estimate — "
        "tool-generated code is not the same as LLM-generated code"
    )

def test_vendor_file_has_no_origin_estimate():
    """VENDOR files (third-party code) must NOT get an origin estimate."""
    result = score_file(
        path=Path("vendor/lib.py"), language="Python", kind="production",
        lines=200, signals={}, category=FileCategory.VENDOR,
    )
    assert result.origin_estimate is None, (
        "VENDOR files must not have origin_estimate — "
        "third-party code is not subject to AI-origin estimation"
    )

def test_production_file_has_origin_estimate():
    """Production logic files SHOULD get an origin estimate."""
    result = score_file(
        path=Path("service.py"), language="Python", kind="production",
        lines=100, signals={"type_annotations": 0.7, "comment_density": 0.5},
        category=FileCategory.PRODUCTION_LOGIC,
    )
    assert result.origin_estimate is not None

def test_test_file_has_origin_estimate():
    """Test files should also get an origin estimate (they are kpi_eligible)."""
    result = score_file(
        path=Path("test_service.py"), language="Python", kind="test",
        lines=80, signals={"test_assertion_quality": 0.7},
        category=FileCategory.TEST,
    )
    assert result.origin_estimate is not None


# ── Portfolio not contaminated by generated/vendor ────────────────────────────

def test_portfolio_excludes_generated_files():
    """Aggregate should not be influenced by generated file origin estimates."""
    from ai_pattern_analyzer.scoring.model import FileAnalysis
    from ai_pattern_analyzer.domain import ScoreBreakdown

    # Create mock analyses: one production, one generated (no origin_estimate)
    prod = score_file(
        Path("service.py"), "Python", "production", 100,
        {"type_annotations": 0.8}, FileCategory.PRODUCTION_LOGIC,
    )
    gen = score_file(
        Path("fake_pb2.py"), "Python", "generated", 100, {},
        FileCategory.GENERATED,
    )

    # GENERATED has no origin_estimate → aggregate only uses prod
    pairs_with_gen = [
        (f.origin_estimate, f.lines)
        for f in [prod, gen]
        if f.origin_estimate is not None
    ]
    assert len(pairs_with_gen) == 1, "Only production file should contribute to portfolio"
    assert pairs_with_gen[0][1] == 100


# ── Caveats always present ────────────────────────────────────────────────────

def test_origin_estimate_always_has_caveats():
    """Every origin estimate must carry non-empty caveats."""
    result = score_file(
        Path("service.py"), "Python", "production", 100,
        {"type_annotations": 0.9, "comment_density": 0.8},
        FileCategory.PRODUCTION_LOGIC,
    )
    assert result.origin_estimate is not None
    assert len(result.origin_estimate.caveats) >= 3, (
        "Origin estimate must carry at least 3 caveats warning against overclaiming"
    )

def test_origin_estimate_caveats_mention_no_proof():
    """At least one caveat must explicitly say 'not forensic proof' or similar."""
    result = score_file(
        Path("service.py"), "Python", "production", 100,
        {"type_annotations": 0.9}, FileCategory.PRODUCTION_LOGIC,
    )
    oe = result.origin_estimate
    combined = " ".join(oe.caveats).lower()
    assert any(phrase in combined for phrase in [
        "not forensic", "not proof", "directional estimate", "not authorship",
    ]), f"No anti-overclaim caveat found in: {oe.caveats}"

def test_origin_estimate_as_dict_has_pct_note():
    """JSON output must contain pct_note warning."""
    result = score_file(
        Path("service.py"), "Python", "production", 100,
        {"type_annotations": 0.8}, FileCategory.PRODUCTION_LOGIC,
    )
    d = result.origin_estimate.as_dict()
    assert "pct_note" in d, "origin_estimate JSON must include pct_note disclaimer"
    note = d["pct_note"].lower()
    assert "not" in note or "do not" in note, (
        f"pct_note must warn against misinterpretation: {d['pct_note']}"
    )


# ── Summary labels use pattern language ───────────────────────────────────────

def test_summary_label_uses_pattern_language():
    """Summary labels must describe pattern signals, not authorship."""
    from ai_pattern_analyzer.scoring.calibration import RepoStats

    for kpi_score, expected_fragment in [
        (0.60, "pattern"),
        (0.45, "pattern"),
        (0.28, "signal"),
        (0.10, "signal"),
    ]:
        stats = RepoStats(
            repo_name="test", total_files=10, production_files=10,
            test_files=0, generated_files=0,
            mean_likelihood=kpi_score, median_likelihood=kpi_score, std_dev=0.05,
            p25=kpi_score * 0.8, p75=kpi_score * 1.2, p90=kpi_score * 1.4,
            mean_adjusted=kpi_score, median_adjusted=kpi_score,
            kpi_score=kpi_score,
            mean_risk=0.2, high_risk_count=0,
            ai_like_count=0, human_like_count=10, mixed_count=0, uncertain_count=0,
        )
        label = stats.summary_label.lower()
        assert expected_fragment in label, (
            f"kpi_score={kpi_score}: summary_label '{stats.summary_label}' "
            f"must contain '{expected_fragment}'"
        )

def test_summary_label_not_claiming_authorship():
    """No summary label should claim to know actual authorship."""
    from ai_pattern_analyzer.scoring.calibration import RepoStats

    for kpi_score in [0.05, 0.20, 0.45, 0.65, 0.85]:
        stats = RepoStats(
            repo_name="test", total_files=10, production_files=10,
            test_files=0, generated_files=0,
            mean_likelihood=kpi_score, median_likelihood=kpi_score, std_dev=0.05,
            p25=0, p75=0, p90=0,
            mean_adjusted=kpi_score, median_adjusted=kpi_score, kpi_score=kpi_score,
            mean_risk=0.2, high_risk_count=0,
            ai_like_count=0, human_like_count=10, mixed_count=0, uncertain_count=0,
        )
        label = stats.summary_label.lower()
        forbidden = [
            "written by ai", "generated by ai", "human authored",
            "humans wrote", "ai wrote", "proven"
        ]
        for phrase in forbidden:
            assert phrase not in label, (
                f"Overclaiming phrase '{phrase}' found in summary_label: '{stats.summary_label}'"
            )


# ── Forbidden phrases in origin estimate output ───────────────────────────────

FORBIDDEN_PHRASES = [
    "confirmed ai", "proven ai", "guaranteed ai", "definitely ai",
    "100% ai", "written by ai", "generated by ai lm",
    "proven human", "guaranteed human", "definitely human",
    "confirmed human",
]

def test_no_forbidden_phrases_in_origin_estimate_dict():
    """The origin_estimate dict must not contain any deterministic AI claims."""
    result = score_file(
        Path("service.py"), "Python", "production", 150,
        {"type_annotations": 0.90, "comment_density": 0.85, "docstring_quality": 0.80},
        FileCategory.PRODUCTION_LOGIC,
    )
    d = result.origin_estimate.as_dict()
    full_text = str(d).lower()
    for phrase in FORBIDDEN_PHRASES:
        assert phrase not in full_text, (
            f"Forbidden phrase '{phrase}' found in origin_estimate output"
        )

def test_no_forbidden_phrases_in_drivers():
    """Drivers must not overclaim."""
    result = score_file(
        Path("service.py"), "Python", "production", 100,
        {"type_annotations": 0.9, "scaffold_completeness": 0.8},
        FileCategory.PRODUCTION_LOGIC,
    )
    if result.origin_estimate:
        drivers_text = " ".join(result.origin_estimate.drivers).lower()
        for phrase in FORBIDDEN_PHRASES:
            assert phrase not in drivers_text, (
                f"Forbidden phrase '{phrase}' in drivers: {result.origin_estimate.drivers}"
            )


# ── Classification labels are pattern labels, not proof ───────────────────────

def test_classification_values_are_pattern_labels():
    """FileAnalysis.classification must only be: AI-like | human-like | mixed | uncertain.
    These are pattern labels, not authorship classifications."""
    valid_labels = {"AI-like", "human-like", "mixed", "uncertain"}

    for adj_score, signals in [
        (0.10, {"type_annotations": 0.1}),
        (0.50, {"type_annotations": 0.5, "comment_density": 0.5}),
        (0.80, {"type_annotations": 0.9, "comment_density": 0.9, "docstring_quality": 0.85}),
    ]:
        result = score_file(
            Path("f.py"), "Python", "production", 80, signals,
            FileCategory.PRODUCTION_LOGIC,
        )
        assert result.classification in valid_labels, (
            f"Classification '{result.classification}' not in allowed pattern labels"
        )

def test_classification_does_not_use_authorship_language():
    """Classification values must not imply verified authorship."""
    bad_labels = {"AI-generated", "human-written", "ai-authored", "bot-written"}
    result = score_file(
        Path("f.py"), "Python", "production", 80,
        {"type_annotations": 0.9}, FileCategory.PRODUCTION_LOGIC,
    )
    assert result.classification not in bad_labels, (
        f"Classification '{result.classification}' uses authorship language"
    )


# ── Confidence interval sanity ────────────────────────────────────────────────

def test_confidence_interval_bounds_are_valid():
    """Confidence intervals must be within [0, 100] and low <= high."""
    result = score_file(
        Path("f.py"), "Python", "production", 100,
        {"type_annotations": 0.7}, FileCategory.PRODUCTION_LOGIC,
    )
    if result.origin_estimate:
        for name, ci in result.origin_estimate.intervals.items():
            if hasattr(ci, "low") and hasattr(ci, "high"):
                assert ci.low >= 0.0, f"{name} interval low < 0: {ci.low}"
                assert ci.high <= 100.0, f"{name} interval high > 100: {ci.high}"
                assert ci.low <= ci.high, (
                    f"{name} interval inverted: [{ci.low}, {ci.high}]"
                )

def test_three_way_sum_with_high_signals():
    """Even with extreme signals, three-way sum must be 100%."""
    result = score_file(
        Path("f.py"), "Python", "production", 200,
        {k: 0.99 for k in ["type_annotations", "comment_density", "docstring_quality",
                             "scaffold_completeness", "prompt_residue"]},
        FileCategory.PRODUCTION_LOGIC,
    )
    if result.origin_estimate:
        oe = result.origin_estimate
        total = oe.fully_ai_generated_pct + oe.ai_assisted_pct + oe.human_authored_pct
        assert abs(total - 100.0) < 0.5, f"Sum {total:.2f} != 100 with extreme signals"


# ── Calibration repo: origin estimate respects kpi_eligible ──────────────────

def test_calibrate_repo_origin_excludes_generated():
    """calibrate_repo() must exclude GENERATED files from origin estimate."""
    prod = score_file(
        Path("service.py"), "Python", "production", 200,
        {"type_annotations": 0.8, "comment_density": 0.7},
        FileCategory.PRODUCTION_LOGIC,
    )
    gen = score_file(
        Path("Gen.py"), "Python", "generated", 300, {},
        FileCategory.GENERATED,
    )
    assert gen.origin_estimate is None, "Generated file should have no origin_estimate"

    stats = calibrate_repo("test_repo", [prod, gen])
    # The origin estimate should be based only on prod
    assert stats.origin_estimate is not None
    # Since only prod contributes, the estimate should reflect prod's signals
    # (not be inflated by generated files)


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
