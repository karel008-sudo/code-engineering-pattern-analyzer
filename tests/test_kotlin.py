"""
tests/test_kotlin.py — Tests for Kotlin-native heuristics (v5.0).

Key design principle: Kotlin idioms (data classes, coroutines, null-safety)
MUST NOT significantly increase AI-like scores — they are language features.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from ai_pattern_analyzer.analyzers.kotlin import (
    kotlin_data_class_signal,
    kotlin_coroutine_usage,
    kotlin_nullability,
    kotlin_android_patterns,
    kotlin_test_patterns,
    compute_kotlin_signals,
)


KOTLIN_DATA_CLASS = """
data class OrderDto(
    val orderId: String,
    val customerId: String,
    val status: OrderStatus,
    val totalAmount: BigDecimal,
    val items: List<OrderItemDto>
)

sealed class OrderStatus {
    object Pending : OrderStatus()
    object Processing : OrderStatus()
    data class Failed(val reason: String) : OrderStatus()
}

value class OrderId(val value: String)
"""

KOTLIN_COROUTINES = """
class OrderRepository(private val db: Database) {
    suspend fun findById(id: String): Order? {
        return withContext(Dispatchers.IO) {
            db.query { orders.find { it.id == id } }
        }
    }

    fun observeOrders(): Flow<List<Order>> = flow {
        while (true) {
            emit(findAll())
            delay(1000)
        }
    }

    suspend fun saveAll(orders: List<Order>) = coroutineScope {
        orders.map { order ->
            async { save(order) }
        }.awaitAll()
    }
}
"""

KOTLIN_NULLABILITY = """
fun processOrder(order: Order?): Result {
    val customer = order?.customer ?: return Result.Error("No customer")
    val address = customer.address?.street
        ?: throw IllegalStateException("Address required")

    requireNotNull(order.items) { "Items cannot be null" }
    checkNotNull(order.totalAmount) { "Amount required" }

    return order.let { o ->
        o.items?.let { items ->
            Result.Success(processItems(items))
        }
    } ?: Result.Error("Processing failed")
}
"""

KOTLIN_ANDROID = """
@AndroidEntryPoint
class OrderFragment : Fragment() {
    private val viewModel: OrderViewModel by viewModels()

    @Composable
    fun OrderScreen() {
        val orders by viewModel.orders.collectAsState()
        LazyColumn {
            items(orders) { order ->
                OrderCard(order = order)
            }
        }
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        lifecycleScope.launch {
            viewModel.uiState.collect { state ->
                updateUI(state)
            }
        }
    }
}
"""

KOTLIN_TESTS = """
class OrderRepositoryTest {
    private val mockDb = mockk<Database>()
    private val repository = OrderRepository(mockDb)

    @Test
    fun `findById returns order when exists`() = runTest {
        val expected = Order(id = "123")
        coEvery { mockDb.query(any()) } returns expected

        val result = repository.findById("123")

        coVerify { mockDb.query(any()) }
        assertEquals(expected, result)
    }

    @Test
    fun `observeOrders emits updates`() = runTest {
        val testOrders = listOf(Order(id = "1"), Order(id = "2"))
        coEvery { repository.findAll() } returns testOrders

        repository.observeOrders().test {
            val item = awaitItem()
            assertEquals(testOrders, item)
            cancelAndIgnoreRemainingEvents()
        }
    }
}
"""


# ── Data classes are idiomatic — must NOT be high AI signal ──────────────────

def test_data_class_signal_is_low():
    """Kotlin data classes are language features, NOT AI-specific."""
    val = kotlin_data_class_signal(KOTLIN_DATA_CLASS)
    assert val <= 0.45, f"data class signal too high ({val}) — Kotlin idioms must not inflate score"

def test_data_class_returns_in_range():
    val = kotlin_data_class_signal(KOTLIN_DATA_CLASS)
    assert 0.0 <= val <= 1.0

def test_empty_kotlin_data_class():
    val = kotlin_data_class_signal("class Foo { fun bar() = 1 }")
    assert val <= 0.40


# ── Coroutines are modern Kotlin — contextual, not decisive ──────────────────

def test_coroutine_signal_is_moderate():
    """Coroutines are normal modern Kotlin — signal should be moderate."""
    val = kotlin_coroutine_usage(KOTLIN_COROUTINES)
    assert 0.30 <= val <= 0.65, f"coroutine signal {val} outside expected moderate range"

def test_no_coroutines_low_signal():
    plain = "fun add(a: Int, b: Int) = a + b\n" * 10
    val = kotlin_coroutine_usage(plain)
    assert val <= 0.45


# ── Null safety is correct Kotlin style ──────────────────────────────────────

def test_nullability_is_moderate():
    """Correct null handling is idiomatic Kotlin, not AI-specific."""
    val = kotlin_nullability(KOTLIN_NULLABILITY)
    assert 0.20 <= val <= 0.60, f"nullability signal {val} outside expected range"

def test_no_nullability_low_signal():
    plain = "fun process(data: String): String = data.uppercase()\n" * 10
    val = kotlin_nullability(plain)
    assert val <= 0.45


# ── Android patterns reduce AI score (framework boilerplate) ─────────────────

def test_android_patterns_reduce_score():
    """Android framework patterns should return LOW score — it's boilerplate."""
    val = kotlin_android_patterns(KOTLIN_ANDROID)
    assert val <= 0.40, f"Android pattern signal {val} too high — should reduce AI interpretation"

def test_android_patterns_reduce_score_vs_plain():
    """Android framework detection should produce LOWER score than plain code —
    it signals boilerplate, not AI generation."""
    plain = "fun calculate(x: Int, y: Int) = x * y\n" * 10
    val_plain = kotlin_android_patterns(plain)
    val_android = kotlin_android_patterns(KOTLIN_ANDROID)
    # Android code should have LOWER signal (boilerplate reduces AI interpretation)
    assert val_android <= val_plain, (
        f"Android ({val_android:.2f}) should be <= plain ({val_plain:.2f}) "
        "— Android patterns should reduce AI score"
    )


# ── Test patterns ─────────────────────────────────────────────────────────────

def test_kotlin_test_patterns_detected():
    val = kotlin_test_patterns(KOTLIN_TESTS)
    assert val >= 0.25  # test patterns should be detectable

def test_kotlin_test_patterns_in_range():
    val = kotlin_test_patterns(KOTLIN_TESTS)
    assert 0.0 <= val <= 1.0


# ── compute_kotlin_signals dispatcher ────────────────────────────────────────

def test_compute_kotlin_signals_returns_dict():
    result = compute_kotlin_signals(KOTLIN_DATA_CLASS)
    assert "kotlin_data_class" in result
    assert "kotlin_coroutines" in result
    assert "kotlin_nullability" in result
    assert "kotlin_android" in result
    assert "kotlin_tests" in result

def test_compute_kotlin_signals_all_in_range():
    result = compute_kotlin_signals(KOTLIN_COROUTINES)
    for k, v in result.items():
        assert 0.0 <= v <= 1.0, f"Signal {k}={v} out of [0,1]"

def test_kotlin_data_class_does_not_inflate_combined_score():
    """The combined Kotlin signal should not heavily inflate AI score."""
    result = compute_kotlin_signals(KOTLIN_DATA_CLASS)
    # Even with all Kotlin signals, the combined shouldn't suggest AI generation
    mean_signal = sum(result.values()) / len(result)
    assert mean_signal <= 0.50, f"Combined Kotlin signal mean {mean_signal:.2f} too high"


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
