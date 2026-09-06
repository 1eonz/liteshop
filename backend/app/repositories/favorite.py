"""商品收藏仓储。"""

from datetime import UTC, datetime
from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.favorite import Favorite


class FavoriteRepository:
    """封装收藏关系的查询和写入。"""

    async def list_product_ids(self, session: AsyncSession, user_id: int) -> list[int]:
        """按最近收藏时间倒序返回商品 ID。"""
        values = await session.scalars(
            select(Favorite.product_id).where(Favorite.user_id == user_id).order_by(Favorite.created_at.desc())
        )
        return list(values.all())

    async def get_for_update(self, session: AsyncSession, user_id: int, product_id: int) -> Favorite | None:
        """锁定指定用户的收藏关系，保证切换操作串行化。"""
        return cast(
            Favorite | None,
            await session.scalar(
                select(Favorite).where(Favorite.user_id == user_id, Favorite.product_id == product_id).with_for_update()
            ),
        )

    async def add(self, session: AsyncSession, user_id: int, product_id: int) -> Favorite:
        """新增收藏关系，不提交外层事务。"""
        favorite = Favorite(user_id=user_id, product_id=product_id, created_at=datetime.now(UTC))
        session.add(favorite)
        await session.flush()
        return favorite

    async def delete(self, session: AsyncSession, favorite: Favorite) -> None:
        """删除收藏关系，不提交外层事务。"""
        await session.delete(favorite)
        await session.flush()
