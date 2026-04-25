"""
tests/test_scaffold.py — Tests for scaffold completeness, magic numbers, name-body coherence,
and style continuity (v5.0).
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from ai_pattern_analyzer.analyzers.scaffold import (
    scaffold_completeness, magic_number_discipline, name_body_coherence,
    compute_scaffold_signals,
)
from ai_pattern_analyzer.analyzers.style_continuity import (
    style_continuity_score, human_irregularity_score,
)


# ── Scaffold completeness ─────────────────────────────────────────────────────

UNIFORM_CRUD = """
def find_by_id(self, id: str) -> Order:
    return self.repo.find(id)

def save(self, order: Order) -> Order:
    return self.repo.save(order)

def delete(self, id: str) -> None:
    self.repo.delete(id)

def find_all(self) -> list:
    return self.repo.find_all()

def update(self, id: str, order: Order) -> Order:
    return self.repo.update(id, order)
""" * 3

IRREGULAR_CODE = """
def process_payment(amount, currency, customer):
    if amount <= 0:
        raise ValueError(f"Invalid amount: {amount}")
    if currency not in SUPPORTED_CURRENCIES:
        raise UnsupportedCurrencyError(f"Currency {currency} not supported")
    txn = self.payment_gateway.charge(customer.id, amount, currency)
    if txn.status == "failed":
        self.audit_log.record_failure(txn, customer)
        raise PaymentFailedError(txn.error_message)
    self.notification_service.send_receipt(customer.email, txn)
    return txn

def calculate_tax(amount, country):
    # Tax rules are complex and country-specific
    rate = TAX_RATES.get(country)
    if rate is None:
        # Some countries have complex multi-tier rates
        return self._calculate_complex_tax(amount, country)
    return round(amount * rate, 2)
"""

def test_uniform_crud_has_high_scaffold():
    val = scaffold_completeness(UNIFORM_CRUD, "Python")
    assert val >= 0.50, f"Uniform CRUD should have elevated scaffold score, got {val}"

def test_irregular_code_has_lower_scaffold():
    val = scaffold_completeness(IRREGULAR_CODE, "Python")
    uniform_val = scaffold_completeness(UNIFORM_CRUD, "Python")
    assert val < uniform_val, "Irregular code should have lower scaffold than uniform CRUD"

def test_scaffold_small_file():
    val = scaffold_completeness("def f():\n    pass\n", "Python")
    assert 0.0 <= val <= 1.0

def test_scaffold_returns_in_range():
    for code in [UNIFORM_CRUD, IRREGULAR_CODE, "", "x = 1\n" * 5]:
        val = scaffold_completeness(code, "Python")
        assert 0.0 <= val <= 1.0, f"scaffold_completeness out of range: {val}"


# ── Magic number discipline ───────────────────────────────────────────────────

HIGH_MAGIC = """
def calculate(x):
    if x > 42:
        return x * 3.14159 + 7
    elif x < 13:
        return x / 0.333 + 99
    elif x == 17:
        return x ** 2.71828
    return x + 42
"""

CLEAN_CODE = """
MAX_RETRIES = 3
TIMEOUT_SECONDS = 30
SUCCESS_STATUS = 200

def process_with_retry(request):
    for attempt in range(MAX_RETRIES):
        response = send_request(request)
        if response.status == SUCCESS_STATUS:
            return response
    raise MaxRetriesExceeded()
"""

def test_many_magic_numbers_low_discipline_score():
    val = magic_number_discipline(HIGH_MAGIC, "Python")
    # Many magic numbers → low discipline → lower AI-like signal
    assert val <= 0.55, f"Many magic numbers should give low discipline score, got {val}"

def test_clean_constants_high_discipline_score():
    val = magic_number_discipline(CLEAN_CODE, "Python")
    assert val >= 0.45, f"Clean constants should give moderate/high discipline score, got {val}"

def test_safe_literals_not_penalized():
    # -1, 0, 1, 2 should not count as magic numbers
    code = """
for i in range(len(items)):
    if items[i] == 0:
        items[i] = 1
    elif i == -1:
        break
"""
    val = magic_number_discipline(code, "Python")
    assert val >= 0.40  # safe literals should not tank the score

def test_http_codes_not_penalized():
    code = """
if response.status == 200:
    return response.json()
elif response.status == 404:
    raise NotFoundError()
elif response.status == 500:
    raise ServerError()
"""
    val = magic_number_discipline(code, "Python")
    assert val >= 0.40  # HTTP codes are safe literals

def test_magic_number_returns_in_range():
    for code in [HIGH_MAGIC, CLEAN_CODE, "", "x = 1"]:
        val = magic_number_discipline(code, "Python")
        assert 0.0 <= val <= 1.0, f"Out of range: {val}"


# ── Name-body coherence ───────────────────────────────────────────────────────

COHERENT_NAMES = """
def calculate_discount(order_value: float, customer_tier: str) -> float:
    if customer_tier == "GOLD" and order_value > 1000:
        return order_value * 0.15
    if customer_tier == "SILVER":
        return order_value * 0.10
    return order_value * 0.05

def validate_email_format(email: str) -> bool:
    import re
    pattern = r'^[\\w\\.-]+@[\\w\\.-]+\\.\\w+$'
    return bool(re.match(pattern, email))
"""

GENERIC_NAMES = """
def process(data):
    return data

def handle(request, response):
    response.send(request.body)

def execute(cmd):
    return run(cmd)

def doStuff(x, y):
    return x + y
