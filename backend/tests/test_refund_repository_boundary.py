"""退款服务仓储边界回归测试。"""

import asyncio
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.refund import Refund
from app.repositories.order import OrderRepository
from app.repositories.payment import PaymentRepository
from app.repositories.refund import RefundRepository
from app.services.refund import RefundService


def test_refund_create_delegates_order_flush_and_refund_create() -> None:
    """退款申请通过订单和退款仓储持久化，不直接操作会话。"""
    payment = SimpleNamespace(id=3, user_id=7, status="SUCCESS", amount_cents=1000, order_id=5)
    order = SimpleNamespace(refund_status="NONE")
    refund = cast(Refund, SimpleNamespace(id=11, amount_cents=500))
    payments = SimpleNamespace(get_by_id=AsyncMock(return_value=payment))
    orders = SimpleNamespace(get_for_update=AsyncMock(return_value=order), flush=AsyncMock())
    refunds = SimpleNamespace(
        get_by_request=AsyncMock(return_value=None),
        sum_active_amount=AsyncMock(return_value=0),
        create=AsyncMock(return_value=refund),
    )
    service = RefundService()
    service.payments = cast(PaymentRepository, payments)
    service.orders = cast(OrderRepository, orders)
    service.refunds = cast(RefundRepository, refunds)
    session = cast(AsyncSession, object())

    result = asyncio.run(
        service.create(
            session,
            user_id=7,
            payment_id=3,
            amount_cents=500,
            reason="商品问题",
            request_id="refund-request",
        )
    )

    assert result is refund
    assert order.refund_status == "APPLYING"
    orders.flush.assert_awaited_once_with(session)
    refunds.create.assert_awaited_once()
