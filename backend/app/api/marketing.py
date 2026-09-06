"""优惠券 API。"""

from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.database import get_session
from ..errors import ApiError
from ..schemas.marketing import CouponClaimRequest, CouponCreate
from ..services.admin import AdminPermissionDenied, AdminService
from ..services.idempotency import IdempotencyInProgress, IdempotentResult, idempotency_service
from ..services.marketing import CouponError, marketing_service
from .dependencies import CurrentSubject
from .responses import success

router = APIRouter(prefix="/coupons", tags=["coupons"])
admin_router = APIRouter(prefix="/admin/coupons", tags=["admin-coupons"])
_session_dependency = Depends(get_session)
_admin_service = AdminService()


async def _require_admin(session: AsyncSession, subject: str) -> None:
    """校验营销配置权限。"""
    if settings.use_database:
        try:
            await _admin_service.require_permission(session, subject, "settings.write")
        except AdminPermissionDenied as error:
            raise ApiError(status_code=403, code=40301, i18n_key="common.forbidden", message=str(error)) from error


@router.get("")
async def list_coupons(session: AsyncSession = _session_dependency) -> dict[str, object]:
    """读取当前可展示的优惠券。"""
    if not settings.use_database:
        return success({"items": []})
    return success({"items": await marketing_service.list_coupons(session)})


@router.post("/claim")
async def claim_coupon(
    payload: CouponClaimRequest,
    subject: CurrentSubject,
    x_request_id: str = Header(...),
) -> dict[str, object]:
    """幂等领取优惠券。"""
    if not settings.use_database:
        raise ApiError(status_code=503, code=50001, i18n_key="common.internal_error", message="优惠券需要本地数据库")

    async def operation(session: AsyncSession | None) -> IdempotentResult:
        if session is None:
            raise RuntimeError("数据库事务会话未初始化")
        response = await marketing_service.claim(session, int(subject), payload.coupon_code)
        return IdempotentResult(response, "coupon_claim", payload.coupon_code.upper())

    try:
        result = await idempotency_service.execute(
            user_id=subject,
            request_id=x_request_id,
            action_type=f"coupon_claim:{payload.coupon_code.upper()}",
            operation=operation,
        )
        return success(result)
    except CouponError as error:
        raise ApiError(status_code=409, code=40920, i18n_key="coupon.unavailable", message=str(error)) from error
    except IdempotencyInProgress as error:
        raise ApiError(
            status_code=429, code=42901, i18n_key="common.request_in_progress", message="请求正在处理中，请稍后再试"
        ) from error


@admin_router.post("", status_code=201)
async def create_coupon(
    payload: CouponCreate,
    subject: CurrentSubject,
    x_request_id: str = Header(...),
    session: AsyncSession = _session_dependency,
) -> dict[str, object]:
    """幂等创建优惠券。"""
    if not settings.use_database:
        raise ApiError(status_code=503, code=50001, i18n_key="common.internal_error", message="优惠券需要本地数据库")

    async def operation(db_session: AsyncSession | None) -> IdempotentResult:
        if db_session is None:
            raise RuntimeError("数据库事务会话未初始化")
        await _require_admin(db_session, subject)
        response = await marketing_service.create_coupon(db_session, payload)
        return IdempotentResult(response, "coupon", str(response["id"]))

    try:
        result = await idempotency_service.execute(
            user_id=subject, request_id=x_request_id, action_type="coupon_create", operation=operation
        )
        return success(result)
    except CouponError as error:
        raise ApiError(status_code=409, code=40920, i18n_key="coupon.conflict", message=str(error)) from error
    except IdempotencyInProgress as error:
        raise ApiError(
            status_code=429, code=42901, i18n_key="common.request_in_progress", message="请求正在处理中，请稍后再试"
        ) from error
