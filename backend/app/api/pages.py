"""商城低代码页面 Schema 读写接口。"""

from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.database import get_session
from ..errors import ApiError
from ..schemas.page import PageConversionEventInput, PageCopyInput, PageCreateInput, PageSchemaInput, PageVariantInput
from ..services.admin import AdminPermissionDenied, AdminService
from ..services.idempotency import IdempotencyInProgress, IdempotentResult, idempotency_service
from ..services.isr import trigger_isr_revalidate
from ..services.page import PageSchemaError, page_service
from .dependencies import CurrentSubject
from .responses import success

router = APIRouter(prefix="/pages", tags=["pages"])
public_router = APIRouter(prefix="/site/pages", tags=["site-pages"])
_session_dependency = Depends(get_session)
_admin_service = AdminService()

_HOME_SCHEMA: dict[str, object] = {
    "id": 1,
    "version": 1,
    "slug": "home",
    "components": [
        {"type": "SearchBar", "props": {"placeholder": "搜索商品"}},
        {"type": "Carousel", "props": {"items": []}},
        {"type": "CategoryGrid", "props": {"columns": 4}},
        {"type": "ProductGrid", "props": {"columns": 2}},
        {"type": "ActivityBanner", "props": {"title": "限时活动"}},
        {"type": "Tabbar", "props": {"items": ["home", "category", "cart", "me"]}},
    ],
}


@public_router.get("/{slug}")
async def get_public_page(slug: str, session: AsyncSession = _session_dependency) -> dict[str, object]:
    """按官网路由读取已发布页面，未启用数据库时提供首页开发回退。"""
    if not slug or any(char not in "abcdefghijklmnopqrstuvwxyz0123456789-" for char in slug):
        raise ApiError(status_code=404, code=40401, i18n_key="common.not_found", message="页面不存在")
    if settings.use_database:
        try:
            return success(await page_service.get_by_slug(session, slug))
        except PageSchemaError as error:
            raise ApiError(status_code=404, code=40401, i18n_key="common.not_found", message=str(error)) from error
    if slug != "home":
        raise ApiError(status_code=404, code=40401, i18n_key="common.not_found", message="页面不存在")
    return success(dict(_HOME_SCHEMA))


async def _require_page_permission(session: AsyncSession, subject: str) -> None:
    """后台页面写操作统一复用 RBAC 权限。"""
    if settings.use_database:
        try:
            await _admin_service.require_permission(session, subject, "settings.write")
        except AdminPermissionDenied as error:
            raise ApiError(status_code=403, code=40301, i18n_key="common.forbidden", message=str(error)) from error


@router.get("")
async def list_pages(subject: CurrentSubject, session: AsyncSession = _session_dependency) -> dict[str, object]:
    """读取后台页面管理列表。"""
    await _require_page_permission(session, subject)
    if not settings.use_database:
        return success({"items": [{"id": 1, "slug": "home", "name": "首页", "version": 1, "isHome": True}]})
    return success({"items": await page_service.list_pages(session)})


@router.post("", status_code=201)
async def create_page(
    payload: PageCreateInput,
    subject: CurrentSubject,
    x_request_id: str = Header(...),
) -> dict[str, object]:
    """幂等创建页面。"""
    if not settings.use_database:
        raise ApiError(status_code=503, code=50001, i18n_key="common.internal_error", message="页面编辑需要本地数据库")

    async def operation(session: AsyncSession | None) -> IdempotentResult:
        if session is None:
            raise RuntimeError("数据库事务会话未初始化")
        await _require_page_permission(session, subject)
        response = await page_service.create(session, payload)
        return IdempotentResult(response, "page", str(response["id"]))

    try:
        result = await idempotency_service.execute(
            user_id=subject, request_id=x_request_id, action_type="page_create", operation=operation
        )
        await trigger_isr_revalidate(payload.slug)
        return success(result)
    except PageSchemaError as error:
        raise ApiError(status_code=409, code=40901, i18n_key="page.slug_conflict", message=str(error)) from error
    except IdempotencyInProgress as error:
        raise ApiError(
            status_code=429,
            code=42901,
            i18n_key="common.request_in_progress",
            message="请求正在处理中，请稍后再试",
        ) from error


