"""会员后台仓储。"""

from typing import cast

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.order import Order
from ..models.user import User


class MembershipRepository:
    """封装会员、订单统计和会员写入所需的数据库访问。"""

    async def list_users(self, session: AsyncSession, offset: int, limit: int) -> list[User]:
        """分页读取会员基础资料。"""
        result = await session.scalars(select(User).order_by(User.created_at.desc()).offset(offset).limit(limit))
        return list(result.all())

    async def count_users(self, session: AsyncSession) -> int:
        """统计会员总数。"""
        return int(await session.scalar(select(func.count(User.id))) or 0)

    async def count_orders(self, session: AsyncSession, user_id: int) -> int:
        """统计会员订单数。"""
        return int(await session.scalar(select(func.count(Order.id)).where(Order.user_id == user_id)) or 0)

    async def sum_paid_orders(self, session: AsyncSession, user_id: int) -> int:
        """汇总已支付、已发货和已完成订单金额。"""
        return int(
            await session.scalar(
                select(func.coalesce(func.sum(Order.paid_amount), 0)).where(
                    Order.user_id == user_id,
                    Order.status.in_(["PAID", "SHIPPED", "COMPLETED"]),
                )
            )
            or 0
        )

    async def get_with_addresses(self, session: AsyncSession, user_id: int) -> User | None:
        """读取会员及地址。"""
        return cast(
            User | None,
            await session.scalar(select(User).where(User.id == user_id).options(selectinload(User.addresses))),
        )

    async def list_orders(self, session: AsyncSession, user_id: int) -> list[Order]:
        """读取会员订单历史。"""
        result = await session.scalars(select(Order).where(Order.user_id == user_id).order_by(Order.created_at.desc()))
        return list(result.all())

    async def get_for_update(self, session: AsyncSession, user_id: int) -> User | None:
        """锁定会员行，供等级和标签更新使用。"""
        return cast(User | None, await session.get(User, user_id, with_for_update=True))

    async def flush(self, session: AsyncSession) -> None:
        """刷新当前事务，不提交外层事务。"""
        await session.flush()
