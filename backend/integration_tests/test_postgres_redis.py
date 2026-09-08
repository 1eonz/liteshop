"""可选的 PostgreSQL/Redis 集成验收。

默认不执行，避免单元测试依赖本机服务。设置 ``LITESHOP_RUN_INTEGRATION=1``
并先执行 Alembic 迁移后运行本文件，可验证真实数据库锁和 Redis NX 幂等。
"""

import asyncio
import os
from collections.abc import Generator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from redis.asyncio import Redis
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core import idempotency as idempotency_module
from app.core.config import settings
from app.core.idempotency import idempotency_store, make_idempotency_key
from app.enums.after_sale import AfterSaleType
from app.models.after_sale import AfterSale
from app.models.inventory import InventoryLedger
from app.models.order import Order, OrderItem, Payment
from app.models.product import Sku, Spu
from app.models.user import User
from app.repositories.inventory import InsufficientStock, InventoryRepository
from app.schemas.after_sale import AfterSaleCreate
from app.services.after_sale import AfterSaleService, after_sale_response
from app.services.idempotency import IdempotencyInProgress, IdempotentResult, idempotency_service

pytestmark = pytest.mark.skipif(
    os.getenv("LITESHOP_RUN_INTEGRATION") != "1",
    reason="设置 LITESHOP_RUN_INTEGRATION=1 后才运行真实 PostgreSQL/Redis 验收",
)


