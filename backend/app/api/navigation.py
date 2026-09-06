"""官网导航公开读取与后台管理 API。"""

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.database import get_session
from ..errors import ApiError
from ..schemas.navigation import NavigationItemCreate, NavigationItemUpdate
from ..services.admin import AdminPermissionDenied, AdminService
from ..services.idempotency import IdempotencyInProgress, IdempotentResult, idempotency_service
from ..services.navigation import NavigationError, navigation_service
from .dependencies import CurrentSubject
from .responses import success

router = APIRouter(prefix="/site/navigation", tags=["site-navigation"])
admin_router = APIRouter(prefix="/admin/navigation", tags=["admin-navigation"])
_session_dependency = Depends(get_session)
_admin_service = AdminService()

_DEFAULT_ITEMS: list[dict[str, object]] = [
    {
        "id": 1,
        "label": "产品能力",
        "href": "/products",
        "location": "header",
        "kind": "internal",
        "openNewTab": False,
        "sortOrder": 1,
        "enabled": True,
    },
    {
        "id": 2,
        "label": "品牌故事",
        "href": "/about",
        "location": "header",
        "kind": "internal",
        "openNewTab": False,
        "sortOrder": 2,
        "enabled": True,
    },
    {
        "id": 3,
        "label": "联系团队",
        "href": "/contact",
        "location": "header",
        "kind": "internal",
        "openNewTab": False,
        "sortOrder": 3,
        "enabled": True,
    },
]


@router.get("")
async def list_site_navigation(
    location: str | None = Query(default=None, pattern="^(header|footer)$"),
    session: AsyncSession = _session_dependency,
) -> dict[str, object]:
    """读取官网启用导航。"""
    if not settings.use_database:
        items = [item for item in _DEFAULT_ITEMS if location is None or item["location"] == location]
        return success({"items": items})
    return success({"items": await navigation_service.list_enabled(session, location)})


async def _require_permission(session: AsyncSession, subject: str) -> None:
    if settings.use_database:
        try:
            await _admin_service.require_permission(session, subject, "settings.write")
        except AdminPermissionDenied as error:
            raise ApiError(status_code=403, code=40301, i18n_key="common.forbidden", message=str(error)) from error


@admin_router.get("")
async def list_admin_navigation(
    subject: CurrentSubject, session: AsyncSession = _session_dependency
) -> dict[str, object]:
    """读取后台全部导航配置。"""
    await _require_permission(session, subject)
    if not settings.use_database:
        return success({"items": list(_DEFAULT_ITEMS)})
    return success({"items": await navigation_service.list_admin(session)})


@admin_router.post("", status_code=201)
async def create_navigation(
    payload: NavigationItemCreate,
    subject: CurrentSubject,
    x_request_id: str = Header(...),
    session: AsyncSession = _session_dependency,
) -> dict[str, object]:
    """幂等创建官网导航项。"""
    if not settings.use_database:
        raise ApiError(status_code=503, code=50001, i18n_key="common.internal_error", message="导航配置需要本地数据库")

    async def operation(db_session: AsyncSession | None) -> IdempotentResult:
        if db_session is None:
            raise RuntimeError("数据库事务会话未初始化")
        await _require_permission(db_session, subject)
        response = await navigation_service.create(db_session, payload)
        return IdempotentResult(response, "navigation", str(response["id"]))

    try:
        return success(
            await idempotency_service.execute(
                user_id=subject, request_id=x_request_id, action_type="navigation_create", operation=operation
            )
        )
    except IdempotencyInProgress as error:
        raise ApiError(
            status_code=429, code=42901, i18n_key="common.request_in_progress", message="请求正在处理中，请稍后再试"
        ) from error


@admin_router.put("/{item_id}")
async def update_navigation(
    item_id: int,
    payload: NavigationItemUpdate,
    subject: CurrentSubject,
    x_request_id: str = Header(...),
) -> dict[str, object]:
    """幂等更新官网导航项。"""
    if not settings.use_database:
        raise ApiError(status_code=503, code=50001, i18n_key="common.internal_error", message="导航配置需要本地数据库")

    async def operation(db_session: AsyncSession | None) -> IdempotentResult:
        if db_session is None:
            raise RuntimeError("数据库事务会话未初始化")
        await _require_permission(db_session, subject)
        response = await navigation_service.update(db_session, item_id, payload)
        return IdempotentResult(response, "navigation", str(item_id))

    try:
        return success(
            await idempotency_service.execute(
                user_id=subject,
                request_id=x_request_id,
                action_type=f"navigation_update:{item_id}",
                operation=operation,
            )
        )
    except NavigationError as error:
        raise ApiError(status_code=404, code=40401, i18n_key="common.not_found", message=str(error)) from error
    except IdempotencyInProgress as error:
        raise ApiError(
            status_code=429, code=42901, i18n_key="common.request_in_progress", message="请求正在处理中，请稍后再试"
        ) from error


@admin_router.delete("/{item_id}")
async def delete_navigation(
    item_id: int, subject: CurrentSubject, x_request_id: str = Header(...)
) -> dict[str, object]:
    """幂等删除官网导航项。"""
    if not settings.use_database:
        raise ApiError(status_code=503, code=50001, i18n_key="common.internal_error", message="导航配置需要本地数据库")

    async def operation(db_session: AsyncSession | None) -> IdempotentResult:
        if db_session is None:
            raise RuntimeError("数据库事务会话未初始化")
        await _require_permission(db_session, subject)
        response = await navigation_service.remove(db_session, item_id)
        return IdempotentResult(response, "navigation", str(item_id))

    try:
        return success(
            await idempotency_service.execute(
                user_id=subject,
                request_id=x_request_id,
                action_type=f"navigation_delete:{item_id}",
                operation=operation,
            )
        )
    except NavigationError as error:
        raise ApiError(status_code=404, code=40401, i18n_key="common.not_found", message=str(error)) from error
    except IdempotencyInProgress as error:
        raise ApiError(
            status_code=429, code=42901, i18n_key="common.request_in_progress", message="请求正在处理中，请稍后再试"
        ) from error
