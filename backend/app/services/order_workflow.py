"""基于数据库事务的订单、库存和支付工作流。"""

import hashlib
import hmac
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from ..enums.order import OrderStatus
from ..enums.payment import PaymentProvider
from ..models.order import Order, Payment
from ..repositories.inventory import InventoryRepository
from ..repositories.order import OrderRepository
from ..repositories.payment import PaymentRepository
from ..repositories.product import ProductRepository
from ..schemas.orders import OrderCreate
from ..schemas.payments import PaymentCallback, PaymentCreate
from .freight import FreightLine, FreightService


class OrderWorkflowError(ValueError):
    """订单工作流业务异常。"""


class PriceChanged(OrderWorkflowError):
    """客户端价格快照与当前 SKU 价格不一致。"""


def payment_callback_fingerprint(payload: PaymentCallback, provider: PaymentProvider | None = None) -> str:
    """生成包含渠道和渠道交易号的支付回调稳定指纹。"""
    channel = provider.value if provider is not None else ""
    canonical = f"{channel}:{payload.order_id}:{payload.amount_cents}:{payload.callback_id}:{payload.provider_trade_no}"
    return hashlib.sha256(canonical.encode()).hexdigest()


def payment_callback_signature_payload(payload: PaymentCallback, provider: PaymentProvider) -> str:
    """生成支付回调签名的规范载荷，渠道和交易号均不可省略。"""
    return (
        f"{provider.value}:{payload.order_id}:{payload.amount_cents}:{payload.callback_id}:{payload.provider_trade_no}"
    )


def verify_payment_callback_signature(
    payload: PaymentCallback,
    secret: str,
    provider: PaymentProvider | None = None,
    *,
    allow_legacy: bool = False,
) -> None:
    """校验支付回调签名；仅开发兼容模式允许旧版三字段载荷。"""
    if provider is not None:
        signature_payload = payment_callback_signature_payload(payload, provider)
    else:
        # 旧调用方没有渠道上下文，只能按旧载荷校验；生产入口始终传入 provider。
        signature_payload = f"{payload.order_id}:{payload.amount_cents}:{payload.callback_id}"
    expected = hmac.new(secret.encode(), signature_payload.encode(), hashlib.sha256).hexdigest()
    if hmac.compare_digest(expected, payload.signature):
        return
    if allow_legacy and provider is not None:
        legacy_payload = f"{payload.order_id}:{payload.amount_cents}:{payload.callback_id}"
        legacy_expected = hmac.new(secret.encode(), legacy_payload.encode(), hashlib.sha256).hexdigest()
        if hmac.compare_digest(legacy_expected, payload.signature):
            return
    raise OrderWorkflowError("支付回调验签失败")


