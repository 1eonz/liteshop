"""物流轨迹仓储。"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.logistics import ShipmentTrackingEvent


class LogisticsRepository:
    """封装订单物流节点读写。"""

    async def list_events(self, session: AsyncSession, order_id: int) -> list[ShipmentTrackingEvent]:
        """按发生时间倒序读取轨迹。"""
        result = await session.scalars(
            select(ShipmentTrackingEvent)
            .where(ShipmentTrackingEvent.order_id == order_id)
            .order_by(ShipmentTrackingEvent.occurred_at.desc(), ShipmentTrackingEvent.id.desc())
        )
        return list(result.all())

    async def add_event(self, session: AsyncSession, event: ShipmentTrackingEvent) -> ShipmentTrackingEvent:
        """新增物流节点。"""
        session.add(event)
        await session.flush()
        return event
