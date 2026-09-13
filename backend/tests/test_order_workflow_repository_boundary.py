"""订单工作流与订单仓储边界回归测试。"""

import asyncio
import hashlib
import hmac
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock

from sqlalchemy.ext.asyncio import AsyncSession

from app.enums.order import OrderStatus
from app.enums.payment import PaymentProvider
from app.models.order import Order
from app.repositories.inventory import InventoryRepository
from app.repositories.order import OrderRepository
from app.repositories.payment import PaymentRepository
from app.schemas.payments import PaymentCallback
from app.services.order_workflow import OrderWorkflow, payment_callback_signature_payload


def _workflow(
    order: SimpleNamespace,
    *,
    changed: SimpleNamespace | None = None,
    payments: SimpleNamespace | None = None,
) -> tuple[OrderWorkflow, SimpleNamespace, SimpleNamespace]:
    """构造只暴露仓储接口的订单工作流替身。"""
    orders = SimpleNamespace(
        get_for_update=AsyncMock(return_value=order),
        transition=AsyncMock(return_value=changed or order),
        flush=AsyncMock(),
    )
    inventory = SimpleNamespace(release=AsyncMock())
    workflow = OrderWorkflow(
        inventory=cast(InventoryRepository, inventory),
        orders=cast(OrderRepository, orders),
        payments=cast(PaymentRepository, payments) if payments is not None else None,
    )
    return workflow, orders, inventory


def _pending_order(**overrides: object) -> SimpleNamespace:
    """构造订单工作流测试所需的最小订单对象。"""
    values: dict[str, object] = {
        "id": 7,
        "order_no": "LS202609120001",
        "status": OrderStatus.PENDING_PAYMENT.value,
        "product_amount": 1000,
        "freight_amount": 100,
        "updated_at": datetime.now(UTC),
        "items": [SimpleNamespace(sku_id=3, quantity=2)],
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_cancel_order_flushes_through_order_repository() -> None:
    """取消订单后的状态和原因刷新必须经过订单仓储。"""
    order = _pending_order()
    changed = _pending_order(status=OrderStatus.CANCELLED.value)
    workflow, orders, _inventory = _workflow(order, changed=changed)
    session = cast(AsyncSession, object())

    result = asyncio.run(workflow.cancel_order(session, order.id, "cancel-request"))

    assert cast(object, result) is changed
    orders.flush.assert_awaited_once_with(session)


def test_confirm_order_flushes_through_order_repository() -> None:
    """确认收货后的完成时间刷新必须经过订单仓储。"""
    order = _pending_order(status=OrderStatus.SHIPPED.value)
    changed = _pending_order(status=OrderStatus.COMPLETED.value)
    workflow, orders, _inventory = _workflow(order, changed=changed)
    session = cast(AsyncSession, object())

    result = asyncio.run(workflow.confirm_order(session, order.id))

    assert cast(object, result) is changed
    orders.flush.assert_awaited_once_with(session)


def test_change_order_price_flushes_through_order_repository() -> None:
    """改价后的金额字段刷新必须经过订单仓储。"""
    order = _pending_order()
    workflow, orders, _inventory = _workflow(order)
    session = cast(AsyncSession, object())

    result = asyncio.run(workflow.change_order_price(session, order.id, 900))

    assert cast(object, result) is order
    assert order.total_amount == 900
    assert order.discount_amount == 200
    orders.flush.assert_awaited_once_with(session)


def test_expire_order_flushes_through_order_repository() -> None:
    """支付超时取消后的订单字段刷新必须经过订单仓储。"""
    order = _pending_order()
    changed = _pending_order(status=OrderStatus.CANCELLED.value)
    workflow, orders, _inventory = _workflow(order, changed=changed)
    session = cast(AsyncSession, object())

    result = asyncio.run(workflow.expire_order(session, cast(Order, order), "expire-request"))

    assert cast(object, result) is changed
    orders.flush.assert_awaited_once_with(session)


def test_payment_callback_flushes_order_before_marking_payment_paid() -> None:
    """支付回调必须先刷新订单已支付状态，再标记支付单成功。"""
    secret = "s" * 32
    provider = PaymentProvider.WECHAT
    payload_without_signature = PaymentCallback.model_validate(
        {
            "orderId": 7,
            "callbackId": "callback-7",
            "amountCents": 1100,
            "signature": "placeholder",
            "providerTradeNo": "trade-7",
        }
    )
    canonical = payment_callback_signature_payload(payload_without_signature, provider)
    signature = hmac.new(secret.encode(), canonical.encode(), hashlib.sha256).hexdigest()
    payload = payload_without_signature.model_copy(update={"signature": signature})
    order = _pending_order(total_amount=1100, items=[])
    payment = SimpleNamespace(
        order_id=order.id,
        amount_cents=1100,
        channel=provider.value,
        status="PENDING",
        transaction_id=None,
    )
    payments = SimpleNamespace(
        get_by_callback=AsyncMock(return_value=None),
        get_for_order=AsyncMock(return_value=payment),
        mark_paid=AsyncMock(return_value=payment),
    )
    workflow, orders, _inventory = _workflow(order, payments=payments)
    session = cast(AsyncSession, object())

    result = asyncio.run(workflow.payment_callback(session, payload, provider, secret))

    assert cast(object, result) is payment
    orders.flush.assert_awaited_once_with(session)
    payments.mark_paid.assert_awaited_once()
