"""物流轨迹服务。"""

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from ..models.logistics import ShipmentTrackingEvent
from ..repositories.logistics import LogisticsRepository
from ..repositories.order import OrderRepository
from ..schemas.logistics import TrackingEventCreate


class LogisticsError(ValueError):
    """物流业务错误。"""


class LogisticsService:
    """提供订单轨迹查询和后台节点写入。"""

    def __init__(
        self,
        repository: LogisticsRepository | None = None,
        orders: OrderRepository | None = None,
    ) -> None:
        self.repository = repository or LogisticsRepository()
        self.orders = orders or OrderRepository()

    async def list_events(self, session: AsyncSession, order_id: int) -> list[dict[str, object]]:
        """读取物流轨迹。"""
        await self.orders.get(session, order_id)
        return [
            {
                "id": event.id,
                "status": event.status,
                "description": event.description,
                "location": event.location,
                "occurredAt": event.occurred_at.isoformat(),
            }
            for event in await self.repository.list_events(session, order_id)
        ]

    async def add_event(self, session: AsyncSession, order_id: int, payload: TrackingEventCreate) -> dict[str, object]:
        """写入物流节点。"""
        await self.orders.get(session, order_id)
        event = ShipmentTrackingEvent(
            order_id=order_id,
            status=payload.status,
            description=payload.description,
            location=payload.location,
            occurred_at=payload.occurred_at,
            created_at=datetime.now(UTC),
        )
        await self.repository.add_event(session, event)
        return {
            "id": event.id,
            "status": event.status,
            "description": event.description,
            "location": event.location,
            "occurredAt": event.occurred_at.isoformat(),
        }


logistics_service = LogisticsService()
