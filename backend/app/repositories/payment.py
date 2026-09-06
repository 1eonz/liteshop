"""支付单仓储。"""

from datetime import UTC, datetime
from typing import cast
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.order import Order, Payment


class PaymentRepository:
    """支付单查询和幂等更新。"""

    async def get_by_request(self, session: AsyncSession, order_id: int, request_id: str) -> Payment | None:
        """按客户端请求 ID 查询已创建支付单。"""
        return cast(
            Payment | None,
            await session.scalar(
                select(Payment).where(
                    Payment.order_id == order_id,
                    Payment.client_request_id == request_id,
                )
            ),
        )

    async def get_by_callback(self, session: AsyncSession, callback_id: str) -> Payment | None:
        """按 provider 回调 ID 查询支付单。"""
        return cast(Payment | None, await session.scalar(select(Payment).where(Payment.callback_id == callback_id)))

    async def get_by_id(self, session: AsyncSession, payment_id: int, *, for_update: bool = False) -> Payment | None:
        """按主键读取支付单，可选加行锁。"""
        statement = (
            select(Payment)
            .where(Payment.id == payment_id)
            .options(selectinload(Payment.order).selectinload(Order.items))
        )
        if for_update:
            statement = statement.with_for_update()
        return cast(Payment | None, await session.scalar(statement))

    async def get_for_order(
        self,
        session: AsyncSession,
        order_id: int,
        *,
        for_update: bool = False,
    ) -> Payment | None:
        """读取订单最近一笔支付单。"""
        statement = select(Payment).where(Payment.order_id == order_id).order_by(Payment.id.desc())
        if for_update:
            statement = statement.with_for_update()
        return cast(
            Payment | None,
            await session.scalar(statement),
        )

    async def create(
        self,
        session: AsyncSession,
        *,
        order_id: int,
        user_id: int,
        provider: str,
        amount_cents: int,
        client_request_id: str,
    ) -> Payment:
        """创建待支付单，外部事务负责提交。"""
        now = datetime.now(UTC)
        payment = Payment(
            payment_no=f"PAY{now:%Y%m%d%H%M%S}{uuid4().hex[:12]}",
            order_id=order_id,
            user_id=user_id,
            channel=provider,
            status="PENDING",
            amount_cents=amount_cents,
            client_request_id=client_request_id,
            created_at=now,
            updated_at=now,
        )
        session.add(payment)
        await session.flush()
        return payment

    async def mark_paid(
        self,
        session: AsyncSession,
        payment: Payment,
        callback_id: str,
        trade_no: str,
        callback_raw: str,
    ) -> Payment:
        """将支付单标记为已支付；重复回调由调用方先查询。"""
        payment.status = "SUCCESS"
        payment.callback_id = callback_id
        payment.transaction_id = trade_no
        payment.callback_raw = callback_raw
        now = datetime.now(UTC)
        payment.paid_at = now
        payment.callback_at = now
        payment.updated_at = now
        await session.flush()
        return payment
