"""订单与支付 HTTP 适配层。"""

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.database import get_session
from ..core.runtime import order_service, payment_service
from ..enums.order import OrderStatus
from ..enums.payment import PaymentProvider
from ..errors import ApiError
from ..schemas.freight import FreightCalculateRequest
from ..schemas.orders import OrderCreate
from ..schemas.payments import PaymentCallback, PaymentCreate, RefundCreate
from ..services.freight import FreightError, freight_service
from ..services.idempotency import IdempotencyInProgress, IdempotentResult, idempotency_service
from ..services.order_workflow import (
    OrderWorkflow,
    OrderWorkflowError,
    order_response,
    payment_callback_fingerprint,
    payment_response,
    verify_payment_callback_signature,
)
from ..services.refund import RefundError, RefundService, refund_response
from .dependencies import CurrentSubject
from .responses import success

router = APIRouter(tags=["orders"])
workflow = OrderWorkflow()
refund_service = RefundService()
_session_dependency = Depends(get_session)


def _require_session(session: AsyncSession | None) -> AsyncSession:
    """数据库模式下拒绝缺失事务会话。"""
    if session is None:
        raise RuntimeError("数据库事务会话未初始化")
    return session


def _database_user_id(subject: str) -> int:
    """把 JWT 主体转换为数据库用户主键。"""
    try:
        return int(subject)
    except ValueError as exc:
        raise ApiError(
            status_code=401,
            code=40101,
            i18n_key="auth.unauthorized",
            message="用户身份无效",
        ) from exc


@router.post("/orders")
async def create_order(
    payload: OrderCreate,
    user_id: CurrentSubject,
    x_request_id: str = Header(...),
) -> dict[str, object]:
    """创建订单，锁库存并按客户端请求 ID 幂等。"""

    async def operation(session: AsyncSession | None) -> IdempotentResult:
        if settings.use_database:
            db_order = await workflow.create_order(
                _require_session(session),
                _database_user_id(user_id),
                x_request_id,
                payload,
            )
            db_response = order_response(db_order)
            return IdempotentResult(db_response, "order", str(db_order.id))
        memory_order = order_service.create(user_id, x_request_id, payload.total_amount)
        memory_response: dict[str, object] = {
            "id": memory_order.order_id,
            "status": memory_order.status.value,
            "totalAmount": memory_order.total_amount,
        }
        return IdempotentResult(memory_response, "order", str(memory_order.order_id))

    try:
        result = await idempotency_service.execute(
            user_id=user_id,
            request_id=x_request_id,
            action_type="order_create",
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
    except OrderWorkflowError as exc:
        raise ApiError(
            status_code=409,
            code=40901,
            i18n_key="order.invalid_transition",
            message=str(exc),
        ) from exc


@router.get("/orders")
async def list_orders(
    user_id: CurrentSubject,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, alias="pageSize", ge=1, le=100),
    session: AsyncSession = _session_dependency,
) -> dict[str, object]:
    """分页读取当前用户订单。"""
    if settings.use_database:
        orders, total = await workflow.list_owned_orders(
            session,
            _database_user_id(user_id),
            (page - 1) * page_size,
            page_size,
        )
        return success(
            {
                "items": [order_response(order) for order in orders],
                "meta": {
                    "page": page,
                    "pageSize": page_size,
                    "total": total,
                    "hasNext": page * page_size < total,
                },
            }
        )
    memory_orders, total = order_service.list_for_user(user_id, (page - 1) * page_size, page_size)
    return success(
        {
            "items": [
                {
                    "id": order.order_id,
                    "orderNo": f"LS{order.order_id:08d}",
                    "status": order.status.value,
                    "totalAmount": order.total_amount,
                    "productAmount": order.total_amount,
                    "freightAmount": 0,
                    "discountAmount": 0,
                    "refundStatus": "NONE",
                    "paidAmount": None,
                    "paidAt": None,
                    "shippedAt": None,
                    "completedAt": None,
                    "cancelledAt": None,
                    "cancelReason": None,
                    "addressSnapshot": {},
                    "remark": None,
                    "shippingCompanyCode": "",
                    "trackingNo": "",
                    "items": [],
                    "createdAt": order.created_at.isoformat(),
                }
                for order in memory_orders
            ],
            "meta": {"page": page, "pageSize": page_size, "total": total, "hasNext": page * page_size < total},
        }
    )


