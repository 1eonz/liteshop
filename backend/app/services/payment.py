"""支付回调验签、金额校验和幂等处理。"""

import hashlib
import hmac
from dataclasses import dataclass

from ..enums.order import OrderStatus
from ..enums.payment import PaymentProvider
from .order import InvalidOrderTransition, OrderService


class PaymentError(ValueError):
    """支付签名或金额校验失败。"""


@dataclass(frozen=True)
class PaymentIntent:
    """内存测试模式的支付单。"""

    payment_id: str
    order_id: int
    provider: PaymentProvider
    amount_cents: int
    request_id: str


class PaymentService:
    """支付服务，重复回调不会重复推进订单状态。"""

    def __init__(self, orders: OrderService, secret: str) -> None:
        self.orders = orders
        self.secret = secret.encode()
        self._callbacks: dict[str, tuple[int, int, PaymentProvider, str]] = {}
        self._intents: dict[tuple[int, str], PaymentIntent] = {}

    def create(
        self,
        user_id: str,
        order_id: int,
        provider: PaymentProvider,
        amount_cents: int,
        request_id: str,
    ) -> PaymentIntent:
        """创建支付单，重复订单请求返回原支付参数。"""
        order = self.orders.get(order_id)
        if order.user_id != user_id:
            raise PaymentError("订单不存在")
        if order.status is not OrderStatus.PENDING_PAYMENT:
            raise PaymentError("订单当前不可支付")
        if order.total_amount != amount_cents:
            raise PaymentError("支付金额与订单金额不一致")
        key = (order_id, request_id)
        existing = self._intents.get(key)
        if existing is not None:
            return existing
        intent = PaymentIntent(
            payment_id=f"pay-{order_id}-{len(self._intents) + 1}",
            order_id=order_id,
            provider=provider,
            amount_cents=amount_cents,
            request_id=request_id,
        )
        self._intents[key] = intent
        return intent

    def verify_signature(self, payload: str, signature: str, secret: bytes | None = None) -> bool:
        """使用 HMAC-SHA256 验证沙箱回调签名。"""
        expected = hmac.new(secret or self.secret, payload.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    def callback(
        self,
        order_id: int,
        callback_id: str,
        amount_cents: int,
        signature: str,
        provider: PaymentProvider = PaymentProvider.WECHAT,
        provider_trade_no: str = "",
        *,
        allow_legacy: bool = True,
        secret: str | None = None,
    ) -> bool:
        """校验回调并推进订单，重复 callback_id 返回成功但不重复处理。"""
        payload = f"{provider.value}:{order_id}:{amount_cents}:{callback_id}:{provider_trade_no}"
        secret_bytes = secret.encode() if secret is not None else None
        valid = self.verify_signature(payload, signature, secret_bytes)
        if not valid and allow_legacy:
            legacy_payload = f"{order_id}:{amount_cents}:{callback_id}"
            valid = self.verify_signature(legacy_payload, signature, secret_bytes)
        if not valid:
            raise PaymentError("支付回调验签失败")
        existing_callback = self._callbacks.get(callback_id)
        if existing_callback is not None:
            if existing_callback != (order_id, amount_cents, provider, provider_trade_no):
                raise PaymentError("支付回调 ID 已用于其他订单")
            return True
        intents = [
            intent for (candidate_order_id, _), intent in self._intents.items() if candidate_order_id == order_id
        ]
        if not intents:
            raise PaymentError("支付单不存在")
        if any(intent.provider is not provider for intent in intents):
            raise PaymentError("支付渠道不匹配")
        order = self.orders.get(order_id)
        if order.total_amount != amount_cents:
            raise PaymentError("支付金额不匹配")
        try:
            self.orders.transition(order_id, OrderStatus.PAID)
        except InvalidOrderTransition as exc:
            raise PaymentError("订单状态不允许支付") from exc
        self._callbacks[callback_id] = (order_id, amount_cents, provider, provider_trade_no)
        return True
