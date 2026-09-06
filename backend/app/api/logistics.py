"""物流轨迹 API。"""

from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.database import get_session
from ..errors import ApiError
from ..schemas.logistics import TrackingEventCreate
from ..services.admin import AdminPermissionDenied, AdminService
from ..services.idempotency import IdempotencyInProgress, IdempotentResult, idempotency_service
from ..services.logistics import LogisticsError, logistics_service
from .dependencies import CurrentSubject
from .responses import success

router = APIRouter(prefix="/orders", tags=["logistics"])
_session_dependency = Depends(get_session)
_admin_service = AdminService()


@router.get("/{order_id}/tracking")
async def list_tracking(
    order_id: int, subject: CurrentSubject, session: AsyncSession = _session_dependency
) -> dict[str, object]:
    """读取订单物流轨迹。"""
    if not settings.use_database:
        return success({"items": []})
    try:
        order = await logistics_service.orders.get(session, order_id)
        if str(order.user_id) != subject:
            raise LogisticsError("订单不存在")
        return success({"items": await logistics_service.list_events(session, order_id)})
    except (LogisticsError, KeyError) as error:
        raise ApiError(status_code=404, code=40401, i18n_key="common.not_found", message="订单不存在") from error


@router.post("/{order_id}/tracking", status_code=201)
async def add_tracking(
    order_id: int,
    payload: TrackingEventCreate,
    subject: CurrentSubject,
    x_request_id: str = Header(...),
) -> dict[str, object]:
    """幂等写入订单物流节点，仅后台管理员可写。"""
    if not settings.use_database:
        raise ApiError(status_code=503, code=50001, i18n_key="common.internal_error", message="物流轨迹需要本地数据库")

    async def operation(session: AsyncSession | None) -> IdempotentResult:
        if session is None:
            raise RuntimeError("数据库事务会话未初始化")
        try:
            await _admin_service.require_permission(session, subject, "order.write")
        except AdminPermissionDenied as error:
            raise ApiError(status_code=403, code=40301, i18n_key="common.forbidden", message=str(error)) from error
        response = await logistics_service.add_event(session, order_id, payload)
        return IdempotentResult(response, "tracking_event", str(response["id"]))

    try:
        result = await idempotency_service.execute(
            user_id=subject, request_id=x_request_id, action_type=f"tracking_event:{order_id}", operation=operation
        )
        return success(result)
    except (LogisticsError, KeyError) as error:
        raise ApiError(status_code=404, code=40401, i18n_key="common.not_found", message="订单不存在") from error
    except IdempotencyInProgress as error:
        raise ApiError(
            status_code=429, code=42901, i18n_key="common.request_in_progress", message="请求正在处理中，请稍后再试"
        ) from error
