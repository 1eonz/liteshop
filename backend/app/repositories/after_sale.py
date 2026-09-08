"""售后单仓储。"""

from datetime import UTC, datetime
from typing import cast
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.after_sale import AfterSale
from ..models.order import Order, OrderItem


class AfterSaleRepository:
    """封装售后查询和创建。"""

    async def get_by_request(self, session: AsyncSession, user_id: int, request_id: str) -> AfterSale | None:
        """按用户请求 ID 查找售后单。"""
        return cast(
            AfterSale | None,
            await session.scalar(
                select(AfterSale).where(AfterSale.user_id == user_id, AfterSale.client_request_id == request_id)
            ),
        )

    async def get_for_update(self, session: AsyncSession, after_sale_id: int) -> AfterSale | None:
        """锁定售后单。"""
        return cast(AfterSale | None, await session.get(AfterSale, after_sale_id, with_for_update=True))

    async def list_for_user(self, session: AsyncSession, user_id: int) -> list[AfterSale]:
        """列出用户售后单。"""
        result = await session.scalars(
            select(AfterSale).where(AfterSale.user_id == user_id).order_by(AfterSale.created_at.desc())
        )
        return list(result.all())

    async def get_order_item_for_user(
        self, session: AsyncSession, order_item_id: int, user_id: int
    ) -> OrderItem | None:
        """锁定用户的订单项。"""
        result = await session.scalars(
            select(OrderItem)
            .join(Order, Order.id == OrderItem.order_id)
            .where(OrderItem.id == order_item_id, Order.user_id == user_id)
            .options(selectinload(OrderItem.order))
            .with_for_update()
        )
        return result.first()

    async def list_all(self, session: AsyncSession, status: str | None = None) -> list[AfterSale]:
        """后台按状态读取售后单。"""
        statement = select(AfterSale)
        if status:
            statement = statement.where(AfterSale.status == status)
        result = await session.scalars(statement.order_by(AfterSale.created_at.desc()))
        return list(result.all())

    async def create(
        self,
        session: AsyncSession,
        *,
        item: OrderItem,
        user_id: int,
        request_id: str,
        sale_type: str,
        amount_cents: int,
        reason: str,
        evidence_urls: list[str],
    ) -> AfterSale:
        """创建售后单。"""
        now = datetime.now(UTC)
        sale = AfterSale(
            after_sale_no=f"AS{now:%Y%m%d%H%M%S}{uuid4().hex[:10]}",
            order_id=item.order_id,
            order_item_id=item.id,
            user_id=user_id,
            type=sale_type,
            status="PENDING_REVIEW",
            amount_cents=amount_cents,
            reason=reason,
            evidence_urls=evidence_urls,
            client_request_id=request_id,
            created_at=now,
            updated_at=now,
        )
        session.add(sale)
        await session.flush()
        return sale
