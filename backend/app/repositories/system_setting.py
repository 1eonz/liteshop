"""系统设置仓储。"""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.system_setting import SystemSetting


class SystemSettingRepository:
    """在调用方事务中读写全局设置。"""

    async def get(self, session: AsyncSession, key: str) -> dict[str, object] | None:
        """读取指定设置，不存在时返回空值。"""
        setting = await session.scalar(select(SystemSetting).where(SystemSetting.key == key))
        return dict(setting.value) if setting is not None else None

    async def upsert(self, session: AsyncSession, key: str, value: dict[str, object]) -> dict[str, object]:
        """在当前事务内创建或更新设置。"""
        setting = await session.scalar(select(SystemSetting).where(SystemSetting.key == key).with_for_update())
        if setting is None:
            setting = SystemSetting(key=key, value=value, updated_at=datetime.now(UTC))
            session.add(setting)
        else:
            setting.value = value
            setting.updated_at = datetime.now(UTC)
        await session.flush()
        return dict(setting.value)
