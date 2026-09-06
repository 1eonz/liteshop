"""站内通知仓储。"""

from datetime import UTC, datetime
from typing import cast

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.notification import Notification


class NotificationRepository:
    """封装通知查询和已读更新。"""

    async def list_for_user(self, session: AsyncSession, user_id: int, limit: int = 50) -> list[Notification]:
        """按时间倒序读取通知。"""
        result = await session.scalars(
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc(), Notification.id.desc())
            .limit(limit)
        )
        return list(result.all())

    async def get_for_user(self, session: AsyncSession, notification_id: int, user_id: int) -> Notification | None:
        """锁定属于用户的通知。"""
        return cast(
            Notification | None,
            await session.scalar(
                select(Notification)
                .where(Notification.id == notification_id, Notification.user_id == user_id)
                .with_for_update()
            ),
        )

    async def mark_all_read(self, session: AsyncSession, user_id: int) -> int:
        """批量标记用户所有未读通知。"""
        result = await session.execute(
            update(Notification)
            .where(Notification.user_id == user_id, Notification.read_at.is_(None))
            .values(read_at=datetime.now(UTC))
        )
        return int(getattr(result, "rowcount", 0) or 0)

    async def flush(self, session: AsyncSession) -> None:
        """刷新单条已读变更，不提交外层事务。"""
        await session.flush()

    async def unread_count(self, session: AsyncSession, user_id: int) -> int:
        """统计未读数量。"""
        return int(
            await session.scalar(
                select(func.count(Notification.id)).where(
                    Notification.user_id == user_id,
                    Notification.read_at.is_(None),
                )
            )
            or 0
        )
