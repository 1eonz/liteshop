"""官网联系表单 API。"""

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.database import get_session
from ..errors import ApiError
from ..schemas.contact import ContactFormCreate, ContactFormStatusUpdate
from ..services.admin import AdminPermissionDenied, AdminService
from ..services.contact import ContactFormError, contact_service
from ..services.idempotency import IdempotencyInProgress, IdempotentResult, idempotency_service
from .dependencies import CurrentSubject
from .responses import success

router = APIRouter(prefix="/contact", tags=["contact"])
admin_router = APIRouter(prefix="/admin/contact", tags=["admin-contact"])
_session_dependency = Depends(get_session)
_admin_service = AdminService()


@router.post("/forms", status_code=202)
async def create_contact_form(payload: ContactFormCreate, x_request_id: str = Header(...)) -> dict[str, object]:
    """受理官网联系表单，重复请求返回第一次结果。"""

    async def operation(session: AsyncSession | None) -> IdempotentResult:
        result = await contact_service.create(session, payload.model_dump())
        return IdempotentResult(result.as_dict(), "form_submission", str(result.id))

    try:
        result = await idempotency_service.execute(
            user_id="anonymous",
            request_id=x_request_id,
            action_type="contact_form_create",
            operation=operation,
        )
        return success(result)
    except ContactFormError as error:
        raise ApiError(status_code=422, code=42210, i18n_key="contact.invalid_form", message=str(error)) from error
    except IdempotencyInProgress as error:
        raise ApiError(
            status_code=429, code=42901, i18n_key="common.request_in_progress", message="请求正在处理中，请稍后再试"
        ) from error


async def _require_admin(session: AsyncSession, subject: str, permission: str) -> None:
    """校验联系表单后台权限。"""
    if not settings.use_database:
        return
    try:
        await _admin_service.require_permission(session, subject, permission)
    except AdminPermissionDenied as error:
        raise ApiError(status_code=403, code=40301, i18n_key="common.forbidden", message=str(error)) from error


@admin_router.get("/forms")
async def list_contact_forms(
    subject: CurrentSubject,
    status: str | None = Query(default=None, pattern="^(NEW|IN_PROGRESS|RESOLVED|SPAM)$"),
    session: AsyncSession = _session_dependency,
) -> dict[str, object]:
    """读取官网联系表单，供后台跟进。"""
    await _require_admin(session, subject, "settings.read")
    if not settings.use_database:
        return success({"items": []})
    return success({"items": await contact_service.list_submissions(session, status)})


@admin_router.put("/forms/{submission_id}")
async def update_contact_form_status(
    submission_id: int,
    payload: ContactFormStatusUpdate,
    subject: CurrentSubject,
    x_request_id: str = Header(...),
) -> dict[str, object]:
    """幂等更新官网联系表单状态。"""
    if not settings.use_database:
        raise ApiError(status_code=503, code=50001, i18n_key="common.internal_error", message="联系表单需要本地数据库")

    async def operation(session: AsyncSession | None) -> IdempotentResult:
        if session is None:
            raise RuntimeError("数据库事务会话未初始化")
        await _require_admin(session, subject, "settings.write")
        response = await contact_service.update_status(session, submission_id, payload.status)
        return IdempotentResult(response, "form_submission", str(submission_id))

    try:
        result = await idempotency_service.execute(
            user_id=subject,
            request_id=x_request_id,
            action_type=f"contact_form_status:{submission_id}",
            operation=operation,
        )
        return success(result)
    except ContactFormError as error:
        raise ApiError(status_code=404, code=40401, i18n_key="common.not_found", message=str(error)) from error
    except IdempotencyInProgress as error:
        raise ApiError(
            status_code=429, code=42901, i18n_key="common.request_in_progress", message="请求正在处理中，请稍后再试"
        ) from error
