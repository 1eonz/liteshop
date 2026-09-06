"""运费模板数据访问。"""

from datetime import UTC, datetime
from typing import cast

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.freight import FreightTemplate, FreightTemplateItem


class FreightRepository:
    """封装运费模板及计费项的持久化操作。"""

    async def list_templates(self, session: AsyncSession) -> list[FreightTemplate]:
        """读取模板和计费项，避免服务层触发异步懒加载。"""
        result = await session.scalars(
            select(FreightTemplate).options(selectinload(FreightTemplate.items)).order_by(FreightTemplate.id)
        )
        return list(result.unique().all())

    async def get_template(
        self, session: AsyncSession, template_id: int, *, for_update: bool = False
    ) -> FreightTemplate | None:
        """按主键读取模板，可选加行锁。"""
        statement = (
            select(FreightTemplate)
            .where(FreightTemplate.id == template_id)
            .options(selectinload(FreightTemplate.items))
        )
        if for_update:
            statement = statement.with_for_update()
        return cast(FreightTemplate | None, await session.scalar(statement))

    async def get_default_template(self, session: AsyncSession) -> FreightTemplate | None:
        """读取启用的默认模板。"""
        result = await session.scalars(
            select(FreightTemplate)
            .where(FreightTemplate.enabled.is_(True), FreightTemplate.is_default.is_(True))
            .options(selectinload(FreightTemplate.items))
            .order_by(FreightTemplate.id)
            .limit(1)
        )
        return result.first()

    async def clear_default(self, session: AsyncSession, *, except_id: int | None = None) -> None:
        """清除其他默认模板，保证同一时刻只有一个默认模板。"""
        statement = update(FreightTemplate).values(is_default=False, updated_at=datetime.now(UTC))
        if except_id is not None:
            statement = statement.where(FreightTemplate.id != except_id)
        await session.execute(statement)

    async def add_template(self, session: AsyncSession, template: FreightTemplate) -> FreightTemplate:
        """新增模板。"""
        session.add(template)
        await session.flush()
        return template

    async def add_item(self, session: AsyncSession, item: FreightTemplateItem) -> FreightTemplateItem:
        """新增模板计费项。"""
        session.add(item)
        await session.flush()
        return item

    async def get_item(self, session: AsyncSession, template_id: int, item_id: int) -> FreightTemplateItem | None:
        """按模板和计费项主键读取项并加锁。"""
        return cast(
            FreightTemplateItem | None,
            await session.scalar(
                select(FreightTemplateItem)
                .where(FreightTemplateItem.id == item_id, FreightTemplateItem.template_id == template_id)
                .with_for_update()
            ),
        )

    async def delete_item(self, session: AsyncSession, item: FreightTemplateItem) -> None:
        """删除模板计费项。"""
        await session.delete(item)
        await session.flush()
