"""可选的 PostgreSQL/Redis 集成验收。

默认不执行，避免单元测试依赖本机服务。设置 ``LITESHOP_RUN_INTEGRATION=1``
并先执行 Alembic 迁移后运行本文件，可验证真实数据库锁和 Redis NX 幂等。
"""

import asyncio
import hashlib
import hmac
import os
from collections.abc import AsyncIterator, Generator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

import app.core.token_store as token_store_module
import app.services.auth as auth_module
import app.services.cart as cart_module
import app.services.idempotency as idempotency_service_module
from app.core import idempotency as idempotency_module
from app.core.config import settings
from app.core.idempotency import idempotency_store, make_idempotency_key
from app.core.security import create_refresh_token, verify_refresh_token_claims
from app.core.token_store import refresh_token_store
from app.enums.after_sale import AfterSaleType
from app.enums.payment import PaymentProvider
from app.models.after_sale import AfterSale
from app.models.favorite import Favorite
from app.models.idempotency import IdempotencyRecord
from app.models.inventory import InventoryLedger
from app.models.order import Order, OrderItem, Payment
from app.models.product import Sku, Spu
from app.models.user import User
from app.repositories.inventory import InsufficientStock, InventoryRepository
from app.repositories.order import OrderRepository
from app.schemas.after_sale import AfterSaleCreate
from app.schemas.orders import OrderCreate
from app.schemas.payments import PaymentCallback, PaymentCreate
from app.services.after_sale import AfterSaleService, after_sale_response
from app.services.auth import AuthenticationError, AuthService
from app.services.cart import CartError, CartLine, CartService
from app.services.favorite import FavoriteService
from app.services.idempotency import IdempotencyInProgress, IdempotentResult, idempotency_service
from app.services.order_workflow import OrderWorkflow, OrderWorkflowError, payment_callback_signature_payload

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


