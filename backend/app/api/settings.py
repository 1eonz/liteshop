"""商城主题、物流枚举和功能开关接口。"""

from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.database import get_session
from ..errors import ApiError
from ..schemas.admin import SiteSettingsUpdate, ThemeSettingsUpdate
from ..services.admin import AdminPermissionDenied, AdminService
from ..services.idempotency import IdempotencyInProgress, IdempotentResult, idempotency_service
from ..services.settings import settings_service
from .dependencies import CurrentSubject
from .responses import success

router = APIRouter(prefix="/settings", tags=["settings"])
admin_service = AdminService()
_session_dependency = Depends(get_session)

_feature_flags: dict[str, bool] = {
    "h5Favorites": True,
    "h5PaymentSandbox": True,
    "adminDashboard": True,
}
_shipping_companies: list[dict[str, str]] = [
    {"code": "SF", "name": "顺丰速运"},
    {"code": "YTO", "name": "圆通速递"},
    {"code": "ZTO", "name": "中通快递"},
    {"code": "OTHER", "name": "其他"},
]


@router.get("/theme")
async def get_theme(session: AsyncSession = _session_dependency) -> dict[str, object]:
    """读取当前商城主题令牌配置。"""
    return success(await settings_service.get_theme(session))


@router.put("/theme")
async def update_theme(
    payload: ThemeSettingsUpdate,
    _subject: CurrentSubject,
    x_request_id: str = Header(...),
    session: AsyncSession = _session_dependency,
) -> dict[str, object]:
    """幂等更新商城主题配置。"""
    if settings.use_database:
        try:
            await admin_service.require_permission(session, _subject, "settings.write")
        except AdminPermissionDenied as error:
            raise ApiError(
                status_code=403,
                code=40301,
                i18n_key="common.forbidden",
                message="缺少系统设置权限",
            ) from error

    async def operation(_session: AsyncSession | None) -> IdempotentResult:
        updated: dict[str, object] = payload.model_dump(by_alias=True)
        response = await settings_service.update_theme(_session, updated)
        return IdempotentResult(response, "theme", "global")

    try:
        result = await idempotency_service.execute(
            user_id=_subject,
            request_id=x_request_id,
            action_type="settings_theme_update",
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


@router.get("/site")
async def get_site_settings(session: AsyncSession = _session_dependency) -> dict[str, object]:
    """读取官网全局设置，公开接口仅返回安全字段。"""
    return success(await settings_service.get_site(session))


@router.put("/site")
async def update_site_settings(
    payload: SiteSettingsUpdate,
    _subject: CurrentSubject,
    x_request_id: str = Header(...),
    session: AsyncSession = _session_dependency,
) -> dict[str, object]:
    """幂等更新官网全局设置。"""
    if settings.use_database:
        try:
            await admin_service.require_permission(session, _subject, "settings.write")
        except AdminPermissionDenied as error:
            raise ApiError(
                status_code=403, code=40301, i18n_key="common.forbidden", message="缺少系统设置权限"
            ) from error

    async def operation(_session: AsyncSession | None) -> IdempotentResult:
        response = await settings_service.update_site(_session, payload.model_dump(by_alias=True))
        return IdempotentResult(response, "site_settings", "site")

    try:
        result = await idempotency_service.execute(
            user_id=_subject,
            request_id=x_request_id,
            action_type="settings_site_update",
            operation=operation,
        )
        return success(result)
    except IdempotencyInProgress as error:
        raise ApiError(
            status_code=429, code=42901, i18n_key="common.request_in_progress", message="请求正在处理中，请稍后再试"
        ) from error


@router.get("/shipping-companies")
async def list_shipping_companies() -> dict[str, object]:
    """读取一期预置物流公司枚举。"""
    return success({"items": list(_shipping_companies)})


@router.get("/feature-flags")
async def list_feature_flags() -> dict[str, object]:
    """读取当前功能开关。"""
    return success({"items": [{"key": key, "enabled": enabled} for key, enabled in _feature_flags.items()]})