class OrderWorkflow:
    """在调用方提供的 AsyncSession 事务中协调库存、订单和支付。"""

    def __init__(
        self,
        products: ProductRepository | None = None,
        inventory: InventoryRepository | None = None,
        orders: OrderRepository | None = None,
        payments: PaymentRepository | None = None,
        freight: FreightService | None = None,
    ) -> None:
        self.products = products or ProductRepository()
        self.inventory = inventory or InventoryRepository()
        self.orders = orders or OrderRepository()
        self.payments = payments or PaymentRepository()
        self.freight = freight or FreightService(products=self.products)

    async def create_order(self, session: AsyncSession, user_id: int, request_id: str, payload: OrderCreate) -> Order:
        """校验价格并锁定库存后创建订单，异常由外层事务自动回滚。"""
        existing = await self.orders.get_by_request(session, user_id, request_id)
        if existing is not None:
            return existing
        if not payload.items:
            raise OrderWorkflowError("订单商品不能为空")

        rows: list[dict[str, object]] = []
        freight_lines: list[FreightLine] = []
        product_amount = 0
        for item in sorted(payload.items, key=lambda candidate: candidate.sku_id):
            sku = await self.products.get_sku_for_update(session, item.sku_id)
            if sku is None:
                raise OrderWorkflowError(f"SKU {item.sku_id} 不存在")
            if sku.spu is None or sku.spu.deleted_at is not None or sku.spu.status != "ON_SHELF":
                raise OrderWorkflowError(f"SKU {item.sku_id} 所属商品已下架")
            if sku.status != "ACTIVE":
                raise OrderWorkflowError(f"SKU {item.sku_id} 已停用")
            if sku.price_cents != item.price_cents:
                raise PriceChanged(f"SKU {item.sku_id} 价格已变更")
            await self.inventory.lock(session, sku.id, item.quantity, request_id, request_id)
            subtotal = sku.price_cents * item.quantity
            product_amount += subtotal
            rows.append(
                {
                    "sku_id": sku.id,
                    "product_id": sku.spu.id,
                    "product_name": sku.spu.name if sku.spu is not None else sku.name,
                    "sku_code": sku.code,
                    "sku_name": sku.name,
                    "spec_values": sku.spec_values,
                    "product_image": sku.image,
                    "quantity": item.quantity,
                    "price_cents": sku.price_cents,
                    "weight_grams": sku.weight_grams or 0,
                    "total_amount": subtotal,
                }
            )
            freight_lines.append(
                FreightLine(
                    quantity=item.quantity,
                    weight_grams=sku.weight_grams or 0,
                    price_cents=sku.price_cents,
                )
            )

        if payload.product_amount is not None and payload.product_amount != product_amount:
            raise PriceChanged("商品金额已变更")
        province_code = payload.address_snapshot.get("provinceCode", payload.address_snapshot.get("province_code", ""))
        calculated_freight = await self.freight.calculate_lines(
            session,
            freight_lines,
            province_code,
            product_amount,
        )
        if payload.freight_amount != calculated_freight:
            raise PriceChanged("运费已变更，请重新计算")
        expected_total = product_amount + calculated_freight
        if payload.total_amount != expected_total:
            raise PriceChanged("订单金额校验失败")
        order = await self.orders.create(
            session,
            user_id=user_id,
            order_no=f"LS{datetime.now(UTC):%Y%m%d%H%M%S}{uuid4().hex[:8]}",
            client_request_id=request_id,
            total_amount=payload.total_amount,
            product_amount=product_amount,
            freight_amount=calculated_freight,
            discount_amount=0,
            address_snapshot=payload.address_snapshot,
            items=rows,
            expired_at=datetime.now(UTC) + timedelta(minutes=30),
            remark=payload.remark,
        )
        return order

    async def cancel_order(
        self, session: AsyncSession, order_id: int, request_id: str, reason: str = "用户取消"
    ) -> Order:
        """取消订单并释放所有锁定库存。"""
        order = await self.orders.get_for_update(session, order_id)
        if OrderStatus(order.status) != OrderStatus.PENDING_PAYMENT:
            raise OrderWorkflowError("只有待支付订单可以取消")
        for item in sorted(order.items, key=lambda candidate: candidate.sku_id):
            await self.inventory.release(session, item.sku_id, item.quantity, order.order_no, request_id)
        changed = await self.orders.transition(session, order_id, OrderStatus.CANCELLED)
        changed.cancelled_at = datetime.now(UTC)
        changed.cancel_reason = reason
        await session.flush()
        return changed

    async def get_owned_order(self, session: AsyncSession, order_id: int, user_id: int) -> Order:
        """读取并校验订单归属。"""
        order = await self.orders.get(session, order_id)
        if order.user_id != user_id:
            raise OrderWorkflowError("订单不存在")
        return order

    async def list_owned_orders(
        self,
        session: AsyncSession,
        user_id: int,
        offset: int,
        limit: int,
    ) -> tuple[list[Order], int]:
        """读取当前用户订单列表。"""
        return await self.orders.list_for_user(session, user_id, offset, limit)

    async def cancel_owned_order(
        self,
        session: AsyncSession,
        order_id: int,
        user_id: int,
        request_id: str,
    ) -> Order:
        """校验归属后取消待付款订单。"""
        order = await self.orders.get_for_update(session, order_id)
        if order.user_id != user_id:
            raise OrderWorkflowError("订单不存在")
        return await self.cancel_order(session, order_id, request_id)

    async def confirm_owned_order(self, session: AsyncSession, order_id: int, user_id: int) -> Order:
        """校验归属后确认收货。"""
        order = await self.orders.get_for_update(session, order_id)
        if order.user_id != user_id:
            raise OrderWorkflowError("订单不存在")
        return await self.confirm_order(session, order_id)

    async def confirm_order(self, session: AsyncSession, order_id: int) -> Order:
        """确认收货，只允许已发货订单完成。"""
        changed = await self.orders.transition(session, order_id, OrderStatus.COMPLETED)
        changed.completed_at = datetime.now(UTC)
        await session.flush()
        return changed

    async def ship_order(
        self,
        session: AsyncSession,
        order_id: int,
        logistics_company_code: str,
        tracking_no: str,
        request_id: str,
    ) -> Order:
        """发货时扣减实物和锁定库存，并推进到已发货。"""
        order = await self.orders.get_for_update(session, order_id)
        if order.status != OrderStatus.PAID.value:
            raise OrderWorkflowError("只有已支付订单可以发货")
        for item in sorted(order.items, key=lambda candidate: candidate.sku_id):
            await self.inventory.deduct(session, item.sku_id, item.quantity, order.order_no, request_id)
        order.shipping_company_code = logistics_company_code
        order.tracking_no = tracking_no
        order.shipped_at = datetime.now(UTC)
        return await self.orders.transition(session, order_id, OrderStatus.SHIPPED)

    async def change_order_price(self, session: AsyncSession, order_id: int, total_amount: int) -> Order:
        """仅允许待付款订单改价，通过优惠额保持明细快照不变。"""
        order = await self.orders.get_for_update(session, order_id)
        if order.status != OrderStatus.PENDING_PAYMENT.value:
            raise OrderWorkflowError("只有待付款订单可以改价")
        gross_amount = order.product_amount + order.freight_amount
        if total_amount < 0 or total_amount > gross_amount:
            raise OrderWorkflowError("改价金额超出允许范围")
        order.total_amount = total_amount
        order.discount_amount = gross_amount - total_amount
        order.updated_at = datetime.now(UTC)
        await session.flush()
        return order

    async def expire_order(self, session: AsyncSession, order: Order, request_id: str) -> Order:
        """任务到期取消待付款订单并释放已锁定库存。"""
        if order.status != OrderStatus.PENDING_PAYMENT.value:
            return order
        for item in sorted(order.items, key=lambda candidate: candidate.sku_id):
            await self.inventory.release(session, item.sku_id, item.quantity, order.order_no, request_id)
        changed = await self.orders.transition(session, order.id, OrderStatus.CANCELLED)
        changed.cancelled_at = datetime.now(UTC)
        changed.cancel_reason = "支付超时"
        await session.flush()
        return changed

    async def create_payment(
        self, session: AsyncSession, user_id: int, request_id: str, payload: PaymentCreate
    ) -> Payment:
        """创建支付单并校验订单归属与整数分金额。"""
        # 必须先锁订单并校验归属，避免攻击者用请求 ID 探测其他用户支付单。
        order = await self.orders.get_for_update(session, payload.order_id)
        if order.user_id != user_id:
            raise OrderWorkflowError("订单不属于当前用户")
        if order.status != OrderStatus.PENDING_PAYMENT.value:
            raise OrderWorkflowError("订单当前不可支付")
        if order.total_amount != payload.amount_cents:
            raise PriceChanged("支付金额与订单金额不一致")
        existing = await self.payments.get_by_request(session, order.id, request_id)
        if existing is not None:
            return existing
        pending = await self.payments.get_for_order(session, order.id, for_update=True)
        if pending is not None and pending.status == "PENDING":
            return pending
        return await self.payments.create(
            session,
            order_id=order.id,
            user_id=user_id,
            provider=payload.provider.value,
            amount_cents=payload.amount_cents,
            client_request_id=request_id,
        )

    async def payment_callback(
        self,
        session: AsyncSession,
        payload: PaymentCallback,
        provider: PaymentProvider,
        secret: str,
        *,
        allow_legacy_signature: bool = False,
    ) -> Payment:
        """验签、金额校验并推进订单；发货时才扣减实物库存。"""
        verify_payment_callback_signature(payload, secret, provider, allow_legacy=allow_legacy_signature)
        order = await self.orders.get_for_update(session, payload.order_id)
        callback_payment = await self.payments.get_by_callback(session, payload.callback_id)
        if callback_payment is not None:
            if callback_payment.order_id != payload.order_id:
                raise OrderWorkflowError("支付回调 ID 已用于其他订单")
            if callback_payment.amount_cents != payload.amount_cents or callback_payment.channel != provider.value:
                raise OrderWorkflowError("支付回调与支付单不匹配")
            if callback_payment.status == "SUCCESS" and callback_payment.transaction_id == payload.provider_trade_no:
                return callback_payment
            raise OrderWorkflowError("支付回调已处理但流水号不匹配")
        payment = await self.payments.get_for_order(session, payload.order_id, for_update=True)
        if payment is None:
            raise OrderWorkflowError("支付单不存在")
        if payment.channel != provider.value:
            raise OrderWorkflowError("支付渠道不匹配")
        if payment.amount_cents != payload.amount_cents:
            raise PriceChanged("支付回调金额不匹配")
        if payment.status == "SUCCESS":
            if payment.transaction_id != payload.provider_trade_no:
                raise OrderWorkflowError("支付流水号不匹配")
            return payment
        if order.status == OrderStatus.CANCELLED.value:
            # 超时任务可能先于回调提交；不能把已取消订单重新置为已支付。
            raise OrderWorkflowError("订单已取消，支付需要走退款流程")
        if order.status != OrderStatus.PENDING_PAYMENT.value:
            raise OrderWorkflowError("订单状态不允许支付")
        await self.orders.transition(session, order.id, OrderStatus.PAID)
        now = datetime.now(UTC)
        order.paid_amount = payment.amount_cents
        order.paid_at = now
        order.updated_at = now
        await session.flush()
        return await self.payments.mark_paid(
            session,
            payment,
            payload.callback_id,
            payload.provider_trade_no,
            payload.model_dump_json(by_alias=True),
        )


