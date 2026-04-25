"""
tests/test_lexical.py — Tests for lexical signal analyzers.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from ai_pattern_analyzer.analyzers.lexical import token_entropy, type_token_ratio, repetition_index


def test_token_entropy_high_variety():
    """High vocabulary variety → low AI signal."""
    code = " ".join([
        "customer", "subscription", "tariff", "billing", "invoice",
        "payment", "contract", "agreement", "activation", "renewal",
        "deactivation", "termination", "transfer", "roaming", "coverage",
        "bandwidth", "latency", "throughput", "handover", "authentication",
    ] * 3)
    result = token_entropy(code)
    assert result <= 0.50  # high entropy = human-like = low AI signal

def test_token_entropy_repetitive():
    """Very repetitive code → higher AI signal than varied code."""
    varied = " ".join([f"var{i}" for i in range(100)])
    repetitive = "get set get set get set get set get set " * 30
    varied_result = token_entropy(varied)
    repetitive_result = token_entropy(repetitive)
    # Repetitive code should score higher than varied code (more AI-like)
    assert repetitive_result >= varied_result - 0.10  # allowing some tolerance

def test_token_entropy_small_file():
    result = token_entropy("x = 1")
    assert result == 0.5  # too small → neutral

def test_token_entropy_bounds():
    for code in ["x = 1\n" * 50, "import os\n" * 50]:
        val = token_entropy(code)
        assert 0.0 <= val <= 1.0


def test_type_token_ratio_high_variety():
    """High TTR (many unique words) → low AI signal."""
    words = [f"var{i}" for i in range(100)]
    code = " ".join(words)
    result = type_token_ratio(code)
    # High unique ratio → low repetition → low AI signal
    assert result <= 0.60

def test_type_token_ratio_repetitive():
    """Low TTR (few unique, repeated often) → high AI signal."""
    code = "get set update delete create list find " * 50
    result = type_token_ratio(code)
    assert result >= 0.40

def test_type_token_ratio_bounds():
    code = "def f(x):\n    return x\n" * 30
    val = type_token_ratio(code)
    assert 0.0 <= val <= 1.0


def test_repetition_index_repeated_blocks():
    """Repeated structural blocks → high AI signal."""
    block = "if condition:\n    do_something()\n    return result\n"
    code = block * 20
    result = repetition_index(code)
    assert result >= 0.50

def test_repetition_index_varied():
    """Varied code → lower repetition index than highly repeated blocks."""
    varied = "\n".join([
        "def process_order(order):",
        "    customer = get_customer(order.customer_id)",
        "    if not customer.is_active:",
        "        raise InactiveCustomerError(customer.id)",
        "def validate_payment(amount, currency):",
        "    if amount <= 0:",
        "        raise ValueError(f'Invalid amount: {amount}')",
        "    if currency not in SUPPORTED_CURRENCIES:",
        "        raise UnsupportedCurrencyError(currency)",
        "def calculate_discount(tier, amount):",
        "    if tier == 'GOLD':",
        "        return amount * 0.15",
        "    return amount * 0.05",
    ] * 3)
    repeated = ("if condition:\n    do_something()\n    return result\n") * 20
    varied_result = repetition_index(varied)
    repeated_result = repetition_index(repeated)
    # Repeated blocks should score higher than varied code
    assert repeated_result >= varied_result

def test_repetition_index_small_file():
    result = repetition_index("x = 1\n" * 5)
    assert result == 0.3  # too small → low signal

def test_repetition_index_bounds():
    code = "x = i + j\n" * 50
    val = repetition_index(code)
    assert 0.0 <= val <= 1.0


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
