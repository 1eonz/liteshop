"""管理后台订单与库存路由。"""

from fastapi import APIRouter, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...schemas.admin import OrderManagementUpdate, OrderPriceUpdate, ShipOrderRequest
from ...schemas.products import InventoryAdjust
from ..dependencies import CurrentSubject
from ..responses import success
from .common import admin_service, authorize_read, execute_write, require_database, session_dependency

router = APIRouter()


@router.get("/orders")
async def list_orders(
    subject: CurrentSubject,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, alias="pageSize", ge=1, le=100),
    session: AsyncSession = session_dependency,
) -> dict[str, object]:
    """后台订单列表。"""
    require_database()
    await authorize_read(session, subject, "order.read")
    return success(await admin_service.list_orders(session, page, page_size))


@router.post("/orders/{order_id}/ship")
async def ship_order(
    order_id: int, payload: ShipOrderRequest, subject: CurrentSubject, x_request_id: str = Header(...)
) -> dict[str, object]:
    """订单发货。"""
    return await execute_write(
        subject=subject,
        request_id=x_request_id,
        action_type=f"admin_order_ship:{order_id}",
        permission="order.ship",
        resource_type="order",
        operation=lambda session, user_id, request_id: admin_service.ship_order(
            session, order_id, payload, user_id, request_id
        ),
    )


@router.post("/orders/{order_id}/price")
async def change_order_price(
    order_id: int, payload: OrderPriceUpdate, subject: CurrentSubject, x_request_id: str = Header(...)
) -> dict[str, object]:
    """待付款订单改价。"""
    return await execute_write(
        subject=subject,
        request_id=x_request_id,
        action_type=f"admin_order_price:{order_id}",
        permission="order.price",
        resource_type="order",
        operation=lambda session, user_id, request_id: admin_service.change_order_price(
            session, order_id, payload, user_id, request_id
        ),
    )


@router.post("/orders/{order_id}/cancel")
async def cancel_admin_order(
    order_id: int, subject: CurrentSubject, x_request_id: str = Header(...)
) -> dict[str, object]:
    """后台取消待支付订单。"""
    return await execute_write(
        subject=subject,
        request_id=x_request_id,
        action_type=f"admin_order_cancel:{order_id}",
        permission="order.cancel",
        resource_type="order",
        operation=lambda session, user_id, request_id: admin_service.cancel_order(
            session, order_id, user_id, request_id
        ),
    )


@router.put("/orders/{order_id}")
async def update_admin_order(
    order_id: int, payload: OrderManagementUpdate, subject: CurrentSubject, x_request_id: str = Header(...)
) -> dict[str, object]:
    """后台更新订单备注和地址快照。"""
    return await execute_write(
        subject=subject,
        request_id=x_request_id,
        action_type=f"admin_order_update:{order_id}",
        permission="order.write",
        resource_type="order",
        operation=lambda session, user_id, request_id: admin_service.update_order(
            session, order_id, payload, user_id, request_id
        ),
    )


@router.get("/inventory")
async def list_inventory(
    subject: CurrentSubject,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, alias="pageSize", ge=1, le=100),
    session: AsyncSession = session_dependency,
) -> dict[str, object]:
    """库存台账列表。"""
    require_database()
    await authorize_read(session, subject, "inventory.read")
    return success(await admin_service.list_inventory(session, page, page_size))


@router.post("/inventory/{sku_id}/adjust")
async def adjust_inventory(
    sku_id: int, payload: InventoryAdjust, subject: CurrentSubject, x_request_id: str = Header(...)
) -> dict[str, object]:
    """手工调整库存。"""
    return await execute_write(
        subject=subject,
        request_id=x_request_id,
        action_type=f"admin_inventory_adjust:{sku_id}",
        permission="inventory.write",
        resource_type="sku",
        operation=lambda session, user_id, request_id: admin_service.adjust_inventory(
            session, sku_id, payload, user_id, request_id
        ),
    )


@router.get("/inventory/{sku_id}/ledger")
async def inventory_ledger(
    sku_id: int, subject: CurrentSubject, session: AsyncSession = session_dependency
) -> dict[str, object]:
    """读取指定 SKU 的库存流水。"""
    require_database()
    await authorize_read(session, subject, "inventory.read")
    return success({"items": await admin_service.inventory_ledgers(session, sku_id)})
