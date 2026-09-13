"""后台领域编排和页面 Schema 服务测试。"""

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums.order import OrderStatus
from app.repositories.inventory import InventoryRepository
from app.schemas.admin import OrderManagementUpdate, OrderPriceUpdate, ShipOrderRequest
from app.schemas.freight import (
    FreightTemplateCreate,
    FreightTemplateItemCreate,
    FreightTemplateItemUpdate,
    FreightTemplateUpdate,
)
from app.schemas.page import PageConversionEventInput, PageCreateInput, PageSchemaInput, PageVariantInput
from app.schemas.products import CategoryCreate, CategoryUpdate, InventoryAdjust, ProductCreate, ProductUpdate
from app.services.admin_catalog import AdminCatalogService
from app.services.admin_freight import AdminFreightService
from app.services.admin_trade import AdminTradeService
from app.services.freight import FreightService
from app.services.order_workflow import OrderWorkflow, OrderWorkflowError
from app.services.page import PageSchemaError, PageService
from app.services.product_catalog import ProductCatalogService

SESSION = cast(AsyncSession, object())


def _product() -> SimpleNamespace:
    """构造后台商品响应所需的最小实体。"""
    now = datetime.now(UTC)
    sku = SimpleNamespace(
        id=11,
        code="SKU-11",
        name="默认规格",
        status="ACTIVE",
        price_cents=1000,
        available_stock=4,
        physical_stock=5,
        locked_stock=1,
        weight_grams=100,
        spec_values={},
        image="",
    )
    return SimpleNamespace(
        id=1,
        name="商品",
        subtitle="",
        brand="",
        description="",
        detail_html="",
        detail_images=[],
        main_images=[],
        seo_title=None,
        seo_description=None,
        seo_keywords=None,
        tags=[],
        recommended_product_ids=[],
        sales_count=0,
        status="ON_SHELF",
        specs=[],
        skus=[sku],
        created_at=now,
        updated_at=now,
    )


def _order(status: str = OrderStatus.PENDING_PAYMENT.value) -> SimpleNamespace:
    """构造后台订单响应实体。"""
    now = datetime.now(UTC)
    return SimpleNamespace(
        id=7,
        order_no="LS-7",
        user_id=3,
        status=status,
        refund_status="NONE",
        total_amount=1100,
        product_amount=1000,
        freight_amount=100,
        discount_amount=0,
        paid_amount=None,
        address_snapshot={"receiverName": "用户", "phone": "13800000000", "detail": "地址"},
        remark=None,
        paid_at=None,
        shipped_at=None,
        completed_at=None,
        cancelled_at=None,
        cancel_reason=None,
        created_at=now,
        updated_at=now,
        expired_at=None,
        shipping_company_code="",
        tracking_no="",
        items=[],
    )


