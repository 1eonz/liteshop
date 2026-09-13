"""用户订单创建和查询路由。"""

from fastapi import APIRouter, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import settings
from ...errors import ApiError
from ...schemas.orders import OrderCreate
from ...services.idempotency import IdempotencyInProgress, IdempotentResult
from ...services.order import Order
from ...services.order_workflow import OrderWorkflowError, order_response
from ..dependencies import CurrentSubject
from ..responses import success
from .common import (
    database_user_id,
    idempotency_service,
    order_service,
    require_session,
    session_dependency,
    workflow,
)

collection_router = APIRouter()
detail_router = APIRouter()
router = APIRouter()


@collection_router.post("/orders")
async def create_order(
    payload: OrderCreate,
    user_id: CurrentSubject,
    x_request_id: str = Header(...),
) -> dict[str, object]:
    """创建订单，锁库存并按客户端请求 ID 幂等。"""

    async def operation(session: AsyncSession | None) -> IdempotentResult:
        if settings.use_database:
            db_order = await workflow.create_order(
                require_session(session),
                database_user_id(user_id),
                x_request_id,
                payload,
            )
            return IdempotentResult(order_response(db_order), "order", str(db_order.id))
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


@collection_router.get("/orders")
async def list_orders(
    user_id: CurrentSubject,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, alias="pageSize", ge=1, le=100),
    session: AsyncSession = session_dependency,
) -> dict[str, object]:
    """分页读取当前用户订单。"""
    if settings.use_database:
        orders, total = await workflow.list_owned_orders(
            session,
            database_user_id(user_id),
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
            "items": [_memory_order_response(order) for order in memory_orders],
            "meta": {"page": page, "pageSize": page_size, "total": total, "hasNext": page * page_size < total},
        }
    )


@detail_router.get("/orders/{order_id}")
async def get_order(
    order_id: int,
    user_id: CurrentSubject,
    session: AsyncSession = session_dependency,
) -> dict[str, object]:
    """读取当前用户订单详情。"""
    if settings.use_database:
        try:
            order = await workflow.get_owned_order(session, order_id, database_user_id(user_id))
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
        raise ApiError(status_code=404, code=40401, i18n_key="common.not_found", message="订单不存在")
    return success(_memory_order_response(memory_order))


def _memory_order_response(order: Order) -> dict[str, object]:
    """将内存订单映射为与数据库响应一致的订单 DTO。"""
    return {
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
        "expiredAt": None,
    }


router.include_router(collection_router)
router.include_router(detail_router)

__all__ = ["collection_router", "create_order", "detail_router", "get_order", "list_orders", "router"]
