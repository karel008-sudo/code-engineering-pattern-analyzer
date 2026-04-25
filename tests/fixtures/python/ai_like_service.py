"""
AI-like service fixture — represents clean, structured code with AI-like patterns.

Expected: high type_annotations, docstring_quality, comment_density, exception_style.
Expected score band: elevated (0.40–0.65 adjusted).
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class CustomerOrderService:
    """
    Service for managing customer orders.

    This service handles the complete order lifecycle including creation,
    validation, processing, and cancellation.

    Attributes:
        repository: The order repository for persistence operations.
        notification_service: Service for sending customer notifications.
        validator: Order validation component.
    """

    def __init__(
        self,
        repository: "OrderRepository",
        notification_service: "NotificationService",
        validator: "OrderValidator",
    ) -> None:
        self._repository = repository
        self._notification_service = notification_service
        self._validator = validator

    def create_order(
        self,
        customer_id: str,
        items: List[Dict[str, int]],
        shipping_address: str,
    ) -> "Order":
        """
        Create a new customer order.

        Args:
            customer_id: The unique identifier of the customer.
            items: List of order items with product_id and quantity.
            shipping_address: The shipping address for the order.

        Returns:
            The newly created Order instance.

        Raises:
            ValidationError: If the order data is invalid.
            CustomerNotFoundError: If the customer does not exist.
            InsufficientInventoryError: If any item is out of stock.
        """
        # Validate the order data before processing
        validation_result = self._validator.validate(customer_id, items)
        if not validation_result.is_valid:
            raise ValidationError(
                f"Order validation failed for customer {customer_id}: "
                f"{validation_result.error_message}"
            )

        # Create the order entity
        order = Order(
            customer_id=customer_id,
            items=items,
            shipping_address=shipping_address,
            status=OrderStatus.PENDING,
        )

        # Persist the order to the repository
        try:
            saved_order = self._repository.save(order)
            logger.info(
                "Order created successfully for customer %s: order_id=%s",
                customer_id,
                saved_order.id,
            )
        except RepositoryException as exc:
            logger.error(
                "Failed to persist order for customer %s: %s",
                customer_id,
                str(exc),
            )
            raise OrderCreationError(
                f"Failed to create order for customer {customer_id}"
            ) from exc

        # Send confirmation notification
        self._notification_service.send_order_confirmation(saved_order)

        return saved_order

    def cancel_order(
        self,
        order_id: str,
        reason: Optional[str] = None,
    ) -> bool:
        """
        Cancel an existing order.

        Args:
            order_id: The unique identifier of the order to cancel.
            reason: Optional reason for cancellation.

        Returns:
            True if the order was successfully cancelled, False otherwise.

        Raises:
            OrderNotFoundError: If the order does not exist.
            OrderCancellationError: If the order cannot be cancelled.
        """
        try:
            order = self._repository.find_by_id(order_id)
        except RepositoryException as exc:
            raise OrderNotFoundError(
                f"Order {order_id} not found"
            ) from exc

        if not order.is_cancellable():
            raise OrderCancellationError(
                f"Order {order_id} cannot be cancelled in status {order.status}"
            )

        order.cancel(reason=reason)
        self._repository.save(order)

        logger.info("Order %s cancelled. Reason: %s", order_id, reason or "not specified")
        return True

    def get_orders_by_customer(
        self,
        customer_id: str,
        status_filter: Optional[List[str]] = None,
    ) -> List["Order"]:
        """
        Retrieve all orders for a specific customer.

        Args:
            customer_id: The customer identifier.
            status_filter: Optional list of status values to filter by.

        Returns:
            List of orders matching the criteria.
        """
        orders = self._repository.find_by_customer(customer_id)

        if status_filter:
            orders = [o for o in orders if o.status in status_filter]

        logger.debug(
            "Retrieved %d orders for customer %s",
            len(orders),
            customer_id,
        )
        return orders
