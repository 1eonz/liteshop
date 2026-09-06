"""库存流水模型。"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


class InventoryLedger(Base):
    """记录库存变更前后快照，便于审计和回滚核对。"""

    __tablename__ = "stock_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    sku_id: Mapped[int] = mapped_column(ForeignKey("skus.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(32), index=True)
    quantity: Mapped[int] = mapped_column(Integer)
    physical_before: Mapped[int] = mapped_column(Integer, default=0)
    physical_after: Mapped[int] = mapped_column(Integer)
    locked_before: Mapped[int] = mapped_column(Integer, default=0)
    locked_after: Mapped[int] = mapped_column(Integer)
    reference_no: Mapped[str] = mapped_column(String(64), default="")
    request_id: Mapped[str] = mapped_column(String(64), default="", index=True)
    # 以下字段与 PRD E3.1.3 的审计列保持一致，旧字段保留用于历史迁移兼容。
    source_type: Mapped[str] = mapped_column(String(20), default="")
    source_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    change_type: Mapped[str] = mapped_column(String(20), default="")
    change_qty: Mapped[int] = mapped_column(Integer, default=0)
    operator_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