async def _create_user_product_fixture(
    factory: async_sessionmaker[AsyncSession], reference: str, *, physical_stock: int = 1
) -> tuple[int, int, int]:
    """创建订单、收藏和支付集成测试共用的用户、商品和 SKU。"""
    now = datetime.now(UTC)
    async with factory.begin() as session:
        user = User(
            phone=f"137{uuid4().int % 10_000_000:07d}",
            nickname="集成测试用户",
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
            name=f"集成订单商品-{reference}",
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
            code=f"ORDER-IT-{uuid4().hex[:20]}",
            name="默认规格",
            spec_values={},
            spec_hash=uuid4().hex,
            price_cents=100,
            cost_cents=50,
            physical_stock=physical_stock,
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
        return user.id, sku.id, product.id


async def _delete_user_product_fixture(
    factory: async_sessionmaker[AsyncSession], user_id: int, product_id: int
) -> None:
    """按外键依赖顺序清理用户、订单、收藏和商品夹具。"""
    async with factory.begin() as session:
        order_ids = select(Order.id).where(Order.user_id == user_id)
        await session.execute(delete(Payment).where(Payment.order_id.in_(order_ids)))
        await session.execute(delete(Favorite).where(Favorite.user_id == user_id))
        await session.execute(delete(Order).where(Order.user_id == user_id))
        await session.execute(
            delete(InventoryLedger).where(
                InventoryLedger.sku_id.in_(select(Sku.id).where(Sku.product_id == product_id))
            )
        )
        await session.execute(delete(Sku).where(Sku.product_id == product_id))
        await session.execute(delete(Spu).where(Spu.id == product_id))
        await session.execute(delete(User).where(User.id == user_id))


def _order_payload(sku_id: int) -> OrderCreate:
    """构造使用服务器价格快照的最小订单请求。"""
    return OrderCreate.model_validate(
        {
            "items": [{"skuId": sku_id, "quantity": 1, "priceCents": 100}],
            "addressSnapshot": {"provinceCode": "110000", "receiverName": "集成用户"},
            "productAmount": 100,
            "freightAmount": 0,
            "totalAmount": 100,
        }
    )


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

        @asynccontextmanager
        async def local_transaction() -> AsyncIterator[AsyncSession]:
            """让集成测试使用当前事件循环创建的数据库连接。"""
            async with integration_session_factory() as session, session.begin():
                yield session

        monkeypatch.setattr(idempotency_service_module, "transaction", local_transaction)
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


def test_postgres_concurrent_order_creation_competes_for_stock(
    integration_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """两个真实事务同时下单时只能有一个事务锁定最后一件库存。"""

    async def run() -> None:
        reference = uuid4().hex
        user_id, sku_id, product_id = await _create_user_product_fixture(integration_session_factory, reference)
        workflow = OrderWorkflow()

        async def create_once(request_id: str) -> str:
            try:
                async with integration_session_factory.begin() as session:
                    order = await workflow.create_order(session, user_id, request_id, _order_payload(sku_id))
                    assert order.status == "PENDING_PAYMENT"
                return "created"
            except InsufficientStock:
                return "insufficient"

        try:
            results = await asyncio.gather(
                create_once(f"order-{reference}-a"),
                create_once(f"order-{reference}-b"),
            )
            assert sorted(results) == ["created", "insufficient"]
            async with integration_session_factory.begin() as session:
                sku = await session.get(Sku, sku_id)
                assert sku is not None
                assert sku.physical_stock == 1
                assert sku.locked_stock == 1
                order_count = await session.scalar(select(func.count(Order.id)).where(Order.user_id == user_id))
                assert order_count == 1
        finally:
            await _delete_user_product_fixture(integration_session_factory, user_id, product_id)

    asyncio.run(run())


def test_postgres_payment_callback_and_timeout_race_preserves_terminal_state(
    integration_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """支付回调与超时取消竞态只能留下已支付或已取消的一致终态。"""

    async def run() -> None:
        reference = uuid4().hex
        user_id, sku_id, product_id = await _create_user_product_fixture(integration_session_factory, reference)
        workflow = OrderWorkflow()
        request_id = f"payment-order-{reference}"
        payment_request_id = f"payment-{reference}"
        provider = PaymentProvider.WECHAT
        trade_no = f"WX-{reference}"
        callback_id = f"callback-{reference}"

        async with integration_session_factory.begin() as session:
            order = await workflow.create_order(session, user_id, request_id, _order_payload(sku_id))
            payment = await workflow.create_payment(
                session,
                user_id,
                payment_request_id,
                PaymentCreate.model_validate(
                    {
                        "orderId": order.id,
                        "provider": provider.value,
                        "amountCents": 100,
                    }
                ),
            )
            order_id = order.id
            payment_id = payment.id

        callback_without_signature = PaymentCallback.model_validate(
            {
                "orderId": order_id,
                "callbackId": callback_id,
                "amountCents": 100,
                "signature": "pending",
                "providerTradeNo": trade_no,
            }
        )
        secret = settings.payment_callback_secret_for(provider.value)
        signature_payload = payment_callback_signature_payload(callback_without_signature, provider)
        callback = callback_without_signature.model_copy(
            update={"signature": hmac.new(secret.encode(), signature_payload.encode(), hashlib.sha256).hexdigest()}
        )

        async def expire_once() -> str:
            try:
                async with integration_session_factory.begin() as session:
                    order_for_update = await OrderRepository().get_for_update(session, order_id)
                    changed = await workflow.expire_order(session, order_for_update, f"expire-{reference}")
                    return changed.status
            except OrderWorkflowError:
                return "REJECTED"

        async def callback_once() -> str:
            try:
                async with integration_session_factory.begin() as session:
                    changed = await workflow.payment_callback(session, callback, provider, secret)
                    return changed.status
            except OrderWorkflowError:
                return "REJECTED"

        try:
            results = await asyncio.gather(expire_once(), callback_once())
            assert set(results) <= {"CANCELLED", "PAID", "SUCCESS", "REJECTED"}
            assert "CANCELLED" in results or "PAID" in results or "SUCCESS" in results
            assert results.count("REJECTED") <= 1
            async with integration_session_factory.begin() as session:
                final_order = await session.get(Order, order_id)
                final_payment = await session.get(Payment, payment_id)
                final_sku = await session.get(Sku, sku_id)
                assert final_order is not None
                assert final_payment is not None
                assert final_sku is not None
                if final_order.status == "CANCELLED":
                    assert final_payment.status == "PENDING"
                    assert final_sku.locked_stock == 0
                elif final_order.status == "PAID":
                    assert final_payment.status == "SUCCESS"
                    assert final_payment.transaction_id == trade_no
                    assert final_sku.locked_stock == 1
                else:
                    pytest.fail(f"支付与超时竞态留下非法订单状态: {final_order.status}")
        finally:
            await _delete_user_product_fixture(integration_session_factory, user_id, product_id)

    asyncio.run(run())


def test_redis_sms_code_is_consumed_once_under_concurrency(monkeypatch: pytest.MonkeyPatch) -> None:
    """真实 Redis 验证码消费脚本在并发请求下只允许一个成功。"""

    async def run() -> None:
        redis = Redis.from_url(settings.redis_url, decode_responses=True)
        phone = f"139{uuid4().int % 10_000_000:07d}"
        key = f"sms:code:{phone}"
        await redis.ping()
        monkeypatch.setattr(auth_module, "redis_client", redis)
        monkeypatch.setattr(auth_module, "settings", type("DatabaseSettings", (), {"use_database": True})())
        await redis.set(key, "246810", ex=300)
        service = AuthService()

        async def verify_once() -> bool:
            try:
                await service.verify_sms_code(phone, "246810")
            except AuthenticationError:
                return False
            return True

        try:
            results = await asyncio.gather(verify_once(), verify_once())
            assert sorted(results) == [False, True]
            assert await redis.get(key) is None
        finally:
            await redis.delete(key)
            await redis.aclose()

    asyncio.run(run())


def test_redis_refresh_token_rotation_rejects_replay(monkeypatch: pytest.MonkeyPatch) -> None:
    """真实 Redis Lua 轮换脚本只能消费一次旧 refresh token。"""

    async def run() -> None:
        redis = Redis.from_url(settings.redis_url, decode_responses=True)
        await redis.ping()
        monkeypatch.setattr(token_store_module, "redis_client", redis)
        old_token = create_refresh_token("integration-user")
        old_claims = verify_refresh_token_claims(old_token)
        assert old_claims is not None
        next_tokens = [create_refresh_token("integration-user"), create_refresh_token("integration-user")]
        next_claims = [verify_refresh_token_claims(token) for token in next_tokens]
        assert all(claim is not None for claim in next_claims)
        valid_claims = [claim for claim in next_claims if claim is not None]
        ttl = settings.refresh_token_expire_days * 24 * 60 * 60
        await refresh_token_store.register(old_claims.jti, old_claims.subject, ttl)
        try:
            results = await asyncio.gather(
                refresh_token_store.rotate(old_claims.jti, valid_claims[0].jti, old_claims.subject, ttl),
                refresh_token_store.rotate(old_claims.jti, valid_claims[1].jti, old_claims.subject, ttl),
            )
            assert sorted(results) == [False, True]
            assert await refresh_token_store.consume(old_claims.jti, old_claims.subject) is False
            consumed = [await refresh_token_store.consume(claim.jti, claim.subject) for claim in valid_claims]
            assert sorted(consumed) == [False, True]
        finally:
            await refresh_token_store.revoke(old_claims.jti)
            for claim in valid_claims:
                await refresh_token_store.revoke(claim.jti)
            await redis.aclose()

    asyncio.run(run())


def test_redis_cart_request_is_idempotent_and_failures_are_mapped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """真实 Redis 购物车请求重复执行不累加，服务不可用时返回领域错误。"""

    async def run() -> None:
        redis = Redis.from_url(settings.redis_url, decode_responses=True)
        await redis.ping()
        user_id = f"integration-cart-{uuid4().hex}"
        request_id = f"add-{uuid4().hex}"
        cart_key = f"cart:{user_id}"
        request_key = f"cart:request:{user_id}:{request_id}"
        monkeypatch.setattr(cart_module, "redis_client", redis)
        service = CartService()
        try:
            first = await service.add(user_id, CartLine(991, 2, 199), use_database=True, request_id=request_id)
            second = await service.add(user_id, CartLine(991, 2, 199), use_database=True, request_id=request_id)
            assert first == second
            assert (await service.list(user_id, use_database=True)) == [CartLine(991, 2, 199)]
            await redis.delete(cart_key, request_key)

            class BrokenRedis:
                async def hvals(self, _key: str) -> list[str]:
                    raise RedisError("redis unavailable")

            monkeypatch.setattr(cart_module, "redis_client", BrokenRedis())
            with pytest.raises(CartError, match="购物车服务暂不可用"):
                await service.list(user_id, use_database=True)
        finally:
            monkeypatch.setattr(cart_module, "redis_client", redis)
            await redis.delete(cart_key, request_key)
            await redis.aclose()

    asyncio.run(run())


def test_postgres_favorite_toggle_is_idempotent_under_concurrency(
    integration_session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """收藏切换通过 Redis+数据库幂等键只产生一条关系记录。"""

    async def run() -> None:
        reference = uuid4().hex
        user_id, _sku_id, product_id = await _create_user_product_fixture(integration_session_factory, reference)
        request_id = f"favorite-{reference}"
        action_type = f"favorite_toggle:{product_id}"
        key = make_idempotency_key(str(user_id), request_id, action_type)
        service = FavoriteService()
        redis = Redis.from_url(settings.redis_url, decode_responses=True)
        await redis.ping()
        monkeypatch.setattr(idempotency_module, "redis_client", redis)

        @asynccontextmanager
        async def local_transaction() -> AsyncIterator[AsyncSession]:
            """让收藏幂等测试在独立连接池中运行，避免跨事件循环复用连接。"""
            async with integration_session_factory() as session, session.begin():
                yield session

        monkeypatch.setattr(idempotency_service_module, "transaction", local_transaction)

        async def operation(session: AsyncSession | None) -> IdempotentResult:
            assert session is not None
            response = await service.toggle(session, user_id, product_id)
            return IdempotentResult(response, "favorite", str(product_id))

        try:
            results = await asyncio.gather(
                idempotency_service.execute(
                    user_id=str(user_id),
                    request_id=request_id,
                    action_type=action_type,
                    operation=operation,
                ),
                idempotency_service.execute(
                    user_id=str(user_id),
                    request_id=request_id,
                    action_type=action_type,
                    operation=operation,
                ),
                return_exceptions=True,
            )
            successful = [result for result in results if isinstance(result, dict)]
            in_progress = [result for result in results if isinstance(result, IdempotencyInProgress)]
            assert len(successful) == 1
            assert len(in_progress) == 1
            assert successful[0]["favorited"] is True

            async with integration_session_factory.begin() as session:
                count = await session.scalar(
                    select(func.count(Favorite.id)).where(
                        Favorite.user_id == user_id,
                        Favorite.product_id == product_id,
                    )
                )
                assert count == 1

            cached = await idempotency_service.execute(
                user_id=str(user_id),
                request_id=request_id,
                action_type=action_type,
                operation=operation,
            )
            assert cached == successful[0]
        finally:
            await idempotency_store.release(key, use_redis=True)
            async with integration_session_factory.begin() as session:
                await session.execute(
                    delete(IdempotencyRecord).where(
                        IdempotencyRecord.user_id == str(user_id),
                        IdempotencyRecord.request_id == request_id,
                        IdempotencyRecord.action_type == action_type,
                    )
                )
            await _delete_user_product_fixture(integration_session_factory, user_id, product_id)
            await redis.aclose()

    asyncio.run(run())
