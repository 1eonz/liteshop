"""管理后台 API 路由。"""

from collections.abc import Awaitable, Callable

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.database import get_session
from ..errors import ApiError
from ..schemas.admin import OrderManagementUpdate, OrderPriceUpdate, ShipOrderRequest
from ..schemas.freight import (
    FreightTemplateCreate,
    FreightTemplateItemCreate,
    FreightTemplateItemUpdate,
    FreightTemplateUpdate,
)
from ..schemas.membership import MemberLevelUpdate, MemberTagsUpdate
from ..schemas.products import CategoryCreate, CategoryUpdate, InventoryAdjust, ProductCreate, ProductUpdate
from ..schemas.review import ReviewAudit
from ..services.admin import AdminPermissionDenied, AdminService
from ..services.idempotency import IdempotencyInProgress, IdempotentResult, idempotency_service
from ..services.membership import MembershipError, membership_service
from ..services.order_workflow import OrderWorkflowError
from ..services.review import review_service
from .dependencies import CurrentSubject
from .responses import success

router = APIRouter(prefix="/admin", tags=["admin"])
admin_service = AdminService()
_session_dependency = Depends(get_session)
AdminWrite = Callable[[AsyncSession, str, str], Awaitable[dict[str, object]]]


def _require_database() -> None:
    """后台真实写操作必须连接本地数据库。"""
    if not settings.use_database:
        raise ApiError(
            status_code=503,
            code=50001,
            i18n_key="common.internal_error",
            message="后台写操作需要本地数据库",
        )


async def _execute_write(
    *,
    subject: str,
    request_id: str,
    action_type: str,
    permission: str,
    resource_type: str,
    operation: AdminWrite,
) -> dict[str, object]:
    """统一执行后台权限校验、幂等事务和错误映射。"""
    _require_database()

    async def idempotent_operation(session: AsyncSession | None) -> IdempotentResult:
        if session is None:
            raise RuntimeError("数据库事务会话未初始化")
        await admin_service.require_permission(session, subject, permission)
        response = await operation(session, subject, request_id)
        resource_id = str(response.get("id", response.get("orderId", response.get("skuId", ""))))
        return IdempotentResult(response, resource_type, resource_id)

    try:
        result = await idempotency_service.execute(
            user_id=subject,
            request_id=request_id,
            action_type=action_type,
            operation=idempotent_operation,
        )
        return success(result)
    except IdempotencyInProgress as exc:
        raise ApiError(
            status_code=429,
            code=42901,
            i18n_key="common.request_in_progress",
            message="请求正在处理中，请稍后再试",
        ) from exc
    except AdminPermissionDenied as exc:
        raise ApiError(
            status_code=403,
            code=40301,
            i18n_key="common.forbidden",
            message=str(exc),
        ) from exc
    except (OrderWorkflowError, KeyError, ValueError) as exc:
        raise ApiError(
            status_code=409,
            code=40901,
            i18n_key="order.invalid_transition",
            message=str(exc),
        ) from exc


async def _authorize_read(session: AsyncSession, subject: str, permission: str) -> str:
    """验证后台读权限并返回主体。"""
    if settings.use_database:
        try:
            await admin_service.require_permission(session, subject, permission)
        except AdminPermissionDenied as exc:
            raise ApiError(
                status_code=403,
                code=40301,
                i18n_key="common.forbidden",
                message=str(exc),
            ) from exc
    return subject


@router.get("/products")
async def list_products(
    subject: CurrentSubject,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, alias="pageSize", ge=1, le=100),
    q: str | None = Query(None, min_length=1, max_length=100),
    session: AsyncSession = _session_dependency,
) -> dict[str, object]:
    """后台商品列表。"""
    _require_database()
    await _authorize_read(session, subject, "product.read")
    return success(
        await admin_service.catalog.list_products(
            session,
            page,
            page_size,
            keyword=q,
            include_off_shelf=True,
        )
    )


@router.post("/categories")
async def create_category(
    payload: CategoryCreate,
    subject: CurrentSubject,
    x_request_id: str = Header(...),
) -> dict[str, object]:
    """创建商品分类。"""
    return await _execute_write(
        subject=subject,
        request_id=x_request_id,
        action_type="admin_category_create",
        permission="product.write",
        resource_type="category",
        operation=lambda session, user_id, request_id: admin_service.create_category(
            session, payload, user_id, request_id
        ),
    )


