"""管理后台查询仓储。"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.operation_log import OperationLog
from ..models.order import Order, OrderItem
from ..models.product import Sku, Spu
from ..models.user import Permission, Role, role_permissions, user_roles


class AdminRepository:
    """封装后台统计、权限与日志查询。"""

    async def has_permission(self, session: AsyncSession, user_id: int, permission_code: str) -> bool:
        """检查用户是否通过角色拥有权限点。"""
        statement = (
            select(func.count(Permission.id))
            .select_from(user_roles)
            .join(Role, Role.id == user_roles.c.role_id)
            .join(role_permissions, role_permissions.c.role_id == Role.id)
            .join(Permission, Permission.id == role_permissions.c.permission_id)
            .where(user_roles.c.user_id == user_id, Permission.code == permission_code)
        )
        return bool(await session.scalar(statement))

    async def dashboard(self, session: AsyncSession) -> dict[str, object]:
        """聚合核心指标和商品销量排行。"""
        paid_statuses = ["PAID", "SHIPPED", "COMPLETED"]
        order_count = int(
            await session.scalar(select(func.count(Order.id)).where(Order.status.in_(paid_statuses))) or 0
        )
        paid_sales = int(
            await session.scalar(
                select(func.coalesce(func.sum(Order.paid_amount), 0)).where(Order.status.in_(paid_statuses))
            )
            or 0
        )
        pending_shipments = int(await session.scalar(select(func.count(Order.id)).where(Order.status == "PAID")) or 0)
        product_count = int(await session.scalar(select(func.count(Spu.id)).where(Spu.deleted_at.is_(None))) or 0)
        low_stock_skus = int(
            await session.scalar(
                select(func.count(Sku.id)).where(Sku.physical_stock - Sku.locked_stock <= Sku.safety_stock)
            )
            or 0
        )
        ranking_rows = await session.execute(
            select(OrderItem.product_name, func.sum(OrderItem.quantity).label("quantity"))
            .join(Order, Order.id == OrderItem.order_id)
            .where(Order.status.in_(paid_statuses))
            .group_by(OrderItem.product_name)
            .order_by(func.sum(OrderItem.quantity).desc())
            .limit(10)
        )
        ranking = [{"name": str(name), "salesCount": int(quantity)} for name, quantity in ranking_rows.all()]
        trend_start = datetime.now(UTC) - timedelta(days=6)
        trend_rows = await session.execute(
            select(
                func.date_trunc("day", Order.paid_at).label("day"),
                func.coalesce(func.sum(Order.paid_amount), 0).label("amount"),
                func.count(Order.id).label("order_count"),
            )
            .where(Order.status.in_(paid_statuses), Order.paid_at.is_not(None), Order.paid_at >= trend_start)
            .group_by(func.date_trunc("day", Order.paid_at))
            .order_by(func.date_trunc("day", Order.paid_at))
        )
        trend = [
            {
                "date": day.date().isoformat() if day is not None else "",
                "amount": int(amount or 0),
                "orderCount": int(order_count_value),
            }
            for day, amount, order_count_value in trend_rows.all()
        ]
        return {
            "metrics": {
                "salesAmount": paid_sales,
                "orderCount": order_count,
                "productCount": product_count,
                "pendingShipmentCount": pending_shipments,
            },
            "trend": trend,
            "ranking": ranking,
            "todo": {"pendingShipments": pending_shipments, "lowStockSkus": low_stock_skus, "auditItems": 0},
        }

    async def list_audit_logs(self, session: AsyncSession, limit: int = 100) -> list[OperationLog]:
        """读取最近操作日志。"""
        result = await session.scalars(select(OperationLog).order_by(OperationLog.created_at.desc()).limit(limit))
        return list(result.all())

    async def list_roles(self, session: AsyncSession) -> list[Role]:
        """读取 RBAC 角色和权限点。"""
        result = await session.scalars(select(Role).options(selectinload(Role.permissions)).order_by(Role.id))
        return list(result.unique().all())

    async def list_permissions(self, session: AsyncSession) -> list[Permission]:
        """读取系统权限点。"""
        result = await session.scalars(select(Permission).order_by(Permission.code))
        return list(result.all())
