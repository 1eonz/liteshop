"""管理后台服务的公共依赖、权限校验与审计能力。"""

from datetime import UTC, datetime

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.operation_log import OperationLog
from ..repositories.admin import AdminRepository
from ..repositories.inventory import InventoryRepository
from ..repositories.operation_log import OperationLogRepository
from .freight import FreightService
from .order_workflow import OrderWorkflow
from .product_catalog import ProductCatalogService


class AdminPermissionDenied(PermissionError):
    """管理员缺少所需权限。"""


class AdminServiceCore:
    """管理后台服务的公共上下文。"""

    catalog: ProductCatalogService
    orders: OrderWorkflow
    inventory: InventoryRepository
    repository: AdminRepository
    freight: FreightService

    def __init__(self) -> None:
        self.catalog = ProductCatalogService()
        self.orders = OrderWorkflow()
        self.inventory = InventoryRepository()
        self.repository = AdminRepository()
        self.freight = FreightService()

    async def require_permission(self, session: AsyncSession, subject: str, permission: str) -> None:
        """按数据库 RBAC 校验权限，不提供硬编码管理员后门。"""
        try:
            user_id = int(subject)
        except ValueError as exc:
            raise AdminPermissionDenied("无效管理员身份") from exc
        if not await self.repository.has_permission(session, user_id, permission):
            raise AdminPermissionDenied("缺少操作权限")

    @staticmethod
    async def audit(
        session: AsyncSession,
        *,
        user_id: str,
        resource_type: str,
        resource_id: int | None,
        action: str,
        request_id: str,
        before_data: dict[str, object] | None,
        after_data: dict[str, object] | None,
    ) -> None:
        """在同一业务事务中写入结构化操作日志。"""
        request_context = structlog.contextvars.get_contextvars()
        await OperationLogRepository(session).append(
            OperationLog(
                admin_id=int(user_id) if user_id.isdigit() else None,
                resource_type=resource_type,
                resource_id=resource_id,
                action=action,
                request_id=request_id,
                before_data=before_data,
                after_data=after_data,
                ip=str(request_context.get("ip", "")),
                user_agent=str(request_context.get("user_agent", "")),
                created_at=datetime.now(UTC),
            )
        )
