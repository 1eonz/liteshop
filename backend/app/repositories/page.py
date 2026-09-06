"""低代码页面仓储。"""

from typing import cast

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.page import StorePage


class PageRepository:
    """封装页面 Schema 的数据库访问和写锁。"""

    async def get(self, session: AsyncSession, page_id: int, *, for_update: bool = False) -> StorePage | None:
        """读取页面，可选行锁。"""
        statement = select(StorePage).where(StorePage.id == page_id)
        if for_update:
            statement = statement.with_for_update()
        return cast(StorePage | None, await session.scalar(statement))

    async def add(self, session: AsyncSession, page: StorePage) -> StorePage:
        """新增页面，不提交外层事务。"""
        session.add(page)
        await session.flush()
        return page

    async def clear_home(self, session: AsyncSession) -> None:
        """清除全部首页标记。"""
        await session.execute(update(StorePage).values(is_home=False))

    async def flush(self, session: AsyncSession) -> None:
        """刷新页面变更，不提交外层事务。"""
        await session.flush()
