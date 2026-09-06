"""官网导航仓储。"""

from datetime import UTC, datetime
from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.navigation import NavigationItem


class NavigationRepository:
    """封装官网导航的查询与写入。"""

    async def list_enabled(self, session: AsyncSession, location: str | None = None) -> list[NavigationItem]:
        """按位置读取启用的导航项。"""
        statement = (
            select(NavigationItem)
            .where(NavigationItem.enabled.is_(True))
            .order_by(NavigationItem.sort_order, NavigationItem.id)
        )
        if location is not None:
            statement = statement.where(NavigationItem.location == location)
        result = await session.scalars(statement)
        return list(result.all())

    async def list_all(self, session: AsyncSession) -> list[NavigationItem]:
        """读取全部导航项供后台管理。"""
        result = await session.scalars(
            select(NavigationItem).order_by(NavigationItem.location, NavigationItem.sort_order, NavigationItem.id)
        )
        return list(result.all())

    async def get_for_update(self, session: AsyncSession, item_id: int) -> NavigationItem | None:
        """锁定导航项。"""
        return cast(NavigationItem | None, await session.get(NavigationItem, item_id, with_for_update=True))

    async def create(self, session: AsyncSession, values: dict[str, object]) -> NavigationItem:
        """创建导航项，不提交事务。"""
        now = datetime.now(UTC)
        item = NavigationItem(**values, created_at=now, updated_at=now)
        session.add(item)
        await session.flush()
        return item

    async def delete(self, session: AsyncSession, item_id: int) -> bool:
        """删除导航项。"""
        item = await session.get(NavigationItem, item_id)
        if item is None:
            return False
        await session.delete(item)
        return True

    async def flush(self, session: AsyncSession) -> None:
        """刷新导航变更。"""
        await session.flush()
