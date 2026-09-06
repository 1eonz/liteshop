"""站内通知 API。"""

from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.database import get_session
from ..errors import ApiError
from ..services.idempotency import IdempotencyInProgress, IdempotentResult, idempotency_service
from ..services.notification import NotificationError, notification_service
from .dependencies import CurrentSubject
from .responses import success

router = APIRouter(prefix="/notifications", tags=["notifications"])
_session_dependency = Depends(get_session)


def _user_id(subject: str) -> int:
    """转换数据库用户主键。"""
    try:
        return int(subject)
    except ValueError as error:
        raise ApiError(status_code=401, code=40101, i18n_key="auth.unauthorized", message="用户身份无效") from error


@router.get("")
async def list_notifications(
    subject: CurrentSubject,
    session: AsyncSession = _session_dependency,
) -> dict[str, object]:
    """读取当前用户通知。"""
    if not settings.use_database:
        return success({"items": [], "unreadCount": 0})
    return success(await notification_service.list_for_user(session, _user_id(subject)))


@router.put("/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    subject: CurrentSubject,
    x_request_id: str = Header(...),
) -> dict[str, object]:
    """幂等标记单条通知已读。"""
    if not settings.use_database:
        return success({"id": notification_id, "readAt": None})

    async def operation(session: AsyncSession | None) -> IdempotentResult:
        if session is None:
            raise RuntimeError("数据库事务会话未初始化")
        response = await notification_service.mark_read(session, _user_id(subject), notification_id)
        return IdempotentResult(response, "notification", str(notification_id))

    try:
        result = await idempotency_service.execute(
            user_id=subject,
            request_id=x_request_id,
            action_type=f"notification_read:{notification_id}",
            operation=operation,
        )
        return success(result)
    except NotificationError as error:
        raise ApiError(status_code=404, code=40401, i18n_key="common.not_found", message=str(error)) from error
    except IdempotencyInProgress as error:
        raise ApiError(
            status_code=429,
            code=42901,
            i18n_key="common.request_in_progress",
            message="请求正在处理中，请稍后再试",
        ) from error


@router.put("/read-all")
async def mark_all_notifications_read(
    subject: CurrentSubject,
    x_request_id: str = Header(...),
) -> dict[str, object]:
    """幂等标记当前用户全部通知已读。"""
    if not settings.use_database:
        return success({"updated": 0})

    async def operation(session: AsyncSession | None) -> IdempotentResult:
        if session is None:
            raise RuntimeError("数据库事务会话未初始化")
        response = await notification_service.mark_all_read(session, _user_id(subject))
        return IdempotentResult(response, "notification", "all")

    try:
        result = await idempotency_service.execute(
            user_id=subject,
            request_id=x_request_id,
            action_type="notification_read_all",
            operation=operation,
        )
        return success(result)
    except IdempotencyInProgress as error:
        raise ApiError(
            status_code=429,
            code=42901,
            i18n_key="common.request_in_progress",
            message="请求正在处理中，请稍后再试",
        ) from error
