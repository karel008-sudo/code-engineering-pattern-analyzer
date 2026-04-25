"""
tests/test_heuristics.py — Unit tests for heuristic signal analyzers.

Tests cover core signals and fallback behavior for Python and Java.
All tests use inline code snippets (no file I/O) for speed.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from ai_pattern_analyzer.analyzers.heuristics import (
    comment_density,
    docstring_quality,
    type_annotations,
    exception_style,
    error_message_quality,
    log_quality,
    function_name_length,
    stream_usage,
    empty_catch,
    optional_usage,
    lombok_annotations,
    compute_all,
)


# ── comment_density ───────────────────────────────────────────────────────────

def test_comment_density_high():
    code = "\n".join(["# comment"] * 50 + ["x = 1"] * 5)
    assert comment_density(code, "Python") >= 0.80

def test_comment_density_low():
    code = "\n".join(["x = i * 2 + 1"] * 50)
    assert comment_density(code, "Python") <= 0.15

def test_comment_density_medium():
    code = "\n".join(["# comment", "x = 1", "y = 2", "z = 3"] * 10)
    val = comment_density(code, "Python")
    assert 0.20 < val < 0.80


# ── docstring_quality ─────────────────────────────────────────────────────────

def test_docstring_quality_structured():
    code = '''
def process(data):
    """
    Process the data.

    Args:
        data: Input data to process.

    Returns:
        Processed result.

    Raises:
        ValueError: If data is invalid.
    """
    return data
'''
    assert docstring_quality(code, "Python") >= 0.50

def test_docstring_quality_none():
    code = "def f(x):\n    return x * 2\n"
    assert docstring_quality(code, "Python") <= 0.15

def test_docstring_quality_javadoc():
    code = '''
/**
 * Process the given data.
 *
 * @param data the input data
 * @return the processed result
 * @throws IllegalArgumentException if data is null
 */
public Result process(Data data) {
    return compute(data);
}
'''
    assert docstring_quality(code, "Java") >= 0.40


# ── type_annotations ──────────────────────────────────────────────────────────

def test_type_annotations_full():
    code = """
def process(data: str, count: int) -> bool:
    pass
def validate(value: float, threshold: float) -> None:
    pass
def transform(items: list, config: dict) -> list:
    pass
"""
    assert type_annotations(code, "Python") >= 0.70

def test_type_annotations_none():
    code = """
def process(data, count):
    pass
def validate(value, threshold):
    pass
"""
    assert type_annotations(code, "Python") <= 0.20

def test_type_annotations_java_neutral():
    code = "public String process(String data) { return data; }"
    val = type_annotations(code, "Java")
    assert 0.35 <= val <= 0.45  # neutral for Java


# ── exception_style ───────────────────────────────────────────────────────────

def test_exception_style_bare_except():
    code = "try:\n    do()\nexcept:\n    pass\n"
    assert exception_style(code, "Python") <= 0.20

def test_exception_style_specific():
    code = """
try:
    result = process(data)
except ValueError as exc:
    raise ProcessingError("Invalid data") from exc
except IOError as exc:
    raise SystemError("IO failed") from exc
"""
    assert exception_style(code, "Python") >= 0.60

def test_exception_style_broad_pass():
    code = "try:\n    do()\nexcept Exception:\n    pass\n"
    assert exception_style(code, "Python") <= 0.20


# ── error_message_quality ─────────────────────────────────────────────────────

def test_error_message_quality_rich():
    code = """
raise ValueError(f"Invalid customer ID {customer_id}: must be a non-empty UUID string")
raise ValueError(f"Order {order_id} not found for customer {customer_id}")
raise ValueError(f"Payment amount {amount} exceeds limit {MAX_AMOUNT}")
raise ValueError(f"Product {product_id} is out of stock (requested: {qty})")
"""
    assert error_message_quality(code, "Python") >= 0.65

def test_error_message_quality_generic():
    code = "raise ValueError('error')\nraise Exception('failed')\n"
    assert error_message_quality(code, "Python") <= 0.30


# ── log_quality ───────────────────────────────────────────────────────────────

def test_log_quality_system_out():
    code = 'System.out.println("Processing...");\nSystem.out.println("Done");\n'
    assert log_quality(code, "Java") <= 0.25

def test_log_quality_parameterized():
    code = """
