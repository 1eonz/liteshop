"""数据库订单工作流的业务分支测试。"""

import asyncio
import hashlib
import hmac
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums.order import OrderStatus
from app.enums.payment import PaymentProvider
from app.models.order import Order
from app.repositories.inventory import InventoryRepository
from app.repositories.order import OrderRepository
from app.repositories.payment import PaymentRepository
from app.repositories.product import ProductRepository
from app.schemas.orders import OrderCreate
from app.schemas.payments import PaymentCallback, PaymentCreate
from app.services.freight import FreightService
from app.services.order_workflow import OrderWorkflow, OrderWorkflowError, PriceChanged

SESSION = cast(AsyncSession, object())


def _order(**overrides: object) -> SimpleNamespace:
    """构造工作流响应所需订单。"""
    now = datetime.now(UTC)
    values: dict[str, object] = {
        "id": 7,
        "order_no": "LS-7",
        "user_id": 3,
        "status": OrderStatus.PENDING_PAYMENT.value,
        "refund_status": "NONE",
        "total_amount": 1100,
        "product_amount": 1000,
        "freight_amount": 100,
        "discount_amount": 0,
        "paid_amount": None,
        "address_snapshot": {"provinceCode": "110000"},
        "remark": None,
        "paid_at": None,
        "shipped_at": None,
        "completed_at": None,
        "cancelled_at": None,
        "cancel_reason": None,
        "created_at": now,
        "updated_at": now,
        "expired_at": now,
        "shipping_company_code": "",
        "tracking_no": "",
        "items": [],
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _sku(**overrides: object) -> SimpleNamespace:
    """构造带商品关系的 SKU。"""
    spu = SimpleNamespace(id=2, name="商品", status="ON_SHELF", deleted_at=None)
    values: dict[str, object] = {
        "id": 11,
        "code": "SKU-11",
        "name": "默认规格",
        "status": "ACTIVE",
        "price_cents": 1000,
        "weight_grams": 500,
        "spec_values": {},
        "image": "",
        "spu": spu,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _workflow(
    order: SimpleNamespace | None = None,
) -> tuple[OrderWorkflow, AsyncMock, AsyncMock, AsyncMock, AsyncMock, AsyncMock]:
    """构造可观察所有仓储调用的订单工作流。"""
    products = AsyncMock(spec=ProductRepository)
    inventory = AsyncMock(spec=InventoryRepository)
    orders = AsyncMock(spec=OrderRepository)
    payments = AsyncMock(spec=PaymentRepository)
    freight = AsyncMock(spec=FreightService)
    current = order or _order()
    orders.get.return_value = current
    orders.get_for_update.return_value = current
    orders.transition.return_value = current
    orders.get_by_request.return_value = None
    payments.get_by_request.return_value = None
    payments.get_for_order.return_value = None
    workflow = OrderWorkflow(products, inventory, orders, payments, freight)
    return workflow, products, inventory, orders, payments, freight


def _order_payload(**updates: object) -> OrderCreate:
    """构造金额为整数分的有效下单请求。"""
    values: dict[str, object] = {
        "items": [{"skuId": 11, "quantity": 1, "priceCents": 1000}],
        "addressSnapshot": {"provinceCode": "110000"},
        "productAmount": 1000,
        "freightAmount": 100,
        "totalAmount": 1100,
    }
    values.update(updates)
    return OrderCreate.model_validate(values)


def _callback(provider: PaymentProvider, secret: str, **updates: object) -> PaymentCallback:
    """构造使用正式五字段载荷签名的支付回调。"""
    values: dict[str, object] = {
        "orderId": 7,
        "callbackId": "callback-7",
        "amountCents": 1100,
        "providerTradeNo": "trade-7",
        "signature": "pending",
    }
    values.update(updates)
    unsigned = PaymentCallback.model_validate(values)
    canonical = (
        f"{provider.value}:{unsigned.order_id}:{unsigned.amount_cents}:"
        f"{unsigned.callback_id}:{unsigned.provider_trade_no}"
    )
    return unsigned.model_copy(
        update={"signature": hmac.new(secret.encode(), canonical.encode(), hashlib.sha256).hexdigest()}
    )


def test_create_order_success_and_early_returns() -> None:
    """下单成功应校验服务端价格、运费并锁库存。"""
    workflow, products, inventory, orders, _payments, freight = _workflow()
    sku = _sku()
    products.get_sku_for_update.return_value = sku
    freight.calculate_lines.return_value = 100
    created = _order()
    orders.create.return_value = created

    async def run() -> None:
        assert cast(object, await workflow.create_order(SESSION, 3, "request-1", _order_payload())) is created
        inventory.lock.assert_awaited_once_with(SESSION, 11, 1, "request-1", "request-1")
        kwargs = orders.create.await_args.kwargs
        assert kwargs["product_amount"] == 1000
        assert kwargs["freight_amount"] == 100
        orders.get_by_request.return_value = created
        assert cast(object, await workflow.create_order(SESSION, 3, "request-1", _order_payload())) is created
        empty = _order_payload().model_copy(update={"items": []})
        orders.get_by_request.return_value = None
        with pytest.raises(OrderWorkflowError, match="不能为空"):
            await workflow.create_order(SESSION, 3, "empty", empty)

    asyncio.run(run())


@pytest.mark.parametrize(
    ("sku", "payload", "freight", "error_type", "message"),
    [
        (None, _order_payload(), 100, OrderWorkflowError, "不存在"),
        (
            _sku(spu=SimpleNamespace(id=2, name="商品", status="OFF_SHELF", deleted_at=None)),
            _order_payload(),
            100,
            OrderWorkflowError,
            "已下架",
        ),
        (_sku(status="DISABLED"), _order_payload(), 100, OrderWorkflowError, "已停用"),
        (_sku(price_cents=999), _order_payload(), 100, PriceChanged, "价格已变更"),
        (_sku(), _order_payload(productAmount=999), 100, PriceChanged, "商品金额已变更"),
        (_sku(), _order_payload(), 99, PriceChanged, "运费已变更"),
        (_sku(), _order_payload(totalAmount=1200), 100, PriceChanged, "金额校验失败"),
    ],
)
def test_create_order_rejects_invalid_snapshots(
    sku: SimpleNamespace | None,
    payload: OrderCreate,
    freight: int,
    error_type: type[OrderWorkflowError],
    message: str,
) -> None:
    """下单必须拒绝无效 SKU、下架商品和不一致金额。"""
    workflow, products, _inventory, _orders, _payments, freight_service = _workflow()
    products.get_sku_for_update.return_value = sku
    freight_service.calculate_lines.return_value = freight
    with pytest.raises(error_type, match=message):
        asyncio.run(workflow.create_order(SESSION, 3, "request", payload))


def test_order_ownership_shipping_price_and_expiry_branches() -> None:
    """订单归属、发货、改价和过期路径拒绝非法状态。"""
    item = SimpleNamespace(sku_id=11, quantity=2)
    order = _order(items=[item])
    workflow, _products, inventory, orders, _payments, _freight = _workflow(order)

    async def run() -> None:
        assert cast(object, await workflow.get_owned_order(SESSION, 7, 3)) is order
        order.user_id = 4
        with pytest.raises(OrderWorkflowError, match="不存在"):
            await workflow.get_owned_order(SESSION, 7, 3)
        with pytest.raises(OrderWorkflowError, match="不存在"):
            await workflow.cancel_owned_order(SESSION, 7, 3, "r")
        with pytest.raises(OrderWorkflowError, match="不存在"):
            await workflow.confirm_owned_order(SESSION, 7, 3)
        order.user_id = 3
        orders.list_for_user.return_value = ([order], 1)
        listed = await workflow.list_owned_orders(SESSION, 3, 0, 20)
        assert cast(object, listed) == ([order], 1)

        order.status = OrderStatus.PAID.value
        orders.transition.return_value = order
        shipped = await workflow.ship_order(SESSION, 7, "SF", "SF123", "ship-r")
        assert shipped.tracking_no == "SF123"
        inventory.deduct.assert_awaited_once_with(SESSION, 11, 2, "LS-7", "ship-r")
        order.status = OrderStatus.SHIPPED.value
        with pytest.raises(OrderWorkflowError, match="已支付"):
            await workflow.ship_order(SESSION, 7, "SF", "SF123", "ship-r2")

        with pytest.raises(OrderWorkflowError, match="待付款"):
            await workflow.change_order_price(SESSION, 7, 1000)
        order.status = OrderStatus.PENDING_PAYMENT.value
        with pytest.raises(OrderWorkflowError, match="允许范围"):
            await workflow.change_order_price(SESSION, 7, 1200)
        with pytest.raises(OrderWorkflowError, match="允许范围"):
            await workflow.change_order_price(SESSION, 7, -1)
        order.status = OrderStatus.PAID.value
        assert cast(object, await workflow.expire_order(SESSION, cast(Order, order), "expire-r")) is order

    asyncio.run(run())


def test_create_payment_covers_owner_amount_and_idempotency() -> None:
    """支付创建覆盖归属、状态、金额和重复请求。"""
    order = _order()
    workflow, _products, _inventory, _orders, payments, _freight = _workflow(order)
    payload = PaymentCreate.model_validate({"orderId": 7, "provider": "WECHAT", "amountCents": 1100})
    payment = SimpleNamespace(status="PENDING")

    async def run() -> None:
        order.user_id = 4
        with pytest.raises(OrderWorkflowError, match="不属于"):
            await workflow.create_payment(SESSION, 3, "pay-1", payload)
        order.user_id = 3
        order.status = OrderStatus.PAID.value
        with pytest.raises(OrderWorkflowError, match="不可支付"):
            await workflow.create_payment(SESSION, 3, "pay-1", payload)
        order.status = OrderStatus.PENDING_PAYMENT.value
        order.total_amount = 1000
        with pytest.raises(PriceChanged, match="不一致"):
            await workflow.create_payment(SESSION, 3, "pay-1", payload)
        order.total_amount = 1100
        payments.get_by_request.return_value = payment
        assert cast(object, await workflow.create_payment(SESSION, 3, "pay-1", payload)) is payment
        payments.get_by_request.return_value = None
        payments.get_for_order.return_value = payment
        assert cast(object, await workflow.create_payment(SESSION, 3, "pay-2", payload)) is payment
        payment.status = "FAILED"
        created = SimpleNamespace(status="PENDING")
        payments.create.return_value = created
        assert cast(object, await workflow.create_payment(SESSION, 3, "pay-3", payload)) is created

    asyncio.run(run())


def test_payment_callback_covers_replay_and_rejection_paths() -> None:
    """支付回调覆盖验签、重放、渠道、金额、状态和流水校验。"""
    secret = "s" * 32
    provider = PaymentProvider.WECHAT
    payload = _callback(provider, secret)
    order = _order()
    workflow, _products, _inventory, _orders, payments, _freight = _workflow(order)
    existing = SimpleNamespace(
        order_id=7,
        amount_cents=1100,
        channel=provider.value,
        status="SUCCESS",
        transaction_id="trade-7",
    )

    async def run() -> None:
        payments.get_by_callback.return_value = existing
        assert cast(object, await workflow.payment_callback(SESSION, payload, provider, secret)) is existing
        existing.order_id = 8
        with pytest.raises(OrderWorkflowError, match="其他订单"):
            await workflow.payment_callback(SESSION, payload, provider, secret)
        existing.order_id = 7
        existing.amount_cents = 1
        with pytest.raises(OrderWorkflowError, match="不匹配"):
            await workflow.payment_callback(SESSION, payload, provider, secret)
        existing.amount_cents = 1100
        existing.transaction_id = "other"
        with pytest.raises(OrderWorkflowError, match="流水号不匹配"):
            await workflow.payment_callback(SESSION, payload, provider, secret)

        payments.get_by_callback.return_value = None
        payments.get_for_order.return_value = None
        with pytest.raises(OrderWorkflowError, match="支付单不存在"):
            await workflow.payment_callback(SESSION, payload, provider, secret)
        pending = SimpleNamespace(
            order_id=7,
            amount_cents=1100,
            channel=PaymentProvider.ALIPAY.value,
            status="PENDING",
            transaction_id=None,
        )
        payments.get_for_order.return_value = pending
        with pytest.raises(OrderWorkflowError, match="渠道不匹配"):
            await workflow.payment_callback(SESSION, payload, provider, secret)
        pending.channel = provider.value
        pending.amount_cents = 1
        with pytest.raises(PriceChanged, match="金额不匹配"):
            await workflow.payment_callback(SESSION, payload, provider, secret)
        pending.amount_cents = 1100
        order.status = OrderStatus.CANCELLED.value
        with pytest.raises(OrderWorkflowError, match="退款流程"):
            await workflow.payment_callback(SESSION, payload, provider, secret)
        order.status = OrderStatus.COMPLETED.value
        with pytest.raises(OrderWorkflowError, match="状态不允许"):
            await workflow.payment_callback(SESSION, payload, provider, secret)
        pending.status = "SUCCESS"
        pending.transaction_id = "other"
        order.status = OrderStatus.PENDING_PAYMENT.value
        with pytest.raises(OrderWorkflowError, match="流水号不匹配"):
            await workflow.payment_callback(SESSION, payload, provider, secret)
        pending.transaction_id = "trade-7"
        assert cast(object, await workflow.payment_callback(SESSION, payload, provider, secret)) is pending

        invalid = payload.model_copy(update={"signature": "invalid"})
        with pytest.raises(OrderWorkflowError, match="验签失败"):
            await workflow.payment_callback(SESSION, invalid, provider, secret)

    asyncio.run(run())
