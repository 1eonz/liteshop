"""退款记录仓储。"""

from datetime import UTC, datetime
from typing import cast
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.order import Payment
from ..models.refund import Refund


class RefundRepository:
    """封装退款记录的查询和创建。"""

    async def get_by_request(self, session: AsyncSession, payment_id: int, request_id: str) -> Refund | None:
        """按客户端请求 ID 查找已创建退款。"""
        return cast(
            Refund | None,
            await session.scalar(
                select(Refund).where(Refund.payment_id == payment_id, Refund.client_request_id == request_id)
            ),
        )

    async def get_for_update(self, session: AsyncSession, refund_id: int) -> Refund | None:
        """按主键锁定退款记录。"""
        return cast(Refund | None, await session.get(Refund, refund_id, with_for_update=True))

    async def flush(self, session: AsyncSession) -> None:
        """刷新退款状态和关联订单字段，不提交外层事务。"""
        await session.flush()

    async def sum_active_amount(self, session: AsyncSession, payment_id: int) -> int:
        """统计尚未失败退款的金额，防止累计超过支付金额。"""
        value = await session.scalar(
            select(func.coalesce(func.sum(Refund.amount_cents), 0)).where(
                Refund.payment_id == payment_id,
                Refund.status.in_(["PENDING", "SUCCESS"]),
            )
        )
        return int(value or 0)

    async def create(
        self,
        session: AsyncSession,
        *,
        payment: Payment,
        amount_cents: int,
        reason: str,
        request_id: str,
    ) -> Refund:
        """创建待处理退款记录，渠道调用在事务外执行。"""
        now = datetime.now(UTC)
        refund = Refund(
            refund_no=f"RF{now:%Y%m%d%H%M%S}{uuid4().hex[:10]}",
            payment_id=payment.id,
            amount_cents=amount_cents,
            status="PENDING",
            refund_reason=reason,
            client_request_id=request_id,
            created_at=now,
            updated_at=now,
        )
        session.add(refund)
        await session.flush()
        return refund
