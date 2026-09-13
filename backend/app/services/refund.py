"""退款申请和渠道处理业务服务。"""

from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from ..models.refund import Refund
from ..repositories.inventory import InventoryRepository
from ..repositories.order import OrderRepository
from ..repositories.payment import PaymentRepository
from ..repositories.refund import RefundRepository


class RefundError(ValueError):
    """退款校验失败。"""


class RefundGateway(Protocol):
    """支付渠道退款适配器协议。"""

    async def refund(self, *, transaction_id: str, refund_no: str, amount_cents: int) -> str:
        """提交退款并返回渠道退款流水号。"""


class SandboxRefundGateway:
    """开发环境退款适配器，模拟渠道成功响应。"""

    async def refund(self, *, transaction_id: str, refund_no: str, amount_cents: int) -> str:
        """返回稳定的沙箱退款流水号。"""
        return f"sandbox-{refund_no}"


class RefundService:
    """创建退款申请；实际支付渠道退款由异步 worker 负责。"""

    def __init__(self, gateway: RefundGateway | None = None) -> None:
        self.payments = PaymentRepository()
        self.orders = OrderRepository()
        self.refunds = RefundRepository()
        self.inventory = InventoryRepository()
        self.gateway = gateway or SandboxRefundGateway()

    async def create(
        self,
        session: AsyncSession,
        *,
        user_id: int,
        payment_id: int,
        amount_cents: int,
        reason: str,
        request_id: str,
    ) -> Refund:
        """锁定支付单并创建不超过可退余额的退款申请。"""
        existing = await self.refunds.get_by_request(session, payment_id, request_id)
        if existing is not None:
            return existing
        payment = await self.payments.get_by_id(session, payment_id, for_update=True)
        if payment is None or payment.user_id != user_id:
            raise RefundError("支付单不存在")
        if payment.status != "SUCCESS":
            raise RefundError("支付单尚未成功，不能退款")
        active_amount = await self.refunds.sum_active_amount(session, payment_id)
        if amount_cents <= 0 or active_amount + amount_cents > payment.amount_cents:
            raise RefundError("退款金额超过可退余额")
        order = await self.orders.get_for_update(session, payment.order_id)
        order.refund_status = "APPLYING"
        await self.orders.flush(session)
        return await self.refunds.create(
            session,
            payment=payment,
            amount_cents=amount_cents,
            reason=reason,
            request_id=request_id,
        )

    async def process(
        self,
        session: AsyncSession,
        refund_id: int,
        *,
        restock_lines: list[tuple[int, int]] | None = None,
    ) -> Refund:
        """处理一笔待退款记录，成功后回补订单商品库存。"""
        refund = await self.refunds.get_for_update(session, refund_id)
        if refund is None:
            raise RefundError("退款记录不存在")
        if refund.status == "SUCCESS":
            return refund
        if refund.status not in {"PENDING", "FAILED"}:
            raise RefundError("退款记录当前不可处理")
        payment = await self.payments.get_by_id(session, refund.payment_id, for_update=True)
        if payment is None or not payment.transaction_id:
            raise RefundError("支付渠道交易号不存在")
        refund.attempt_count += 1
        try:
            transaction_id = await self.gateway.refund(
                transaction_id=payment.transaction_id,
                refund_no=refund.refund_no,
                amount_cents=refund.amount_cents,
            )
        except Exception as error:
            refund.status = "FAILED"
            refund.fail_reason = str(error)
            refund.updated_at = datetime.now(UTC)
            await self.refunds.flush(session)
            raise RefundError("渠道退款失败，可稍后重试") from error
        refund.status = "SUCCESS"
        refund.transaction_id = transaction_id
        refund.fail_reason = None
        refund.refunded_at = datetime.now(UTC)
        refund.updated_at = refund.refunded_at
        refund.provider_response = {"transactionId": transaction_id}
        order = payment.order
        active_amount = await self.refunds.sum_active_amount(session, payment.id)
        order.refund_status = "FULL" if active_amount >= payment.amount_cents else "PARTIAL"
        inventory_lines = (
            [(item.sku_id, item.quantity) for item in order.items] if restock_lines is None else restock_lines
        )
        for sku_id, quantity in inventory_lines:
            await self.inventory.purchase_in(
                session,
                sku_id,
                quantity,
                refund.refund_no,
                f"refund:{refund.id}",
            )
        await self.refunds.flush(session)
        return refund


def refund_response(refund: Refund) -> dict[str, object]:
    """转换退款实体为 API 响应。"""
    return {
        "id": refund.id,
        "refundNo": refund.refund_no,
        "paymentId": refund.payment_id,
        "amountCents": refund.amount_cents,
        "status": refund.status,
        "reason": refund.refund_reason,
        "createdAt": refund.created_at.isoformat(),
        "attemptCount": refund.attempt_count,
        "transactionId": refund.transaction_id,
    }