def test_admin_catalog_and_freight_orchestration(monkeypatch: pytest.MonkeyPatch) -> None:
    """后台商品、分类和运费模板操作都应委托领域服务并记录审计。"""
    product = _product()
    catalog = AsyncMock(spec=ProductCatalogService)
    catalog.list_products.return_value = {"items": [], "meta": {"total": 0}}
    category = SimpleNamespace(id=4, parent_id=None, name="服装", icon="", sort_order=1, is_active=True)
    catalog.create_category.return_value = category
    catalog.categories.return_value = []
    catalog.update_category.return_value = category
    catalog.delete_category.return_value = category
    catalog.create_product.return_value = product
    catalog.products = AsyncMock()
    catalog.products.get_spu.return_value = product
    catalog.update_product.return_value = product
    catalog.soft_delete_product.return_value = product
    catalog.detail.return_value = {"id": 1, "name": "商品"}
    catalog_service = AdminCatalogService()
    catalog_service.catalog = cast(ProductCatalogService, catalog)
    monkeypatch.setattr(AdminCatalogService, "audit", AsyncMock())

    freight = AsyncMock(spec=FreightService)
    freight.list_templates.return_value = []
    freight.create_template.return_value = {"id": 7, "name": "全国"}
    freight.update_template.return_value = {"id": 7, "name": "更新"}
    freight.delete_template.return_value = {"deleted": True, "templateId": 7}
    freight.add_item.return_value = {"id": 7}
    freight.update_item.return_value = {"id": 7}
    freight.delete_item.return_value = {"deleted": True, "itemId": 8}
    freight_service = AdminFreightService()
    freight_service.freight = cast(FreightService, freight)
    monkeypatch.setattr(AdminFreightService, "audit", AsyncMock())

    async def run() -> None:
        products_result = await catalog_service.list_products(SESSION, 1, 20)
        products_meta = cast(dict[str, object], products_result["meta"])
        assert products_meta["total"] == 0
        assert (await catalog_service.create_category(SESSION, CategoryCreate(name="服装"), "3", "c1"))["id"] == 4
        assert await catalog_service.list_categories(SESSION) == []
        assert (await catalog_service.update_category(SESSION, 4, CategoryUpdate(name="服饰"), "3", "c2"))[
            "name"
        ] == "服装"
        assert await catalog_service.delete_category(SESSION, 4, "3", "c3") == {"deleted": True, "categoryId": 4}
        product_payload = ProductCreate.model_validate(
            {"name": "商品", "skus": [{"code": "SKU-1", "name": "默认规格", "priceCents": 1000}]}
        )
        assert (await catalog_service.create_product(SESSION, product_payload, "3", "p1"))["id"] == 1
        assert (await catalog_service.update_product(SESSION, 1, ProductUpdate(name="更新"), "3", "p2"))["id"] == 1
        assert await catalog_service.delete_product(SESSION, 1, "3", "p3") == {"deleted": True, "productId": 1}

        assert await freight_service.list_freight_templates(SESSION) == []
        item_create = FreightTemplateItemCreate.model_validate(
            {"firstUnit": 1, "firstFee": 10, "additionalUnit": 1, "additionalFee": 1}
        )
        template_create = FreightTemplateCreate(name="全国", type="PIECE", items=[item_create])
        template_update = FreightTemplateUpdate(name="更新", type="PIECE")
        item_update = FreightTemplateItemUpdate.model_validate(
            {"firstUnit": 2, "firstFee": 20, "additionalUnit": 1, "additionalFee": 2}
        )
        assert (await freight_service.create_freight_template(SESSION, template_create, "3", "f1"))["id"] == 7
        assert (await freight_service.update_freight_template(SESSION, 7, template_update, "3", "f2"))["id"] == 7
        assert await freight_service.delete_freight_template(SESSION, 7, "3", "f3") == {
            "deleted": True,
            "templateId": 7,
        }
        assert (await freight_service.add_freight_item(SESSION, 7, item_create, "3", "f4"))["id"] == 7
        assert (await freight_service.update_freight_item(SESSION, 7, 8, item_update, "3", "f5"))["id"] == 7
        assert await freight_service.delete_freight_item(SESSION, 7, 8, "3", "f6") == {"deleted": True, "itemId": 8}

    asyncio.run(run())


def test_admin_trade_orchestration_and_inventory_warning(monkeypatch: pytest.MonkeyPatch) -> None:
    """后台订单、库存和地址更新分支应保持统一响应。"""
    current = _order()
    orders = SimpleNamespace(
        orders=AsyncMock(),
        ship_order=AsyncMock(return_value=current),
        change_order_price=AsyncMock(return_value=current),
        cancel_order=AsyncMock(return_value=current),
    )
    orders.orders.get_for_update.return_value = current
    orders.orders.list_all.return_value = ([current], 1)
    orders.orders.flush = AsyncMock()
    inventory = AsyncMock()
    inventory.list_stock.return_value = (
        [
            SimpleNamespace(
                id=11, code="SKU", name="库存", physical_stock=5, available_stock=1, locked_stock=4, safety_stock=2
            )
        ],
        1,
    )
    inventory.adjust.return_value = SimpleNamespace(id=11, physical_stock=6, available_stock=2, locked_stock=4)
    inventory.list_ledgers.return_value = [
        SimpleNamespace(
            id=1,
            sku_id=11,
            event_type="MANUAL_ADJUST",
            quantity=1,
            physical_before=5,
            physical_after=6,
            locked_before=4,
            locked_after=4,
            reference_no="r1",
            reason="补货",
            created_at=datetime.now(UTC),
        )
    ]
    service = AdminTradeService()
    service.orders = cast(OrderWorkflow, orders)
    service.inventory = cast(InventoryRepository, inventory)
    monkeypatch.setattr(AdminTradeService, "audit", AsyncMock())

    async def run() -> None:
        orders_result = await service.list_orders(SESSION, 1, 20)
        orders_meta = cast(dict[str, object], orders_result["meta"])
        assert orders_meta["total"] == 1
        ship_payload = ShipOrderRequest.model_validate({"logisticsCompanyCode": "SF", "trackingNo": "SF-1"})
        assert (await service.ship_order(SESSION, 7, ship_payload, "3", "s1"))["id"] == 7
        price_payload = OrderPriceUpdate.model_validate({"totalAmount": 900})
        assert (await service.change_order_price(SESSION, 7, price_payload, "3", "p1"))["id"] == 7
        assert (await service.cancel_order(SESSION, 7, "3", "c1"))["id"] == 7
        updated = await service.update_order(SESSION, 7, OrderManagementUpdate(remark="备注"), "3", "u1")
        assert updated["remark"] == "备注"
        inventory_result = await service.list_inventory(SESSION, 1, 20)
        assert cast(list[dict[str, object]], inventory_result["items"])[0]["warning"] is True
        adjusted = await service.adjust_inventory(SESSION, 11, InventoryAdjust(quantity=1, reason="补货"), "3", "a1")
        assert adjusted["availableStock"] == 2
        assert (await service.inventory_ledgers(SESSION, 11))[0]["eventType"] == "MANUAL_ADJUST"
        current.status = "SHIPPED"
        with pytest.raises(OrderWorkflowError, match="只有待付款"):
            await service.update_order(
                SESSION,
                7,
                OrderManagementUpdate(
                    addressSnapshot={"receiverName": "用户", "phone": "13800000000", "detail": "地址"}
                ),
                "3",
                "u2",
            )

    asyncio.run(run())