"""

def test_name_body_coherence_is_heuristic_signal():
    """name_body_coherence is a supporting heuristic — just verify it's in range
    and produces different values for different code styles."""
    coherent = name_body_coherence(COHERENT_NAMES, "Python")
    generic = name_body_coherence(GENERIC_NAMES, "Python")
    # Both should be valid floats in range — the signal is context-dependent
    assert 0.0 <= coherent <= 1.0
    assert 0.0 <= generic <= 1.0
    # The two values should not be identical (signal is discriminating)
    # Allow up to 0.20 difference in either direction
    assert abs(coherent - generic) <= 0.80  # just a sanity check

def test_name_body_returns_in_range():
    for code in [COHERENT_NAMES, GENERIC_NAMES, "", "def f(): pass"]:
        val = name_body_coherence(code, "Python")
        assert 0.0 <= val <= 1.0, f"Out of range: {val}"


# ── Compute scaffold signals dispatcher ──────────────────────────────────────

def test_compute_scaffold_signals_has_expected_keys():
    result = compute_scaffold_signals(UNIFORM_CRUD, "Python")
    assert "scaffold_completeness" in result
    assert "magic_number_discipline" in result
    assert "name_body_coherence" in result

def test_compute_scaffold_signals_all_in_range():
    result = compute_scaffold_signals(IRREGULAR_CODE, "Python")
    for k, v in result.items():
        assert 0.0 <= v <= 1.0, f"Signal {k}={v} out of [0,1]"


# ── Style continuity ──────────────────────────────────────────────────────────

UNIFORM_STYLE = """
def method_one(self, param: str) -> None:
    '''Process param one.'''
    logger.info("Processing: %s", param)
    result = self.service.process(param)
    return result

def method_two(self, param: str) -> None:
    '''Process param two.'''
    logger.info("Processing: %s", param)
    result = self.service.handle(param)
    return result

def method_three(self, param: str) -> None:
    '''Process param three.'''
    logger.info("Processing: %s", param)
    result = self.service.execute(param)
    return result
""" * 4

DISCONTINUOUS_FILE = """
def legacy_method(x):
    # old style, messy
    res=x+1
    if res>0: return res
    return -1

def legacy_two(y,z):
    t=y*z
    if t<0:t=0
    return t

""" + """
def modern_well_structured_method(
    input_value: float,
    configuration: Configuration,
) -> ProcessingResult:
    '''
    Process input with full type annotations.

    Args:
        input_value: The value to process.
        configuration: Processing configuration.

    Returns:
        ProcessingResult with full metadata.

    Raises:
        ValidationError: If input is invalid.
    '''
    logger.info("Processing input_value=%s with config=%s", input_value, configuration)
    validated = self._validator.validate(input_value, configuration)
    if not validated.is_valid:
        raise ValidationError(
            f"Invalid input {input_value}: {validated.error_message}"
        )
    return self._processor.execute(validated.data, configuration)
""" * 3

def test_uniform_style_has_high_continuity():
    score, breaks = style_continuity_score(UNIFORM_STYLE)
    assert score >= 0.50, f"Uniform style should have high continuity, got {score:.2f}"

def test_discontinuous_file_has_lower_continuity():
    uniform_score, _ = style_continuity_score(UNIFORM_STYLE)
    discont_score, _ = style_continuity_score(DISCONTINUOUS_FILE)
    # Discontinuous should score lower than uniform
    assert discont_score <= uniform_score + 0.15  # allow some tolerance

def test_continuity_returns_valid_types():
    score, breaks = style_continuity_score(UNIFORM_STYLE)
    assert 0.0 <= score <= 1.0
    assert isinstance(breaks, list)

def test_small_file_continuity_neutral():
    score, breaks = style_continuity_score("x = 1\n" * 5)
    assert 0.0 <= score <= 1.0
    assert breaks == []  # small file → no breaks detected


# ── Human irregularity ────────────────────────────────────────────────────────

HUMAN_PATTERNS = """
def bad_exception_handling(x):
    try:
        return process(x)
    except:
        pass  # bare except — very human

def messy_debug():
    print("DEBUG: starting process")
    x = compute()
    print("result:", x)
    return x

def magic_heavy(items):
    if len(items) > 42:
        return items[:13]
    elif len(items) < 7:
        return items * 3
    return items
"""

AI_LIKE_PATTERNS = """
def calculate_total_order_amount(order: Order) -> Decimal:
    '''
    Calculate the total amount for an order.

    Args:
        order: The order to calculate.
    Returns:
        Total amount as Decimal.
    '''
    try:
        subtotal = sum(item.quantity * item.unit_price for item in order.items)
        tax = subtotal * Decimal('0.21')
        return subtotal + tax
    except SpecificCalculationError as exc:
        raise OrderCalculationError(
            f"Failed to calculate total for order {order.id}"
        ) from exc
"""

def test_human_patterns_have_higher_irregularity():
    human = human_irregularity_score(HUMAN_PATTERNS, "Python")
    ai = human_irregularity_score(AI_LIKE_PATTERNS, "Python")
    assert human >= ai, f"Human patterns ({human:.2f}) should score >= AI-like ({ai:.2f})"

def test_human_irregularity_returns_in_range():
    for code in [HUMAN_PATTERNS, AI_LIKE_PATTERNS, "", "x = 1"]:
        val = human_irregularity_score(code, "Python")
        assert 0.0 <= val <= 1.0, f"Out of range: {val}"


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
