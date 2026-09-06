"""商品收藏 API。"""

from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.database import get_session
from ..errors import ApiError
from ..services.favorite import favorite_service
from ..services.idempotency import IdempotencyInProgress, IdempotentResult, idempotency_service
from .dependencies import CurrentSubject
from .responses import success

router = APIRouter(prefix="/favorites", tags=["favorites"])
_session_dependency = Depends(get_session)


def _user_id(subject: str) -> int:
    try:
        return int(subject)
    except ValueError as error:
        raise ApiError(status_code=401, code=40101, i18n_key="auth.unauthorized", message="用户身份无效") from error


@router.get("")
async def list_favorites(subject: CurrentSubject, session: AsyncSession = _session_dependency) -> dict[str, object]:
    """返回当前用户收藏商品 ID。"""
    if not settings.use_database:
        return success({"items": []})
    return success({"items": await favorite_service.list_ids(session, _user_id(subject))})


@router.put("/{product_id}")
async def toggle_favorite(
    product_id: int,
    subject: CurrentSubject,
    x_request_id: str = Header(...),
) -> dict[str, object]:
    """幂等切换收藏状态。"""
    if not settings.use_database:
        raise ApiError(status_code=503, code=50001, i18n_key="common.internal_error", message="收藏服务需要本地数据库")

    async def operation(session: AsyncSession | None) -> IdempotentResult:
        if session is None:
            raise RuntimeError("数据库事务会话未初始化")
        response = await favorite_service.toggle(session, _user_id(subject), product_id)
        return IdempotentResult(response, "favorite", str(product_id))

    try:
        result = await idempotency_service.execute(
            user_id=subject,
            request_id=x_request_id,
            action_type=f"favorite_toggle:{product_id}",
            operation=operation,
        )
        return success(result)
    except IdempotencyInProgress as error:
        raise ApiError(
            status_code=429, code=42901, i18n_key="common.request_in_progress", message="请求正在处理中，请稍后再试"
        ) from error