@router.get("/categories")
async def list_categories(subject: CurrentSubject, session: AsyncSession = _session_dependency) -> dict[str, object]:
    """后台分类管理列表。"""
    _require_database()
    await _authorize_read(session, subject, "product.read")
    return success({"items": await admin_service.list_categories(session)})


@router.put("/categories/{category_id}")
async def update_category(
    category_id: int, payload: CategoryUpdate, subject: CurrentSubject, x_request_id: str = Header(...)
) -> dict[str, object]:
    """更新后台商品分类。"""
    return await _execute_write(
        subject=subject,
        request_id=x_request_id,
        action_type=f"admin_category_update:{category_id}",
        permission="product.write",
        resource_type="category",
        operation=lambda session, user_id, request_id: admin_service.update_category(
            session, category_id, payload, user_id, request_id
        ),
    )


@router.delete("/categories/{category_id}")
async def delete_category(
    category_id: int, subject: CurrentSubject, x_request_id: str = Header(...)
) -> dict[str, object]:
    """停用后台商品分类。"""
    return await _execute_write(
        subject=subject,
        request_id=x_request_id,
        action_type=f"admin_category_delete:{category_id}",
        permission="product.write",
        resource_type="category",
        operation=lambda session, user_id, request_id: admin_service.delete_category(
            session, category_id, user_id, request_id
        ),
    )


@router.post("/products")
async def create_product(
    payload: ProductCreate,
    subject: CurrentSubject,
    x_request_id: str = Header(...),
) -> dict[str, object]:
    """创建商品及 SKU。"""
    return await _execute_write(
        subject=subject,
        request_id=x_request_id,
        action_type="admin_product_create",
        permission="product.write",
        resource_type="product",
        operation=lambda session, user_id, request_id: admin_service.create_product(
            session, payload, user_id, request_id
        ),
    )


@router.put("/products/{product_id}")
async def update_product(
    product_id: int,
    payload: ProductUpdate,
    subject: CurrentSubject,
    x_request_id: str = Header(...),
) -> dict[str, object]:
    """更新商品基础字段。"""
    return await _execute_write(
        subject=subject,
        request_id=x_request_id,
        action_type=f"admin_product_update:{product_id}",
        permission="product.write",
        resource_type="product",
        operation=lambda session, user_id, request_id: admin_service.update_product(
            session, product_id, payload, user_id, request_id
        ),
    )


@router.delete("/products/{product_id}")
async def delete_product(
    product_id: int,
    subject: CurrentSubject,
    x_request_id: str = Header(...),
) -> dict[str, object]:
    """软删除商品。"""
    return await _execute_write(
        subject=subject,
        request_id=x_request_id,
        action_type=f"admin_product_delete:{product_id}",
        permission="product.write",
        resource_type="product",
        operation=lambda session, user_id, request_id: admin_service.delete_product(
            session, product_id, user_id, request_id
        ),
    )


@router.get("/orders")
async def list_orders(
    subject: CurrentSubject,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, alias="pageSize", ge=1, le=100),
    session: AsyncSession = _session_dependency,
) -> dict[str, object]:
    """后台订单列表。"""
    _require_database()
    await _authorize_read(session, subject, "order.read")
    return success(await admin_service.list_orders(session, page, page_size))


