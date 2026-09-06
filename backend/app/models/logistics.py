"""物流轨迹模型。"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


class ShipmentTrackingEvent(Base):
    """订单物流节点，由本地适配器或第三方 webhook 写入。"""

    __tablename__ = "shipment_tracking_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(40))
    description: Mapped[str] = mapped_column(String(500))
    location: Mapped[str] = mapped_column(String(120), default="")
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
