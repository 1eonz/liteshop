"""API、基础设施后备存储和仓储边界测试。"""

import asyncio
import time
from collections.abc import Mapping
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock, Mock

import pytest
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import after_sales, logistics, marketing, navigation, pages
from app.core import idempotency as idempotency_module
from app.core import token_store as token_store_module
from app.core.config import settings
from app.enums.after_sale import AfterSaleType
from app.enums.order import OrderStatus
from app.errors import ApiError
from app.models.order import Order, Payment
from app.models.page import PageVariant, StorePage
from app.models.product import Category, Sku, Spu
from app.repositories.inventory import InsufficientStock, InventoryNotFound, InventoryRepository
from app.repositories.order import OrderNotFound, OrderRepository, OrderStatusConflict
from app.repositories.page import PageRepository
from app.repositories.payment import PaymentRepository
from app.repositories.product import ProductRepository
from app.schemas.after_sale import AfterSaleAudit, AfterSaleCreate, AfterSaleReturn
from app.schemas.logistics import TrackingEventCreate
from app.schemas.marketing import CouponClaimRequest, CouponCreate
from app.schemas.page import PageConversionEventInput, PageCopyInput, PageCreateInput, PageSchemaInput, PageVariantInput

SESSION = cast(AsyncSession, object())


class _ExecuteResult:
    """模拟 SQLAlchemy execute 返回值。"""

    def __init__(self, values: list[object], *, first_value: object | None = None) -> None:
        self.values = values
        self.first_value = first_value if first_value is not None else (values[0] if values else None)

    def first(self) -> object | None:
        """返回条件更新是否命中。"""
        return self.first_value

    def all(self) -> list[object]:
        """返回查询列表。"""
        return self.values

    def unique(self) -> "_ExecuteResult":
        """兼容带关系预加载的查询结果。"""
        return self


def _db_flag(monkeypatch: pytest.MonkeyPatch, value: bool) -> None:
    """切换开发内存模式或数据库模式。"""
    configured = replace(settings, use_database=value)
    for module in (
        pages,
        navigation,
        marketing,
        logistics,
        after_sales,
        token_store_module,
        idempotency_module,
    ):
        monkeypatch.setattr(module, "settings", configured)


def _response_data(response: Mapping[str, object]) -> Mapping[str, object]:
    """读取统一成功响应内的业务数据。"""
    data = response["data"]
    assert isinstance(data, Mapping)
    return data


def _response_items(response: Mapping[str, object]) -> list[object]:
    """读取统一成功响应内的列表字段。"""
    items = _response_data(response)["items"]
    assert isinstance(items, list)
    return items


