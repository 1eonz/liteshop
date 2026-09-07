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
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.idempotency import idempotency_store
from app.models.inventory import InventoryLedger
from app.models.product import Sku, Spu
from app.repositories.inventory import InsufficientStock, InventoryRepository

pytestmark = pytest.mark.skipif(
    os.getenv("LITESHOP_RUN_INTEGRATION") != "1",
    reason="设置 LITESHOP_RUN_INTEGRATION=1 后才运行真实 PostgreSQL/Redis 验收",
)


@pytest.fixture
def integration_session_factory() -> Generator[async_sessionmaker[AsyncSession], None, None]:
    """为集成测试创建独立连接池，避免污染应用全局连接。"""
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
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
