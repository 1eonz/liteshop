"""管理后台商品、订单、库存、权限和审计用例。"""

from datetime import UTC, datetime

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from ..enums.order import OrderStatus
from ..models.operation_log import OperationLog
from ..models.user import Role
from ..repositories.admin import AdminRepository
from ..repositories.inventory import InventoryRepository
from ..repositories.operation_log import OperationLogRepository
from ..schemas.admin import (
    OrderManagementUpdate,
    OrderPriceUpdate,
    RoleCreate,
    RoleUpdate,
    ShipOrderRequest,
    UserRolesUpdate,
    validate_address_snapshot,
)
from ..schemas.freight import (
    FreightTemplateCreate,
    FreightTemplateItemCreate,
    FreightTemplateItemUpdate,
    FreightTemplateUpdate,
)
from ..schemas.products import CategoryCreate, CategoryUpdate, InventoryAdjust, ProductCreate, ProductUpdate
from .freight import FreightService
from .order_workflow import OrderWorkflow, OrderWorkflowError, order_response
from .product_catalog import ProductCatalogService


class AdminPermissionDenied(PermissionError):
    """管理员缺少所需权限。"""


class AdminService:
    """集中管理后台业务，API 层不直接访问仓储。"""

    def __init__(self) -> None:
        self.catalog = ProductCatalogService()
        self.orders = OrderWorkflow()
        self.inventory = InventoryRepository()
        self.repository = AdminRepository()
        self.freight = FreightService()

    async def require_permission(self, session: AsyncSession, subject: str, permission: str) -> None:
        """按数据库 RBAC 校验权限；不存在开发或生产硬编码后门。"""
        try:
            user_id = int(subject)
        except ValueError as exc:
            raise AdminPermissionDenied("无效管理员身份") from exc
        if not await self.repository.has_permission(session, user_id, permission):
            raise AdminPermissionDenied("缺少操作权限")

    @staticmethod
    async def audit(
        session: AsyncSession,
        *,
        user_id: str,
        resource_type: str,
        resource_id: int | None,
        action: str,
        request_id: str,
        before_data: dict[str, object] | None,
        after_data: dict[str, object] | None,
    ) -> None:
        """在同一业务事务中写入操作日志。"""
        request_context = structlog.contextvars.get_contextvars()
        await OperationLogRepository(session).append(
            OperationLog(
                admin_id=int(user_id) if user_id.isdigit() else None,
                resource_type=resource_type,
                resource_id=resource_id,
                action=action,
                request_id=request_id,
                before_data=before_data,
                after_data=after_data,
                ip=str(request_context.get("ip", "")),
                user_agent=str(request_context.get("user_agent", "")),
                created_at=datetime.now(UTC),
            )
        )

    async def list_products(self, session: AsyncSession, page: int, page_size: int) -> dict[str, object]:
        """后台读取全部未删除商品。"""
        return await self.catalog.list_products(
            session,
            page,
            page_size,
            include_off_shelf=True,
        )

    async def create_category(
        self,
        session: AsyncSession,
        payload: CategoryCreate,
        user_id: str,
        request_id: str,
    ) -> dict[str, object]:
        """创建分类并记录审计日志。"""
        category = await self.catalog.create_category(session, payload)
        await self.audit(
            session,
            user_id=user_id,
            resource_type="CATEGORY",
            resource_id=category.id,
            action="CREATE",
            request_id=request_id,
            before_data=None,
            after_data={"id": category.id, "name": category.name},
        )
        return {"id": category.id, "name": category.name}

    async def list_categories(self, session: AsyncSession) -> list[dict[str, object]]:
        """读取后台分类管理列表。"""
        return await self.catalog.categories(session)

    async def update_category(
        self, session: AsyncSession, category_id: int, payload: CategoryUpdate, user_id: str, request_id: str
    ) -> dict[str, object]:
        """更新分类并记录审计日志。"""
        category = await self.catalog.update_category(session, category_id, payload)
        response: dict[str, object] = {
            "id": category.id,
            "parentId": category.parent_id,
            "name": category.name,
            "icon": category.icon,
            "sortOrder": category.sort_order,
            "isActive": category.is_active,
        }
        await self.audit(
            session,
            user_id=user_id,
            resource_type="CATEGORY",
            resource_id=category_id,
            action="UPDATE",
            request_id=request_id,
            before_data=None,
            after_data=response,
        )
        return response

    async def delete_category(
        self, session: AsyncSession, category_id: int, user_id: str, request_id: str
    ) -> dict[str, object]:
        """停用分类并记录审计日志。"""
        category = await self.catalog.delete_category(session, category_id)
        response: dict[str, object] = {"deleted": True, "categoryId": category.id}
        await self.audit(
            session,
            user_id=user_id,
            resource_type="CATEGORY",
            resource_id=category_id,
            action="DELETE",
            request_id=request_id,
            before_data=None,
            after_data=response,
        )
        return response

    async def create_product(
        self,
        session: AsyncSession,
        payload: ProductCreate,
        user_id: str,
        request_id: str,
    ) -> dict[str, object]:
        """创建商品和 SKU 并记录审计日志。"""
        product = await self.catalog.create_product(session, payload)
        response = self.catalog.detail(product)
        await self.audit(
            session,
            user_id=user_id,
            resource_type="PRODUCT",
            resource_id=product.id,
            action="CREATE",
            request_id=request_id,
            before_data=None,
            after_data=response,
        )
        return response

    async def update_product(
        self,
        session: AsyncSession,
        product_id: int,
        payload: ProductUpdate,
        user_id: str,
        request_id: str,
    ) -> dict[str, object]:
        """更新商品基础信息并记录审计日志。"""
        current = await self.catalog.products.get_spu(session, product_id, for_update=True)
        before_data = self.catalog.detail(current)
        product = await self.catalog.update_product(session, product_id, payload)
        after_data = self.catalog.detail(product)
        await self.audit(
            session,
            user_id=user_id,
            resource_type="PRODUCT",
            resource_id=product_id,
            action="UPDATE",
            request_id=request_id,
            before_data=before_data,
            after_data=after_data,
        )
        return after_data

    async def delete_product(
        self,
        session: AsyncSession,
        product_id: int,
        user_id: str,
        request_id: str,
    ) -> dict[str, object]:
        """软删除商品并记录审计日志。"""
        current = await self.catalog.products.get_spu(session, product_id, for_update=True)
        before_data = self.catalog.detail(current)
        product = await self.catalog.soft_delete_product(session, product_id)
        await self.audit(
            session,
            user_id=user_id,
            resource_type="PRODUCT",
            resource_id=product_id,
            action="DELETE",
            request_id=request_id,
            before_data=before_data,
            after_data=self.catalog.detail(product),
        )
        return {"deleted": True, "productId": product_id}

    async def list_orders(
        self,
        session: AsyncSession,
        page: int,
        page_size: int,
    ) -> dict[str, object]:
        """后台分页读取订单。"""
        orders, total = await self.orders.orders.list_all(session, (page - 1) * page_size, page_size)
        return {
            "items": [order_response(order) for order in orders],
            "meta": {
                "page": page,
                "pageSize": page_size,
                "total": total,
                "hasNext": page * page_size < total,
            },
        }

    async def ship_order(
        self,
        session: AsyncSession,
        order_id: int,
        payload: ShipOrderRequest,
        user_id: str,
        request_id: str,
    ) -> dict[str, object]:
        """发货并在同一事务扣减库存与写日志。"""
        current = await self.orders.orders.get_for_update(session, order_id)
        before_data = order_response(current)
        order = await self.orders.ship_order(
            session,
            order_id,
            payload.logistics_company_code,
            payload.tracking_no,
            request_id,
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
        self,
        session: AsyncSession,
        order_id: int,
        payload: OrderPriceUpdate,
        user_id: str,
        request_id: str,
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
        await session.flush()
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
        self,
        session: AsyncSession,
        sku_id: int,
        payload: InventoryAdjust,
        user_id: str,
        request_id: str,
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

    async def dashboard(self, session: AsyncSession) -> dict[str, object]:
        """读取数据看板聚合。"""
        return await self.repository.dashboard(session)

    async def audit_logs(self, session: AsyncSession) -> list[dict[str, object]]:
        """返回结构化操作日志。"""
        logs = await self.repository.list_audit_logs(session)
        return [
            {
                "id": log.id,
                "adminId": log.admin_id,
                "resourceType": log.resource_type,
                "resourceId": log.resource_id,
                "action": log.action,
                "requestId": log.request_id,
                "beforeData": log.before_data,
                "afterData": log.after_data,
                "ip": log.ip,
                "userAgent": log.user_agent,
                "createdAt": log.created_at.isoformat(),
            }
            for log in logs
        ]

    async def list_roles(self, session: AsyncSession) -> list[dict[str, object]]:
        """返回角色及权限点，供后台 RBAC 页面展示。"""
        roles = await self.repository.list_roles(session)
        return [
            {"id": role.id, "name": role.name, "permissions": [permission.code for permission in role.permissions]}
            for role in roles
        ]

    async def list_permissions(self, session: AsyncSession) -> list[dict[str, object]]:
        """返回系统权限点。"""
        permissions = await self.repository.list_permissions(session)
        return [{"id": permission.id, "code": permission.code} for permission in permissions]

    async def list_users_with_roles(self, session: AsyncSession) -> list[dict[str, object]]:
        """返回管理员角色分配页面所需的最小用户快照。"""
        users = await self.repository.list_users_with_roles(session)
        return [
            {
                "id": user.id,
                "nickname": user.nickname,
                "phone": user.phone,
                "roleIds": [role.id for role in user.roles],
            }
            for user in users
        ]

    @staticmethod
    def _role_response(role: Role) -> dict[str, object]:
        """把角色 ORM 转为后台契约响应。"""
        return {
            "id": role.id,
            "name": role.name,
            "permissions": [permission.code for permission in role.permissions],
        }

    async def create_role(
        self, session: AsyncSession, payload: RoleCreate, user_id: str, request_id: str
    ) -> dict[str, object]:
        """创建角色并记录审计日志。"""
        name = payload.name.strip()
        if await self.repository.get_role_by_name(session, name) is not None:
            raise ValueError("角色名称已存在")
        permissions = await self.repository.get_permissions_by_codes(
            session, list(dict.fromkeys(payload.permission_codes))
        )
        if len(permissions) != len(set(payload.permission_codes)):
            raise ValueError("包含不存在的权限点")
        role = Role(name=name, permissions=permissions)
        session.add(role)
        await session.flush()
        response = self._role_response(role)
        await self.audit(
            session,
            user_id=user_id,
            resource_type="ROLE",
            resource_id=role.id,
            action="CREATE",
            request_id=request_id,
            before_data=None,
            after_data=response,
        )
        return response

    async def update_role(
        self, session: AsyncSession, role_id: int, payload: RoleUpdate, user_id: str, request_id: str
    ) -> dict[str, object]:
        """更新角色名称和权限绑定。"""
        role = await self.repository.get_role(session, role_id, for_update=True)
        if role is None:
            raise ValueError("角色不存在")
        before = self._role_response(role)
        changes = payload.model_dump(exclude_unset=True, by_alias=False)
        if "name" in changes and changes["name"] is not None:
            name = str(changes["name"]).strip()
            duplicate = await self.repository.get_role_by_name(session, name)
            if duplicate is not None and duplicate.id != role_id:
                raise ValueError("角色名称已存在")
            role.name = name
        if "permission_codes" in changes and changes["permission_codes"] is not None:
            codes = list(dict.fromkeys(str(code) for code in changes["permission_codes"]))
            permissions = await self.repository.get_permissions_by_codes(session, codes)
            if len(permissions) != len(set(codes)):
                raise ValueError("包含不存在的权限点")
            if user_id.isdigit():
                operator = await self.repository.get_user_with_roles(session, int(user_id), for_update=True)
                if operator is not None and any(item.id == role_id for item in operator.roles):
                    other_codes = {
                        permission.code
                        for assigned_role in operator.roles
                        if assigned_role.id != role_id
                        for permission in assigned_role.permissions
                    }
                    if "rbac.write" not in set(codes) | other_codes:
                        raise ValueError("不能移除自己最后的权限管理能力")
            role.permissions = permissions
        await session.flush()
        response = self._role_response(role)
        await self.audit(
            session,
            user_id=user_id,
            resource_type="ROLE",
            resource_id=role.id,
            action="UPDATE",
            request_id=request_id,
            before_data=before,
            after_data=response,
        )
        return response

    async def delete_role(
        self, session: AsyncSession, role_id: int, user_id: str, request_id: str
    ) -> dict[str, object]:
        """删除未分配给管理员的角色，避免权限悬挂。"""
        role = await self.repository.get_role(session, role_id, for_update=True)
        if role is None:
            raise ValueError("角色不存在")
        if await self.repository.count_role_users(session, role_id):
            raise ValueError("角色仍绑定管理员，不能删除")
        before = self._role_response(role)
        await session.delete(role)
        await session.flush()
        await self.audit(
            session,
            user_id=user_id,
            resource_type="ROLE",
            resource_id=role_id,
            action="DELETE",
            request_id=request_id,
            before_data=before,
            after_data={"deleted": True},
        )
        return {"deleted": True, "roleId": role_id}

    async def update_user_roles(
        self, session: AsyncSession, user_id: int, payload: UserRolesUpdate, operator_id: str, request_id: str
    ) -> dict[str, object]:
        """覆盖管理员角色集合并写入审计记录。"""
        user = await self.repository.get_user_with_roles(session, user_id, for_update=True)
        if user is None:
            raise ValueError("管理员不存在")
        role_ids = list(dict.fromkeys(payload.role_ids))
        roles = await self.repository.list_roles_by_ids(session, role_ids)
        if len(roles) != len(role_ids):
            raise ValueError("包含不存在的角色")
        if operator_id.isdigit() and int(operator_id) == user_id:
            retained_codes = {permission.code for role in roles for permission in role.permissions}
            if "rbac.write" not in retained_codes:
                raise ValueError("不能移除自己最后的权限管理能力")
        before = {"userId": user.id, "roleIds": [role.id for role in user.roles]}
        user.roles = roles
        await session.flush()
        response = {
            "id": user.id,
            "nickname": user.nickname,
            "phone": user.phone,
            "roleIds": [role.id for role in user.roles],
        }
        await self.audit(
            session,
            user_id=operator_id,
            resource_type="USER_ROLE",
            resource_id=user.id,
            action="UPDATE",
            request_id=request_id,
            before_data=before,
            after_data=response,
        )
        return response

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

    async def list_freight_templates(self, session: AsyncSession) -> list[dict[str, object]]:
        """读取后台运费模板。"""
        return await self.freight.list_templates(session)

    async def create_freight_template(
        self, session: AsyncSession, payload: FreightTemplateCreate, user_id: str, request_id: str
    ) -> dict[str, object]:
        """创建运费模板并记录操作日志。"""
        response = await self.freight.create_template(session, payload)
        await self.audit(
            session,
            user_id=user_id,
            resource_type="FREIGHT_TEMPLATE",
            resource_id=int(str(response["id"])),
            action="CREATE",
            request_id=request_id,
            before_data=None,
            after_data=response,
        )
        return response

    async def update_freight_template(
        self, session: AsyncSession, template_id: int, payload: FreightTemplateUpdate, user_id: str, request_id: str
    ) -> dict[str, object]:
        """更新运费模板并记录操作日志。"""
        response = await self.freight.update_template(session, template_id, payload)
        await self.audit(
            session,
            user_id=user_id,
            resource_type="FREIGHT_TEMPLATE",
            resource_id=template_id,
            action="UPDATE",
            request_id=request_id,
            before_data=None,
            after_data=response,
        )
        return response

    async def delete_freight_template(
        self, session: AsyncSession, template_id: int, user_id: str, request_id: str
    ) -> dict[str, object]:
        """删除运费模板并记录操作日志。"""
        response = await self.freight.delete_template(session, template_id)
        await self.audit(
            session,
            user_id=user_id,
            resource_type="FREIGHT_TEMPLATE",
            resource_id=template_id,
            action="DELETE",
            request_id=request_id,
            before_data=None,
            after_data=response,
        )
        return response

    async def add_freight_item(
        self, session: AsyncSession, template_id: int, payload: FreightTemplateItemCreate, user_id: str, request_id: str
    ) -> dict[str, object]:
        """增加运费模板计费项并记录操作日志。"""
        response = await self.freight.add_item(session, template_id, payload)
        await self.audit(
            session,
            user_id=user_id,
            resource_type="FREIGHT_TEMPLATE",
            resource_id=template_id,
            action="ITEM_CREATE",
            request_id=request_id,
            before_data=None,
            after_data=response,
        )
        return response

    async def update_freight_item(
        self,
        session: AsyncSession,
        template_id: int,
        item_id: int,
        payload: FreightTemplateItemUpdate,
        user_id: str,
        request_id: str,
    ) -> dict[str, object]:
        """更新运费模板计费项并记录操作日志。"""
        response = await self.freight.update_item(session, template_id, item_id, payload)
        await self.audit(
            session,
            user_id=user_id,
            resource_type="FREIGHT_TEMPLATE",
            resource_id=template_id,
            action="ITEM_UPDATE",
            request_id=request_id,
            before_data=None,
            after_data=response,
        )
        return response

    async def delete_freight_item(
        self, session: AsyncSession, template_id: int, item_id: int, user_id: str, request_id: str
    ) -> dict[str, object]:
        """删除运费模板计费项并记录操作日志。"""
        response = await self.freight.delete_item(session, template_id, item_id)
        await self.audit(
            session,
            user_id=user_id,
            resource_type="FREIGHT_TEMPLATE",
            resource_id=template_id,
            action="ITEM_DELETE",
            request_id=request_id,
            before_data=None,
            after_data=response,
        )
        return response