def payment_response(payment: Payment) -> dict[str, object]:
    """转换支付实体为不暴露 ORM 的响应。"""
    return {
        "id": payment.id,
        "orderId": payment.order_id,
        "provider": payment.channel,
        "status": payment.status,
        "amountCents": payment.amount_cents,
    }


def order_response(order: Order) -> dict[str, object]:
    """转换订单实体为跨端共享响应。"""
    expired_at = getattr(order, "expired_at", None)
    return {
        "id": order.id,
        "orderNo": order.order_no,
        "status": order.status,
        "totalAmount": order.total_amount,
        "productAmount": order.product_amount,
        "freightAmount": order.freight_amount,
        "discountAmount": order.discount_amount,
        "refundStatus": order.refund_status,
        "paidAmount": order.paid_amount,
        "addressSnapshot": order.address_snapshot,
        "remark": order.remark,
        "paidAt": order.paid_at.isoformat() if order.paid_at else None,
        "shippedAt": order.shipped_at.isoformat() if order.shipped_at else None,
        "completedAt": order.completed_at.isoformat() if order.completed_at else None,
        "cancelledAt": order.cancelled_at.isoformat() if order.cancelled_at else None,
        "cancelReason": order.cancel_reason,
        "createdAt": order.created_at.isoformat(),
        "expiredAt": expired_at.isoformat() if isinstance(expired_at, datetime) else None,
        "shippingCompanyCode": order.shipping_company_code,
        "trackingNo": order.tracking_no,
        "items": [
            {
                "id": item.id,
                "skuId": item.sku_id,
                "productId": item.product_id,
                "productName": item.product_name,
                "skuCode": item.sku_code,
                "skuName": item.sku_name,
                "specValues": item.spec_values,
                "productImage": item.product_image,
                "quantity": item.quantity,
                "priceCents": item.price_cents,
                "weightGrams": item.weight_grams,
                "discountAmount": item.discount_amount,
                "totalAmount": item.total_amount,
            }
            for item in order.items
        ],
    }