@router.post("/orders/freight-calc")
async def calculate_freight(
    payload: FreightCalculateRequest,
    _user_id: CurrentSubject,
    session: AsyncSession = _session_dependency,
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


@router.get("/orders/{order_id}")
async def get_order(
    order_id: int,
    user_id: CurrentSubject,
    session: AsyncSession = _session_dependency,
) -> dict[str, object]:
    """读取当前用户订单详情。"""
    if settings.use_database:
        try:
            order = await workflow.get_owned_order(session, order_id, _database_user_id(user_id))
        except (KeyError, OrderWorkflowError) as exc:
            raise ApiError(
                status_code=404,
                code=40401,
                i18n_key="common.not_found",
                message="订单不存在",
            ) from exc
        return success(order_response(order))
    try:
        memory_order = order_service.get(order_id)
    except KeyError as exc:
        raise ApiError(
            status_code=404,
            code=40401,
            i18n_key="common.not_found",
            message="订单不存在",
        ) from exc
    if memory_order.user_id != user_id:
        raise ApiError(
            status_code=404,
            code=40401,
            i18n_key="common.not_found",
            message="订单不存在",
        )
    return success(
        {
            "id": memory_order.order_id,
            "orderNo": f"LS{memory_order.order_id:08d}",
            "status": memory_order.status.value,
            "totalAmount": memory_order.total_amount,
            "productAmount": memory_order.total_amount,
            "freightAmount": 0,
            "discountAmount": 0,
            "refundStatus": "NONE",
            "paidAmount": None,
            "paidAt": None,
            "shippedAt": None,
            "completedAt": None,
            "cancelledAt": None,
            "cancelReason": None,
            "addressSnapshot": {},
            "remark": None,
            "shippingCompanyCode": "",
            "trackingNo": "",
            "items": [],
            "createdAt": memory_order.created_at.isoformat(),
        }
    )


async def _change_order_status(
    order_id: int,
    request_id: str,
    user_id: str,
    target: OrderStatus,
) -> dict[str, object]:
    """统一执行取消或确认收货的幂等状态流转。"""

    async def operation(session: AsyncSession | None) -> IdempotentResult:
        if settings.use_database:
            tx = _require_session(session)
            changed_db_order = (
                await workflow.cancel_owned_order(tx, order_id, _database_user_id(user_id), request_id)
                if target is OrderStatus.CANCELLED
                else await workflow.confirm_owned_order(tx, order_id, _database_user_id(user_id))
            )
            return IdempotentResult(order_response(changed_db_order), "order", str(order_id))
        memory_order = order_service.get(order_id)
        if memory_order.user_id != user_id:
            raise OrderWorkflowError("订单不存在")
        changed_memory_order = order_service.transition(order_id, target)
        memory_response: dict[str, object] = {
            "id": changed_memory_order.order_id,
            "status": changed_memory_order.status.value,
            "requestId": request_id,
        }
        return IdempotentResult(memory_response, "order", str(order_id))

    return await idempotency_service.execute(
        user_id=user_id,
        request_id=request_id,
        action_type=f"order_{target.value.lower()}:{order_id}",
        operation=operation,
    )


@router.post("/orders/{order_id}/cancel")
async def cancel_order(
    order_id: int,
    user_id: CurrentSubject,
    x_request_id: str = Header(...),
) -> dict[str, object]:
    """取消待支付订单并释放锁定库存。"""
    try:
        return success(await _change_order_status(order_id, x_request_id, user_id, OrderStatus.CANCELLED))
    except IdempotencyInProgress as exc:
        raise ApiError(
            status_code=429,
            code=42901,
            i18n_key="common.request_in_progress",
            message="请求正在处理中，请稍后再试",
        ) from exc
    except (OrderWorkflowError, KeyError, ValueError) as exc:
        raise ApiError(
            status_code=409,
            code=40901,
            i18n_key="order.invalid_transition",
            message=str(exc),
        ) from exc


@router.post("/orders/{order_id}/confirm")
async def confirm_order(
    order_id: int,
    user_id: CurrentSubject,
    x_request_id: str = Header(...),
) -> dict[str, object]:
    """确认收货，状态机只允许 SHIPPED 转 COMPLETED。"""
    try:
        return success(await _change_order_status(order_id, x_request_id, user_id, OrderStatus.COMPLETED))
    except IdempotencyInProgress as exc:
        raise ApiError(
            status_code=429,
            code=42901,
            i18n_key="common.request_in_progress",
            message="请求正在处理中，请稍后再试",
        ) from exc
    except (OrderWorkflowError, KeyError, ValueError) as exc:
        raise ApiError(
            status_code=409,
            code=40901,
            i18n_key="order.invalid_transition",
            message=str(exc),
        ) from exc


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
                _require_session(session),
                _database_user_id(user_id),
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


async def _payment_callback(payload: PaymentCallback, provider: PaymentProvider) -> dict[str, object]:
    """统一处理支付渠道回调，验签通过后按 callback ID 幂等。"""
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
                _require_session(session),
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


@router.post("/payments/{payment_id}/refund")
async def create_refund(
    payment_id: int,
    payload: RefundCreate,
    user_id: CurrentSubject,
    x_request_id: str = Header(...),
    session: AsyncSession = _session_dependency,
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
            _require_session(tx),
            user_id=_database_user_id(user_id),
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


@router.post("/payments/callback")
async def payment_callback(payload: PaymentCallback) -> dict[str, object]:
    """兼容开发沙箱回调入口，默认按微信渠道处理。"""
    return success(await _payment_callback(payload, PaymentProvider.WECHAT))


@router.post("/payments/wechat/callback")
async def wechat_callback(payload: PaymentCallback) -> dict[str, object]:
    """微信支付回调。"""
    return success(await _payment_callback(payload, PaymentProvider.WECHAT))


@router.post("/payments/alipay/callback")
async def alipay_callback(payload: PaymentCallback) -> dict[str, object]:
    """支付宝回调。"""
    return success(await _payment_callback(payload, PaymentProvider.ALIPAY))
