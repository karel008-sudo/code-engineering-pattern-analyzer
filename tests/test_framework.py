"""
tests/test_framework.py — Unit tests for framework detection.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from ai_pattern_analyzer.analyzers.framework import detect_framework_context


SPRING_CONTROLLER = """
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.beans.factory.annotation.Autowired;

@RestController
@RequestMapping("/api/orders")
public class OrderController {
    @Autowired
    private OrderService orderService;

    @GetMapping("/{id}")
    public ResponseEntity<OrderDto> getOrder(@PathVariable String id) {
        return ResponseEntity.ok(orderService.findById(id));
    }
}
"""

JPA_ENTITY = """
import javax.persistence.*;

@Entity
@Table(name = "orders")
public class OrderEntity {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String customerId;

    @ManyToOne
    @JoinColumn(name = "customer_id")
    private CustomerEntity customer;
}
"""

MAPSTRUCT_MAPPER = """
import org.mapstruct.Mapper;
import org.mapstruct.Mapping;
import org.mapstruct.AfterMapping;

@Mapper(componentModel = "spring")
public interface OrderMapper {
    @Mapping(source = "customer.id", target = "customerId")
    OrderDto toDto(OrderEntity entity);

    @Mapping(source = "customerId", target = "customer.id")
    OrderEntity toEntity(OrderDto dto);
}
"""

PYDANTIC_MODEL = """
from pydantic import BaseModel, Field
from typing import Optional, List

class OrderItemSchema(BaseModel):
    product_id: str
    quantity: int = Field(ge=1)
    unit_price: float = Field(ge=0.0)

class CreateOrderRequest(BaseModel):
    customer_id: str
    items: List[OrderItemSchema]
    shipping_address: str
    notes: Optional[str] = None
"""

FASTAPI_ROUTES = """
from fastapi import FastAPI, APIRouter, Depends

app = FastAPI()
router = APIRouter()

@router.get("/orders/{order_id}")
async def get_order(order_id: str):
    return {"order_id": order_id}

@router.post("/orders")
async def create_order(request: CreateOrderRequest):
    return {"status": "created"}
"""

PLAIN_PYTHON = """
def process_data(items):
    result = []
    for item in items:
        if item.is_valid():
            result.append(item.transform())
    return result
"""


def test_spring_controller_detected():
    ctx = detect_framework_context(SPRING_CONTROLLER, "Java")
    assert ctx.is_spring_component
    assert "spring-boot" in ctx.detected_frameworks
    assert ctx.boilerplate_score > 0.15

def test_jpa_entity_detected():
    ctx = detect_framework_context(JPA_ENTITY, "Java")
    assert ctx.is_jpa_entity
    assert ctx.boilerplate_score >= 0.50

def test_mapstruct_detected():
    ctx = detect_framework_context(MAPSTRUCT_MAPPER, "Java")
    assert ctx.is_mapstruct_mapper
    assert ctx.boilerplate_score >= 0.70
    assert ctx.is_framework_boilerplate

def test_pydantic_detected():
    ctx = detect_framework_context(PYDANTIC_MODEL, "Python")
    assert ctx.is_pydantic_model
    assert ctx.boilerplate_score >= 0.30

def test_fastapi_detected():
    ctx = detect_framework_context(FASTAPI_ROUTES, "Python")
    assert ctx.is_fastapi_route
    assert ctx.boilerplate_score > 0.0

def test_no_framework():
    ctx = detect_framework_context(PLAIN_PYTHON, "Python")
    assert not ctx.detected_frameworks
    assert ctx.boilerplate_score == 0.0

def test_java_no_spring():
    plain_java = "public class Calculator { public int add(int a, int b) { return a + b; } }"
    ctx = detect_framework_context(plain_java, "Java")
    assert not ctx.is_spring_component
    assert not ctx.is_jpa_entity

def test_boilerplate_reduces_score():
    """Framework boilerplate should reduce the adjusted score vs raw score."""
    from ai_pattern_analyzer.scoring.adjusted import apply_framework_adjustment
    raw = 0.60
    adj, delta = apply_framework_adjustment(raw, detect_framework_context(MAPSTRUCT_MAPPER, "Java"))
    assert adj < raw  # framework reduces the score
    assert delta < 0   # delta is negative


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