@pytest.fixture
def integration_session_factory() -> Generator[async_sessionmaker[AsyncSession], None, None]:
    """为集成测试创建独立连接池，避免污染应用全局连接。"""
    # 每个测试通过 asyncio.run 创建独立事件循环，禁止默认连接池跨循环复用连接。
    engine = create_async_engine(settings.database_url, poolclass=NullPool, pool_pre_ping=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def dispose() -> None:
        await engine.dispose()

    yield factory
    asyncio.run(dispose())


async def _create_fixture(factory: async_sessionmaker[AsyncSession]) -> tuple[int, str]:
    """写入最小商品和 SKU 夹具，返回 SKU 与唯一引用。"""
    reference = f"integration-{uuid4().hex}"
    async with factory.begin() as session:
        product = Spu(
            name=f"集成测试商品-{reference}",
            subtitle="",
            brand="",
            main_images=[],
            detail_images=[],
            description="",
            detail_html="",
            tags=[],
            recommended_product_ids=[],
            status="ON_SHELF",
            sort_order=0,
            sales_count=0,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.add(product)
        await session.flush()
        sku = Sku(
            product_id=product.id,
            code=f"IT-{uuid4().hex[:24]}",
            name="默认规格",
            spec_values={},
            spec_hash=uuid4().hex,
            price_cents=100,
            cost_cents=50,
            physical_stock=1,
            locked_stock=0,
            weight_grams=100,
            image="",
            bar_code="",
            safety_stock=0,
            status="ACTIVE",
            sort_order=0,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.add(sku)
        await session.flush()
        return sku.id, reference


async def _delete_fixture(factory: async_sessionmaker[AsyncSession], reference: str) -> None:
    """按唯一名称删除测试商品，级联清理 SKU。"""
    async with factory.begin() as session:
        product = await session.scalar(select(Spu).where(Spu.name == f"集成测试商品-{reference}"))
        if product is not None:
            sku_ids = select(Sku.id).where(Sku.product_id == product.id)
            await session.execute(delete(InventoryLedger).where(InventoryLedger.sku_id.in_(sku_ids)))
            await session.delete(product)


async def _create_after_sale_fixture(
    factory: async_sessionmaker[AsyncSession], reference: str
) -> tuple[int, int, int, int]:
    """创建已支付订单、SKU 和用户，供真实售后并发测试使用。"""
    now = datetime.now(UTC)
    async with factory.begin() as session:
        user = User(
            phone=f"138{uuid4().int % 10_000_000:07d}",
            nickname="集成售后用户",
            avatar="",
            gender="UNKNOWN",
            status="ACTIVE",
            member_level="NORMAL",
            points=0,
            tags=[],
            created_at=now,
            updated_at=now,
        )
        session.add(user)
        await session.flush()
        product = Spu(
            name=f"集成售后商品-{reference}",
            subtitle="",
            brand="",
            main_images=[],
            detail_images=[],
            description="",
            detail_html="",
            tags=[],
            recommended_product_ids=[],
            status="ON_SHELF",
            sort_order=0,
            sales_count=0,
            created_at=now,
            updated_at=now,
        )
        session.add(product)
        await session.flush()
        sku = Sku(
            product_id=product.id,
            code=f"AS-IT-{uuid4().hex[:20]}",
            name="默认规格",
            spec_values={},
            spec_hash=uuid4().hex,
            price_cents=12900,
            cost_cents=5000,
            physical_stock=1,
            locked_stock=0,
            weight_grams=100,
            image="",
            bar_code="",
            safety_stock=0,
            status="ACTIVE",
            sort_order=0,
            created_at=now,
            updated_at=now,
        )
        session.add(sku)
        await session.flush()
        order = Order(
            order_no=f"AS-ORDER-{uuid4().hex[:20]}",
            user_id=user.id,
            status="PAID",
            refund_status="NONE",
            total_amount=12900,
            product_amount=12900,
            freight_amount=0,
            discount_amount=0,
            paid_amount=12900,
            address_snapshot={
                "receiverName": "集成用户",
                "phone": "13800000000",
                "detail": "集成测试地址",
            },
            client_request_id=f"order-{uuid4().hex}",
            paid_at=now,
            created_at=now,
            updated_at=now,
        )
        session.add(order)
        await session.flush()
        order_item = OrderItem(
            order_id=order.id,
            sku_id=sku.id,
            product_id=product.id,
            product_name=product.name,
            sku_code=sku.code,
            sku_name=sku.name,
            spec_values={},
            product_image="",
            quantity=1,
            price_cents=12900,
            weight_grams=100,
            discount_amount=0,
            total_amount=12900,
            created_at=now,
        )
        payment = Payment(
            payment_no=f"AS-PAY-{uuid4().hex[:20]}",
            order_id=order.id,
            user_id=user.id,
            channel="WECHAT",
            status="SUCCESS",
            amount_cents=12900,
            transaction_id=f"trade-{uuid4().hex}",
            callback_id=f"callback-{uuid4().hex}",
            callback_raw="{}",
            paid_at=now,
            callback_at=now,
            fail_reason="",
            client_request_id=f"payment-{uuid4().hex}",
            created_at=now,
            updated_at=now,
        )
        session.add_all([order_item, payment])
        await session.flush()
        return user.id, order_item.id, product.id, order.id


async def _delete_after_sale_fixture(
    factory: async_sessionmaker[AsyncSession], user_id: int, product_id: int, order_id: int
) -> None:
    """按外键依赖顺序清理售后集成夹具。"""
    async with factory.begin() as session:
        await session.execute(delete(AfterSale).where(AfterSale.user_id == user_id))
        await session.execute(delete(Payment).where(Payment.order_id == order_id))
        await session.execute(delete(Order).where(Order.id == order_id))
        await session.execute(delete(Sku).where(Sku.product_id == product_id))
        await session.execute(delete(Spu).where(Spu.id == product_id))
        await session.execute(delete(User).where(User.id == user_id))


def test_postgres_inventory_update_is_atomic(integration_session_factory: async_sessionmaker[AsyncSession]) -> None:
    """两个真实事务竞争一个库存时只能有一个成功。"""

    async def run() -> None:
        sku_id, reference = await _create_fixture(integration_session_factory)

        async def lock_once() -> str:
            try:
                async with integration_session_factory.begin() as session:
                    await InventoryRepository().lock(session, sku_id, 1, reference, uuid4().hex)
                return "success"
            except InsufficientStock:
                return "insufficient"

        results = await asyncio.gather(lock_once(), lock_once())
        assert sorted(results) == ["insufficient", "success"]

        async with integration_session_factory.begin() as session:
            sku = await session.get(Sku, sku_id)
            assert sku is not None
            assert sku.physical_stock == 1
            assert sku.locked_stock == 1
        await _delete_fixture(integration_session_factory, reference)

    asyncio.run(run())


def test_redis_nx_idempotency_returns_cached_response() -> None:
    """真实 Redis NX 锁完成后，重复请求必须返回原响应。"""

    async def run() -> None:
        redis = Redis.from_url(settings.redis_url, decode_responses=True)
        await redis.ping()
        key = f"integration:idempotency:{uuid4().hex}"
        first = await idempotency_store.probe(key, use_redis=True)
        assert first.acquired is True
        await idempotency_store.complete(key, '{"accepted":true}', use_redis=True)
        second = await idempotency_store.probe(key, use_redis=True)
        assert second.acquired is False
        assert second.cached_response == '{"accepted":true}'
        await idempotency_store.release(key, use_redis=True)
        await redis.aclose()

    asyncio.run(run())


def test_postgres_redis_after_sale_request_is_idempotent(
    integration_session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """售后创建并发请求最多创建一个记录，完成后重复请求读取缓存响应。"""

    async def run() -> None:
        redis = Redis.from_url(settings.redis_url, decode_responses=True)
        await redis.ping()
        monkeypatch.setattr(idempotency_module, "redis_client", redis)
        reference = uuid4().hex
        user_id, order_item_id, product_id, order_id = await _create_after_sale_fixture(
            integration_session_factory, reference
        )
        request_id = f"after-sale-{reference}"
        payload = AfterSaleCreate.model_validate(
            {
                "orderItemId": order_item_id,
                "type": AfterSaleType.REFUND_ONLY.value,
                "amountCents": 12900,
                "reason": "集成测试退款",
                "evidenceUrls": [],
            }
        )

        async def operation(session: AsyncSession | None) -> IdempotentResult:
            assert session is not None
            item = await AfterSaleService().create(session, user_id, request_id, payload)
            response = after_sale_response(item)
            return IdempotentResult(response, "after_sale", str(item.id))

        try:
            results = await asyncio.gather(
                idempotency_service.execute(
                    user_id=str(user_id),
                    request_id=request_id,
                    action_type="after_sale_create",
                    operation=operation,
                ),
                idempotency_service.execute(
                    user_id=str(user_id),
                    request_id=request_id,
                    action_type="after_sale_create",
                    operation=operation,
                ),
                return_exceptions=True,
            )
            successful = [result for result in results if isinstance(result, dict)]
            in_progress = [result for result in results if isinstance(result, IdempotencyInProgress)]
            unexpected = [result for result in results if not isinstance(result, (dict, IdempotencyInProgress))]
            assert not unexpected, results
            assert len(successful) + len(in_progress) == 2, results
            assert len(successful) >= 1

            async with integration_session_factory.begin() as session:
                count = await session.scalar(select(func.count(AfterSale.id)).where(AfterSale.user_id == user_id))
                assert count == 1

            cached = await idempotency_service.execute(
                user_id=str(user_id),
                request_id=request_id,
                action_type="after_sale_create",
                operation=operation,
            )
            assert cached["orderItemId"] == order_item_id
            await idempotency_store.release(
                make_idempotency_key(str(user_id), request_id, "after_sale_create"), use_redis=True
            )
        finally:
            await _delete_after_sale_fixture(integration_session_factory, user_id, product_id, order_id)
            await redis.aclose()

    asyncio.run(run())
