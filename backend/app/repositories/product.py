"""商品仓储：只负责 SQLAlchemy 持久化访问。"""

from typing import cast

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.elements import ColumnElement

from ..errors.domain import ProductNotFound
from ..models.product import Category, ProductSpec, Sku, Spu


class ProductRepository:
    """封装商品、分类和 SKU 数据访问。"""

    async def get_sku_for_update(self, session: AsyncSession, sku_id: int) -> Sku | None:
        """锁定 SKU 行，供下单库存和价格校验使用。"""
        return cast(
            Sku | None,
            await session.scalar(
                select(Sku).where(Sku.id == sku_id).options(selectinload(Sku.spu)).with_for_update(of=Sku)
            ),
        )

    async def get_sku(self, session: AsyncSession, sku_id: int) -> Sku | None:
        """读取 SKU 及其商品状态，不获取写锁。"""
        return cast(
            Sku | None,
            await session.scalar(select(Sku).where(Sku.id == sku_id).options(selectinload(Sku.spu))),
        )

    async def list_spus(
        self,
        session: AsyncSession,
        offset: int,
        limit: int,
        *,
        keyword: str | None = None,
        include_off_shelf: bool = False,
    ) -> tuple[list[Spu], int]:
        """分页读取商品，并同时返回总数。"""
        conditions: list[ColumnElement[bool]] = [Spu.deleted_at.is_(None)]
        if not include_off_shelf:
            conditions.append(Spu.status == "ON_SHELF")
        if keyword:
            conditions.append(Spu.name.ilike(f"%{keyword}%"))
        statement = (
            select(Spu)
            .where(*conditions)
            .options(selectinload(Spu.skus), selectinload(Spu.specs).selectinload(ProductSpec.values))
            .order_by(Spu.sort_order, Spu.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await session.scalars(statement)
        total = await session.scalar(select(func.count(Spu.id)).where(*conditions))
        return list(result.unique().all()), int(total or 0)

    async def get_spu(self, session: AsyncSession, product_id: int, *, for_update: bool = False) -> Spu:
        """读取商品及其 SKU，可选行锁。"""
        statement = (
            select(Spu)
            .where(Spu.id == product_id, Spu.deleted_at.is_(None))
            .options(selectinload(Spu.skus), selectinload(Spu.specs).selectinload(ProductSpec.values))
        )
        if for_update:
            statement = statement.with_for_update()
        product = cast(Spu | None, await session.scalar(statement))
        if product is None:
            raise ProductNotFound(product_id)
        return product

    async def list_categories(self, session: AsyncSession) -> list[Category]:
        """按层级和排序读取启用分类。"""
        result = await session.scalars(
            select(Category)
            .where(Category.is_active.is_(True))
            .order_by(Category.parent_id.nullsfirst(), Category.sort_order, Category.id)
        )
        return list(result.all())

    async def add_category(self, session: AsyncSession, category: Category) -> Category:
        """新增分类，不提交外层事务。"""
        session.add(category)
        await session.flush()
        return category

    async def get_category(self, session: AsyncSession, category_id: int, *, for_update: bool = False) -> Category:
        """读取分类，可选行锁。"""
        statement = select(Category).where(Category.id == category_id)
        if for_update:
            statement = statement.with_for_update()
        category = cast(Category | None, await session.scalar(statement))
        if category is None:
            raise KeyError(category_id)
        return category

    async def add_product(self, session: AsyncSession, product: Spu) -> Spu:
        """新增商品聚合，不提交外层事务。"""
        session.add(product)
        await session.flush()
        return product

    async def flush(self, session: AsyncSession) -> None:
        """刷新仓储内待写变更。"""
        await session.flush()