def test_memory_api_boundaries(monkeypatch: pytest.MonkeyPatch) -> None:
    """页面、导航、优惠券、物流和售后在无数据库时返回明确状态。"""
    _db_flag(monkeypatch, False)

    async def run() -> None:
        assert len(_response_items(await pages.list_public_pages())) == 1
        assert len(_response_items(await pages.list_pages("memory-admin", SESSION))) == 1
        assert _response_data(await pages.get_page_schema(8))["components"] == []
        assert (
            _response_data(await pages.record_page_event(1, PageConversionEventInput(eventName="view"), "event-1"))[
                "accepted"
            ]
            is True
        )
        with pytest.raises(ApiError) as unsafe:
            await pages.get_public_page("../unsafe", SESSION)
        assert unsafe.value.status_code == 404

        assert len(_response_items(await navigation.list_site_navigation("header", SESSION))) == 3
        assert _response_items(await navigation.list_site_navigation("footer", SESSION)) == []
        assert len(_response_items(await navigation.list_admin_navigation("admin", SESSION))) == 3

        assert _response_items(await marketing.list_coupons(SESSION)) == []
        with pytest.raises(ApiError) as coupon_claim:
            await marketing.claim_coupon(CouponClaimRequest(couponCode="WELCOME"), "7", "coupon-1")
        assert coupon_claim.value.status_code == 503
        with pytest.raises(ApiError) as coupon_create:
            await marketing.create_coupon(
                CouponCreate(
                    code="WELCOME",
                    name="新人券",
                    couponType="FULL_REDUCTION",
                    thresholdCents=100,
                    discountCents=10,
                    startsAt=datetime.now(UTC),
                    endsAt=datetime.now(UTC) + timedelta(days=1),
                ),
                "7",
                "coupon-2",
                SESSION,
            )
        assert coupon_create.value.status_code == 503

        assert _response_items(await logistics.list_tracking(1, "7", SESSION)) == []
        with pytest.raises(ApiError) as tracking:
            await logistics.add_tracking(
                1,
                TrackingEventCreate(status="IN_TRANSIT", description="已揽收", occurredAt=datetime.now(UTC)),
                "7",
                "tracking-1",
            )
        assert tracking.value.status_code == 503

        with pytest.raises(ApiError) as invalid_subject:
            after_sales._user_id("not-a-number")
        assert invalid_subject.value.status_code == 401
        payload = AfterSaleCreate(
            order_item_id=1,
            type=AfterSaleType.REFUND_ONLY,
            amount_cents=100,
            reason="不需要",
        )
        with pytest.raises(ApiError) as create_sale:
            await after_sales.create_after_sale(payload, "7", "sale-1")
        assert create_sale.value.status_code == 503
        with pytest.raises(ApiError) as list_sale:
            await after_sales.list_after_sales("7", SESSION)
        assert list_sale.value.status_code == 503
        with pytest.raises(ApiError) as detail_sale:
            await after_sales.get_after_sale(1, "7", SESSION)
        assert detail_sale.value.status_code == 503
        with pytest.raises(ApiError) as return_sale:
            await after_sales.submit_after_sale_return(1, AfterSaleReturn(trackingNo="YT1"), "7", "sale-2")
        assert return_sale.value.status_code == 503
        with pytest.raises(ApiError) as audit_sale:
            await after_sales.audit_after_sale(1, AfterSaleAudit(approved=True), "7", "sale-3")
        assert audit_sale.value.status_code == 503
        with pytest.raises(ApiError) as complete_sale:
            await after_sales.complete_after_sale(1, "7", "sale-4")
        assert complete_sale.value.status_code == 503

        with pytest.raises(ApiError) as create_page:
            await pages.create_page(
                PageCreateInput.model_validate({"slug": "new", "channel": "site", "version": 1, "components": []}),
                "7",
                "page-1",
            )
        assert create_page.value.status_code == 503
        with pytest.raises(ApiError) as save_page:
            await pages.save_page_schema(
                1, PageSchemaInput.model_validate({"slug": "home", "version": 1, "components": []}), "7", "page-2"
            )
        assert save_page.value.status_code == 503
        with pytest.raises(ApiError) as home_page:
            await pages.set_home_page(1, "7", "page-3")
        assert home_page.value.status_code == 503
        with pytest.raises(ApiError) as publish:
            await pages.publish_page(1, "7", "page-4")
        assert publish.value.status_code == 503
        with pytest.raises(ApiError) as copy:
            await pages.copy_page(1, PageCopyInput(slug="copy"), "7", "page-5")
        assert copy.value.status_code == 503
        with pytest.raises(ApiError) as remove:
            await pages.delete_page(1, "7", "page-6")
        assert remove.value.status_code == 503
        assert (await pages.list_page_variants(1, "7", SESSION))["data"] == []
        with pytest.raises(ApiError) as variant:
            await pages.save_page_variant(
                1,
                "a",
                PageVariantInput.model_validate(
                    {"key": "b", "name": "B", "schema": {"slug": "variant", "version": 1, "components": []}}
                ),
                "7",
                "page-7",
            )
        assert variant.value.status_code == 422

    asyncio.run(run())


def test_token_store_fallback_and_expiration(monkeypatch: pytest.MonkeyPatch) -> None:
    """刷新令牌后备存储覆盖注册、消费、轮换、撤销和过期。"""
    _db_flag(monkeypatch, False)
    store = token_store_module.RefreshTokenStore()

    async def run() -> None:
        await store.register("old", "user", 30)
        assert await store.consume("old", "other") is False
        await store.register("old", "user", 30)
        assert await store.rotate("old", "new", "user", 30) is True
        assert await store.rotate("old", "next", "user", 30) is False
        assert await store.consume("new", "user") is True
        await store.register("revoke", "user", 30)
        await store.revoke("revoke")
        assert await store.consume("revoke", "user") is False
        await store.register("expired", "user", 1)
        store._fallback["expired"] = token_store_module.RefreshSession("user", time.monotonic() - 1)
        assert await store.consume("expired", "user") is False

    asyncio.run(run())


