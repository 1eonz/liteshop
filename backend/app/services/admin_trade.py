"""管理后台订单与库存领域服务。"""

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from ..enums.order import OrderStatus
from ..schemas.admin import OrderManagementUpdate, OrderPriceUpdate, ShipOrderRequest, validate_address_snapshot
from ..schemas.products import InventoryAdjust
from .admin_core import AdminServiceCore
from .order_workflow import OrderWorkflowError, order_response


class AdminTradeService(AdminServiceCore):
    """编排订单状态变更、库存调整和审计记录。"""

    async def list_orders(self, session: AsyncSession, page: int, page_size: int) -> dict[str, object]:
        """后台分页读取订单。"""
        orders, total = await self.orders.orders.list_all(session, (page - 1) * page_size, page_size)
        return {
            "items": [order_response(order) for order in orders],
            "meta": {"page": page, "pageSize": page_size, "total": total, "hasNext": page * page_size < total},
        }

    async def ship_order(
        self, session: AsyncSession, order_id: int, payload: ShipOrderRequest, user_id: str, request_id: str
    ) -> dict[str, object]:
        """发货并在同一事务扣减库存与写日志。"""
        current = await self.orders.orders.get_for_update(session, order_id)
        before_data = order_response(current)
        order = await self.orders.ship_order(
            session, order_id, payload.logistics_company_code, payload.tracking_no, request_id
        )
        await self.audit(
            session,
            user_id=user_id,
            resource_type="ORDER",
            resource_id=order_id,
            action="SHIP",
            request_id=request_id,
            before_data=before_data,
            after_data=order_response(order),
        )
        return order_response(order)

    async def change_order_price(
        self, session: AsyncSession, order_id: int, payload: OrderPriceUpdate, user_id: str, request_id: str
    ) -> dict[str, object]:
        """改价并在同一事务写日志。"""
        current = await self.orders.orders.get_for_update(session, order_id)
        before_data = order_response(current)
        order = await self.orders.change_order_price(session, order_id, payload.total_amount)
        await self.audit(
            session,
            user_id=user_id,
            resource_type="ORDER",
            resource_id=order_id,
            action="CHANGE_PRICE",
            request_id=request_id,
            before_data=before_data,
            after_data=order_response(order),
        )
        return order_response(order)

    async def cancel_order(
        self, session: AsyncSession, order_id: int, user_id: str, request_id: str
    ) -> dict[str, object]:
        """后台取消待支付订单并记录审计日志。"""
        current = await self.orders.orders.get_for_update(session, order_id)
        before_data = order_response(current)
        order = await self.orders.cancel_order(session, order_id, request_id, reason="管理员取消")
        response = order_response(order)
        await self.audit(
            session,
            user_id=user_id,
            resource_type="ORDER",
            resource_id=order_id,
            action="CANCEL",
            request_id=request_id,
            before_data=before_data,
            after_data=response,
        )
        return response

    async def update_order(
        self, session: AsyncSession, order_id: int, payload: OrderManagementUpdate, user_id: str, request_id: str
    ) -> dict[str, object]:
        """更新后台允许编辑的订单备注和地址快照。"""
        order = await self.orders.orders.get_for_update(session, order_id)
        before_data = order_response(order)
        if payload.remark is not None:
            order.remark = payload.remark
        if payload.address_snapshot is not None:
            try:
                current_status = OrderStatus(order.status)
            except ValueError as exc:
                raise OrderWorkflowError(f"订单状态无效: {order.status}") from exc
            if current_status not in {OrderStatus.PENDING_PAYMENT, OrderStatus.PAID}:
                raise OrderWorkflowError("只有待付款或已支付订单可以修改收货地址")
            validate_address_snapshot(payload.address_snapshot)
            order.address_snapshot = payload.address_snapshot
        order.updated_at = datetime.now(UTC)
        await self.orders.orders.flush(session)
        response = order_response(order)
        await self.audit(
            session,
            user_id=user_id,
            resource_type="ORDER",
            resource_id=order_id,
            action="UPDATE",
            request_id=request_id,
            before_data=before_data,
            after_data=response,
        )
        return response

    async def list_inventory(self, session: AsyncSession, page: int, page_size: int) -> dict[str, object]:
        """返回三层库存和安全库存预警。"""
        skus, total = await self.inventory.list_stock(session, (page - 1) * page_size, page_size)
        return {
            "items": [
                {
                    "skuId": sku.id,
                    "skuCode": sku.code,
                    "name": sku.name,
                    "physicalStock": sku.physical_stock,
                    "availableStock": sku.available_stock,
                    "lockedStock": sku.locked_stock,
                    "safetyStock": sku.safety_stock,
                    "warning": sku.available_stock <= sku.safety_stock,
                }
                for sku in skus
            ],
            "meta": {"page": page, "pageSize": page_size, "total": total, "hasNext": page * page_size < total},
        }

    async def adjust_inventory(
        self, session: AsyncSession, sku_id: int, payload: InventoryAdjust, user_id: str, request_id: str
    ) -> dict[str, object]:
        """手工调整库存并记录原因。"""
        sku = await self.inventory.adjust(session, sku_id, payload.quantity, payload.reason, request_id)
        before_data: dict[str, object] = {
            "physicalStock": sku.physical_stock - payload.quantity,
            "lockedStock": sku.locked_stock,
            "availableStock": sku.physical_stock - payload.quantity - sku.locked_stock,
        }
        after_data: dict[str, object] = {
            "physicalStock": sku.physical_stock,
            "lockedStock": sku.locked_stock,
            "availableStock": sku.available_stock,
        }
        await self.audit(
            session,
            user_id=user_id,
            resource_type="SKU",
            resource_id=sku_id,
            action="ADJUST_STOCK",
            request_id=request_id,
            before_data=before_data,
            after_data={**after_data, "reason": payload.reason},
        )
        return {
            "skuId": sku.id,
            "physicalStock": sku.physical_stock,
            "availableStock": sku.available_stock,
            "lockedStock": sku.locked_stock,
        }

    async def inventory_ledgers(self, session: AsyncSession, sku_id: int) -> list[dict[str, object]]:
        """返回指定 SKU 的库存流水。"""
        entries = await self.inventory.list_ledgers(session, sku_id)
        return [
            {
                "id": entry.id,
                "skuId": entry.sku_id,
                "eventType": entry.event_type,
                "quantity": entry.quantity,
                "physicalBefore": entry.physical_before,
                "physicalAfter": entry.physical_after,
                "lockedBefore": entry.locked_before,
                "lockedAfter": entry.locked_after,
                "referenceNo": entry.reference_no,
                "reason": entry.reason,
                "createdAt": entry.created_at.isoformat(),
            }
            for entry in entries
        ]
