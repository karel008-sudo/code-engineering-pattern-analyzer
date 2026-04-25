"""
DTO fixture — represents a Pydantic data class.

Expected: high type_annotations, moderate docstring_quality.
Expected: adjusted_score LOWER than raw_score (category = dto_mapper).
Expected: should NOT be classified as high-risk.
"""
from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class AddressDto(BaseModel):
    """Address data transfer object."""
    street: str
    city: str
    postal_code: str
    country: str = "CZ"


class OrderItemDto(BaseModel):
    """Single order item DTO."""
    product_id: str
    quantity: int = Field(ge=1)
    unit_price: float = Field(ge=0.0)

    @property
    def total_price(self) -> float:
        return self.quantity * self.unit_price


class CreateOrderRequest(BaseModel):
    """
    Request DTO for order creation endpoint.

    Attributes:
        customer_id: Unique customer identifier.
        items: List of order items.
        shipping_address: Delivery address.
        notes: Optional order notes.
    """
    customer_id: str
    items: List[OrderItemDto]
    shipping_address: AddressDto
    notes: Optional[str] = None


class OrderResponse(BaseModel):
    """Response DTO for order operations."""
    order_id: str
    customer_id: str
    status: str
    total_amount: float
    items: List[OrderItemDto]
    shipping_address: AddressDto
