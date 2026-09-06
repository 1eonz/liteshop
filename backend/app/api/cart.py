"""购物车 API，持久化实现使用 Redis Hash。"""

from typing import NoReturn

from fastapi import APIRouter, Header
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..errors import ApiError
from ..schemas.cart import CartItemInput
from ..services.cart import CartError, CartLine, cart_service
from ..services.idempotency import IdempotencyInProgress, IdempotentResult, idempotency_service
from .dependencies import CurrentSubject
from .responses import success

router = APIRouter(tags=["cart"])


def _raise_cart_error(error: Exception, status_code: int = 409) -> NoReturn:
    """把购物车领域异常统一映射到错误信封。"""
    raise ApiError(
        status_code=status_code,
        code=40901 if status_code < 500 else 50001,
        i18n_key="cart.invalid_operation" if status_code < 500 else "common.internal_error",
        message=str(error),
    ) from error


def _response(line: CartLine) -> dict[str, object]:
    """转换购物车领域对象为前端契约字段。"""
    return {
        "id": line.sku_id,
        "skuId": line.sku_id,
        "quantity": line.quantity,
        "priceCents": line.price_cents,
        "stale": False,
    }


@router.get("/cart")
async def get_cart(user_id: CurrentSubject) -> dict[str, object]:
    """读取当前用户 Redis 购物车。"""
    try:
        lines = await cart_service.list(user_id, use_database=settings.use_database)
    except CartError as exc:
        _raise_cart_error(exc, 503)
    return success({"items": [_response(line) for line in lines]})


@router.post("/cart/items")
async def add_cart_item(
    payload: CartItemInput,
    user_id: CurrentSubject,
    x_request_id: str = Header(...),
) -> dict[str, object]:
    """添加购物车项，同一请求 ID 不重复累加。"""

    async def operation(_session: AsyncSession | None) -> IdempotentResult:
        line = await cart_service.add(
            user_id,
            CartLine(payload.sku_id, payload.quantity, payload.price_cents),
            use_database=settings.use_database,
            request_id=f"add:{payload.sku_id}:{x_request_id}",
        )
        return IdempotentResult({"item": _response(line)}, "cart_item", str(line.sku_id))

    try:
        result = await idempotency_service.execute(
            user_id=user_id,
            request_id=x_request_id,
            action_type=f"cart_add:{payload.sku_id}",
            operation=operation,
        )
        return success(result)
    except (CartError, IdempotencyInProgress) as exc:
        _raise_cart_error(exc)


@router.put("/cart/items/{sku_id}")
async def update_cart_item(
    sku_id: int,
    payload: CartItemInput,
    user_id: CurrentSubject,
    x_request_id: str = Header(...),
) -> dict[str, object]:
    """覆盖购物车数量，路径 SKU 与请求体必须一致。"""
    if sku_id != payload.sku_id:
        _raise_cart_error(ValueError("SKU 不一致"), 422)

    async def operation(_session: AsyncSession | None) -> IdempotentResult:
        line = await cart_service.update(
            user_id,
            CartLine(payload.sku_id, payload.quantity, payload.price_cents),
            use_database=settings.use_database,
            request_id=f"update:{sku_id}:{x_request_id}",
        )
        return IdempotentResult({"item": _response(line)}, "cart_item", str(line.sku_id))

    try:
        result = await idempotency_service.execute(
            user_id=user_id,
            request_id=x_request_id,
            action_type=f"cart_update:{sku_id}",
            operation=operation,
        )
        return success(result)
    except (CartError, IdempotencyInProgress) as exc:
        _raise_cart_error(exc)


@router.delete("/cart/items/{sku_id}")
async def remove_cart_item(
    sku_id: int,
    user_id: CurrentSubject,
    x_request_id: str = Header(...),
) -> dict[str, object]:
    """删除购物车项，重复删除保持幂等。"""

    async def operation(_session: AsyncSession | None) -> IdempotentResult:
        await cart_service.remove(
            user_id,
            sku_id,
            use_database=settings.use_database,
            request_id=f"remove:{sku_id}:{x_request_id}",
        )
        return IdempotentResult({"removed": True, "skuId": sku_id}, "cart_item", str(sku_id))

    try:
        result = await idempotency_service.execute(
            user_id=user_id,
            request_id=x_request_id,
            action_type=f"cart_remove:{sku_id}",
            operation=operation,
        )
        return success(result)
    except (CartError, IdempotencyInProgress) as exc:
        _raise_cart_error(exc)
