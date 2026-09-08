"""用户与后台售后 API。"""

from collections.abc import Awaitable, Callable

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.database import get_session
from ..errors import ApiError
from ..schemas.after_sale import AfterSaleAudit, AfterSaleCreate, AfterSaleReturn
from ..services.admin import AdminPermissionDenied, AdminService
from ..services.after_sale import AfterSaleError, after_sale_response, after_sale_service
from ..services.idempotency import IdempotencyInProgress, IdempotentResult, idempotency_service
from .dependencies import CurrentSubject
from .responses import success

router = APIRouter(prefix="/after-sales", tags=["after-sales"])
admin_router = APIRouter(prefix="/admin/after-sales", tags=["admin-after-sales"])
_session_dependency = Depends(get_session)
_admin_service = AdminService()
AfterSaleWrite = Callable[[AsyncSession], Awaitable[dict[str, object]]]


def _user_id(subject: str) -> int:
    """把 JWT 主体转换为数据库用户主键。"""
    try:
        return int(subject)
    except ValueError as error:
        raise ApiError(status_code=401, code=40101, i18n_key="auth.unauthorized", message="用户身份无效") from error


def _require_database() -> None:
    """售后必须在数据库事务中运行。"""
    if not settings.use_database:
        raise ApiError(status_code=503, code=50001, i18n_key="common.internal_error", message="售后服务需要本地数据库")


async def _write(subject: str, request_id: str, action_type: str, operation: AfterSaleWrite) -> dict[str, object]:
    """统一执行售后幂等写操作。"""
    _require_database()

    async def execute(session: AsyncSession | None) -> IdempotentResult:
        if session is None:
            raise RuntimeError("数据库事务会话未初始化")
        response = await operation(session)
        return IdempotentResult(response, "after_sale", str(response["id"]))

    try:
        return success(
            await idempotency_service.execute(
                user_id=subject,
                request_id=request_id,
                action_type=action_type,
                operation=execute,
            )
        )
    except IdempotencyInProgress as error:
        raise ApiError(
            status_code=429,
            code=42901,
            i18n_key="common.request_in_progress",
            message="请求正在处理中，请稍后再试",
        ) from error
    except AfterSaleError as error:
        raise ApiError(status_code=409, code=40907, i18n_key="after_sale.invalid", message=str(error)) from error


@router.post("")
async def create_after_sale(
    payload: AfterSaleCreate,
    subject: CurrentSubject,
    x_request_id: str = Header(...),
) -> dict[str, object]:
    """创建售后申请。"""
    return await _write(
        subject,
        x_request_id,
        f"after_sale_create:{payload.order_item_id}",
        lambda session: _create_response(session, _user_id(subject), x_request_id, payload),
    )


async def _create_response(
    session: AsyncSession, user_id: int, request_id: str, payload: AfterSaleCreate
) -> dict[str, object]:
    """创建并转换售后响应。"""
    return after_sale_response(await after_sale_service.create(session, user_id, request_id, payload))


@router.get("")
async def list_after_sales(subject: CurrentSubject, session: AsyncSession = _session_dependency) -> dict[str, object]:
    """读取当前用户售后单。"""
    _require_database()
    return success({"items": await after_sale_service.list_for_user(session, _user_id(subject))})


@router.get("/{after_sale_id}")
async def get_after_sale(
    after_sale_id: int, subject: CurrentSubject, session: AsyncSession = _session_dependency
) -> dict[str, object]:
    """读取售后详情。"""
    _require_database()
    try:
        item = await after_sale_service.get_for_user(session, after_sale_id, _user_id(subject))
        return success(after_sale_response(item))
    except AfterSaleError as error:
        raise ApiError(status_code=404, code=40401, i18n_key="common.not_found", message=str(error)) from error


@router.put("/{after_sale_id}/return")
async def submit_after_sale_return(
    after_sale_id: int,
    payload: AfterSaleReturn,
    subject: CurrentSubject,
    x_request_id: str = Header(...),
) -> dict[str, object]:
    """提交退货物流。"""
    return await _write(
        subject,
        x_request_id,
        f"after_sale_return:{after_sale_id}",
        lambda session: _return_response(session, after_sale_id, _user_id(subject), payload.tracking_no),
    )


async def _return_response(
    session: AsyncSession, after_sale_id: int, user_id: int, tracking_no: str
) -> dict[str, object]:
    """提交物流并转换响应。"""
    return after_sale_response(await after_sale_service.submit_return(session, after_sale_id, user_id, tracking_no))


async def _admin_permission(session: AsyncSession, subject: str, permission: str) -> None:
    """校验售后后台权限。"""
    try:
        await _admin_service.require_permission(session, subject, permission)
    except AdminPermissionDenied as error:
        raise ApiError(status_code=403, code=40301, i18n_key="common.forbidden", message=str(error)) from error


@admin_router.get("")
async def list_admin_after_sales(
    subject: CurrentSubject,
    status: str | None = Query(None),
    session: AsyncSession = _session_dependency,
) -> dict[str, object]:
    """后台读取售后列表。"""
    _require_database()
    await _admin_permission(session, subject, "review.read")
    items = await after_sale_service.repository.list_all(session, status)
    return success({"items": [after_sale_response(item) for item in items]})


@admin_router.put("/{after_sale_id}/audit")
async def audit_after_sale(
    after_sale_id: int,
    payload: AfterSaleAudit,
    subject: CurrentSubject,
    x_request_id: str = Header(...),
) -> dict[str, object]:
    """后台审核售后申请。"""

    async def operation(session: AsyncSession) -> dict[str, object]:
        await _admin_permission(session, subject, "review.write")
        item = await after_sale_service.audit(session, after_sale_id, payload.approved, payload.reason)
        response = after_sale_response(item)
        await _admin_service.audit(
            session,
            user_id=subject,
            resource_type="AFTER_SALE",
            resource_id=after_sale_id,
            action="APPROVE" if payload.approved else "REJECT",
            request_id=x_request_id,
            before_data=None,
            after_data=response,
        )
        return response

    return await _write(subject, x_request_id, f"after_sale_audit:{after_sale_id}", operation)


@admin_router.put("/{after_sale_id}/complete")
async def complete_after_sale(
    after_sale_id: int,
    subject: CurrentSubject,
    x_request_id: str = Header(...),
) -> dict[str, object]:
    """后台确认退货并完成退款或换货入库。"""

    async def operation(session: AsyncSession) -> dict[str, object]:
        await _admin_permission(session, subject, "review.write")
        response = after_sale_response(await after_sale_service.complete_refund(session, after_sale_id))
        await _admin_service.audit(
            session,
            user_id=subject,
            resource_type="AFTER_SALE",
            resource_id=after_sale_id,
            action="COMPLETE",
            request_id=x_request_id,
            before_data=None,
            after_data=response,
        )
        return response

    return await _write(subject, x_request_id, f"after_sale_complete:{after_sale_id}", operation)
