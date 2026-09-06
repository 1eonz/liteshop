"""后台操作日志仓储。"""

from sqlalchemy.ext.asyncio import AsyncSession

from ..models.operation_log import OperationLog


class OperationLogRepository:
    """在调用方事务中持久化操作日志。"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def append(self, entry: OperationLog) -> OperationLog:
        """追加日志实体，不自行提交外层事务。"""
        self.session.add(entry)
        await self.session.flush()
        return entry
