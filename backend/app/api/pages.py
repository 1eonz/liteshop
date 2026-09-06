"""商城低代码页面 Schema 读写接口。"""

from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.database import get_session
from ..errors import ApiError
from ..schemas.page import PageSchemaInput
from ..services.idempotency import IdempotencyInProgress, IdempotentResult, idempotency_service
from ..services.page import PageSchemaError, page_service
from .dependencies import CurrentSubject
from .responses import success

router = APIRouter(prefix="/pages", tags=["pages"])
_session_dependency = Depends(get_session)

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
        response = await page_service.save(session, page_id, payload)
        return IdempotentResult(response, "page", str(page_id))

    try:
        result = await idempotency_service.execute(
            user_id=subject,
            request_id=x_request_id,
            action_type=f"page_save:{page_id}",
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
        response = await page_service.set_home(session, page_id)
        return IdempotentResult(response, "page", str(page_id))

    try:
        result = await idempotency_service.execute(
            user_id=subject,
            request_id=x_request_id,
            action_type=f"page_home:{page_id}",
            operation=operation,
        )
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
