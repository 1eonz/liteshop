"""库存、订单状态机和支付幂等测试。"""

import asyncio
import hashlib
import hmac

import pytest

from app.enums.order import OrderStatus
from app.enums.payment import PaymentProvider
from app.services.inventory import InventoryError, InventoryService
from app.services.order import InvalidOrderTransition, OrderService
from app.services.payment import PaymentService


def test_inventory_lock_release() -> None:
    service = InventoryService()
    service.seed(1, 5)
    asyncio.run(service.lock(1, 3))
    assert service.snapshot(1).available == 2
    asyncio.run(service.release(1, 3))
    assert service.snapshot(1).available == 5
    with pytest.raises(InventoryError):
        asyncio.run(service.lock(1, 6))


def test_order_transition_and_payment_idempotency() -> None:
    orders = OrderService()
    order = orders.create("u1", "r1", 1299)
    payment = PaymentService(orders, "secret")
    payment.create("u1", order.order_id, PaymentProvider.WECHAT, 1299, "pay-request")
    callback_id = "cb1"
    payload = f"{order.order_id}:1299:{callback_id}"
    signature = hmac.new(b"secret", payload.encode(), hashlib.sha256).hexdigest()
    assert payment.callback(order.order_id, callback_id, 1299, signature)
    assert payment.callback(order.order_id, callback_id, 1299, signature)
    assert order.status is OrderStatus.PAID
    with pytest.raises(InvalidOrderTransition):
        orders.transition(order.order_id, OrderStatus.PENDING_PAYMENT)


def test_payment_create_validates_owner_and_amount() -> None:
    """支付创建必须校验订单归属和金额。"""
    orders = OrderService()
    order = orders.create("u1", "order-request", 1299)
    payments = PaymentService(orders, "secret")
    intent = payments.create("u1", order.order_id, PaymentProvider.WECHAT, 1299, "pay-request")
    assert payments.create("u1", order.order_id, PaymentProvider.WECHAT, 1299, "pay-request") == intent
    with pytest.raises(ValueError):
        payments.create("u2", order.order_id, PaymentProvider.WECHAT, 1299, "other-user")
    with pytest.raises(ValueError):
        payments.create("u1", order.order_id, PaymentProvider.WECHAT, 1300, "wrong-amount")


def test_payment_callback_id_cannot_cross_orders() -> None:
    """同一个渠道回调 ID 不能被重放到另一笔订单。"""
    orders = OrderService()
    first = orders.create("u1", "order-one", 1299)
    second = orders.create("u1", "order-two", 1299)
    payments = PaymentService(orders, "secret")
    payments.create("u1", first.order_id, PaymentProvider.WECHAT, 1299, "pay-one")
    payments.create("u1", second.order_id, PaymentProvider.WECHAT, 1299, "pay-two")

    callback_id = "shared-callback"
    first_payload = f"{first.order_id}:1299:{callback_id}"
    first_signature = hmac.new(b"secret", first_payload.encode(), hashlib.sha256).hexdigest()
    payments.callback(first.order_id, callback_id, 1299, first_signature)

    second_payload = f"{second.order_id}:1299:{callback_id}"
    second_signature = hmac.new(b"secret", second_payload.encode(), hashlib.sha256).hexdigest()
    with pytest.raises(ValueError, match="其他订单"):
        payments.callback(second.order_id, callback_id, 1299, second_signature)
