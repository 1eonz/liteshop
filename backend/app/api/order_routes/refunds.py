"""支付退款申请路由。"""

from fastapi import APIRouter, Header
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import settings
from ...errors import ApiError
from ...schemas.payments import RefundCreate
from ...services.idempotency import IdempotencyInProgress, IdempotentResult
from ...services.refund import RefundError, refund_response
from ..dependencies import CurrentSubject
from ..responses import success
from .common import database_user_id, idempotency_service, refund_service, require_session, session_dependency

router = APIRouter()


@router.post("/payments/{payment_id}/refund")
async def create_refund(
    payment_id: int,
    payload: RefundCreate,
    user_id: CurrentSubject,
    x_request_id: str = Header(...),
    session: AsyncSession = session_dependency,
) -> dict[str, object]:
    """创建退款申请，支付渠道调用由后续异步任务执行。"""
    if not settings.use_database:
        raise ApiError(
            status_code=503,
            code=50001,
            i18n_key="common.internal_error",
            message="退款申请需要本地数据库",
        )

    async def operation(tx: AsyncSession | None) -> IdempotentResult:
        refund = await refund_service.create(
            require_session(tx),
            user_id=database_user_id(user_id),
            payment_id=payment_id,
            amount_cents=payload.amount_cents,
            reason=payload.reason,
            request_id=x_request_id,
        )
        return IdempotentResult(refund_response(refund), "refund", str(refund.id))

    try:
        result = await idempotency_service.execute(
            user_id=user_id,
            request_id=x_request_id,
            action_type=f"refund_create:{payment_id}",
            operation=operation,
        )
        return success(result)
    except IdempotencyInProgress as exc:
        raise ApiError(
            status_code=429,
            code=42901,
            i18n_key="common.request_in_progress",
            message="请求正在处理中，请稍后再试",
        ) from exc
    except RefundError as exc:
        raise ApiError(
            status_code=409,
            code=40905,
            i18n_key="payment.refund_invalid",
            message=str(exc),
        ) from exc


__all__ = ["create_refund", "router"]
