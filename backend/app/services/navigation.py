"""官网导航领域服务。"""

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from ..models.navigation import NavigationItem
from ..repositories.navigation import NavigationRepository
from ..schemas.navigation import NavigationItemCreate, NavigationItemUpdate


class NavigationError(ValueError):
    """导航项不存在或配置不合法。"""


class NavigationService:
    """编排导航读取、创建、更新和删除。"""

    def __init__(self, repository: NavigationRepository | None = None) -> None:
        self.repository = repository or NavigationRepository()

    @staticmethod
    def response(item: NavigationItem) -> dict[str, object]:
        """将 ORM 模型映射为 API 响应。"""
        return {
            "id": item.id,
            "label": item.label,
            "href": item.href,
            "location": item.location,
            "kind": item.kind,
            "openNewTab": item.open_new_tab,
            "sortOrder": item.sort_order,
            "enabled": item.enabled,
        }

    async def list_enabled(self, session: AsyncSession) -> list[dict[str, object]]:
        """读取全部启用导航。"""
        return [self.response(item) for item in await self.repository.list_enabled(session)]

    async def list_admin(self, session: AsyncSession) -> list[dict[str, object]]:
        """读取后台导航配置。"""
        return [self.response(item) for item in await self.repository.list_all(session)]

    async def create(self, session: AsyncSession, payload: NavigationItemCreate) -> dict[str, object]:
        """创建导航项。"""
        item = await self.repository.create(session, payload.model_dump(by_alias=False))
        return self.response(item)

    async def update(self, session: AsyncSession, item_id: int, payload: NavigationItemUpdate) -> dict[str, object]:
        """更新导航项。"""
        item = await self.repository.get_for_update(session, item_id)
        if item is None:
            raise NavigationError("导航项不存在")
        for key, value in payload.model_dump(by_alias=False).items():
            setattr(item, key, value)
        item.updated_at = datetime.now(UTC)
        await self.repository.flush(session)
        return self.response(item)

    async def remove(self, session: AsyncSession, item_id: int) -> dict[str, object]:
        """删除导航项。"""
        if not await self.repository.delete(session, item_id):
            raise NavigationError("导航项不存在")
        return {"deleted": True, "id": item_id}


navigation_service = NavigationService()
