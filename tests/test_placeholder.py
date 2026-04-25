"""
tests/test_placeholder.py — Tests for placeholder and LLM-residue detection.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from ai_pattern_analyzer.analyzers.placeholder import (
    prompt_residue,
    placeholder_density,
    generic_literal_density,
    resilience_theater_score,
    compute_placeholder_signals,
)


# ── prompt_residue ────────────────────────────────────────────────────────────

def test_prompt_residue_high_with_instructional():
    code = """
# Here is an example implementation of the service
# You can use this as a starting point
# Replace with your actual business logic
# Note: This is a placeholder implementation
def process():
    pass
"""
    assert prompt_residue(code) >= 0.45

def test_prompt_residue_low_clean():
    code = """
def calculate_discount(order_value, customer_tier):
    if customer_tier == "GOLD" and order_value > 1000:
        return 0.15
    if customer_tier == "SILVER":
        return 0.10
    return 0.05
"""
    assert prompt_residue(code) <= 0.35

def test_prompt_residue_api_key_placeholder():
    code = 'api_key = "your-api-key"\nendpoint = "your-endpoint-here"\n'
    assert prompt_residue(code) >= 0.40


# ── placeholder_density ───────────────────────────────────────────────────────

def test_placeholder_density_many_todos():
    code = "\n".join([
        "# TODO: implement this",
        "# TODO: add validation",
        "# TODO: handle errors",
        "# FIXME: this is wrong",
        "raise NotImplementedError('not done')",
    ] + ["x = 1"] * 20)
    assert placeholder_density(code) >= 0.40

def test_placeholder_density_low_clean():
    code = """
def process_payment(amount, currency):
    if amount <= 0:
        raise ValueError(f"Amount must be positive, got {amount}")
    return {"status": "success", "amount": amount, "currency": currency}
""" * 5
    assert placeholder_density(code) <= 0.25

def test_placeholder_density_standalone_pass():
    code = "def stub():\n    pass\n" * 5 + "x = 1\n" * 20
    result = placeholder_density(code)
    assert result >= 0.25  # standalone pass is a signal


# ── generic_literal_density ───────────────────────────────────────────────────

def test_generic_literals_detected():
    code = """
user = {"name": "John Doe", "email": "test@example.com"}
api_key = "your-api-key"
endpoint = "http://localhost:8080"
dummy_data = {"value": "sample"}
"""
    assert generic_literal_density(code) >= 0.35

def test_generic_literals_domain_specific():
    code = """
customer = {"name": "T-Mobile CZ", "subscription": "ENTERPRISE_PRO"}
tariff = "UNLIMITED_5G"
billing_cycle = "MONTHLY"
"""
    assert generic_literal_density(code) <= 0.20


# ── resilience_theater ────────────────────────────────────────────────────────

def test_resilience_theater_empty_catch_comment():
    code = """
try {
    process(data);
} catch (Exception e) {
    // ignore
}
"""
    score = resilience_theater_score(code)
    assert score >= 0.40  # empty catch with comment

def test_resilience_theater_clean_code():
    code = """
try {
    result = process(data);
} catch (ProcessingException e) {
    logger.error("Processing failed: {}", e.getMessage());
    throw new ServiceException("Failed to process", e);
}
"""
    score = resilience_theater_score(code)
    assert score <= 0.20  # proper handling


# ── compute_placeholder_signals (dispatcher) ──────────────────────────────────

def test_compute_returns_expected_keys():
    result = compute_placeholder_signals("def f():\n    pass\n" * 20, "Python")
    assert "placeholder_density" in result
    assert "prompt_residue" in result
    for v in result.values():
        assert 0.0 <= v <= 1.0


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