@router.post("/orders/{order_id}/ship")
async def ship_order(
    order_id: int,
    payload: ShipOrderRequest,
    subject: CurrentSubject,
    x_request_id: str = Header(...),
) -> dict[str, object]:
    """订单发货。"""
    return await _execute_write(
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
    order_id: int,
    payload: OrderPriceUpdate,
    subject: CurrentSubject,
    x_request_id: str = Header(...),
) -> dict[str, object]:
    """待付款订单改价。"""
    return await _execute_write(
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
    return await _execute_write(
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
    return await _execute_write(
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
    session: AsyncSession = _session_dependency,
) -> dict[str, object]:
    """库存台账列表。"""
    _require_database()
    await _authorize_read(session, subject, "inventory.read")
    return success(await admin_service.list_inventory(session, page, page_size))


@router.get("/members")
async def list_members(
    subject: CurrentSubject,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, alias="pageSize", ge=1, le=100),
    session: AsyncSession = _session_dependency,
) -> dict[str, object]:
    """会员分页列表。"""
    _require_database()
    await _authorize_read(session, subject, "member.read")
    return success(await membership_service.list_members(session, page, page_size))


@router.get("/reviews")
async def list_reviews(subject: CurrentSubject, session: AsyncSession = _session_dependency) -> dict[str, object]:
    """评价审核列表。"""
    _require_database()
    await _authorize_read(session, subject, "review.read")
    reviews = await review_service.repository.list_for_audit(session)
    return success(
        {
            "items": [
                {
                    "id": review.id,
                    "productId": review.product_id,
                    "skuId": review.sku_id,
                    "userId": review.user_id,
                    "rating": review.rating,
                    "content": review.content,
                    "images": list(review.images),
                    "status": review.status,
                    "reason": review.audit_reason,
                    "createdAt": review.created_at.isoformat(),
                }
                for review in reviews
            ]
        }
    )


@router.put("/reviews/{review_id}")
async def audit_review(
    review_id: int,
    payload: ReviewAudit,
    subject: CurrentSubject,
    x_request_id: str = Header(...),
) -> dict[str, object]:
    """审核评价并记录幂等操作。"""
    return await _execute_write(
        subject=subject,
        request_id=x_request_id,
        action_type=f"admin_review_audit:{review_id}",
        permission="review.write",
        resource_type="review",
        operation=lambda session, _user_id, _request_id: review_service.audit(
            session, review_id, payload.status, payload.reason
        ),
    )


@router.get("/members/{user_id}")
async def get_member(
    user_id: int,
    subject: CurrentSubject,
    session: AsyncSession = _session_dependency,
) -> dict[str, object]:
    """会员详情。"""
    _require_database()
    await _authorize_read(session, subject, "member.read")
    try:
        return success(await membership_service.get_member(session, user_id))
    except MembershipError as error:
        raise ApiError(status_code=404, code=40401, i18n_key="common.not_found", message=str(error)) from error


@router.put("/members/{user_id}/tags")
async def update_member_tags(
    user_id: int,
    payload: MemberTagsUpdate,
    subject: CurrentSubject,
    x_request_id: str = Header(...),
) -> dict[str, object]:
    """幂等更新会员标签。"""
    return await _execute_write(
        subject=subject,
        request_id=x_request_id,
        action_type=f"admin_member_tags:{user_id}",
        permission="member.write",
        resource_type="member",
        operation=lambda session, _user_id, _request_id: membership_service.update_tags(session, user_id, payload.tags),
    )


@router.put("/members/{user_id}/level")
async def update_member_level(
    user_id: int,
    payload: MemberLevelUpdate,
    subject: CurrentSubject,
    x_request_id: str = Header(...),
) -> dict[str, object]:
    """幂等更新会员等级。"""
    return await _execute_write(
        subject=subject,
        request_id=x_request_id,
        action_type=f"admin_member_level:{user_id}",
        permission="member.write",
        resource_type="member",
        operation=lambda session, _user_id, _request_id: membership_service.update_level(
            session, user_id, payload.member_level
        ),
    )


@router.post("/inventory/{sku_id}/adjust")
async def adjust_inventory(
    sku_id: int,
    payload: InventoryAdjust,
    subject: CurrentSubject,
    x_request_id: str = Header(...),
) -> dict[str, object]:
    """手工调整库存。"""
    return await _execute_write(
        subject=subject,
        request_id=x_request_id,
        action_type=f"admin_inventory_adjust:{sku_id}",
        permission="inventory.write",
        resource_type="sku",
        operation=lambda session, user_id, request_id: admin_service.adjust_inventory(
            session, sku_id, payload, user_id, request_id
        ),
    )


@router.get("/dashboard")
async def dashboard(
    subject: CurrentSubject,
    session: AsyncSession = _session_dependency,
) -> dict[str, object]:
    """返回核心指标、趋势和商品排行。"""
    _require_database()
    await _authorize_read(session, subject, "dashboard.read")
    return success(await admin_service.dashboard(session))


@router.get("/audit-logs")
async def audit_logs(
    subject: CurrentSubject,
    session: AsyncSession = _session_dependency,
) -> dict[str, object]:
    """返回最近后台操作日志。"""
    _require_database()
    await _authorize_read(session, subject, "audit.read")
    return success({"items": await admin_service.audit_logs(session)})


@router.get("/roles")
async def list_roles(subject: CurrentSubject, session: AsyncSession = _session_dependency) -> dict[str, object]:
    """读取 RBAC 角色列表。"""
    _require_database()
    await _authorize_read(session, subject, "rbac.read")
    return success({"items": await admin_service.list_roles(session)})


@router.get("/permissions")
async def list_permissions(subject: CurrentSubject, session: AsyncSession = _session_dependency) -> dict[str, object]:
    """读取 RBAC 权限点列表。"""
    _require_database()
    await _authorize_read(session, subject, "rbac.read")
    return success({"items": await admin_service.list_permissions(session)})


@router.get("/inventory/{sku_id}/ledger")
async def inventory_ledger(
    sku_id: int, subject: CurrentSubject, session: AsyncSession = _session_dependency
) -> dict[str, object]:
    """读取指定 SKU 的库存流水。"""
    _require_database()
    await _authorize_read(session, subject, "inventory.read")
    return success({"items": await admin_service.inventory_ledgers(session, sku_id)})


@router.get("/freight-templates")
async def list_freight_templates(
    subject: CurrentSubject,
    session: AsyncSession = _session_dependency,
) -> dict[str, object]:
    """读取后台运费模板列表。"""
    _require_database()
    await _authorize_read(session, subject, "settings.read")
    return success({"items": await admin_service.list_freight_templates(session)})


@router.post("/freight-templates")
async def create_freight_template(
    payload: FreightTemplateCreate,
    subject: CurrentSubject,
    x_request_id: str = Header(...),
) -> dict[str, object]:
    """创建运费模板。"""
    return await _execute_write(
        subject=subject,
        request_id=x_request_id,
        action_type="admin_freight_template_create",
        permission="settings.write",
        resource_type="freight_template",
        operation=lambda session, user_id, request_id: admin_service.create_freight_template(
            session, payload, user_id, request_id
        ),
    )


@router.put("/freight-templates/{template_id}")
async def update_freight_template(
    template_id: int,
    payload: FreightTemplateUpdate,
    subject: CurrentSubject,
    x_request_id: str = Header(...),
) -> dict[str, object]:
    """更新运费模板。"""
    return await _execute_write(
        subject=subject,
        request_id=x_request_id,
        action_type=f"admin_freight_template_update:{template_id}",
        permission="settings.write",
        resource_type="freight_template",
        operation=lambda session, user_id, request_id: admin_service.update_freight_template(
            session, template_id, payload, user_id, request_id
        ),
    )


@router.delete("/freight-templates/{template_id}")
async def delete_freight_template(
    template_id: int,
    subject: CurrentSubject,
    x_request_id: str = Header(...),
) -> dict[str, object]:
    """删除运费模板。"""
    return await _execute_write(
        subject=subject,
        request_id=x_request_id,
        action_type=f"admin_freight_template_delete:{template_id}",
        permission="settings.write",
        resource_type="freight_template",
        operation=lambda session, user_id, request_id: admin_service.delete_freight_template(
            session, template_id, user_id, request_id
        ),
    )


@router.post("/freight-templates/{template_id}/items")
async def add_freight_item(
    template_id: int,
    payload: FreightTemplateItemCreate,
    subject: CurrentSubject,
    x_request_id: str = Header(...),
) -> dict[str, object]:
    """为模板增加地区计费项。"""
    return await _execute_write(
        subject=subject,
        request_id=x_request_id,
        action_type=f"admin_freight_item_create:{template_id}",
        permission="settings.write",
        resource_type="freight_template",
        operation=lambda session, user_id, request_id: admin_service.add_freight_item(
            session, template_id, payload, user_id, request_id
        ),
    )


@router.put("/freight-templates/{template_id}/items/{item_id}")
async def update_freight_item(
    template_id: int,
    item_id: int,
    payload: FreightTemplateItemUpdate,
    subject: CurrentSubject,
    x_request_id: str = Header(...),
) -> dict[str, object]:
    """更新地区计费项。"""
    return await _execute_write(
        subject=subject,
        request_id=x_request_id,
        action_type=f"admin_freight_item_update:{item_id}",
        permission="settings.write",
        resource_type="freight_template",
        operation=lambda session, user_id, request_id: admin_service.update_freight_item(
            session, template_id, item_id, payload, user_id, request_id
        ),
    )


@router.delete("/freight-templates/{template_id}/items/{item_id}")
async def delete_freight_item(
    template_id: int,
    item_id: int,
    subject: CurrentSubject,
    x_request_id: str = Header(...),
) -> dict[str, object]:
    """删除地区计费项。"""
    return await _execute_write(
        subject=subject,
        request_id=x_request_id,
        action_type=f"admin_freight_item_delete:{item_id}",
        permission="settings.write",
        resource_type="freight_template",
        operation=lambda session, user_id, request_id: admin_service.delete_freight_item(
            session, template_id, item_id, user_id, request_id
        ),
    )
