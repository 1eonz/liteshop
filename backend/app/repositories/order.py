"""订单仓储：持久化订单聚合并在状态变更时加行锁。"""

from datetime import UTC, datetime
from typing import cast

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..enums.order import ALLOWED_TRANSITIONS, OrderStatus
from ..models.order import Order, OrderItem


class OrderNotFound(KeyError):
    """订单不存在。"""


class OrderStatusConflict(RuntimeError):
    """订单状态在事务期间被其他请求修改。"""


class OrderRepository:
    """订单查询和写入，不在仓储层决定 HTTP 行为。"""

    async def get_by_request(self, session: AsyncSession, user_id: int, request_id: str) -> Order | None:
        """按客户端请求 ID 查询已创建订单。"""
        return cast(
            Order | None,
            await session.scalar(
                select(Order)
                .where(Order.user_id == user_id, Order.client_request_id == request_id)
                .options(selectinload(Order.items))
            ),
        )

    async def get(self, session: AsyncSession, order_id: int) -> Order:
        """读取订单详情，不获取写锁。"""
        order = cast(
            Order | None,
            await session.scalar(select(Order).where(Order.id == order_id).options(selectinload(Order.items))),
        )
        if order is None:
            raise OrderNotFound(order_id)
        return order

    async def get_for_update(self, session: AsyncSession, order_id: int) -> Order:
        """锁定订单行，供状态机或支付回调使用。"""
        order = cast(
            Order | None,
            await session.scalar(
                select(Order).where(Order.id == order_id).options(selectinload(Order.items)).with_for_update()
            ),
        )
        if order is None:
            raise OrderNotFound(order_id)
        return order

    async def create(
        self,
        session: AsyncSession,
        *,
        user_id: int,
        order_no: str,
        client_request_id: str,
        total_amount: int,
        product_amount: int,
        freight_amount: int,
        discount_amount: int,
        address_snapshot: dict[str, str],
        items: list[dict[str, object]],
        expired_at: datetime | None = None,
        remark: str | None = None,
    ) -> Order:
        """在外部事务中创建订单及商品快照。"""
        now = datetime.now(UTC)
        order = Order(
            user_id=user_id,
            order_no=order_no,
            status=OrderStatus.PENDING_PAYMENT.value,
            total_amount=total_amount,
            product_amount=product_amount,
            freight_amount=freight_amount,
            discount_amount=discount_amount,
            address_snapshot=address_snapshot,
            remark=remark,
            client_request_id=client_request_id,
            expired_at=expired_at,
            created_at=now,
            updated_at=now,
        )
        order.items = [
            OrderItem(
                sku_id=cast(int, item["sku_id"]),
                product_id=cast(int, item["product_id"]),
                product_name=str(item["product_name"]),
                sku_code=str(item["sku_code"]),
                sku_name=str(item["sku_name"]),
                spec_values=cast(dict[str, str], item["spec_values"]),
                product_image=str(item["product_image"]),
                quantity=cast(int, item["quantity"]),
                price_cents=cast(int, item["price_cents"]),
                weight_grams=cast(int, item["weight_grams"]),
                total_amount=cast(int, item["total_amount"]),
                created_at=now,
            )
            for item in items
        ]
        session.add(order)
        await session.flush()
        return order

    async def transition(self, session: AsyncSession, order_id: int, target: OrderStatus) -> Order:
        """用状态条件更新实现乐观锁，只允许声明过的流转。"""
        order = await self.get_for_update(session, order_id)
        current = OrderStatus(order.status)
        if target not in ALLOWED_TRANSITIONS[current]:
            raise ValueError(f"{current}->{target} 不允许")
        changed_id = await session.scalar(
            update(Order)
            .where(Order.id == order_id, Order.status == current.value)
            .values(status=target.value, updated_at=datetime.now(UTC))
            .returning(Order.id)
        )
        if changed_id is None:
            raise OrderStatusConflict(f"订单 {order_id} 状态已变化")
        await session.refresh(order)
        return order

    async def list_for_user(
        self, session: AsyncSession, user_id: int, offset: int, limit: int
    ) -> tuple[list[Order], int]:
        """按创建时间倒序分页查询用户订单。"""
        result = await session.scalars(
            select(Order)
            .where(Order.user_id == user_id)
            .options(selectinload(Order.items))
            .order_by(Order.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        total = await session.scalar(select(func.count(Order.id)).where(Order.user_id == user_id))
        return list(result.unique().all()), int(total or 0)

    async def list_all(
        self,
        session: AsyncSession,
        offset: int,
        limit: int,
        status: OrderStatus | None = None,
    ) -> tuple[list[Order], int]:
        """后台分页读取订单，可按正向状态筛选。"""
        conditions = [Order.status == status.value] if status is not None else []
        result = await session.scalars(
            select(Order)
            .where(*conditions)
            .options(selectinload(Order.items))
            .order_by(Order.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        total = await session.scalar(select(func.count(Order.id)).where(*conditions))
        return list(result.unique().all()), int(total or 0)

    async def list_expired_for_update(self, session: AsyncSession, now: datetime, limit: int) -> list[Order]:
        """读取已到期的待付款订单并按行锁保护任务并发。"""
        result = await session.scalars(
            select(Order)
            .where(Order.status == OrderStatus.PENDING_PAYMENT.value, Order.expired_at <= now)
            .options(selectinload(Order.items))
            .order_by(Order.expired_at, Order.id)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return list(result.unique().all())