logger.info("Processing order {}: customer={}", orderId, customerId);
logger.debug("Validation result for {}: valid={}", requestId, isValid);
logger.warn("Retry attempt {} for {}", attempt, serviceId);
"""
    assert log_quality(code, "Java") >= 0.55

def test_log_quality_bare_print():
    code = "print('starting')\nprint('processing')\nprint('done')\n" * 5
    assert log_quality(code, "Python") <= 0.20


# ── function_name_length ──────────────────────────────────────────────────────

def test_function_name_length_long():
    code = """
def calculate_total_order_amount_with_discounts(order, discounts):
    pass
def validate_customer_shipping_address_format(address):
    pass
def process_payment_transaction_with_retry_logic(payment, retries):
    pass
"""
    assert function_name_length(code, "Python") >= 0.65

def test_function_name_length_short():
    code = """
def calc(x, y):
    pass
def get(id):
    pass
def run(data):
    pass
"""
    assert function_name_length(code, "Python") <= 0.40


# ── stream_usage (Java) ───────────────────────────────────────────────────────

def test_stream_usage_heavy():
    code = """
List<Order> result = orders.stream()
    .filter(o -> o.getStatus() == ACTIVE)
    .map(OrderMapper::toDto)
    .collect(Collectors.toList());
long count = items.stream().filter(i -> i.isValid()).count();
Optional<Product> found = products.stream().findFirst();
"""
    assert stream_usage(code, "Java") >= 0.65

def test_stream_usage_loops():
    code = """
for (int i = 0; i < orders.size(); i++) {
    Order o = orders.get(i);
    process(o);
}
for (Order o : pendingOrders) {
    if (o.isExpired()) continue;
    o.cancel();
}
"""
    assert stream_usage(code, "Java") <= 0.30

def test_stream_usage_non_java():
    val = stream_usage("x = list(map(f, items))", "Python")
    assert 0.25 <= val <= 0.45  # neutral


# ── empty_catch ───────────────────────────────────────────────────────────────

def test_empty_catch_detected():
    code = "try { process(); } catch (Exception e) { }\n"
    assert empty_catch(code, "Java") <= 0.20

def test_empty_catch_print_stack():
    code = "try { process(); } catch (Exception e) { e.printStackTrace(); }\n"
    assert empty_catch(code, "Java") <= 0.20

def test_empty_catch_good():
    code = """
try {
    result = process(data);
} catch (SpecificException e) {
    logger.error("Processing failed: {}", e.getMessage());
    throw new ServiceException("Processing error", e);
}
"""
    # Good exception handling — no empty catch, no printStackTrace
    # Should score above bare_pass threshold (not human-like)
    assert empty_catch(code, "Java") >= 0.35


# ── lombok_annotations ────────────────────────────────────────────────────────

def test_lombok_heavy():
    code = """
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Slf4j
public class OrderEntity { }
"""
    assert lombok_annotations(code, "Java") >= 0.55

def test_lombok_none_with_getters():
    code = """
public class Order {
    public String getId() { return id; }
    public void setId(String id) { this.id = id; }
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }
}
"""
    assert lombok_annotations(code, "Java") <= 0.20


# ── compute_all ───────────────────────────────────────────────────────────────

def test_compute_all_returns_expected_keys():
    result = compute_all("def f(x: int) -> int:\n    return x\n", "Python")
    expected_keys = {
        "comment_density", "docstring_quality", "type_annotations",
        "exception_style", "error_message_quality", "log_quality",
        "function_name_length", "stream_usage", "empty_catch",
        "final_fields", "optional_usage", "lombok_annotations",
    }
    assert expected_keys.issubset(set(result.keys()))

def test_compute_all_values_in_range():
    result = compute_all("def f():\n    pass\n" * 20, "Python")
    for k, v in result.items():
        assert 0.0 <= v <= 1.0, f"Signal {k} out of range: {v}"


if __name__ == "__main__":
    import traceback
    tests = [v for k, v in globals().items() if k.startswith("test_") and callable(v)]
    passed = failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"FAIL: {test.__name__}: {e}")
            traceback.print_exc()
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
