"""会员后台查询和标签管理服务。"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.order import Order
from ..models.user import User


class MembershipError(ValueError):
    """会员业务校验失败。"""


class MembershipService:
    """按数据库真实数据提供会员列表、详情和可审计写操作。"""

    async def list_members(self, session: AsyncSession, page: int, page_size: int) -> dict[str, object]:
        """返回会员分页摘要，手机号默认脱敏。"""
        offset = (page - 1) * page_size
        users = await session.scalars(select(User).order_by(User.created_at.desc()).offset(offset).limit(page_size))
        total = int(await session.scalar(select(func.count(User.id))) or 0)
        items: list[dict[str, object]] = []
        for user in users.all():
            order_count = int(await session.scalar(select(func.count(Order.id)).where(Order.user_id == user.id)) or 0)
            spent = int(
                await session.scalar(
                    select(func.coalesce(func.sum(Order.paid_amount), 0)).where(
                        Order.user_id == user.id,
                        Order.status.in_(["PAID", "SHIPPED", "COMPLETED"]),
                    )
                )
                or 0
            )
            items.append(self._summary(user, order_count, spent))
        return {
            "items": items,
            "meta": {"page": page, "pageSize": page_size, "total": total, "hasNext": page * page_size < total},
        }

    async def get_member(self, session: AsyncSession, user_id: int) -> dict[str, object]:
        """返回会员详情及订单历史。"""
        user = await session.scalar(select(User).where(User.id == user_id).options(selectinload(User.addresses)))
        if user is None:
            raise MembershipError("会员不存在")
        orders = await session.scalars(select(Order).where(Order.user_id == user_id).order_by(Order.created_at.desc()))
        return {
            **self._summary(user, 0, 0),
            "addresses": [
                {
                    "id": address.id,
                    "receiverName": address.receiver_name,
                    "phone": address.phone,
                    "detail": address.detail,
                    "isDefault": address.is_default,
                }
                for address in user.addresses
            ],
            "orders": [
                {"id": order.id, "orderNo": order.order_no, "status": order.status, "totalAmount": order.total_amount}
                for order in orders.all()
            ],
        }

    async def update_tags(self, session: AsyncSession, user_id: int, tags: list[str]) -> dict[str, object]:
        """去重、清理后保存会员标签。"""
        user = await session.get(User, user_id, with_for_update=True)
        if user is None:
            raise MembershipError("会员不存在")
        normalized = list(dict.fromkeys(tag.strip() for tag in tags if tag.strip()))
        user.tags = normalized
        await session.flush()
        return {"userId": user.id, "tags": normalized}

    async def update_level(self, session: AsyncSession, user_id: int, level: str) -> dict[str, object]:
        """更新普通/会员两级等级。"""
        if level not in {"NORMAL", "MEMBER"}:
            raise MembershipError("会员等级无效")
        user = await session.get(User, user_id, with_for_update=True)
        if user is None:
            raise MembershipError("会员不存在")
        user.member_level = level
        await session.flush()
        return {"userId": user.id, "memberLevel": user.member_level}

    @staticmethod
    def _summary(user: User, order_count: int, spent: int) -> dict[str, object]:
        phone = user.phone
        masked_phone = f"{phone[:3]}****{phone[-4:]}" if len(phone) >= 7 else "****"
        return {
            "id": user.id,
            "nickname": user.nickname,
            "avatar": user.avatar,
            "phone": masked_phone,
            "memberLevel": user.member_level,
            "points": user.points,
            "tags": list(user.tags),
            "createdAt": user.created_at.isoformat(),
            "orderCount": order_count,
            "totalSpent": spent,
        }


membership_service = MembershipService()