@router.get("/{page_id}/schema")
async def get_page_schema(page_id: int, session: AsyncSession = _session_dependency) -> dict[str, object]:
    """返回带版本号的首页 Schema，供渲染器和预览使用。"""
    if settings.use_database:
        try:
            return success(await page_service.get(session, page_id))
        except PageSchemaError as error:
            raise ApiError(status_code=404, code=40401, i18n_key="common.not_found", message=str(error)) from error
    if page_id != 1:
        return success({"id": page_id, "version": 1, "components": []})
    return success(dict(_HOME_SCHEMA))


@router.put("/{page_id}/schema")
async def save_page_schema(
    page_id: int,
    payload: PageSchemaInput,
    subject: CurrentSubject,
    x_request_id: str = Header(...),
) -> dict[str, object]:
    """幂等保存页面 Schema。"""
    if not settings.use_database:
        raise ApiError(status_code=503, code=50001, i18n_key="common.internal_error", message="页面编辑需要本地数据库")

    async def operation(session: AsyncSession | None) -> IdempotentResult:
        if session is None:
            raise RuntimeError("数据库事务会话未初始化")
        await _require_page_permission(session, subject)
        response = await page_service.save(session, page_id, payload)
        return IdempotentResult(response, "page", str(page_id))

    try:
        result = await idempotency_service.execute(
            user_id=subject,
            request_id=x_request_id,
            action_type=f"page_save:{page_id}",
            operation=operation,
        )
        await trigger_isr_revalidate(payload.slug)
        return success(result)
    except PageSchemaError as error:
        raise ApiError(status_code=422, code=42201, i18n_key="page.invalid_schema", message=str(error)) from error
    except IdempotencyInProgress as error:
        raise ApiError(
            status_code=429,
            code=42901,
            i18n_key="common.request_in_progress",
            message="请求正在处理中，请稍后再试",
        ) from error


@router.put("/{page_id}/home")
async def set_home_page(
    page_id: int,
    subject: CurrentSubject,
    x_request_id: str = Header(...),
) -> dict[str, object]:
    """幂等设置首页。"""
    if not settings.use_database:
        raise ApiError(status_code=503, code=50001, i18n_key="common.internal_error", message="页面编辑需要本地数据库")

    async def operation(session: AsyncSession | None) -> IdempotentResult:
        if session is None:
            raise RuntimeError("数据库事务会话未初始化")
        await _require_page_permission(session, subject)
        response = await page_service.set_home(session, page_id)
        return IdempotentResult(response, "page", str(page_id))

    try:
        result = await idempotency_service.execute(
            user_id=subject,
            request_id=x_request_id,
            action_type=f"page_home:{page_id}",
            operation=operation,
        )
        await trigger_isr_revalidate(str(result.get("slug", "home")))
        return success(result)
    except PageSchemaError as error:
        raise ApiError(status_code=404, code=40401, i18n_key="common.not_found", message=str(error)) from error
    except IdempotencyInProgress as error:
        raise ApiError(
            status_code=429,
            code=42901,
            i18n_key="common.request_in_progress",
            message="请求正在处理中，请稍后再试",
        ) from error


@router.post("/{page_id}/copy", status_code=201)
async def copy_page(
    page_id: int,
    payload: PageCopyInput,
    subject: CurrentSubject,
    x_request_id: str = Header(...),
) -> dict[str, object]:
    """幂等复制页面并校验新路由冲突。"""
    if not settings.use_database:
        raise ApiError(status_code=503, code=50001, i18n_key="common.internal_error", message="页面编辑需要本地数据库")
    slug = payload.slug.strip()
    name_value = payload.name or None

    async def operation(session: AsyncSession | None) -> IdempotentResult:
        if session is None:
            raise RuntimeError("数据库事务会话未初始化")
        await _require_page_permission(session, subject)
        response = await page_service.copy(session, page_id, slug, name_value)
        return IdempotentResult(response, "page", str(response["id"]))

    try:
        result = await idempotency_service.execute(
            user_id=subject, request_id=x_request_id, action_type=f"page_copy:{page_id}", operation=operation
        )
        await trigger_isr_revalidate(slug)
        return success(result)
    except PageSchemaError as error:
        raise ApiError(status_code=409, code=40901, i18n_key="page.slug_conflict", message=str(error)) from error
    except IdempotencyInProgress as error:
        raise ApiError(
            status_code=429,
            code=42901,
            i18n_key="common.request_in_progress",
            message="请求正在处理中，请稍后再试",
        ) from error


