"""订单超时取消任务，由 Celery beat 或同等调度器定时调用。"""

from datetime import UTC, datetime

from ..core.database import transaction
from ..services.order_workflow import OrderWorkflow


async def expire_pending_orders(batch_size: int = 100) -> int:
    """批量取消到期订单，返回本次处理数量。"""
    workflow = OrderWorkflow()
    processed = 0
    async with transaction() as session:
        orders = await workflow.orders.list_expired_for_update(session, datetime.now(UTC), batch_size)
        for order in orders:
            await workflow.expire_order(session, order, f"expiry:{order.id}")
            processed += 1
    return processed
