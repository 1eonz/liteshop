"""支付单创建路由。"""

from fastapi import APIRouter, Header
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import settings
from ...errors import ApiError
from ...schemas.payments import PaymentCreate
from ...services.idempotency import IdempotencyInProgress, IdempotentResult
from ...services.order_workflow import OrderWorkflowError, payment_response
from ..dependencies import CurrentSubject
from ..responses import success
from .common import (
    database_user_id,
    idempotency_service,
    payment_service,
    require_session,
    workflow,
)

router = APIRouter()


@router.post("/payments")
async def create_payment(
    payload: PaymentCreate,
    user_id: CurrentSubject,
    x_request_id: str = Header(...),
) -> dict[str, object]:
    """创建支付单并校验订单状态、归属和整数分金额。"""

    async def operation(session: AsyncSession | None) -> IdempotentResult:
        if settings.use_database:
            payment = await workflow.create_payment(
                require_session(session),
                database_user_id(user_id),
                x_request_id,
                payload,
            )
            return IdempotentResult(payment_response(payment), "payment", str(payment.id))
        intent = payment_service.create(
            user_id,
            payload.order_id,
            payload.provider,
            payload.amount_cents,
            x_request_id,
        )
        response: dict[str, object] = {
            "id": intent.payment_id,
            "orderId": intent.order_id,
            "provider": intent.provider.value,
            "amountCents": intent.amount_cents,
        }
        return IdempotentResult(response, "payment", intent.payment_id)

    try:
        result = await idempotency_service.execute(
            user_id=user_id,
            request_id=x_request_id,
            action_type=f"payment_create:{payload.order_id}",
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
    except (OrderWorkflowError, ValueError, KeyError) as exc:
        raise ApiError(
            status_code=409,
            code=40901,
            i18n_key="order.invalid_transition",
            message=str(exc),
        ) from exc


__all__ = ["create_payment", "router"]
