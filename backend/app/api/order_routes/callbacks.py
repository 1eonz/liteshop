"""支付渠道回调路由。"""

from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import settings
from ...enums.payment import PaymentProvider
from ...errors import ApiError
from ...schemas.payments import PaymentCallback
from ...services.idempotency import IdempotencyInProgress, IdempotentResult
from ...services.order_workflow import (
    OrderWorkflowError,
    payment_callback_fingerprint,
    payment_response,
    verify_payment_callback_signature,
)
from ..responses import success
from .common import idempotency_service, payment_service, require_session, workflow

router = APIRouter()


async def handle_payment_callback(payload: PaymentCallback, provider: PaymentProvider) -> dict[str, object]:
    """统一处理支付渠道回调，验签通过后按回调指纹幂等。"""
    callback_secret = settings.payment_callback_secret_for(provider.value)
    allow_legacy_signature = settings.environment == "development"
    try:
        verify_payment_callback_signature(
            payload,
            callback_secret,
            provider,
            allow_legacy=allow_legacy_signature,
        )
    except OrderWorkflowError as exc:
        raise ApiError(
            status_code=409,
            code=40904,
            i18n_key="payment.amount_mismatch",
            message=str(exc),
        ) from exc

    async def operation(session: AsyncSession | None) -> IdempotentResult:
        if settings.use_database:
            payment = await workflow.payment_callback(
                require_session(session),
                payload,
                provider,
                callback_secret,
                allow_legacy_signature=allow_legacy_signature,
            )
            response = {"success": True, **payment_response(payment)}
            return IdempotentResult(response, "payment", str(payment.id))
        payment_service.callback(
            payload.order_id,
            payload.callback_id,
            payload.amount_cents,
            payload.signature,
            provider,
            payload.provider_trade_no,
            allow_legacy=allow_legacy_signature,
            secret=callback_secret,
        )
        return IdempotentResult({"success": True}, "payment", str(payload.order_id))

    try:
        return await idempotency_service.execute(
            user_id=f"payment:{payload.order_id}",
            request_id=payment_callback_fingerprint(payload, provider),
            action_type=f"payment_callback:{provider.value}",
            operation=operation,
        )
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
            code=40904,
            i18n_key="payment.amount_mismatch",
            message=str(exc),
        ) from exc


@router.post("/payments/callback")
async def payment_callback(payload: PaymentCallback) -> dict[str, object]:
    """兼容开发沙箱回调入口，默认按微信渠道处理。"""
    return success(await handle_payment_callback(payload, PaymentProvider.WECHAT))


@router.post("/payments/wechat/callback")
async def wechat_callback(payload: PaymentCallback) -> dict[str, object]:
    """微信支付回调。"""
    return success(await handle_payment_callback(payload, PaymentProvider.WECHAT))


@router.post("/payments/alipay/callback")
async def alipay_callback(payload: PaymentCallback) -> dict[str, object]:
    """支付宝回调。"""
    return success(await handle_payment_callback(payload, PaymentProvider.ALIPAY))


__all__ = ["alipay_callback", "handle_payment_callback", "payment_callback", "router", "wechat_callback"]
