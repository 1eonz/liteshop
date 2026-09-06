"""站内通知业务服务。"""

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from ..repositories.notification import NotificationRepository


class NotificationError(ValueError):
    """通知业务错误。"""


class NotificationService:
    """编排通知读取和幂等已读操作。"""

    def __init__(self, repository: NotificationRepository | None = None) -> None:
        self.repository = repository or NotificationRepository()

    async def list_for_user(self, session: AsyncSession, user_id: int) -> dict[str, object]:
        """返回通知列表和未读计数。"""
        notifications = await self.repository.list_for_user(session, user_id)
        unread_count = await self.repository.unread_count(session, user_id)
        return {
            "items": [
                {
                    "id": notification.id,
                    "type": notification.notification_type,
                    "title": notification.title,
                    "content": notification.content,
                    "readAt": notification.read_at.isoformat() if notification.read_at else None,
                    "createdAt": notification.created_at.isoformat(),
                }
                for notification in notifications
            ],
            "unreadCount": unread_count,
        }

    async def mark_read(self, session: AsyncSession, user_id: int, notification_id: int) -> dict[str, object]:
        """标记单条通知已读，重复调用保持幂等。"""
        notification = await self.repository.get_for_user(session, notification_id, user_id)
        if notification is None:
            raise NotificationError("通知不存在")
        if notification.read_at is None:
            notification.read_at = datetime.now(UTC)
            await session.flush()
        return {"id": notification.id, "readAt": notification.read_at.isoformat()}

    async def mark_all_read(self, session: AsyncSession, user_id: int) -> dict[str, object]:
        """标记全部通知已读。"""
        count = await self.repository.mark_all_read(session, user_id)
        return {"updated": count}


notification_service = NotificationService()
