"""管理后台路由共享的权限、幂等与错误映射。"""

from collections.abc import Awaitable, Callable

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import settings
from ...core.database import get_session
from ...errors import ApiError
from ...services.admin import AdminPermissionDenied, AdminService
from ...services.idempotency import IdempotencyInProgress, IdempotentResult, idempotency_service
from ...services.order_workflow import OrderWorkflowError
from ..dependencies import CurrentSubject
from ..responses import success

__all__ = ["admin_service", "authorize_read", "execute_write", "require_database", "session_dependency"]

admin_service = AdminService()
session_dependency = Depends(get_session)
AdminWrite = Callable[[AsyncSession, str, str], Awaitable[dict[str, object]]]


def require_database() -> None:
    """后台真实写操作必须连接本地数据库。"""
    if not settings.use_database:
        raise ApiError(
            status_code=503,
            code=50001,
            i18n_key="common.internal_error",
            message="后台写操作需要本地数据库",
        )


async def authorize_read(session: AsyncSession, subject: CurrentSubject, permission: str) -> str:
    """验证后台读权限并返回主体。"""
    if settings.use_database:
        try:
            await admin_service.require_permission(session, subject, permission)
        except AdminPermissionDenied as exc:
            raise ApiError(
                status_code=403,
                code=40301,
                i18n_key="common.forbidden",
                message=str(exc),
            ) from exc
    return subject


async def execute_write(
    *,
    subject: str,
    request_id: str,
    action_type: str,
    permission: str,
    resource_type: str,
    operation: AdminWrite,
) -> dict[str, object]:
    """统一执行后台权限校验、幂等事务和错误映射。"""
    require_database()

    async def idempotent_operation(session: AsyncSession | None) -> IdempotentResult:
        if session is None:
            raise RuntimeError("数据库事务会话未初始化")
        await admin_service.require_permission(session, subject, permission)
        response = await operation(session, subject, request_id)
        resource_id = str(response.get("id", response.get("orderId", response.get("skuId", ""))))
        return IdempotentResult(response, resource_type, resource_id)

    try:
        result = await idempotency_service.execute(
            user_id=subject,
            request_id=request_id,
            action_type=action_type,
            operation=idempotent_operation,
        )
        return success(result)
    except IdempotencyInProgress as exc:
        raise ApiError(
            status_code=429,
            code=42901,
            i18n_key="common.request_in_progress",
            message="请求正在处理中，请稍后再试",
        ) from exc
    except AdminPermissionDenied as exc:
        raise ApiError(
            status_code=403,
            code=40301,
            i18n_key="common.forbidden",
            message=str(exc),
        ) from exc
    except (OrderWorkflowError, KeyError, ValueError) as exc:
        raise ApiError(
            status_code=409,
            code=40901,
            i18n_key="order.invalid_transition",
            message=str(exc),
        ) from exc
