"""商品收藏服务。"""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.favorite import Favorite


class FavoriteService:
    """提供服务端收藏查询和幂等切换。"""

    async def list_ids(self, session: AsyncSession, user_id: int) -> list[int]:
        """返回用户收藏的商品 ID。"""
        values = await session.scalars(
            select(Favorite.product_id).where(Favorite.user_id == user_id).order_by(Favorite.created_at.desc())
        )
        return list(values.all())

    async def toggle(self, session: AsyncSession, user_id: int, product_id: int) -> dict[str, object]:
        """在事务内切换收藏关系。"""
        favorite = await session.scalar(
            select(Favorite).where(Favorite.user_id == user_id, Favorite.product_id == product_id).with_for_update()
        )
        if favorite is None:
            session.add(Favorite(user_id=user_id, product_id=product_id, created_at=datetime.now(UTC)))
            await session.flush()
            return {"productId": product_id, "favorited": True}
        await session.delete(favorite)
        await session.flush()
        return {"productId": product_id, "favorited": False}


favorite_service = FavoriteService()
