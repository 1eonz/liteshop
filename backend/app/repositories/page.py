"""低代码页面仓储。"""

from typing import cast

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.page import PageConversionEvent, PageVariant, StorePage


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

    async def list_pages(self, session: AsyncSession) -> list[StorePage]:
        """按更新时间倒序读取页面。"""
        result = await session.scalars(select(StorePage).order_by(StorePage.updated_at.desc(), StorePage.id))
        return list(result.all())

    async def get_by_slug(self, session: AsyncSession, slug: str) -> StorePage | None:
        """按路由 slug 查询页面。"""
        return cast(StorePage | None, await session.scalar(select(StorePage).where(StorePage.slug == slug)))

    async def delete(self, session: AsyncSession, page_id: int) -> bool:
        """删除页面及级联的变体和事件。"""
        page = await self.get(session, page_id, for_update=True)
        if page is None:
            return False
        await session.delete(page)
        return True

    async def list_variants(self, session: AsyncSession, page_id: int) -> list[PageVariant]:
        """读取页面变体。"""
        result = await session.scalars(
            select(PageVariant).where(PageVariant.page_id == page_id).order_by(PageVariant.key)
        )
        return list(result.all())

    async def get_variant(
        self, session: AsyncSession, page_id: int, key: str, *, for_update: bool = False
    ) -> PageVariant | None:
        """按页面和变体键查询变体。"""
        statement = select(PageVariant).where(PageVariant.page_id == page_id, PageVariant.key == key)
        if for_update:
            statement = statement.with_for_update()
        return cast(PageVariant | None, await session.scalar(statement))

    async def add_variant(self, session: AsyncSession, variant: PageVariant) -> PageVariant:
        """新增变体。"""
        session.add(variant)
        await session.flush()
        return variant

    async def add_conversion_event(self, session: AsyncSession, event: PageConversionEvent) -> PageConversionEvent:
        """记录页面转化事件。"""
        session.add(event)
        await session.flush()
        return event

    async def clear_home(self, session: AsyncSession) -> None:
        """清除全部首页标记。"""
        await session.execute(update(StorePage).values(is_home=False))

    async def flush(self, session: AsyncSession) -> None:
        """刷新页面变更，不提交外层事务。"""
        await session.flush()