def test_page_service_schema_lifecycle_and_validation() -> None:
    """页面服务覆盖创建、复制、删除、变体和发布校验。"""
    repository = AsyncMock()
    repository.get_by_slug.return_value = None
    repository.get.return_value = None
    repository.get_variant.return_value = None
    repository.list_pages.return_value = []
    repository.list_published_pages.return_value = []
    repository.list_variants.return_value = []
    service = PageService(repository)

    async def run() -> None:
        payload = PageCreateInput.model_validate(
            {"slug": "landing", "channel": "site", "title": "落地页", "version": 1, "components": []}
        )
        created = await service.create(SESSION, payload)
        assert created["slug"] == "landing"
        page = SimpleNamespace(
            id=9,
            slug="landing",
            channel="site",
            name="落地页",
            status="DRAFT",
            version=1,
            schema={"title": "落地页", "components": []},
            is_home=False,
            published_at=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        repository.get.return_value = page
        repository.get_by_slug.return_value = page
        saved = await service.save(
            SESSION,
            9,
            PageSchemaInput.model_validate({"slug": "landing", "channel": "site", "version": 1, "components": []}),
        )
        assert saved["version"] == 2
        repository.get_by_slug.return_value = None
        copied = await service.copy(SESSION, 9, "landing-copy")
        assert copied["slug"] == "landing-copy"
        repository.get.return_value = page
        page.is_home = True
        with pytest.raises(PageSchemaError, match="首页不能"):
            await service.remove(SESSION, 9)
        page.is_home = False
        assert await service.remove(SESSION, 9) == {"deleted": True, "id": 9}
        repository.get.return_value = None
        with pytest.raises(PageSchemaError, match="不存在"):
            await service.list_variants(SESSION, 9)
        repository.get.return_value = page
        assert await service.list_variants(SESSION, 9) == []
        repository.get_variant.return_value = None
        variant = await service.save_variant(
            SESSION,
            9,
            PageVariantInput.model_validate(
                {"key": "control", "name": "默认", "schema": {"slug": "x", "version": 1, "components": []}}
            ),
        )
        assert variant["key"] == "control"
        event = await service.record_event(SESSION, 9, PageConversionEventInput.model_validate({"eventName": "view"}))
        assert event["accepted"] is True
        page.channel = "store"
        with pytest.raises(PageSchemaError, match="官网"):
            await service.publish(SESSION, 9)
        page.channel = "site"
        assert (await service.publish(SESSION, 9))["status"] == "PUBLISHED"

        unsafe = PageSchemaInput.model_validate(
            {"slug": "unsafe", "version": 1, "pageStyle": {"padding": "8px"}, "components": []}
        )
        with pytest.raises(PageSchemaError, match="Design Token"):
            PageService.validate(unsafe)

    asyncio.run(run())