def test_redis_stores_fallback_and_error_mapping(monkeypatch: pytest.MonkeyPatch) -> None:
    """幂等存储和令牌存储在 Redis 故障时保持后备语义。"""
    _db_flag(monkeypatch, True)
    redis = AsyncMock()
    monkeypatch.setattr(idempotency_module, "redis_client", redis)
    store = idempotency_module.RedisIdempotencyStore()

    async def run() -> None:
        redis.get.side_effect = RedisError("down")
        first = await store.probe("k")
        second = await store.probe("k")
        assert first.acquired is True
        assert second.acquired is False
        redis.get.side_effect = None
        redis.get.return_value = None
        redis.set.side_effect = RedisError("down")
        await store.complete("k", '{"ok":true}')
        redis.set.side_effect = None
        redis.get.return_value = '{"ok":true}'
        assert (await store.probe("k")).cached_response == '{"ok":true}'
        await store.release("k")

        redis.get.return_value = b"subject"
        redis.set.side_effect = RedisError("down")
        redis.eval.side_effect = RedisError("down")
        token_store = token_store_module.RefreshTokenStore()
        monkeypatch.setattr(token_store_module, "redis_client", redis)
        with pytest.raises(token_store_module.TokenStoreUnavailable):
            await token_store.register("jti", "subject", 30)

    asyncio.run(run())


def test_inventory_repository_success_and_failure_boundaries() -> None:
    """库存仓储覆盖五类原子写入、流水映射和失败分类。"""
    repository = InventoryRepository()
    sku = cast(Sku, SimpleNamespace(id=1, physical_stock=10, locked_stock=2, spu=SimpleNamespace(status="ON_SHELF")))
    session = AsyncMock()
    session.add = Mock()
    session.execute.return_value = _ExecuteResult([1])
    session.scalar.side_effect = [sku, sku, sku, sku, sku]
    session.flush = AsyncMock()

    async def run() -> None:
        for method, quantity, reference in [
            (repository.lock, 2, "1"),
            (repository.release, 1, "order"),
            (repository.deduct, 1, "2"),
            (repository.purchase_in, 3, "3"),
            (repository.adjust, -1, "manual"),
        ]:
            result = await method(session, 1, quantity, reference, "req")
            assert result is sku
        with pytest.raises(ValueError):
            await repository.lock(session, 1, 0, "1", "bad")
        session.execute.return_value = _ExecuteResult([], first_value=None)
        session.scalar.side_effect = [1]
        with pytest.raises(InsufficientStock):
            await repository.lock(session, 1, 1, "1", "short")
        session.scalar.side_effect = [None]
        with pytest.raises(InventoryNotFound):
            await repository.purchase_in(session, 1, 1, "1", "missing")
        with pytest.raises(ValueError):
            await repository.adjust(session, 1, 0, "1", "bad")

        session.scalars.side_effect = [_ExecuteResult([sku]), _ExecuteResult([])]
        session.scalar.side_effect = [1]
        stock, total = await repository.list_stock(session, 0, 10)
        assert stock == [sku] and total == 1
        assert await repository.list_ledgers(session, 1, 5) == []

    asyncio.run(run())


