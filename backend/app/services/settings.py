"""商城设置领域服务。"""

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..repositories.system_setting import SystemSettingRepository


class SettingsService:
    """统一编排主题设置的内存开发实现和数据库实现。"""

    def __init__(self, repository: SystemSettingRepository | None = None) -> None:
        self.repository = repository or SystemSettingRepository()
        self._theme: dict[str, object] = {
            "primaryColor": "#ff6b6b",
            "navigationStyle": "glass",
            "tabbarStyle": "gallery",
        }

    async def get_theme(self, session: AsyncSession) -> dict[str, object]:
        """读取主题配置，开发模式使用进程内默认值。"""
        if settings.use_database:
            stored = await self.repository.get(session, "theme")
            if stored is not None:
                return stored
        return dict(self._theme)

    async def update_theme(
        self,
        session: AsyncSession | None,
        values: dict[str, object],
    ) -> dict[str, object]:
        """更新主题配置，数据库模式由调用方事务提交。"""
        updated: dict[str, object] = {key: str(value) for key, value in values.items()}
        if settings.use_database:
            if session is None:
                raise RuntimeError("数据库事务会话未初始化")
            return await self.repository.upsert(session, "theme", updated)
        self._theme.update(updated)
        return dict(self._theme)


settings_service = SettingsService()
