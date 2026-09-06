"""商品评价 API。"""

from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.database import get_session
from ..errors import ApiError
from ..schemas.review import ReviewCreate
from ..services.idempotency import IdempotencyInProgress, IdempotentResult, idempotency_service
from ..services.review import ReviewError, review_service
from .dependencies import CurrentSubject
from .responses import success

router = APIRouter(prefix="/reviews", tags=["reviews"])
_session_dependency = Depends(get_session)


def _user_id(subject: str) -> int:
    try:
        return int(subject)
    except ValueError as error:
        raise ApiError(status_code=401, code=40101, i18n_key="auth.unauthorized", message="用户身份无效") from error


@router.get("/products/{product_id}")
async def list_product_reviews(product_id: int, session: AsyncSession = _session_dependency) -> dict[str, object]:
    """读取审核通过的商品评价。"""
    if not settings.use_database:
        return success({"averageRating": 0, "items": []})
    return success(await review_service.list_product(session, product_id))


@router.post("")
async def create_review(
    payload: ReviewCreate,
    subject: CurrentSubject,
    x_request_id: str = Header(...),
) -> dict[str, object]:
    """创建评价并按订单项幂等。"""
    if not settings.use_database:
        raise ApiError(status_code=503, code=50001, i18n_key="common.internal_error", message="评价服务需要本地数据库")

    async def operation(session: AsyncSession | None) -> IdempotentResult:
        if session is None:
            raise RuntimeError("数据库事务会话未初始化")
        review = await review_service.create(
            session,
            _user_id(subject),
            payload.order_item_id,
            payload.rating,
            payload.content,
            payload.images,
        )
        response = {"id": review.id, "status": review.status, "rating": review.rating}
        return IdempotentResult(response, "review", str(review.id))

    try:
        result = await idempotency_service.execute(
            user_id=subject,
            request_id=x_request_id,
            action_type=f"review_create:{payload.order_item_id}",
            operation=operation,
        )
        return success(result)
    except ReviewError as error:
        raise ApiError(status_code=409, code=40906, i18n_key="review.invalid", message=str(error)) from error
    except IdempotencyInProgress as error:
        raise ApiError(
            status_code=429, code=42901, i18n_key="common.request_in_progress", message="请求正在处理中，请稍后再试"
        ) from error
