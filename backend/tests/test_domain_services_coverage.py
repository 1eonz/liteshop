"""领域服务正常、异常和边界分支测试。"""

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums.after_sale import AfterSaleStatus, AfterSaleType
from app.models.freight import FreightTemplate
from app.models.product import Spu
from app.models.user import Permission, Role
from app.schemas.admin import RoleCreate, RoleUpdate, UserRolesUpdate
from app.schemas.freight import (
    FreightCalculateRequest,
    FreightLineInput,
    FreightTemplateCreate,
    FreightTemplateItemCreate,
    FreightTemplateItemUpdate,
    FreightTemplateUpdate,
)
from app.schemas.products import CategoryCreate, CategoryUpdate, ProductCreate, ProductUpdate, SkuCreate
from app.services.admin_access import AdminAccessService
from app.services.after_sale import AfterSaleService
from app.services.freight import FreightError, FreightService
from app.services.product_catalog import ProductCatalogService
from app.services.refund import RefundService
from app.services.review import ReviewError, ReviewService

SESSION = cast(AsyncSession, object())


def _sku(**overrides: object) -> SimpleNamespace:
    """构造商品目录测试所需的 SKU。"""
    values: dict[str, object] = {
        "id": 11,
        "code": "SKU-11",
        "name": "红色 M",
        "status": "ACTIVE",
        "price_cents": 12900,
        "available_stock": 8,
        "physical_stock": 10,
        "locked_stock": 2,
        "weight_grams": 500,
        "spec_values": {"颜色": "红色"},
        "image": "",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _product(**overrides: object) -> SimpleNamespace:
    """构造带规格和 SKU 的商品测试替身。"""
    now = datetime.now(UTC)
    values: dict[str, object] = {
        "id": 1,
        "name": "基础商品",
        "subtitle": "日常款",
        "brand": "LiteShop",
        "description": "商品描述",
        "detail_html": "",
        "detail_images": ["detail.jpg"],
        "main_images": [{"url": "cover.jpg"}],
        "seo_title": None,
        "seo_description": None,
        "seo_keywords": None,
        "tags": ["新品"],
        "recommended_product_ids": [2],
        "sales_count": 3,
        "status": "ON_SHELF",
        "specs": [
            SimpleNamespace(
                id=2,
                name="颜色",
                sort_order=1,
                values=[SimpleNamespace(id=3, value="红色", sort_order=1)],
            )
        ],
        "skus": [_sku()],
        "created_at": now,
        "updated_at": now,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_product_catalog_service_maps_and_writes() -> None:
    """商品目录覆盖摘要、分类、SPU 和 SKU 组装分支。"""
    repository = AsyncMock()
    product = _product()
    category = SimpleNamespace(id=4, parent_id=None, name="服装", icon="", sort_order=1, is_active=True)
    repository.list_spus.return_value = ([product], 3)
    repository.get_spu.return_value = product
    repository.list_categories.return_value = [category]
    repository.add_category.side_effect = lambda _session, value: value
    repository.get_category.return_value = category
    repository.add_product.side_effect = lambda _session, value: value
    service = ProductCatalogService(products=repository)

    async def run() -> None:
        listed = await service.list_products(SESSION, 2, 1, keyword="基础")
        assert listed["meta"] == {"page": 2, "pageSize": 1, "total": 3, "hasNext": True}
        detail = await service.get(SESSION, 1)
        detail_skus = cast(list[dict[str, object]], detail["skus"])
        detail_specs = cast(list[dict[str, object]], detail["specDefinitions"])
        detail_values = cast(list[dict[str, object]], detail_specs[0]["values"])
        assert detail_skus[0]["quantity"] == 8
        assert detail_values[0]["value"] == "红色"
        assert await service.categories(SESSION) == [
            {"id": 4, "parentId": None, "name": "服装", "icon": "", "sortOrder": 1}
        ]
        created_category = await service.create_category(SESSION, CategoryCreate(name="鞋包"))
        assert created_category.name == "鞋包"
        updated_category = await service.update_category(SESSION, 4, CategoryUpdate(name="服饰", sortOrder=2))
        assert updated_category.name == "服饰"
        deleted_category = await service.delete_category(SESSION, 4)
        assert deleted_category.is_active is False

        payload = ProductCreate(
            name="新商品",
            status="DRAFT",
            skus=[
                SkuCreate.model_validate(
                    {"code": "NEW-1", "name": "默认", "priceCents": 1000, "specs": {"颜色": "黑色"}}
                )
            ],
        )
        created_product = await service.create_product(SESSION, payload)
        assert isinstance(created_product, Spu)
        assert created_product.skus[0].spec_hash
        changed = await service.update_product(SESSION, 1, ProductUpdate(name="更新商品", status="ON_SHELF"))
        assert changed.name == "更新商品"
        removed = await service.soft_delete_product(SESSION, 1)
        assert removed.status == "OFF_SHELF"

    asyncio.run(run())
    repository.list_spus.assert_awaited_once_with(SESSION, 1, 1, keyword="基础", include_off_shelf=False)


def _freight_item(**overrides: object) -> SimpleNamespace:
    """构造运费计费项。"""
    values: dict[str, object] = {
        "id": 5,
        "region_codes": [],
        "first_unit": 1,
        "first_fee": 100,
        "additional_unit": 1,
        "additional_fee": 50,
        "free_condition": {},
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _freight_template(**overrides: object) -> SimpleNamespace:
    """构造运费模板。"""
    values: dict[str, object] = {
        "id": 7,
        "name": "全国模板",
        "type": "PIECE",
        "is_default": True,
        "enabled": True,
        "items": [_freight_item()],
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_freight_service_calculation_and_template_lifecycle() -> None:
    """运费覆盖实时 SKU 校验、模板计算及计费项生命周期。"""
    repository = AsyncMock()
    products = AsyncMock()
    template = _freight_template()
    repository.get_default_template.return_value = template
    repository.get_template.return_value = template
    repository.list_templates.return_value = [template]
    repository.add_template.side_effect = lambda _session, value: value
    repository.get_item.return_value = template.items[0]
    repository.get_item.side_effect = [template.items[0], None, template.items[0]]
    service = FreightService(repository=repository, products=products)
    sku = _sku(spu=SimpleNamespace(status="ON_SHELF"))
    products.get_sku.return_value = sku

    async def run() -> None:
        payload = FreightCalculateRequest.model_validate(
            {"provinceCode": "110000", "productAmount": 25800, "items": [{"skuId": 11, "quantity": 2}]}
        )
        assert await service.calculate(SESSION, payload) == 150
        with pytest.raises(FreightError, match="不能重复"):
            await service.calculate(
                SESSION,
                payload.model_copy(
                    update={"items": [FreightLineInput.model_validate({"skuId": 11, "quantity": 1})] * 2}
                ),
            )
        with pytest.raises(FreightError, match="金额已变更"):
            await service.calculate(SESSION, payload.model_copy(update={"product_amount": 1}))
        products.get_sku.return_value = None
        with pytest.raises(FreightError, match="已下架"):
            await service.calculate(SESSION, payload)
        products.get_sku.return_value = sku
        assert await service.calculate_lines(SESSION, [], "110000", 0) == 100
        repository.get_template.return_value = None
        with pytest.raises(FreightError, match="不存在"):
            await service.calculate_lines(SESSION, [], "110000", 0, template_id=99)

        assert (await service.list_templates(SESSION))[0]["id"] == 7
        created = await service.create_template(
            SESSION,
            FreightTemplateCreate.model_validate(
                {
                    "name": "新模板",
                    "type": "REGION",
                    "isDefault": True,
                    "items": [{"firstUnit": 1, "firstFee": 80, "additionalUnit": 1, "additionalFee": 20}],
                }
            ),
        )
        assert created["name"] == "新模板"
        repository.get_template.return_value = template
        updated = await service.update_template(
            SESSION,
            7,
            FreightTemplateUpdate.model_validate(
                {
                    "name": "更新模板",
                    "isDefault": False,
                    "items": [{"firstUnit": 1, "firstFee": 1, "additionalUnit": 1, "additionalFee": 1}],
                }
            ),
        )
        assert updated["name"] == "更新模板"
        assert await service.delete_template(SESSION, 7) == {"deleted": True, "templateId": 7}
        orm_template = FreightTemplate(
            id=7,
            name="更新模板",
            type="PIECE",
            is_default=False,
            enabled=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        orm_template.items = []
        repository.get_template.return_value = orm_template
        added = await service.add_item(
            SESSION,
            7,
            FreightTemplateItemCreate.model_validate(
                {"firstUnit": 1, "firstFee": 60, "additionalUnit": 1, "additionalFee": 10}
            ),
        )
        assert added["id"] == 7
        repository.get_item.side_effect = [orm_template.items[0], None]
        changed = await service.update_item(SESSION, 7, 5, FreightTemplateItemUpdate(firstFee=120))
        assert changed["id"] == 7
        with pytest.raises(FreightError, match="计费项不存在"):
            await service.update_item(SESSION, 7, 404, FreightTemplateItemUpdate(firstFee=1))
        repository.get_item.side_effect = [orm_template.items[0]]
        assert await service.delete_item(SESSION, 7, 5) == {"deleted": True, "templateId": 7, "itemId": 5}

    asyncio.run(run())


def test_review_and_after_sale_services_cover_state_machines() -> None:
    """评价和售后覆盖重复提交、状态流转、退款和换货路径。"""
    review_repository = AsyncMock()
    review = SimpleNamespace(
        id=1,
        user_id=3,
        status="PENDING",
        rating=5,
        content="很好",
        images=[],
        merchant_reply=None,
        merchant_replied_at=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    review_repository.get_by_order_item.return_value = review
    review_repository.list_approved.return_value = ([review], 4.5)
    review_repository.get_for_update.return_value = review
    review_service = ReviewService(review_repository)

    after_repository = AsyncMock()
    order_item = SimpleNamespace(
        id=9,
        order_id=8,
        sku_id=11,
        quantity=1,
        total_amount=1000,
        order=SimpleNamespace(status="COMPLETED"),
    )
    sale = SimpleNamespace(
        id=10,
        after_sale_no="AS-10",
        order_id=8,
        order_item_id=9,
        user_id=3,
        type=AfterSaleType.RETURN_REFUND.value,
        status=AfterSaleStatus.PENDING_REVIEW.value,
        amount_cents=900,
        reason="不需要",
        evidence_urls=[],
        return_tracking_no=None,
        audit_reason=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        active_key="ACTIVE",
    )
    after_repository.get_by_request.return_value = None
    after_repository.get_order_item_for_user.return_value = order_item
    after_repository.has_active_for_order_item.return_value = False
    after_repository.create.return_value = sale
    after_repository.get_for_update.return_value = sale
    refunds = SimpleNamespace(
        payments=SimpleNamespace(get_for_order=AsyncMock(return_value=SimpleNamespace(id=20))),
        create=AsyncMock(return_value=SimpleNamespace(id=30)),
        process=AsyncMock(),
        inventory=SimpleNamespace(purchase_in=AsyncMock()),
    )
    after_service = AfterSaleService(after_repository, refunds=cast(RefundService, refunds))

    async def run() -> None:
        assert cast(object, await review_service.create(SESSION, 3, 9, 5, "很好", [])) is review
        review_repository.get_by_order_item.return_value = None
        review_repository.get_order_item_for_user.return_value = None
        with pytest.raises(ReviewError, match="购买者"):
            await review_service.create(SESSION, 4, 9, 5, "很好", [])
        review_repository.get_by_order_item.return_value = review
        assert (await review_service.list_product(SESSION, 1))["averageRating"] == 4.5
        review.status = "APPROVED"
        assert (await review_service.reply(SESSION, 1, "感谢反馈"))["merchantReply"] == "感谢反馈"
        review.status = "PENDING"
        assert (await review_service.audit(SESSION, 1, "APPROVED", "通过"))["status"] == "APPROVED"

        from app.schemas.after_sale import AfterSaleCreate

        payload = AfterSaleCreate.model_validate(
            {"orderItemId": 9, "type": "RETURN_REFUND", "amountCents": 900, "reason": "不需要"}
        )
        assert cast(object, await after_service.create(SESSION, 3, "request-1", payload)) is sale
        sale.status = AfterSaleStatus.PENDING_REVIEW.value
        assert (await after_service.audit(SESSION, 10, True, "通过")).status == AfterSaleStatus.WAITING_RETURN.value
        assert (await after_service.submit_return(SESSION, 10, 3, "YT123")).status == AfterSaleStatus.RETURNED.value
        completed = await after_service.complete_refund(SESSION, 10)
        assert completed.status == AfterSaleStatus.COMPLETED.value
        after_repository.get_by_request.return_value = sale
        assert cast(object, await after_service.create(SESSION, 3, "request-1", payload)) is sale

    asyncio.run(run())


def test_admin_access_service_rbac_invariants(monkeypatch: pytest.MonkeyPatch) -> None:
    """RBAC 服务覆盖角色、权限和自我锁死保护。"""
    repository = AsyncMock()
    repository.get_role_by_name.return_value = None
    permission = Permission(id=1, code="rbac.write")
    repository.get_permissions_by_codes.return_value = [permission]
    role = Role(id=5, name="运营", permissions=[permission])
    repository.add_role.side_effect = lambda _session, value: value
    repository.get_role.return_value = role
    repository.get_user_with_roles.return_value = SimpleNamespace(
        id=7, nickname="管理员", phone="13800000000", roles=[role]
    )
    repository.list_roles_by_ids.return_value = [role]
    repository.count_role_users.return_value = 0
    service = AdminAccessService()
    service.repository = repository
    monkeypatch.setattr(AdminAccessService, "audit", AsyncMock())

    async def run() -> None:
        created = await service.create_role(SESSION, RoleCreate(name="运营", permissionCodes=["rbac.write"]), "7", "r1")
        assert created["permissions"] == ["rbac.write"]
        updated = await service.update_role(SESSION, 5, RoleUpdate(name="运营主管"), "7", "r2")
        assert updated["name"] == "运营主管"
        assert await service.update_user_roles(SESSION, 7, UserRolesUpdate(roleIds=[5]), "7", "r3")
        assert await service.delete_role(SESSION, 5, "7", "r4") == {"deleted": True, "roleId": 5}
        repository.get_role_by_name.return_value = role
        with pytest.raises(ValueError, match="已存在"):
            await service.create_role(SESSION, RoleCreate(name="运营", permissionCodes=[]), "7", "r5")
        repository.get_role_by_name.return_value = None
        repository.get_permissions_by_codes.return_value = []
        with pytest.raises(ValueError, match="不存在"):
            await service.create_role(SESSION, RoleCreate(name="空权限", permissionCodes=["missing"]), "7", "r6")

    asyncio.run(run())
