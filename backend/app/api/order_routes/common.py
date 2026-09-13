"""订单 API 路由共享的依赖、工作流和错误转换辅助函数。"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_session
from ...core.runtime import order_service, payment_service
from ...errors import ApiError
from ...services.idempotency import idempotency_service
from ...services.order_workflow import OrderWorkflow
from ...services.refund import RefundService

workflow = OrderWorkflow()
refund_service = RefundService()
session_dependency = Depends(get_session)


def require_session(session: AsyncSession | None) -> AsyncSession:
    """数据库模式下拒绝缺失事务会话。"""
    if session is None:
        raise RuntimeError("数据库事务会话未初始化")
    return session


def database_user_id(subject: str) -> int:
    """把 JWT 主体转换为数据库用户主键。"""
    try:
        return int(subject)
    except ValueError as exc:
        raise ApiError(
            status_code=401,
            code=40101,
            i18n_key="auth.unauthorized",
            message="用户身份无效",
        ) from exc


__all__ = [
    "database_user_id",
    "idempotency_service",
    "order_service",
    "payment_service",
    "refund_service",
    "require_session",
    "session_dependency",
    "workflow",
]
