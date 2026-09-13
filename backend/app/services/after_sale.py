"""售后申请、审核和退款编排。"""

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from ..enums.after_sale import ALLOWED_AFTER_SALE_TRANSITIONS, AfterSaleStatus, AfterSaleType
from ..models.after_sale import AfterSale
from ..repositories.after_sale import AfterSaleRepository
from ..schemas.after_sale import AfterSaleCreate
from .refund import RefundError, RefundService


class AfterSaleError(ValueError):
    """售后业务校验失败。"""


class AfterSaleService:
    """在事务中协调售后状态、金额和退款。"""

    def __init__(self, repository: AfterSaleRepository | None = None, refunds: RefundService | None = None) -> None:
        self.repository = repository or AfterSaleRepository()
        self.refunds = refunds or RefundService()

    @staticmethod
    def _transition(item: AfterSale, target: AfterSaleStatus) -> None:
        """只允许状态机声明过的售后流转。"""
        current = AfterSaleStatus(item.status)
        if target not in ALLOWED_AFTER_SALE_TRANSITIONS[current]:
            raise AfterSaleError(f"{current.value}->{target.value} 不允许")
        item.status = target.value
        item.updated_at = datetime.now(UTC)

    async def create(self, session: AsyncSession, user_id: int, request_id: str, payload: AfterSaleCreate) -> AfterSale:
        """校验订单项归属、完成状态和可退金额后创建售后单。"""
        existing = await self.repository.get_by_request(session, user_id, request_id)
        if existing is not None:
            return existing
        order_item_id = payload.order_item_id
        sale_type = payload.type
        amount_cents = payload.amount_cents
        item = await self.repository.get_order_item_for_user(session, order_item_id, user_id)
        if item is None or item.order.status not in {"PAID", "SHIPPED", "COMPLETED"}:
            raise AfterSaleError("只有已支付或已发货订单可以申请售后")
        if amount_cents > item.total_amount:
            raise AfterSaleError("售后金额不能超过订单项金额")
        if await self.repository.has_active_for_order_item(session, order_item_id):
            raise AfterSaleError("该订单项已有进行中的售后申请")
        return await self.repository.create(
            session,
            item=item,
            user_id=user_id,
            request_id=request_id,
            sale_type=sale_type.value,
            amount_cents=amount_cents,
            reason=payload.reason,
            evidence_urls=payload.evidence_urls,
        )

    async def list_for_user(self, session: AsyncSession, user_id: int) -> list[dict[str, object]]:
        """读取用户售后单。"""
        return [after_sale_response(item) for item in await self.repository.list_for_user(session, user_id)]

    async def list_for_admin(self, session: AsyncSession, status: str | None = None) -> list[AfterSale]:
        """读取后台售后单，隐藏仓储筛选实现。"""
        return await self.repository.list_all(session, status)

    async def get_for_user(self, session: AsyncSession, after_sale_id: int, user_id: int) -> AfterSale:
        """读取并校验售后归属。"""
        item = await self.repository.get_for_update(session, after_sale_id)
        if item is None or item.user_id != user_id:
            raise AfterSaleError("售后单不存在")
        return item

    async def audit(self, session: AsyncSession, after_sale_id: int, approved: bool, reason: str) -> AfterSale:
        """审核售后申请；仅审核中状态可操作。"""
        item = await self.repository.get_for_update(session, after_sale_id)
        if item is None:
            raise AfterSaleError("售后单不存在")
        if item.status != AfterSaleStatus.PENDING_REVIEW.value:
            raise AfterSaleError("售后单当前不可审核")
        target = AfterSaleStatus.APPROVED if approved else AfterSaleStatus.REJECTED
        self._transition(item, target)
        item.audit_reason = reason or None
        item.reviewed_at = datetime.now(UTC)
        if not approved:
            item.active_key = None
        elif item.type == AfterSaleType.REFUND_ONLY.value:
            self._transition(item, AfterSaleStatus.REFUNDING)
        else:
            self._transition(item, AfterSaleStatus.WAITING_RETURN)
        await self.repository.flush(session)
        return item

    async def submit_return(
        self, session: AsyncSession, after_sale_id: int, user_id: int, tracking_no: str
    ) -> AfterSale:
        """提交退货物流并推进状态。"""
        item = await self.get_for_user(session, after_sale_id, user_id)
        if item.status != AfterSaleStatus.WAITING_RETURN.value:
            raise AfterSaleError("当前售后单不需要提交退货")
        item.return_tracking_no = tracking_no
        self._transition(item, AfterSaleStatus.RETURNED)
        item.returned_at = datetime.now(UTC)
        await self.repository.flush(session)
        return item

    async def complete_refund(self, session: AsyncSession, after_sale_id: int) -> AfterSale:
        """执行一次退款并将售后单置为完成。"""
        item = await self.repository.get_for_update(session, after_sale_id)
        if item is None:
            raise AfterSaleError("售后单不存在")
        if item.status not in {AfterSaleStatus.REFUNDING.value, AfterSaleStatus.RETURNED.value}:
            raise AfterSaleError("当前售后单不可退款")
        order_item = await self.repository.get_order_item_for_user(session, item.order_item_id, item.user_id)
        if order_item is None:
            raise AfterSaleError("售后订单项不存在")
        if item.type == AfterSaleType.EXCHANGE.value:
            await self.refunds.inventory.purchase_in(
                session,
                order_item.sku_id,
                order_item.quantity,
                item.after_sale_no,
                f"after-sale:{item.id}",
            )
            self._transition(item, AfterSaleStatus.REFUNDING)
            self._transition(item, AfterSaleStatus.COMPLETED)
            item.completed_at = datetime.now(UTC)
            item.active_key = None
            await self.repository.flush(session)
            return item
        payment = await self.refunds.payments.get_for_order(session, item.order_id, for_update=True)
        if payment is None:
            raise AfterSaleError("订单支付单不存在")
        if item.status == AfterSaleStatus.RETURNED.value:
            self._transition(item, AfterSaleStatus.REFUNDING)
        try:
            refund = await self.refunds.create(
                session,
                user_id=item.user_id,
                payment_id=payment.id,
                amount_cents=item.amount_cents,
                reason=item.reason,
                request_id=f"after-sale:{item.id}",
            )
        except RefundError as error:
            raise AfterSaleError(str(error)) from error
        restock_lines = (
            [(order_item.sku_id, order_item.quantity)] if item.type == AfterSaleType.RETURN_REFUND.value else []
        )
        try:
            await self.refunds.process(session, refund.id, restock_lines=restock_lines)
        except RefundError as error:
            raise AfterSaleError(str(error)) from error
        item.refund_id = refund.id
        self._transition(item, AfterSaleStatus.COMPLETED)
        item.completed_at = datetime.now(UTC)
        item.active_key = None
        await self.repository.flush(session)
        return item


def after_sale_response(item: AfterSale) -> dict[str, object]:
    """转换售后实体为响应。"""
    return {
        "id": item.id,
        "afterSaleNo": item.after_sale_no,
        "orderId": item.order_id,
        "orderItemId": item.order_item_id,
        "type": item.type,
        "status": item.status,
        "amountCents": item.amount_cents,
        "reason": item.reason,
        "evidenceUrls": list(item.evidence_urls),
        "returnTrackingNo": item.return_tracking_no,
        "auditReason": item.audit_reason,
        "createdAt": item.created_at.isoformat(),
        "updatedAt": item.updated_at.isoformat(),
    }


after_sale_service = AfterSaleService()
