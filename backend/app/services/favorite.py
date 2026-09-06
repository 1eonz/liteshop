"""商品收藏服务。"""

from sqlalchemy.ext.asyncio import AsyncSession

from ..repositories.favorite import FavoriteRepository


class FavoriteService:
    """提供服务端收藏查询和幂等切换。"""

    def __init__(self, repository: FavoriteRepository | None = None) -> None:
        self.repository = repository or FavoriteRepository()

    async def list_ids(self, session: AsyncSession, user_id: int) -> list[int]:
        """返回用户收藏的商品 ID。"""
        return await self.repository.list_product_ids(session, user_id)

    async def toggle(self, session: AsyncSession, user_id: int, product_id: int) -> dict[str, object]:
        """在事务内切换收藏关系。"""
        favorite = await self.repository.get_for_update(session, user_id, product_id)
        if favorite is None:
            await self.repository.add(session, user_id, product_id)
            return {"productId": product_id, "favorited": True}
        await self.repository.delete(session, favorite)
        return {"productId": product_id, "favorited": False}


favorite_service = FavoriteService()
