"""订单运费计算路由。"""

from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import settings
from ...errors import ApiError
from ...schemas.freight import FreightCalculateRequest
from ...services.freight import FreightError, freight_service
from ..dependencies import CurrentSubject
from ..responses import success
from .common import session_dependency

router = APIRouter()


@router.post("/orders/freight-calc")
async def calculate_freight(
    payload: FreightCalculateRequest,
    _user_id: CurrentSubject,
    session: AsyncSession = session_dependency,
) -> dict[str, object]:
    """实时读取 SKU 重量并计算服务端运费。"""
    if not settings.use_database:
        raise ApiError(
            status_code=503,
            code=50001,
            i18n_key="common.internal_error",
            message="运费计算需要本地数据库",
        )
    try:
        amount = await freight_service.calculate(session, payload, template_id=payload.template_id)
    except FreightError as exc:
        raise ApiError(
            status_code=409,
            code=40903,
            i18n_key="order.price_changed",
            message=str(exc),
        ) from exc
    return success({"freightAmount": amount})


__all__ = ["calculate_freight", "router"]