@router.delete("/{page_id}")
async def delete_page(page_id: int, subject: CurrentSubject, x_request_id: str = Header(...)) -> dict[str, object]:
    """幂等删除非首页页面。"""
    if not settings.use_database:
        raise ApiError(status_code=503, code=50001, i18n_key="common.internal_error", message="页面编辑需要本地数据库")

    async def operation(session: AsyncSession | None) -> IdempotentResult:
        if session is None:
            raise RuntimeError("数据库事务会话未初始化")
        await _require_page_permission(session, subject)
        response = await page_service.remove(session, page_id)
        return IdempotentResult(response, "page", str(page_id))

    try:
        result = await idempotency_service.execute(
            user_id=subject, request_id=x_request_id, action_type=f"page_delete:{page_id}", operation=operation
        )
        return success(result)
    except PageSchemaError as error:
        raise ApiError(status_code=409, code=40901, i18n_key="page.delete_forbidden", message=str(error)) from error
    except IdempotencyInProgress as error:
        raise ApiError(
            status_code=429,
            code=42901,
            i18n_key="common.request_in_progress",
            message="请求正在处理中，请稍后再试",
        ) from error


@router.get("/{page_id}/variants")
async def list_page_variants(
    page_id: int, subject: CurrentSubject, session: AsyncSession = _session_dependency
) -> dict[str, object]:
    """读取页面变体。"""
    await _require_page_permission(session, subject)
    if not settings.use_database:
        return success([])
    try:
        return success(await page_service.list_variants(session, page_id))
    except PageSchemaError as error:
        raise ApiError(status_code=404, code=40401, i18n_key="common.not_found", message=str(error)) from error


@router.put("/{page_id}/variants/{variant_key}")
async def save_page_variant(
    page_id: int,
    variant_key: str,
    payload: PageVariantInput,
    subject: CurrentSubject,
    x_request_id: str = Header(...),
) -> dict[str, object]:
    """幂等保存页面 A/B 变体。"""
    if variant_key != payload.key:
        raise ApiError(status_code=422, code=42201, i18n_key="page.invalid_schema", message="变体键与路径不一致")
    if not settings.use_database:
        raise ApiError(status_code=503, code=50001, i18n_key="common.internal_error", message="页面编辑需要本地数据库")

    async def operation(session: AsyncSession | None) -> IdempotentResult:
        if session is None:
            raise RuntimeError("数据库事务会话未初始化")
        await _require_page_permission(session, subject)
        response = await page_service.save_variant(session, page_id, payload)
        return IdempotentResult(response, "page_variant", str(response["id"]))

    try:
        result = await idempotency_service.execute(
            user_id=subject,
            request_id=x_request_id,
            action_type=f"page_variant:{page_id}:{variant_key}",
            operation=operation,
        )
        return success(result)
    except PageSchemaError as error:
        raise ApiError(status_code=422, code=42201, i18n_key="page.invalid_schema", message=str(error)) from error
    except IdempotencyInProgress as error:
        raise ApiError(
            status_code=429,
            code=42901,
            i18n_key="common.request_in_progress",
            message="请求正在处理中，请稍后再试",
        ) from error


@router.post("/{page_id}/events", status_code=202)
async def record_page_event(
    page_id: int,
    payload: PageConversionEventInput,
    x_request_id: str = Header(...),
) -> dict[str, object]:
    """幂等接收页面转化事件，匿名访客也可上报。"""
    if not settings.use_database:
        return success({"accepted": True})

    async def operation(session: AsyncSession | None) -> IdempotentResult:
        if session is None:
            raise RuntimeError("数据库事务会话未初始化")
        response = await page_service.record_event(session, page_id, payload)
        return IdempotentResult(response, "page_event", str(response["id"]))

    try:
        result = await idempotency_service.execute(
            user_id=payload.anonymous_id or "anonymous",
            request_id=x_request_id,
            action_type=f"page_event:{page_id}:{payload.event_name}",
            operation=operation,
        )
        return success(result)
    except PageSchemaError as error:
        raise ApiError(status_code=404, code=40401, i18n_key="common.not_found", message=str(error)) from error
    except IdempotencyInProgress as error:
        raise ApiError(
            status_code=429, code=42901, i18n_key="common.request_in_progress", message="请求正在处理中，请稍后再试"
        ) from error