def test_order_payment_product_and_page_repositories() -> None:
    """订单、支付、商品和页面仓储覆盖查询、写入、锁和异常分支。"""
    session = AsyncMock()
    session.add = Mock()
    order = cast(Order, SimpleNamespace(id=1, user_id=7, status=OrderStatus.PENDING_PAYMENT.value, items=[]))
    session.scalar.side_effect = [order, order, order]
    session.scalars.side_effect = [_ExecuteResult([order]), _ExecuteResult([order]), _ExecuteResult([order])]
    session.execute.return_value = _ExecuteResult([1])
    session.refresh = AsyncMock()
    orders = OrderRepository()

    async def run() -> None:
        assert await orders.get_by_request(session, 7, "r") is order
        assert await orders.get(session, 1) is order
        assert await orders.get_for_update(session, 1) is order
        created = await orders.create(
            session,
            user_id=7,
            order_no="O-1",
            client_request_id="r",
            total_amount=100,
            product_amount=100,
            freight_amount=0,
            discount_amount=0,
            address_snapshot={"receiverName": "甲"},
            items=[
                {
                    "sku_id": 1,
                    "product_id": 1,
                    "product_name": "商品",
                    "sku_code": "S",
                    "sku_name": "默认",
                    "spec_values": {},
                    "product_image": "",
                    "quantity": 1,
                    "price_cents": 100,
                    "weight_grams": 1,
                    "total_amount": 100,
                }
            ],
        )
        assert created.status == OrderStatus.PENDING_PAYMENT.value
        session.scalar.side_effect = [order, 1]
        order.status = OrderStatus.PENDING_PAYMENT.value
        transitioned = await orders.transition(session, 1, OrderStatus.CANCELLED)
        assert transitioned is order
        session.scalar.side_effect = [1]
        assert await orders.list_for_user(session, 7, 0, 10) == ([order], 1)
        session.scalar.side_effect = [1]
        assert await orders.list_all(session, 0, 10, OrderStatus.CANCELLED) == ([order], 1)
        assert await orders.list_expired_for_update(session, datetime.now(UTC), 10) == [order]
        await orders.flush(session)

        session.scalar.side_effect = [None]
        with pytest.raises(OrderNotFound):
            await orders.get(session, 404)
        order.status = OrderStatus.COMPLETED.value
        session.scalar.side_effect = [order]
        with pytest.raises(ValueError):
            await orders.transition(session, 1, OrderStatus.CANCELLED)
        order.status = OrderStatus.PENDING_PAYMENT.value
        session.scalar.side_effect = [order, None]
        with pytest.raises(OrderStatusConflict):
            await orders.transition(session, 1, OrderStatus.CANCELLED)

        payment_repo = PaymentRepository()
        payment = cast(Payment, SimpleNamespace(id=2, order_id=1))
        session.scalar.side_effect = [payment, payment, payment, payment]
        assert await payment_repo.get_by_request(session, 1, "r") is payment
        assert await payment_repo.get_by_callback(session, "c") is payment
        assert await payment_repo.get_by_id(session, 2, for_update=True) is payment
        assert await payment_repo.get_for_order(session, 1, for_update=True) is payment
        created_payment = await payment_repo.create(
            session, order_id=1, user_id=7, provider="WECHAT", amount_cents=100, client_request_id="p"
        )
        assert created_payment.amount_cents == 100
        await payment_repo.mark_paid(session, created_payment, "c", "trade", "raw")
        assert created_payment.status == "SUCCESS"

        product_repo = ProductRepository()
        product = cast(Spu, SimpleNamespace(id=1, status="ON_SHELF", deleted_at=None, skus=[], specs=[]))
        sku = cast(Sku, SimpleNamespace(id=1, spu=product))
        session.scalar.side_effect = [sku, sku, product, 1]
        session.scalars.side_effect = [_ExecuteResult([product]), _ExecuteResult([])]
        assert await product_repo.get_sku_for_update(session, 1) is sku
        assert await product_repo.get_sku(session, 1) is sku
        assert await product_repo.get_spu(session, 1, for_update=True) is product
        assert await product_repo.list_spus(session, 0, 10) == ([product], 1)
        assert await product_repo.list_categories(session) == []
        category = cast(Category, SimpleNamespace(id=3))
        assert await product_repo.add_category(session, category) is category
        session.scalar.side_effect = [SimpleNamespace(id=3)]
        assert (await product_repo.get_category(session, 3)).id == 3

        page_repo = PageRepository()
        page = cast(StorePage, SimpleNamespace(id=1))
        variant = cast(PageVariant, SimpleNamespace(id=1))
        session.scalar.side_effect = [page, page, variant, page]
        session.scalars.side_effect = [_ExecuteResult([page]), _ExecuteResult([page]), _ExecuteResult([])]
        assert await page_repo.get(session, 1, for_update=True) is page
        assert await page_repo.get_by_slug(session, "home", channel="site") is page
        assert await page_repo.list_pages(session) == [page]
        assert await page_repo.list_published_pages(session) == [page]
        assert await page_repo.list_variants(session, 1) == []
        assert await page_repo.get_variant(session, 1, "a", for_update=True) is variant
        assert await page_repo.add(session, page) is page
        assert await page_repo.delete(session, 1) is True
        await page_repo.clear_home(session, channel="site")
        await page_repo.flush(session)

    asyncio.run(run())
