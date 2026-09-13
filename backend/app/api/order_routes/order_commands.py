"""用户订单状态变更路由。"""

from fastapi import APIRouter, Header
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import settings
from ...enums.order import OrderStatus
from ...errors import ApiError
from ...services.idempotency import IdempotencyInProgress, IdempotentResult
from ...services.order_workflow import OrderWorkflowError, order_response
from ..dependencies import CurrentSubject
from ..responses import success
from .common import database_user_id, idempotency_service, order_service, require_session, workflow

router = APIRouter()


async def change_order_status(
    order_id: int,
    request_id: str,
    user_id: str,
    target: OrderStatus,
) -> dict[str, object]:
    """统一执行取消或确认收货的幂等状态流转。"""

    async def operation(session: AsyncSession | None) -> IdempotentResult:
        if settings.use_database:
            changed_db_order = (
                await workflow.cancel_owned_order(
                    require_session(session), order_id, database_user_id(user_id), request_id
                )
                if target is OrderStatus.CANCELLED
                else await workflow.confirm_owned_order(require_session(session), order_id, database_user_id(user_id))
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
        return success(await change_order_status(order_id, x_request_id, user_id, OrderStatus.CANCELLED))
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
        return success(await change_order_status(order_id, x_request_id, user_id, OrderStatus.COMPLETED))
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


__all__ = ["cancel_order", "change_order_status", "confirm_order", "router"]
