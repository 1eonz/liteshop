"""plan-14 支付签名、订单归属和商品状态安全回归测试。"""

import asyncio
import hashlib
import hmac
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums.order import OrderStatus
from app.enums.payment import PaymentProvider
from app.repositories.inventory import InventoryRepository
from app.repositories.order import OrderRepository
from app.repositories.payment import PaymentRepository
from app.repositories.product import ProductRepository
from app.schemas.orders import OrderCreate, OrderItemCreate
from app.schemas.payments import PaymentCallback, PaymentCreate
from app.services.order import OrderService
from app.services.order_workflow import (
    OrderWorkflow,
    OrderWorkflowError,
    payment_callback_signature_payload,
    verify_payment_callback_signature,
)
from app.services.payment import PaymentError, PaymentService


def _callback(provider: PaymentProvider = PaymentProvider.WECHAT) -> PaymentCallback:
    """构造带完整渠道交易信息的回调。"""
    return PaymentCallback(
        order_id=7,
        callback_id="callback-7",
        amount_cents=12900,
        signature="placeholder",
        providerTradeNo="trade-7",
    )


def test_payment_signature_covers_provider_and_trade_number() -> None:
    """渠道或渠道交易号被篡改时，新签名必须失效。"""
    secret = "s" * 32
    provider = PaymentProvider.WECHAT
    payload = _callback(provider)
    canonical = payment_callback_signature_payload(payload, provider)
    signature = hmac.new(secret.encode(), canonical.encode(), hashlib.sha256).hexdigest()
    signed = payload.model_copy(update={"signature": signature})

    verify_payment_callback_signature(signed, secret, provider)
    tampered_trade = signed.model_copy(update={"provider_trade_no": "trade-other"})
    with pytest.raises(OrderWorkflowError, match="验签失败"):
        verify_payment_callback_signature(tampered_trade, secret, provider)
    with pytest.raises(OrderWorkflowError, match="验签失败"):
        verify_payment_callback_signature(signed, secret, PaymentProvider.ALIPAY)


def test_legacy_payment_signature_is_explicitly_development_only() -> None:
    """旧版三字段签名只有显式开启兼容时才允许通过。"""
    secret = "s" * 32
    payload = _callback()
    legacy = f"{payload.order_id}:{payload.amount_cents}:{payload.callback_id}"
    signature = hmac.new(secret.encode(), legacy.encode(), hashlib.sha256).hexdigest()
    signed = payload.model_copy(update={"signature": signature})

    with pytest.raises(OrderWorkflowError, match="验签失败"):
        verify_payment_callback_signature(signed, secret, PaymentProvider.WECHAT)
    verify_payment_callback_signature(signed, secret, PaymentProvider.WECHAT, allow_legacy=True)


def test_memory_payment_rejects_channel_mismatch() -> None:
    """内存沙箱支付回调也必须匹配支付单渠道。"""
    orders = OrderService()
    order = orders.create("user-1", "order-1", 12900)
    payments = PaymentService(orders, "s" * 32)
    payments.create("user-1", order.order_id, PaymentProvider.WECHAT, 12900, "payment-1")
    canonical = f"{PaymentProvider.ALIPAY.value}:{order.order_id}:12900:callback-1:trade-1"
    signature = hmac.new(("s" * 32).encode(), canonical.encode(), hashlib.sha256).hexdigest()

    with pytest.raises(PaymentError, match="支付渠道不匹配"):
        payments.callback(
            order.order_id,
            "callback-1",
            12900,
            signature,
            PaymentProvider.ALIPAY,
            "trade-1",
            allow_legacy=False,
        )


def test_create_payment_checks_order_owner_before_idempotency_lookup() -> None:
    """订单不属于当前用户时，不得先读取支付幂等记录。"""

    class Orders:
        async def get_for_update(self, _session: object, _order_id: int) -> SimpleNamespace:
            return SimpleNamespace(id=1, user_id=99, status=OrderStatus.PENDING_PAYMENT.value, total_amount=12900)

    class Payments:
        async def get_by_request(self, *_args: object, **_kwargs: object) -> None:
            raise AssertionError("归属校验失败时不应查询支付幂等记录")

        async def get_for_order(self, *_args: object, **_kwargs: object) -> None:
            raise AssertionError("归属校验失败时不应查询已有支付单")

    workflow = OrderWorkflow(
        orders=cast(OrderRepository, Orders()),
        payments=cast(PaymentRepository, Payments()),
    )
    payload = PaymentCreate(order_id=1, provider=PaymentProvider.WECHAT, amount_cents=12900)
    with pytest.raises(OrderWorkflowError, match="不属于当前用户"):
        asyncio.run(workflow.create_payment(cast(AsyncSession, object()), 1, "request-1", payload))


@pytest.mark.parametrize(
    ("spu_status", "deleted_at", "sku_status", "message"),
    [
        ("OFF_SHELF", None, "ACTIVE", "已下架"),
        ("ON_SHELF", datetime.now(UTC), "ACTIVE", "已下架"),
        ("ON_SHELF", None, "INACTIVE", "已停用"),
    ],
)
def test_create_order_rejects_unavailable_product_before_locking_stock(
    spu_status: str,
    deleted_at: datetime | None,
    sku_status: str,
    message: str,
) -> None:
    """商品删除、下架或 SKU 停用时必须在库存锁定前拒绝下单。"""

    class Products:
        async def get_sku_for_update(self, _session: object, _sku_id: int) -> SimpleNamespace:
            spu = SimpleNamespace(id=1, name="不可售商品", status=spu_status, deleted_at=deleted_at)
            return SimpleNamespace(
                id=1,
                spu=spu,
                status=sku_status,
                price_cents=12900,
                name="默认 SKU",
                code="SKU-1",
                spec_values={},
                image="",
                weight_grams=0,
            )

    class Inventory:
        async def lock(self, *_args: object, **_kwargs: object) -> None:
            raise AssertionError("下架商品不应锁定库存")

    class Orders:
        async def get_by_request(self, *_args: object, **_kwargs: object) -> None:
            return None

        async def create(self, *_args: object, **_kwargs: object) -> None:
            raise AssertionError("下架商品不应创建订单")

    workflow = OrderWorkflow(
        products=cast(ProductRepository, Products()),
        inventory=cast(InventoryRepository, Inventory()),
        orders=cast(OrderRepository, Orders()),
    )
    payload = OrderCreate.model_validate(
        {
            "items": [OrderItemCreate(sku_id=1, quantity=1, price_cents=12900)],
            "addressSnapshot": {},
            "totalAmount": 12900,
        }
    )
    with pytest.raises(OrderWorkflowError, match=message):
        asyncio.run(workflow.create_order(cast(AsyncSession, object()), 1, "request-1", payload))
